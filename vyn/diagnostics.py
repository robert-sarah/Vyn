"""Smart real-time diagnostics for VynStudio (VS Code style)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from vyn.lexer import LexError, Lexer
from vyn.parser import ParseError, Parser
from vyn.semantic import SemanticError, SemanticAnalyzer

_INCOMPLETE_LINE_END = re.compile(
    r"(?:^|\s)(?:try|catch|match|case|if|else|loop|fn|let|mut|enum|struct|impl|"
    r"import|use|return|throw|break|continue|pub|hot|extern|and|or|in|default)$"
)
_TRAILING_OP = re.compile(r"(?:->|&&|\|\||[=+\-*/%,:(\[])\s*$")
_UNKNOWN_FN = re.compile(r"(?:unknown function|fonction inconnue|unknown identifier|identifiant inconnu):\s*(\w+)", re.I)


@dataclass
class Diagnostic:
    line: int
    col: int
    message: str
    severity: str = "error"  # error | warning | info
    length: int = 0


def _balance_braces(source: str) -> int:
    depth = 0
    in_str = False
    esc = False
    i = 0
    while i < len(source):
        c = source[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == "/" and i + 1 < len(source):
            if source[i + 1] == "/":
                while i < len(source) and source[i] != "\n":
                    i += 1
                continue
            if source[i + 1] == "*":
                i += 2
                while i + 1 < len(source) and not (source[i] == "*" and source[i + 1] == "/"):
                    i += 1
                i += 2
                continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return depth


def _is_incomplete(source: str) -> bool:
    text = source.rstrip()
    if not text:
        return True
    if _balance_braces(text) > 0:
        return True
    last = text.splitlines()[-1].strip()
    if not last:
        return True
    if _INCOMPLETE_LINE_END.search(last):
        return True
    if _TRAILING_OP.search(last):
        return True
    if last.endswith("{") or last.endswith("(") or last.endswith("["):
        return True
    return False


def _clean_message(msg: str) -> str:
    msg = msg.replace("[Parser] ", "").replace("[Semantic] ", "").replace("[Lexer] ", "")
    msg = re.sub(r"^(?:line|ligne) \d+, col \d+: ", "", msg)
    return msg.strip()


def _locate_name(source: str, name: str) -> tuple[int, int, int]:
    for i, line in enumerate(source.splitlines(), 1):
        for m in re.finditer(rf"\b{re.escape(name)}\b", line):
            return i, m.start() + 1, len(name)
    return 1, 1, len(name)


def _suppress_parse_error(source: str, err: ParseError) -> bool:
    if _is_incomplete(source):
        return True
    msg = str(err).lower()
    if "eof" in msg or "found ''" in msg:
        return True
    if err.line >= len(source.splitlines()):
        return True
    return False


def analyze_source(source: str) -> List[Diagnostic]:
    diags: List[Diagnostic] = []
    if not source.strip():
        return diags

    if _is_incomplete(source):
        return diags  # silent while typing (VS Code style)

    try:
        Lexer(source).tokenize()
        program = Parser(source).parse()
        sem = SemanticAnalyzer()
        sem.analyze(program)
        for fn in program.functions:
            if fn.is_hot:
                diags.append(Diagnostic(1, 1, f"hot fn '{fn.name}' — hot reload enabled", "info", 0))
            if any(a.name == "profile" for a in fn.attributes):
                diags.append(Diagnostic(1, 1, f"@[profile] on '{fn.name}'", "info", 0))
        if "server.listen(" in source and "listen_async" not in source:
            diags.append(Diagnostic(1, 1, "Use server.listen_async() to avoid blocking", "warning", 0))
        if "gui.run(" in source:
            diags.append(Diagnostic(1, 1, "gui.run() blocks until window closes", "info", 0))
    except LexError as e:
        diags.append(Diagnostic(e.line, e.col, _clean_message(str(e)), "error", 1))
    except ParseError as e:
        if not _suppress_parse_error(source, e):
            diags.append(Diagnostic(e.line, e.col, _clean_message(str(e)), "error", 1))
    except SemanticError as e:
        for line_msg in _clean_message(str(e)).splitlines():
            if not line_msg:
                continue
            m = _UNKNOWN_FN.search(line_msg)
            if m:
                ln, col, length = _locate_name(source, m.group(1))
                diags.append(Diagnostic(ln, col, line_msg, "error", length))
            else:
                diags.append(Diagnostic(1, 1, line_msg, "error", 0))
    except Exception as e:
        diags.append(Diagnostic(1, 1, str(e), "error", 0))
    return diags
