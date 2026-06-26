"""Nœuds AST Vyn — version complète : closures, tuples, ranges, generics, for/while, Option/Result, cast, char, guards."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


# ─── Visibilité ──────────────────────────────────────────────────────────────

class Visibility(Enum):
    PRIVATE = auto()
    PUBLIC  = auto()


# ─── Span (position dans le source) ─────────────────────────────────────────

@dataclass
class Span:
    line: int = 0
    col:  int = 0

    def __repr__(self) -> str:
        return f"{self.line}:{self.col}"


# ─── Attributs ───────────────────────────────────────────────────────────────

@dataclass
class Attribute:
    """@[name] ou @[name(arg1, arg2)]"""
    name: str
    args: List[str] = field(default_factory=list)


# ─── Types ───────────────────────────────────────────────────────────────────

@dataclass
class TypeNode:
    """Représentation d'un type dans l'AST.

    Exemples :
      i32                   → TypeNode("i32")
      f32[]                 → TypeNode("array", args=[TypeNode("f32")])
      Vec<i32>              → TypeNode("Vec", args=[TypeNode("i32")])
      HashMap<str, i32>     → TypeNode("HashMap", args=[TypeNode("str"), TypeNode("i32")])
      fn(i32, f32) -> bool  → TypeNode("fn", args=[TypeNode("i32"), TypeNode("f32"), TypeNode("bool")])
      (i32, str)            → TypeNode("tuple", args=[TypeNode("i32"), TypeNode("str")])
      Option<i32>           → TypeNode("Option", args=[TypeNode("i32")])
      Result<i32, str>      → TypeNode("Result", args=[TypeNode("i32"), TypeNode("str")])
      &i32                  → TypeNode("ref", args=[TypeNode("i32")])
      mut i32               → TypeNode("i32", is_mut=True)
      T                     → TypeNode("T")          # type variable
    """
    name:       str
    args:       List["TypeNode"]  = field(default_factory=list)
    array_size: Optional[int]     = None    # taille statique [N]
    is_mut:     bool              = False
    is_ref:     bool              = False
    is_own:     bool              = False
    is_ptr:     bool              = False   # pointeur brut *T
    nullable:   bool              = False   # T?  (syntaxe courte pour Option<T>)
    span:       Span              = field(default_factory=Span)

    # ── helpers ──────────────────────────────────────────────────────────────
    def is_primitive(self) -> bool:
        return self.name in {
            "i8","i16","i32","i64",
            "u8","u16","u32","u64",
            "f32","f64","bool","str","char","void","usize","isize",
        }

    def is_numeric(self) -> bool:
        return self.name in {
            "i8","i16","i32","i64",
            "u8","u16","u32","u64",
            "f32","f64","usize","isize",
        }

    def is_integer(self) -> bool:
        return self.name in {
            "i8","i16","i32","i64",
            "u8","u16","u32","u64",
            "usize","isize",
        }

    def is_float(self) -> bool:
        return self.name in ("f32", "f64")

    def is_generic(self) -> bool:
        """True si le nom est une variable de type (convention : lettre majuscule unique ou T/U/V/K/V)."""
        return len(self.name) == 1 and self.name.isupper()

    def __str__(self) -> str:
        base = self.name
        if self.args:
            if self.name == "fn":
                params = ", ".join(str(a) for a in self.args[:-1])
                ret    = str(self.args[-1])
                base   = f"fn({params}) -> {ret}"
            elif self.name == "tuple":
                base = "(" + ", ".join(str(a) for a in self.args) + ")"
            elif self.name == "array":
                inner = str(self.args[0])
                base  = f"{inner}[{self.array_size or ''}]"
            else:
                base  = f"{self.name}<{', '.join(str(a) for a in self.args)}>"
        if self.is_ref:
            base = f"&{base}"
        if self.is_own:
            base = f"own {base}"
        if self.is_mut:
            base = f"mut {base}"
        if self.nullable:
            base = f"{base}?"
        return base


# ─── Paramètres et champs ─────────────────────────────────────────────────────

@dataclass
class Param:
    name:   str
    type:   TypeNode
    is_mut: bool  = False
    default: Optional["Expr"] = None   # valeur par défaut
    span:   Span  = field(default_factory=Span)


@dataclass
class GenericParam:
    """Paramètre générique : fn foo<T: Trait>(…)"""
    name:   str                        # "T"
    bounds: List[str] = field(default_factory=list)  # ["Clone", "Debug"]
    span:   Span      = field(default_factory=Span)


@dataclass
class Field:
    name:   str
    type:   TypeNode
    is_mut: bool     = False
    visibility: Visibility = Visibility.PRIVATE
    default: Optional["Expr"] = None
    span:   Span     = field(default_factory=Span)


# ─── Déclarations top-level ───────────────────────────────────────────────────

@dataclass
class ExternDecl:
    name:        str
    params:      List[Param]
    return_type: TypeNode
    abi:         str  = "C"
    span:        Span = field(default_factory=Span)


@dataclass
class StructDecl:
    name:           str
    fields:         List[Field]
    generics:       List[GenericParam] = field(default_factory=list)
    visibility:     Visibility         = Visibility.PRIVATE
    attributes:     List[Attribute]    = field(default_factory=list)
    span:           Span               = field(default_factory=Span)


@dataclass
class EnumVariant:
    name:    str
    payload: Optional[TypeNode] = None   # Some(i32)  →  payload=TypeNode("i32")
    fields:  List[Field]        = field(default_factory=list)  # struct variant
    span:    Span               = field(default_factory=Span)


@dataclass
class EnumDecl:
    name:       str
    variants:   List[EnumVariant]
    generics:   List[GenericParam] = field(default_factory=list)
    visibility: Visibility         = Visibility.PRIVATE
    attributes: List[Attribute]    = field(default_factory=list)
    span:       Span               = field(default_factory=Span)


@dataclass
class TraitMethod:
    name:        str
    params:      List[Param]
    return_type: TypeNode
    generics:    List[GenericParam] = field(default_factory=list)
    default_body: Optional[List["Stmt"]] = None  # méthode par défaut
    span:        Span               = field(default_factory=Span)


@dataclass
class TraitDecl:
    name:       str
    methods:    List[TraitMethod]
    generics:   List[GenericParam] = field(default_factory=list)
    bounds:     List[str]          = field(default_factory=list)  # : Clone + Debug
    visibility: Visibility         = Visibility.PRIVATE
    span:       Span               = field(default_factory=Span)


@dataclass
class ImplDecl:
    """impl Struct { … }  ou  impl Trait for Struct { … }"""
    struct_name:  str
    trait_name:   Optional[str]        = None
    methods:      List["FunctionDecl"] = field(default_factory=list)
    generics:     List[GenericParam]   = field(default_factory=list)
    span:         Span                 = field(default_factory=Span)

# Alias rétro-compat
ImplBlock = ImplDecl


@dataclass
class FunctionDecl:
    name:        str
    params:      List[Param]
    return_type: TypeNode
    body:        List["Stmt"]
    is_hot:      bool              = False
    is_async:    bool              = False
    is_extern:   bool              = False
    generics:    List[GenericParam]= field(default_factory=list)
    attributes:  List[Attribute]   = field(default_factory=list)
    visibility:  Visibility        = Visibility.PRIVATE
    span:        Span              = field(default_factory=Span)


@dataclass
class ConstDecl:
    name:       str
    type:       TypeNode
    value:      "Expr"
    visibility: Visibility = Visibility.PRIVATE
    span:       Span       = field(default_factory=Span)


@dataclass
class TypeAliasDecl:
    name:       str
    target:     TypeNode
    generics:   List[GenericParam] = field(default_factory=list)
    visibility: Visibility         = Visibility.PRIVATE
    span:       Span               = field(default_factory=Span)


@dataclass
class ImportDecl:
    path: str
    alias: Optional[str] = None   # import std.io as io
    span: Span = field(default_factory=Span)


@dataclass
class UseDecl:
    path:    str
    symbols: List[str] = field(default_factory=list)
    alias:   Optional[str] = None
    span:    Span = field(default_factory=Span)


@dataclass
class ModDecl:
    name:       str
    functions:  List[FunctionDecl]  = field(default_factory=list)
    structs:    List[StructDecl]    = field(default_factory=list)
    enums:      List[EnumDecl]      = field(default_factory=list)
    consts:     List[ConstDecl]     = field(default_factory=list)
    impls:      List[ImplDecl]      = field(default_factory=list)
    visibility: Visibility          = Visibility.PRIVATE
    span:       Span                = field(default_factory=Span)


# ─── Programme (racine de l'AST) ──────────────────────────────────────────────

@dataclass
class Program:
    imports:      List[ImportDecl]
    uses:         List[UseDecl]
    externs:      List[ExternDecl]
    structs:      List[StructDecl]
    functions:    List[FunctionDecl]
    impls:        List[ImplDecl]
    enums:        List[EnumDecl]          = field(default_factory=list)
    consts:       List[ConstDecl]         = field(default_factory=list)
    type_aliases: List[TypeAliasDecl]     = field(default_factory=list)
    traits:       List[TraitDecl]         = field(default_factory=list)
    mods:         List[ModDecl]           = field(default_factory=list)
    init_stmts:   List["Stmt"]            = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPRESSIONS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Littéraux ────────────────────────────────────────────────────────────────

@dataclass
class IntLiteral:
    value: int
    span:  Span = field(default_factory=Span)


@dataclass
class FloatLiteral:
    value: float
    span:  Span = field(default_factory=Span)


@dataclass
class BoolLiteral:
    value: bool
    span:  Span = field(default_factory=Span)


@dataclass
class StringLiteral:
    value: str
    span:  Span = field(default_factory=Span)


@dataclass
class CharLiteral:
    """Littéral caractère : 'a', '\n', '\u{1F600}'"""
    value: str   # la chaîne Python de longueur 1
    span:  Span = field(default_factory=Span)


@dataclass
class NilLiteral:
    """Valeur nulle : nil"""
    span: Span = field(default_factory=Span)


# ─── Identifiant ─────────────────────────────────────────────────────────────

@dataclass
class Identifier:
    name: str
    span: Span = field(default_factory=Span)


# ─── Option / Result constructeurs ───────────────────────────────────────────

@dataclass
class SomeExpr:
    """Some(expr)"""
    value: "Expr"
    span:  Span = field(default_factory=Span)


@dataclass
class NoneExpr:
    """None"""
    span: Span = field(default_factory=Span)


@dataclass
class OkExpr:
    """Ok(expr)"""
    value: "Expr"
    span:  Span = field(default_factory=Span)


@dataclass
class ErrExpr:
    """Err(expr)"""
    value: "Expr"
    span:  Span = field(default_factory=Span)


# ─── Collections ─────────────────────────────────────────────────────────────

@dataclass
class ArrayLiteral:
    elements: List["Expr"]
    repeat:   Optional[tuple["Expr", int]] = None   # [val; N]
    span:     Span = field(default_factory=Span)


@dataclass
class TupleExpr:
    """(expr1, expr2, …)"""
    elements: List["Expr"]
    span:     Span = field(default_factory=Span)


@dataclass
class TupleIndex:
    """tuple.0 , tuple.1 …"""
    object: "Expr"
    index:  int
    span:   Span = field(default_factory=Span)


@dataclass
class MapLiteral:
    """#{key: value, …}  — littéral HashMap"""
    entries: List[tuple["Expr", "Expr"]]
    span:    Span = field(default_factory=Span)


