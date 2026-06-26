"""Détection du contexte de saisie pour autocomplétion intelligente."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CompletionContext:
    """Contexte détecté autour du curseur."""
    kind: str = "general"
    prefix: str = ""
    replace_len: int = 0
    module_path: str = ""
    hint: str = ""


def detect_context(before: str) -> CompletionContext:
    """Analyse la ligne avant le curseur et déduit ce que l'utilisateur est en train d'écrire."""
    # import std.io  /  import serde
    m = re.search(r"import\s+([\w.]*)$", before)
    if m:
        partial = m.group(1)
        if partial.startswith("std.") and "." not in partial[4:]:
            mod = partial[4:]
            return CompletionContext(
                "import_std", mod, len(partial), "",
                "Choisissez un module standard (std.*)",
            )
        return CompletionContext(
            "import", partial, len(partial), "",
            "Modules std.* et packages vendor",
        )

    # use std.io.println  /  use std.io.
    m = re.search(r"use\s+([\w.]*)$", before)
    if m:
        partial = m.group(1)
        if partial.endswith("."):
            mod = partial.rstrip(".")
            if mod.startswith("std."):
                mod = mod.split(".", 1)[1]
            return CompletionContext(
                "use_symbol", "", 0, mod,
                f"Symboles disponibles dans {partial}",
            )
        if "." in partial:
            mod_part, sym = partial.rsplit(".", 1)
            mod = mod_part.split(".")[-1] if "std." in mod_part else mod_part
            return CompletionContext(
                "use_symbol", sym, len(sym), mod,
                "Fonction ou symbole à importer",
            )
        return CompletionContext(
            "use", partial, len(partial), "",
            "Chemin de module (use std.io; ou use std.io.println;)",
        )

    # type de retour fn(...) -> TYPE
    m = re.search(r"->\s*([\w\[\]]*)$", before)
    if m:
        p = m.group(1)
        return CompletionContext("type", p, len(p), "", "Type de retour")

    # annotation de type : TYPE
    m = re.search(r":\s*([\w\[\]]*)$", before)
    if m and not re.search(r"::\s*$", before):
        p = m.group(1)
        return CompletionContext("type", p, len(p), "", "Type Vyn (i32, f32, str, struct…)")

    # let mut |
    if re.search(r"let\s+mut\s*$", before):
        return CompletionContext("let_mut", "", 0, "", "Nom de variable mutable")

    # let |
    if re.search(r"let\s+$", before):
        return CompletionContext("let", "", 0, "", "mut ou déclaration de variable")

    # const NAME :
    m = re.search(r"const\s+\w+\s*:\s*([\w\[\]]*)$", before)
    if m:
        p = m.group(1)
        return CompletionContext("type", p, len(p), "", "Type de la constante")

    # fn name
    m = re.search(r"fn\s+([\w]*)$", before)
    if m:
        p = m.group(1)
        return CompletionContext("fn_name", p, len(p), "", "Nom de fonction")

    # pub |
    if re.search(r"pub\s+$", before):
        return CompletionContext("pub", "", 0, "", "fn, struct, enum, const, trait…")

    # struct / enum
    m = re.search(r"struct\s+([\w]*)$", before)
    if m:
        return CompletionContext("struct_name", m.group(1), len(m.group(1)), "", "Nom du struct")

    m = re.search(r"enum\s+([\w]*)$", before)
    if m:
        return CompletionContext("enum_name", m.group(1), len(m.group(1)), "", "Nom de l'enum")

    # mot courant
    m = re.search(r"([\w]+)$", before)
    if m:
        p = m.group(1)
        return CompletionContext("general", p, len(p), "", "")

    return CompletionContext("general", "", 0, "", "")


def should_auto_trigger(before: str) -> bool:
    """Ouvre la complétion automatiquement après certains mots-clés + espace."""
    triggers = (
        r"import\s+$",
        r"use\s+$",
        r"let\s+$",
        r"let\s+mut\s+$",
        r"pub\s+$",
        r"->\s*$",
        r":\s*$",
        r"fn\s+$",
    )
    return any(re.search(p, before) for p in triggers)
