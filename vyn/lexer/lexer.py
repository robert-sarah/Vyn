"""Analyse lexicale Vyn — version complète avec closures, ranges, generics, char, bitwise, for/while."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List

# BOM UTF-8
_BOM = "\ufeff"


class TokenKind(Enum):
    # ── Littéraux ──────────────────────────────────────────────
    INT        = auto()
    FLOAT      = auto()
    STRING     = auto()
    CHAR       = auto()   # 'a'
    TRUE       = auto()
    FALSE      = auto()
    NIL        = auto()   # nil

    # ── Types primitifs ────────────────────────────────────────
    I8         = auto()
    I16        = auto()
    I32        = auto()
    I64        = auto()
    U8         = auto()
    U16        = auto()
    U32        = auto()
    U64        = auto()
    F32        = auto()
    F64        = auto()
    BOOL       = auto()
    STR        = auto()
    CHAR_TYPE  = auto()   # char (type keyword)
    USIZE      = auto()
    ISIZE      = auto()
    VOID       = auto()

    # ── Mots-clés déclarations ─────────────────────────────────
    LET        = auto()
    MUT        = auto()
    CONST      = auto()
    TYPE       = auto()
    STRUCT     = auto()
    ENUM       = auto()
    FN         = auto()
    PUB        = auto()
    EXTERN     = auto()
    IMPL       = auto()
    TRAIT      = auto()
    MOD        = auto()
    WHERE      = auto()
    AS         = auto()

    # ── Mots-clés ownership ────────────────────────────────────
    OWN        = auto()
    REF        = auto()
    SELF       = auto()
    HOT        = auto()

    # ── Mots-clés flux de contrôle ────────────────────────────
    IF         = auto()
    ELSE       = auto()
    LOOP       = auto()
    FOR        = auto()
    WHILE      = auto()
    BREAK      = auto()
    CONTINUE   = auto()
    RETURN     = auto()
    MATCH      = auto()
    CASE       = auto()
    DEFAULT    = auto()
    IN         = auto()

    # ── Mots-clés erreurs ──────────────────────────────────────
    TRY        = auto()
    CATCH      = auto()
    THROW      = auto()

    # ── Mots-clés async ───────────────────────────────────────
    ASYNC      = auto()
    SYNC       = auto()
    TASK       = auto()
    AWAIT      = auto()

    # ── Mots-clés imports ─────────────────────────────────────
    IMPORT     = auto()
    USE        = auto()

    # ── Option / Result intégrés ──────────────────────────────
    SOME       = auto()
    NONE       = auto()
    OK         = auto()
    ERR        = auto()

    # ── Opérateurs logiques (forme keyword) ───────────────────
    AND        = auto()
    OR         = auto()
    NOT        = auto()

    # ── Identifiants ──────────────────────────────────────────
    IDENT      = auto()

    # ── Symboles / ponctuations ───────────────────────────────
    AT         = auto()   # @
    HASH       = auto()   # #
    QUESTION   = auto()   # ?
    TILDE      = auto()   # ~
    UNDERSCORE = auto()   # _ (wildcard)

    # ── Délimiteurs ───────────────────────────────────────────
    LBRACKET   = auto()   # [
    RBRACKET   = auto()   # ]
    LBRACE     = auto()   # {
    RBRACE     = auto()   # }
    LPAREN     = auto()   # (
    RPAREN     = auto()   # )

    # ── Séparateurs ───────────────────────────────────────────
    SEMI       = auto()   # ;
    COMMA      = auto()   # ,
    COLON      = auto()   # :
    DCOLON     = auto()   # ::
    DOT        = auto()   # .
    DOTDOT     = auto()   # ..
    DOTDOTEQ   = auto()   # ..=

    # ── Flèches ───────────────────────────────────────────────
    ARROW      = auto()   # ->
    FAT_ARROW  = auto()   # =>

    # ── Opérateurs arithmétiques ──────────────────────────────
    PLUS       = auto()   # +
    MINUS      = auto()   # -
    STAR       = auto()   # *
    SLASH      = auto()   # /
    PERCENT    = auto()   # %

    # ── Opérateurs de comparaison ─────────────────────────────
    EQEQ       = auto()   # ==
    NEQ        = auto()   # !=
    LT         = auto()   # <
    GT         = auto()   # >
    LE         = auto()   # <=
    GE         = auto()   # >=

    # ── Opérateurs d'affectation ──────────────────────────────
    EQ         = auto()   # =
    PLUSEQ     = auto()   # +=
    MINUSEQ    = auto()   # -=
    STAREQ     = auto()   # *=
    SLASHEQ    = auto()   # /=
    PERCENTEQ  = auto()   # %=
    ANDEQ      = auto()   # &=
    OREQ       = auto()   # |=
    XOREQ      = auto()   # ^=
    LSHIFTEQ   = auto()   # <<=
    RSHIFTEQ   = auto()   # >>=

    # ── Opérateurs logiques (forme symbole) ───────────────────
    ANDAND     = auto()   # &&
    OROR       = auto()   # ||
    BANG       = auto()   # !

    # ── Opérateurs bitwise ────────────────────────────────────
    AMPERSAND  = auto()   # &
    PIPE       = auto()   # |
    CARET      = auto()   # ^
    LSHIFT     = auto()   # <<
    RSHIFT     = auto()   # >>

    EOF        = auto()


# ─── Table des mots-clés ──────────────────────────────────────────────────────
KEYWORDS: dict[str, TokenKind] = {
    # types primitifs
    "i8":   TokenKind.I8,   "i16":   TokenKind.I16,
    "i32":  TokenKind.I32,  "i64":   TokenKind.I64,
    "u8":   TokenKind.U8,   "u16":   TokenKind.U16,
    "u32":  TokenKind.U32,  "u64":   TokenKind.U64,
    "f32":  TokenKind.F32,  "f64":   TokenKind.F64,
    "bool": TokenKind.BOOL, "str":   TokenKind.STR,
    "char": TokenKind.CHAR_TYPE,
    "usize":TokenKind.USIZE,"isize": TokenKind.ISIZE,
    "void": TokenKind.VOID,
    # déclarations
    "let":    TokenKind.LET,    "mut":    TokenKind.MUT,
    "const":  TokenKind.CONST,  "type":   TokenKind.TYPE,
    "struct": TokenKind.STRUCT, "enum":   TokenKind.ENUM,
    "fn":     TokenKind.FN,     "pub":    TokenKind.PUB,
    "extern": TokenKind.EXTERN, "impl":   TokenKind.IMPL,
    "trait":  TokenKind.TRAIT,  "mod":    TokenKind.MOD,
    "where":  TokenKind.WHERE,  "as":     TokenKind.AS,
    # ownership
    "own":    TokenKind.OWN,    "ref":    TokenKind.REF,
    "self":   TokenKind.SELF,   "hot":    TokenKind.HOT,
    # contrôle
    "if":       TokenKind.IF,       "else":     TokenKind.ELSE,
    "loop":     TokenKind.LOOP,     "for":      TokenKind.FOR,
    "while":    TokenKind.WHILE,    "break":    TokenKind.BREAK,
    "continue": TokenKind.CONTINUE, "return":   TokenKind.RETURN,
    "match":    TokenKind.MATCH,    "case":     TokenKind.CASE,
    "default":  TokenKind.DEFAULT,  "in":       TokenKind.IN,
    # erreurs
    "try":    TokenKind.TRY,    "catch":  TokenKind.CATCH,
    "throw":  TokenKind.THROW,
    # async
    "async":  TokenKind.ASYNC,  "sync":   TokenKind.SYNC,
    "task":   TokenKind.TASK,   "await":  TokenKind.AWAIT,
    # imports
    "import": TokenKind.IMPORT, "use":    TokenKind.USE,
    # option / result
    "Some":   TokenKind.SOME,   "None":   TokenKind.NONE,
    "Ok":     TokenKind.OK,     "Err":    TokenKind.ERR,
    # logique
    "and":    TokenKind.AND,    "or":     TokenKind.OR,
    "not":    TokenKind.NOT,
    # littéraux
    "true":   TokenKind.TRUE,   "false":  TokenKind.FALSE,
    "nil":    TokenKind.NIL,
}


@dataclass
class Token:
    kind:  TokenKind
    value: str
    line:  int
    col:   int

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.value!r}, {self.line}:{self.col})"


@dataclass
class LexError(Exception):
    message: str
    line:    int
    col:     int

    def __str__(self) -> str:
        return f"[Lexer] ligne {self.line}, col {self.col}: {self.message}"


# ─── Lexer principal ──────────────────────────────────────────────────────────
class Lexer:
    """Tokenise du source Vyn (.vyn).

    Commentaires supportés :
      - Ligne  : // … (jusqu'au saut de ligne)
      - Bloc   : /* … */  (imbriqués non supportés)
      - Doc    : /// … (doc-comment, conservé comme token futur)
    """

    # ── Ce qui est ignoré (espaces + commentaires) ───────────────────────────
    _SKIP = re.compile(
        r"(?P<BLOCK_COMMENT>/\*.*?\*/)"
        r"|(?P<LINE_COMMENT>//[^\n]*)"
        r"|(?P<WHITESPACE>[ \t\r\n]+)",
        re.DOTALL,
    )

    # ── Tokens (ordre important : plus longs en premier) ─────────────────────
    _TOKEN = re.compile(
        # ── nombres ──────────────────────────────────────────────────────────
        r"(?P<FLOAT_EXP>\d+\.\d+[eE][+-]?\d+)"
        r"|(?P<FLOAT>\d+\.\d+)"
        r"|(?P<HEXINT>0[xX][0-9a-fA-F]+)"
        r"|(?P<BININT>0[bB][01]+)"
        r"|(?P<OCTINT>0[oO][0-7]+)"
        r"|(?P<INT>\d+)"
        # ── chaînes ──────────────────────────────────────────────────────────
        r'|(?P<STRING>"(?:[^"\\]|\\.)*")'
        r"|(?P<CHAR_LIT>'(?:[^'\\]|\\.)')"
        # ── identifiants / mots-clés ─────────────────────────────────────────
        r"|(?P<IDENT>[a-zA-Z_][a-zA-Z0-9_]*)"
        # ── opérateurs d'affectation composés (3 chars) ──────────────────────
        r"|(?P<LSHIFTEQ><<=)"
        r"|(?P<RSHIFTEQ>>>=)"                # NB : on écrit >>> pour shift droit
        # ── opérateurs d'affectation composés (2 chars) ──────────────────────
        r"|(?P<PLUSEQ>\+=)"
        r"|(?P<MINUSEQ>-=)"
        r"|(?P<STAREQ>\*=)"
        r"|(?P<SLASHEQ>/=)"
        r"|(?P<PERCENTEQ>%=)"
        r"|(?P<ANDEQ>&=)"
        r"|(?P<OREQ>\|=)"
        r"|(?P<XOREQ>\^=)"
        # ── opérateurs logiques double ────────────────────────────────────────
        r"|(?P<ANDAND>&&)"
        r"|(?P<OROR>\|\|)"
        # ── comparaisons ─────────────────────────────────────────────────────
        r"|(?P<EQEQ>==)"
        r"|(?P<NEQ>!=)"
        r"|(?P<LE><=)"
        r"|(?P<GE>>=)"
        r"|(?P<LSHIFT><<)"
        r"|(?P<RSHIFT>>>)"
        # ── flèches ──────────────────────────────────────────────────────────
        r"|(?P<FAT_ARROW>=>)"
        r"|(?P<ARROW>->)"
        # ── range ─────────────────────────────────────────────────────────────
        r"|(?P<DOTDOTEQ>\.\.\=)"
        r"|(?P<DOTDOT>\.\.)"
        # ── double ponctuation ────────────────────────────────────────────────
        r"|(?P<DCOLON>::)"
        # ── symboles simples ──────────────────────────────────────────────────
        r"|(?P<AT>@)"
        r"|(?P<HASH>\#)"
        r"|(?P<QUESTION>\?)"
        r"|(?P<TILDE>~)"
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
        r"|(?P<AMPERSAND>&)"
        r"|(?P<PIPE>\|)"
        r"|(?P<CARET>\^)"
        r"|(?P<BANG>!)"
    )

    def __init__(self, source: str) -> None:
        if source.startswith(_BOM):
            source = source[len(_BOM):]
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1

    # ── API publique ─────────────────────────────────────────────────────────

    def tokenize(self) -> List[Token]:
        """Retourne la liste complète des tokens (inclus EOF)."""
        return list(self._generate())

    # ── Générateur interne ───────────────────────────────────────────────────

    def _generate(self) -> Iterator[Token]:
        while self.pos < len(self.source):
            # sauter espaces et commentaires
            skipped = self._SKIP.match(self.source, self.pos)
            if skipped:
                self._advance_text(skipped.group())
                continue

            m = self._TOKEN.match(self.source, self.pos)
            if not m:
                ch = self.source[self.pos]
                display = (
                    repr(ch) if ch in "\n\r\t\0" or ord(ch) < 32 else f"'{ch}'"
                )
                raise LexError(
                    f"Caractère inattendu {display}", self.line, self.col
                )

            kind_name = m.lastgroup
            text       = m.group()
            start_line = self.line
            start_col  = self.col
            self._advance_text(text)

            tok = self._classify(kind_name, text, start_line, start_col)
            if tok is not None:
                yield tok

        yield Token(TokenKind.EOF, "", self.line, self.col)

    # ── Classification ───────────────────────────────────────────────────────

    def _classify(
        self, kind_name: str, text: str, line: int, col: int
    ) -> Token | None:
        # ── nombres ──────────────────────────────────────────────────────────
        if kind_name in ("FLOAT", "FLOAT_EXP"):
            return Token(TokenKind.FLOAT, text, line, col)
        if kind_name in ("INT",):
            return Token(TokenKind.INT, text, line, col)
        if kind_name == "HEXINT":
            return Token(TokenKind.INT, str(int(text, 16)), line, col)
        if kind_name == "BININT":
            return Token(TokenKind.INT, str(int(text, 2)), line, col)
        if kind_name == "OCTINT":
            return Token(TokenKind.INT, str(int(text, 8)), line, col)

        # ── chaînes et chars ─────────────────────────────────────────────────
        if kind_name == "STRING":
            return Token(TokenKind.STRING, self._decode_string(text[1:-1]), line, col)
        if kind_name == "CHAR_LIT":
            inner = text[1:-1]          # contenu entre les apostrophes
            decoded = self._decode_char(inner)
            return Token(TokenKind.CHAR, decoded, line, col)

        # ── identifiants / mots-clés ─────────────────────────────────────────
        if kind_name == "IDENT":
            # wildcard '_' utilisé comme pattern dans match
            if text == "_":
                return Token(TokenKind.UNDERSCORE, text, line, col)
            kw = KEYWORDS.get(text)
            return Token(kw or TokenKind.IDENT, text, line, col)

        # ── opérateurs d'affectation composés (2-3 chars) ────────────────────
        _ASSIGN_MAP: dict[str, TokenKind] = {
            "PLUSEQ":    TokenKind.PLUSEQ,
            "MINUSEQ":   TokenKind.MINUSEQ,
            "STAREQ":    TokenKind.STAREQ,
            "SLASHEQ":   TokenKind.SLASHEQ,
            "PERCENTEQ": TokenKind.PERCENTEQ,
            "ANDEQ":     TokenKind.ANDEQ,
            "OREQ":      TokenKind.OREQ,
            "XOREQ":     TokenKind.XOREQ,
            "LSHIFTEQ":  TokenKind.LSHIFTEQ,
            "RSHIFTEQ":  TokenKind.RSHIFTEQ,
        }
        if kind_name in _ASSIGN_MAP:
            return Token(_ASSIGN_MAP[kind_name], text, line, col)

        # ── opérateurs logiques double ────────────────────────────────────────
        if kind_name == "ANDAND":
            return Token(TokenKind.ANDAND, text, line, col)
        if kind_name == "OROR":
            return Token(TokenKind.OROR, text, line, col)

        # ── comparaisons et shifts ────────────────────────────────────────────
        _CMP_MAP: dict[str, TokenKind] = {
            "EQEQ":   TokenKind.EQEQ,
            "NEQ":    TokenKind.NEQ,
            "LE":     TokenKind.LE,
            "GE":     TokenKind.GE,
            "LSHIFT": TokenKind.LSHIFT,
            "RSHIFT": TokenKind.RSHIFT,
        }
        if kind_name in _CMP_MAP:
            return Token(_CMP_MAP[kind_name], text, line, col)

        # ── flèches ──────────────────────────────────────────────────────────
        if kind_name == "FAT_ARROW":
            return Token(TokenKind.FAT_ARROW, text, line, col)
        if kind_name == "ARROW":
            return Token(TokenKind.ARROW, text, line, col)

        # ── range ─────────────────────────────────────────────────────────────
        if kind_name == "DOTDOTEQ":
            return Token(TokenKind.DOTDOTEQ, text, line, col)
        if kind_name == "DOTDOT":
            return Token(TokenKind.DOTDOT, text, line, col)

        # ── double-deux-points ────────────────────────────────────────────────
        if kind_name == "DCOLON":
            return Token(TokenKind.DCOLON, text, line, col)

        # ── symboles génériques via TokenKind ────────────────────────────────
        _SIMPLE: dict[str, TokenKind] = {
            "AT":        TokenKind.AT,
            "HASH":      TokenKind.HASH,
            "QUESTION":  TokenKind.QUESTION,
            "TILDE":     TokenKind.TILDE,
            "LBRACKET":  TokenKind.LBRACKET,
            "RBRACKET":  TokenKind.RBRACKET,
            "LBRACE":    TokenKind.LBRACE,
            "RBRACE":    TokenKind.RBRACE,
            "LPAREN":    TokenKind.LPAREN,
            "RPAREN":    TokenKind.RPAREN,
            "SEMI":      TokenKind.SEMI,
            "COMMA":     TokenKind.COMMA,
            "COLON":     TokenKind.COLON,
            "DOT":       TokenKind.DOT,
            "PLUS":      TokenKind.PLUS,
            "MINUS":     TokenKind.MINUS,
            "STAR":      TokenKind.STAR,
            "SLASH":     TokenKind.SLASH,
            "PERCENT":   TokenKind.PERCENT,
            "EQ":        TokenKind.EQ,
            "LT":        TokenKind.LT,
            "GT":        TokenKind.GT,
            "AMPERSAND": TokenKind.AMPERSAND,
            "PIPE":      TokenKind.PIPE,
            "CARET":     TokenKind.CARET,
            "BANG":      TokenKind.BANG,
        }
        if kind_name in _SIMPLE:
            return Token(_SIMPLE[kind_name], text, line, col)

        # cas non géré (ne devrait pas arriver)
        raise LexError(f"Token inconnu: {kind_name!r} ({text!r})", line, col)

    # ── Décodage des chaînes de caractères ────────────────────────────────────

    @staticmethod
    def _decode_string(raw: str) -> str:
        """Interprète les séquences d'échappement dans les chaînes."""
        out: list[str] = []
        i = 0
        escapes = {
            "n": "\n", "t": "\t", "r": "\r",
            "\\": "\\", '"': '"', "'": "'",
            "0": "\0", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
        }
        while i < len(raw):
            if raw[i] == "\\" and i + 1 < len(raw):
                nxt = raw[i + 1]
                if nxt == "u" and i + 5 < len(raw) and raw[i + 2] == "{":
                    # \u{XXXX}
                    end = raw.find("}", i + 3)
                    if end != -1:
                        code_point = int(raw[i + 3:end], 16)
                        out.append(chr(code_point))
                        i = end + 1
                        continue
                if nxt == "x" and i + 3 < len(raw):
                    # \xXX
                    out.append(chr(int(raw[i + 2:i + 4], 16)))
                    i += 4
                    continue
                out.append(escapes.get(nxt, nxt))
                i += 2
            else:
                out.append(raw[i])
                i += 1
        return "".join(out)

    @staticmethod
    def _decode_char(raw: str) -> str:
        """Décode un char littéral (contenu sans apostrophes)."""
        if raw.startswith("\\"):
            escapes = {
                "n": "\n", "t": "\t", "r": "\r",
                "\\": "\\", "'": "'", '"': '"',
                "0": "\0", "a": "\a",
            }
            if len(raw) == 2:
                return escapes.get(raw[1], raw[1])
            if raw[1] == "x" and len(raw) == 4:
                return chr(int(raw[2:], 16))
            if raw[1] == "u" and raw[2] == "{":
                return chr(int(raw[3:-1], 16))
        return raw  # caractère brut

    # ── Avance de position ────────────────────────────────────────────────────

    def _advance_text(self, text: str) -> None:
        for ch in text:
            if ch == "\n":
                self.line += 1
                self.col   = 1
            else:
                self.col += 1
        self.pos += len(text)


# ─── Utilitaire rapide ────────────────────────────────────────────────────────

def tokenize(source: str) -> List[Token]:
    """Raccourci : tokenise une source et retourne la liste."""
    return Lexer(source).tokenize()
