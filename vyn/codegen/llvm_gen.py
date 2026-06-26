"""Génération LLVM IR pour Vyn."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from llvmlite import ir, binding

from vyn.ast.nodes import *
from vyn.semantic import SemanticAnalyzer


@dataclass
class CodegenError(Exception):
    message: str

    def __str__(self) -> str:
        return f"[Codegen] {self.message}"


class LLVMGenerator:
    TYPE_MAP = {
        "void": ir.VoidType(),
        "i32": ir.IntType(32),
        "f32": ir.FloatType(),
        "bool": ir.IntType(1),
        "str": ir.PointerType(ir.IntType(8)),
    }

    def __init__(self, program: Program, semantic: SemanticAnalyzer):
        self.program = program
        self.semantic = semantic
        self.module = ir.Module(name="vyn_module")
        self.builder: Optional[ir.IRBuilder] = None
        self.local_vars: Dict[str, ir.AllocaInstr] = {}
        self.local_types: Dict[str, str] = {}
        self.local_mut: Dict[str, bool] = {}
        self.functions: Dict[str, ir.Function] = {}
        self.struct_types: Dict[str, ir.LiteralStructType] = {}
        self.current_fn: Optional[FunctionDecl] = None
        self.string_literals: List[str] = []
        self.array_sizes: Dict[str, int] = {}
        self.loop_stack: List[tuple] = []
        self.enum_map: Dict[str, Dict[str, int]] = {}
        for e in getattr(program, "enums", []):
            self.enum_map[e.name] = {v.name: i for i, v in enumerate(e.variants)}
        for mod in getattr(program, "mods", []):
            for e in mod.enums:
                self.enum_map[e.name] = {v.name: i for i, v in enumerate(e.variants)}
        self._declare_runtime()

    def _declare_runtime(self) -> None:
        void = ir.VoidType()
        f32 = ir.FloatType()
        i32 = ir.IntType(32)
        i8p = ir.PointerType(ir.IntType(8))

        for name, args, ret in [
            ("vyn_io_print_f32", [f32], void),
            ("vyn_io_println_str", [i8p], void),
            ("vyn_sys_sleep_ms", [i32], void),
            ("vyn_profile_begin", [i8p], void),
            ("vyn_profile_end", [i8p, ir.DoubleType()], void),
        ]:
            fnty = ir.FunctionType(ret, args)
            if name not in self.module.globals:
                ir.Function(self.module, fnty, name=name)

        for ext in self.program.externs:
            args = [self._llvm_type(p.type.name) for p in ext.params]
            ret = self._llvm_type(ext.return_type.name)
            fnty = ir.FunctionType(ret, args)
            if ext.name not in self.module.globals:
                ir.Function(self.module, fnty, name=ext.name)

    def generate(self) -> str:
        for s in self.program.structs:
            self._gen_struct(s)
        for fn in self.program.functions:
            self._declare_function(fn)
        for impl in self.program.impls:
            for m in impl.methods:
                m_copy = FunctionDecl(
                    f"{impl.struct_name}_{m.name}",
                    [Param("self_ptr", TypeNode(impl.struct_name))] + [
                        p for p in m.params if p.name != "self"
                    ],
                    m.return_type,
                    m.body,
                    m.is_hot,
                    m.attributes,
                    m.visibility,
                )
                self._declare_function(m_copy, original=m)
        for fn in self.program.functions:
            self._gen_function(fn)
        for impl in self.program.impls:
            for m in impl.methods:
                m_copy = FunctionDecl(
                    f"{impl.struct_name}_{m.name}",
                    [Param("self_ptr", TypeNode(impl.struct_name))] + [
                        p for p in m.params if p.name != "self"
                    ],
                    m.return_type,
                    m.body,
                    m.is_hot,
                    m.attributes,
                    m.visibility,
                )
                self._gen_function(m_copy, struct_name=impl.struct_name, original=m)
        return str(self.module)

    def _gen_struct(self, s: StructDecl) -> None:
        fields = []
        for f in s.fields:
            fields.append(self._llvm_type(f.type.name))
        self.struct_types[s.name] = ir.LiteralStructType(fields)

    def _llvm_type(self, name: str, array_size: int = 500) -> ir.Type:
        if name == "Self":
            return ir.IntType(32)
        if name in self.TYPE_MAP:
            return self.TYPE_MAP[name]
        if name in self.struct_types:
            return self.struct_types[name]
        if name == "array":
            return ir.ArrayType(ir.FloatType(), array_size)
        return ir.IntType(32)

    def _declare_function(self, fn: FunctionDecl, original: Optional[FunctionDecl] = None) -> None:
        param_types = []
        for p in fn.params:
            sz = p.type.array_size or 500
            param_types.append(self._llvm_type(p.type.name, sz))
        ret_type = self._llvm_type(fn.return_type.name)
        fnty = ir.FunctionType(ret_type, param_types)
        func = ir.Function(self.module, fnty, name=fn.name)
        if fn.is_hot or fn.name == "main":
            func.linkage = "external"
        else:
            func.linkage = "internal"
        self.functions[fn.name] = func

    def _gen_function(
        self,
        fn: FunctionDecl,
        struct_name: Optional[str] = None,
        original: Optional[FunctionDecl] = None,
    ) -> None:
        self.current_fn = original or fn
        func = self.functions[fn.name]
        self.builder = ir.IRBuilder()
        entry = func.append_basic_block("entry")
        self.builder.position_at_end(entry)
        self.local_vars.clear()
        self.local_types.clear()
        self.local_mut.clear()

        profiled = any(a.name == "profile" for a in (original or fn).attributes)
        if profiled:
            name_ptr = self._const_str(fn.name)
            self.builder.call(
                self.module.get_global("vyn_profile_begin"),
                [name_ptr],
            )

        for i, p in enumerate(fn.params):
            sz = p.type.array_size or 500
            typ = self._llvm_type(p.type.name, sz)
            if p.type.name == "array":
                self.array_sizes[p.name] = sz
            alloca = self.builder.alloca(typ, name=p.name)
            self.builder.store(func.args[i], alloca)
            self.local_vars[p.name] = alloca
            self.local_types[p.name] = p.type.name
            self.local_mut[p.name] = p.is_mut

        for stmt in fn.body:
            self._gen_stmt(stmt, struct_name)

        if not self.builder.block.is_terminated:
            if fn.return_type.name == "void":
                self.builder.ret_void()
            elif fn.return_type.name == "i32":
                self.builder.ret(ir.Constant(ir.IntType(32), 0))
            else:
                self.builder.ret_void()

        if profiled:
            # instrumentation simplifiée — elapsed fixe pour démo
            name_ptr = self._const_str(fn.name)
            elapsed = ir.Constant(ir.DoubleType(), 0.0)
            end_block = func.append_basic_block("profile_end")
            self.builder.position_at_end(end_block)
            self.builder.call(
                self.module.get_global("vyn_profile_end"),
                [name_ptr, elapsed],
            )

    def _gen_stmt(self, stmt: Stmt, struct_name: Optional[str] = None) -> None:
        assert self.builder is not None
        if isinstance(stmt, LetStmt):
            val = self._gen_expr(stmt.value) if stmt.value else ir.Constant(ir.IntType(32), 0)
            arr_size = 500
            if stmt.type:
                typ_name = stmt.type.name
                if stmt.type.array_size:
                    arr_size = stmt.type.array_size
            elif isinstance(stmt.value, StructInit):
                typ_name = stmt.value.struct_name
            elif isinstance(stmt.value, ArrayLiteral):
                typ_name = "array"
                if stmt.value.repeat:
                    arr_size = stmt.value.repeat[1]
                    self.array_sizes[stmt.name] = arr_size
            else:
                typ_name = self._infer_llvm_type(val)
            if typ_name == "array":
                self.array_sizes[stmt.name] = arr_size
                if isinstance(stmt.value, ArrayLiteral):
                    alloca = self._gen_array_literal(stmt.value)
                    self.local_vars[stmt.name] = alloca
                    self.local_types[stmt.name] = typ_name
                    self.local_mut[stmt.name] = stmt.is_mut
                    return
            typ = self._llvm_type(typ_name, arr_size)
            alloca = self.builder.alloca(typ, name=stmt.name)
            if isinstance(val.type, ir.IntType) and typ == ir.FloatType():
                val = self.builder.sitofp(val, ir.FloatType())
            if isinstance(val.type, ir.PointerType) and isinstance(typ, ir.ArrayType):
                pass
            else:
                self.builder.store(val, alloca)
            self.local_vars[stmt.name] = alloca
            self.local_types[stmt.name] = typ_name
            self.local_mut[stmt.name] = stmt.is_mut
        elif isinstance(stmt, AssignStmt):
            val = self._gen_expr(stmt.value)
            if isinstance(stmt.target, Identifier):
                ptr = self.local_vars.get(stmt.target.name)
                if ptr:
                    self.builder.store(val, ptr)
            elif isinstance(stmt.target, BinaryOp) and stmt.target.op == "[]":
                arr_ptr = self.local_vars.get(self._expr_name(stmt.target.left))
                if arr_ptr:
                    idx = self._gen_expr(stmt.target.right)
                    elem_ptr = self.builder.gep(
                        arr_ptr,
                        [ir.Constant(ir.IntType(32), 0), idx],
                    )
                    self.builder.store(val, elem_ptr)
            elif isinstance(stmt.target, MemberAccess) and isinstance(stmt.target.object, Identifier):
                if stmt.target.object.name == "self" and struct_name:
                    self_ptr = self.local_vars.get("self_ptr")
                    if self_ptr:
                        struct_ty = self.struct_types[struct_name]
                        idx = self._field_index(struct_name, stmt.target.member)
                        field_ptr = self.builder.gep(
                            self.builder.load(self_ptr),
                            [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)],
                        )
                        self.builder.store(val, field_ptr)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self.builder.ret(self._gen_expr(stmt.value))
            else:
                self.builder.ret(ir.Constant(ir.IntType(32), 0))
        elif isinstance(stmt, IfStmt):
            self._gen_if(stmt)
        elif isinstance(stmt, LoopStmt):
            self._gen_loop(stmt, struct_name)
        elif isinstance(stmt, MatchStmt):
            self._gen_match(stmt, struct_name)
        elif isinstance(stmt, TryStmt):
            self._gen_try(stmt, struct_name)
        elif isinstance(stmt, ExprStmt):
            self._gen_expr(stmt.expr)
        elif isinstance(stmt, BreakStmt):
            if self.loop_stack:
                self.builder.branch(self.loop_stack[-1][0])
        elif isinstance(stmt, ContinueStmt):
            if self.loop_stack:
                self.builder.branch(self.loop_stack[-1][1])

    def _gen_if(self, stmt: IfStmt) -> None:
        assert self.builder is not None
        func = self.builder.basic_block.function
        cond = self._gen_expr(stmt.condition)
        if cond.type != ir.IntType(1):
            cond = self.builder.icmp_signed("!=", cond, ir.Constant(cond.type, 0))
        then_bb = func.append_basic_block("then")
        else_bb = func.append_basic_block("else") if stmt.else_body else None
        merge_bb = func.append_basic_block("merge")
        if else_bb:
            self.builder.cbranch(cond, then_bb, else_bb)
        else:
            self.builder.cbranch(cond, then_bb, merge_bb)
        self.builder.position_at_end(then_bb)
        for s in stmt.then_body:
            self._gen_stmt(s)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_bb)
        if else_bb and stmt.else_body:
            self.builder.position_at_end(else_bb)
            for s in stmt.else_body:
                self._gen_stmt(s)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)
        self.builder.position_at_end(merge_bb)

    def _expr_name(self, expr: Expr) -> str:
        if isinstance(expr, Identifier):
            return expr.name
        return ""

    def _gen_match(self, stmt: MatchStmt, struct_name: Optional[str] = None) -> None:
        assert self.builder is not None
        func = self.builder.basic_block.function
        val = self._gen_expr(stmt.expr)
        merge_bb = func.append_basic_block("match_merge")
        matched = False
        for case in stmt.cases:
            if case.pattern is None:
                if not matched:
                    next_bb = func.append_basic_block("match_default")
                    self.builder.branch(next_bb)
                    self.builder.position_at_end(next_bb)
                    for s in case.body:
                        self._gen_stmt(s, struct_name)
                    if not self.builder.block.is_terminated:
                        self.builder.branch(merge_bb)
                break
            test_bb = func.append_basic_block("match_case")
            cont_bb = func.append_basic_block("match_cont")
            if isinstance(case.pattern, MemberAccess) and isinstance(case.pattern.object, Identifier):
                ename = case.pattern.object.name
                vname = case.pattern.member
                idx = self.enum_map.get(ename, {}).get(vname, -1)
                if idx >= 0:
                    cond = self.builder.icmp_signed("==", val, ir.Constant(ir.IntType(32), idx))
                else:
                    cond = ir.Constant(ir.IntType(1), 0)
            else:
                pat = self._gen_expr(case.pattern)
                cond = self.builder.icmp_signed("==", val, pat)
            self.builder.cbranch(cond, test_bb, cont_bb)
            self.builder.position_at_end(test_bb)
            for s in case.body:
                self._gen_stmt(s, struct_name)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)
            self.builder.position_at_end(cont_bb)
            matched = True
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_bb)
        self.builder.position_at_end(merge_bb)

    def _gen_try(self, stmt: TryStmt, struct_name: Optional[str] = None) -> None:
        assert self.builder is not None
        for s in stmt.body:
            self._gen_stmt(s, struct_name)
        catch_bb = self.builder.basic_block.function.append_basic_block("catch_unused")
        self.builder.position_at_end(catch_bb)

    def _gen_loop(self, stmt: LoopStmt, struct_name: Optional[str] = None) -> None:
        assert self.builder is not None
        func = self.builder.basic_block.function
        cond_bb = func.append_basic_block("loop_cond")
        body_bb = func.append_basic_block("loop_body")
        exit_bb = func.append_basic_block("loop_exit")
        self.loop_stack.append((exit_bb, cond_bb))
        self.builder.branch(cond_bb)
        self.builder.position_at_end(cond_bb)

        if stmt.iterator:
            var_name, iterable = stmt.iterator
            if isinstance(iterable, Identifier) and iterable.name in self.local_vars:
                arr_ptr = self.local_vars[iterable.name]
                # boucle for simplifiée sur 500 éléments
                if "_loop_i" not in self.local_vars:
                    i_alloca = self.builder.alloca(ir.IntType(32), name="_loop_i")
                    self.builder.store(ir.Constant(ir.IntType(32), 0), i_alloca)
                    self.local_vars["_loop_i"] = i_alloca
                i_val = self.builder.load(self.local_vars["_loop_i"])
                cond = self.builder.icmp_signed("<", i_val, ir.Constant(ir.IntType(32), self.array_sizes.get(iterable.name if isinstance(iterable, Identifier) else "", 500)))
                self.builder.cbranch(cond, body_bb, exit_bb)
                self.builder.position_at_end(body_bb)
                idx = self.builder.load(self.local_vars["_loop_i"])
                elem_ptr = self.builder.gep(
                    self.builder.load(arr_ptr) if False else arr_ptr,
                    [ir.Constant(ir.IntType(32), 0), idx],
                )
                if var_name not in self.local_vars:
                    v_alloca = self.builder.alloca(ir.FloatType(), name=var_name)
                    self.local_vars[var_name] = v_alloca
                    self.local_types[var_name] = "f32"
                self.builder.store(self.builder.load(elem_ptr), self.local_vars[var_name])
                for s in stmt.body:
                    self._gen_stmt(s, struct_name)
                new_i = self.builder.add(i_val, ir.Constant(ir.IntType(32), 1))
                self.builder.store(new_i, self.local_vars["_loop_i"])
                self.builder.branch(cond_bb)
            else:
                self.builder.branch(body_bb)
                self.builder.position_at_end(body_bb)
                for s in stmt.body:
                    self._gen_stmt(s, struct_name)
                self.builder.branch(cond_bb)
        else:
            self.builder.branch(body_bb)
            self.builder.position_at_end(body_bb)
            for s in stmt.body:
                self._gen_stmt(s, struct_name)
            self.builder.branch(cond_bb)

        self.builder.position_at_end(exit_bb)
        self.loop_stack.pop()

    def _gen_expr(self, expr: Optional[Expr]) -> Any:
        assert self.builder is not None
        if expr is None:
            return ir.Constant(ir.IntType(32), 0)
        if isinstance(expr, IntLiteral):
            return ir.Constant(ir.IntType(32), expr.value)
        if isinstance(expr, FloatLiteral):
            return ir.Constant(ir.FloatType(), expr.value)
        if isinstance(expr, BoolLiteral):
            return ir.Constant(ir.IntType(1), int(expr.value))
        if isinstance(expr, StringLiteral):
            return self._const_str(expr.value)
        if isinstance(expr, Identifier):
            ptr = self.local_vars.get(expr.name)
            if ptr:
                val = self.builder.load(ptr)
                return val
            if expr.name in self.functions:
                return self.functions[expr.name]
            raise CodegenError(f"variable non définie: {expr.name}")
        if isinstance(expr, BinaryOp):
            l = self._gen_expr(expr.left)
            r = self._gen_expr(expr.right)
            if expr.op == "+":
                if l.type == ir.FloatType() or r.type == ir.FloatType():
                    if l.type != ir.FloatType():
                        l = self.builder.sitofp(l, ir.FloatType())
                    if r.type != ir.FloatType():
                        r = self.builder.sitofp(r, ir.FloatType())
                    return self.builder.fadd(l, r)
                return self.builder.add(l, r)
            if expr.op == "-":
                if l.type == ir.FloatType():
                    return self.builder.fsub(l, r)
                return self.builder.sub(l, r)
            if expr.op == "*":
                if l.type == ir.FloatType() or r.type == ir.FloatType():
                    if l.type != ir.FloatType():
                        l = self.builder.sitofp(l, ir.FloatType())
                    if r.type != ir.FloatType():
                        r = self.builder.sitofp(r, ir.FloatType())
                    return self.builder.fmul(l, r)
                return self.builder.mul(l, r)
            if expr.op == "/":
                if l.type == ir.FloatType():
                    return self.builder.fdiv(l, r)
                return self.builder.sdiv(l, r)
            if expr.op in ("==", "!=", "<", ">", "<=", ">="):
                if l.type == ir.FloatType():
                    cmp_map = {"==": "==", "!=": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">="}
                    return self.builder.fcmp_ordered(cmp_map[expr.op], l, r)
                signed = {"<": "<", ">": ">", "<=": "<=", ">=": ">="}
                if expr.op in signed:
                    return self.builder.icmp_signed(signed[expr.op], l, r)
                if expr.op == "==":
                    return self.builder.icmp_signed("==", l, r)
                return self.builder.icmp_signed("!=", l, r)
            if expr.op == "[]":
                if isinstance(expr.left, Identifier):
                    arr_ptr = self.local_vars.get(expr.left.name)
                    if arr_ptr:
                        idx = r
                        elem_ptr = self.builder.gep(
                            arr_ptr,
                            [ir.Constant(ir.IntType(32), 0), idx],
                        )
                        return self.builder.load(elem_ptr)
                return ir.Constant(ir.IntType(32), 0)
        if isinstance(expr, UnaryOp):
            o = self._gen_expr(expr.operand)
            if expr.op == "-":
                if o.type == ir.FloatType():
                    return self.builder.fneg(o)
                return self.builder.sub(ir.Constant(o.type, 0), o)
        if isinstance(expr, CallExpr):
            return self._gen_call(expr)
        if isinstance(expr, MemberAccess):
            return self._gen_member(expr)
        if isinstance(expr, StructInit):
            return self._gen_struct_init(expr)
        if isinstance(expr, ArrayLiteral):
            return self._gen_array_literal(expr)
        return ir.Constant(ir.IntType(32), 0)

    def _gen_call(self, expr: CallExpr) -> Any:
        assert self.builder is not None
        if isinstance(expr.callee, MemberAccess):
            obj = expr.callee.object
            method = expr.callee.member
            if isinstance(obj, Identifier):
                if obj.name == "io" and method == "print":
                    val = self._gen_expr(expr.args[0])
                    if val.type != ir.FloatType():
                        val = self.builder.sitofp(val, ir.FloatType())
                    fn = self.module.get_global("vyn_io_print_f32")
                    self.builder.call(fn, [val])
                    return ir.Constant(ir.IntType(32), 0)
                if obj.name == "io" and method == "println":
                    s = self._gen_expr(expr.args[0])
                    fn = self.module.get_global("vyn_io_println_str")
                    self.builder.call(fn, [s])
                    return ir.Constant(ir.IntType(32), 0)
                if obj.name == "sys" and method == "sleep":
                    ms = self._gen_expr(expr.args[0])
                    fn = self.module.get_global("vyn_sys_sleep_ms")
                    self.builder.call(fn, [ms])
                    return ir.Constant(ir.IntType(32), 0)
                struct = None
                if obj.name in self.struct_types:
                    struct = obj.name
                elif obj.name in self.local_types:
                    struct = self.local_types[obj.name]
                if struct and struct in self.struct_types:
                    fname = f"{struct}_{method}"
                    if fname in self.functions:
                        self_ptr = self.local_vars.get(obj.name)
                        if self_ptr and self.local_types.get(obj.name) == struct:
                            args = [self.builder.load(self_ptr)]
                        else:
                            val = self._gen_expr(obj)
                            tmp = self.builder.alloca(val.type)
                            self.builder.store(val, tmp)
                            args = [self.builder.load(tmp)]
                        args += [self._gen_expr(a) for a in expr.args]
                        return self.builder.call(self.functions[fname], args)
        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if name in self.functions:
                args = [self._gen_expr(a) for a in expr.args]
                fn = self.functions[name]
                # promotions de type
                fixed = []
                for i, a in enumerate(args):
                    if i < len(fn.args):
                        if fn.args[i].type == ir.FloatType() and a.type != ir.FloatType():
                            a = self.builder.sitofp(a, ir.FloatType())
                    fixed.append(a)
                return self.builder.call(fn, fixed)
            if name in {e.name for e in self.program.externs}:
                args = [self._gen_expr(a) for a in expr.args]
                fn = self.module.get_global(name)
                return self.builder.call(fn, args)
        return ir.Constant(ir.IntType(32), 0)

    def _gen_member(self, expr: MemberAccess) -> Any:
        assert self.builder is not None
        if isinstance(expr.object, Identifier) and expr.object.name in self.enum_map:
            idx = self.enum_map[expr.object.name].get(expr.member, 0)
            return ir.Constant(ir.IntType(32), idx)
        if isinstance(expr.object, Identifier) and expr.object.name == "self":
            self_ptr = self.local_vars.get("self_ptr")
            if self_ptr:
                loaded = self.builder.load(self_ptr)
                # accès champ via struct name from current context — simplifié
                for sname, stype in self.struct_types.items():
                    idx = self._field_index(sname, expr.member)
                    if idx >= 0:
                        field_ptr = self.builder.gep(
                            loaded,
                            [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)],
                        )
                        return self.builder.load(field_ptr)
        if isinstance(expr.object, Identifier):
            ptr = self.local_vars.get(expr.object.name)
            struct_name = self.local_types.get(expr.object.name)
            if ptr and struct_name in self.struct_types:
                idx = self._field_index(struct_name, expr.member)
                field_ptr = self.builder.gep(
                    self.builder.load(ptr),
                    [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)],
                )
                return self.builder.load(field_ptr)
        return ir.Constant(ir.IntType(32), 0)

    def _gen_struct_init(self, expr: StructInit) -> Any:
        assert self.builder is not None
        stype = self.struct_types[expr.struct_name]
        alloca = self.builder.alloca(stype)
        for i, (fname, fexpr) in enumerate(expr.fields.items()):
            val = self._gen_expr(fexpr)
            field_ptr = self.builder.gep(
                alloca,
                [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)],
            )
            self.builder.store(val, field_ptr)
        return self.builder.load(alloca)

    def _gen_array_literal(self, expr: ArrayLiteral) -> Any:
        assert self.builder is not None
        if expr.repeat:
            elem, count = expr.repeat
            val = self._gen_expr(elem)
            arr_ty = ir.ArrayType(ir.FloatType(), count)
            alloca = self.builder.alloca(arr_ty)
            for i in range(count):
                ptr = self.builder.gep(
                    alloca,
                    [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)],
                )
                self.builder.store(val, ptr)
            return alloca
        return ir.Constant(ir.IntType(32), 0)

    def _const_str(self, s: str) -> ir.Constant:
        assert self.builder is not None
        bs = bytearray(s.encode("utf-8") + b"\0")
        ctype = ir.ArrayType(ir.IntType(8), len(bs))
        gv = ir.GlobalVariable(self.module, ctype, name=f"str.{len(self.string_literals)}")
        gv.linkage = "internal"
        gv.global_constant = True
        gv.initializer = ir.Constant(ctype, bs)
        self.string_literals.append(s)
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(gv, [zero, zero], inbounds=True)

    def _field_index(self, struct_name: str, field: str) -> int:
        for s in self.program.structs:
            if s.name == struct_name:
                for i, f in enumerate(s.fields):
                    if f.name == field:
                        return i
        return 0

    def _infer_llvm_type(self, val: Any) -> str:
        if val.type == ir.FloatType():
            return "f32"
        if val.type == ir.IntType(1):
            return "bool"
        return "i32"


def compile_to_ir(source: str) -> tuple[str, SemanticAnalyzer]:
    from vyn.parser import Parser
    from vyn.prelude import inject_prelude
    program = Parser(inject_prelude(source)).parse()
    sem = SemanticAnalyzer()
    sem.analyze(program)
    gen = LLVMGenerator(program, sem)
    ir_code = gen.generate()
    return ir_code, sem
