"""Analyse syntaxique descendante Vyn — robuste."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

from vyn.ast.nodes import *
from vyn.lexer import Lexer, Token, TokenKind

# Tous les mots-cles utilisables comme identifiants (noms variables/fonctions/champs)
_IDENT_KINDS: Set[TokenKind] = {
    TokenKind.IDENT,
    TokenKind.I32, TokenKind.F32, TokenKind.BOOL, TokenKind.STR, TokenKind.VOID,
    TokenKind.TYPE, TokenKind.ENUM, TokenKind.OWN, TokenKind.REF, TokenKind.CONST,
    TokenKind.TASK, TokenKind.SYNC, TokenKind.ASYNC, TokenKind.MOD, TokenKind.MATCH,
    TokenKind.LOOP, TokenKind.USE, TokenKind.IF, TokenKind.ELSE, TokenKind.IN,
    TokenKind.CASE, TokenKind.BREAK, TokenKind.CONTINUE, TokenKind.TRY, TokenKind.CATCH,
    TokenKind.THROW, TokenKind.AND, TokenKind.OR, TokenKind.NOT, TokenKind.HOT,
    TokenKind.FN, TokenKind.LET, TokenKind.STRUCT, TokenKind.IMPL, TokenKind.IMPORT,
}

# Types primitifs + identifiants custom
_TYPE_KINDS: Set[TokenKind] = _IDENT_KINDS | {TokenKind.SELF}


@dataclass
class ParseError(Exception):
    message: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"[Parser] ligne {self.line}, col {self.col}: {self.message}"


class Parser:
    def __init__(self, source: str):
        self.tokens = Lexer(source).tokenize()
        self.pos = 0

    def parse(self) -> Program:
        imports, uses, externs, structs, functions, impls, init_stmts = [], [], [], [], [], [], []
        while not self._check(TokenKind.EOF):
            if self._check(TokenKind.AT):
                functions.append(self._parse_function(attributes=self._parse_attributes()))
            elif self._match(TokenKind.IMPORT):
                imports.append(self._parse_import())
            elif self._match(TokenKind.USE):
                uses.append(self._parse_use())
            elif self._match(TokenKind.EXTERN):
                externs.append(self._parse_extern())
            elif self._match(TokenKind.STRUCT):
                structs.append(self._parse_struct())
            elif self._match(TokenKind.IMPL):
                impls.append(self._parse_impl())
            elif self._match(TokenKind.HOT):
                self._expect(TokenKind.FN)
                functions.append(self._parse_function(is_hot=True, skip_fn=True))
            elif self._match(TokenKind.PUB):
                if self._check(TokenKind.FN):
                    self._advance()
                    functions.append(self._parse_function(visibility=Visibility.PUBLIC, skip_fn=True))
                elif self._check(TokenKind.STRUCT):
                    self._advance()
                    structs.append(self._parse_struct(visibility=Visibility.PUBLIC))
                else:
                    self._error("pub doit preceder fn ou struct")
            elif self._check(TokenKind.FN):
                functions.append(self._parse_function())
            else:
                # Instructions au niveau module: log.info(), let x, loop {}, etc.
                init_stmts.append(self._parse_stmt())
        return Program(imports, uses, externs, structs, functions, impls, init_stmts)

    def _parse_ident(self, ctx: str = "identifiant") -> str:
        tok = self._peek()
        if tok.kind in _IDENT_KINDS:
            self._advance()
            return tok.value
        self._error(f"{ctx} attendu, trouve '{tok.value}'")
        return tok.value

    def _parse_use(self) -> UseDecl:
        path = self._parse_ident("module")
        while self._match(TokenKind.DOT):
            part = self._parse_ident("symbole")
            if part in ("print", "println", "sleep", "clamp", "lerp", "window", "run",
                        "label", "button", "abs", "sqrt", "len", "parse", "exists"):
                self._expect(TokenKind.SEMI)
                return UseDecl(path, [part])
            path += "." + part
        self._expect(TokenKind.SEMI)
        return UseDecl(path)

    def _parse_attributes(self) -> List[Attribute]:
        attrs = []
        while self._check(TokenKind.AT):
            self._expect(TokenKind.AT)
            self._expect(TokenKind.LBRACKET)
            attrs.append(Attribute(self._parse_ident("attribut")))
            self._expect(TokenKind.RBRACKET)
        return attrs

    def _parse_import(self) -> ImportDecl:
        path = self._parse_ident("module")
        while self._match(TokenKind.DOT):
            path += "." + self._parse_ident("module")
        self._expect(TokenKind.SEMI)
        return ImportDecl(path)

    def _parse_extern(self) -> ExternDecl:
        abi = "C"
        if self._match(TokenKind.STRING):
            abi = self._previous().value
        self._expect(TokenKind.LBRACE)
        self._expect(TokenKind.FN)
        fname = self._parse_ident("fonction")
        self._expect(TokenKind.LPAREN)
        params = self._parse_params()
        self._expect(TokenKind.RPAREN)
        ret = self._parse_return_type()
        self._expect(TokenKind.SEMI)
        self._expect(TokenKind.RBRACE)
        return ExternDecl(fname, params, ret, abi)

    def _parse_struct(self, visibility=Visibility.PRIVATE) -> StructDecl:
        name = self._parse_ident("struct")
        self._expect(TokenKind.LBRACE)
        fields = []
        while not self._check(TokenKind.RBRACE):
            is_mut = self._match(TokenKind.MUT)
            fname = self._parse_ident("champ")
            self._expect(TokenKind.COLON)
            fields.append(Field(fname, self._parse_type(), is_mut))
            self._expect(TokenKind.SEMI)
        self._expect(TokenKind.RBRACE)
        return StructDecl(name, fields, visibility)

    def _parse_impl(self) -> ImplBlock:
        name = self._parse_ident("struct")
        self._expect(TokenKind.LBRACE)
        methods = []
        while not self._check(TokenKind.RBRACE):
            methods.append(self._parse_function(is_method=True))
        self._expect(TokenKind.RBRACE)
        return ImplBlock(name, methods)

    def _parse_function(self, is_hot=False, attributes=None, visibility=Visibility.PRIVATE,
                        is_method=False, skip_fn=False) -> FunctionDecl:
        if not skip_fn:
            self._expect(TokenKind.FN)
        name = self._parse_ident("fonction")
        self._expect(TokenKind.LPAREN)
        params = self._parse_params(allow_self=is_method)
        self._expect(TokenKind.RPAREN)
        ret = self._parse_return_type()
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        return FunctionDecl(name, params, ret, body, is_hot, attributes or [], visibility)

    def _parse_params(self, allow_self=False) -> List[Param]:
        params = []
        if self._check(TokenKind.RPAREN):
            return params
        while True:
            if allow_self and self._match(TokenKind.SELF):
                params.append(Param("self", TypeNode("Self"), False))
            else:
                is_mut = self._match(TokenKind.MUT)
                pname = self._parse_ident("parametre")
                self._expect(TokenKind.COLON)
                params.append(Param(pname, self._parse_type(), is_mut))
            if not self._match(TokenKind.COMMA):
                break
        return params

    def _parse_return_type(self) -> TypeNode:
        if self._match(TokenKind.ARROW):
            return self._parse_type()
        return TypeNode("void")

    def _parse_type(self) -> TypeNode:
        if self._match(TokenKind.OWN):
            t = self._parse_type(); t.is_own = True; return t
        if self._match(TokenKind.REF):
            t = self._parse_type(); t.is_ref = True; return t
        if self._match(TokenKind.MUT):
            t = self._parse_type(); t.is_mut = True; return t
        if self._check(TokenKind.LBRACKET):
            return self._parse_array_type()
        return self._parse_type_name()

    def _parse_type_name(self) -> TypeNode:
        tok = self._peek()
        mapping = {
            TokenKind.VOID: "void", TokenKind.I32: "i32", TokenKind.F32: "f32",
            TokenKind.BOOL: "bool", TokenKind.STR: "str",
        }
        if tok.kind in mapping:
            self._advance()
            return TypeNode(mapping[tok.kind])
        if tok.kind in _TYPE_KINDS:
            self._advance()
            return TypeNode(tok.value)
        self._error(f"type attendu, trouve '{tok.value}'")
        return TypeNode("void")

    def _parse_array_type(self) -> TypeNode:
        self._expect(TokenKind.LBRACKET)
        elem = self._parse_type()
        self._expect(TokenKind.SEMI)
        size = int(self._expect(TokenKind.INT).value)
        self._expect(TokenKind.RBRACKET)
        return TypeNode("array", [elem], array_size=size)

    def _parse_block(self) -> List[Stmt]:
        stmts = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_stmt(self) -> Stmt:
        if self._match(TokenKind.LET):
            return self._parse_let()
        if self._match(TokenKind.RETURN):
            val = None if self._check(TokenKind.SEMI) else self._parse_expr()
            self._expect(TokenKind.SEMI)
            return ReturnStmt(val)
        if self._match(TokenKind.IF):
            return self._parse_if()
        if self._match(TokenKind.LOOP):
            return self._parse_loop()
        if self._match(TokenKind.BREAK):
            self._expect(TokenKind.SEMI)
            return BreakStmt()
        if self._match(TokenKind.CONTINUE):
            self._expect(TokenKind.SEMI)
            return ContinueStmt()

        expr = self._parse_expr()
        if self._match(TokenKind.EQ):
            val = self._parse_expr()
            self._expect(TokenKind.SEMI)
            return AssignStmt(expr, val)
        for op, tok in (("+", TokenKind.PLUSEQ), ("-", TokenKind.MINUSEQ),
                        ("*", TokenKind.STAREQ), ("/", TokenKind.SLASHEQ)):
            if self._match(tok):
                rhs = self._parse_expr()
                self._expect(TokenKind.SEMI)
                return AssignStmt(expr, BinaryOp(op, expr, rhs))
        self._expect(TokenKind.SEMI)
        return ExprStmt(expr)

    def _parse_let(self) -> LetStmt:
        is_mut = self._match(TokenKind.MUT)
        name = self._parse_ident("variable")
        typ = None
        if self._match(TokenKind.COLON):
            typ = self._parse_type()
        val = self._parse_expr() if self._match(TokenKind.EQ) else None
        self._expect(TokenKind.SEMI)
        return LetStmt(name, typ, val, is_mut)

    def _parse_if(self) -> IfStmt:
        self._expect(TokenKind.LPAREN)
        cond = self._parse_expr()
        self._expect(TokenKind.RPAREN)
        self._expect(TokenKind.LBRACE)
        then_body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        else_body = None
        if self._match(TokenKind.ELSE):
            self._expect(TokenKind.LBRACE)
            else_body = self._parse_block()
            self._expect(TokenKind.RBRACE)
        return IfStmt(cond, then_body, else_body)

    def _parse_loop(self) -> LoopStmt:
        iterator = None
        if self._check(TokenKind.IDENT) or self._peek().kind in _IDENT_KINDS:
            saved = self.pos
            var = self._parse_ident("variable")
            if self._match(TokenKind.IN):
                iterable = Identifier(self._parse_ident()) if (
                    self._peek().kind in _IDENT_KINDS) else self._parse_expr()
                iterator = (var, iterable)
            else:
                self.pos = saved
        self._expect(TokenKind.LBRACE)
        body = self._parse_block()
        self._expect(TokenKind.RBRACE)
        return LoopStmt(body, iterator)

    def _parse_expr(self) -> Expr:
        return self._parse_or()

    def _parse_or(self) -> Expr:
        left = self._parse_and()
        while self._match(TokenKind.OR):
            left = BinaryOp("||", left, self._parse_and())
        return left

    def _parse_and(self) -> Expr:
        left = self._parse_equality()
        while self._match(TokenKind.AND):
            left = BinaryOp("&&", left, self._parse_equality())
        return left

    def _parse_equality(self) -> Expr:
        left = self._parse_comparison()
        while self._match(TokenKind.EQEQ, TokenKind.NEQ):
            left = BinaryOp(self._previous().value, left, self._parse_comparison())
        return left

    def _parse_comparison(self) -> Expr:
        left = self._parse_term()
        while self._match(TokenKind.LT, TokenKind.GT, TokenKind.LE, TokenKind.GE):
            left = BinaryOp(self._previous().value, left, self._parse_term())
        return left

    def _parse_term(self) -> Expr:
        left = self._parse_factor()
        while self._match(TokenKind.PLUS, TokenKind.MINUS):
            left = BinaryOp(self._previous().value, left, self._parse_factor())
        return left

    def _parse_factor(self) -> Expr:
        left = self._parse_unary()
        while self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            left = BinaryOp(self._previous().value, left, self._parse_unary())
        return left

    def _parse_unary(self) -> Expr:
        if self._match(TokenKind.NOT):
            return UnaryOp("!", self._parse_unary())
        if self._match(TokenKind.MINUS):
            return UnaryOp("-", self._parse_unary())
        return self._parse_postfix()

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()
        while True:
            if self._match(TokenKind.DOT):
                expr = MemberAccess(expr, self._parse_ident("membre"))
            elif self._match(TokenKind.LPAREN):
                args = []
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._parse_expr())
                        if not self._match(TokenKind.COMMA):
                            break
                self._expect(TokenKind.RPAREN)
                expr = CallExpr(expr, args)
            elif self._match(TokenKind.LBRACKET):
                expr = BinaryOp("[]", expr, self._parse_expr())
                self._expect(TokenKind.RBRACKET)
            else:
                break
        return expr

    def _parse_primary(self) -> Expr:
        if self._match(TokenKind.INT):
            return IntLiteral(int(self._previous().value))
        if self._match(TokenKind.FLOAT):
            return FloatLiteral(float(self._previous().value))
        if self._match(TokenKind.TRUE):
            return BoolLiteral(True)
        if self._match(TokenKind.FALSE):
            return BoolLiteral(False)
        if self._match(TokenKind.STRING):
            return StringLiteral(self._previous().value)
        if self._match(TokenKind.LBRACKET):
            return self._parse_array_literal()
        if self._match(TokenKind.SELF):
            return Identifier("self")
        if self._peek().kind in _IDENT_KINDS:
            name = self._parse_ident()
            if self._check(TokenKind.LBRACE) and name and name[0].isupper():
                self._advance()
                fields = {}
                while not self._check(TokenKind.RBRACE):
                    fname = self._parse_ident("champ")
                    self._expect(TokenKind.COLON)
                    fields[fname] = self._parse_expr()
                    self._match(TokenKind.COMMA)
                self._expect(TokenKind.RBRACE)
                return StructInit(name, fields)
            return Identifier(name)
        if self._match(TokenKind.LPAREN):
            e = self._parse_expr()
            self._expect(TokenKind.RPAREN)
            return e
        self._error(f"expression attendue, trouve '{self._peek().value}'")
        return IntLiteral(0)

    def _parse_array_literal(self) -> ArrayLiteral:
        if self._check(TokenKind.RBRACKET):
            self._advance()
            return ArrayLiteral([])
        first = self._parse_expr()
        if self._match(TokenKind.SEMI):
            count = int(self._expect(TokenKind.INT).value)
            self._expect(TokenKind.RBRACKET)
            return ArrayLiteral([], repeat=(first, count))
        elements = [first]
        while self._match(TokenKind.COMMA):
            if self._check(TokenKind.RBRACKET):
                break
            elements.append(self._parse_expr())
        self._expect(TokenKind.RBRACKET)
        return ArrayLiteral(elements)

    def _match(self, *kinds: TokenKind) -> bool:
        for k in kinds:
            if self._check(k):
                self._advance()
                return True
        return False

    def _check(self, kind: TokenKind) -> bool:
        return self._peek().kind == kind if not self._is_at_end() else kind == TokenKind.EOF

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.pos += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().kind == TokenKind.EOF

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def _expect(self, kind: TokenKind) -> Token:
        if self._check(kind):
            return self._advance()
        tok = self._peek()
        self._error(f"'{kind.name}' attendu, trouve '{tok.value}' ({tok.kind.name})")
        return tok

    def _error(self, message: str) -> None:
        tok = self._peek()
        raise ParseError(message, tok.line, tok.col)
