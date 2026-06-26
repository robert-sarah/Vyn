"""Vyn Local Language Server — base de symboles offline & complétion (style Pylance).

Charge automatiquement :
  - tous les modules stdlib/std/*.vyn
  - tous les packages vendor/*/lib.vyn
  - symboles runtime natifs (io, sys, gui, math…)
  - mots-clés du langage

100 % offline — aucune connexion réseau.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from vynstudio.completion_context import CompletionContext, detect_context, should_auto_trigger

ROOT = Path(__file__).resolve().parent.parent
STDLIB = ROOT / "stdlib" / "std"
VENDOR = ROOT / "vendor"

_PUB_FN = re.compile(
    r"pub\s+fn\s+(\w+)\s*\(([^)]*)\)\s*->\s*([\w\[\]]+)",
    re.MULTILINE,
)
_IMPORT = re.compile(r"import\s+([\w.]+)\s*;")
_USE = re.compile(r"use\s+([\w.]+)\s*;")
_FN_DECL = re.compile(r"fn\s+(\w+)\s*\(")
_STRUCT = re.compile(r"struct\s+(\w+)")
_ENUM = re.compile(r"enum\s+(\w+)")


@dataclass
class SymbolInfo:
    """Un symbole connu du langage (fonction, module, mot-clé…)."""
    name: str
    kind: str = "function"          # keyword | module | function | type | snippet
    module: str = ""                # ex. "io" pour io.println
    signature: str = ""             # ex. "println(msg: str) -> void"
    insert: str = ""                # texte inséré dans l'éditeur
    detail: str = ""                # courte description


@dataclass
class DocumentContext:
    """Contexte extrait d'un fichier .vyn ouvert."""
    imports: Set[str] = field(default_factory=set)       # modules importés (io, numpy…)
    vendor_packages: Set[str] = field(default_factory=set) # serde, collections…
    functions: List[str] = field(default_factory=list)
    structs: List[str] = field(default_factory=list)
    enums: List[str] = field(default_factory=list)
    locals_at_cursor: List[str] = field(default_factory=list)


# Symboles fournis par le runtime Python mais absents des stubs .vyn
KEYWORD_DOCS: Dict[str, str] = {
    "let": "Déclare une variable immuable.",
    "mut": "Modificateur — variable mutable (let mut x).",
    "const": "Constante compile-time.",
    "type": "Alias de type.",
    "struct": "Définit une structure de données.",
    "enum": "Énumération de variantes.",
    "void": "Type sans valeur de retour.",
    "i32": "Entier signé 32 bits.",
    "f32": "Flottant 32 bits.",
    "bool": "Booléen (true / false).",
    "str": "Chaîne de caractères.",
    "own": "Propriété exclusive (ownership).",
    "ref": "Référence empruntée.",
    "fn": "Déclare une fonction.",
    "pub": "Visibilité publique.",
    "extern": "Bloc FFI externe \"C\".",
    "return": "Retourne une valeur depuis une fonction.",
    "impl": "Implémentation de méthodes pour un struct.",
    "trait": "Interface / trait (réservé).",
    "self": "Référence à l'instance courante.",
    "hot": "Fonction hot-reloadable.",
    "if": "Branchement conditionnel.",
    "else": "Branche alternative.",
    "loop": "Boucle (loop { } ou loop x in arr).",
    "break": "Sort de la boucle courante.",
    "continue": "Passe à l'itération suivante.",
    "match": "Pattern matching sur une valeur.",
    "case": "Branche d'un match.",
    "default": "Branche par défaut d'un match.",
    "async": "Mot-clé asynchrone (réservé).",
    "sync": "Synchronisation / yield.",
    "task": "Tâche concurrente (réservé).",
    "import": "Importe un module (import std.io;).",
    "mod": "Déclare un module (réservé).",
    "use": "Import sélectif (use std.io.println;).",
    "try": "Bloc try/catch pour erreurs.",
    "catch": "Gestionnaire d'exception.",
    "throw": "Lève une erreur.",
    "in": "Itération (loop x in arr).",
    "true": "Littéral booléen vrai.",
    "false": "Littéral booléen faux.",
    "and": "ET logique.",
    "or": "OU logique.",
    "not": "Négation logique.",
}