# ─── Accès membres & appels ───────────────────────────────────────────────────

@dataclass
class MemberAccess:
    object: "Expr"
    member: str
    span:   Span = field(default_factory=Span)


@dataclass
class IndexExpr:
    """array[index]"""
    object: "Expr"
    index:  "Expr"
    span:   Span = field(default_factory=Span)


@dataclass
class CallExpr:
    callee:        "Expr"
    args:          List["Expr"]
    generic_args:  List[TypeNode] = field(default_factory=list)  # foo::<i32>(...)
    span:          Span           = field(default_factory=Span)


@dataclass
class MethodCall:
    """obj.method(args) — variante explicite pour différencier de MemberAccess."""
    object:        "Expr"
    method:        str
    args:          List["Expr"]
    generic_args:  List[TypeNode] = field(default_factory=list)
    span:          Span           = field(default_factory=Span)


# ─── Opérateurs ──────────────────────────────────────────────────────────────

@dataclass
class BinaryOp:
    op:    str    # "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
                  # "&&", "||", "&", "|", "^", "<<", ">>"
    left:  "Expr"
    right: "Expr"
    span:  Span = field(default_factory=Span)


@dataclass
class UnaryOp:
    op:      str    # "-", "!", "~", "&", "*"
    operand: "Expr"
    span:    Span = field(default_factory=Span)


