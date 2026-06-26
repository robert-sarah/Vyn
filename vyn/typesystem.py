"""Système de types Vyn — inférence, génériques, Option/Result, closures, tuples."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import Enum, auto

from vyn.ast.nodes import TypeNode


# ═══════════════════════════════════════════════════════════════════════════════
#  Représentation interne des types (IR de types)
# ═══════════════════════════════════════════════════════════════════════════════

class TKind(Enum):
    PRIM    = auto()   # i32, f32, bool, str, char, void, usize …
    ARRAY   = auto()   # T[]  /  [T; N]
    TUPLE   = auto()   # (T1, T2, …)
    STRUCT  = auto()   # struct défini par l'utilisateur
    ENUM    = auto()   # enum défini par l'utilisateur
    FN      = auto()   # fn(T1, T2) -> R
    CLOSURE = auto()   # même représentation que FN mais capturant
    OPTION  = auto()   # Option<T>
    RESULT  = auto()   # Result<T, E>
    HASHMAP = auto()   # HashMap<K, V>
    VEC     = auto()   # Vec<T>
    REF     = auto()   # &T
    PTR     = auto()   # *T
    VAR     = auto()   # variable de type (T, U, K, V …)
    NEVER   = auto()   # ! (type de throw/return sans valeur)
    UNKNOWN = auto()   # type non encore inféré


# ─── Primitives connues ───────────────────────────────────────────────────────

PRIMITIVES: Set[str] = {
    "i8","i16","i32","i64",
    "u8","u16","u32","u64",
    "f32","f64",
    "bool","str","char","void","usize","isize",
}

INT_TYPES:   Set[str] = {"i8","i16","i32","i64","u8","u16","u32","u64","usize","isize"}
FLOAT_TYPES: Set[str] = {"f32","f64"}
NUM_TYPES:   Set[str] = INT_TYPES | FLOAT_TYPES


@dataclass
class VynType:
    """Représentation interne d'un type résolu."""
    kind:    TKind
    name:    str                          # nom canonique
    params:  List["VynType"]  = field(default_factory=list)  # types paramètres
    var_id:  Optional[int]    = None      # id unique pour les variables de type
    size:    Optional[int]    = None      # taille statique du tableau

    # ── Constructeurs statiques ──────────────────────────────────────────────

    @staticmethod
    def prim(name: str) -> "VynType":
        return VynType(TKind.PRIM, name)

    @staticmethod
    def var(name: str, uid: int = 0) -> "VynType":
        return VynType(TKind.VAR, name, var_id=uid)

    @staticmethod
    def array(elem: "VynType", size: Optional[int] = None) -> "VynType":
        t = VynType(TKind.ARRAY, "array", [elem])
        t.size = size
        return t

    @staticmethod
    def tuple_(*elems: "VynType") -> "VynType":
        return VynType(TKind.TUPLE, "tuple", list(elems))

    @staticmethod
    def fn_(*params: "VynType", ret: "VynType") -> "VynType":
        return VynType(TKind.FN, "fn", list(params) + [ret])

    @staticmethod
    def closure(*params: "VynType", ret: "VynType") -> "VynType":
        return VynType(TKind.CLOSURE, "closure", list(params) + [ret])

    @staticmethod
    def option(inner: "VynType") -> "VynType":
        return VynType(TKind.OPTION, "Option", [inner])

    @staticmethod
    def result(ok: "VynType", err: "VynType") -> "VynType":
        return VynType(TKind.RESULT, "Result", [ok, err])

    @staticmethod
    def hashmap(key: "VynType", val: "VynType") -> "VynType":
        return VynType(TKind.HASHMAP, "HashMap", [key, val])

    @staticmethod
    def vec(inner: "VynType") -> "VynType":
        return VynType(TKind.VEC, "Vec", [inner])

    @staticmethod
    def ref_(inner: "VynType") -> "VynType":
        return VynType(TKind.REF, "ref", [inner])

    @staticmethod
    def struct_(name: str) -> "VynType":
        return VynType(TKind.STRUCT, name)

    @staticmethod
    def enum_(name: str) -> "VynType":
        return VynType(TKind.ENUM, name)

    @staticmethod
    def never() -> "VynType":
        return VynType(TKind.NEVER, "!")

    @staticmethod
    def unknown() -> "VynType":
        return VynType(TKind.UNKNOWN, "?")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def is_numeric(self) -> bool:
        return self.kind == TKind.PRIM and self.name in NUM_TYPES

    def is_integer(self) -> bool:
        return self.kind == TKind.PRIM and self.name in INT_TYPES

    def is_float(self) -> bool:
        return self.kind == TKind.PRIM and self.name in FLOAT_TYPES

    def is_bool(self) -> bool:
        return self.kind == TKind.PRIM and self.name == "bool"

    def is_str(self) -> bool:
        return self.kind == TKind.PRIM and self.name == "str"

    def is_void(self) -> bool:
        return self.kind == TKind.PRIM and self.name == "void"

    def is_var(self) -> bool:
        return self.kind == TKind.VAR

    def is_option(self) -> bool:
        return self.kind == TKind.OPTION

    def is_result(self) -> bool:
        return self.kind == TKind.RESULT

    def is_callable(self) -> bool:
        return self.kind in (TKind.FN, TKind.CLOSURE)

    def ret_type(self) -> "VynType":
        """Retourne le type de retour d'une fonction/closure."""
        if self.is_callable() and self.params:
            return self.params[-1]
        return VynType.unknown()

    def param_types(self) -> List["VynType"]:
        """Retourne les types des paramètres (sans le type de retour)."""
        if self.is_callable() and self.params:
            return self.params[:-1]
        return []

    def inner(self) -> "VynType":
        """Retourne le type intérieur (Option<T> → T, &T → T, array<T> → T)."""
        if self.params:
            return self.params[0]
        return VynType.unknown()

    def ok_type(self) -> "VynType":
        """Result<T, E> → T"""
        if self.is_result() and len(self.params) >= 1:
            return self.params[0]
        return VynType.unknown()

    def err_type(self) -> "VynType":
        """Result<T, E> → E"""
        if self.is_result() and len(self.params) >= 2:
            return self.params[1]
        return VynType.unknown()

    def __str__(self) -> str:
        if self.kind == TKind.PRIM:
            return self.name
        if self.kind == TKind.VAR:
            return self.name
        if self.kind == TKind.ARRAY:
            inner = str(self.params[0]) if self.params else "?"
            size  = f"; {self.size}" if self.size else ""
            return f"{inner}[{size}]"
        if self.kind == TKind.TUPLE:
            return "(" + ", ".join(str(p) for p in self.params) + ")"
        if self.kind in (TKind.FN, TKind.CLOSURE):
            ps  = ", ".join(str(p) for p in self.params[:-1]) if self.params else ""
            ret = str(self.params[-1]) if self.params else "void"
            kw  = "fn" if self.kind == TKind.FN else "closure"
            return f"{kw}({ps}) -> {ret}"
        if self.kind == TKind.OPTION:
            return f"Option<{self.params[0]}>" if self.params else "Option<?>"
        if self.kind == TKind.RESULT:
            if len(self.params) >= 2:
                return f"Result<{self.params[0]}, {self.params[1]}>"
            return "Result<?>"
        if self.kind == TKind.HASHMAP:
            if len(self.params) >= 2:
                return f"HashMap<{self.params[0]}, {self.params[1]}>"
            return "HashMap<?>"
        if self.kind == TKind.VEC:
            return f"Vec<{self.params[0]}>" if self.params else "Vec<?>"
        if self.kind == TKind.REF:
            return f"&{self.params[0]}" if self.params else "&?"
        if self.kind == TKind.PTR:
            return f"*{self.params[0]}" if self.params else "*?"
        if self.kind == TKind.NEVER:
            return "!"
        if self.kind == TKind.UNKNOWN:
            return "?"
        if self.params:
            args = ", ".join(str(p) for p in self.params)
            return f"{self.name}<{args}>"
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VynType):
            return False
        if self.kind != other.kind:
            return False
        if self.name != other.name:
            return False
        if len(self.params) != len(other.params):
            return False
        return all(a == b for a, b in zip(self.params, other.params))

    def __hash__(self) -> int:
        return hash((self.kind, self.name, tuple(str(p) for p in self.params)))


