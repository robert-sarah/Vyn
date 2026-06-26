"""Interpréteur Vyn — exécution directe sans LLVM."""
from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Optional

from vyn.ast.nodes import *
from vyn.parser import Parser
from vyn.semantic import SemanticAnalyzer


class _BreakLoop(Exception):
    pass


class _ContinueLoop(Exception):
    pass


from vyn.ownership import OwnedValue, OwnershipError


class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.globals: Dict[str, OwnedValue] = {}
        self.scopes: List[Dict[str, OwnedValue]] = [self._builtin_scope()]
        self.modules: Dict[str, ModDecl] = {m.name: m for m in getattr(program, "mods", [])}
        self.structs: Dict[str, StructDecl] = {s.name: s for s in program.structs}
        for mod in getattr(program, "mods", []):
            for s in mod.structs:
                self.structs[s.name] = s
        self.enums: Dict[str, Dict[str, int]] = {}
        self.enum_meta: Dict[str, EnumDecl] = {}
        for e in getattr(program, "enums", []):
            self._register_enum(e)
        for mod in getattr(program, "mods", []):
            for e in mod.enums:
                self._register_enum(e)
        self.functions: Dict[str, FunctionDecl] = {}
        self.impl_methods: Dict[str, FunctionDecl] = {}
        for fn in program.functions:
            self.functions[fn.name] = fn
        for mod in getattr(program, "mods", []):
            for fn in mod.functions:
                self.functions[f"{mod.name}.{fn.name}"] = fn
        for impl in program.impls:
            for m in impl.methods:
                self.impl_methods[f"{impl.struct_name}.{m.name}"] = m
                self.impl_methods[f"{impl.struct_name}_{m.name}"] = m
        for c in getattr(program, "consts", []):
            val = self._eval_const(c.value)
            self.globals[c.name] = OwnedValue(val, c.type.name, False)
        for mod in getattr(program, "mods", []):
            for c in mod.consts:
                val = self._eval_const(c.value)
                self.globals[f"{mod.name}.{c.name}"] = OwnedValue(val, c.type.name, False)

    def _register_enum(self, e: EnumDecl) -> None:
        self.enum_meta[e.name] = e
        self.enums[e.name] = {v.name: i for i, v in enumerate(e.variants)}

    def reload_hot_functions(self, program: Program) -> list[str]:
        """Remplace les corps des hot fn — swap à chaud en mémoire."""
        swapped = []
        for fn in program.functions:
            if fn.is_hot and fn.name in self.functions:
                self.functions[fn.name] = fn
                swapped.append(fn.name)
        for mod in getattr(program, "mods", []):
            for fn in mod.functions:
                if fn.is_hot:
                    key = f"{mod.name}.{fn.name}"
                    if key in self.functions:
                        self.functions[key] = fn
                        swapped.append(key)
        return swapped

    def _builtin_scope(self) -> Dict[str, OwnedValue]:
        return {}

    def run(self) -> int:
        from vyn.gui_runtime import reset_gui
        from vyn.stdlib_runtime import reset_http_server
        reset_gui()
        reset_http_server()
        if "main" not in self.functions:
            raise RuntimeError("fonction main introuvable")
        for stmt in self.program.init_stmts:
            r = self._exec_stmt(stmt)
            if r and r[0] == "return":
                return int(r[1] or 0)
        return int(self._call_fn(self.functions["main"], []) or 0)

    def _push(self):
        self.scopes.append({})

    def _pop(self):
        self.scopes.pop()

    def _set(self, name: str, val: Any, vtype: str, is_mut: bool,
             is_own: bool = False, is_ref: bool = False) -> None:
        self.scopes[-1][name] = OwnedValue(val, vtype, is_mut, is_own, is_ref)

    def _get(self, name: str) -> OwnedValue:
        if name in self.globals:
            self.globals[name].check_read(name)
            return self.globals[name]
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name].check_read(name)
                return scope[name]
        raise RuntimeError(f"variable non définie: {name}")

    def _eval_const(self, expr: Optional[Expr]) -> Any:
        """Évalue une expression constante (sans scope utilisateur)."""
        if expr is None:
            return 0
        if isinstance(expr, (IntLiteral, FloatLiteral, BoolLiteral, StringLiteral)):
            return expr.value
        if isinstance(expr, UnaryOp):
            o = self._eval_const(expr.operand)
            if expr.op == "-":
                return -o
            if expr.op == "!":
                return not self._truthy(o)
        if isinstance(expr, BinaryOp):
            l, r = self._eval_const(expr.left), self._eval_const(expr.right)
            if expr.op == "+":
                return l + r
            if expr.op == "-":
                return l - r
            if expr.op == "*":
                return l * r
        return self._eval(expr)

    def _call_method(self, fn: FunctionDecl, args: list, self_obj=None, struct_name=None) -> Any:
        self._push()
        profiled = any(a.name == "profile" for a in fn.attributes)
        t0 = time.perf_counter() if profiled else 0
        if profiled:
            print(f"[VynProfile] START {fn.name}", file=sys.stderr)
        ai = 0
        for p in fn.params:
            if p.name == "self":
                self._set("self", self_obj, struct_name or "Self", False)
            else:
                self._set(p.name, args[ai], p.type.name, p.is_mut); ai += 1
        result = None
        for stmt in fn.body:
            r = self._exec_stmt(stmt, struct_name)
            if r and r[0] == "return":
                result = r[1]; break
        self._pop()
        if profiled:
            ms = (time.perf_counter() - t0) * 1000
            print(f"[VynProfile] END {fn.name} — {ms:.3f} ms", file=sys.stderr)
        return result

    def _call_fn(self, fn: FunctionDecl, args: list, self_obj=None, struct_name=None) -> Any:
        if fn.is_hot:
            print(f"[VynHot] {fn.name}", file=sys.stderr)
        return self._call_method(fn, args, self_obj, struct_name)

    def _exec_stmt(self, stmt: Stmt, struct_name: Optional[str] = None):
        if isinstance(stmt, LetStmt):
            val = self._eval(stmt.value) if stmt.value else 0
            if stmt.type:
                vtype = stmt.type.name
                is_own = stmt.type.is_own
                is_ref = stmt.type.is_ref
            elif isinstance(stmt.value, StructInit):
                vtype = stmt.value.struct_name
                is_own, is_ref = False, False
            elif isinstance(stmt.value, ArrayLiteral):
                vtype = "array"
                is_own, is_ref = False, False
            else:
                vtype = self._infer_type(val)
                is_own, is_ref = False, False
            if isinstance(stmt.value, Identifier):
                src = self._find_binding(stmt.value.name)
                if src and src.is_own:
                    src.move_out(stmt.value.name)
            self._set(stmt.name, val, vtype, stmt.is_mut, is_own, is_ref)
        elif isinstance(stmt, AssignStmt):
            val = self._eval(stmt.value)
            if isinstance(stmt.target, Identifier):
                v = self._get(stmt.target.name)
                if not v.is_mut:
                    raise RuntimeError(f"assignation à immutable: {stmt.target.name}")
                if isinstance(stmt.value, Identifier):
                    src = self._find_binding(stmt.value.name)
                    if src and src.is_own:
                        val = src.move_out(stmt.value.name)
                v.data = val
            elif isinstance(stmt.target, BinaryOp) and stmt.target.op == "[]":
                arr = self._eval(stmt.target.left)
                idx = int(self._eval(stmt.target.right))
                if isinstance(arr, list):
                    while len(arr) <= idx:
                        arr.append(0)
                    arr[idx] = val
                else:
                    raise RuntimeError("indexation sur non-tableau")
            elif isinstance(stmt.target, MemberAccess):
                if isinstance(stmt.target.object, Identifier) and stmt.target.object.name == "self" and struct_name:
                    self_obj = self._get("self").data
                    self_obj[stmt.target.member] = val
                else:
                    obj = self._eval(stmt.target.object)
                    if isinstance(obj, dict):
                        obj[stmt.target.member] = val
                    else:
                        raise RuntimeError(f"assignation membre impossible: {stmt.target.member}")
        elif isinstance(stmt, ReturnStmt):
            return ("return", self._eval(stmt.value) if stmt.value else 0)
        elif isinstance(stmt, IfStmt):
            if self._truthy(self._eval(stmt.condition)):
                for s in stmt.then_body:
                    r = self._exec_stmt(s, struct_name)
                    if r and r[0] == "return":
                        return r
            elif stmt.else_body:
                for s in stmt.else_body:
                    r = self._exec_stmt(s, struct_name)
                    if r and r[0] == "return":
                        return r
        elif isinstance(stmt, LoopStmt):
            if stmt.iterator:
                var, it = stmt.iterator
                arr = self._eval(it)
                if isinstance(arr, list):
                    try:
                        for item in arr:
                            self._set(var, item, "f32", False)
                            try:
                                for s in stmt.body:
                                    r = self._exec_stmt(s, struct_name)
                                    if r and r[0] == "return":
                                        return r
                            except _ContinueLoop:
                                continue
                    except _BreakLoop:
                        pass
            else:
                try:
                    while True:
                        try:
                            for s in stmt.body:
                                r = self._exec_stmt(s, struct_name)
                                if r and r[0] == "return":
                                    return r
                        except _ContinueLoop:
                            continue
                except _BreakLoop:
                    pass
        elif isinstance(stmt, BreakStmt):
            raise _BreakLoop()
        elif isinstance(stmt, ContinueStmt):
            raise _ContinueLoop()
        elif isinstance(stmt, MatchStmt):
            val = self._eval(stmt.expr)
            matched = False
            for case in stmt.cases:
                if case.pattern is None:
                    if not matched:
                        for s in case.body:
                            r = self._exec_stmt(s, struct_name)
                            if r and r[0] == "return":
                                return r
                    break
                elif isinstance(case.pattern, MemberAccess) and isinstance(case.pattern.object, Identifier):
                    if self._match_enum_pattern(val, case.pattern.object.name, case.pattern.member):
                        matched = True
                        for s in case.body:
                            r = self._exec_stmt(s, struct_name)
                            if r and r[0] == "return":
                                return r
                        break
                elif self._eval(case.pattern) == val:
                    matched = True
                    for s in case.body:
                        r = self._exec_stmt(s, struct_name)
                        if r and r[0] == "return":
                            return r
                    break
        elif isinstance(stmt, TryStmt):
            try:
                for s in stmt.body:
                    r = self._exec_stmt(s, struct_name)
                    if r and r[0] == "return":
                        return r
            except _BreakLoop:
                raise
            except _ContinueLoop:
                raise
            except Exception as e:
                self._push()
                self._set(stmt.catch_var, str(e), "str", False)
                for s in stmt.catch_body:
                    r = self._exec_stmt(s, struct_name)
                    if r and r[0] == "return":
                        self._pop()
                        return r
                self._pop()
        elif isinstance(stmt, ThrowStmt):
            raise RuntimeError(str(self._eval(stmt.value)))
        elif isinstance(stmt, ExprStmt):
            self._eval(stmt.expr)

    def _eval(self, expr: Optional[Expr]) -> Any:
        if expr is None:
            return 0
        if isinstance(expr, IntLiteral):
            return expr.value
        if isinstance(expr, FloatLiteral):
            return expr.value
        if isinstance(expr, BoolLiteral):
            return expr.value
        if isinstance(expr, StringLiteral):
            return expr.value
        if isinstance(expr, Identifier):
            return self._get(expr.name).data
        if isinstance(expr, BinaryOp):
            l, r = self._eval(expr.left), self._eval(expr.right)
            if expr.op == "+": return l + r
            if expr.op == "-": return l - r
            if expr.op == "*": return l * r
            if expr.op == "/": return l / r if r else 0
            if expr.op == "%": return l % r
            if expr.op == "==": return l == r
            if expr.op == "!=": return l != r
            if expr.op == "<": return l < r
            if expr.op == ">": return l > r
            if expr.op == "<=": return l <= r
            if expr.op == ">=": return l >= r
            if expr.op == "||": return self._truthy(l) or self._truthy(r)
            if expr.op == "&&": return self._truthy(l) and self._truthy(r)
            if expr.op == "[]": return l[int(r)]
        if isinstance(expr, UnaryOp):
            o = self._eval(expr.operand)
            if expr.op == "-": return -o
            if expr.op == "!": return not self._truthy(o)
        if isinstance(expr, CallExpr):
            return self._call(expr)
        if isinstance(expr, MemberAccess):
            if isinstance(expr.object, Identifier) and expr.object.name in self.modules:
                key = f"{expr.object.name}.{expr.member}"
                if key in self.globals:
                    return self.globals[key].data
            if isinstance(expr.object, Identifier) and expr.object.name in self.enums:
                ename = expr.object.name
                vname = expr.member
                idx = self.enums[ename].get(vname, 0)
                variant = self.enum_meta[ename].variants[idx]
                if variant.payload:
                    return {"__enum__": ename, "__variant__": vname, "__index__": idx, "__value__": None}
                return idx
            if isinstance(expr.object, Identifier) and expr.object.name == "self":
                return self._get("self").data.get(expr.member)
            obj = self._eval(expr.object)
            if isinstance(obj, dict):
                return obj.get(expr.member)
        if isinstance(expr, StructInit):
            return {k: self._eval(v) for k, v in expr.fields.items()}
        if isinstance(expr, ArrayLiteral):
            if expr.repeat:
                elem, count = expr.repeat
                v = self._eval(elem)
                return [v] * count
            return [self._eval(e) for e in expr.elements]
        return 0

    def _call(self, expr: CallExpr) -> Any:
        from vyn.stdlib_runtime import dispatch, _MISSING
        if isinstance(expr.callee, MemberAccess) and isinstance(expr.callee.object, Identifier):
            mod, method = expr.callee.object.name, expr.callee.member
            args = [self._eval(a) for a in expr.args]
            qual = f"{mod}.{method}"
            if qual in self.functions:
                return self._call_fn(self.functions[qual], args)
            if mod in self.modules and method in {f.name for f in self.modules[mod].functions}:
                return self._call_fn(self.functions[qual], args)
            result = dispatch(mod, method, args, self)
            if result is not _MISSING:
                return result
            if mod == "io" and method == "print":
                v = args[0]
                print(int(v) if isinstance(v, (int, float)) and float(v) == int(v) else v)
                return 0
            if mod == "io" and method == "println":
                print(args[0]); return 0
            if mod == "io" and method in ("print_int", "print_i32"):
                print(int(args[0])); return 0
            if mod == "sys" and method == "sleep":
                time.sleep(args[0] / 1000.0); return 0
            if mod == "log" and method in ("info", "error", "warn", "debug"):
                level = method.upper()
                out = sys.stderr if method == "error" else sys.stdout
                print(f"[{level}] {args[0]}", file=out)
                return 0
            if mod == "gui":
                from vyn.gui_runtime import get_gui
                g = get_gui()
                if method == "window":
                    g.window(str(args[0]), int(args[1]) if len(args) > 1 else 640,
                             int(args[2]) if len(args) > 2 else 480); return 0
                if method == "label":
                    g.label(str(args[0]), str(args[1]), int(args[2]), int(args[3])); return 0
                if method == "button":
                    cb_id = str(args[4]) if len(args) > 4 else ""
                    g.button(str(args[0]), str(args[1]), int(args[2]), int(args[3]), cb_id)
                    if cb_id and cb_id in self.functions:
                        fn = self.functions[cb_id]
                        g.set_callback(cb_id, lambda f=fn: self._call_fn(f, []))
                    return 0
                if method == "run":
                    g.run(); return 0
                if method == "alert":
                    g.alert(str(args[0])); return 0
            try:
                v = self._get(mod)
                stype = v.vtype
                for mk in (f"{stype}.{method}", f"{stype}_{method}"):
                    if mk in self.impl_methods:
                        return self._call_fn(self.impl_methods[mk], args, v.data, stype)
            except RuntimeError:
                pass
        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            args = [self._eval(a) for a in expr.args]
            for ename, variants in self.enums.items():
                if name in variants:
                    payload = args[0] if args else None
                    idx = variants[name]
                    variant = self.enum_meta[ename].variants[idx]
                    if variant.payload:
                        return {
                            "__enum__": ename, "__variant__": name,
                            "__index__": idx, "__value__": payload,
                        }
                    return idx
            if name in self.functions:
                return self._call_fn(self.functions[name], args)
            if name == "raw_hardware_call":
                return args[0] * 2
        return 0

    def _find_binding(self, name: str) -> Optional[OwnedValue]:
        if name in self.globals:
            return self.globals[name]
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _match_enum_pattern(self, val: Any, enum_name: str, variant_name: str) -> bool:
        if isinstance(val, dict) and val.get("__enum__") == enum_name:
            return val.get("__variant__") == variant_name
        if isinstance(val, int) and enum_name in self.enums:
            return self.enums[enum_name].get(variant_name) == val
        return False

    def _truthy(self, v) -> bool:
        return bool(v) if not isinstance(v, (int, float)) else v != 0

    def _infer_type(self, val) -> str:
        if isinstance(val, float): return "f32"
        if isinstance(val, bool): return "bool"
        if isinstance(val, str): return "str"
        if isinstance(val, list): return "array"
        return "i32"


def run_source(source: str) -> int:
    from vyn.gui_runtime import reset_gui
    from vyn.stdlib_runtime import reset_http_server
    from vyn.prelude import inject_prelude
    reset_gui()
    reset_http_server()
    source = inject_prelude(source)
    program = Parser(source).parse()
    sem = SemanticAnalyzer()
    sem.analyze(program)
    return Interpreter(program).run()
