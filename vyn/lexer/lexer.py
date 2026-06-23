"""Analyse lexicale Vyn — équivalent Flex, implémenté en Python."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List

# BOM UTF-8
_BOM = "\ufeff"


class TokenKind(Enum):
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    TRUE = auto()
    FALSE = auto()

    LET = auto()
    MUT = auto()
    CONST = auto()
    TYPE = auto()
    STRUCT = auto()
    ENUM = auto()
    VOID = auto()
    I32 = auto()
    F32 = auto()
    BOOL = auto()
    STR = auto()
    OWN = auto()
    REF = auto()
    FN = auto()
    PUB = auto()
    EXTERN = auto()
    RETURN = auto()
    IMPL = auto()
    TRAIT = auto()
    SELF = auto()
    HOT = auto()
    IF = auto()
    ELSE = auto()
    LOOP = auto()
    BREAK = auto()
    CONTINUE = auto()
    MATCH = auto()
    CASE = auto()
    ASYNC = auto()
    SYNC = auto()
    TASK = auto()
    IMPORT = auto()
    MOD = auto()
    USE = auto()
    TRY = auto()
    CATCH = auto()
    THROW = auto()
    IN = auto()

    IDENT = auto()
    AT = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    LPAREN = auto()
    RPAREN = auto()
    SEMI = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    ARROW = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    EOF = auto()


KEYWORDS = {
    "let": TokenKind.LET, "mut": TokenKind.MUT, "const": TokenKind.CONST,
    "type": TokenKind.TYPE, "struct": TokenKind.STRUCT, "enum": TokenKind.ENUM,
    "void": TokenKind.VOID, "i32": TokenKind.I32, "f32": TokenKind.F32,
    "bool": TokenKind.BOOL, "str": TokenKind.STR, "own": TokenKind.OWN,
    "ref": TokenKind.REF, "fn": TokenKind.FN, "pub": TokenKind.PUB,
    "extern": TokenKind.EXTERN, "return": TokenKind.RETURN, "impl": TokenKind.IMPL,
    "trait": TokenKind.TRAIT, "self": TokenKind.SELF, "hot": TokenKind.HOT,
    "if": TokenKind.IF, "else": TokenKind.ELSE, "loop": TokenKind.LOOP,
    "break": TokenKind.BREAK, "continue": TokenKind.CONTINUE, "match": TokenKind.MATCH,
    "case": TokenKind.CASE, "async": TokenKind.ASYNC, "sync": TokenKind.SYNC,
    "task": TokenKind.TASK, "import": TokenKind.IMPORT, "mod": TokenKind.MOD,
    "use": TokenKind.USE, "try": TokenKind.TRY, "catch": TokenKind.CATCH,
    "throw": TokenKind.THROW, "in": TokenKind.IN,
    "true": TokenKind.TRUE, "false": TokenKind.FALSE,
    "and": TokenKind.AND, "or": TokenKind.OR, "not": TokenKind.NOT,
}


@dataclass
class Token:
    kind: TokenKind
    value: str
    line: int
    col: int


@dataclass
class LexError(Exception):
    message: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"[Lexer] ligne {self.line}, col {self.col}: {self.message}"


class Lexer:
    """Tokenise du source Vyn (.vyn).

    Commentaires supportés :
      - Ligne : // ... (jusqu'au saut de ligne, apostrophes OK)
      - Bloc  : /* ... */
    """

    _SKIP = re.compile(
        r"(?P<BLOCK_COMMENT>/\*.*?\*/)"
        r"|(?P<LINE_COMMENT>//[^\n]*)"
        r"|(?P<WHITESPACE>[ \t\r\n]+)",
        re.DOTALL,
    )

    _TOKEN = re.compile(
        r'(?P<FLOAT>\d+\.\d+(?:[eE][+-]?\d+)?)'
        r"|(?P<INT>\d+)"
        r'|(?P<STRING>"(?:[^"\\]|\\.)*")'
        r"|(?P<IDENT>[a-zA-Z_][a-zA-Z0-9_]*)"
        r"|(?P<PLUSEQ>\+=)"
        r"|(?P<MINUSEQ>-=)"
        r"|(?P<STAREQ>\*=)"
        r"|(?P<SLASHEQ>/=)"
        r"|(?P<EQEQ>==)"
        r"|(?P<NEQ>!=)"
        r"|(?P<LE><=)"
        r"|(?P<GE>>=)"
        r"|(?P<ARROW>->)"
        r"|(?P<AT>@)"
        r"|(?P<LBRACKET>\[)"
        r"|(?P<RBRACKET>\])"
        r"|(?P<LBRACE>\{)"
        r"|(?P<RBRACE>\})"
        r"|(?P<LPAREN>\()"
        r"|(?P<RPAREN>\))"
        r"|(?P<SEMI>;)"
        r"|(?P<COMMA>,)"
        r"|(?P<COLON>:)"
        r"|(?P<DOT>\.)"
        r"|(?P<PLUS>\+)"
        r"|(?P<MINUS>-)"
        r"|(?P<STAR>\*)"
        r"|(?P<SLASH>/)"
        r"|(?P<PERCENT>%)"
        r"|(?P<EQ>=)"
        r"|(?P<LT><)"
        r"|(?P<GT>>)"
    )

    def __init__(self, source: str):
        if source.startswith(_BOM):
            source = source[len(_BOM):]
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> List[Token]:
        return list(self._generate())

    def _generate(self) -> Iterator[Token]:
        while self.pos < len(self.source):
            skipped = self._SKIP.match(self.source, self.pos)
            if skipped:
                self._advance_text(skipped.group())
                continue

            m = self._TOKEN.match(self.source, self.pos)
            if not m:
                ch = self.source[self.pos]
                display = repr(ch) if ch in "\n\r\t\0" or ord(ch) < 32 else f"'{ch}'"
                raise LexError(f"Caractère inattendu {display}", self.line, self.col)

            kind_name = m.lastgroup
            text = m.group()
            start_line, start_col = self.line, self.col
            self._advance_text(text)

            if kind_name == "IDENT":
                kw = KEYWORDS.get(text)
                yield Token(kw or TokenKind.IDENT, text, start_line, start_col)
            elif kind_name == "INT":
                yield Token(TokenKind.INT, text, start_line, start_col)
            elif kind_name == "FLOAT":
                yield Token(TokenKind.FLOAT, text, start_line, start_col)
            elif kind_name == "STRING":
                yield Token(TokenKind.STRING, text[1:-1], start_line, start_col)
            else:
                yield Token(TokenKind[kind_name], text, start_line, start_col)

        yield Token(TokenKind.EOF, "", self.line, self.col)

    def _advance_text(self, text: str) -> None:
        for ch in text:
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        self.pos += len(text)