# ─── Instances pré-construites des primitives ─────────────────────────────────

T_I8    = VynType.prim("i8")
T_I16   = VynType.prim("i16")
T_I32   = VynType.prim("i32")
T_I64   = VynType.prim("i64")
T_U8    = VynType.prim("u8")
T_U16   = VynType.prim("u16")
T_U32   = VynType.prim("u32")
T_U64   = VynType.prim("u64")
T_F32   = VynType.prim("f32")
T_F64   = VynType.prim("f64")
T_BOOL  = VynType.prim("bool")
T_STR   = VynType.prim("str")
T_CHAR  = VynType.prim("char")
T_VOID  = VynType.prim("void")
T_USIZE = VynType.prim("usize")
T_ISIZE = VynType.prim("isize")
T_NEVER = VynType.never()
T_UNKN  = VynType.unknown()

_PRIM_MAP: Dict[str, VynType] = {
    "i8":   T_I8,   "i16":  T_I16,  "i32":  T_I32,  "i64":  T_I64,
    "u8":   T_U8,   "u16":  T_U16,  "u32":  T_U32,  "u64":  T_U64,
    "f32":  T_F32,  "f64":  T_F64,
    "bool": T_BOOL, "str":  T_STR,  "char": T_CHAR,
    "void": T_VOID, "usize":T_USIZE,"isize":T_ISIZE,
    "!":    T_NEVER,"?":    T_UNKN,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Conversion TypeNode (AST) → VynType
# ═══════════════════════════════════════════════════════════════════════════════

class TypeConvError(Exception):
    """Erreur de conversion de type."""


def from_node(node: TypeNode, env: Optional[Dict[str, VynType]] = None) -> VynType:
    """Convertit un nœud AST TypeNode en VynType résolu.

    env  : environnement des types génériques actuellement liés { "T": VynType, … }
    """
    if env is None:
        env = {}

    name = node.name

    # ── type variable liée dans l'environnement générique ─────────────────────
    if name in env:
        t = env[name]
        if node.is_ref:
            t = VynType.ref_(t)
        return t

    # ── variable de type libre (T, U, K, V, E …) ──────────────────────────────
    if len(name) == 1 and name.isupper():
        return VynType.var(name)

    # ── primitive ─────────────────────────────────────────────────────────────
    if name in _PRIM_MAP and not node.args:
        base = _PRIM_MAP[name]
        if node.is_ref:
            base = VynType.ref_(base)
        return base

    # ── array / slice ─────────────────────────────────────────────────────────
    if name == "array" or (node.args and name in _PRIM_MAP):
        inner = from_node(node.args[0], env) if node.args else T_UNKN
        t = VynType.array(inner, node.array_size)
        if node.is_ref:
            t = VynType.ref_(t)
        return t

    # Syntaxe `T[]` : le lexer/parser peut stocker le nom du type inner + array_size
    # On détecte un tableau par la présence de args ET nom primitif/struct
    if node.array_size is not None or (node.args and name != "fn" and name != "tuple"
                                       and name != "HashMap" and name != "Vec"
                                       and name != "Option" and name != "Result"):
        if node.args:
            inner = from_node(node.args[0], env)
        else:
            inner = _PRIM_MAP.get(name, VynType.struct_(name))
        return VynType.array(inner, node.array_size)

    # ── Option<T> ─────────────────────────────────────────────────────────────
    if name == "Option":
        inner = from_node(node.args[0], env) if node.args else T_UNKN
        return VynType.option(inner)

    # ── Result<T, E> ──────────────────────────────────────────────────────────
    if name == "Result":
        ok  = from_node(node.args[0], env) if len(node.args) > 0 else T_UNKN
        err = from_node(node.args[1], env) if len(node.args) > 1 else T_STR
        return VynType.result(ok, err)

    # ── HashMap<K, V> ─────────────────────────────────────────────────────────
    if name == "HashMap":
        k = from_node(node.args[0], env) if len(node.args) > 0 else T_STR
        v = from_node(node.args[1], env) if len(node.args) > 1 else T_UNKN
        return VynType.hashmap(k, v)

    # ── Vec<T> ────────────────────────────────────────────────────────────────
    if name == "Vec":
        inner = from_node(node.args[0], env) if node.args else T_UNKN
        return VynType.vec(inner)

    # ── fn(T1, T2) -> R ───────────────────────────────────────────────────────
    if name == "fn":
        # convention : args = [param0, param1, …, returnType]
        if node.args:
            params = [from_node(a, env) for a in node.args[:-1]]
            ret    = from_node(node.args[-1], env)
            return VynType.fn_(*params, ret=ret)
        return VynType.fn_(ret=T_VOID)

    # ── tuple ─────────────────────────────────────────────────────────────────
    if name == "tuple":
        elems = [from_node(a, env) for a in node.args]
        return VynType.tuple_(*elems)

    # ── référence &T ─────────────────────────────────────────────────────────
    if name == "ref" and node.args:
        return VynType.ref_(from_node(node.args[0], env))
    if node.is_ref:
        base = _PRIM_MAP.get(name, VynType.struct_(name))
        return VynType.ref_(base)

    # ── type générique custom  Foo<T, U> ─────────────────────────────────────
    if node.args:
        resolved = [from_node(a, env) for a in node.args]
        t = VynType(TKind.STRUCT, name, resolved)
        return t

    # ── struct / enum utilisateur ─────────────────────────────────────────────
    return VynType.struct_(name)


def to_node(t: VynType) -> TypeNode:
    """Convertit un VynType en TypeNode (pour les messages d'erreur / codegen)."""
    if t.kind == TKind.PRIM:
        return TypeNode(t.name)
    if t.kind == TKind.VAR:
        return TypeNode(t.name)
    if t.kind == TKind.ARRAY:
        inner = to_node(t.params[0]) if t.params else TypeNode("void")
        return TypeNode("array", [inner], t.size)
    if t.kind == TKind.TUPLE:
        return TypeNode("tuple", [to_node(p) for p in t.params])
    if t.kind in (TKind.FN, TKind.CLOSURE):
        return TypeNode("fn", [to_node(p) for p in t.params])
    if t.kind == TKind.OPTION:
        return TypeNode("Option", [to_node(t.params[0])] if t.params else [])
    if t.kind == TKind.RESULT:
        return TypeNode("Result", [to_node(p) for p in t.params[:2]])
    if t.kind == TKind.HASHMAP:
        return TypeNode("HashMap", [to_node(p) for p in t.params[:2]])
    if t.kind == TKind.VEC:
        return TypeNode("Vec", [to_node(t.params[0])] if t.params else [])
    if t.kind == TKind.REF:
        inner = to_node(t.params[0]) if t.params else TypeNode("void")
        inner.is_ref = True
        return inner
    return TypeNode(t.name)


# ═══════════════════════════════════════════════════════════════════════════════
#  Unification et substitution
# ═══════════════════════════════════════════════════════════════════════════════

class UnificationError(Exception):
    """Erreur de typage : types incompatibles."""
    def __init__(self, t1: VynType, t2: VynType, msg: str = ""):
        self.t1  = t1
        self.t2  = t2
        self.msg = msg
        super().__init__(msg or f"type mismatch: {t1} ≠ {t2}")


# Substitution : variable de type → type concret
Subst = Dict[int, VynType]


def apply_subst(subst: Subst, t: VynType) -> VynType:
    """Applique une substitution à un type."""
    if t.kind == TKind.VAR and t.var_id is not None and t.var_id in subst:
        return apply_subst(subst, subst[t.var_id])
    if not t.params:
        return t
    new_params = [apply_subst(subst, p) for p in t.params]
    # ne recréer que si changé
    if all(np is op for np, op in zip(new_params, t.params)):
        return t
    result = VynType(t.kind, t.name, new_params, t.var_id, t.size)
    return result


def occurs_in(var_id: int, t: VynType) -> bool:
    """Vérifie si la variable var_id apparaît dans t (occurs check)."""
    if t.kind == TKind.VAR and t.var_id == var_id:
        return True
    return any(occurs_in(var_id, p) for p in t.params)


def unify(t1: VynType, t2: VynType, subst: Optional[Subst] = None) -> Subst:
    """Unifie t1 et t2, retourne la substitution résultante."""
    if subst is None:
        subst = {}

    t1 = apply_subst(subst, t1)
    t2 = apply_subst(subst, t2)

    # Identiques → rien à faire
    if t1 == t2:
        return subst

    # t1 est une variable de type
    if t1.kind == TKind.VAR and t1.var_id is not None:
        if t1.var_id == (t2.var_id if t2.var_id else -1):
            return subst
        if occurs_in(t1.var_id, t2):
            raise UnificationError(t1, t2, f"recursive type: {t1} occurs in {t2}")
        subst[t1.var_id] = t2
        return subst

    # t2 est une variable de type
    if t2.kind == TKind.VAR and t2.var_id is not None:
        return unify(t2, t1, subst)

    # UNKNOWN est compatible avec tout
    if t1.kind == TKind.UNKNOWN or t2.kind == TKind.UNKNOWN:
        return subst

    # NEVER est compatible avec tout (coerce)
    if t1.kind == TKind.NEVER or t2.kind == TKind.NEVER:
        return subst

    # Compatibilité numérique implicite (i32 ↔ f32, i32 ↔ i64, …)
    if t1.is_numeric() and t2.is_numeric():
        return subst   # on autorise la coercition numérique

    # Les deux doivent avoir le même kind et le même nom
    if t1.kind != t2.kind or t1.name != t2.name:
        raise UnificationError(t1, t2)

    # Unifier récursivement les paramètres
    if len(t1.params) != len(t2.params):
        raise UnificationError(t1, t2, f"wrong number of type params")

    for p1, p2 in zip(t1.params, t2.params):
        subst = unify(p1, p2, subst)

    return subst


def types_compatible(t1: VynType, t2: VynType) -> bool:
    """Retourne True si t1 et t2 sont unifiables sans lever d'exception."""
    try:
        unify(t1, t2)
        return True
    except UnificationError:
        return False


def is_assignable(from_: VynType, to: VynType) -> bool:
    """Vérifie si une valeur de type `from_` peut être assignée à `to`."""
    if from_ == to:
        return True
    if from_.kind in (TKind.UNKNOWN, TKind.NEVER):
        return True
    if to.kind == TKind.UNKNOWN:
        return True
    # coercition numérique
    if from_.is_numeric() and to.is_numeric():
        return True
    # &T assignable à T (déréférencement implicite)
    if from_.kind == TKind.REF and from_.params:
        return is_assignable(from_.params[0], to)
    return types_compatible(from_, to)


# ═══════════════════════════════════════════════════════════════════════════════
#  Inférence de type
# ═══════════════════════════════════════════════════════════════════════════════

class TypeVarGen:
    """Générateur de variables de type fraîches."""
    _counter: int = 0

    @classmethod
    def fresh(cls, hint: str = "T") -> VynType:
        cls._counter += 1
        return VynType.var(f"{hint}{cls._counter}", cls._counter)

    @classmethod
    def reset(cls) -> None:
        cls._counter = 0


# ─── Environnement de typage ──────────────────────────────────────────────────

@dataclass
class TypeEnv:
    """Environnement de typage à portée lexicale (scopes imbriqués)."""

    _scopes: List[Dict[str, VynType]] = field(default_factory=lambda: [{}])

    def push(self) -> None:
        self._scopes.append({})

    def pop(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()

    def define(self, name: str, t: VynType, overwrite: bool = False) -> None:
        if not overwrite and name in self._scopes[-1]:
            pass   # redéfinition silencieuse dans la même portée
        self._scopes[-1][name] = t

    def lookup(self, name: str) -> Optional[VynType]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_strict(self, name: str) -> VynType:
        t = self.lookup(name)
        if t is None:
            raise KeyError(f"identifiant inconnu dans l'env de types: {name!r}")
        return t

    def copy(self) -> "TypeEnv":
        env = TypeEnv()
        env._scopes = [dict(s) for s in self._scopes]
        return env


# ─── Schéma de type générique ─────────────────────────────────────────────────

@dataclass
class TypeScheme:
    """Schéma polymorphe : ∀ T1 T2 … . type."""
    vars:  List[int]    # ids des variables universellement quantifiées
    body:  VynType

    def instantiate(self, gen: TypeVarGen) -> VynType:
        """Crée une instance fraîche du schéma."""
        renaming: Subst = {v: gen.fresh() for v in self.vars}
        return apply_subst(renaming, self.body)

    @staticmethod
    def mono(t: VynType) -> "TypeScheme":
        """Schéma monomorphe (pas de variables universelles)."""
        return TypeScheme([], t)

    @staticmethod
    def generalize(t: VynType, env: TypeEnv) -> "TypeScheme":
        """Généralize t par rapport à env (trouve les variables libres)."""
        free_in_env: Set[int] = set()
        for scope in env._scopes:
            for vt in scope.values():
                free_in_env.update(_free_vars(vt))
        free_in_t = _free_vars(t) - free_in_env
        return TypeScheme(sorted(free_in_t), t)


def _free_vars(t: VynType) -> Set[int]:
    """Collecte les ids des variables de type libres dans t."""
    if t.kind == TKind.VAR and t.var_id is not None:
        return {t.var_id}
    result: Set[int] = set()
    for p in t.params:
        result.update(_free_vars(p))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Registre des types connus (structs, enums, traits)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StructInfo:
    name:     str
    fields:   Dict[str, VynType]          # nom champ → type
    generics: List[str] = field(default_factory=list)  # noms des paramètres génériques

    def instantiate(self, args: List[VynType]) -> Dict[str, VynType]:
        """Retourne les champs avec les génériques substitués."""
        subst: Dict[str, VynType] = dict(zip(self.generics, args))
        return {
            fname: _substitute_by_name(ft, subst)
            for fname, ft in self.fields.items()
        }


@dataclass
class EnumInfo:
    name:     str
    variants: Dict[str, Optional[VynType]]   # variant → payload type (None si unit)
    generics: List[str] = field(default_factory=list)


@dataclass
class FnSig:
    """Signature de fonction."""
    name:        str
    param_types: List[VynType]
    ret_type:    VynType
    generics:    List[str] = field(default_factory=list)
    is_method:   bool      = False

    def as_vyntype(self) -> VynType:
        return VynType.fn_(*self.param_types, ret=self.ret_type)

    def arity(self) -> int:
        return len(self.param_types)


def _substitute_by_name(t: VynType, mapping: Dict[str, VynType]) -> VynType:
    """Substitue les variables de type par nom (T, U …)."""
    if t.kind == TKind.VAR and t.name in mapping:
        return mapping[t.name]
    if not t.params:
        return t
    new_params = [_substitute_by_name(p, mapping) for p in t.params]
    return VynType(t.kind, t.name, new_params, t.var_id, t.size)


@dataclass
class TypeRegistry:
    """Registre global des déclarations de types."""
    structs:   Dict[str, StructInfo]  = field(default_factory=dict)
    enums:     Dict[str, EnumInfo]    = field(default_factory=dict)
    functions: Dict[str, FnSig]       = field(default_factory=dict)
    aliases:   Dict[str, VynType]     = field(default_factory=dict)
    traits:    Dict[str, List[FnSig]] = field(default_factory=dict)

    def register_struct(self, name: str, fields: Dict[str, VynType],
                        generics: Optional[List[str]] = None) -> None:
        self.structs[name] = StructInfo(name, fields, generics or [])

    def register_enum(self, name: str, variants: Dict[str, Optional[VynType]],
                      generics: Optional[List[str]] = None) -> None:
        self.enums[name] = EnumInfo(name, variants, generics or [])

    def register_fn(self, name: str, param_types: List[VynType],
                    ret_type: VynType, generics: Optional[List[str]] = None,
                    is_method: bool = False) -> None:
        self.functions[name] = FnSig(name, param_types, ret_type, generics or [], is_method)

    def register_alias(self, name: str, target: VynType) -> None:
        self.aliases[name] = target

    def resolve_alias(self, t: VynType) -> VynType:
        """Résout les alias de types récursivement."""
        if t.name in self.aliases and not t.params:
            return self.resolve_alias(self.aliases[t.name])
        return t

    def lookup_type(self, name: str) -> Optional[VynType]:
        """Cherche un type par nom (struct, enum, alias, primitive)."""
        if name in _PRIM_MAP:
            return _PRIM_MAP[name]
        if name in self.aliases:
            return self.resolve_alias(self.aliases[name])
        if name in self.structs:
            return VynType.struct_(name)
        if name in self.enums:
            return VynType.enum_(name)
        return None

    def field_type(self, struct_name: str, field_name: str,
                   generic_args: Optional[List[VynType]] = None) -> Optional[VynType]:
        """Retourne le type d'un champ de struct."""
        info = self.structs.get(struct_name)
        if info is None:
            return None
        if generic_args and info.generics:
            fields = info.instantiate(generic_args)
            return fields.get(field_name)
        return info.fields.get(field_name)

    def variant_payload(self, enum_name: str, variant: str,
                        generic_args: Optional[List[VynType]] = None
                        ) -> Optional[VynType]:
        """Retourne le type de payload d'un variant d'enum."""
        info = self.enums.get(enum_name)
        if info is None:
            return None
        payload = info.variants.get(variant)
        if payload is None:
            return None
        if generic_args and info.generics:
            mapping = dict(zip(info.generics, generic_args))
            return _substitute_by_name(payload, mapping)
        return payload

    def fn_sig(self, name: str) -> Optional[FnSig]:
        return self.functions.get(name)


# ─── Registre global pré-peuplé avec la stdlib ───────────────────────────────

def _build_stdlib_registry() -> TypeRegistry:
    reg = TypeRegistry()

    # Option / Result (pseudo-enums)
    reg.register_enum("Option", {"Some": T_UNKN, "None": None}, ["T"])
    reg.register_enum("Result", {"Ok": T_UNKN, "Err": T_STR},  ["T", "E"])

    # std.io
    reg.register_fn("io.print",    [T_UNKN],            T_VOID)
    reg.register_fn("io.println",  [T_UNKN],            T_VOID)
    reg.register_fn("io.print_int",[T_I32],             T_VOID)
    reg.register_fn("io.print_i32",[T_I32],             T_VOID)
    reg.register_fn("io.readln",   [],                  T_STR)
    reg.register_fn("io.read_int", [],                  T_I32)

    # std.math
    reg.register_fn("math.abs",    [T_F32],             T_F32)
    reg.register_fn("math.sqrt",   [T_F32],             T_F32)
    reg.register_fn("math.clamp",  [T_F32, T_F32, T_F32], T_F32)
    reg.register_fn("math.lerp",   [T_F32, T_F32, T_F32], T_F32)
    reg.register_fn("math.pow",    [T_F32, T_F32],      T_F32)
    reg.register_fn("math.floor",  [T_F32],             T_F32)
    reg.register_fn("math.ceil",   [T_F32],             T_F32)
    reg.register_fn("math.sin",    [T_F32],             T_F32)
    reg.register_fn("math.cos",    [T_F32],             T_F32)
    reg.register_fn("math.min",    [T_F32, T_F32],      T_F32)
    reg.register_fn("math.max",    [T_F32, T_F32],      T_F32)
    reg.register_fn("math.PI",     [],                  T_F32)
    reg.register_fn("math.E",      [],                  T_F32)

    # std.str
    reg.register_fn("str.len",      [T_STR],            T_I32)
    reg.register_fn("str.upper",    [T_STR],            T_STR)
    reg.register_fn("str.lower",    [T_STR],            T_STR)
    reg.register_fn("str.trim",     [T_STR],            T_STR)
    reg.register_fn("str.contains", [T_STR, T_STR],     T_BOOL)
    reg.register_fn("str.replace",  [T_STR, T_STR, T_STR], T_STR)
    reg.register_fn("str.split",    [T_STR, T_STR],     VynType.array(T_STR))
    reg.register_fn("str.starts_with",[T_STR, T_STR],   T_BOOL)
    reg.register_fn("str.ends_with",[T_STR, T_STR],     T_BOOL)
    reg.register_fn("str.parse_int",[T_STR],            T_I32)
    reg.register_fn("str.parse_f32",[T_STR],            T_F32)
    reg.register_fn("str.from_int", [T_I32],            T_STR)
    reg.register_fn("str.chars",    [T_STR],            VynType.array(T_CHAR))
    reg.register_fn("str.index",    [T_STR, T_I32],     T_CHAR)
    reg.register_fn("str.concat",   [T_STR, T_STR],     T_STR)
    reg.register_fn("str.format",   [T_STR],            T_STR)

    # std.fs
    reg.register_fn("fs.exists",   [T_STR],             T_BOOL)
    reg.register_fn("fs.read",     [T_STR],             T_STR)
    reg.register_fn("fs.write",    [T_STR, T_STR],      T_VOID)
    reg.register_fn("fs.remove",   [T_STR],             T_BOOL)
    reg.register_fn("fs.list_dir", [T_STR],             VynType.array(T_STR))
    reg.register_fn("fs.mkdir",    [T_STR],             T_BOOL)

    # std.json
    reg.register_fn("json.parse",    [T_STR],           T_STR)
    reg.register_fn("json.stringify",[T_UNKN],          T_STR)
    reg.register_fn("json.parse_int",[T_STR],           T_I32)

    # std.db
    reg.register_fn("db.open",  [T_STR],                T_STR)
    reg.register_fn("db.exec",  [T_STR, T_STR],         T_I32)
    reg.register_fn("db.query", [T_STR, T_STR],         T_STR)
    reg.register_fn("db.close", [T_STR],                T_I32)

    # std.ai
    reg.register_fn("ai.model_new",[T_STR, T_I32, T_I32, T_I32], T_STR)
    reg.register_fn("ai.train",    [T_STR, T_I32, T_F32],         T_F32)
    reg.register_fn("ai.predict",  [T_STR, T_F32],                T_F32)
    reg.register_fn("ai.loss",     [T_STR],                       T_F32)
    reg.register_fn("ai.save",     [T_STR, T_STR],                T_VOID)
    reg.register_fn("ai.load",     [T_STR],                       T_STR)

    # std.server
    reg.register_fn("server.route",        [T_STR, T_STR],          T_VOID)
    reg.register_fn("server.listen",       [T_I32],                 T_VOID)
    reg.register_fn("server.listen_async", [T_I32],                 T_VOID)
    reg.register_fn("server.stop",         [],                      T_VOID)
    reg.register_fn("server.serve_static", [T_STR, T_STR],          T_VOID)

    # std.html
    reg.register_fn("html.page",   [T_STR, T_STR],      T_STR)
    reg.register_fn("html.h1",     [T_STR],             T_STR)
    reg.register_fn("html.h2",     [T_STR],             T_STR)
    reg.register_fn("html.p",      [T_STR],             T_STR)
    reg.register_fn("html.div",    [T_STR],             T_STR)
    reg.register_fn("html.a",      [T_STR, T_STR],      T_STR)
    reg.register_fn("html.escape", [T_STR],             T_STR)
    reg.register_fn("html.body",   [T_STR],             T_STR)
    reg.register_fn("html.head",   [T_STR],             T_STR)
    reg.register_fn("html.style",  [T_STR],             T_STR)

    # std.log
    reg.register_fn("log.info",    [T_STR],             T_VOID)
    reg.register_fn("log.error",   [T_STR],             T_VOID)
    reg.register_fn("log.warn",    [T_STR],             T_VOID)
    reg.register_fn("log.debug",   [T_STR],             T_VOID)

    # std.sys
    reg.register_fn("sys.sleep",   [T_I32],             T_VOID)
    reg.register_fn("sys.exit",    [T_I32],             T_NEVER)
    reg.register_fn("sys.env",     [T_STR],             T_STR)
    reg.register_fn("sys.args",    [],                  VynType.array(T_STR))

    # std.time
    reg.register_fn("time.now_ms", [],                  T_I64)
    reg.register_fn("time.now_sec",[],                  T_I64)
    reg.register_fn("time.format", [T_I64, T_STR],      T_STR)

    # std.vec
    reg.register_fn("vec.new",     [],                  VynType.array(T_UNKN))
    reg.register_fn("vec.push",    [T_UNKN, T_UNKN],    T_VOID)
    reg.register_fn("vec.len",     [T_UNKN],            T_I32)
    reg.register_fn("vec.get",     [T_UNKN, T_I32],     T_UNKN)
    reg.register_fn("vec.set",     [T_UNKN, T_I32, T_UNKN], T_VOID)
    reg.register_fn("vec.remove",  [T_UNKN, T_I32],     T_UNKN)
    reg.register_fn("vec.clear",   [T_UNKN],            T_VOID)
    reg.register_fn("vec.sort",    [T_UNKN],            T_VOID)

    # std.hashmap (nouveau)
    reg.register_fn("hashmap.new",      [],             VynType.hashmap(T_UNKN, T_UNKN))
    reg.register_fn("hashmap.insert",   [T_UNKN, T_UNKN, T_UNKN], T_VOID)
    reg.register_fn("hashmap.get",      [T_UNKN, T_UNKN],  VynType.option(T_UNKN))
    reg.register_fn("hashmap.get_or",   [T_UNKN, T_UNKN, T_UNKN], T_UNKN)
    reg.register_fn("hashmap.remove",   [T_UNKN, T_UNKN],  T_BOOL)
    reg.register_fn("hashmap.contains", [T_UNKN, T_UNKN],  T_BOOL)
    reg.register_fn("hashmap.len",      [T_UNKN],       T_I32)
    reg.register_fn("hashmap.keys",     [T_UNKN],       VynType.array(T_UNKN))
    reg.register_fn("hashmap.values",   [T_UNKN],       VynType.array(T_UNKN))
    reg.register_fn("hashmap.clear",    [T_UNKN],       T_VOID)

    # std.rand
    reg.register_fn("rand.seed",      [T_I32],          T_VOID)
    reg.register_fn("rand.next_f32",  [],               T_F32)
    reg.register_fn("rand.next_i32",  [],               T_I32)
    reg.register_fn("rand.range",     [T_I32, T_I32],   T_I32)

    # std.gui
    reg.register_fn("gui.window",  [T_STR, T_I32, T_I32], T_VOID)
    reg.register_fn("gui.label",   [T_STR, T_STR, T_I32, T_I32], T_VOID)
    reg.register_fn("gui.button",  [T_STR, T_STR, T_I32, T_I32, T_STR], T_VOID)
    reg.register_fn("gui.run",     [],                  T_VOID)
    reg.register_fn("gui.alert",   [T_STR],             T_VOID)

    # std.net
    reg.register_fn("net.get",     [T_STR],             T_STR)
    reg.register_fn("net.post",    [T_STR, T_STR],      T_STR)
    reg.register_fn("net.ping",    [T_STR],             T_BOOL)
    reg.register_fn("net.resolve", [T_STR],             T_STR)

    # std.thread
    reg.register_fn("thread.spawn",    [T_STR],         T_I32)
    reg.register_fn("thread.join",     [T_I32],         T_VOID)
    reg.register_fn("thread.sleep_ms", [T_I32],         T_VOID)
    reg.register_fn("thread.current",  [],              T_I32)

    # std.http
    reg.register_fn("http.get",        [T_STR],         T_STR)
    reg.register_fn("http.post",       [T_STR, T_STR],  T_STR)
    reg.register_fn("http.ok",         [T_STR],         T_STR)
    reg.register_fn("http.not_found",  [],              T_STR)

    # numpy / ML (retournent str comme handle)
    reg.register_fn("numpy.array",    [T_UNKN],         T_STR)
    reg.register_fn("numpy.zeros",    [T_I32],          T_STR)
    reg.register_fn("numpy.ones",     [T_I32],          T_STR)
    reg.register_fn("numpy.mean",     [T_STR],          T_F32)
    reg.register_fn("numpy.dot",      [T_STR, T_STR],   T_STR)
    reg.register_fn("numpy.shape",    [T_STR],          T_STR)

    reg.register_fn("torch.tensor",   [T_UNKN],         T_STR)
    reg.register_fn("torch.relu",     [T_STR],          T_STR)
    reg.register_fn("torch.train_linear",[T_I32],       T_F32)

    reg.register_fn("tensorflow.train_xor",[T_I32],     T_F32)
    reg.register_fn("tensorflow.predict",  [T_STR, T_STR], T_F32)

    reg.register_fn("sklearn.fit_linear", [T_UNKN, T_UNKN], T_STR)
    reg.register_fn("sklearn.predict",    [T_STR, T_F32],   T_F32)
    reg.register_fn("sklearn.score",      [T_STR],          T_F32)

    reg.register_fn("pandas.read_csv",   [T_STR],       T_STR)
    reg.register_fn("pandas.rows",       [T_STR],       T_I32)
    reg.register_fn("pandas.mean",       [T_STR],       T_F32)

    reg.register_fn("cv.grayscale",      [T_STR, T_STR],T_VOID)
    reg.register_fn("cv.resize",         [T_STR, T_I32, T_I32, T_STR], T_VOID)

    reg.register_fn("plot.line",  [T_STR, T_UNKN, T_UNKN, T_STR], T_VOID)
    reg.register_fn("plot.hist",  [T_STR, T_UNKN, T_STR],          T_VOID)

    # std.css
    reg.register_fn("css.rule",       [T_STR, T_STR],   T_STR)
    reg.register_fn("css.class",      [T_STR, T_STR],   T_STR)
    reg.register_fn("css.stylesheet", [T_STR],          T_STR)

    return reg


# Singleton global
STDLIB_REGISTRY: TypeRegistry = _build_stdlib_registry()


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers de coercition et de largeur numérique
# ═══════════════════════════════════════════════════════════════════════════════

_NUM_WIDTH: Dict[str, int] = {
    "i8":1,"i16":2,"i32":4,"i64":8,
    "u8":1,"u16":2,"u32":4,"u64":8,
    "f32":4,"f64":8,"usize":8,"isize":8,
}


def wider_numeric(a: VynType, b: VynType) -> VynType:
    """Retourne le type numérique le plus large entre a et b."""
    if not (a.is_numeric() and b.is_numeric()):
        return a
    if a.is_float() or b.is_float():
        return T_F64 if (a.name == "f64" or b.name == "f64") else T_F32
    wa = _NUM_WIDTH.get(a.name, 4)
    wb = _NUM_WIDTH.get(b.name, 4)
    # signé prend la priorité sur non-signé de même largeur
    if wa >= wb:
        return a
    return b


def coerce_numeric_op(op: str, l: VynType, r: VynType) -> VynType:
    """Retourne le type résultat d'une opération binaire numérique."""
    if op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||", "and", "or"):
        return T_BOOL
    if op in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"):
        return wider_numeric(l, r)
    return T_BOOL
