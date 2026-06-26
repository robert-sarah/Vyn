"""Parseur Vyn — version complète : closures, while/for, génériques, patterns, tuples, ranges, casts, Option/Result."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from vyn.lexer.lexer import Lexer, Token, TokenKind
from vyn.ast.nodes import (
    # programme
    Program, ImportDecl, UseDecl, ExternDecl, ModDecl,
    # déclarations
    StructDecl, EnumDecl, EnumVariant, FunctionDecl, ImplDecl,
    TraitDecl, TraitMethod, ConstDecl, TypeAliasDecl,
    GenericParam, Field, Param,
    # types
    TypeNode,
    # expressions
    Expr, IntLiteral, FloatLiteral, BoolLiteral, StringLiteral,
    CharLiteral, NilLiteral, Identifier,
    SomeExpr, NoneExpr, OkExpr, ErrExpr,
    ArrayLiteral, TupleExpr, TupleIndex, MapLiteral,
    MemberAccess, IndexExpr, CallExpr, MethodCall,
    BinaryOp, UnaryOp, CastExpr, RangeExpr, QuestionExpr,
    ClosureExpr, ClosureParam, StructInit, IfExpr,
    # statements
    Stmt, LetStmt, LetTupleStmt, AssignStmt, ReturnStmt, ExprStmt,
    IfStmt, IfLetStmt,
    LoopStmt, WhileStmt, ForStmt,
    BreakStmt, ContinueStmt,
    MatchStmt, MatchArm, MatchCase,
    TryStmt, ThrowStmt, LocalFnStmt,
    # patterns
    Pattern, WildcardPattern, LiteralPattern, IdentPattern,
    EnumPattern, TuplePattern, StructPattern, OrPattern, RangePattern,
    # utils
    Attribute, Visibility, Span, make_void, make_i32,
)
from vyn.prelude import inject_prelude

# ─── Jeux de TokenKind pour les helpers ──────────────────────────────────────

_TYPE_KINDS = {
    TokenKind.I8,  TokenKind.I16, TokenKind.I32,  TokenKind.I64,
    TokenKind.U8,  TokenKind.U16, TokenKind.U32,  TokenKind.U64,
    TokenKind.F32, TokenKind.F64,
    TokenKind.BOOL, TokenKind.STR, TokenKind.CHAR_TYPE,
    TokenKind.VOID, TokenKind.USIZE, TokenKind.ISIZE,
    TokenKind.IDENT,
    TokenKind.FN,
}

_IDENT_KINDS = {TokenKind.IDENT} | _TYPE_KINDS

_ASSIGN_OPS = {
    TokenKind.EQ:        "=",
    TokenKind.PLUSEQ:    "+=",
    TokenKind.MINUSEQ:   "-=",
    TokenKind.STAREQ:    "*=",
    TokenKind.SLASHEQ:   "/=",
    TokenKind.PERCENTEQ: "%=",
    TokenKind.ANDEQ:     "&=",
    TokenKind.OREQ:      "|=",
    TokenKind.XOREQ:     "^=",
    TokenKind.LSHIFTEQ:  "<<=",
    TokenKind.RSHIFTEQ:  ">>=",
}


# ─── Erreur de parsing ────────────────────────────────────────────────────────

class ParseError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.message = message
        self.line    = line
        self.col     = col
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"[Parser] ligne {self.line}, col {self.col}: {self.message}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Parser principal
# ═══════════════════════════════════════════════════════════════════════════════

class Parser:
    """Descente récursive complète pour Vyn."""

    def __init__(self, source: str):
        self.tokens: List[Token] = Lexer(source).tokenize()
        self.pos: int = 0

    # ══════════════════════════════════════════════════════════════════════════
    #  Point d'entrée
    # ══════════════════════════════════════════════════════════════════════════

    def parse(self) -> Program:
        imports:      List[ImportDecl]    = []
        uses:         List[UseDecl]       = []
        externs:      List[ExternDecl]    = []
        structs:      List[StructDecl]    = []
        functions:    List[FunctionDecl]  = []
        impls:        List[ImplDecl]      = []
        enums:        List[EnumDecl]      = []
        consts:       List[ConstDecl]     = []
        type_aliases: List[TypeAliasDecl] = []
        traits:       List[TraitDecl]     = []
        mods:         List[ModDecl]       = []
        init_stmts:   List[Stmt]          = []

        while not self._is_at_end():
            tok = self._peek()

            # ── skip separateurs ──────────────────────────────────────────────
            if self._match(TokenKind.SEMI):
                continue

            # ── imports ───────────────────────────────────────────────────────
            if tok.kind == TokenKind.IMPORT:
                imports.append(self._parse_import())
                continue

            if tok.kind == TokenKind.USE:
                uses.append(self._parse_use())
                continue

            # ── extern ────────────────────────────────────────────────────────
            if tok.kind == TokenKind.EXTERN:
                for e in self._parse_extern_block():
                    externs.append(e)
                continue

            # ── visibilité (pub) ─────────────────────────────────────────────
            is_pub = self._match(TokenKind.PUB)
            vis = Visibility.PUBLIC if is_pub else Visibility.PRIVATE

            tok2 = self._peek()

            # ── mod ───────────────────────────────────────────────────────────
            if tok2.kind == TokenKind.MOD:
                mods.append(self._parse_mod(vis))
                continue

            # ── struct ────────────────────────────────────────────────────────
            if tok2.kind == TokenKind.STRUCT:
                structs.append(self._parse_struct(vis))
                continue

            # ── enum ──────────────────────────────────────────────────────────
            if tok2.kind == TokenKind.ENUM:
                enums.append(self._parse_enum(vis))
                continue

            # ── trait ─────────────────────────────────────────────────────────
            if tok2.kind == TokenKind.TRAIT:
                traits.append(self._parse_trait(vis))
                continue

            # ── type alias ────────────────────────────────────────────────────
            if tok2.kind == TokenKind.TYPE:
                type_aliases.append(self._parse_type_alias(vis))
                continue

            # ── const ─────────────────────────────────────────────────────────
            if tok2.kind == TokenKind.CONST:
                consts.append(self._parse_const(vis))
                continue

            # ── impl ──────────────────────────────────────────────────────────
            if tok2.kind == TokenKind.IMPL:
                impls.append(self._parse_impl())
                continue

            # ── fonction ──────────────────────────────────────────────────────
            if tok2.kind in (TokenKind.FN, TokenKind.HOT, TokenKind.ASYNC):
                attrs = self._peek_attributes()
                fn = self._parse_function(vis, attrs)
                functions.append(fn)
                continue

            # ── attribut @[...] suivi d'une fonction ─────────────────────────
            if tok2.kind == TokenKind.AT:
                attrs = self._parse_attributes()
                fn_vis = Visibility.PUBLIC if self._match(TokenKind.PUB) else Visibility.PRIVATE
                fn = self._parse_function(fn_vis, attrs)
                functions.append(fn)
                continue

            # ── instruction top-level (script-style) ─────────────────────────
            if is_pub:
                self._error(f"'pub' inattendu ici")
            stmt = self._parse_stmt()
            init_stmts.append(stmt)

        return Program(
            imports=imports, uses=uses, externs=externs,
            structs=structs, functions=functions, impls=impls,
            enums=enums, consts=consts, type_aliases=type_aliases,
            traits=traits, mods=mods, init_stmts=init_stmts,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  Déclarations top-level
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_import(self) -> ImportDecl:
        self._expect(TokenKind.IMPORT)
        path = self._parse_dotted_path()
        alias = None
        if self._match(TokenKind.AS):
            alias = self._parse_ident("alias")
        self._expect_semi()
        return ImportDecl(path, alias)

    def _parse_use(self) -> UseDecl:
        self._expect(TokenKind.USE)
        path = self._parse_dotted_path()
        symbols: List[str] = []
        # use std.io.{print, println}
        if self._match(TokenKind.DCOLON) or self._check(TokenKind.LBRACE):
            if self._match(TokenKind.LBRACE):
                while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
                    symbols.append(self._parse_ident("symbol"))
                    if not self._match(TokenKind.COMMA):
                        break
                self._expect(TokenKind.RBRACE)
        alias = None
        if self._match(TokenKind.AS):
            alias = self._parse_ident("alias")
        self._expect_semi()
        return UseDecl(path, symbols, alias)

    def _parse_dotted_path(self) -> str:
        parts = [self._parse_ident("module")]
        while self._check(TokenKind.DOT) or self._check(TokenKind.DCOLON):
            self._advance()
            if self._peek().kind in _IDENT_KINDS:
                parts.append(self._parse_ident("module"))
            else:
                break
        return ".".join(parts)

    def _parse_extern_block(self) -> List[ExternDecl]:
        self._expect(TokenKind.EXTERN)
        abi = "C"
        if self._check(TokenKind.STRING):
            abi = self._advance().value
        decls: List[ExternDecl] = []
        if self._match(TokenKind.LBRACE):
            while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
                self._match(TokenKind.FN)
                name = self._parse_ident("extern fn")
                params = self._parse_params()
                ret = self._parse_return_type()
                self._expect_semi()
                decls.append(ExternDecl(name, params, ret, abi))
            self._expect(TokenKind.RBRACE)
        else:
            # inline: extern "C" fn name(…) -> T;
            self._match(TokenKind.FN)
            name = self._parse_ident("extern fn")
            params = self._parse_params()
            ret = self._parse_return_type()
            self._expect_semi()
            decls.append(ExternDecl(name, params, ret, abi))
        return decls

    def _parse_struct(self, vis: Visibility = Visibility.PRIVATE) -> StructDecl:
        self._expect(TokenKind.STRUCT)
        name = self._parse_ident("struct")
        generics = self._parse_generic_params()
        self._expect(TokenKind.LBRACE)
        fields: List[Field] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            fvis = Visibility.PUBLIC if self._match(TokenKind.PUB) else Visibility.PRIVATE
            is_mut = self._match(TokenKind.MUT)
            fname = self._parse_ident("field")
            self._expect(TokenKind.COLON)
            ftype = self._parse_type()
            default = None
            if self._match(TokenKind.EQ):
                default = self._parse_expr()
            self._match(TokenKind.SEMI)
            self._match(TokenKind.COMMA)
            fields.append(Field(fname, ftype, is_mut, fvis, default))
        self._expect(TokenKind.RBRACE)
        return StructDecl(name, fields, generics, vis)

    def _parse_enum(self, vis: Visibility = Visibility.PRIVATE) -> EnumDecl:
        self._expect(TokenKind.ENUM)
        name = self._parse_ident("enum")
        generics = self._parse_generic_params()
        self._expect(TokenKind.LBRACE)
        variants: List[EnumVariant] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            vname = self._parse_ident("variant")
            payload = None
            fields: List[Field] = []
            if self._match(TokenKind.LPAREN):
                payload = self._parse_type()
                self._expect(TokenKind.RPAREN)
            elif self._match(TokenKind.LBRACE):
                while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
                    is_mut = self._match(TokenKind.MUT)
                    fn2 = self._parse_ident("field")
                    self._expect(TokenKind.COLON)
                    ft = self._parse_type()
                    self._match(TokenKind.COMMA)
                    fields.append(Field(fn2, ft, is_mut))
                self._expect(TokenKind.RBRACE)
            self._match(TokenKind.COMMA)
            variants.append(EnumVariant(vname, payload, fields))
        self._expect(TokenKind.RBRACE)
        return EnumDecl(name, variants, generics, vis)

    def _parse_trait(self, vis: Visibility = Visibility.PRIVATE) -> TraitDecl:
        self._expect(TokenKind.TRAIT)
        name = self._parse_ident("trait")
        generics = self._parse_generic_params()
        bounds: List[str] = []
        if self._match(TokenKind.COLON):
            bounds.append(self._parse_ident("bound"))
            while self._match(TokenKind.PLUS):
                bounds.append(self._parse_ident("bound"))
        self._expect(TokenKind.LBRACE)
        methods: List[TraitMethod] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            self._match(TokenKind.PUB)
            self._match(TokenKind.FN)
            mname = self._parse_ident("method")
            mg = self._parse_generic_params()
            params = self._parse_params()
            ret = self._parse_return_type()
            default_body = None
            if self._check(TokenKind.LBRACE):
                self._expect(TokenKind.LBRACE)
                default_body = self._parse_block()
                self._expect(TokenKind.RBRACE)
            else:
                self._expect_semi()
            methods.append(TraitMethod(mname, params, ret, mg, default_body))
        self._expect(TokenKind.RBRACE)
        return TraitDecl(name, methods, generics, bounds, vis)

    def _parse_type_alias(self, vis: Visibility = Visibility.PRIVATE) -> TypeAliasDecl:
        self._expect(TokenKind.TYPE)
        name = self._parse_ident("type alias")
        generics = self._parse_generic_params()
        self._expect(TokenKind.EQ)
        target = self._parse_type()
        self._expect_semi()
        return TypeAliasDecl(name, target, generics, vis)

    def _parse_const(self, vis: Visibility = Visibility.PRIVATE) -> ConstDecl:
        self._expect(TokenKind.CONST)
        name = self._parse_ident("const")
        self._expect(TokenKind.COLON)
        typ = self._parse_type()
        self._expect(TokenKind.EQ)
        val = self._parse_expr()
        self._expect_semi()
        return ConstDecl(name, typ, val, vis)

    def _parse_impl(self) -> ImplDecl:
        self._expect(TokenKind.IMPL)
        generics = self._parse_generic_params()
        # impl Trait for Struct  ou  impl Struct
        name_a = self._parse_ident("impl target")
        # consume generic args after name
        if self._check(TokenKind.LT):
            self._parse_type_args()  # discard
        trait_name = None
        struct_name = name_a
        if self._match(TokenKind.FOR):
            trait_name  = name_a
            struct_name = self._parse_ident("struct")
            if self._check(TokenKind.LT):
                self._parse_type_args()
        self._expect(TokenKind.LBRACE)
        methods: List[FunctionDecl] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            attrs = []
            if self._check(TokenKind.AT):
                attrs = self._parse_attributes()
            is_pub2 = self._match(TokenKind.PUB)
            fn_vis = Visibility.PUBLIC if is_pub2 else Visibility.PRIVATE
            fn = self._parse_function(fn_vis, attrs)
            methods.append(fn)
        self._expect(TokenKind.RBRACE)
        return ImplDecl(struct_name, trait_name, methods, generics)

    def _parse_mod(self, vis: Visibility = Visibility.PRIVATE) -> ModDecl:
        self._expect(TokenKind.MOD)
        name = self._parse_ident("mod")
        self._expect(TokenKind.LBRACE)
        fns:    List[FunctionDecl] = []
        structs:List[StructDecl]   = []
        enums:  List[EnumDecl]     = []
        consts: List[ConstDecl]    = []
        impls:  List[ImplDecl]     = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            is_pub = self._match(TokenKind.PUB)
            v2 = Visibility.PUBLIC if is_pub else Visibility.PRIVATE
            t = self._peek()
            if t.kind == TokenKind.STRUCT:
                structs.append(self._parse_struct(v2))
            elif t.kind == TokenKind.ENUM:
                enums.append(self._parse_enum(v2))
            elif t.kind == TokenKind.CONST:
                consts.append(self._parse_const(v2))
            elif t.kind == TokenKind.IMPL:
                impls.append(self._parse_impl())
            elif t.kind in (TokenKind.FN, TokenKind.HOT, TokenKind.ASYNC):
                fns.append(self._parse_function(v2))
            elif t.kind == TokenKind.AT:
                attrs = self._parse_attributes()
                fns.append(self._parse_function(v2, attrs))
            else:
                break
        self._expect(TokenKind.RBRACE)
        return ModDecl(name, fns, structs, enums, consts, impls, vis)

    # ══════════════════════════════════════════════════════════════════════════
    #  Fonctions
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_function(
        self,
        vis: Visibility = Visibility.PRIVATE,
        attrs: Optional[List[Attribute]] = None,
    ) -> FunctionDecl:
        if attrs is None:
            attrs = []
        is_async = self._match(TokenKind.ASYNC)
        is_hot   = self._match(TokenKind.HOT)
        self._expect(TokenKind.FN)
        name     = self._parse_ident("function name")
        generics = self._parse_generic_params()
        params   = self._parse_params()
        ret      = self._parse_return_type()
        # where clause optionnelle
        if self._peek().kind == TokenKind.WHERE:
            self._advance()
            while self._peek().kind in _IDENT_KINDS:
                self._parse_ident("where bound")
                if self._match(TokenKind.COLON):
                    self._parse_ident("trait bound")
                    while self._match(TokenKind.PLUS):
                        self._parse_ident("trait bound")
                if not self._match(TokenKind.COMMA):
                    break
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        return FunctionDecl(
            name=name, params=params, return_type=ret, body=body,
            is_hot=is_hot, is_async=is_async,
            generics=generics, attributes=attrs, visibility=vis,
        )

    def _parse_params(self) -> List[Param]:
        self._expect(TokenKind.LPAREN)
        params: List[Param] = []
        while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            if self._peek().kind == TokenKind.SELF:
                self._advance()
                params.append(Param("self", TypeNode("Self")))
                self._match(TokenKind.COMMA)
                continue
            is_mut = self._match(TokenKind.MUT)
            # support &self, &mut self
            if self._match(TokenKind.AMPERSAND):
                is_mut_ref = self._match(TokenKind.MUT)
                if self._peek().kind == TokenKind.SELF:
                    self._advance()
                    params.append(Param("self", TypeNode("Self"), is_mut_ref))
                    self._match(TokenKind.COMMA)
                    continue
            pname = self._parse_ident("parameter")
            # support vararg "..."
            if pname == "..." or pname == "vararg":
                params.append(Param("...", TypeNode("vararg")))
                self._match(TokenKind.COMMA)
                break
            self._expect(TokenKind.COLON)
            ptype = self._parse_type()
            default = None
            if self._match(TokenKind.EQ):
                default = self._parse_expr()
            params.append(Param(pname, ptype, is_mut, default))
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN)
        return params

    def _parse_return_type(self) -> TypeNode:
        if self._match(TokenKind.ARROW):
            return self._parse_type()
        return make_void()

    # ══════════════════════════════════════════════════════════════════════════
    #  Types
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_type(self) -> TypeNode:
        """Parse un type complet."""
        # référence &T ou &mut T
        if self._match(TokenKind.AMPERSAND):
            is_mut = self._match(TokenKind.MUT)
            inner  = self._parse_type()
            inner.is_ref = True
            inner.is_mut = is_mut or inner.is_mut
            return inner

        # mut T
        if self._match(TokenKind.MUT):
            inner = self._parse_type()
            inner.is_mut = True
            return inner

        # own T
        if self._match(TokenKind.OWN):
            inner = self._parse_type()
            inner.is_own = True
            return inner

        # pointeur brut *T
        if self._match(TokenKind.STAR):
            inner = self._parse_type()
            inner.is_ptr = True
            return inner

        # fn(T1, T2) -> R
        if self._check(TokenKind.FN):
            return self._parse_fn_type()

        # tuple (T1, T2, T3)
        if self._check(TokenKind.LPAREN):
            return self._parse_tuple_type()

        base = self._parse_type_name()

        # T[] ou T[N]
        while self._check(TokenKind.LBRACKET):
            self._advance()
            size = None
            if self._check(TokenKind.INT):
                size = int(self._advance().value)
            self._expect(TokenKind.RBRACKET)
            base = TypeNode("array", [base], size)

        # T? → Option<T>
        if self._check(TokenKind.QUESTION):
            self._advance()
            base = TypeNode("Option", [base])

        return base

    def _parse_type_name(self) -> TypeNode:
        """Parse un nom de type simple ou générique."""
        tok = self._peek()
        if tok.kind not in _TYPE_KINDS:
            raise self._error(f"type attendu, trouvé '{tok.value}'")
        name = self._advance().value
        args: List[TypeNode] = []
        # Type<T, U, …>
        if self._check(TokenKind.LT):
            args = self._parse_type_args()
        return TypeNode(name, args)

    def _parse_type_args(self) -> List[TypeNode]:
        """Parse <T, U, V, …>"""
        self._expect(TokenKind.LT)
        args: List[TypeNode] = []
        while not self._check(TokenKind.GT) and not self._check(TokenKind.EOF):
            args.append(self._parse_type())
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.GT)
        return args

    def _parse_fn_type(self) -> TypeNode:
        """fn(T1, T2) -> R"""
        self._expect(TokenKind.FN)
        self._expect(TokenKind.LPAREN)
        params: List[TypeNode] = []
        while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            params.append(self._parse_type())
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN)
        ret = make_void()
        if self._match(TokenKind.ARROW):
            ret = self._parse_type()
        return TypeNode("fn", params + [ret])

    def _parse_tuple_type(self) -> TypeNode:
        """(T1, T2, T3)"""
        self._expect(TokenKind.LPAREN)
        elems: List[TypeNode] = []
        while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            elems.append(self._parse_type())
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN)
        if len(elems) == 1:
            return elems[0]   # pas un tuple, juste des parenthèses
        return TypeNode("tuple", elems)

    # ══════════════════════════════════════════════════════════════════════════
    #  Génériques
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_generic_params(self) -> List[GenericParam]:
        """<T, U: Clone, V: Clone + Debug>"""
        if not self._check(TokenKind.LT):
            return []
        self._advance()
        params: List[GenericParam] = []
        while not self._check(TokenKind.GT) and not self._check(TokenKind.EOF):
            pname = self._parse_ident("generic param")
            bounds: List[str] = []
            if self._match(TokenKind.COLON):
                bounds.append(self._parse_ident("bound"))
                while self._match(TokenKind.PLUS):
                    bounds.append(self._parse_ident("bound"))
            params.append(GenericParam(pname, bounds))
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.GT)
        return params

    # ══════════════════════════════════════════════════════════════════════════
    #  Attributs @[…]
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_attributes(self) -> List[Attribute]:
        attrs: List[Attribute] = []
        while self._check(TokenKind.AT):
            self._advance()
            self._expect(TokenKind.LBRACKET)
            name = self._parse_ident("attribute")
            args: List[str] = []
            if self._match(TokenKind.LPAREN):
                while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
                    args.append(self._advance().value)
                    if not self._match(TokenKind.COMMA):
                        break
                self._expect(TokenKind.RPAREN)
            self._expect(TokenKind.RBRACKET)
            attrs.append(Attribute(name, args))
        return attrs

    def _peek_attributes(self) -> List[Attribute]:
        """Lit les attributs @[…] AVANT le fn, sans les consommer depuis la pile."""
        saved = self.pos
        attrs = self._parse_attributes()
        if not attrs:
            self.pos = saved
        return attrs

    # ══════════════════════════════════════════════════════════════════════════
    #  Blocs et statements
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_block(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            if self._match(TokenKind.SEMI):
                continue
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_stmt(self) -> Stmt:
        tok = self._peek()

        # ── let / let mut / let (tuple) ──────────────────────────────────────
        if tok.kind == TokenKind.LET:
            return self._parse_let()

        # ── const local ───────────────────────────────────────────────────────
        if tok.kind == TokenKind.CONST:
            return ExprStmt(self._parse_const_expr())

        # ── return ────────────────────────────────────────────────────────────
        if self._match(TokenKind.RETURN):
            if self._check(TokenKind.SEMI) or self._check(TokenKind.RBRACE):
                self._match(TokenKind.SEMI)
                return ReturnStmt(None)
            val = self._parse_expr()
            self._expect_semi()
            return ReturnStmt(val)

        # ── if / if let ───────────────────────────────────────────────────────
        if tok.kind == TokenKind.IF:
            return self._parse_if()

        # ── while ─────────────────────────────────────────────────────────────
        if tok.kind == TokenKind.WHILE:
            return self._parse_while()

        # ── for ───────────────────────────────────────────────────────────────
        if tok.kind == TokenKind.FOR:
            return self._parse_for()

        # ── loop ──────────────────────────────────────────────────────────────
        if tok.kind == TokenKind.LOOP:
            return self._parse_loop()

        # ── match ─────────────────────────────────────────────────────────────
        if tok.kind == TokenKind.MATCH:
            return self._parse_match()

        # ── try / catch ───────────────────────────────────────────────────────
        if tok.kind == TokenKind.TRY:
            return self._parse_try()

        # ── throw ─────────────────────────────────────────────────────────────
        if self._match(TokenKind.THROW):
            val = self._parse_expr()
            self._expect_semi()
            return ThrowStmt(val)

        # ── break ─────────────────────────────────────────────────────────────
        if self._match(TokenKind.BREAK):
            label = None
            value = None
            if self._check(TokenKind.IDENT) and not self._check(TokenKind.SEMI):
                try:
                    value = self._parse_expr()
                except Exception:
                    pass
            self._expect_semi()
            return BreakStmt(label, value)

        # ── continue ──────────────────────────────────────────────────────────
        if self._match(TokenKind.CONTINUE):
            self._expect_semi()
            return ContinueStmt()

        # ── fonction locale ───────────────────────────────────────────────────
        if tok.kind in (TokenKind.FN, TokenKind.HOT, TokenKind.ASYNC):
            fn = self._parse_function()
            return LocalFnStmt(fn)

        # ── expression / affectation ──────────────────────────────────────────
        expr = self._parse_expr()

        # assignation composée
        op_tok = self._peek()
        if op_tok.kind in _ASSIGN_OPS:
            self._advance()
            op_str = _ASSIGN_OPS[op_tok.kind]
            rhs = self._parse_expr()
            self._expect_semi()
            if op_str == "=":
                return AssignStmt(expr, rhs, "=")
            # opérateur composé : a += b  →  AssignStmt(a, BinaryOp(op, a, b), op)
            bin_op = op_str[:-1]   # "+=" → "+"
            return AssignStmt(expr, BinaryOp(bin_op, expr, rhs), op_str)

        self._expect_semi()
        return ExprStmt(expr)

    # ── let ───────────────────────────────────────────────────────────────────

    def _parse_let(self) -> Stmt:
        self._expect(TokenKind.LET)
        is_mut = self._match(TokenKind.MUT)

        # destructuration tuple : let (a, b, c) = …
        if self._check(TokenKind.LPAREN):
            names = self._parse_let_tuple_names()
            typ = None
            if self._match(TokenKind.COLON):
                typ = self._parse_type()
            self._expect(TokenKind.EQ)
            val = self._parse_expr()
            self._expect_semi()
            return LetTupleStmt(names, typ, val, is_mut)

        name = self._parse_ident("variable")
        typ = None
        if self._match(TokenKind.COLON):
            typ = self._parse_type()
        val = None
        if self._match(TokenKind.EQ):
            val = self._parse_expr()
        self._expect_semi()
        return LetStmt(name, typ, val, is_mut)

    def _parse_let_tuple_names(self) -> List[str]:
        self._expect(TokenKind.LPAREN)
        names: List[str] = []
        while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            names.append(self._parse_ident("variable"))
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN)
        return names

    def _parse_const_expr(self) -> Expr:
        """Parse une const locale comme expression (retourne l'Identifier)."""
        self._expect(TokenKind.CONST)
        name = self._parse_ident("const")
        self._expect(TokenKind.COLON)
        self._parse_type()  # on consomme le type
        self._expect(TokenKind.EQ)
        val = self._parse_expr()
        self._expect_semi()
        return val

    # ── if / if let ───────────────────────────────────────────────────────────

    def _parse_if(self) -> Stmt:
        self._expect(TokenKind.IF)

        # if let Pattern = expr { … }
        if self._check(TokenKind.LET):
            return self._parse_if_let()

        cond = self._parse_paren_expr()
        self._expect(TokenKind.LBRACE)
        then_body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        else_body = None
        if self._match(TokenKind.ELSE):
            if self._check(TokenKind.IF):
                else_body = [self._parse_if()]
            else:
                self._expect(TokenKind.LBRACE)
                else_body = self._parse_block()
                self._expect(TokenKind.RBRACE)
        return IfStmt(cond, then_body, else_body)

    def _parse_if_let(self) -> Stmt:
        self._expect(TokenKind.LET)
        pat   = self._parse_pattern()
        self._expect(TokenKind.EQ)
        value = self._parse_expr()
        self._expect(TokenKind.LBRACE)
        then_body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        else_body = None
        if self._match(TokenKind.ELSE):
            if self._check(TokenKind.IF):
                else_body = [self._parse_if()]
            else:
                self._expect(TokenKind.LBRACE)
                else_body = self._parse_block()
                self._expect(TokenKind.RBRACE)
        return IfLetStmt(pat, value, then_body, else_body)

    # ── while ─────────────────────────────────────────────────────────────────

    def _parse_while(self) -> Stmt:
        self._expect(TokenKind.WHILE)
        cond = self._parse_paren_expr()
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        return WhileStmt(cond, body)

    # ── for ───────────────────────────────────────────────────────────────────

    def _parse_for(self) -> Stmt:
        self._expect(TokenKind.FOR)
        var = self._parse_ident("loop variable")
        var_type = None
        if self._match(TokenKind.COLON):
            var_type = self._parse_type()
        self._expect(TokenKind.IN)
        iterable = self._parse_expr()
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        return ForStmt(var, var_type, iterable, body)

    # ── loop ──────────────────────────────────────────────────────────────────

    def _parse_loop(self) -> Stmt:
        self._expect(TokenKind.LOOP)
        # loop var in iterable { … }
        iterator = None
        if self._peek().kind in _IDENT_KINDS and not self._check_next(TokenKind.LPAREN):
            saved = self.pos
            try:
                var = self._parse_ident("loop variable")
                if self._match(TokenKind.IN):
                    iterable = self._parse_expr()
                    iterator = (var, iterable)
                else:
                    self.pos = saved
            except Exception:
                self.pos = saved
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        return LoopStmt(body, iterator)

    # ── match ─────────────────────────────────────────────────────────────────

    def _parse_match(self) -> Stmt:
        self._expect(TokenKind.MATCH)
        expr = self._parse_paren_expr()
        self._expect(TokenKind.LBRACE)
        arms:  List[MatchArm]  = []
        cases: List[MatchCase] = []  # legacy

        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            arm = self._parse_match_arm()
            arms.append(arm)
            # legacy MatchCase (pour la compatibilité interpréteur)
            cases.append(MatchCase(
                pattern=arm.pattern if not isinstance(arm.pattern, WildcardPattern) else None,
                body=arm.body,
                guard=arm.guard,
            ))
        self._expect(TokenKind.RBRACE)
        ms = MatchStmt(expr)
        ms.arms  = arms
        ms.cases = cases
        return ms

    def _parse_match_arm(self) -> MatchArm:
        """Parse une branche de match."""
        # default / else / _
        if (self._check(TokenKind.DEFAULT) or self._check(TokenKind.ELSE)
                or self._peek().kind == TokenKind.UNDERSCORE):
            self._advance()
            self._match(TokenKind.COLON)
            body = self._parse_case_body()
            return MatchArm(WildcardPattern(), None, body)

        # case pattern [if guard] : body
        self._match(TokenKind.CASE)   # optionnel
        pat = self._parse_or_pattern()

        # guard : if condition
        guard = None
        if self._match(TokenKind.IF):
            guard = self._parse_expr()

        self._match(TokenKind.COLON)
        # fat arrow =>
        self._match(TokenKind.FAT_ARROW)

        body = self._parse_case_body()
        return MatchArm(pat, guard, body)

    def _parse_case_body(self) -> List[Stmt]:
        if self._check(TokenKind.LBRACE):
            self._advance()
            body = self._parse_block()
            self._expect(TokenKind.RBRACE)
            return body
        # corps en ligne jusqu'au ; ou à la prochaine case/}
        stmts: List[Stmt] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            if self._check(TokenKind.CASE) or self._check(TokenKind.DEFAULT):
                break
            if self._check(TokenKind.ELSE) and self._check_ahead(1, TokenKind.COLON):
                break
            stmts.append(self._parse_stmt())
        return stmts

    # ── try/catch ─────────────────────────────────────────────────────────────

    def _parse_try(self) -> Stmt:
        self._expect(TokenKind.TRY)
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        var = "err"
        catch_body: List[Stmt] = []
        finally_body: List[Stmt] = []
        if self._match(TokenKind.CATCH):
            if self._match(TokenKind.LPAREN):
                var = self._parse_ident("catch variable")
                self._expect(TokenKind.RPAREN)
            elif self._peek().kind in _IDENT_KINDS:
                var = self._parse_ident("catch variable")
            self._expect(TokenKind.LBRACE)
            catch_body = self._parse_block()
            self._expect(TokenKind.RBRACE)
        # finally (extension)
        if self._peek().value == "finally":
            self._advance()
            self._expect(TokenKind.LBRACE)
            finally_body = self._parse_block()
            self._expect(TokenKind.RBRACE)
        return TryStmt(body, var, catch_body, finally_body)

    # ══════════════════════════════════════════════════════════════════════════
    #  Patterns
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_or_pattern(self) -> Pattern:
        """pat1 | pat2 | pat3"""
        first = self._parse_single_pattern()
        if not self._check(TokenKind.PIPE):
            return first
        pats = [first]
        while self._match(TokenKind.PIPE):
            pats.append(self._parse_single_pattern())
        return OrPattern(pats)

    def _parse_pattern(self) -> Pattern:
        return self._parse_or_pattern()

    def _parse_single_pattern(self) -> Pattern:
        tok = self._peek()

        # wildcard _
        if tok.kind == TokenKind.UNDERSCORE:
            self._advance()
            return WildcardPattern()

        # tuple pattern (a, b, c)
        if tok.kind == TokenKind.LPAREN:
            return self._parse_tuple_pattern()

        # littéraux
        if tok.kind in (TokenKind.INT, TokenKind.FLOAT, TokenKind.STRING,
                        TokenKind.CHAR, TokenKind.TRUE, TokenKind.FALSE,
                        TokenKind.NIL):
            lit = self._parse_primary()
            # range pattern : lit..=lit2
            if self._check(TokenKind.DOTDOT) or self._check(TokenKind.DOTDOTEQ):
                inclusive = self._advance().kind == TokenKind.DOTDOTEQ
                end = self._parse_primary()
                return RangePattern(lit, end, inclusive)
            return LiteralPattern(lit)

        # négatif : -42
        if tok.kind == TokenKind.MINUS:
            self._advance()
            inner = self._parse_primary()
            lit = UnaryOp("-", inner)
            return LiteralPattern(lit)

        # None / nil
        if tok.kind in (TokenKind.NONE, TokenKind.NIL):
            self._advance()
            return LiteralPattern(NoneExpr())

        # Some(pat) / Ok(pat) / Err(pat) / EnumName::Variant(pat)
        if tok.kind in (TokenKind.SOME, TokenKind.OK, TokenKind.ERR):
            name = self._advance().value
            payload = None
            if self._match(TokenKind.LPAREN):
                payload = self._parse_single_pattern()
                self._expect(TokenKind.RPAREN)
            # map Some → Option::Some etc.
            enum_map = {"Some": ("Option", "Some"), "Ok": ("Result", "Ok"), "Err": ("Result", "Err")}
            en, vn = enum_map[name]
            return EnumPattern(en, vn, payload)

        # struct / enum pattern avec nom majuscule
        if tok.kind == TokenKind.IDENT and tok.value[0].isupper():
            name = self._advance().value
            # Enum::Variant
            if self._match(TokenKind.DCOLON):
                variant = self._parse_ident("variant")
                payload = None
                if self._match(TokenKind.LPAREN):
                    payload = self._parse_single_pattern()
                    self._expect(TokenKind.RPAREN)
                return EnumPattern(name, variant, payload)
            # Struct { fields }
            if self._check(TokenKind.LBRACE):
                return self._parse_struct_pattern(name)
            # EnumVariant(payload)
            if self._check(TokenKind.LPAREN):
                self._advance()
                payload = self._parse_single_pattern()
                self._expect(TokenKind.RPAREN)
                return EnumPattern("", name, payload)
            # Variable capture (nom minuscule conventionnel, mais IDENT majuscule = enum unit)
            return EnumPattern("", name, None)

        # Enum.Variant (accès par point, legacy)
        if tok.kind == TokenKind.IDENT:
            name = self._advance().value
            if self._check(TokenKind.DOT):
                self._advance()
                variant = self._parse_ident("variant")
                return EnumPattern(name, variant, None)
            # variable de capture
            is_mut = False
            return IdentPattern(name, is_mut)

        # type keyword comme capture (i32, str …)
        if tok.kind in _TYPE_KINDS and tok.kind != TokenKind.IDENT:
            name = self._advance().value
            return IdentPattern(name)

        raise self._error(f"pattern attendu, trouvé '{tok.value}'")

    def _parse_tuple_pattern(self) -> Pattern:
        self._expect(TokenKind.LPAREN)
        elems: List[Pattern] = []
        while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            elems.append(self._parse_single_pattern())
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN)
        if len(elems) == 1:
            return elems[0]
        return TuplePattern(elems)

    def _parse_struct_pattern(self, name: str) -> Pattern:
        self._expect(TokenKind.LBRACE)
        fields: Dict[str, Pattern] = {}
        rest = False
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            if self._check(TokenKind.DOTDOT):
                self._advance()
                rest = True
                break
            fname = self._parse_ident("field")
            if self._match(TokenKind.COLON):
                fields[fname] = self._parse_single_pattern()
            else:
                fields[fname] = IdentPattern(fname)
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RBRACE)
        return StructPattern(name, fields, rest)

    # ══════════════════════════════════════════════════════════════════════════
    #  Expressions (descente récursive, du moins prioritaire au plus)
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_expr(self) -> Expr:
        return self._parse_range()

    # ── range ─────────────────────────────────────────────────────────────────

    def _parse_range(self) -> Expr:
        left = self._parse_or()
        if self._check(TokenKind.DOTDOT):
            self._advance()
            right = self._parse_or()
            return RangeExpr(left, right, False)
        if self._check(TokenKind.DOTDOTEQ):
            self._advance()
            right = self._parse_or()
            return RangeExpr(left, right, True)
        return left

    # ── logique or ────────────────────────────────────────────────────────────

    def _parse_or(self) -> Expr:
        left = self._parse_and()
        while self._check(TokenKind.OR) or self._check(TokenKind.OROR):
            self._advance()
            right = self._parse_and()
            left  = BinaryOp("||", left, right)
        return left

    # ── logique and ───────────────────────────────────────────────────────────

    def _parse_and(self) -> Expr:
        left = self._parse_not()
        while self._check(TokenKind.AND) or self._check(TokenKind.ANDAND):
            self._advance()
            right = self._parse_not()
            left  = BinaryOp("&&", left, right)
        return left

    # ── not ───────────────────────────────────────────────────────────────────

    def _parse_not(self) -> Expr:
        if self._check(TokenKind.NOT):
            self._advance()
            return UnaryOp("!", self._parse_not())
        if self._check(TokenKind.BANG):
            self._advance()
            return UnaryOp("!", self._parse_not())
        return self._parse_equality()

    # ── comparaison / égalité ────────────────────────────────────────────────

    def _parse_equality(self) -> Expr:
        left = self._parse_comparison()
        while True:
            if self._match(TokenKind.EQEQ):
                left = BinaryOp("==", left, self._parse_comparison())
            elif self._match(TokenKind.NEQ):
                left = BinaryOp("!=", left, self._parse_comparison())
            else:
                break
        return left

    def _parse_comparison(self) -> Expr:
        left = self._parse_bitwise_or()
        while True:
            if self._match(TokenKind.LT):
                left = BinaryOp("<", left, self._parse_bitwise_or())
            elif self._match(TokenKind.GT):
                left = BinaryOp(">", left, self._parse_bitwise_or())
            elif self._match(TokenKind.LE):
                left = BinaryOp("<=", left, self._parse_bitwise_or())
            elif self._match(TokenKind.GE):
                left = BinaryOp(">=", left, self._parse_bitwise_or())
            else:
                break
        return left

    # ── bitwise ───────────────────────────────────────────────────────────────

    def _parse_bitwise_or(self) -> Expr:
        left = self._parse_bitwise_xor()
        while self._check(TokenKind.PIPE) and not self._check_ahead(1, TokenKind.PIPE):
            self._advance()
            left = BinaryOp("|", left, self._parse_bitwise_xor())
        return left

    def _parse_bitwise_xor(self) -> Expr:
        left = self._parse_bitwise_and()
        while self._match(TokenKind.CARET):
            left = BinaryOp("^", left, self._parse_bitwise_and())
        return left

    def _parse_bitwise_and(self) -> Expr:
        left = self._parse_shift()
        while self._check(TokenKind.AMPERSAND) and not self._check_ahead(1, TokenKind.AMPERSAND):
            self._advance()
            left = BinaryOp("&", left, self._parse_shift())
        return left

    def _parse_shift(self) -> Expr:
        left = self._parse_term()
        while True:
            if self._match(TokenKind.LSHIFT):
                left = BinaryOp("<<", left, self._parse_term())
            elif self._match(TokenKind.RSHIFT):
                left = BinaryOp(">>", left, self._parse_term())
            else:
                break
        return left

    # ── addition / soustraction ───────────────────────────────────────────────

    def _parse_term(self) -> Expr:
        left = self._parse_factor()
        while True:
            if self._match(TokenKind.PLUS):
                left = BinaryOp("+", left, self._parse_factor())
            elif self._match(TokenKind.MINUS):
                left = BinaryOp("-", left, self._parse_factor())
            else:
                break
        return left

    # ── multiplication / division ─────────────────────────────────────────────

    def _parse_factor(self) -> Expr:
        left = self._parse_cast()
        while True:
            if self._match(TokenKind.STAR):
                left = BinaryOp("*", left, self._parse_cast())
            elif self._match(TokenKind.SLASH):
                left = BinaryOp("/", left, self._parse_cast())
            elif self._match(TokenKind.PERCENT):
                left = BinaryOp("%", left, self._parse_cast())
            else:
                break
        return left

    # ── cast as ───────────────────────────────────────────────────────────────

    def _parse_cast(self) -> Expr:
        expr = self._parse_unary()
        while self._match(TokenKind.AS):
            target = self._parse_type()
            expr = CastExpr(expr, target)
        return expr

    # ── unaire ────────────────────────────────────────────────────────────────

    def _parse_unary(self) -> Expr:
        if self._match(TokenKind.MINUS):
            return UnaryOp("-", self._parse_unary())
        if self._check(TokenKind.BANG) or self._check(TokenKind.NOT):
            self._advance()
            return UnaryOp("!", self._parse_unary())
        if self._match(TokenKind.TILDE):
            return UnaryOp("~", self._parse_unary())
        if self._match(TokenKind.STAR):
            return UnaryOp("*", self._parse_unary())   # déréférencement
        if self._match(TokenKind.AMPERSAND):
            is_mut = self._match(TokenKind.MUT)
            inner  = self._parse_unary()
            return UnaryOp("&mut" if is_mut else "&", inner)
        return self._parse_question()

    # ── ? propagation ─────────────────────────────────────────────────────────

    def _parse_question(self) -> Expr:
        expr = self._parse_postfix()
        while self._match(TokenKind.QUESTION):
            expr = QuestionExpr(expr)
        return expr

    # ── postfix : appel, indexation, accès membre ─────────────────────────────

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()
        while True:
            if self._check(TokenKind.DOT):
                self._advance()
                # accès champ ou appel méthode
                member = self._parse_ident("member")
                if self._check(TokenKind.LPAREN):
                    args = self._parse_call_args()
                    expr = CallExpr(MemberAccess(expr, member), args)
                elif self._check(TokenKind.INT):
                    # tuple.0
                    idx = int(self._advance().value)
                    expr = TupleIndex(expr, idx)
                else:
                    expr = MemberAccess(expr, member)

            elif self._check(TokenKind.LBRACKET):
                self._advance()
                idx = self._parse_expr()
                self._expect(TokenKind.RBRACKET)
                expr = IndexExpr(expr, idx)

            elif self._check(TokenKind.LPAREN):
                args = self._parse_call_args()
                expr = CallExpr(expr, args)

            elif self._check(TokenKind.QUESTION):
                self._advance()
                expr = QuestionExpr(expr)

            else:
                break
        return expr

    def _parse_call_args(self) -> List[Expr]:
        self._expect(TokenKind.LPAREN)
        args: List[Expr] = []
        while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
            args.append(self._parse_expr())
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RPAREN)
        return args

    # ── primaire ──────────────────────────────────────────────────────────────

    def _parse_primary(self) -> Expr:
        tok = self._peek()

        # ── littéraux ─────────────────────────────────────────────────────────
        if tok.kind == TokenKind.INT:
            self._advance()
            return IntLiteral(int(tok.value))

        if tok.kind == TokenKind.FLOAT:
            self._advance()
            return FloatLiteral(float(tok.value))

        if tok.kind == TokenKind.STRING:
            self._advance()
            return StringLiteral(tok.value)

        if tok.kind == TokenKind.CHAR:
            self._advance()
            return CharLiteral(tok.value)

        if tok.kind == TokenKind.TRUE:
            self._advance()
            return BoolLiteral(True)

        if tok.kind == TokenKind.FALSE:
            self._advance()
            return BoolLiteral(False)

        if tok.kind in (TokenKind.NIL, TokenKind.NONE):
            self._advance()
            return NilLiteral()

        # ── None explicite ────────────────────────────────────────────────────
        if tok.kind == TokenKind.NONE:
            self._advance()
            return NoneExpr()

        # ── Some(…) / Ok(…) / Err(…) ─────────────────────────────────────────
        if tok.kind == TokenKind.SOME:
            self._advance()
            self._expect(TokenKind.LPAREN)
            inner = self._parse_expr()
            self._expect(TokenKind.RPAREN)
            return SomeExpr(inner)

        if tok.kind == TokenKind.OK:
            self._advance()
            self._expect(TokenKind.LPAREN)
            inner = self._parse_expr()
            self._expect(TokenKind.RPAREN)
            return OkExpr(inner)

        if tok.kind == TokenKind.ERR:
            self._advance()
            self._expect(TokenKind.LPAREN)
            inner = self._parse_expr()
            self._expect(TokenKind.RPAREN)
            return ErrExpr(inner)

        # ── closure |params| expr  ou  |params| -> T { stmts } ───────────────
        if tok.kind == TokenKind.PIPE:
            return self._parse_closure()

        # ── tableau [elem, …] ou [val; N] ─────────────────────────────────────
        if tok.kind == TokenKind.LBRACKET:
            return self._parse_array_literal()

        # ── map literal #{k: v, …} ────────────────────────────────────────────
        if tok.kind == TokenKind.HASH and self._check_ahead(1, TokenKind.LBRACE):
            return self._parse_map_literal()

        # ── if expr (expression) ──────────────────────────────────────────────
        if tok.kind == TokenKind.IF and self._check_ahead(2, TokenKind.LBRACE):
            return self._parse_if_expr()

        # ── parenthèses / tuple ───────────────────────────────────────────────
        if tok.kind == TokenKind.LPAREN:
            return self._parse_paren_or_tuple()

        # ── fn littéral (closure nommée ou pointeur) ──────────────────────────
        if tok.kind == TokenKind.FN:
            fn = self._parse_function()
            return Identifier(fn.name)  # référence la fonction

        # ── identifiant / appel / struct init ─────────────────────────────────
        if tok.kind in _IDENT_KINDS:
            return self._parse_ident_or_call()

        raise self._error(f"expression attendue, trouvé '{tok.value}'")

    # ── closure ───────────────────────────────────────────────────────────────

    def _parse_closure(self) -> Expr:
        self._expect(TokenKind.PIPE)
        params: List[ClosureParam] = []
        while not self._check(TokenKind.PIPE) and not self._check(TokenKind.EOF):
            is_mut = self._match(TokenKind.MUT)
            pname  = self._parse_ident("closure param")
            ptype  = None
            if self._match(TokenKind.COLON):
                ptype = self._parse_type()
            params.append(ClosureParam(pname, ptype, is_mut))
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.PIPE)
        ret_type = None
        if self._match(TokenKind.ARROW):
            ret_type = self._parse_type()
        # bloc ou expression
        if self._check(TokenKind.LBRACE):
            self._advance()
            body = self._parse_block()
            self._expect(TokenKind.RBRACE)
            return ClosureExpr(params, ret_type, body, None)
        else:
            expr = self._parse_expr()
            return ClosureExpr(params, ret_type, None, expr)

    # ── tableau ───────────────────────────────────────────────────────────────

    def _parse_array_literal(self) -> Expr:
        self._expect(TokenKind.LBRACKET)
        if self._check(TokenKind.RBRACKET):
            self._advance()
            return ArrayLiteral([])
        first = self._parse_expr()
        # [val; N] — répétition
        if self._match(TokenKind.SEMI):
            count = int(self._expect(TokenKind.INT).value)
            self._expect(TokenKind.RBRACKET)
            return ArrayLiteral([], (first, count))
        elems = [first]
        while self._match(TokenKind.COMMA):
            if self._check(TokenKind.RBRACKET):
                break
            elems.append(self._parse_expr())
        self._expect(TokenKind.RBRACKET)
        return ArrayLiteral(elems)

    # ── map literal ───────────────────────────────────────────────────────────

    def _parse_map_literal(self) -> Expr:
        self._advance()  # #
        self._expect(TokenKind.LBRACE)
        entries: List[Tuple[Expr, Expr]] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            key = self._parse_expr()
            self._expect(TokenKind.COLON)
            val = self._parse_expr()
            entries.append((key, val))
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RBRACE)
        return MapLiteral(entries)

    # ── if expression ─────────────────────────────────────────────────────────

    def _parse_if_expr(self) -> Expr:
        self._expect(TokenKind.IF)
        cond = self._parse_paren_expr()
        self._expect(TokenKind.LBRACE)
        then_stmts = self._parse_block()
        self._expect(TokenKind.RBRACE)
        self._expect(TokenKind.ELSE)
        self._expect(TokenKind.LBRACE)
        else_stmts = self._parse_block()
        self._expect(TokenKind.RBRACE)
        # simplifier : retourner les valeurs finales
        then_val = _last_expr(then_stmts)
        else_val = _last_expr(else_stmts)
        if then_val and else_val:
            return IfExpr(cond, then_val, else_val)
        return IfExpr(cond,
                      then_val or NilLiteral(),
                      else_val or NilLiteral())

    # ── parenthèses / tuple ───────────────────────────────────────────────────

    def _parse_paren_or_tuple(self) -> Expr:
        self._expect(TokenKind.LPAREN)
        if self._check(TokenKind.RPAREN):
            self._advance()
            return TupleExpr([])   # unit ()
        first = self._parse_expr()
        if self._match(TokenKind.COMMA):
            elems = [first]
            while not self._check(TokenKind.RPAREN) and not self._check(TokenKind.EOF):
                elems.append(self._parse_expr())
                if not self._match(TokenKind.COMMA):
                    break
            self._expect(TokenKind.RPAREN)
            return TupleExpr(elems)
        self._expect(TokenKind.RPAREN)
        return first   # juste des parenthèses

    def _parse_paren_expr(self) -> Expr:
        """Parse une expression optionnellement entourée de parenthèses."""
        if self._check(TokenKind.LPAREN):
            saved = self.pos
            try:
                self._advance()
                expr = self._parse_expr()
                self._expect(TokenKind.RPAREN)
                return expr
            except ParseError:
                self.pos = saved
        return self._parse_expr()

    # ── identifiant → appel, struct init, accès module ───────────────────────

    def _parse_ident_or_call(self) -> Expr:
        name = self._parse_ident("identifier")

        # struct init : Name { field: val, … }
        if self._check(TokenKind.LBRACE) and self._is_struct_init():
            return self._parse_struct_init(name)

        # appel direct : name(…)
        if self._check(TokenKind.LPAREN):
            args = self._parse_call_args()
            return CallExpr(Identifier(name), args)

        # chemin qualifié : name.field / name.method(…) / mod.fn(…)
        return Identifier(name)

    def _is_struct_init(self) -> bool:
        """Heuristique : { suivi d'ident : expr → init de struct."""
        saved = self.pos
        try:
            self._advance()   # {
            if self._peek().kind in _IDENT_KINDS:
                self._advance()
                if self._check(TokenKind.COLON):
                    self.pos = saved
                    return True
            self.pos = saved
            return False
        except Exception:
            self.pos = saved
            return False

    def _parse_struct_init(self, name: str) -> Expr:
        self._expect(TokenKind.LBRACE)
        fields: Dict[str, Expr] = {}
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            if self._check(TokenKind.DOTDOT):
                self._advance()
                self._parse_expr()  # spread …base
                break
            fname = self._parse_ident("field")
            if self._match(TokenKind.COLON):
                fields[fname] = self._parse_expr()
            else:
                fields[fname] = Identifier(fname)  # shorthand
            if not self._match(TokenKind.COMMA):
                break
        self._expect(TokenKind.RBRACE)
        return StructInit(name, fields)

    # ══════════════════════════════════════════════════════════════════════════
    #  Helpers parser
    # ══════════════════════════════════════════════════════════════════════════

    def _parse_ident(self, role: str = "identifier") -> str:
        tok = self._peek()
        if tok.kind in _IDENT_KINDS:
            return self._advance().value
        raise self._error(f"identifiant attendu pour {role}, trouvé '{tok.value}'")

    def _expect_semi(self) -> None:
        """Attend un ';' ou l'ignore si absente (syntaxe flexible)."""
        self._match(TokenKind.SEMI)

    def _match(self, kind: TokenKind) -> bool:
        if self._check(kind):
            self._advance()
            return True
        return False

    def _check(self, kind: TokenKind) -> bool:
        if self._is_at_end():
            return kind == TokenKind.EOF
        return self._peek().kind == kind

    def _check_next(self, kind: TokenKind) -> bool:
        """Vérifie le token après le courant."""
        if self.pos + 1 >= len(self.tokens):
            return False
        return self.tokens[self.pos + 1].kind == kind

    def _check_ahead(self, offset: int, kind: TokenKind) -> bool:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return False
        return self.tokens[idx].kind == kind

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if not self._is_at_end():
            self.pos += 1
        return tok

    def _is_at_end(self) -> bool:
        return self.pos >= len(self.tokens) or self.tokens[self.pos].kind == TokenKind.EOF

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _previous(self) -> Token:
        return self.tokens[max(0, self.pos - 1)]

    def _expect(self, kind: TokenKind) -> Token:
        if self._check(kind):
            return self._advance()
        tok = self._peek()
        raise self._error(f"'{kind.name}' attendu, trouvé '{tok.value}' ({tok.kind.name})")

    def _error(self, message: str) -> ParseError:
        tok = self._peek()
        return ParseError(message, tok.line, tok.col)


# ─── Utilitaire interne ───────────────────────────────────────────────────────

def _last_expr(stmts: List[Stmt]) -> Optional[Expr]:
    """Extrait la dernière expression d'une liste de statements (pour if-expr)."""
    if not stmts:
        return None
    last = stmts[-1]
    if isinstance(last, ExprStmt):
        return last.expr
    if isinstance(last, ReturnStmt) and last.value:
        return last.value
    return None