_RUNTIME_EXTRAS: Dict[str, List[Tuple[str, str]]] = {
    "io": [
        ("print", "print(msg: str) -> void"),
        ("println", "println(msg: str) -> void"),
        ("print_int", "print_int(n: i32) -> void"),
        ("print_i32", "print_i32(n: i32) -> void"),
    ],
    "sys": [("sleep", "sleep(ms: i32) -> void")],
    "math": [
        ("abs", "abs(x: f32) -> f32"),
        ("sqrt", "sqrt(x: f32) -> f32"),
        ("clamp", "clamp(val: f32, min: f32, max: f32) -> f32"),
        ("lerp", "lerp(a: f32, b: f32, t: f32) -> f32"),
    ],
    "gui": [
        ("window", 'window(title: str, w: i32, h: i32) -> void'),
        ("label", 'label(text: str) -> void'),
        ("button", 'button(text: str) -> void'),
        ("alert", 'alert(msg: str) -> void'),
        ("run", "run() -> void"),
    ],
    "vec": [("set", "set(v: i32, idx: i32, val: f32) -> void")],
    "array": [("push", "push(arr: i32, val: f32) -> void")],
    "crypto": [("sha256", "sha256(data: str) -> str")],
    "hash": [("md5", "md5(data: str) -> str")],
    "html": [("escape", "escape(text: str) -> str")],
}

# Catalogue intelligent des modules — descriptions pour l'IDE
MODULE_CATALOG: Dict[str, str] = {
    "io": "Console — print, println, print_int",
    "sys": "Système — sleep(ms)",
    "fs": "Fichiers — read, write, exists, list_dir",
    "json": "JSON — parse, stringify",
    "http": "HTTP client — get, post",
    "server": "Serveur web — route, listen, listen_async",
    "html": "HTML — page, h1, body, div, escape",
    "css": "CSS — rule, class, stylesheet",
    "db": "SQLite — open, exec, query, close",
    "gui": "Interface Tkinter — window, button, label, run",
    "math": "Mathématiques — abs, sqrt, clamp, lerp",
    "str": "Chaînes — len, upper, lower, trim, contains",
    "time": "Temps — now_ms, now_sec, format",
    "net": "Réseau — ping, resolve, get, post",
    "log": "Journalisation — info, warn, error, debug",
    "vec": "Vecteur dynamique — new, push, len, get, set",
    "array": "Tableaux — len, push, sum_f32, fill",
    "rand": "Aléatoire — seed, next_f32, next_i32",
    "hash": "Hachage — fnv1a, md5",
    "crypto": "Cryptographie — sha256, xor_bytes",
    "mem": "Mémoire — size_of",
    "thread": "Threads — spawn, join, sleep_ms",
    "sync": "Sync — yield_task",
    "ai": "IA — model_new, train, predict, save",
    "numpy": "NumPy — array, mean, dot, zeros",
    "torch": "PyTorch — tensor, relu, train_linear",
    "tensorflow": "TensorFlow — train_xor, predict",
    "cv": "OpenCV — read_size, grayscale, resize",
    "pandas": "Pandas — read_csv, rows, mean",
    "sklearn": "Scikit-learn — fit_linear, predict, score",
    "plot": "Graphiques — line, hist",
}

VENDOR_CATALOG: Dict[str, str] = {
    "serde": "Sérialisation JSON — serialize, deserialize",
    "collections": "Collections — Vec, HashMap",
    "ai": "Package IA — create_classifier, train_classifier",
    "web": "Web helpers — route, handler",
    "async": "Async utilities",
    "neural": "Réseaux de neurones — relu, load, save",
    "db": "Base de données avancée",
}

