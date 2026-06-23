"""Syntax highlighting for VynStudio."""
from __future__ import annotations

import re

from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter


class VynHighlighter(QSyntaxHighlighter):
    """VS Code Light / Dark syntax highlighting for Vyn."""

    def __init__(self, document, light: bool = True):
        super().__init__(document)
        self._light = light
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []

        def _fmt(color: str, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        if light:
            comment, string_c = "#008000", "#A31515"
            keyword, type_c = "#0000FF", "#267F99"
            number, ident = "#098658", "#001080"
            struct_c, hot_c = "#267F99", "#E51400"
            base = "#000000"
        else:
            comment, string_c = "#6A9955", "#CE9178"
            keyword, type_c = "#C586C0", "#4FC1FF"
            number, ident = "#B5CEA8", "#9CDCFE"
            struct_c, hot_c = "#4EC9B0", "#FF6B35"
            base = "#D4D4D4"

        self._base_color = base
        self._rules.append((re.compile(r"//[^\n]*"), _fmt(comment)))
        self._rules.append((re.compile(r'"([^"\\]|\\.)*"'), _fmt(string_c)))
        self._rules.append((re.compile(r"@\[[\w]+\]"), _fmt("#4EC9B0", bold=True)))
        self._rules.append((re.compile(r"\bhot\b"), _fmt(hot_c, bold=True)))

        keywords = [
            "let", "mut", "const", "type", "struct", "enum", "void", "fn", "pub",
            "extern", "return", "impl", "trait", "self", "if", "else", "loop",
            "break", "continue", "match", "case", "async", "sync", "task",
            "import", "mod", "use", "try", "catch", "throw", "in",
            "true", "false", "and", "or", "not", "own", "ref",
        ]
        kw_fmt = _fmt(keyword, bold=True)
        for w in keywords:
            self._rules.append((re.compile(rf"\b{w}\b"), kw_fmt))

        for t in ["i32", "f32", "bool", "str"]:
            self._rules.append((re.compile(rf"\b{t}\b"), _fmt(type_c)))

        self._rules.append((re.compile(r"\b\d+\.\d+([eE][+-]?\d+)?\b"), _fmt(number)))
        self._rules.append((re.compile(r"\b\d+\b"), _fmt(number)))
        self._rules.append((re.compile(r"\b[A-Z][a-zA-Z0-9_]*\b"), _fmt(struct_c)))
        self._rules.append((re.compile(r"\b[a-z_][a-zA-Z0-9_]*\b"), _fmt(ident)))

    def highlightBlock(self, text: str) -> None:
        base = QTextCharFormat()
        base.setForeground(QColor(self._base_color))
        self.setFormat(0, len(text), base)
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
