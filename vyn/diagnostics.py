"""Diagnostics Vyn — erreurs en temps réel pour l'IDE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from vyn.lexer import LexError, Lexer
from vyn.parser import ParseError, Parser
from vyn.semantic import SemanticError, SemanticAnalyzer
from vyn.prelude import inject_prelude


@dataclass
class Diagnostic:
    line: int
    col: int
    message: str
    severity: str = "error"  # error | warning | info


def analyze_source(source: str) -> List[Diagnostic]:
    diags: List[Diagnostic] = []
    try:
        src = inject_prelude(source)
        Lexer(src).tokenize()
        program = Parser(src).parse()
        sem = SemanticAnalyzer()
        sem.analyze(program)
        for fn in program.functions:
            if fn.is_hot:
                diags.append(Diagnostic(1, 1,
                    f"hot fn '{fn.name}' — rechargement à chaud actif", "info"))
            if any(a.name == "profile" for a in fn.attributes):
                diags.append(Diagnostic(1, 1,
                    f"@[profile] sur '{fn.name}' — télémétrie active", "info"))
    except LexError as e:
        diags.append(Diagnostic(e.line, e.col, str(e), "error"))
    except ParseError as e:
        diags.append(Diagnostic(e.line, e.col, str(e), "error"))
    except SemanticError as e:
        for i, line in enumerate(str(e).splitlines()):
            diags.append(Diagnostic(i + 1, 1, line, "error"))
    except Exception as e:
        diags.append(Diagnostic(1, 1, str(e), "error"))
    return diags
