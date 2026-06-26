"""Nœuds AST pour le langage Vyn."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Union


class Visibility(Enum):
    PRIVATE = auto()
    PUBLIC = auto()


@dataclass
class Span:
    line: int
    col: int


@dataclass
class Attribute:
    name: str  # ex: "profile"


@dataclass
class TypeNode:
    name: str
    args: List["TypeNode"] = field(default_factory=list)
    array_size: Optional[int] = None
    is_mut: bool = False
    is_ref: bool = False
    is_own: bool = False


@dataclass
class Param:
    name: str
    type: TypeNode
    is_mut: bool = False


@dataclass
class Field:
    name: str
    type: TypeNode
    is_mut: bool = False


@dataclass
class ExternDecl:
    name: str
    params: List[Param]
    return_type: TypeNode
    abi: str = "C"


@dataclass
class StructDecl:
    name: str
    fields: List[Field]
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class FunctionDecl:
    name: str
    params: List[Param]
    return_type: TypeNode
    body: List["Stmt"]
    is_hot: bool = False
    attributes: List[Attribute] = field(default_factory=list)
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class ImplBlock:
    struct_name: str
    methods: List[FunctionDecl]


@dataclass
class ImportDecl:
    path: str


@dataclass
class UseDecl:
    path: str
    symbols: List[str] = field(default_factory=list)


@dataclass
class EnumVariant:
    name: str
    payload: Optional[TypeNode] = None


@dataclass
class ConstDecl:
    name: str
    type: TypeNode
    value: Expr
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class TypeAliasDecl:
    name: str
    target: TypeNode
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class TraitMethod:
    name: str
    params: List[Param]
    return_type: TypeNode


@dataclass
class TraitDecl:
    name: str
    methods: List[TraitMethod]
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class ModDecl:
    name: str
    functions: List[FunctionDecl] = field(default_factory=list)
    structs: List[StructDecl] = field(default_factory=list)
    enums: List["EnumDecl"] = field(default_factory=list)
    consts: List[ConstDecl] = field(default_factory=list)
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class Program:
    imports: List[ImportDecl]
    uses: List[UseDecl]
    externs: List[ExternDecl]
    structs: List[StructDecl]
    functions: List[FunctionDecl]
    impls: List[ImplBlock]
    enums: List["EnumDecl"] = field(default_factory=list)
    consts: List[ConstDecl] = field(default_factory=list)
    type_aliases: List[TypeAliasDecl] = field(default_factory=list)
    traits: List[TraitDecl] = field(default_factory=list)
    mods: List[ModDecl] = field(default_factory=list)
    init_stmts: List["Stmt"] = field(default_factory=list)


# --- Expressions ---

@dataclass
class IntLiteral:
    value: int


@dataclass
class FloatLiteral:
    value: float


@dataclass
class BoolLiteral:
    value: bool


@dataclass
class StringLiteral:
    value: str


@dataclass
class Identifier:
    name: str


@dataclass
class ArrayLiteral:
    elements: List["Expr"]
    repeat: Optional[tuple["Expr", int]] = None  # [1.0; 500]


@dataclass
class MemberAccess:
    object: "Expr"
    member: str


@dataclass
class CallExpr:
    callee: "Expr"
    args: List["Expr"]


@dataclass
class BinaryOp:
    op: str
    left: "Expr"
    right: "Expr"


@dataclass
class UnaryOp:
    op: str
    operand: "Expr"


@dataclass
class StructInit:
    struct_name: str
    fields: dict[str, "Expr"]


Expr = Union[
    IntLiteral, FloatLiteral, BoolLiteral, StringLiteral,
    Identifier, ArrayLiteral, MemberAccess, CallExpr,
    BinaryOp, UnaryOp, StructInit,
]


# --- Statements ---

@dataclass
class LetStmt:
    name: str
    type: Optional[TypeNode]
    value: Optional[Expr]
    is_mut: bool = False


@dataclass
class AssignStmt:
    target: Expr
    value: Expr


@dataclass
class ReturnStmt:
    value: Optional[Expr]


@dataclass
class ExprStmt:
    expr: Expr


@dataclass
class IfStmt:
    condition: Expr
    then_body: List["Stmt"]
    else_body: Optional[List["Stmt"]] = None


@dataclass
class LoopStmt:
    body: List["Stmt"]
    iterator: Optional[tuple[str, Expr]] = None  # loop val in input


@dataclass
class BreakStmt:
    pass


@dataclass
class EnumDecl:
    name: str
    variants: List[EnumVariant]
    visibility: Visibility = Visibility.PRIVATE


@dataclass
class MatchCase:
    pattern: Optional[Expr]  # None = default/else
    body: List["Stmt"]


@dataclass
class MatchStmt:
    expr: Expr
    cases: List[MatchCase]


@dataclass
class TryStmt:
    body: List["Stmt"]
    catch_var: str
    catch_body: List["Stmt"]


@dataclass
class ThrowStmt:
    value: Expr


@dataclass
class ContinueStmt:
    pass


Stmt = Union[
    LetStmt, AssignStmt, ReturnStmt, ExprStmt,
    IfStmt, LoopStmt, BreakStmt, ContinueStmt, MatchStmt, TryStmt, ThrowStmt,
]
