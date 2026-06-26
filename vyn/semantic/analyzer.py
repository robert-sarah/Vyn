"""Analyseur sémantique Vyn — typage statique complet, génériques, closures, Option/Result, for/while, patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from vyn.ast.nodes import (
    # programme
    Program, ImportDecl, UseDecl, ExternDecl, ModDecl,
    # déclarations
    StructDecl, EnumDecl, EnumVariant, FunctionDecl, ImplDecl, ImplBlock,
    TraitDecl, TraitMethod, ConstDecl, TypeAliasDecl, GenericParam, Field, Param,
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
    Visibility, Span, make_void, make_i32, make_f32, make_str, make_bool,
    make_option, make_result, make_array, make_tuple, make_fn_type,
)
from vyn.typesystem import (
    VynType, TKind, TypeEnv, TypeScheme, TypeVarGen, TypeRegistry,
    StructInfo, EnumInfo, FnSig,
    from_node, to_node, unify, types_compatible, is_assignable,
    wider_numeric, coerce_numeric_op,
    PRIMITIVES, INT_TYPES, FLOAT_TYPES, NUM_TYPES,
    T_I32, T_I64, T_F32, T_F64, T_BOOL, T_STR, T_CHAR, T_VOID,
    T_UNKN, T_NEVER, T_USIZE,
    STDLIB_REGISTRY,
    UnificationError,
)

ROOT   = Path(__file__).resolve().parent.parent.parent
STDLIB = ROOT / "stdlib"
VENDOR = ROOT / "vendor"


# ─── Modules standard dont les symboles sont connus ──────────────────────────

_STD_SYMBOLS: List[Tuple[str, Tuple[str, ...]]] = [
    ("io",          ("print", "println", "print_int", "print_i32", "readln", "read_int")),
    ("sys",         ("sleep", "exit", "env", "args")),
    ("math",        ("abs", "sqrt", "clamp", "lerp", "pow", "floor", "ceil",
                     "sin", "cos", "min", "max", "PI", "E", "log", "log2", "log10")),
    ("log",         ("info", "error", "warn", "debug")),
    ("str",         ("len", "upper", "lower", "trim", "contains", "replace",
                     "split", "starts_with", "ends_with", "parse_int", "parse_f32",
                     "from_int", "chars", "index", "concat", "format", "repeat", "pad")),
    ("fs",          ("exists", "read", "write", "remove", "list_dir", "mkdir",
                     "copy", "move", "size", "is_dir", "is_file")),
    ("json",        ("parse", "stringify", "parse_int", "parse_f32", "parse_bool")),
    ("time",        ("now_ms", "now_sec", "format", "sleep_ms")),
    ("net",         ("ping", "resolve", "get", "post", "put", "delete", "download")),
    ("http",        ("get", "post", "ok", "not_found", "created", "bad_request",
                     "internal_error", "redirect")),
    ("server",      ("route", "listen", "listen_async", "serve_static", "stop",
                     "middleware", "cors", "websocket")),
    ("html",        ("page", "h1", "h2", "h3", "p", "div", "span", "a", "escape",
                     "body", "head", "style", "script", "link", "img", "form",
                     "input", "button", "table", "ul", "li", "nav", "footer", "header")),
    ("css",         ("rule", "class", "stylesheet", "id", "media", "keyframe")),
    ("db",          ("open", "exec", "query", "close", "begin", "commit",
                     "rollback", "prepare", "bind")),
    ("ai",          ("model_new", "train", "predict", "loss", "epochs", "save",
                     "load", "accuracy", "layers")),
    ("numpy",       ("version", "array", "zeros", "ones", "mean", "dot", "shape",
                     "reshape", "sum", "std", "max", "min", "argmax", "linspace",
                     "arange", "random", "random_normal", "matmul", "transpose")),
    ("torch",       ("version", "tensor", "relu", "train_linear", "save", "load",
                     "sigmoid", "tanh", "softmax", "cross_entropy", "adam",
                     "backward", "forward", "no_grad")),
    ("tensorflow",  ("version", "train_xor", "predict", "model", "sequential",
                     "dense", "compile", "fit", "evaluate")),
    ("cv",          ("version", "read_size", "grayscale", "resize", "blur",
                     "read", "write", "show", "threshold", "canny", "detect_faces")),
    ("pandas",      ("version", "read_csv", "rows", "mean", "head_json", "describe",
                     "groupby", "merge", "pivot", "fillna", "dropna", "sort")),
    ("sklearn",     ("version", "fit_linear", "predict", "score", "fit_logistic",
                     "fit_svm", "fit_tree", "fit_forest", "split", "cross_val")),
    ("plot",        ("version", "line", "hist", "scatter", "bar", "pie", "save",
                     "show", "figure", "subplot", "xlabel", "ylabel", "title")),
    ("gui",         ("window", "label", "button", "run", "alert", "input",
                     "checkbox", "radiobutton", "listbox", "canvas", "menu",
                     "filedialog", "messagebox", "grid", "pack", "place")),
    ("vec",         ("new", "push", "len", "get", "set", "remove", "clear",
                     "sort", "reverse", "contains", "index_of", "pop", "insert",
                     "slice", "map", "filter", "find")),
    ("hashmap",     ("new", "insert", "get", "get_or", "remove", "contains",
                     "len", "keys", "values", "clear", "entries", "merge")),
    ("rand",        ("seed", "next_f32", "next_i32", "range", "shuffle", "choice")),
    ("hash",        ("fnv1a", "sha256", "md5", "crc32")),
    ("thread",      ("spawn", "join", "sleep_ms", "current", "mutex_new",
                     "mutex_lock", "mutex_unlock", "channel_new", "send", "recv")),
    ("sync",        ("atomic_i32", "atomic_load", "atomic_store", "atomic_add",
                     "barrier", "semaphore_new", "semaphore_wait", "semaphore_post")),
    ("crypto",      ("sha256", "sha512", "md5", "hmac", "aes_encrypt",
                     "aes_decrypt", "base64_encode", "base64_decode", "random_bytes")),
    ("mem",         ("alloc", "free", "copy", "set", "size_of", "align_of")),
    ("option",      ("some", "none", "is_some", "is_none", "unwrap", "unwrap_or",
                     "map", "and_then", "or_else", "filter", "flatten")),
    ("result",      ("ok", "err", "is_ok", "is_err", "unwrap", "unwrap_or",
                     "map", "map_err", "and_then", "or_else")),
    ("iter",        ("map", "filter", "fold", "collect", "enumerate", "zip",
                     "take", "skip", "chain", "flat_map", "any", "all", "count",
                     "find", "position", "min", "max", "sum", "product",
                     "last", "nth", "peekable", "step_by", "cycle")),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Erreurs sémantiques
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SemanticError(Exception):
    message: str

    def __str__(self) -> str:
        return f"[Semantic] {self.message}"


@dataclass
class SemanticWarning:
    message: str
    line:    int = 0
    col:     int = 0


# ═══════════════════════════════════════════════════════════════════════════════
#  Symbole dans la table des symboles
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Symbol:
    name:     str
    type:     TypeNode
    vtype:    VynType       = field(default_factory=lambda: T_UNKN)
    is_mut:   bool          = False
    is_hot:   bool          = False
    is_const: bool          = False
    kind:     str           = "variable"   # "variable" | "fn" | "struct" | "enum" | "const" | "type"
    span:     Span          = field(default_factory=Span)


@dataclass
class StructInfo:
    name:     str
    fields:   Dict[str, Field]
    generics: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  Analyseur sémantique
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticAnalyzer:
    """Analyseur sémantique complet pour Vyn.

    Vérifie :
    - Existence des symboles (variables, fonctions, modules)
    - Nombre d'arguments des appels de fonctions
    - Types compatibles sur les affectations et les opérations
    - Immutabilité (const, let non-mut)
    - Option/Result, closures, for/while, patterns
    - Imports et modules
    - Génériques
    """

    PRIMITIVES: Set[str] = {
        "i8","i16","i32","i64",
        "u8","u16","u32","u64",
        "f32","f64","bool","str","char","void","usize","isize",
    }

    COPY_TYPES: Set[str] = {
        "i8","i16","i32","i64",
        "u8","u16","u32","u64",
        "f32","f64","bool","char","usize","isize",
    }

    def __init__(self) -> None:
        self.structs:           Dict[str, StructInfo]   = {}
        self.functions:         Dict[str, FunctionDecl] = {}
        self.externs:           Dict[str, ExternDecl]   = {}
        self.enums:             Dict[str, EnumDecl]     = {}
        self.traits:            Dict[str, TraitDecl]    = {}
        self.type_aliases:      Dict[str, TypeNode]     = {}
        self.consts:            Dict[str, Symbol]       = {}
        self.scopes:            List[Dict[str, Symbol]] = [self._builtin_scope()]
        self.errors:            List[str]               = []
        self.warnings:          List[str]               = []
        self.profiled_functions:List[str]               = []
        self.hot_functions:     List[str]               = []
        self._current_fn:       Optional[FunctionDecl]  = None
        self._loop_depth:       int                     = 0
        self._generic_params:   Set[str]                = set()
        # Registre de types (pour le type system avancé)
        self._registry:         TypeRegistry            = STDLIB_REGISTRY
        # Modules importés (path → set de symboles)
        self._imported_modules: Dict[str, Set[str]]     = {}
        # Cache de signatures de fonctions pour vérification de l'arité
        self._fn_sigs:          Dict[str, Tuple[int, int]] = {}
        # (min_args, max_args) — max -1 = variadique

    # ══════════════════════════════════════════════════════════════════════════
    #  Portée builtin
    # ══════════════════════════════════════════════════════════════════════════

    def _builtin_scope(self) -> Dict[str, Symbol]:
        syms: Dict[str, Symbol] = {}
        for mod, methods in _STD_SYMBOLS:
            for m in methods:
                key = f"{mod}.{m}"
                syms[key] = Symbol(key, TypeNode("fn"), T_UNKN, False, False, False, "fn")
        # Constructeurs Option/Result
        for name in ("Some", "None", "Ok", "Err"):
            syms[name] = Symbol(name, TypeNode("fn"), T_UNKN, False, False, False, "fn")
        return syms

    # ══════════════════════════════════════════════════════════════════════════
    #  Point d'entrée
    # ══════════════════════════════════════════════════════════════════════════

    def analyze(self, program: Program) -> None:
        """Analyse complète du programme."""
        # ── Phase 1 : imports ─────────────────────────────────────────────────
        for imp in program.imports:
            self._resolve_import(imp)
            self._load_module_symbols(imp.path)
        for u in getattr(program, "uses", []):
            self._resolve_import(ImportDecl(u.path))
            self._load_module_symbols(u.path)

        # ── Phase 2 : chargement des dépendances VPM ─────────────────────────
        self._load_manifest_deps()

        # ── Phase 3 : enregistrement des déclarations top-level ───────────────
        self._register_declarations(program)

        # ── Phase 4 : vérification des corps ─────────────────────────────────
        for fn in program.functions:
            self._check_function(fn)
        for impl in program.impls:
            for m in impl.methods:
                self._check_method(impl.struct_name, m)
        for stmt in getattr(program, "init_stmts", []):
            self._check_stmt(stmt, TypeNode("void"))

        # ── Phase 5 : vérification des consts ────────────────────────────────
        for c in program.consts:
            self._infer(c.value)

        if self.errors:
            raise SemanticError("\n".join(self.errors))

    # ══════════════════════════════════════════════════════════════════════════
    #  Enregistrement des déclarations
    # ══════════════════════════════════════════════════════════════════════════

    def _register_declarations(self, program: Program) -> None:
        """Enregistre tous les types, fonctions et constantes dans les tables."""
        # Externs
        for ext in program.externs:
            self.externs[ext.name] = ext
            n_params = len(ext.params)
            self._fn_sigs[ext.name] = (n_params, n_params)

        # Structs
        for s in program.structs:
            self.structs[s.name] = StructInfo(
                s.name,
                {f.name: f for f in s.fields},
                [g.name for g in s.generics],
            )
            self._registry.register_struct(
                s.name,
                {f.name: from_node(f.type) for f in s.fields},
                [g.name for g in s.generics],
            )

        # Enums
        for e in program.enums:
            self.enums[e.name] = e
            variants = {v.name: (from_node(v.payload) if v.payload else None) for v in e.variants}
            self._registry.register_enum(e.name, variants, [g.name for g in e.generics])

        # Type aliases
        for ta in program.type_aliases:
            self.type_aliases[ta.name] = ta.target

        # Consts
        for c in program.consts:
            sym = Symbol(c.name, c.type, from_node(c.type), False, False, True, "const")
            self.consts[c.name] = sym
            self._define(sym)

        # Traits
        for t in program.traits:
            self.traits[t.name] = t

        # Modules (mod)
        for mod in getattr(program, "mods", []):
            for fn in mod.functions:
                key = f"{mod.name}.{fn.name}"
                self.functions[key] = fn
                n = len(fn.params)
                self._fn_sigs[key] = (n, n)
            for s in mod.structs:
                self.structs[s.name] = StructInfo(s.name, {f.name: f for f in s.fields})
            for e in mod.enums:
                self.enums[e.name] = e
            for c in mod.consts:
                key = f"{mod.name}.{c.name}"
                self.consts[key] = Symbol(key, c.type, from_node(c.type), False, False, True, "const")

        # Fonctions top-level
        for fn in program.functions:
            self.functions[fn.name] = fn
            if fn.is_hot:
                self.hot_functions.append(fn.name)
            if any(a.name == "profile" for a in fn.attributes):
                self.profiled_functions.append(fn.name)
            # Arité : on ne compte pas 'self' comme paramètre d'arité externe
            n_params = len([p for p in fn.params if p.name != "self"])
            has_default = any(p.default is not None for p in fn.params)
            min_args = len([p for p in fn.params if p.name != "self" and p.default is None])
            self._fn_sigs[fn.name] = (min_args, n_params if not has_default else n_params)
            # Enregistrer dans le registry
            param_types = [from_node(p.type) for p in fn.params if p.name != "self"]
            ret_type = from_node(fn.return_type)
            self._registry.register_fn(fn.name, param_types, ret_type)

        # Méthodes impl
        for impl in program.impls:
            for m in impl.methods:
                key = f"{impl.struct_name}.{m.name}"
                self.functions[key] = m
                n_params = len([p for p in m.params if p.name != "self"])
                self._fn_sigs[key] = (n_params, n_params)

    # ══════════════════════════════════════════════════════════════════════════
    #  Chargement de modules
    # ══════════════════════════════════════════════════════════════════════════

    def _load_module_symbols(self, path: str) -> None:
        """Charge les symboles d'un module depuis stdlib/ ou vendor/."""
        for base, suffix in ((VENDOR, "lib.vyn"), (STDLIB, ".vyn")):
            if suffix == "lib.vyn":
                lib = base / path / "lib.vyn"
            else:
                # std.io → stdlib/std/io.vyn
                parts = path.replace("std.", "").split(".")
                lib = STDLIB / "std" / f"{'/'.join(parts)}.vyn"
            if lib.exists():
                try:
                    from vyn.parser.parser import Parser
                    sub = Parser(lib.read_text(encoding="utf-8")).parse()
                    for fn in sub.functions:
                        self.functions[fn.name] = fn
                        n = len(fn.params)
                        self._fn_sigs[fn.name] = (n, n)
                except Exception:
                    pass
                # Enregistrer les symboles publics dans la portée builtin
                mod_short = path.split(".")[-1]
                if mod_short in {m for m, _ in _STD_SYMBOLS}:
                    self._imported_modules[mod_short] = set()
                break

    def _load_manifest_deps(self) -> None:
        """Charge les packages listés dans vyn.toml."""
        manifest = ROOT / "vyn.toml"
        if not manifest.exists():
            return
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore
            data = tomllib.loads(manifest.read_text(encoding="utf-8"))
            for dep in data.get("dependencies", {}):
                self._load_module_symbols(dep)
        except Exception:
            pass

    def _resolve_import(self, imp: ImportDecl) -> None:
        """Vérifie que l'import est valide."""
        allowed_prefixes = ("std.", "std")
        if imp.path.startswith("std.") or imp.path == "std":
            return
        if imp.path in {"std"}:
            return
        pkg = VENDOR / imp.path / "lib.vyn"
        if pkg.exists():
            return
        # Pas une erreur fatale, juste un avertissement
        self.warnings.append(f"import potentiellement introuvable: '{imp.path}' (vpm add {imp.path}?)")

    # ══════════════════════════════════════════════════════════════════════════
    #  Portées
    # ══════════════════════════════════════════════════════════════════════════

    def _push(self) -> None:
        self.scopes.append({})

    def _pop(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop()

    def _define(self, sym: Symbol) -> None:
        if sym.name in self.scopes[-1]:
            self.warnings.append(f"redéfinition du symbole: {sym.name}")
        self.scopes[-1][sym.name] = sym

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name in self.consts:
            return self.consts[name]
        return None

    # ══════════════════════════════════════════════════════════════════════════
    #  Vérification de fonctions
    # ══════════════════════════════════════════════════════════════════════════

    def _check_function(self, fn: FunctionDecl) -> None:
        """Vérifie le corps d'une fonction."""
        saved_fn = self._current_fn
        self._current_fn = fn

        # Enregistrer les paramètres génériques
        saved_generics = self._generic_params.copy()
        for g in fn.generics:
            self._generic_params.add(g.name)

        self._push()
        for p in fn.params:
            vtype = from_node(p.type) if p.type.name != "Self" else T_UNKN
            self._define(Symbol(p.name, p.type, vtype, p.is_mut, False, False, "variable"))
        for stmt in fn.body:
            self._check_stmt(stmt, fn.return_type)
        self._pop()

        self._generic_params = saved_generics
        self._current_fn = saved_fn

    def _check_method(self, struct_name: str, fn: FunctionDecl) -> None:
        """Vérifie le corps d'une méthode (avec self)."""
        saved_fn = self._current_fn
        self._current_fn = fn

        self._push()
        struct_type = TypeNode(struct_name)
        self._define(Symbol("self", struct_type, from_node(struct_type), False, False, False, "variable"))
        for p in fn.params:
            if p.name == "self":
                continue
            vtype = from_node(p.type)
            self._define(Symbol(p.name, p.type, vtype, p.is_mut, False, False, "variable"))
        for stmt in fn.body:
            self._check_stmt(stmt, fn.return_type)
        self._pop()

        self._current_fn = saved_fn

    # ══════════════════════════════════════════════════════════════════════════
    #  Vérification de statements
    # ══════════════════════════════════════════════════════════════════════════

    def _check_stmt(self, stmt: Stmt, ret: TypeNode) -> None:
        """Vérifie un statement."""
        if stmt is None:
            return

        # ── let ───────────────────────────────────────────────────────────────
        if isinstance(stmt, LetStmt):
            if stmt.value is not None:
                val_type = self._infer(stmt.value)
                if stmt.type and not self._types_compat(stmt.type, val_type):
                    self.errors.append(
                        f"type incompatible: attendu '{stmt.type}', "
                        f"obtenu '{val_type}' pour '{stmt.name}'"
                    )
            declared_type = stmt.type or (self._type_node_of(self._infer(stmt.value)) if stmt.value else TypeNode("void"))
            vtype = from_node(declared_type) if declared_type else T_UNKN
            self._define(Symbol(stmt.name, declared_type, vtype, stmt.is_mut, False, False, "variable"))

        # ── let tuple ─────────────────────────────────────────────────────────
        elif isinstance(stmt, LetTupleStmt):
            val_type = self._infer(stmt.value)
            for name in stmt.names:
                self._define(Symbol(name, TypeNode("void"), T_UNKN, stmt.is_mut, False, False, "variable"))

        # ── assignation ───────────────────────────────────────────────────────
        elif isinstance(stmt, AssignStmt):
            self._check_assign(stmt)

        # ── return ────────────────────────────────────────────────────────────
        elif isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                val_type = self._infer(stmt.value)
                if ret.name not in ("void", "?") and not self._types_compat(ret, val_type):
                    self.errors.append(
                        f"type de retour incompatible: attendu '{ret}', obtenu '{val_type}'"
                    )

        # ── if ────────────────────────────────────────────────────────────────
        elif isinstance(stmt, IfStmt):
            self._infer(stmt.condition)
            self._push()
            for s in stmt.then_body:
                self._check_stmt(s, ret)
            self._pop()
            if stmt.else_body:
                self._push()
                for s in stmt.else_body:
                    self._check_stmt(s, ret)
                self._pop()

        # ── if let ────────────────────────────────────────────────────────────
        elif isinstance(stmt, IfLetStmt):
            val_type = self._infer(stmt.value)
            self._push()
            self._bind_pattern(stmt.pattern, val_type)
            for s in stmt.then_body:
                self._check_stmt(s, ret)
            self._pop()
            if stmt.else_body:
                self._push()
                for s in stmt.else_body:
                    self._check_stmt(s, ret)
                self._pop()

        # ── while ─────────────────────────────────────────────────────────────
        elif isinstance(stmt, WhileStmt):
            self._infer(stmt.condition)
            self._loop_depth += 1
            self._push()
            for s in stmt.body:
                self._check_stmt(s, ret)
            self._pop()
            self._loop_depth -= 1

        # ── for ───────────────────────────────────────────────────────────────
        elif isinstance(stmt, ForStmt):
            iter_type = self._infer(stmt.iterable)
            self._loop_depth += 1
            self._push()
            # Déduire le type de la variable de boucle
            var_type = self._iter_elem_type(iter_type, stmt.var_type)
            vtype = from_node(var_type)
            self._define(Symbol(stmt.var, var_type, vtype, False, False, False, "variable"))
            for s in stmt.body:
                self._check_stmt(s, ret)
            self._pop()
            self._loop_depth -= 1

        # ── loop ──────────────────────────────────────────────────────────────
        elif isinstance(stmt, LoopStmt):
            self._loop_depth += 1
            if stmt.iterator:
                var, it = stmt.iterator
                iter_type = self._infer(it)
                self._push()
                elem_type = self._iter_elem_type(iter_type, None)
                self._define(Symbol(var, elem_type, from_node(elem_type), False, False, False, "variable"))
                for s in stmt.body:
                    self._check_stmt(s, ret)
                self._pop()
            else:
                self._push()
                for s in stmt.body:
                    self._check_stmt(s, ret)
                self._pop()
            self._loop_depth -= 1

        # ── break / continue ──────────────────────────────────────────────────
        elif isinstance(stmt, (BreakStmt, ContinueStmt)):
            if self._loop_depth == 0:
                self.errors.append(f"'{'break' if isinstance(stmt, BreakStmt) else 'continue'}' hors d'une boucle")

        # ── match ─────────────────────────────────────────────────────────────
        elif isinstance(stmt, MatchStmt):
            self._check_match(stmt, ret)

        # ── try/catch ─────────────────────────────────────────────────────────
        elif isinstance(stmt, TryStmt):
            self._push()
            for s in stmt.body:
                self._check_stmt(s, ret)
            self._pop()
            self._push()
            self._define(Symbol(stmt.catch_var, TypeNode("str"), T_STR, False, False, False, "variable"))
            for s in stmt.catch_body:
                self._check_stmt(s, ret)
            self._pop()
            if stmt.finally_body:
                self._push()
                for s in stmt.finally_body:
                    self._check_stmt(s, ret)
                self._pop()

        # ── throw ─────────────────────────────────────────────────────────────
        elif isinstance(stmt, ThrowStmt):
            self._infer(stmt.value)

        # ── fonction locale ───────────────────────────────────────────────────
        elif isinstance(stmt, LocalFnStmt):
            fn = stmt.decl
            self.functions[fn.name] = fn
            n = len(fn.params)
            self._fn_sigs[fn.name] = (n, n)
            self._check_function(fn)
            self._define(Symbol(fn.name, TypeNode("fn"), T_UNKN, False, fn.is_hot, False, "fn"))

        # ── expr statement ────────────────────────────────────────────────────
        elif isinstance(stmt, ExprStmt):
            self._infer(stmt.expr)

    # ── assignation ───────────────────────────────────────────────────────────

    def _check_assign(self, stmt: AssignStmt) -> None:
        """Vérifie une assignation avec vérification d'immutabilité."""
        val_type = self._infer(stmt.value)

        if isinstance(stmt.target, Identifier):
            name = stmt.target.name
            if name in self.consts:
                self.errors.append(f"impossible d'assigner à la constante: '{name}'")
                return
            sym = self._lookup(name)
            if sym:
                if not sym.is_mut:
                    self.errors.append(f"impossible d'assigner à '{name}': variable immutable (utilisez 'let mut')")
                else:
                    if not self._types_compat(sym.type, val_type):
                        self.warnings.append(f"type potentiellement incompatible pour '{name}'")
            else:
                self.errors.append(f"identifiant inconnu: '{name}'")

        elif isinstance(stmt.target, BinaryOp) and stmt.target.op == "[]":
            self._infer(stmt.target.left)
            self._infer(stmt.target.right)

        elif isinstance(stmt.target, IndexExpr):
            self._infer(stmt.target.object)
            self._infer(stmt.target.index)

        elif isinstance(stmt.target, MemberAccess):
            self._infer(stmt.target.object)

        else:
            self._infer(stmt.target)

    # ── match ─────────────────────────────────────────────────────────────────

    def _check_match(self, stmt: MatchStmt, ret: TypeNode) -> None:
        """Vérifie un match complet."""
        match_type = self._infer(stmt.expr)

        # Nouvelles branches MatchArm
        for arm in stmt.arms:
            self._push()
            self._bind_pattern(arm.pattern, match_type)
            if arm.guard:
                guard_t = self._infer(arm.guard)
                # La guard doit être un bool
            for s in arm.body:
                self._check_stmt(s, ret)
            self._pop()

        # Legacy MatchCase (rétro-compat)
        if not stmt.arms:
            for case in stmt.cases:
                if case.pattern is not None:
                    self._infer(case.pattern)
                self._push()
                for s in case.body:
                    self._check_stmt(s, ret)
                self._pop()

    # ─── binding de patterns ──────────────────────────────────────────────────

    def _bind_pattern(self, pat: Pattern, match_type) -> None:
        """Lie les variables d'un pattern dans la portée courante."""
        if isinstance(pat, WildcardPattern):
            return

        if isinstance(pat, IdentPattern):
            # Déduire le type depuis match_type si possible
            vtype = match_type if isinstance(match_type, VynType) else T_UNKN
            type_node = to_node(vtype) if isinstance(vtype, VynType) else TypeNode("void")
            self._define(Symbol(pat.name, type_node, vtype, pat.is_mut, False, False, "variable"))

        elif isinstance(pat, LiteralPattern):
            self._infer(pat.value)

        elif isinstance(pat, EnumPattern):
            # Si c'est Some(x), Ok(x), Err(x) → lier x avec le type intérieur
            vtype = match_type if isinstance(match_type, VynType) else T_UNKN
            if pat.payload:
                inner_type = T_UNKN
                if isinstance(vtype, VynType):
                    if vtype.is_option() and pat.variant_name == "Some":
                        inner_type = vtype.inner()
                    elif vtype.is_result():
                        if pat.variant_name == "Ok":
                            inner_type = vtype.ok_type()
                        elif pat.variant_name == "Err":
                            inner_type = vtype.err_type()
                self._bind_pattern(pat.payload, inner_type)

        elif isinstance(pat, TuplePattern):
            for elem_pat in pat.elements:
                self._bind_pattern(elem_pat, T_UNKN)

        elif isinstance(pat, StructPattern):
            struct_info = self.structs.get(pat.struct_name)
            for fname, fpat in pat.fields.items():
                field_type = T_UNKN
                if struct_info and fname in struct_info.fields:
                    field_type = from_node(struct_info.fields[fname].type)
                self._bind_pattern(fpat, field_type)

        elif isinstance(pat, OrPattern):
            for p in pat.patterns:
                self._bind_pattern(p, match_type)

        elif isinstance(pat, RangePattern):
            self._infer(pat.start)
            self._infer(pat.end)

    # ══════════════════════════════════════════════════════════════════════════
    #  Inférence de types
    # ══════════════════════════════════════════════════════════════════════════

    def _infer(self, expr: Optional[Expr]) -> VynType:
        """Infère le type d'une expression. Ne lève pas d'exception."""
        if expr is None:
            return T_VOID

        # ── littéraux ─────────────────────────────────────────────────────────
        if isinstance(expr, IntLiteral):
            return T_I32
        if isinstance(expr, FloatLiteral):
            return T_F32
        if isinstance(expr, BoolLiteral):
            return T_BOOL
        if isinstance(expr, StringLiteral):
            return T_STR
        if isinstance(expr, CharLiteral):
            return T_CHAR
        if isinstance(expr, NilLiteral):
            return VynType.option(T_UNKN)   # nil ~ None ~ Option<_>

        # ── Option / Result ───────────────────────────────────────────────────
        if isinstance(expr, NoneExpr):
            return VynType.option(T_UNKN)
        if isinstance(expr, SomeExpr):
            inner = self._infer(expr.value)
            return VynType.option(inner)
        if isinstance(expr, OkExpr):
            inner = self._infer(expr.value)
            return VynType.result(inner, T_STR)
        if isinstance(expr, ErrExpr):
            inner = self._infer(expr.value)
            return VynType.result(T_UNKN, inner)

        # ── identifiant ───────────────────────────────────────────────────────
        if isinstance(expr, Identifier):
            return self._infer_identifier(expr.name)

        # ── opérateurs binaires ───────────────────────────────────────────────
        if isinstance(expr, BinaryOp):
            return self._infer_binary(expr)

        # ── opérateur unaire ──────────────────────────────────────────────────
        if isinstance(expr, UnaryOp):
            inner = self._infer(expr.operand)
            if expr.op == "!":
                return T_BOOL
            if expr.op == "&" or expr.op.startswith("&"):
                return VynType.ref_(inner)
            return inner

        # ── cast as ───────────────────────────────────────────────────────────
        if isinstance(expr, CastExpr):
            self._infer(expr.expr)
            return from_node(expr.to)

        # ── appel ─────────────────────────────────────────────────────────────
        if isinstance(expr, CallExpr):
            return self._infer_call(expr)

        # ── accès membre ──────────────────────────────────────────────────────
        if isinstance(expr, MemberAccess):
            return self._infer_member_access(expr)

        # ── indexation ────────────────────────────────────────────────────────
        if isinstance(expr, IndexExpr):
            arr = self._infer(expr.object)
            self._infer(expr.index)
            if arr.kind == TKind.ARRAY and arr.params:
                return arr.params[0]
            if arr.kind == TKind.VEC and arr.params:
                return arr.params[0]
            if arr.is_str():
                return T_CHAR
            return T_UNKN

        # ── tuple index ───────────────────────────────────────────────────────
        if isinstance(expr, TupleIndex):
            tup = self._infer(expr.object)
            if tup.kind == TKind.TUPLE and expr.index < len(tup.params):
                return tup.params[expr.index]
            return T_UNKN

        # ── struct init ───────────────────────────────────────────────────────
        if isinstance(expr, StructInit):
            self._check_struct_init(expr)
            return VynType.struct_(expr.struct_name)

        # ── tableau ───────────────────────────────────────────────────────────
        if isinstance(expr, ArrayLiteral):
            if expr.repeat:
                elem_type = self._infer(expr.repeat[0])
                return VynType.array(elem_type, expr.repeat[1])
            if expr.elements:
                elem_type = self._infer(expr.elements[0])
                for e in expr.elements[1:]:
                    self._infer(e)
                return VynType.array(elem_type)
            return VynType.array(T_UNKN)

        # ── tuple ─────────────────────────────────────────────────────────────
        if isinstance(expr, TupleExpr):
            elem_types = [self._infer(e) for e in expr.elements]
            return VynType.tuple_(*elem_types)

        # ── map literal ───────────────────────────────────────────────────────
        if isinstance(expr, MapLiteral):
            if expr.entries:
                k = self._infer(expr.entries[0][0])
                v = self._infer(expr.entries[0][1])
                for ek, ev in expr.entries[1:]:
                    self._infer(ek)
                    self._infer(ev)
                return VynType.hashmap(k, v)
            return VynType.hashmap(T_UNKN, T_UNKN)

        # ── range ─────────────────────────────────────────────────────────────
        if isinstance(expr, RangeExpr):
            self._infer(expr.start)
            self._infer(expr.end)
            return VynType.struct_("Range")

        # ── ? propagation ─────────────────────────────────────────────────────
        if isinstance(expr, QuestionExpr):
            inner = self._infer(expr.expr)
            if inner.is_option():
                return inner.inner()
            if inner.is_result():
                return inner.ok_type()
            return inner

        # ── closure ───────────────────────────────────────────────────────────
        if isinstance(expr, ClosureExpr):
            return self._infer_closure(expr)

        # ── if expr ───────────────────────────────────────────────────────────
        if isinstance(expr, IfExpr):
            self._infer(expr.condition)
            t1 = self._infer(expr.then_expr)
            t2 = self._infer(expr.else_expr)
            return t1 if t1 != T_UNKN else t2

        # Fallback
        return T_UNKN

    # ── identifiant ───────────────────────────────────────────────────────────

    def _infer_identifier(self, name: str) -> VynType:
        """Infère le type d'un identifiant."""
        # Variable de type générique
        if name in self._generic_params:
            return VynType.var(name)

        # Constante
        if name in self.consts:
            return self.consts[name].vtype

        # Option/Result constructeurs
        if name == "None":
            return VynType.option(T_UNKN)
        if name == "Some":
            return VynType.fn_(T_UNKN, ret=VynType.option(T_UNKN))
        if name == "Ok":
            return VynType.fn_(T_UNKN, ret=VynType.result(T_UNKN, T_STR))
        if name == "Err":
            return VynType.fn_(T_UNKN, ret=VynType.result(T_UNKN, T_UNKN))

        # Enum variant (unit)
        for ename, edecl in self.enums.items():
            for v in edecl.variants:
                if v.name == name:
                    if v.payload:
                        return VynType.fn_(from_node(v.payload), ret=VynType.enum_(ename))
                    return VynType.enum_(ename)

        # Portée lexicale
        sym = self._lookup(name)
        if sym:
            return sym.vtype if sym.vtype != T_UNKN else from_node(sym.type)

        # Fonction connue
        if name in self.functions:
            fn = self.functions[name]
            param_types = [from_node(p.type) for p in fn.params if p.name != "self"]
            ret = from_node(fn.return_type)
            return VynType.fn_(*param_types, ret=ret)

        # Extern
        if name in self.externs:
            ext = self.externs[name]
            param_types = [from_node(p.type) for p in ext.params]
            ret = from_node(ext.return_type)
            return VynType.fn_(*param_types, ret=ret)

        # Struct (comme type, pas comme valeur)
        if name in self.structs:
            return VynType.struct_(name)

        self.errors.append(f"identifiant inconnu: '{name}'")
        return T_UNKN

    # ── appels de fonctions ───────────────────────────────────────────────────

    def _infer_call(self, expr: CallExpr) -> VynType:
        """Infère le type d'un appel de fonction avec vérification de l'arité."""
        args = expr.args
        n_args = len(args)

        # Vérifier les arguments
        for a in args:
            self._infer(a)

        # ── Appel de méthode : obj.method(args) ──────────────────────────────
        if isinstance(expr.callee, MemberAccess):
            return self._infer_member_call(expr.callee.object, expr.callee.member, args)

        # ── Appel direct : name(args) ─────────────────────────────────────────
        if isinstance(expr.callee, Identifier):
            name = expr.callee.name

            # Constructeurs spéciaux
            if name == "Some":
                if n_args != 1:
                    self.errors.append(f"'Some' attend 1 argument, reçu {n_args}")
                inner = self._infer(args[0]) if args else T_UNKN
                return VynType.option(inner)
            if name == "Ok":
                if n_args != 1:
                    self.errors.append(f"'Ok' attend 1 argument, reçu {n_args}")
                inner = self._infer(args[0]) if args else T_UNKN
                return VynType.result(inner, T_STR)
            if name == "Err":
                if n_args != 1:
                    self.errors.append(f"'Err' attend 1 argument, reçu {n_args}")
                inner = self._infer(args[0]) if args else T_UNKN
                return VynType.result(T_UNKN, inner)

            # Variant d'enum avec payload
            for ename, edecl in self.enums.items():
                for v in edecl.variants:
                    if v.name == name and v.payload:
                        if n_args != 1:
                            self.errors.append(f"variant '{name}' attend 1 argument, reçu {n_args}")
                        return VynType.enum_(ename)

            # Fonction connue
            if name in self.functions:
                fn = self.functions[name]
                return self._check_fn_call(name, fn.params, from_node(fn.return_type), args)

            # Extern
            if name in self.externs:
                ext = self.externs[name]
                return self._check_fn_call(name, ext.params, from_node(ext.return_type), args, is_vararg=True)

            # Signature connue
            if name in self._fn_sigs:
                min_a, max_a = self._fn_sigs[name]
                if n_args < min_a or (max_a >= 0 and n_args > max_a):
                    self.errors.append(
                        f"'{name}' attend {min_a}–{max_a} argument(s), reçu {n_args}"
                    )

            # Variable de type closure
            sym = self._lookup(name)
            if sym:
                t = sym.vtype
                if t.is_callable():
                    return t.ret_type()
                return T_UNKN

            # Registre stdlib
            sig = self._registry.fn_sig(name)
            if sig:
                return sig.ret_type

            self.errors.append(f"fonction inconnue: '{name}'")
            return T_UNKN

        # ── Appel d'une closure ───────────────────────────────────────────────
        callee_type = self._infer(expr.callee)
        if callee_type.is_callable():
            return callee_type.ret_type()
        return T_UNKN

    def _check_fn_call(
        self,
        name: str,
        params: List[Param],
        ret: VynType,
        args: List[Expr],
        is_vararg: bool = False,
    ) -> VynType:
        """Vérifie l'arité et retourne le type de retour."""
        real_params = [p for p in params if p.name != "self"]
        n_params    = len(real_params)
        n_args      = len(args)
        min_params  = len([p for p in real_params if p.default is None])

        is_vararg_fn = is_vararg or any(p.name == "..." for p in real_params)
        if not is_vararg_fn:
            if n_args < min_params:
                self.errors.append(
                    f"'{name}' attend au moins {min_params} argument(s), reçu {n_args}"
                )
            elif n_args > n_params:
                self.errors.append(
                    f"'{name}' attend {n_params} argument(s), reçu {n_args}"
                )
        return ret

    # ── accès membre ──────────────────────────────────────────────────────────

    def _infer_member_access(self, expr: MemberAccess) -> VynType:
        """Infère le type d'un accès membre (obj.field ou mod.sym)."""
        obj_type = self._infer(expr.object)
        member   = expr.member

        # Accès module (obj est un identifiant connu comme module)
        if isinstance(expr.object, Identifier):
            mod = expr.object.name
            full = f"{mod}.{member}"
            # Symbole stdlib connu
            sym = self._lookup(full)
            if sym:
                return sym.vtype if sym.vtype != T_UNKN else T_UNKN
            # Fonction connue avec namespace
            if full in self.functions:
                fn = self.functions[full]
                return from_node(fn.return_type)
            # Registre
            sig = self._registry.fn_sig(full)
            if sig:
                return sig.ret_type
            # Constante de module
            if full in self.consts:
                return self.consts[full].vtype

        # Accès de champ sur struct
        if obj_type.kind == TKind.STRUCT:
            field_vtype = self._registry.field_type(obj_type.name, member)
            if field_vtype:
                return field_vtype
            struct_info = self.structs.get(obj_type.name)
            if struct_info and member in struct_info.fields:
                return from_node(struct_info.fields[member].type)

        # Accès de variant d'enum
        if isinstance(expr.object, Identifier):
            enum_name = expr.object.name
            if enum_name in self.enums:
                edecl = self.enums[enum_name]
                for v in edecl.variants:
                    if v.name == member:
                        if v.payload:
                            return VynType.fn_(from_node(v.payload), ret=VynType.enum_(enum_name))
                        return VynType.enum_(enum_name)

        return T_UNKN

    def _infer_member_call(self, obj: Expr, method: str, args: List[Expr]) -> VynType:
        """Infère le type d'un appel de méthode obj.method(args)."""
        obj_type = self._infer(obj)
        n_args   = len(args)

        # Objet = identifiant → accès module std
        if isinstance(obj, Identifier):
            mod  = obj.name
            full = f"{mod}.{method}"

            # Méthodes sur Option
            if mod == "option" or obj_type.is_option():
                return self._infer_option_method(obj_type, method, args)

            # Méthodes sur Result
            if mod == "result" or obj_type.is_result():
                return self._infer_result_method(obj_type, method, args)

            # Fonction dans les fonctions connues
            if full in self.functions:
                fn = self.functions[full]
                return self._check_fn_call(full, fn.params, from_node(fn.return_type), args)

            # Registre stdlib
            sig = self._registry.fn_sig(full)
            if sig:
                return sig.ret_type

            # Symbole builtin (std.*) — arité inconnue, on accepte
            sym = self._lookup(full)
            if sym:
                return T_UNKN

        # Méthode sur type struct
        if obj_type.kind == TKind.STRUCT:
            method_key = f"{obj_type.name}.{method}"
            if method_key in self.functions:
                fn = self.functions[method_key]
                return self._check_fn_call(method_key, fn.params, from_node(fn.return_type), args)

        # Méthodes builtin sur tableaux
        if obj_type.kind in (TKind.ARRAY, TKind.VEC):
            return self._infer_array_method(obj_type, method, args)

        # Méthodes builtin sur str
        if obj_type.is_str():
            return self._infer_str_method(method, args)

        return T_UNKN

    def _infer_option_method(self, opt_type: VynType, method: str, args: List[Expr]) -> VynType:
        """Type des méthodes sur Option<T>."""
        inner = opt_type.inner() if opt_type.is_option() else T_UNKN
        methods = {
            "is_some":    T_BOOL,
            "is_none":    T_BOOL,
            "unwrap":     inner,
            "unwrap_or":  inner,
            "map":        VynType.option(T_UNKN),
            "and_then":   VynType.option(T_UNKN),
            "or_else":    opt_type,
            "filter":     opt_type,
            "flatten":    inner,
            "take":       opt_type,
            "expect":     inner,
        }
        for a in args:
            self._infer(a)
        return methods.get(method, T_UNKN)

    def _infer_result_method(self, res_type: VynType, method: str, args: List[Expr]) -> VynType:
        """Type des méthodes sur Result<T, E>."""
        ok  = res_type.ok_type()  if res_type.is_result() else T_UNKN
        err = res_type.err_type() if res_type.is_result() else T_UNKN
        methods = {
            "is_ok":      T_BOOL,
            "is_err":     T_BOOL,
            "unwrap":     ok,
            "unwrap_or":  ok,
            "unwrap_err": err,
            "map":        VynType.result(T_UNKN, err),
            "map_err":    VynType.result(ok, T_UNKN),
            "and_then":   VynType.result(T_UNKN, err),
            "or_else":    res_type,
            "ok":         VynType.option(ok),
            "err":        VynType.option(err),
            "expect":     ok,
        }
        for a in args:
            self._infer(a)
        return methods.get(method, T_UNKN)

    def _infer_array_method(self, arr_type: VynType, method: str, args: List[Expr]) -> VynType:
        """Type des méthodes builtin sur tableaux."""
        elem = arr_type.inner()
        for a in args:
            self._infer(a)
        methods = {
            "len":        T_I32,
            "push":       T_VOID,
            "pop":        VynType.option(elem),
            "get":        VynType.option(elem),
            "set":        T_VOID,
            "remove":     elem,
            "clear":      T_VOID,
            "sort":       T_VOID,
            "reverse":    T_VOID,
            "contains":   T_BOOL,
            "index_of":   VynType.option(T_I32),
            "insert":     T_VOID,
            "slice":      arr_type,
            "map":        VynType.array(T_UNKN),
            "filter":     arr_type,
            "find":       VynType.option(elem),
            "any":        T_BOOL,
            "all":        T_BOOL,
            "count":      T_I32,
            "sum":        elem,
            "first":      VynType.option(elem),
            "last":       VynType.option(elem),
            "is_empty":   T_BOOL,
            "join":       T_STR,
            "extend":     T_VOID,
        }
        return methods.get(method, T_UNKN)

    def _infer_str_method(self, method: str, args: List[Expr]) -> VynType:
        """Type des méthodes builtin sur str."""
        for a in args:
            self._infer(a)
        methods = {
            "len":         T_I32,
            "upper":       T_STR,
            "lower":       T_STR,
            "trim":        T_STR,
            "trim_start":  T_STR,
            "trim_end":    T_STR,
            "contains":    T_BOOL,
            "starts_with": T_BOOL,
            "ends_with":   T_BOOL,
            "replace":     T_STR,
            "split":       VynType.array(T_STR),
            "chars":       VynType.array(T_CHAR),
            "index":       T_CHAR,
            "concat":      T_STR,
            "repeat":      T_STR,
            "is_empty":    T_BOOL,
            "parse_int":   T_I32,
            "parse_f32":   T_F32,
            "to_int":      T_I32,
            "to_f32":      T_F32,
            "bytes":       VynType.array(T_I32),
        }
        return methods.get(method, T_STR)

    # ── closures ──────────────────────────────────────────────────────────────

    def _infer_closure(self, expr: ClosureExpr) -> VynType:
        """Infère le type d'une closure."""
        self._push()
        param_types: List[VynType] = []
        for p in expr.params:
            pt = from_node(p.type) if p.type else TypeVarGen.fresh("T")
            param_types.append(pt)
            type_node = p.type or TypeNode("void")
            self._define(Symbol(p.name, type_node, pt, p.is_mut, False, False, "variable"))

        ret_type: VynType
        if expr.body:
            for s in expr.body:
                self._check_stmt(s, expr.return_type or TypeNode("void"))
            ret_type = from_node(expr.return_type) if expr.return_type else T_UNKN
        elif expr.expr:
            ret_type = self._infer(expr.expr)
        else:
            ret_type = T_VOID

        self._pop()
        return VynType.closure(*param_types, ret=ret_type)

    # ── opérateurs binaires ───────────────────────────────────────────────────

    def _infer_binary(self, expr: BinaryOp) -> VynType:
        """Infère le type d'un opérateur binaire."""
        left  = self._infer(expr.left)
        right = self._infer(expr.right)
        op    = expr.op

        # Opérateurs de comparaison → bool
        if op in ("==", "!=", "<", ">", "<=", ">="):
            return T_BOOL

        # Opérateurs logiques → bool
        if op in ("&&", "||", "and", "or"):
            return T_BOOL

        # Opérateurs bitwise sur entiers
        if op in ("&", "|", "^", "<<", ">>"):
            if left.is_integer() and right.is_integer():
                return wider_numeric(left, right)
            return T_I32

        # Concaténation de strings
        if op == "+" and left.is_str() and right.is_str():
            return T_STR

        # Arithmétique numérique
        if left.is_numeric() and right.is_numeric():
            return wider_numeric(left, right)

        # Opérateur sur tableaux : tab[i]
        if op == "[]":
            if left.kind == TKind.ARRAY and left.params:
                return left.params[0]
            return T_UNKN

        return T_UNKN

    # ── struct init ───────────────────────────────────────────────────────────

    def _check_struct_init(self, expr: StructInit) -> None:
        """Vérifie l'initialisation d'un struct."""
        if expr.struct_name not in self.structs:
            # Peut-être un enum variant
            for edecl in self.enums.values():
                for v in edecl.variants:
                    if v.name == expr.struct_name:
                        return
            self.errors.append(f"struct inconnue: '{expr.struct_name}'")
            return
        struct_info = self.structs[expr.struct_name]
        # Vérifier les champs fournis
        for fname, fexpr in expr.fields.items():
            if fname not in struct_info.fields:
                self.errors.append(f"champ inconnu '{fname}' dans '{expr.struct_name}'")
            self._infer(fexpr)
        # Vérifier les champs manquants obligatoires (non mutables)
        for fname, field in struct_info.fields.items():
            if fname not in expr.fields and field.default is None:
                self.warnings.append(f"champ '{fname}' manquant dans l'init de '{expr.struct_name}'")

    # ══════════════════════════════════════════════════════════════════════════
    #  Utilitaires de types
    # ══════════════════════════════════════════════════════════════════════════

    def _resolve_type(self, typ: TypeNode) -> TypeNode:
        """Résout les alias de types."""
        while typ.name in self.type_aliases and not typ.args:
            typ = self.type_aliases[typ.name]
        return typ

    def _types_compat(self, expected: TypeNode, got: VynType) -> bool:
        """Vérifie la compatibilité entre un TypeNode attendu et un VynType obtenu."""
        exp_name = expected.name
        if exp_name in ("void", "?"):
            return True
        if exp_name in self.type_aliases:
            resolved = self._resolve_type(expected)
            exp_name = resolved.name
        if exp_name in self._generic_params:
            return True
        got_name = got.name
        # Compatibilité numérique
        if exp_name in NUM_TYPES and got_name in NUM_TYPES:
            return True
        if exp_name == got_name:
            return True
        if got == T_UNKN:
            return True
        # Option compat
        if exp_name == "Option" and got.is_option():
            return True
        if exp_name == "Result" and got.is_result():
            return True
        # Struct compat
        if exp_name in self.structs and got.kind == TKind.STRUCT and got.name == exp_name:
            return True
        return False

    def _type_node_of(self, vtype: VynType) -> TypeNode:
        """Convertit un VynType en TypeNode."""
        return to_node(vtype)

    def _iter_elem_type(self, iter_type: VynType, hint: Optional[TypeNode]) -> TypeNode:
        """Déduit le type de l'élément d'un itérable."""
        if hint:
            return hint
        if iter_type.kind == TKind.ARRAY and iter_type.params:
            return self._type_node_of(iter_type.params[0])
        if iter_type.kind == TKind.VEC and iter_type.params:
            return self._type_node_of(iter_type.params[0])
        if iter_type.is_str():
            return TypeNode("char")
        if iter_type.kind == TKind.STRUCT and iter_type.name == "Range":
            return TypeNode("i32")
        return TypeNode("void")


# ═══════════════════════════════════════════════════════════════════════════════
#  Alias rétro-compat
# ═══════════════════════════════════════════════════════════════════════════════

# Pour compatibilité avec le code existant qui importe directement
from vyn.typesystem import TypeVarGen
