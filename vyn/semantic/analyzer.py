"""Analyse sémantique — typage statique & ownership."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from vyn.ast.nodes import *


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
        self.scopes: list[Dict[str, Symbol]] = [self._builtin_scope()]
        self.errors: list[str] = []
        self.profiled_functions: list[str] = []
        self.hot_functions: list[str] = []

    def _builtin_scope(self) -> Dict[str, Symbol]:
        return {
            "io.print": Symbol("io.print", TypeNode("fn", [TypeNode("f32")]), False),
            "io.println": Symbol("io.println", TypeNode("fn", [TypeNode("str")]), False),
            "sys.sleep": Symbol("sys.sleep", TypeNode("fn", [TypeNode("i32")]), False),
            "math.clamp": Symbol("math.clamp", TypeNode("fn", [TypeNode("f32"), TypeNode("f32"), TypeNode("f32")]), False),
            "math.lerp": Symbol("math.lerp", TypeNode("fn", [TypeNode("f32"), TypeNode("f32"), TypeNode("f32")]), False),
            "math.abs": Symbol("math.abs", TypeNode("fn", [TypeNode("f32")]), False),
            "math.sqrt": Symbol("math.sqrt", TypeNode("fn", [TypeNode("f32")]), False),
        }

    def analyze(self, program: Program) -> None:
        for imp in program.imports:
            self._resolve_import(imp)
        for u in getattr(program, "uses", []):
            self._resolve_import(ImportDecl(u.path))
        for ext in program.externs:
            self.externs[ext.name] = ext
        for s in program.structs:
            self.structs[s.name] = StructInfo(s.name, {f.name: f for f in s.fields})
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
        if self.errors:
            raise SemanticError("\n".join(self.errors))

    def _resolve_import(self, imp: ImportDecl) -> None:
        allowed = {"std.io", "std.sys", "std.mem", "std.math", "std.str",
                   "std.net", "std.sync", "std.fs", "std.json", "std.time",
                   "std.gui", "std.log", "std.vec", "std.rand", "std.hash",
                   "std.array", "std.thread", "std.crypto", "std.html", "std.css",
                   "std.server", "std.http"}
        if imp.path in allowed or imp.path.startswith("std."):
            return
        # Packages VPM dans vendor/
        from pathlib import Path
        vendor = Path(__file__).resolve().parent.parent.parent / "vendor"
        pkg = vendor / imp.path / "lib.vyn"
        if pkg.exists():
            return
        self.errors.append(f"import inconnu: {imp.path} (stdlib ou vpm add {imp.path})")

    def _push(self) -> None:
        self.scopes.append({})

    def _pop(self) -> None:
        self.scopes.pop()

    def _define(self, sym: Symbol) -> None:
        if sym.name in self.scopes[-1]:
            self.errors.append(f"symbole redéfini: {sym.name}")
        self.scopes[-1][sym.name] = sym

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
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
                sym = self._lookup(stmt.target.name)
                if sym and not sym.is_mut:
                    self.errors.append(f"assignation à variable immutable: {stmt.target.name}")
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
            sym = self._lookup(expr.name)
            if not sym:
                self.errors.append(f"identifiant inconnu: {expr.name}")
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
                if name in self.functions:
                    return self.functions[name].return_type
                if name in self.externs:
                    return self.externs[name].return_type
                sym = self._lookup(name)
                if sym:
                    return sym.type.args[-1] if sym.type.name == "fn" else TypeNode("void")
                self.errors.append(f"fonction inconnue: {name}")
            return TypeNode("void")
        if isinstance(expr, MemberAccess):
            return TypeNode("fn")
        if isinstance(expr, StructInit):
            if expr.struct_name not in self.structs:
                self.errors.append(f"struct inconnu: {expr.struct_name}")
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
        qual = access.object
        method = access.member
        if isinstance(qual, Identifier) and qual.name in ("io", "sys", "math"):
            full = f"{qual.name}.{method}"
            sym = self._lookup(full)
            if sym:
                return TypeNode("void")
        if isinstance(qual, Identifier):
            key = f"{qual.name}.{method}"
            if key in self.functions:
                return self.functions[key].return_type
        return TypeNode("void")