@dataclass
class CastExpr:
    """expr as Type"""
    expr: "Expr"
    to:   TypeNode
    span: Span = field(default_factory=Span)


@dataclass
class RangeExpr:
    """start..end  (exclusive) ou  start..=end  (inclusive)"""
    start:     "Expr"
    end:       "Expr"
    inclusive: bool  = False
    span:      Span  = field(default_factory=Span)


@dataclass
class QuestionExpr:
    """expr?  — propagation d'erreur (Result/Option)"""
    expr: "Expr"
    span: Span = field(default_factory=Span)


# ─── Closures ────────────────────────────────────────────────────────────────

@dataclass
class ClosureParam:
    name:   str
    type:   Optional[TypeNode] = None   # optionnel : inféré si absent
    is_mut: bool               = False
    span:   Span               = field(default_factory=Span)


@dataclass
class ClosureExpr:
    """|params| -> ret_type { body }   ou   |params| expr"""
    params:      List[ClosureParam]
    return_type: Optional[TypeNode]    = None
    body:        Optional[List["Stmt"]]= None   # bloc { ... }
    expr:        Optional["Expr"]      = None   # expression courte
    span:        Span                  = field(default_factory=Span)


# ─── Struct init ─────────────────────────────────────────────────────────────

@dataclass
class StructInit:
    struct_name: str
    fields:      Dict[str, "Expr"]
    span:        Span = field(default_factory=Span)


