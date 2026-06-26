"""Borrow checker statique Vyn — move semantics, lifetimes, règles d'emprunt."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

from vyn.ast.nodes import (
    Program, FunctionDecl, ImplDecl, Stmt, Expr,
    LetStmt, AssignStmt, ReturnStmt, ExprStmt,
    IfStmt, IfLetStmt, WhileStmt, ForStmt, LoopStmt,
    BreakStmt, ContinueStmt, MatchStmt, TryStmt, ThrowStmt,
    LocalFnStmt, LetTupleStmt,
    Identifier, MemberAccess, IndexExpr, CallExpr, BinaryOp, UnaryOp,
    ClosureExpr, StructInit, ArrayLiteral, TupleExpr,
    SomeExpr, OkExpr, ErrExpr, QuestionExpr, CastExpr, RangeExpr,
    TypeNode,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  États d'une valeur dans la portée
# ═══════════════════════════════════════════════════════════════════════════════

class ValueState(Enum):
    OWNED      = auto()   # valeur possédée, non déplacée
    MOVED      = auto()   # valeur déplacée (use-after-move interdit)
    BORROWED   = auto()   # référence partagée active
    MUT_BORROW = auto()   # référence mutable active
    DROPPED    = auto()   # hors de portée


# ═══════════════════════════════════════════════════════════════════════════════
#  Entrée dans le tableau de borrow
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BorrowEntry:
    name:      str
    state:     ValueState = ValueState.OWNED
    is_mut:    bool       = False
    is_own:    bool       = False   # type own T
    borrow_count: int     = 0       # nb d'emprunts partagés actifs
    mut_borrow:   bool    = False   # emprunt mutable actif
    defined_at:   int     = 0       # numéro de ligne AST (approximatif)

    def is_readable(self) -> bool:
        return self.state not in (ValueState.MOVED, ValueState.DROPPED)

    def is_writable(self) -> bool:
        return (self.state not in (ValueState.MOVED, ValueState.DROPPED)
                and self.is_mut
                and self.borrow_count == 0)

    def can_move(self) -> bool:
        return self.state == ValueState.OWNED and self.borrow_count == 0

    def can_borrow(self) -> bool:
        return self.state not in (ValueState.MOVED, ValueState.DROPPED) and not self.mut_borrow

    def can_mut_borrow(self) -> bool:
        return (self.state not in (ValueState.MOVED, ValueState.DROPPED)
                and self.borrow_count == 0
                and not self.mut_borrow
                and self.is_mut)


# ═══════════════════════════════════════════════════════════════════════════════
#  Erreur de borrow
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BorrowError:
    message:  str
    line:     int = 0
    col:      int = 0
    severity: str = "error"   # "error" | "warning"

    def __str__(self) -> str:
        loc = f"ligne {self.line}, col {self.col}: " if self.line else ""
        return f"[Borrow] {loc}{self.message}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Portée d'emprunt (scope)
# ═══════════════════════════════════════════════════════════════════════════════

class BorrowScope:
    """Tableau de symboles pour le borrow checker, à portée lexicale."""

    def __init__(self, parent: Optional["BorrowScope"] = None):
        self._vars:   Dict[str, BorrowEntry] = {}
        self._parent: Optional["BorrowScope"] = parent

    # ── accès ────────────────────────────────────────────────────────────────

    def define(self, name: str, is_mut: bool = False, is_own: bool = False,
               line: int = 0) -> BorrowEntry:
        entry = BorrowEntry(name, ValueState.OWNED, is_mut, is_own, defined_at=line)
        self._vars[name] = entry
        return entry

    def lookup(self, name: str) -> Optional[BorrowEntry]:
        if name in self._vars:
            return self._vars[name]
        if self._parent:
            return self._parent.lookup(name)
        return None

    def local_names(self) -> Set[str]:
        return set(self._vars.keys())

    # ── mutations d'état ──────────────────────────────────────────────────────

    def mark_moved(self, name: str) -> None:
        e = self.lookup(name)
        if e:
            e.state = ValueState.MOVED

    def mark_borrowed(self, name: str) -> None:
        e = self.lookup(name)
        if e:
            e.borrow_count += 1
            e.state = ValueState.BORROWED

    def release_borrow(self, name: str) -> None:
        e = self.lookup(name)
        if e and e.borrow_count > 0:
            e.borrow_count -= 1
            if e.borrow_count == 0:
                e.state = ValueState.OWNED

    def mark_mut_borrow(self, name: str) -> None:
        e = self.lookup(name)
        if e:
            e.mut_borrow = True
            e.state = ValueState.MUT_BORROW

    def release_mut_borrow(self, name: str) -> None:
        e = self.lookup(name)
        if e and e.mut_borrow:
            e.mut_borrow = False
            e.state = ValueState.OWNED

    def drop_all(self) -> None:
        """Marque toutes les variables locales comme droppées."""
        for e in self._vars.values():
            e.state = ValueState.DROPPED


# ═══════════════════════════════════════════════════════════════════════════════
#  Borrow Checker principal
# ═══════════════════════════════════════════════════════════════════════════════

class BorrowChecker:
    """Analyse statique d'ownership et d'emprunt pour Vyn.

    Règles vérifiées :
    1. Pas d'utilisation après move (use-after-move)
    2. Pas d'assignation à une variable immutable
    3. Pas d'assignation à une constante
    4. Une seule référence mutable active à la fois
    5. Pas de référence mutable + référence partagée simultanées
    6. Les valeurs `own T` sont déplacées, pas copiées
    7. Les types `Copy` (i32, f32, bool, char, …) sont copiés, pas déplacés
    """

    COPY_TYPES: Set[str] = {
        "i8","i16","i32","i64",
        "u8","u16","u32","u64",
        "f32","f64","bool","char","usize","isize",
    }

    def __init__(self) -> None:
        self.errors:   List[BorrowError] = []
        self.warnings: List[BorrowError] = []
        self._scope:   BorrowScope       = BorrowScope()
        self._consts:  Set[str]          = set()
        self._return_type: Optional[TypeNode] = None

    # ── API publique ──────────────────────────────────────────────────────────

    def check_program(self, program: Program) -> List[BorrowError]:
        """Point d'entrée : vérifie tout le programme."""
        self.errors.clear()
        self.warnings.clear()

        # Enregistrer les constantes
        for c in program.consts:
            self._consts.add(c.name)

        # Vérifier chaque fonction top-level
        for fn in program.functions:
            self._check_function(fn)

        # Vérifier les impl
        for impl in program.impls:
            for m in impl.methods:
                self._check_function(m)

        # Instructions init (script)
        for stmt in program.init_stmts:
            self._check_stmt(stmt)

        return self.errors

    def check_function(self, fn: FunctionDecl) -> List[BorrowError]:
        """Vérifie une seule fonction."""
        self.errors.clear()
        self._check_function(fn)
        return self.errors

    # ── Fonctions ─────────────────────────────────────────────────────────────

    def _check_function(self, fn: FunctionDecl) -> None:
        outer = self._scope
        self._scope = BorrowScope(outer)
        saved_ret = self._return_type
        self._return_type = fn.return_type

        # Définir les paramètres dans la portée
        for p in fn.params:
            is_own = getattr(p.type, "is_own", False)
            self._scope.define(p.name, p.is_mut, is_own)

        for stmt in fn.body:
            self._check_stmt(stmt)

        self._scope.drop_all()
        self._scope = outer
        self._return_type = saved_ret

    # ── Statements ────────────────────────────────────────────────────────────

    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, LetStmt):
            self._check_let(stmt)
        elif isinstance(stmt, LetTupleStmt):
            self._check_let_tuple(stmt)
        elif isinstance(stmt, AssignStmt):
            self._check_assign(stmt)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._check_expr_read(stmt.value)
        elif isinstance(stmt, ExprStmt):
            self._check_expr_read(stmt.expr)
        elif isinstance(stmt, IfStmt):
            self._check_if(stmt)
        elif isinstance(stmt, IfLetStmt):
            self._check_expr_read(stmt.value)
            self._in_scope(stmt.then_body)
            if stmt.else_body:
                self._in_scope(stmt.else_body)
        elif isinstance(stmt, WhileStmt):
            self._check_expr_read(stmt.condition)
            self._in_scope(stmt.body)
        elif isinstance(stmt, ForStmt):
            self._check_expr_read(stmt.iterable)
            inner = BorrowScope(self._scope)
            inner.define(stmt.var, False, False)
            self._with_scope(inner, stmt.body)
        elif isinstance(stmt, LoopStmt):
            if stmt.iterator:
                var, it = stmt.iterator
                self._check_expr_read(it)
                inner = BorrowScope(self._scope)
                inner.define(var, False, False)
                self._with_scope(inner, stmt.body)
            else:
                self._in_scope(stmt.body)
        elif isinstance(stmt, MatchStmt):
            self._check_expr_read(stmt.expr)
            for arm in stmt.arms:
                # Les variables liées dans le pattern sont définies dans le corps
                self._check_match_arm_body(arm.body, arm.guard)
            # Legacy cases
            if not stmt.arms:
                for case in stmt.cases:
                    if case.pattern:
                        self._check_expr_read(case.pattern)
                    self._in_scope(case.body)
        elif isinstance(stmt, TryStmt):
            self._in_scope(stmt.body)
            inner = BorrowScope(self._scope)
            inner.define(stmt.catch_var, False, False)
            self._with_scope(inner, stmt.catch_body)
            if stmt.finally_body:
                self._in_scope(stmt.finally_body)
        elif isinstance(stmt, ThrowStmt):
            self._check_expr_read(stmt.value)
        elif isinstance(stmt, LocalFnStmt):
            self._check_function(stmt.decl)
        elif isinstance(stmt, (BreakStmt, ContinueStmt)):
            pass

    def _check_let(self, stmt: LetStmt) -> None:
        if stmt.value:
            self._check_expr_read(stmt.value)
            # Si la valeur est un identifiant own → move
            if isinstance(stmt.value, Identifier):
                entry = self._scope.lookup(stmt.value.name)
                if entry and entry.is_own:
                    if not entry.can_move():
                        self._err(f"impossible de déplacer '{stmt.value.name}' : déjà déplacé ou emprunté")
                    else:
                        self._scope.mark_moved(stmt.value.name)
        is_own = bool(stmt.type and getattr(stmt.type, "is_own", False))
        self._scope.define(stmt.name, stmt.is_mut, is_own)

    def _check_let_tuple(self, stmt: LetTupleStmt) -> None:
        self._check_expr_read(stmt.value)
        for name in stmt.names:
            self._scope.define(name, stmt.is_mut, False)

    def _check_assign(self, stmt: AssignStmt) -> None:
        # Vérifier la cible
        if isinstance(stmt.target, Identifier):
            name = stmt.target.name
            if name in self._consts:
                self._err(f"impossible d'assigner à la constante '{name}'")
                return
            entry = self._scope.lookup(name)
            if entry:
                if not entry.is_mut:
                    self._err(f"impossible d'assigner à '{name}' : variable immutable")
                elif entry.state == ValueState.MOVED:
                    self._err(f"impossible d'assigner à '{name}' : valeur déplacée")
                elif entry.borrow_count > 0:
                    self._err(f"impossible d'assigner à '{name}' : emprunté en lecture")
                elif entry.mut_borrow:
                    self._warn(f"assignation à '{name}' pendant un emprunt mutable")
        elif isinstance(stmt.target, MemberAccess):
            self._check_expr_read(stmt.target.object)
        elif isinstance(stmt.target, IndexExpr):
            self._check_expr_read(stmt.target.object)

        # Vérifier la valeur
        self._check_expr_read(stmt.value)
        # Move si la valeur est un own ident
        if isinstance(stmt.value, Identifier):
            entry = self._scope.lookup(stmt.value.name)
            if entry and entry.is_own:
                if entry.can_move():
                    self._scope.mark_moved(stmt.value.name)

    def _check_if(self, stmt: IfStmt) -> None:
        self._check_expr_read(stmt.condition)
        self._in_scope(stmt.then_body)
        if stmt.else_body:
            self._in_scope(stmt.else_body)

    def _check_match_arm_body(self, body: List[Stmt],
                               guard: Optional[Expr]) -> None:
        inner = BorrowScope(self._scope)
        old = self._scope
        self._scope = inner
        if guard:
            self._check_expr_read(guard)
        for s in body:
            self._check_stmt(s)
        inner.drop_all()
        self._scope = old

    # ── Expressions ───────────────────────────────────────────────────────────

    def _check_expr_read(self, expr: Expr) -> None:
        """Vérifie qu'une expression est lisible (non déplacée, non droppée)."""
        if expr is None:
            return

        if isinstance(expr, Identifier):
            name = expr.name
            entry = self._scope.lookup(name)
            if entry:
                if entry.state == ValueState.MOVED:
                    self._err(f"utilisation de '{name}' après déplacement (use-after-move)")
                elif entry.state == ValueState.DROPPED:
                    self._err(f"utilisation de '{name}' hors de sa portée")

        elif isinstance(expr, UnaryOp):
            if expr.op == "&":
                # référence partagée
                if isinstance(expr.operand, Identifier):
                    entry = self._scope.lookup(expr.operand.name)
                    if entry and not entry.can_borrow():
                        self._err(f"impossible d'emprunter '{expr.operand.name}' : emprunt mutable actif")
            elif expr.op in ("&mut", "&mut "):
                # référence mutable
                if isinstance(expr.operand, Identifier):
                    entry = self._scope.lookup(expr.operand.name)
                    if entry:
                        if not entry.can_mut_borrow():
                            self._err(
                                f"impossible d'emprunter mutuellement '{expr.operand.name}' : "
                                f"déjà emprunté ou non mutable"
                            )
            self._check_expr_read(expr.operand)

        elif isinstance(expr, BinaryOp):
            self._check_expr_read(expr.left)
            self._check_expr_read(expr.right)

        elif isinstance(expr, CallExpr):
            self._check_expr_read(expr.callee)
            for a in expr.args:
                self._check_expr_read(a)
                # Move des arguments own
                if isinstance(a, Identifier):
                    entry = self._scope.lookup(a.name)
                    if entry and entry.is_own and not self._is_copy_type(entry):
                        if entry.can_move():
                            self._scope.mark_moved(a.name)

        elif isinstance(expr, MemberAccess):
            self._check_expr_read(expr.object)

        elif isinstance(expr, IndexExpr):
            self._check_expr_read(expr.object)
            self._check_expr_read(expr.index)

        elif isinstance(expr, StructInit):
            for v in expr.fields.values():
                self._check_expr_read(v)

        elif isinstance(expr, ArrayLiteral):
            if expr.repeat:
                self._check_expr_read(expr.repeat[0])
            for e in expr.elements:
                self._check_expr_read(e)

        elif isinstance(expr, TupleExpr):
            for e in expr.elements:
                self._check_expr_read(e)

        elif isinstance(expr, (SomeExpr, OkExpr, ErrExpr)):
            self._check_expr_read(expr.value)

        elif isinstance(expr, QuestionExpr):
            self._check_expr_read(expr.expr)

        elif isinstance(expr, CastExpr):
            self._check_expr_read(expr.expr)

        elif isinstance(expr, RangeExpr):
            self._check_expr_read(expr.start)
            self._check_expr_read(expr.end)

        elif isinstance(expr, ClosureExpr):
            # Une closure capture les variables de l'environnement
            # On crée une portée interne pour le corps
            inner = BorrowScope(self._scope)
            for p in expr.params:
                inner.define(p.name, p.is_mut, False)
            old = self._scope
            self._scope = inner
            if expr.body:
                for s in expr.body:
                    self._check_stmt(s)
            if expr.expr:
                self._check_expr_read(expr.expr)
            inner.drop_all()
            self._scope = old

    # ── Utilitaires ───────────────────────────────────────────────────────────

    def _in_scope(self, stmts: List[Stmt]) -> None:
        """Exécute une liste de statements dans une nouvelle portée enfant."""
        inner = BorrowScope(self._scope)
        self._with_scope(inner, stmts)

    def _with_scope(self, scope: BorrowScope, stmts: List[Stmt]) -> None:
        old = self._scope
        self._scope = scope
        for s in stmts:
            self._check_stmt(s)
        scope.drop_all()
        self._scope = old

    def _is_copy_type(self, entry: BorrowEntry) -> bool:
        """Retourne True si le type est Copy (pas besoin de move)."""
        # On n'a pas le type résolu ici, on se base sur is_own
        return not entry.is_own

    def _err(self, msg: str, line: int = 0, col: int = 0) -> None:
        self.errors.append(BorrowError(msg, line, col, "error"))

    def _warn(self, msg: str, line: int = 0, col: int = 0) -> None:
        self.warnings.append(BorrowError(msg, line, col, "warning"))


# ═══════════════════════════════════════════════════════════════════════════════
#  API simplifiée
# ═══════════════════════════════════════════════════════════════════════════════

def check_program(program: Program) -> List[BorrowError]:
    """Vérifie le programme entier et retourne les erreurs."""
    return BorrowChecker().check_program(program)


def check_function(fn: FunctionDecl) -> List[BorrowError]:
    """Vérifie une seule fonction."""
    return BorrowChecker().check_function(fn)


def format_errors(errors: List[BorrowError]) -> str:
    """Formate une liste d'erreurs en chaîne lisible."""
    if not errors:
        return ""
    lines = ["=== Borrow Check Errors ==="]
    for e in errors:
        prefix = "  ERROR  " if e.severity == "error" else "  WARN   "
        loc = f"(ligne {e.line})" if e.line else ""
        lines.append(f"{prefix}{e.message} {loc}")
    return "\n".join(lines)
