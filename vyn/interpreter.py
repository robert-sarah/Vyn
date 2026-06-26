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

    def _exec_stmt(self, stmt, struct_name=None):
        # ── Import new AST nodes lazily to avoid circular imports ─────────────
        from vyn.ast.nodes import (
            LetTupleStmt, WhileStmt, ForStmt, IfLetStmt, LocalFnStmt,
            IndexExpr, TupleExpr, TupleIndex, MapLiteral,
            SomeExpr, NoneExpr, OkExpr, ErrExpr, CharLiteral, NilLiteral,
            RangeExpr, CastExpr, QuestionExpr, ClosureExpr, IfExpr,
            MatchArm, WildcardPattern, LiteralPattern, IdentPattern,
            EnumPattern, TuplePattern, OrPattern, RangePattern, StructPattern,
        )

        if isinstance(stmt, LetStmt):
            val = self._eval(stmt.value) if stmt.value else 0
            if stmt.type:
                vtype = stmt.type.name
                is_own = getattr(stmt.type, 'is_own', False)
                is_ref = getattr(stmt.type, 'is_ref', False)
            elif stmt.value is not None and hasattr(stmt.value, 'struct_name'):
                vtype = stmt.value.struct_name
                is_own, is_ref = False, False
            elif stmt.value is not None and isinstance(stmt.value, ArrayLiteral):
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

        elif isinstance(stmt, LetTupleStmt):
            # let (a, b, c) = tuple_expr;
            val = self._eval(stmt.value)
            if isinstance(val, (list, tuple)):
                for i, name in enumerate(stmt.names):
                    v = val[i] if i < len(val) else 0
                    self._set(name, v, self._infer_type(v), stmt.is_mut)
            elif isinstance(val, dict) and "__values__" in val:
                for i, name in enumerate(stmt.names):
                    v = val["__values__"][i] if i < len(val["__values__"]) else 0
                    self._set(name, v, self._infer_type(v), stmt.is_mut)
            else:
                for name in stmt.names:
                    self._set(name, val, self._infer_type(val), stmt.is_mut)

        elif isinstance(stmt, AssignStmt):
            # compute new value considering compound ops
            if stmt.op != "=" and stmt.op:
                op = stmt.op[:-1]  # "+=" → "+"
                old_val = self._eval(stmt.target)
                rhs = self._eval(stmt.value)
                val = self._apply_op(op, old_val, rhs)
            else:
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
            elif isinstance(stmt.target, IndexExpr):
                arr = self._eval(stmt.target.object)
                idx = int(self._eval(stmt.target.index))
                if isinstance(arr, list):
                    while len(arr) <= idx:
                        arr.append(0)
                    arr[idx] = val
                elif isinstance(arr, dict):
                    arr[idx] = val
                else:
                    raise RuntimeError("indexation sur non-tableau")
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
                if (isinstance(stmt.target.object, Identifier)
                        and stmt.target.object.name == "self" and struct_name):
                    self_obj = self._get("self").data
                    if isinstance(self_obj, dict):
                        self_obj[stmt.target.member] = val
                else:
                    obj = self._eval(stmt.target.object)
                    if isinstance(obj, dict):
                        obj[stmt.target.member] = val
                    else:
                        raise RuntimeError(f"assignation membre impossible: {stmt.target.member}")
            elif isinstance(stmt.target, TupleIndex):
                tup = self._eval(stmt.target.object)
                if isinstance(tup, list):
                    while len(tup) <= stmt.target.index:
                        tup.append(0)
                    tup[stmt.target.index] = val

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

        elif isinstance(stmt, IfLetStmt):
            # if let Some(x) = expr { … }
            val = self._eval(stmt.value)
            bound = self._exec_pattern_bind(stmt.pattern, val)
            if bound is not None:
                self._push()
                for name, bval in bound.items():
                    self._set(name, bval, self._infer_type(bval), False)
                for s in stmt.then_body:
                    r = self._exec_stmt(s, struct_name)
                    if r and r[0] == "return":
                        self._pop()
                        return r
                self._pop()
            elif stmt.else_body:
                for s in stmt.else_body:
                    r = self._exec_stmt(s, struct_name)
                    if r and r[0] == "return":
                        return r

        elif isinstance(stmt, WhileStmt):
            try:
                while self._truthy(self._eval(stmt.condition)):
                    try:
                        for s in stmt.body:
                            r = self._exec_stmt(s, struct_name)
                            if r and r[0] == "return":
                                return r
                    except _ContinueLoop:
                        continue
            except _BreakLoop:
                pass

        elif isinstance(stmt, ForStmt):
            iterable = self._eval(stmt.iterable)
            # Range object
            if isinstance(iterable, dict) and iterable.get("__type__") == "Range":
                start = iterable["__start__"]
                end   = iterable["__end__"]
                inc   = iterable.get("__inclusive__", False)
                rng   = range(start, end + (1 if inc else 0))
                items = list(rng)
            elif isinstance(iterable, range):
                items = list(iterable)
            elif isinstance(iterable, (list, tuple)):
                items = list(iterable)
            elif isinstance(iterable, str):
                items = list(iterable)
            else:
                items = []
            try:
                for item in items:
                    self._push()
                    self._set(stmt.var, item, self._infer_type(item), False)
                    try:
                        for s in stmt.body:
                            r = self._exec_stmt(s, struct_name)
                            if r and r[0] == "return":
                                self._pop()
                                return r
                    except _ContinueLoop:
                        pass
                    finally:
                        self._pop()
            except _BreakLoop:
                pass

        elif isinstance(stmt, LoopStmt):
            if stmt.iterator:
                var, it = stmt.iterator
                arr = self._eval(it)
                if isinstance(arr, dict) and arr.get("__type__") == "Range":
                    start = arr["__start__"]
                    end   = arr["__end__"]
                    inc   = arr.get("__inclusive__", False)
                    arr = list(range(start, end + (1 if inc else 0)))
                if isinstance(arr, list):
                    try:
                        for item in arr:
                            self._set(var, item, self._infer_type(item), False)
                            try:
                                for s in stmt.body:
                                    r = self._exec_stmt(s, struct_name)
                                    if r and r[0] == "return":
                                        return r
                            except _ContinueLoop:
                                continue
                    except _BreakLoop:
                        pass
                elif isinstance(arr, str):
                    try:
                        for ch in arr:
                            self._set(var, ch, "char", False)
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

            # Prefer new MatchArm (from new parser)
            arms = getattr(stmt, 'arms', [])
            if arms:
                for arm in arms:
                    # Check guard
                    if arm.guard and not self._truthy(self._eval(arm.guard)):
                        continue
                    bound = self._exec_pattern_bind(arm.pattern, val)
                    if bound is not None:
                        matched = True
                        self._push()
                        for bname, bval in bound.items():
                            self._set(bname, bval, self._infer_type(bval), False)
                        for s in arm.body:
                            r = self._exec_stmt(s, struct_name)
                            if r and r[0] == "return":
                                self._pop()
                                return r
                        self._pop()
                        break
            else:
                # Legacy MatchCase
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
            finally:
                if hasattr(stmt, 'finally_body') and stmt.finally_body:
                    for s in stmt.finally_body:
                        self._exec_stmt(s, struct_name)

        elif isinstance(stmt, ThrowStmt):
            raise RuntimeError(str(self._eval(stmt.value)))

        elif isinstance(stmt, LocalFnStmt):
            fn = stmt.decl
            self.functions[fn.name] = fn
            self._set(fn.name, fn, "fn", False)

        elif isinstance(stmt, ExprStmt):
            self._eval(stmt.expr)

    def _eval(self, expr) -> Any:
        if expr is None:
            return 0

        # ── Import new AST nodes lazily ───────────────────────────────────────
        from vyn.ast.nodes import (
            IndexExpr, TupleExpr, TupleIndex, MapLiteral,
            SomeExpr, NoneExpr, OkExpr, ErrExpr, CharLiteral, NilLiteral,
            RangeExpr, CastExpr, QuestionExpr, ClosureExpr, IfExpr,
            LetTupleStmt, WhileStmt, ForStmt, IfLetStmt, LocalFnStmt,
        )

        if isinstance(expr, IntLiteral):
            return expr.value
        if isinstance(expr, FloatLiteral):
            return expr.value
        if isinstance(expr, BoolLiteral):
            return expr.value
        if isinstance(expr, StringLiteral):
            return expr.value
        if isinstance(expr, CharLiteral):
            return expr.value
        if isinstance(expr, NilLiteral):
            return None
        if isinstance(expr, NoneExpr):
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if isinstance(expr, SomeExpr):
            inner = self._eval(expr.value)
            return {"__type__": "Option", "__tag__": "Some", "__value__": inner}
        if isinstance(expr, OkExpr):
            inner = self._eval(expr.value)
            return {"__type__": "Result", "__tag__": "Ok", "__value__": inner}
        if isinstance(expr, ErrExpr):
            inner = self._eval(expr.value)
            return {"__type__": "Result", "__tag__": "Err", "__value__": inner}

        if isinstance(expr, Identifier):
            # Check globals first (consts, mod consts)
            if expr.name in self.globals:
                return self.globals[expr.name].data
            # None / nil literal
            if expr.name in ("None", "nil"):
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
            return self._get(expr.name).data

        if isinstance(expr, BinaryOp):
            l = self._eval(expr.left)
            r = self._eval(expr.right)
            return self._apply_op(expr.op, l, r)

        if isinstance(expr, UnaryOp):
            o = self._eval(expr.operand)
            if expr.op == "-":  return -o
            if expr.op in ("!", "not"): return not self._truthy(o)
            if expr.op == "~":  return ~int(o) if isinstance(o, (int, float)) else o
            if expr.op == "&":  return o   # runtime: ref is same value
            if expr.op == "&mut": return o
            if expr.op == "*":  return o   # deref: same value in interpreter
            return o

        if isinstance(expr, CastExpr):
            val = self._eval(expr.expr)
            tname = expr.to.name
            try:
                if tname in ("i8","i16","i32","i64","u8","u16","u32","u64","usize","isize"):
                    return int(val)
                if tname in ("f32","f64"):
                    return float(val)
                if tname == "bool":
                    return bool(val)
                if tname in ("str",):
                    return str(val)
                if tname == "char":
                    return chr(int(val)) if isinstance(val, (int, float)) else str(val)
            except Exception:
                pass
            return val

        if isinstance(expr, RangeExpr):
            start = self._eval(expr.start)
            end   = self._eval(expr.end)
            return {
                "__type__": "Range",
                "__start__": int(start),
                "__end__": int(end),
                "__inclusive__": expr.inclusive,
            }

        if isinstance(expr, QuestionExpr):
            val = self._eval(expr.expr)
            if isinstance(val, dict):
                tag = val.get("__tag__") or val.get("__variant__")
                if tag in ("None", "Err"):
                    raise RuntimeError(str(val.get("__value__", "error propagation")))
                return val.get("__value__", val)
            return val

        if isinstance(expr, TupleExpr):
            return {"__type__": "Tuple", "__values__": [self._eval(e) for e in expr.elements]}

        if isinstance(expr, TupleIndex):
            tup = self._eval(expr.object)
            if isinstance(tup, dict) and "__values__" in tup:
                vals = tup["__values__"]
                return vals[expr.index] if expr.index < len(vals) else 0
            if isinstance(tup, (list, tuple)):
                return tup[expr.index] if expr.index < len(tup) else 0
            return 0

        if isinstance(expr, MapLiteral):
            result = {}
            for k, v in expr.entries:
                result[self._eval(k)] = self._eval(v)
            return result

        if isinstance(expr, IfExpr):
            cond = self._eval(expr.condition)
            if self._truthy(cond):
                return self._eval(expr.then_expr)
            return self._eval(expr.else_expr)

        if isinstance(expr, ClosureExpr):
            # Capture current scope
            captured = {}
            for scope in self.scopes:
                for k, v in scope.items():
                    captured[k] = v
            return {
                "__type__": "Closure",
                "__params__": expr.params,
                "__body__":   expr.body,
                "__expr__":   expr.expr,
                "__captured__": captured,
                "__interp__": self,
            }

        if isinstance(expr, IndexExpr):
            obj = self._eval(expr.object)
            idx = self._eval(expr.index)
            if isinstance(obj, list):
                i = int(idx)
                if 0 <= i < len(obj):
                    return obj[i]
                raise RuntimeError(f"index {i} hors des limites ({len(obj)})")
            if isinstance(obj, dict):
                return obj.get(idx, 0)
            if isinstance(obj, str):
                i = int(idx)
                if 0 <= i < len(obj):
                    return obj[i]
                raise RuntimeError(f"index {i} hors des limites ({len(obj)})")
            raise RuntimeError(f"indexation sur type non indexable: {type(obj)}")

        if isinstance(expr, CallExpr):
            return self._call(expr)

        if isinstance(expr, MemberAccess):
            # Module global const (mod.CONST)
            if isinstance(expr.object, Identifier):
                mod_name = expr.object.name
                key = f"{mod_name}.{expr.member}"
                if key in self.globals:
                    return self.globals[key].data
                # Enum variant access
                if mod_name in self.enums:
                    vname = expr.member
                    idx   = self.enums[mod_name].get(vname, 0)
                    meta  = self.enum_meta.get(mod_name)
                    if meta:
                        variant = meta.variants[idx]
                        if variant.payload:
                            return {"__enum__": mod_name, "__variant__": vname,
                                    "__index__": idx, "__value__": None}
                    return idx
                if mod_name == "self":
                    selfdata = self._get("self").data
                    if isinstance(selfdata, dict):
                        return selfdata.get(expr.member)
                    return 0
            obj = self._eval(expr.object)
            if isinstance(obj, dict):
                # Tuple field via member name? (legacy)
                if "__values__" in obj:
                    try:
                        idx = int(expr.member)
                        vals = obj["__values__"]
                        return vals[idx] if idx < len(vals) else 0
                    except ValueError:
                        pass
                return obj.get(expr.member, 0)
            if isinstance(obj, list) and expr.member == "len":
                return len(obj)
            if isinstance(obj, str) and expr.member == "len":
                return len(obj)
            return 0

        if isinstance(expr, StructInit):
            return {k: self._eval(v) for k, v in expr.fields.items()}

        if isinstance(expr, ArrayLiteral):
            if expr.repeat:
                elem, count = expr.repeat
                v = self._eval(elem)
                return [v] * count
            return [self._eval(e) for e in expr.elements]

        return 0

    def _call(self, expr) -> Any:
        from vyn.stdlib_runtime import dispatch, _MISSING
        from vyn.ast.nodes import IndexExpr, ClosureExpr

        # ── Appel de méthode obj.method(args) ────────────────────────────────
        if isinstance(expr.callee, MemberAccess) and isinstance(expr.callee.object, Identifier):
            mod, method = expr.callee.object.name, expr.callee.member
            args = [self._eval(a) for a in expr.args]
            qual = f"{mod}.{method}"

            # Option/Result methods
            if mod in self.scopes[-1] or any(mod in s for s in self.scopes):
                try:
                    obj_val = self._get(mod).data
                    if isinstance(obj_val, dict):
                        tag = obj_val.get("__type__")
                        if tag == "Option":
                            return self._call_option_method(obj_val, method, args)
                        if tag == "Result":
                            return self._call_result_method(obj_val, method, args)
                        # Struct method call
                        stype = self._get(mod).vtype
                        for mk in (f"{stype}.{method}", f"{stype}_{method}"):
                            if mk in self.impl_methods:
                                return self._call_fn(self.impl_methods[mk], args, obj_val, stype)
                except RuntimeError:
                    pass

            # User-defined function (qual or mod.method)
            if qual in self.functions:
                return self._call_fn(self.functions[qual], args)
            if mod in self.modules and method in {f.name for f in self.modules[mod].functions}:
                if qual in self.functions:
                    return self._call_fn(self.functions[qual], args)

            # Stdlib dispatch
            result = dispatch(mod, method, args, self)
            if result is not _MISSING:
                return result

            # Fallback builtins
            if mod == "io":
                if method in ("print", "println"):
                    v = args[0] if args else ""
                    if isinstance(v, (int, float)) and float(v) == int(v):
                        v = int(v)
                    print(v)
                    return 0
                if method in ("print_int", "print_i32"):
                    print(int(args[0]) if args else 0); return 0
                if method == "readln":
                    return input()
                if method == "read_int":
                    return int(input())
            if mod == "sys" and method == "sleep":
                time.sleep((args[0] if args else 0) / 1000.0); return 0
            if mod == "sys" and method == "exit":
                sys.exit(int(args[0]) if args else 0)
            if mod == "log" and method in ("info", "error", "warn", "debug"):
                level = method.upper()
                out = sys.stderr if method == "error" else sys.stdout
                print(f"[{level}] {args[0] if args else ''}", file=out)
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
                    g.alert(str(args[0]) if args else ""); return 0

            # Struct instance method call
            try:
                v = self._get(mod)
                stype = v.vtype
                for mk in (f"{stype}.{method}", f"{stype}_{method}"):
                    if mk in self.impl_methods:
                        return self._call_fn(self.impl_methods[mk], args, v.data, stype)
            except RuntimeError:
                pass

        # ── Appel de méthode sur expression non-Identifier ────────────────────
        elif isinstance(expr.callee, MemberAccess):
            obj  = self._eval(expr.callee.object)
            method = expr.callee.member
            args = [self._eval(a) for a in expr.args]
            if isinstance(obj, dict):
                tag = obj.get("__type__")
                if tag == "Option":
                    return self._call_option_method(obj, method, args)
                if tag == "Result":
                    return self._call_result_method(obj, method, args)
                stype = obj.get("__struct__", "")
                for mk in (f"{stype}.{method}", f"{stype}_{method}"):
                    if mk in self.impl_methods:
                        return self._call_fn(self.impl_methods[mk], args, obj, stype)
            if isinstance(obj, list):
                return self._call_list_method(obj, method, args)
            if isinstance(obj, str):
                return self._call_str_method(obj, method, args)

        # ── Appel direct name(args) ───────────────────────────────────────────
        elif isinstance(expr.callee, Identifier):
            name = expr.callee.name
            args = [self._eval(a) for a in expr.args]

            # Option/Result constructors
            if name == "Some":
                inner = args[0] if args else None
                return {"__type__": "Option", "__tag__": "Some", "__value__": inner}
            if name == "None":
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
            if name == "Ok":
                inner = args[0] if args else None
                return {"__type__": "Result", "__tag__": "Ok", "__value__": inner}
            if name == "Err":
                inner = args[0] if args else None
                return {"__type__": "Result", "__tag__": "Err", "__value__": inner}

            # Enum variants
            for ename, variants in self.enums.items():
                if name in variants:
                    payload = args[0] if args else None
                    idx     = variants[name]
                    variant = self.enum_meta[ename].variants[idx]
                    if variant.payload:
                        return {
                            "__enum__": ename, "__variant__": name,
                            "__index__": idx, "__value__": payload,
                        }
                    return idx

            # User functions
            if name in self.functions:
                return self._call_fn(self.functions[name], args)

            # Closure variable
            try:
                cv = self._get(name).data
                if isinstance(cv, dict) and cv.get("__type__") == "Closure":
                    return self._call_closure(cv, args)
            except RuntimeError:
                pass

            if name == "raw_hardware_call":
                return args[0] * 2

        # ── Appel d'une closure directement ──────────────────────────────────
        else:
            callee_val = self._eval(expr.callee)
            args       = [self._eval(a) for a in expr.args]
            if isinstance(callee_val, dict) and callee_val.get("__type__") == "Closure":
                return self._call_closure(callee_val, args)

        return 0

    # ── Appel de closure ──────────────────────────────────────────────────────

    def _call_closure(self, cv: dict, args: list) -> Any:
        interp = cv.get("__interp__", self)
        params = cv.get("__params__", [])
        body   = cv.get("__body__")
        expr   = cv.get("__expr__")
        captured = cv.get("__captured__", {})

        old_scopes = interp.scopes
        interp.scopes = [captured.copy(), {}]

        for p, a in zip(params, args):
            name = p.name if hasattr(p, 'name') else str(p)
            interp._set(name, a, interp._infer_type(a), getattr(p, 'is_mut', False))

        result = 0
        if body:
            for s in body:
                r = interp._exec_stmt(s)
                if r and r[0] == "return":
                    result = r[1]
                    break
        elif expr is not None:
            result = interp._eval(expr)

        interp.scopes = old_scopes
        return result

    # ── Méthodes builtin sur Option ───────────────────────────────────────────

    def _call_option_method(self, opt: dict, method: str, args: list) -> Any:
        tag   = opt.get("__tag__", "None")
        inner = opt.get("__value__")
        if method == "is_some":  return tag == "Some"
        if method == "is_none":  return tag == "None"
        if method == "unwrap":
            if tag == "None":
                raise RuntimeError("unwrap() sur None")
            return inner
        if method == "unwrap_or":
            return inner if tag == "Some" else (args[0] if args else 0)
        if method == "expect":
            if tag == "None":
                raise RuntimeError(str(args[0]) if args else "expect() sur None")
            return inner
        if method == "map":
            if tag == "None":
                return opt
            if args and isinstance(args[0], dict) and args[0].get("__type__") == "Closure":
                mapped = self._call_closure(args[0], [inner])
                return {"__type__": "Option", "__tag__": "Some", "__value__": mapped}
            return opt
        if method == "or_else":
            return opt if tag == "Some" else (args[0] if args else opt)
        return 0

    # ── Méthodes builtin sur Result ───────────────────────────────────────────

    def _call_result_method(self, res: dict, method: str, args: list) -> Any:
        tag   = res.get("__tag__", "Err")
        inner = res.get("__value__")
        if method == "is_ok":    return tag == "Ok"
        if method == "is_err":   return tag == "Err"
        if method == "unwrap":
            if tag == "Err":
                raise RuntimeError(f"unwrap() sur Err({inner})")
            return inner
        if method == "unwrap_or":
            return inner if tag == "Ok" else (args[0] if args else 0)
        if method == "unwrap_err":
            return inner if tag == "Err" else None
        if method == "ok":
            if tag == "Ok":
                return {"__type__": "Option", "__tag__": "Some", "__value__": inner}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        return 0

    # ── Méthodes builtin sur list ─────────────────────────────────────────────

    def _call_list_method(self, lst: list, method: str, args: list) -> Any:
        if method == "len":      return len(lst)
        if method == "push":     lst.append(args[0] if args else 0); return 0
        if method == "pop":
            if lst:
                v = lst.pop()
                return {"__type__": "Option", "__tag__": "Some", "__value__": v}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "get":
            idx = int(args[0]) if args else 0
            if 0 <= idx < len(lst):
                return {"__type__": "Option", "__tag__": "Some", "__value__": lst[idx]}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "set":
            if args and len(args) >= 2:
                idx = int(args[0])
                while len(lst) <= idx:
                    lst.append(0)
                lst[idx] = args[1]
            return 0
        if method == "remove":
            idx = int(args[0]) if args else 0
            if 0 <= idx < len(lst):
                return lst.pop(idx)
            return 0
        if method == "clear":    lst.clear(); return 0
        if method == "sort":     lst.sort(key=lambda x: (str(type(x)), x) if not isinstance(x, (int, float, str)) else x); return 0
        if method == "reverse":  lst.reverse(); return 0
        if method == "contains": return args[0] in lst if args else False
        if method == "is_empty": return len(lst) == 0
        if method == "first":
            if lst:
                return {"__type__": "Option", "__tag__": "Some", "__value__": lst[0]}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "last":
            if lst:
                return {"__type__": "Option", "__tag__": "Some", "__value__": lst[-1]}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "join":
            sep = str(args[0]) if args else ""
            return sep.join(str(x) for x in lst)
        if method == "map":
            if args and isinstance(args[0], dict) and args[0].get("__type__") == "Closure":
                return [self._call_closure(args[0], [x]) for x in lst]
            return lst
        if method == "filter":
            if args and isinstance(args[0], dict) and args[0].get("__type__") == "Closure":
                return [x for x in lst if self._truthy(self._call_closure(args[0], [x]))]
            return lst
        if method == "any":
            if args and isinstance(args[0], dict) and args[0].get("__type__") == "Closure":
                return any(self._truthy(self._call_closure(args[0], [x])) for x in lst)
            return False
        if method == "all":
            if args and isinstance(args[0], dict) and args[0].get("__type__") == "Closure":
                return all(self._truthy(self._call_closure(args[0], [x])) for x in lst)
            return True
        if method == "count":    return len(lst)
        if method == "sum":      return sum(lst) if lst else 0
        return 0

    # ── Méthodes builtin sur str ──────────────────────────────────────────────

    def _call_str_method(self, s: str, method: str, args: list) -> Any:
        if method == "len":           return len(s)
        if method == "upper":         return s.upper()
        if method == "lower":         return s.lower()
        if method == "trim":          return s.strip()
        if method == "trim_start":    return s.lstrip()
        if method == "trim_end":      return s.rstrip()
        if method == "contains":      return (args[0] in s) if args else False
        if method == "starts_with":   return s.startswith(args[0]) if args else False
        if method == "ends_with":     return s.endswith(args[0]) if args else False
        if method == "replace":
            if len(args) >= 2:
                return s.replace(str(args[0]), str(args[1]))
            return s
        if method == "split":
            sep = str(args[0]) if args else " "
            return s.split(sep)
        if method == "chars":         return list(s)
        if method == "is_empty":      return len(s) == 0
        if method == "parse_int":
            try: return int(s)
            except: return 0
        if method == "parse_f32":
            try: return float(s)
            except: return 0.0
        if method == "repeat":
            n = int(args[0]) if args else 1
            return s * n
        if method == "index":
            idx = int(args[0]) if args else 0
            return s[idx] if 0 <= idx < len(s) else ""
        return s

    # ── Opérateur binaire ─────────────────────────────────────────────────────

    def _apply_op(self, op: str, l: Any, r: Any) -> Any:
        try:
            if op == "+":
                if isinstance(l, str) or isinstance(r, str):
                    return str(l) + str(r)
                return l + r
            if op == "-": return l - r
            if op == "*": return l * r
            if op == "/":
                if r == 0:
                    return 0
                return l / r
            if op == "%": return l % r if r else 0
            if op == "==": return l == r
            if op == "!=": return l != r
            if op == "<":  return l < r
            if op == ">":  return l > r
            if op == "<=": return l <= r
            if op == ">=": return l >= r
            if op in ("||", "or"):  return self._truthy(l) or self._truthy(r)
            if op in ("&&", "and"): return self._truthy(l) and self._truthy(r)
            if op == "&":  return int(l) & int(r)
            if op == "|":  return int(l) | int(r)
            if op == "^":  return int(l) ^ int(r)
            if op == "<<": return int(l) << int(r)
            if op == ">>": return int(l) >> int(r)
            if op == "[]":
                if isinstance(l, list): return l[int(r)]
                if isinstance(l, dict): return l.get(r, 0)
                if isinstance(l, str):  return l[int(r)]
        except Exception:
            pass
        return 0

    def _find_binding(self, name: str) -> Optional[OwnedValue]:
        if name in self.globals:
            return self.globals[name]
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _match_enum_pattern(self, val: Any, enum_name: str, variant_name: str) -> bool:
        if isinstance(val, dict):
            if val.get("__enum__") == enum_name and val.get("__variant__") == variant_name:
                return True
            # Also match Option/Result tags
            tag = val.get("__tag__") or val.get("__variant__")
            if tag == variant_name:
                return True
        if isinstance(val, int) and enum_name in self.enums:
            return self.enums[enum_name].get(variant_name) == val
        return False

    def _exec_pattern_bind(self, pattern, val: Any) -> Optional[dict]:
        """Match a pattern against val. Returns dict of bindings if matched, None if not."""
        from vyn.ast.nodes import (
            WildcardPattern, LiteralPattern, IdentPattern,
            EnumPattern, TuplePattern, OrPattern, RangePattern, StructPattern,
        )

        if isinstance(pattern, WildcardPattern):
            return {}  # always matches, no bindings

        if isinstance(pattern, IdentPattern):
            # lowercase ident = capture variable
            return {pattern.name: val}

        if isinstance(pattern, LiteralPattern):
            lit_val = self._eval(pattern.value)
            if lit_val == val:
                return {}
            return None

        if isinstance(pattern, EnumPattern):
            # None
            if pattern.variant_name == "None":
                if isinstance(val, dict) and val.get("__tag__") == "None":
                    return {}
                if val is None:
                    return {}
                return None
            # Some(x)
            if pattern.variant_name == "Some":
                if isinstance(val, dict) and val.get("__tag__") == "Some":
                    inner = val.get("__value__")
                    if pattern.payload:
                        return self._exec_pattern_bind(pattern.payload, inner)
                    return {}
                return None
            # Ok(x) / Err(x)
            if pattern.variant_name in ("Ok", "Err"):
                if isinstance(val, dict) and val.get("__tag__") == pattern.variant_name:
                    inner = val.get("__value__")
                    if pattern.payload:
                        return self._exec_pattern_bind(pattern.payload, inner)
                    return {}
                return None
            # Regular enum variant
            ename = pattern.enum_name
            vname = pattern.variant_name
            if isinstance(val, dict) and val.get("__enum__") == ename and val.get("__variant__") == vname:
                if pattern.payload:
                    inner = val.get("__value__")
                    return self._exec_pattern_bind(pattern.payload, inner)
                return {}
            if isinstance(val, int) and ename in self.enums:
                if self.enums[ename].get(vname) == val:
                    return {}
            # Try by variant name only (enum_name may be empty or wrong)
            if isinstance(val, dict):
                tag = val.get("__variant__") or val.get("__tag__")
                if tag == vname:
                    if pattern.payload:
                        inner = val.get("__value__")
                        return self._exec_pattern_bind(pattern.payload, inner)
                    return {}
            if isinstance(val, int):
                for en, variants in self.enums.items():
                    if variants.get(vname) == val:
                        return {}
            return None

        if isinstance(pattern, TuplePattern):
            if isinstance(val, dict) and "__values__" in val:
                vals = val["__values__"]
            elif isinstance(val, (list, tuple)):
                vals = list(val)
            else:
                return None
            if len(vals) != len(pattern.elements):
                return None
            bindings = {}
            for p, v in zip(pattern.elements, vals):
                b = self._exec_pattern_bind(p, v)
                if b is None:
                    return None
                bindings.update(b)
            return bindings

        if isinstance(pattern, OrPattern):
            for p in pattern.patterns:
                b = self._exec_pattern_bind(p, val)
                if b is not None:
                    return b
            return None

        if isinstance(pattern, RangePattern):
            start = self._eval(pattern.start)
            end   = self._eval(pattern.end)
            if pattern.inclusive:
                if start <= val <= end:
                    return {}
            else:
                if start <= val < end:
                    return {}
            return None

        if isinstance(pattern, StructPattern):
            if not isinstance(val, dict):
                return None
            bindings = {}
            for fname, fpat in pattern.fields.items():
                fval = val.get(fname)
                b = self._exec_pattern_bind(fpat, fval)
                if b is None:
                    return None
                bindings.update(b)
            return bindings

        # Fallback: treat as wildcard
        return {}

    def _truthy(self, v) -> bool:
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return len(v) > 0
        if isinstance(v, list):
            return len(v) > 0
        if isinstance(v, dict):
            tag = v.get("__tag__") or v.get("__type__")
            if tag == "None":
                return False
        return bool(v)

    def _infer_type(self, val) -> str:
        if isinstance(val, bool):   return "bool"
        if isinstance(val, float):  return "f32"
        if isinstance(val, int):    return "i32"
        if isinstance(val, str):    return "str"
        if isinstance(val, list):   return "array"
        if isinstance(val, dict):
            t = val.get("__type__")
            if t == "Option":  return "option"
            if t == "Result":  return "result"
            if t == "Tuple":   return "tuple"
            if t == "Range":   return "range"
            if t == "Closure": return "closure"
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
