"""Interpréteur Vyn — exécution directe sans LLVM."""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from vyn.ast.nodes import *
from vyn.parser import Parser
from vyn.semantic import SemanticAnalyzer


class _BreakLoop(Exception):
    pass


class _ContinueLoop(Exception):
    pass


@dataclass
class VynValue:
    data: Any
    vtype: str
    is_mut: bool = False


class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.globals: Dict[str, Any] = {}
        self.scopes: List[Dict[str, VynValue]] = [self._builtin_scope()]
        self.structs: Dict[str, StructDecl] = {s.name: s for s in program.structs}
        self.functions: Dict[str, FunctionDecl] = {}
        self.impl_methods: Dict[str, FunctionDecl] = {}
        for fn in program.functions:
            self.functions[fn.name] = fn
        for impl in program.impls:
            for m in impl.methods:
                self.impl_methods[f"{impl.struct_name}.{m.name}"] = m
                self.impl_methods[f"{impl.struct_name}_{m.name}"] = m

    def _builtin_scope(self) -> Dict[str, VynValue]:
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

    def _set(self, name: str, val: Any, vtype: str, is_mut: bool):
        self.scopes[-1][name] = VynValue(val, vtype, is_mut)

    def _get(self, name: str) -> VynValue:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise RuntimeError(f"variable non définie: {name}")

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
        return self._call_method(fn, args, self_obj, struct_name)

    def _exec_stmt(self, stmt: Stmt, struct_name: Optional[str] = None):
        if isinstance(stmt, LetStmt):
            val = self._eval(stmt.value) if stmt.value else 0
            if stmt.type:
                vtype = stmt.type.name
            elif isinstance(stmt.value, StructInit):
                vtype = stmt.value.struct_name
            elif isinstance(stmt.value, ArrayLiteral):
                vtype = "array"
            else:
                vtype = self._infer_type(val)
            self._set(stmt.name, val, vtype, stmt.is_mut)
        elif isinstance(stmt, AssignStmt):
            val = self._eval(stmt.value)
            if isinstance(stmt.target, Identifier):
                v = self._get(stmt.target.name)
                if not v.is_mut:
                    raise RuntimeError(f"assignation à immutable: {stmt.target.name}")
                v.data = val
            elif isinstance(stmt.target, MemberAccess) and isinstance(stmt.target.object, Identifier):
                if stmt.target.object.name == "self" and struct_name:
                    self_obj = self._get("self").data
                    self_obj[stmt.target.member] = val
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
            if name in self.functions:
                return self._call_fn(self.functions[name], args)
            if name == "raw_hardware_call":
                return args[0] * 2
        return 0

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
