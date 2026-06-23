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
        """Complétion générale (Ctrl+Espace ou frappe de 2+ caractères)."""
        prefix_lower = prefix.lower()
        results: List[SymbolInfo] = []
        ctx = self.analyze_document(source) if source else DocumentContext()

        # Mots-clés
        for kw in self.KEYWORDS:
            if kw.lower().startswith(prefix_lower):
                results.append(SymbolInfo(kw, "keyword", "", "", kw))

        # Modules importés
        for mod in ctx.imports:
            if mod in self._modules:
                for sym in self._modules[mod]:
                    full = f"{mod}.{sym.name}"
                    if full.lower().startswith(prefix_lower) or sym.name.lower().startswith(prefix_lower):
                        results.append(SymbolInfo(
                            sym.name, "function", mod, sym.signature, full
                        ))

        # Packages vendor (fonctions top-level)
        for pkg in ctx.vendor_packages:
            if pkg in self._vendor:
                for sym in self._vendor[pkg]:
                    if sym.name.lower().startswith(prefix_lower):
                        results.append(sym)

        # Imports std
        if prefix_lower.startswith("std") or "std." in prefix_lower:
            for mod in self._modules:
                imp = f"std.{mod}"
                if imp.lower().startswith(prefix_lower):
                    results.append(SymbolInfo(imp, "module", mod, f"import std.{mod}", f"import {imp};"))

        # Fonctions locales
        for fn in ctx.functions:
            if fn.lower().startswith(prefix_lower):
                results.append(SymbolInfo(fn, "function", "", f"fn {fn}(...)", fn))

        return results[:80]

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