# ─── If expression (if expr { … } else { … } utilisé comme expression) ───────

@dataclass
class IfExpr:
    condition:  "Expr"
    then_expr:  "Expr"
    else_expr:  "Expr"
    span:       Span = field(default_factory=Span)


# ─── Type Expr ────────────────────────────────────────────────────────────────

Expr = Union[
    # littéraux
    IntLiteral, FloatLiteral, BoolLiteral, StringLiteral, CharLiteral, NilLiteral,
    # identifiant
    Identifier,
    # option / result
    SomeExpr, NoneExpr, OkExpr, ErrExpr,
    # collections
    ArrayLiteral, TupleExpr, TupleIndex, MapLiteral,
    # accès
    MemberAccess, IndexExpr, CallExpr, MethodCall,
    # opérateurs
    BinaryOp, UnaryOp, CastExpr, RangeExpr, QuestionExpr,
    # closures
    ClosureExpr,
    # struct
    StructInit,
    # if expr
    IfExpr,
]


# ═══════════════════════════════════════════════════════════════════════════════
#  STATEMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LetStmt:
    name:   str
    type:   Optional[TypeNode]
    value:  Optional[Expr]
    is_mut: bool  = False
    span:   Span  = field(default_factory=Span)


@dataclass
class LetTupleStmt:
    """Destructuration : let (a, b, c) = tuple_expr;"""
    names:  List[str]
    type:   Optional[TypeNode]
    value:  Expr
    is_mut: bool = False
    span:   Span = field(default_factory=Span)


@dataclass
class AssignStmt:
    target: Expr
    value:  Expr
    op:     str  = "="   # "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^="
    span:   Span = field(default_factory=Span)


@dataclass
class ReturnStmt:
    value: Optional[Expr]
    span:  Span = field(default_factory=Span)


@dataclass
class ExprStmt:
    expr: Expr
    span: Span = field(default_factory=Span)


# ─── Conditionnelles ─────────────────────────────────────────────────────────

@dataclass
class IfStmt:
    condition: Expr
    then_body: List["Stmt"]
    else_body: Optional[List["Stmt"]] = None
    span:      Span                   = field(default_factory=Span)


@dataclass
class IfLetStmt:
    """if let Some(x) = expr { … } else { … }"""
    pattern:   "Pattern"
    value:     Expr
    then_body: List["Stmt"]
    else_body: Optional[List["Stmt"]] = None
    span:      Span                   = field(default_factory=Span)


# ─── Boucles ─────────────────────────────────────────────────────────────────

@dataclass
class LoopStmt:
    """loop { … }  ou  loop var in iterable { … }"""
    body:     List["Stmt"]
    iterator: Optional[tuple[str, Expr]] = None
    label:    Optional[str]              = None   # 'outer: loop { ... }
    span:     Span                       = field(default_factory=Span)


@dataclass
class WhileStmt:
    """while condition { … }"""
    condition: Expr
    body:      List["Stmt"]
    label:     Optional[str] = None
    span:      Span          = field(default_factory=Span)


@dataclass
class ForStmt:
    """for variable in iterable { … }"""
    var:      str
    var_type: Optional[TypeNode]
    iterable: Expr
    body:     List["Stmt"]
    label:    Optional[str] = None
    span:     Span          = field(default_factory=Span)


@dataclass
class BreakStmt:
    label: Optional[str] = None
    value: Optional[Expr] = None   # break expr;  (valeur d'une boucle)
    span:  Span           = field(default_factory=Span)


@dataclass
class ContinueStmt:
    label: Optional[str] = None
    span:  Span          = field(default_factory=Span)


# ─── Pattern Matching ────────────────────────────────────────────────────────