TYPE_DOCS: Dict[str, str] = {
    "void": "Aucune valeur",
    "i32": "Entier signé 32 bits",
    "f32": "Nombre décimal 32 bits",
    "bool": "true / false",
    "str": "Chaîne UTF-8",
    "own": "Propriété exclusive (move semantics)",
    "ref": "Référence empruntée",
}

LET_SNIPPETS: List[tuple[str, str, str]] = [
    ("let i32", "let name: i32 = 0;", "Variable entière immuable"),
    ("let f32", "let name: f32 = 0.0;", "Variable flottante immuable"),
    ("let str", 'let name: str = "";', "Chaîne immuable"),
    ("let mut i32", "let mut name: i32 = 0;", "Entier mutable"),
    ("let mut f32", "let mut name: f32 = 0.0;", "Flottant mutable"),
    ("let array", "let name: [f32; 3] = [0.0, 0.0, 0.0];", "Tableau typé"),
]

FN_NAME_SUGGESTIONS = ["main", "init", "update", "process", "handler", "callback", "worker"]

PUB_KEYWORDS = ["fn", "struct", "enum", "const", "type", "trait", "mod"]


class VynLanguageServer:
    """Mini LSP offline : index de symboles + complétion contextuelle."""

    KEYWORDS = [
        "let", "mut", "const", "type", "struct", "enum", "void",
        "i32", "f32", "bool", "str", "own", "ref", "fn", "pub",
        "extern", "return", "impl", "trait", "self", "hot",
        "if", "else", "loop", "break", "continue", "match", "case", "default",
        "async", "sync", "task", "import", "mod", "use",
        "try", "catch", "throw", "in", "true", "false", "and", "or", "not",
    ]

    TYPES = ["void", "i32", "f32", "bool", "str", "own", "ref"]

    def __init__(self) -> None:
        # module_name -> liste de SymbolInfo (membres)
        self._modules: Dict[str, List[SymbolInfo]] = {}
        # package vendor -> fonctions top-level
        self._vendor: Dict[str, List[SymbolInfo]] = {}
        self._all_flat: List[str] = []
        self._symbol_lookup: Dict[str, SymbolInfo] = {}
        self._build_index()

    # ------------------------------------------------------------------ index
    def _build_index(self) -> None:
        """Construit la base de données depuis stdlib, vendor et runtime."""
        for path in sorted(STDLIB.glob("*.vyn")):
            mod = path.stem
            self._modules[mod] = self._parse_vyn_file(path, mod)

        for mod, extras in _RUNTIME_EXTRAS.items():
            existing = {s.name for s in self._modules.get(mod, [])}
            for name, sig in extras:
                if name not in existing:
                    self._modules.setdefault(mod, []).append(
                        SymbolInfo(name, "function", mod, sig, name)
                    )

        for pkg_dir in sorted(VENDOR.iterdir()) if VENDOR.exists() else []:
            lib = pkg_dir / "lib.vyn"
            if lib.is_file():
                self._vendor[pkg_dir.name] = self._parse_vyn_file(lib, pkg_dir.name, top_level=True)

        self._rebuild_flat_list()
        self._rebuild_lookup()

    def _parse_vyn_file(self, path: Path, mod: str, *, top_level: bool = False) -> List[SymbolInfo]:
        text = path.read_text(encoding="utf-8")
        symbols: List[SymbolInfo] = []
        for m in _PUB_FN.finditer(text):
            name, params, ret = m.group(1), m.group(2).strip(), m.group(3)
            sig = f"{name}({params}) -> {ret}" if params else f"{name}() -> {ret}"
            insert = name if top_level else name
            symbols.append(SymbolInfo(name, "function", mod, sig, insert))
        return symbols

    def _rebuild_flat_list(self) -> None:
        items: Set[str] = set(self.KEYWORDS)
        for mod, syms in self._modules.items():
            for s in syms:
                items.add(f"{mod}.{s.name}")
        for pkg, syms in self._vendor.items():
            for s in syms:
                items.add(s.name)
                items.add(f"{pkg}.{s.name}")
        for mod in self._modules:
            items.add(f"std.{mod}")
        for pkg in self._vendor:
            items.add(pkg)
        self._all_flat = sorted(items)

    def _rebuild_lookup(self) -> None:
        """Index nom → SymbolInfo pour infobulles et complétion rapide."""
        lookup: Dict[str, SymbolInfo] = {}
        for kw in self.KEYWORDS:
            lookup[kw] = SymbolInfo(
                kw, "keyword", "", "", kw, KEYWORD_DOCS.get(kw, f"Mot-clé Vyn : {kw}")
            )
        for mod, syms in self._modules.items():
            lookup[mod] = SymbolInfo(
                mod, "module", mod, f"module std.{mod}", f"std.{mod}",
                f"Module standard std.{mod}",
            )
            for s in syms:
                full = f"{mod}.{s.name}"
                lookup[s.name] = SymbolInfo(
                    s.name, s.kind, mod, s.signature, s.insert or s.name,
                    s.detail or s.signature or f"{mod}.{s.name}",
                )
                lookup[full] = SymbolInfo(
                    full, "function", mod, s.signature, full,
                    s.signature or f"Fonction {full}",
                )
        for pkg, syms in self._vendor.items():
            lookup[pkg] = SymbolInfo(
                pkg, "module", pkg, f"package {pkg}", pkg, f"Package vendor {pkg}",
            )
            for s in syms:
                lookup[s.name] = SymbolInfo(
                    s.name, s.kind, pkg, s.signature, s.insert or s.name,
                    s.detail or s.signature,
                )
                lookup[f"{pkg}.{s.name}"] = SymbolInfo(
                    f"{pkg}.{s.name}", "function", pkg, s.signature,
                    f"{pkg}.{s.name}", s.signature,
                )
        self._symbol_lookup = lookup

    # -------------------------------------------------------------- contexte doc
    def analyze_document(self, source: str, cursor_line: int = 0, cursor_col: int = 0) -> DocumentContext:
        """Extrait imports, structs, fonctions et variables locales du fichier."""
        ctx = DocumentContext()
        for m in _IMPORT.finditer(source):
            path = m.group(1)
            if path.startswith("std."):
                ctx.imports.add(path.split(".", 1)[1])
            else:
                ctx.vendor_packages.add(path)
                ctx.imports.add(path)
        for m in _USE.finditer(source):
            path = m.group(1)
            if path.startswith("std."):
                ctx.imports.add(path.split(".", 1)[1])
        ctx.functions = _FN_DECL.findall(source)
        ctx.structs = _STRUCT.findall(source)
        ctx.enums = _ENUM.findall(source)
        if cursor_line > 0:
            ctx.locals_at_cursor = self._locals_before_cursor(source, cursor_line, cursor_col)
        return ctx

    def _locals_before_cursor(self, source: str, line: int, col: int) -> List[str]:
        """Variables `let` déclarées avant le curseur (heuristique rapide)."""
        lines = source.splitlines()[:line]
        text = "\n".join(lines)
        if line <= len(source.splitlines()):
            text += "\n" + source.splitlines()[line - 1][: max(0, col - 1)]
        found: List[str] = []
        for m in re.finditer(r"let\s+(?:mut\s+)?(\w+)", text):
            found.append(m.group(1))
        return found

    # ----------------------------------------------------------- complétion "."
    def namespace_before_dot(self, line_text: str) -> Optional[str]:
        """Retourne le mot juste avant le dernier '.' sur la ligne."""
        before = line_text[: len(line_text.rstrip())]
        m = re.search(r"([\w]+)\.$", before)
        return m.group(1) if m else None

    def partial_after_dot(self, line_text: str) -> str:
        """Préfixe tapé après le dernier '.' (ex. io.pr -> 'pr')."""
        m = re.search(r"\.([\w]*)$", line_text)
        return m.group(1) if m else ""

    def complete_member(self, namespace: str, prefix: str = "", source: str = "") -> List[SymbolInfo]:
        """Complétion après 'namespace.' — cœur du trigger sur '.'."""
        prefix_lower = prefix.lower()
        results: List[SymbolInfo] = []

        if namespace == "std":
            for mod in sorted(self._modules):
                if not prefix_lower or mod.lower().startswith(prefix_lower):
                    results.append(SymbolInfo(
                        mod, "module", mod, f"std.{mod}",
                        f"std.{mod}", f"Module standard std.{mod}",
                    ))
            return results

        if namespace in self._modules:
            for sym in self._modules[namespace]:
                if not prefix_lower or sym.name.lower().startswith(prefix_lower):
                    results.append(sym)

        elif namespace in self._vendor:
            for sym in self._vendor[namespace]:
                if not prefix_lower or sym.name.lower().startswith(prefix_lower):
                    results.append(sym)

        # Chaîne std.io -> io
        elif namespace.startswith("std") and "." in namespace:
            sub = namespace.split(".", 1)[1]
            return self.complete_member(sub, prefix, source)

        # Symboles utilisateur : struct methods via impl
        if source:
            ctx = self.analyze_document(source)
            if namespace in ctx.structs:
                results.append(SymbolInfo("field", "field", namespace, "struct field", "field"))

        return sorted(results, key=lambda s: s.name)

    def complete_general(self, prefix: str, source: str = "") -> List[SymbolInfo]:
        """Complétion générale — filtre dynamique par préfixe (startswith)."""
        return self.complete_unified(prefix, source)

    def complete_unified(self, prefix: str, source: str = "",
                         cursor_line: int = 0, cursor_col: int = 0) -> List[SymbolInfo]:
        """Point d'entrée intelligent — détecte le contexte puis complète."""
        before = ""
        if source and cursor_line > 0:
            lines = source.splitlines()
            if cursor_line <= len(lines):
                before = lines[cursor_line - 1][: max(0, cursor_col - 1)]
        ctx = detect_context(before)
        if ctx.kind != "general" or should_auto_trigger(before):
            return self.complete_contextual(ctx, source, cursor_line, cursor_col)
        if not prefix:
            return []
        return self._complete_general_fallback(prefix, source, cursor_line, cursor_col)

    def complete_contextual(
        self,
        ctx: CompletionContext,
        source: str = "",
        cursor_line: int = 0,
        cursor_col: int = 0,
    ) -> List[SymbolInfo]:
        """Complétion contextuelle selon import / let / type / use / fn…"""
        doc = self.analyze_document(source, cursor_line, cursor_col) if source else DocumentContext()
        pfx = ctx.prefix.lower()
        results: List[SymbolInfo] = []
        seen: Set[str] = set()

        def add(sym: SymbolInfo) -> None:
            key = sym.insert or sym.name
            if key not in seen:
                seen.add(key)
                results.append(sym)

        def match(name: str) -> bool:
            return not pfx or name.lower().startswith(pfx)

        kind = ctx.kind

        if kind in ("import", "import_std"):
            for mod, desc in sorted(MODULE_CATALOG.items()):
                path = f"std.{mod}"
                if match(mod) or match(path):
                    add(SymbolInfo(path, "import", mod, path, f"{mod};", desc))
            for pkg, desc in sorted(VENDOR_CATALOG.items()):
                if match(pkg):
                    add(SymbolInfo(pkg, "import", pkg, pkg, f"{pkg};", desc))

        elif kind == "use":
            for mod in sorted(self._modules):
                path = f"std.{mod}"
                if match(mod) or match(path):
                    add(SymbolInfo(
                        path, "use", mod, path, f"{path};",
                        MODULE_CATALOG.get(mod, path),
                    ))
            for pkg in sorted(self._vendor):
                if match(pkg):
                    add(SymbolInfo(
                        pkg, "use", pkg, pkg, f"{pkg};",
                        VENDOR_CATALOG.get(pkg, pkg),
                    ))

        elif kind == "use_symbol":
            mod = ctx.module_path
            if mod in self._modules:
                for sym in self._modules[mod]:
                    if match(sym.name):
                        add(SymbolInfo(
                            sym.name, "function", mod, sym.signature,
                            f"{sym.name};", sym.signature or f"{mod}.{sym.name}",
                        ))

        elif kind == "type":
            for t, desc in TYPE_DOCS.items():
                if match(t):
                    add(SymbolInfo(t, "type", "", t, t, desc))
            for s in doc.structs:
                if match(s):
                    add(SymbolInfo(s, "struct", "", s, s, f"Struct {s}"))
            for e in doc.enums:
                if match(e):
                    add(SymbolInfo(e, "enum", "", e, e, f"Enum {e}"))
            if match("[") or match("f32") or match("i32"):
                add(SymbolInfo("[f32; 3]", "type", "", "[f32; 3]", "[f32; 3]", "Tableau f32 taille 3"))
                add(SymbolInfo("[i32; 3]", "type", "", "[i32; 3]", "[i32; 3]", "Tableau i32 taille 3"))

        elif kind == "let":
            add(SymbolInfo("mut", "keyword", "", "mut", "mut ", "Variable mutable"))
            for label, insert, desc in LET_SNIPPETS[:3]:
                add(SymbolInfo(label, "snippet", "", insert, insert, desc))

        elif kind == "let_mut":
            for label, insert, desc in LET_SNIPPETS[3:]:
                add(SymbolInfo(label, "snippet", "", insert, insert, desc))

        elif kind == "fn_name":
            for name in FN_NAME_SUGGESTIONS:
                if match(name):
                    add(SymbolInfo(
                        name, "function", "", f"fn {name}()", name,
                        "Point d'entrée du programme" if name == "main" else f"Fonction {name}",
                    ))

        elif kind == "pub":
            for kw in PUB_KEYWORDS:
                if match(kw):
                    add(SymbolInfo(kw, "keyword", "", kw, f"{kw} ",
                                    KEYWORD_DOCS.get(kw, f"pub {kw}")))

        elif kind == "struct_name":
            add(SymbolInfo("MyStruct", "snippet", "", "MyStruct", "MyStruct", "Nom de struct"))

        elif kind == "enum_name":
            add(SymbolInfo("MyEnum", "snippet", "", "MyEnum", "MyEnum", "Nom d'enum"))

        else:
            return self._complete_general_fallback(ctx.prefix, source, cursor_line, cursor_col)

        if not results and pfx:
            return self._complete_general_fallback(pfx, source, cursor_line, cursor_col)
        return results[:80]

    def _complete_general_fallback(self, prefix: str, source: str,
                                   cursor_line: int, cursor_col: int) -> List[SymbolInfo]:
        prefix_lower = prefix.lower()
        if not prefix_lower:
            return []
        results: List[SymbolInfo] = []
        seen: Set[str] = set()
        doc = self.analyze_document(source, cursor_line, cursor_col) if source else DocumentContext()

        def add(sym: SymbolInfo) -> None:
            key = sym.insert or sym.name
            if key not in seen:
                seen.add(key)
                results.append(sym)

        for kw in self.KEYWORDS:
            if kw.lower().startswith(prefix_lower):
                add(SymbolInfo(kw, "keyword", "", "", kw, KEYWORD_DOCS.get(kw, "")))

        for mod in doc.imports:
            if mod in self._modules:
                for sym in self._modules[mod]:
                    if sym.name.lower().startswith(prefix_lower):
                        add(SymbolInfo(
                            f"{mod}.{sym.name}", "function", mod, sym.signature,
                            f"{mod}.{sym.name}", sym.signature,
                        ))

        for loc in doc.locals_at_cursor:
            if loc.lower().startswith(prefix_lower):
                add(SymbolInfo(loc, "variable", "", loc, loc, "Variable locale"))

        for fn in doc.functions:
            if fn.lower().startswith(prefix_lower):
                add(SymbolInfo(fn, "function", "", fn, fn, "Fonction locale"))

        if prefix_lower.startswith("i") or prefix_lower.startswith("s") or len(prefix_lower) >= 1:
            for mod, desc in MODULE_CATALOG.items():
                path = f"std.{mod}"
                if mod.startswith(prefix_lower) or path.startswith(prefix_lower):
                    add(SymbolInfo(mod, "module", mod, path, f"{mod}.", desc))
                    add(SymbolInfo(path, "import", mod, path, f"import {path};", desc))
                    if mod in self._modules:
                        for sym in self._modules[mod]:
                            full = f"{mod}.{sym.name}"
                            if sym.name.lower().startswith(prefix_lower) or mod == prefix_lower:
                                add(SymbolInfo(
                                    full, "function", mod, sym.signature,
                                    full, sym.signature,
                                ))

        try:
            from vynstudio.completions import SNIPPETS
            for sk in SNIPPETS:
                if sk.lower().startswith(prefix_lower):
                    add(SymbolInfo(sk, "snippet", "", sk, sk, f"Snippet : {sk}"))
        except ImportError:
            pass

        return sorted(results, key=lambda s: s.name.lower())[:80]

    def lookup_hover(self, word: str, source: str = "") -> Optional[SymbolInfo]:
        """Résout un identifiant pour l'infobulle au survol."""
        if not word:
            return None
        if word in self._symbol_lookup:
            return self._symbol_lookup[word]
        if source:
            ctx = self.analyze_document(source)
            if word in ctx.functions:
                return SymbolInfo(word, "function", "", f"fn {word}(...)", word, f"Fonction locale")
            if word in ctx.structs:
                return SymbolInfo(word, "struct", "", word, word, f"Struct {word}")
            if word in ctx.enums:
                return SymbolInfo(word, "enum", "", word, word, f"Enum {word}")
            if word in ctx.locals_at_cursor:
                return SymbolInfo(word, "variable", "", word, word, "Variable locale")
        parts = word.split(".")
        if len(parts) == 2:
            mod, name = parts
            if mod in self._modules:
                for sym in self._modules[mod]:
                    if sym.name == name:
                        return SymbolInfo(
                            word, "function", mod, sym.signature, word, sym.signature,
                        )
        return None

    def all_completion_strings(self) -> List[str]:
        """Liste plate pour QCompleter de secours."""
        return self._all_flat

    def module_names(self) -> List[str]:
        return sorted(self._modules.keys())

    def member_names(self, namespace: str) -> List[str]:
        return [s.name for s in self.complete_member(namespace)]

    @staticmethod
    def call_snippet(name: str, signature: str) -> tuple[str, int]:
        """Texte à insérer + offset curseur (à l'intérieur des parenthèses si args)."""
        safe_name = name or "fn"
        if not signature:
            return f"{safe_name}()", len(safe_name) + 1
        m = re.match(rf"{re.escape(safe_name)}\s*\(([^)]*)\)", signature.strip())
        has_params = bool(m and m.group(1).strip()) if m else "(" in signature
        text = f"{safe_name}()"
        if has_params or "()" in signature or signature.startswith(f"{safe_name}("):
            return text, len(safe_name) + 1
        return safe_name, len(safe_name)


# Instance globale partagée (chargée une seule fois au démarrage)
SERVER = VynLanguageServer()
