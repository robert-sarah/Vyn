"""Analyse sémantique — typage statique & ownership."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from vyn.ast.nodes import *
from vyn.parser import Parser as VynParser

ROOT = Path(__file__).resolve().parent.parent.parent
STDLIB = ROOT / "stdlib"
VENDOR = ROOT / "vendor"

_STD_SYMBOLS = [
    ("io", ("print", "println", "print_int", "print_i32")),
    ("sys", ("sleep",)),
    ("math", ("abs", "sqrt", "clamp", "lerp")),
    ("log", ("info", "error", "warn", "debug")),
    ("str", ("len", "upper", "lower", "trim", "contains", "replace")),
    ("fs", ("exists", "read", "write", "remove", "list_dir")),
    ("json", ("parse", "stringify", "parse_int")),
    ("time", ("now_ms", "now_sec", "format")),
    ("net", ("ping", "resolve", "get", "post")),
    ("http", ("get", "post", "ok", "not_found")),
    ("server", ("route", "listen", "listen_async", "serve_static", "stop")),
    ("html", ("page", "h1", "h2", "p", "div", "a", "escape", "style")),
    ("css", ("rule", "class", "stylesheet")),
    ("db", ("open", "exec", "query", "close")),
    ("ai", ("model_new", "train", "predict", "loss", "epochs", "save", "load")),
    ("numpy", ("version", "array", "zeros", "ones", "mean", "dot", "shape", "reshape")),
    ("torch", ("version", "tensor", "relu", "train_linear", "save", "load")),
    ("tensorflow", ("version", "train_xor", "predict")),
    ("cv", ("version", "read_size", "grayscale", "resize", "blur")),
    ("pandas", ("version", "read_csv", "rows", "mean", "head_json")),
    ("sklearn", ("version", "fit_linear", "predict", "score")),
    ("plot", ("version", "line", "hist")),
    ("gui", ("window", "label", "button", "run", "alert")),
    ("vec", ("new", "push", "len", "get", "set")),
    ("rand", ("seed", "next_f32", "next_i32")),
]


@dataclass
class SemanticError(Exception):
    message: str

    def __str__(self) -> str:
        return f"[Semantic] {self.message}"


@dataclass
class Symbol:
    name: str
    type: TypeNode
    is_mut: bool = False
    is_hot: bool = False


@dataclass
class StructInfo:
    name: str
    fields: Dict[str, Field]


class SemanticAnalyzer:
    PRIMITIVES = {"void", "i32", "f32", "bool", "str"}

    def __init__(self):
        self.structs: Dict[str, StructInfo] = {}
        self.functions: Dict[str, FunctionDecl] = {}
        self.externs: Dict[str, ExternDecl] = {}
        self.enums: Dict[str, EnumDecl] = {}
        self.traits: Dict[str, TraitDecl] = {}
        self.type_aliases: Dict[str, TypeNode] = {}
        self.consts: Dict[str, Symbol] = {}
        self.scopes: list[Dict[str, Symbol]] = [self._builtin_scope()]
        self.errors: list[str] = []
        self.profiled_functions: list[str] = []
        self.hot_functions: list[str] = []

    def _builtin_scope(self) -> Dict[str, Symbol]:
        syms: Dict[str, Symbol] = {}
        for mod, methods in _STD_SYMBOLS:
            for m in methods:
                syms[f"{mod}.{m}"] = Symbol(f"{mod}.{m}", TypeNode("fn"), False)
        return syms

    def analyze(self, program: Program) -> None:
        for imp in program.imports:
            self._resolve_import(imp)
            self._load_module_symbols(imp.path)
        for u in getattr(program, "uses", []):
            self._resolve_import(ImportDecl(u.path))
            self._load_module_symbols(u.path)
        self._load_manifest_deps()
        for ext in program.externs:
            self.externs[ext.name] = ext
        for s in program.structs:
            self.structs[s.name] = StructInfo(s.name, {f.name: f for f in s.fields})
        for e in program.enums:
            self.enums[e.name] = e
        for ta in program.type_aliases:
            self.type_aliases[ta.name] = ta.target
        for c in program.consts:
            self.consts[c.name] = Symbol(c.name, c.type, False)
        for t in program.traits:
            self.traits[t.name] = t
        for mod in getattr(program, "mods", []):
            for fn in mod.functions:
                self.functions[f"{mod.name}.{fn.name}"] = fn
            for s in mod.structs:
                self.structs[s.name] = StructInfo(s.name, {f.name: f for f in s.fields})
            for e in mod.enums:
                self.enums[e.name] = e
        for fn in program.functions:
            self.functions[fn.name] = fn
            if fn.is_hot:
                self.hot_functions.append(fn.name)
            if any(a.name == "profile" for a in fn.attributes):
                self.profiled_functions.append(fn.name)
        for impl in program.impls:
            for m in impl.methods:
                key = f"{impl.struct_name}.{m.name}"
                self.functions[key] = m
        for fn in program.functions:
            self._check_function(fn)
        for impl in program.impls:
            for m in impl.methods:
                self._check_method(impl.struct_name, m)
        for stmt in getattr(program, "init_stmts", []):
            self._check_stmt(stmt, TypeNode("void"))
        for c in program.consts:
            val_type = self._infer(c.value)
            if c.type.name not in self.PRIMITIVES and c.type.name not in self.structs:
                resolved = self._resolve_type(c.type)
                if resolved.name not in self.PRIMITIVES:
                    self.errors.append(f"unknown type in const {c.name}: {c.type.name}")
        if self.errors:
            raise SemanticError("\n".join(self.errors))

    def _resolve_type(self, typ: TypeNode) -> TypeNode:
        while typ.name in self.type_aliases and not typ.args:
            typ = self.type_aliases[typ.name]
        return typ

    def _load_module_symbols(self, path: str) -> None:
        for base, suffix in ((VENDOR, "lib.vyn"), (STDLIB, ".vyn")):
            if suffix == "lib.vyn":
                lib = base / path / "lib.vyn"
            else:
                lib = base / f"{path.replace('.', '/')}.vyn"
            if lib.exists():
                try:
                    sub = VynParser(lib.read_text(encoding="utf-8")).parse()
                    for fn in sub.functions:
                        self.functions[fn.name] = fn
                except Exception:
                    pass
                break

    def _load_manifest_deps(self) -> None:
        manifest = ROOT / "vyn.toml"
        if not manifest.exists():
            return
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore
            data = tomllib.loads(manifest.read_text(encoding="utf-8"))
            for dep in data.get("dependencies", {}):
                self._load_module_symbols(dep)
        except Exception:
            pass

    def _resolve_import(self, imp: ImportDecl) -> None:
        allowed = {"std.io", "std.sys", "std.mem", "std.math", "std.str",
                   "std.net", "std.sync", "std.fs", "std.json", "std.time",
                   "std.gui", "std.log", "std.vec", "std.rand", "std.hash",
                   "std.array", "std.thread", "std.crypto", "std.html", "std.css",
                   "std.server", "std.http", "std.ai", "std.db",
                   "std.numpy", "std.torch", "std.tensorflow", "std.cv",
                   "std.pandas", "std.sklearn", "std.plot"}
        if imp.path in allowed or imp.path.startswith("std."):
            return
        pkg = VENDOR / imp.path / "lib.vyn"
        if pkg.exists():
            return
        self.errors.append(f"unknown import: {imp.path} (vpm add {imp.path})")

    def _push(self) -> None:
        self.scopes.append({})

    def _pop(self) -> None:
        self.scopes.pop()

    def _define(self, sym: Symbol) -> None:
        if sym.name in self.scopes[-1]:
            self.errors.append(f"redefined symbol: {sym.name}")
        self.scopes[-1][sym.name] = sym

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name in self.consts:
            return self.consts[name]
        return None

    def _check_function(self, fn: FunctionDecl) -> None:
        self._push()
        for p in fn.params:
            self._define(Symbol(p.name, p.type, p.is_mut))
        for stmt in fn.body:
            self._check_stmt(stmt, fn.return_type)
        self._pop()

    def _check_method(self, struct_name: str, fn: FunctionDecl) -> None:
        self._push()
        self._define(Symbol("self", TypeNode(struct_name), False))
        for p in fn.params:
            if p.name != "self":
                self._define(Symbol(p.name, p.type, p.is_mut))
        for stmt in fn.body:
            self._check_stmt(stmt, fn.return_type)
        self._pop()

    def _check_stmt(self, stmt: Stmt, ret: TypeNode) -> None:
        if isinstance(stmt, LetStmt):
            typ = stmt.type or self._infer(stmt.value)
            if not stmt.is_mut and isinstance(stmt.value, Identifier):
                pass  # immutabilité par défaut
            self._define(Symbol(stmt.name, typ, stmt.is_mut))
        elif isinstance(stmt, AssignStmt):
            if isinstance(stmt.target, Identifier):
                if stmt.target.name in self.consts:
                    self.errors.append(f"cannot assign to const: {stmt.target.name}")
                sym = self._lookup(stmt.target.name)
                if sym and not sym.is_mut:
                    self.errors.append(f"cannot assign to immutable: {stmt.target.name}")
                else:
                    self._infer(stmt.value)
            elif isinstance(stmt.target, BinaryOp) and stmt.target.op == "[]":
                self._infer(stmt.target.left)
                self._infer(stmt.target.right)
                self._infer(stmt.value)
            elif isinstance(stmt.target, MemberAccess):
                self._infer(stmt.target.object)
                self._infer(stmt.value)
            else:
                self._infer(stmt.value)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._infer(stmt.value)
        elif isinstance(stmt, IfStmt):
            self._infer(stmt.condition)
            for s in stmt.then_body:
                self._check_stmt(s, ret)
            if stmt.else_body:
                for s in stmt.else_body:
                    self._check_stmt(s, ret)
        elif isinstance(stmt, LoopStmt):
            if stmt.iterator:
                self._push()
                var, it = stmt.iterator
                self._define(Symbol(var, TypeNode("f32"), False))
                self._infer(it)
            for s in stmt.body:
                self._check_stmt(s, ret)
            if stmt.iterator:
                self._pop()
        elif isinstance(stmt, MatchStmt):
            self._infer(stmt.expr)
            for case in stmt.cases:
                if case.pattern:
                    self._infer(case.pattern)
                for s in case.body:
                    self._check_stmt(s, ret)
        elif isinstance(stmt, TryStmt):
            for s in stmt.body:
                self._check_stmt(s, ret)
            self._push()
            self._define(Symbol(stmt.catch_var, TypeNode("str"), False))
            for s in stmt.catch_body:
                self._check_stmt(s, ret)
            self._pop()
        elif isinstance(stmt, ThrowStmt):
            self._infer(stmt.value)
        elif isinstance(stmt, BreakStmt):
            pass
        elif isinstance(stmt, ContinueStmt):
            pass
        elif isinstance(stmt, ExprStmt):
            self._infer(stmt.expr)

    def _infer(self, expr: Optional[Expr]) -> TypeNode:
        if expr is None:
            return TypeNode("void")
        if isinstance(expr, IntLiteral):
            return TypeNode("i32")
        if isinstance(expr, FloatLiteral):
            return TypeNode("f32")
        if isinstance(expr, BoolLiteral):
            return TypeNode("bool")
        if isinstance(expr, StringLiteral):
            return TypeNode("str")
        if isinstance(expr, Identifier):
            if expr.name in self.consts:
                return self.consts[expr.name].type
            sym = self._lookup(expr.name)
            if not sym:
                self.errors.append(f"unknown identifier: {expr.name}")
                return TypeNode("void")
            return sym.type
        if isinstance(expr, BinaryOp):
            lt = self._infer(expr.left)
            rt = self._infer(expr.right)
            if lt.name in ("i32", "f32") and rt.name in ("i32", "f32"):
                return TypeNode("f32" if "f32" in (lt.name, rt.name) else "i32")
            return TypeNode("bool")
        if isinstance(expr, UnaryOp):
            return self._infer(expr.operand)
        if isinstance(expr, CallExpr):
            if isinstance(expr.callee, MemberAccess):
                return self._infer_member_call(expr.callee, expr.args)
            if isinstance(expr.callee, Identifier):
                name = expr.callee.name
                for enum_decl in self.enums.values():
                    for variant in enum_decl.variants:
                        if variant.name == name and variant.payload:
                            return variant.payload
                if name in self.functions:
                    return self.functions[name].return_type
                if name in self.externs:
                    return self.externs[name].return_type
                sym = self._lookup(name)
                if sym:
                    return sym.type.args[-1] if sym.type.name == "fn" else TypeNode("void")
                self.errors.append(f"unknown function: {name}")
            return TypeNode("void")
        if isinstance(expr, MemberAccess):
            if isinstance(expr.object, Identifier) and expr.object.name in self.enums:
                enum = self.enums[expr.object.name]
                if any(v.name == expr.member for v in enum.variants):
                    v = next(x for x in enum.variants if x.name == expr.member)
                    return v.payload or TypeNode("i32")
            return TypeNode("fn")
        if isinstance(expr, StructInit):
            if expr.struct_name not in self.structs:
                self.errors.append(f"unknown struct: {expr.struct_name}")
            return TypeNode(expr.struct_name)
        if isinstance(expr, ArrayLiteral):
            if expr.repeat:
                elem, _ = expr.repeat
                return TypeNode("array", [self._infer(elem)])
            if expr.elements:
                return TypeNode("array", [self._infer(expr.elements[0])])
            return TypeNode("array", [TypeNode("void")])
        return TypeNode("void")

    def _infer_member_call(self, access: MemberAccess, args: list[Expr]) -> TypeNode:
        method = access.member
        if isinstance(access.object, Identifier):
            mod = access.object.name
            full = f"{mod}.{method}"
            if full in self.functions:
                return self.functions[full].return_type
            sym = self._lookup(full)
            if sym:
                return TypeNode("void")
            if full in self.functions:
                return self.functions[full].return_type
            if method in self.functions:
                return self.functions[method].return_type
        return TypeNode("void")
