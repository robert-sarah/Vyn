"""Résolution de modules Vyn — support multi-fichiers, imports, détection de cycles."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from vyn.ast.nodes import (
    Program, ImportDecl, UseDecl, FunctionDecl, StructDecl,
    EnumDecl, ConstDecl, TypeAliasDecl, TraitDecl, ModDecl,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Chemins de recherche
# ═══════════════════════════════════════════════════════════════════════════════

_ROOT    = Path(__file__).resolve().parent.parent
_STDLIB  = _ROOT / "stdlib"
_VENDOR  = _ROOT / "vendor"

# Modules standard reconnus
_STD_MODULES: Set[str] = {
    "std.io", "std.sys", "std.mem", "std.math", "std.str",
    "std.net", "std.sync", "std.fs", "std.json", "std.time",
    "std.gui", "std.log", "std.vec", "std.rand", "std.hash",
    "std.array", "std.thread", "std.crypto", "std.html", "std.css",
    "std.server", "std.http", "std.ai", "std.db",
    "std.numpy", "std.torch", "std.tensorflow", "std.cv",
    "std.pandas", "std.sklearn", "std.plot",
    "std.option", "std.result", "std.hashmap", "std.iter",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Résultat de résolution
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResolvedModule:
    """Un module résolu avec son chemin, son source et son AST (si parsé)."""
    path:        str                      # chemin logique (ex: "std.io")
    file_path:   Optional[Path]           # chemin physique sur disque
    source:      str                      # code source
    program:     Optional[Program]        = None  # AST parsé
    checksum:    str                      = ""    # SHA-256 du source
    is_builtin:  bool                     = False  # module stdlib builtin
    is_vendor:   bool                     = False  # package VPM
    exports:     Dict[str, str]           = field(default_factory=dict)
    # exports : { "nom_symbole" → "kind" }  ("fn", "struct", "enum", "const", …)

    def __post_init__(self) -> None:
        if self.source and not self.checksum:
            self.checksum = hashlib.sha256(self.source.encode()).hexdigest()[:16]


@dataclass
class ResolveError(Exception):
    message: str
    module:  str = ""

    def __str__(self) -> str:
        loc = f" [{self.module}]" if self.module else ""
        return f"[ModuleResolver]{loc} {self.message}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Résolveur
# ═══════════════════════════════════════════════════════════════════════════════

class ModuleResolver:
    """Résout les imports Vyn en fichiers sources.

    Stratégie de recherche (dans l'ordre) :
      1. Cache mémoire (_cache)
      2. Builtins Python (modules std gérés par stdlib_runtime.py)
      3. stdlib/ sur disque  (stdlib/std/io.vyn, …)
      4. vendor/<pkg>/lib.vyn
      5. Chemin relatif depuis le fichier appelant
      6. Répertoire racine du projet
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        extra_paths:  Optional[List[Path]] = None,
    ) -> None:
        self._root:        Path                     = project_root or _ROOT
        self._extra_paths: List[Path]               = extra_paths or []
        self._cache:       Dict[str, ResolvedModule] = {}
        self._resolving:   Set[str]                  = set()   # détection de cycles
        self.errors:       List[ResolveError]        = []

    # ── API publique ──────────────────────────────────────────────────────────

    def resolve(
        self,
        path: str,
        from_file: Optional[Path] = None,
    ) -> Optional[ResolvedModule]:
        """Résout un chemin de module et retourne le ResolvedModule, ou None."""
        canonical = self._canonicalize(path)

        if canonical in self._cache:
            return self._cache[canonical]

        if canonical in self._resolving:
            self.errors.append(ResolveError(
                f"import circulaire détecté: {canonical}", canonical
            ))
            return None

        self._resolving.add(canonical)
        try:
            mod = self._do_resolve(canonical, from_file)
            if mod:
                self._cache[canonical] = mod
            return mod
        finally:
            self._resolving.discard(canonical)

    def resolve_all(
        self,
        imports: List[ImportDecl],
        from_file: Optional[Path] = None,
    ) -> Dict[str, ResolvedModule]:
        """Résout une liste d'imports et retourne le dictionnaire path → module."""
        result: Dict[str, ResolvedModule] = {}
        for imp in imports:
            mod = self.resolve(imp.path, from_file)
            if mod:
                result[imp.path] = mod
            else:
                if not self._is_std_builtin(imp.path):
                    self.errors.append(ResolveError(
                        f"module introuvable: '{imp.path}' (vpm add {imp.path}?)",
                        imp.path,
                    ))
        return result

    def resolve_program(
        self,
        program: Program,
        from_file: Optional[Path] = None,
    ) -> Dict[str, ResolvedModule]:
        """Résout tous les imports d'un Program AST."""
        all_imports = list(program.imports)
        for u in program.uses:
            # Convertir un UseDecl en ImportDecl logique
            all_imports.append(ImportDecl(u.path))
        return self.resolve_all(all_imports, from_file)

    def get_source(self, path: str) -> Optional[str]:
        """Retourne le source d'un module déjà résolu."""
        mod = self._cache.get(self._canonicalize(path))
        return mod.source if mod else None

    def get_exports(self, path: str) -> Dict[str, str]:
        """Retourne les symboles exportés d'un module."""
        mod = self._cache.get(self._canonicalize(path))
        return mod.exports if mod else {}

    def known_modules(self) -> List[str]:
        """Retourne la liste de tous les modules connus (cache + stdlib)."""
        known = list(_STD_MODULES)
        for vendor_dir in _VENDOR.iterdir() if _VENDOR.exists() else []:
            if (vendor_dir / "lib.vyn").exists():
                known.append(vendor_dir.name)
        known.extend(self._cache.keys())
        return sorted(set(known))

    def clear_cache(self) -> None:
        self._cache.clear()

    # ── Résolution interne ────────────────────────────────────────────────────

    def _do_resolve(
        self,
        path: str,
        from_file: Optional[Path],
    ) -> Optional[ResolvedModule]:

        # 1. Module stdlib builtin (géré en Python, pas de fichier .vyn requis)
        if self._is_std_builtin(path):
            return ResolvedModule(
                path=path,
                file_path=None,
                source="",
                is_builtin=True,
                exports=self._builtin_exports(path),
            )

        # 2. Fichier stdlib sur disque
        std_file = self._find_stdlib_file(path)
        if std_file:
            src = std_file.read_text(encoding="utf-8")
            mod = ResolvedModule(path=path, file_path=std_file, source=src, is_builtin=True)
            mod.exports = self._scan_exports(src)
            return mod

        # 3. Vendor package
        vendor_file = self._find_vendor_file(path)
        if vendor_file:
            src = vendor_file.read_text(encoding="utf-8")
            mod = ResolvedModule(path=path, file_path=vendor_file, source=src, is_vendor=True)
            mod.exports = self._scan_exports(src)
            return mod

        # 4. Chemin relatif depuis le fichier appelant
        if from_file:
            rel = self._find_relative_file(path, from_file.parent)
            if rel:
                src = rel.read_text(encoding="utf-8")
                mod = ResolvedModule(path=path, file_path=rel, source=src)
                mod.exports = self._scan_exports(src)
                # résolution récursive des imports du module trouvé
                self._resolve_transitive(mod, rel)
                return mod

        # 5. Chemins supplémentaires
        for extra in self._extra_paths:
            f = self._find_relative_file(path, extra)
            if f:
                src = f.read_text(encoding="utf-8")
                mod = ResolvedModule(path=path, file_path=f, source=src)
                mod.exports = self._scan_exports(src)
                self._resolve_transitive(mod, f)
                return mod

        # 6. Racine du projet
        root_file = self._find_relative_file(path, self._root)
        if root_file:
            src = root_file.read_text(encoding="utf-8")
            mod = ResolvedModule(path=path, file_path=root_file, source=src)
            mod.exports = self._scan_exports(src)
            self._resolve_transitive(mod, root_file)
            return mod

        return None

    def _resolve_transitive(self, mod: ResolvedModule, file_path: Path) -> None:
        """Parse le module et résout ses imports transitivement."""
        try:
            from vyn.parser.parser import Parser
            from vyn.prelude import inject_prelude
            src_with_prelude = inject_prelude(mod.source)
            program = Parser(src_with_prelude).parse()
            mod.program = program
            for imp in program.imports:
                sub_canonical = self._canonicalize(imp.path)
                if sub_canonical not in self._cache and sub_canonical not in self._resolving:
                    self.resolve(imp.path, file_path)
        except Exception:
            pass   # erreurs de parse ignorées ici (le semantic les remontera)

    # ── Recherche de fichiers ─────────────────────────────────────────────────

    def _find_stdlib_file(self, path: str) -> Optional[Path]:
        """Cherche dans stdlib/."""
        # std.io → stdlib/std/io.vyn
        # std.numpy → stdlib/std/numpy.vyn
        parts = path.split(".")
        candidates: List[Path] = []

        if parts[0] == "std" and len(parts) >= 2:
            # stdlib/std/module.vyn
            candidates.append(_STDLIB / "std" / f"{'.'.join(parts[1:])}.vyn")
            # stdlib/std/module/index.vyn
            candidates.append(_STDLIB / "std" / "/".join(parts[1:]) / "index.vyn")

        # stdlib/<module>.vyn
        candidates.append(_STDLIB / f"{path.replace('.', '/')}.vyn")
        candidates.append(_STDLIB / path.replace(".", "/") / "index.vyn")

        for c in candidates:
            if c.exists():
                return c
        return None

    def _find_vendor_file(self, path: str) -> Optional[Path]:
        """Cherche dans vendor/<pkg>/lib.vyn."""
        if not _VENDOR.exists():
            return None

        # vendor/path/lib.vyn
        pkg_name = path.split(".")[0]
        candidates = [
            _VENDOR / path.replace(".", "/") / "lib.vyn",
            _VENDOR / pkg_name / "lib.vyn",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _find_relative_file(self, path: str, base: Path) -> Optional[Path]:
        """Cherche un fichier .vyn relativement à base."""
        rel = path.replace(".", "/")
        candidates = [
            base / f"{rel}.vyn",
            base / rel / "index.vyn",
            base / rel / "lib.vyn",
            base / f"{path}.vyn",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    # ── Utilitaires ───────────────────────────────────────────────────────────

    @staticmethod
    def _canonicalize(path: str) -> str:
        """Normalise un chemin de module."""
        return path.strip().rstrip(";").lower().replace("/", ".").replace("\\", ".")

    def _is_std_builtin(self, path: str) -> bool:
        """Retourne True si le module est géré directement en Python (pas de .vyn)."""
        canon = self._canonicalize(path)
        # Modules dont le runtime Python dispatch() gère tout
        _PYTHON_BUILTINS = {
            "std.io", "std.sys", "std.math", "std.str", "std.fs",
            "std.json", "std.db", "std.ai", "std.gui", "std.log",
            "std.net", "std.http", "std.server", "std.html", "std.css",
            "std.time", "std.vec", "std.rand", "std.hash", "std.thread",
            "std.numpy", "std.torch", "std.tensorflow", "std.cv",
            "std.pandas", "std.sklearn", "std.plot",
            "std.crypto", "std.sync", "std.mem",
        }
        return canon in _PYTHON_BUILTINS

    @staticmethod
    def _builtin_exports(path: str) -> Dict[str, str]:
        """Retourne les exports connus d'un module builtin."""
        _KNOWN: Dict[str, List[str]] = {
            "std.io":     ["print", "println", "print_int", "print_i32", "readln", "read_int"],
            "std.sys":    ["sleep", "exit", "env", "args"],
            "std.math":   ["abs", "sqrt", "clamp", "lerp", "pow", "floor", "ceil",
                           "sin", "cos", "min", "max", "PI", "E"],
            "std.str":    ["len", "upper", "lower", "trim", "contains", "replace",
                           "split", "starts_with", "ends_with", "parse_int",
                           "parse_f32", "from_int", "chars", "index", "concat", "format"],
            "std.fs":     ["exists", "read", "write", "remove", "list_dir", "mkdir"],
            "std.json":   ["parse", "stringify", "parse_int"],
            "std.db":     ["open", "exec", "query", "close"],
            "std.ai":     ["model_new", "train", "predict", "loss", "save", "load"],
            "std.gui":    ["window", "label", "button", "run", "alert"],
            "std.log":    ["info", "error", "warn", "debug"],
            "std.net":    ["get", "post", "ping", "resolve"],
            "std.http":   ["get", "post", "ok", "not_found"],
            "std.server": ["route", "listen", "listen_async", "stop", "serve_static"],
            "std.html":   ["page", "h1", "h2", "p", "div", "a", "escape", "body",
                           "head", "style", "script", "link"],
            "std.css":    ["rule", "class", "stylesheet"],
            "std.time":   ["now_ms", "now_sec", "format"],
            "std.vec":    ["new", "push", "len", "get", "set", "remove", "clear", "sort"],
            "std.rand":   ["seed", "next_f32", "next_i32", "range"],
            "std.hash":   ["fnv1a", "sha256", "md5"],
            "std.thread": ["spawn", "join", "sleep_ms", "current"],
            "std.numpy":  ["array", "zeros", "ones", "mean", "dot", "shape", "reshape", "version"],
            "std.torch":  ["tensor", "relu", "train_linear", "save", "load", "version"],
            "std.tensorflow": ["train_xor", "predict", "version"],
            "std.cv":     ["read_size", "grayscale", "resize", "blur", "version"],
            "std.pandas": ["read_csv", "rows", "mean", "head_json", "version"],
            "std.sklearn":["fit_linear", "predict", "score", "version"],
            "std.plot":   ["line", "hist", "version"],
            "std.hashmap":["new", "insert", "get", "get_or", "remove", "contains",
                           "len", "keys", "values", "clear"],
            "std.option": ["Some", "None", "is_some", "is_none", "unwrap", "unwrap_or", "map"],
            "std.result": ["Ok", "Err", "is_ok", "is_err", "unwrap", "unwrap_or", "map"],
            "std.iter":   ["map", "filter", "fold", "collect", "enumerate", "zip",
                           "take", "skip", "chain", "flat_map", "any", "all", "count"],
        }
        canon = ModuleResolver._canonicalize(path)
        fns = _KNOWN.get(canon, [])
        return {fn: "fn" for fn in fns}

    @staticmethod
    def _scan_exports(source: str) -> Dict[str, str]:
        """Scanne un source Vyn et retourne les symboles `pub` exportés."""
        import re
        exports: Dict[str, str] = {}
        patterns = [
            (r"\bpub\s+fn\s+(\w+)", "fn"),
            (r"\bpub\s+struct\s+(\w+)", "struct"),
            (r"\bpub\s+enum\s+(\w+)", "enum"),
            (r"\bpub\s+const\s+(\w+)", "const"),
            (r"\bpub\s+type\s+(\w+)", "type"),
            (r"\bpub\s+trait\s+(\w+)", "trait"),
            (r"\bpub\s+mod\s+(\w+)", "mod"),
        ]
        for pat, kind in patterns:
            for m in re.finditer(pat, source):
                exports[m.group(1)] = kind
        return exports


# ═══════════════════════════════════════════════════════════════════════════════
#  Graphe de dépendances
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DependencyNode:
    path:   str
    deps:   List[str]    = field(default_factory=list)
    rdeps:  List[str]    = field(default_factory=list)   # reverse deps


class DependencyGraph:
    """Graphe orienté des dépendances entre modules."""

    def __init__(self) -> None:
        self._nodes: Dict[str, DependencyNode] = {}

    def add_dep(self, from_: str, to: str) -> None:
        if from_ not in self._nodes:
            self._nodes[from_] = DependencyNode(from_)
        if to not in self._nodes:
            self._nodes[to] = DependencyNode(to)
        if to not in self._nodes[from_].deps:
            self._nodes[from_].deps.append(to)
        if from_ not in self._nodes[to].rdeps:
            self._nodes[to].rdeps.append(from_)

    def has_cycle(self) -> bool:
        """Détecte les cycles par DFS."""
        visited:  Set[str] = set()
        in_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            n = self._nodes.get(node)
            if n:
                for dep in n.deps:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in in_stack:
                        return True
            in_stack.discard(node)
            return False

        for name in list(self._nodes.keys()):
            if name not in visited:
                if dfs(name):
                    return True
        return False

    def topological_order(self) -> List[str]:
        """Retourne les modules dans l'ordre topologique (dépendances d'abord)."""
        visited: Set[str] = set()
        order:   List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            n = self._nodes.get(node)
            if n:
                for dep in n.deps:
                    if dep not in visited:
                        dfs(dep)
            order.append(node)

        for name in self._nodes:
            if name not in visited:
                dfs(name)
        return order

    def direct_deps(self, module: str) -> List[str]:
        n = self._nodes.get(module)
        return n.deps if n else []

    def all_deps(self, module: str) -> Set[str]:
        """Retourne toutes les dépendances transitives d'un module."""
        result: Set[str] = set()
        queue = list(self.direct_deps(module))
        while queue:
            dep = queue.pop()
            if dep not in result:
                result.add(dep)
                queue.extend(self.direct_deps(dep))
        return result

    def all_modules(self) -> List[str]:
        return list(self._nodes.keys())


def build_dep_graph(
    resolver: ModuleResolver,
    program: Program,
    from_file: Optional[Path] = None,
) -> DependencyGraph:
    """Construit le graphe de dépendances à partir d'un programme."""
    graph  = DependencyGraph()
    root   = from_file.stem if from_file else "main"
    queue  = [(root, program.imports)]
    seen:  Set[str] = {root}

    while queue:
        mod_name, imports = queue.pop()
        for imp in imports:
            graph.add_dep(mod_name, imp.path)
            if imp.path not in seen:
                seen.add(imp.path)
                resolved = resolver.resolve(imp.path, from_file)
                if resolved and resolved.program:
                    queue.append((imp.path, resolved.program.imports))

    return graph


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton global (utilisé par le compilateur et l'IDE)
# ═══════════════════════════════════════════════════════════════════════════════

_GLOBAL_RESOLVER: Optional[ModuleResolver] = None


def get_resolver(project_root: Optional[Path] = None) -> ModuleResolver:
    """Retourne le résolveur global, en le créant si nécessaire."""
    global _GLOBAL_RESOLVER
    if _GLOBAL_RESOLVER is None or project_root:
        _GLOBAL_RESOLVER = ModuleResolver(project_root)
    return _GLOBAL_RESOLVER


def reset_resolver() -> None:
    """Réinitialise le résolveur global (utile pour les tests)."""
    global _GLOBAL_RESOLVER
    _GLOBAL_RESOLVER = None