@dataclass
class WildcardPattern:
    """_ — wildcard"""
    span: Span = field(default_factory=Span)


@dataclass
class LiteralPattern:
    """42, "hello", true, 'a'"""
    value: Expr
    span:  Span = field(default_factory=Span)


@dataclass
class IdentPattern:
    """x — capture dans une variable"""
    name:   str
    is_mut: bool = False
    span:   Span = field(default_factory=Span)


@dataclass
class EnumPattern:
    """Color::Red ou Some(x) ou None"""
    enum_name:    str
    variant_name: str
    payload:      Optional["Pattern"] = None
    span:         Span                = field(default_factory=Span)


@dataclass
class TuplePattern:
    """(a, b, c)"""
    elements: List["Pattern"]
    span:     Span = field(default_factory=Span)


@dataclass
class StructPattern:
    """Struct { field: pat, … }"""
    struct_name: str
    fields:      Dict[str, "Pattern"]
    rest:        bool = False   # .. (ignorer les champs restants)
    span:        Span = field(default_factory=Span)


@dataclass
class OrPattern:
    """pat1 | pat2 | pat3"""
    patterns: List["Pattern"]
    span:     Span = field(default_factory=Span)


@dataclass
class RangePattern:
    """1..=5"""
    start:     Expr
    end:       Expr
    inclusive: bool = True
    span:      Span = field(default_factory=Span)


Pattern = Union[
    WildcardPattern, LiteralPattern, IdentPattern,
    EnumPattern, TuplePattern, StructPattern,
    OrPattern, RangePattern,
]


@dataclass
class MatchArm:
    """Une branche de match : pattern [if guard] => { body }"""
    pattern:  Pattern
    guard:    Optional[Expr]    = None    # if condition
    body:     List["Stmt"]      = field(default_factory=list)
    span:     Span              = field(default_factory=Span)


# Alias rétro-compat
@dataclass
class MatchCase:
    pattern:  Optional[Expr]   # None = default/else (legacy)
    body:     List["Stmt"]
    guard:    Optional[Expr]   = None
    span:     Span             = field(default_factory=Span)


@dataclass
class MatchStmt:
    expr:  Expr
    arms:  List[MatchArm]         = field(default_factory=list)
    cases: List[MatchCase]        = field(default_factory=list)   # legacy
    span:  Span                   = field(default_factory=Span)


# ─── Gestion d'erreurs ───────────────────────────────────────────────────────

@dataclass
class TryStmt:
    body:       List["Stmt"]
    catch_var:  str
    catch_body: List["Stmt"]
    finally_body: List["Stmt"] = field(default_factory=list)
    span:       Span           = field(default_factory=Span)


@dataclass
class ThrowStmt:
    value: Expr
    span:  Span = field(default_factory=Span)


# ─── Déclarations locales ────────────────────────────────────────────────────

@dataclass
class LocalFnStmt:
    """Fonction définie à l'intérieur d'un bloc (closure nommée)."""
    decl: FunctionDecl
    span: Span = field(default_factory=Span)


# ─── Type Stmt ───────────────────────────────────────────────────────────────

Stmt = Union[
    LetStmt, LetTupleStmt, AssignStmt, ReturnStmt, ExprStmt,
    IfStmt, IfLetStmt,
    LoopStmt, WhileStmt, ForStmt,
    BreakStmt, ContinueStmt,
    MatchStmt,
    TryStmt, ThrowStmt,
    LocalFnStmt,
]


# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def make_void() -> TypeNode:
    return TypeNode("void")


def make_i32() -> TypeNode:
    return TypeNode("i32")


def make_f32() -> TypeNode:
    return TypeNode("f32")


def make_bool() -> TypeNode:
    return TypeNode("bool")


def make_str() -> TypeNode:
    return TypeNode("str")


def make_option(inner: TypeNode) -> TypeNode:
    return TypeNode("Option", args=[inner])


def make_result(ok: TypeNode, err: TypeNode) -> TypeNode:
    return TypeNode("Result", args=[ok, err])


def make_array(inner: TypeNode, size: Optional[int] = None) -> TypeNode:
    t = TypeNode("array", args=[inner])
    t.array_size = size
    return t


def make_tuple(*types: TypeNode) -> TypeNode:
    return TypeNode("tuple", args=list(types))


def make_fn_type(param_types: List[TypeNode], ret: TypeNode) -> TypeNode:
    return TypeNode("fn", args=list(param_types) + [ret])


def literal_span(tok_line: int, tok_col: int) -> Span:
    return Span(tok_line, tok_col)
