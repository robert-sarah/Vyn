"""Coloration syntaxique Vyn — partagee IDE."""
from __future__ import annotations

import re

from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter


class VynHighlighter(QSyntaxHighlighter):
  """Coloration VS Code Dark+ pour Vyn."""

  def __init__(self, document):
    super().__init__(document)
    self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []
    self._comment_state = 0

    def _fmt(color: str, bold=False, italic=False):
      f = QTextCharFormat()
      f.setForeground(QColor(color))
      if bold:
        f.setFontWeight(QFont.Bold)
      if italic:
        f.setFontItalic(True)
      return f

    # Ordre: commentaires et chaines d'abord, puis mots-cles
    self._rules.append((re.compile(r"//[^\n]*"), _fmt("#6A9955")))
    self._rules.append((re.compile(r'"([^"\\]|\\.)*"'), _fmt("#CE9178")))
    self._rules.append((re.compile(r"@\[[\w]+\]"), _fmt("#4EC9B0", bold=True)))
    self._rules.append((re.compile(r"\bhot\b"), _fmt("#FF6B35", bold=True)))

    keywords = [
      "let", "mut", "const", "type", "struct", "enum", "void", "fn", "pub",
      "extern", "return", "impl", "trait", "self", "if", "else", "loop",
      "break", "continue", "match", "case", "async", "sync", "task",
      "import", "mod", "use", "try", "catch", "throw", "in",
      "true", "false", "and", "or", "not", "own", "ref",
    ]
    kw_fmt = _fmt("#C586C0", bold=True)
    for w in keywords:
      self._rules.append((re.compile(rf"\b{w}\b"), kw_fmt))

    types = ["i32", "f32", "bool", "str"]
    ty_fmt = _fmt("#4FC1FF")
    for t in types:
      self._rules.append((re.compile(rf"\b{t}\b"), ty_fmt))

    self._rules.append((re.compile(r"\b\d+\.\d+([eE][+-]?\d+)?\b"), _fmt("#B5CEA8")))
    self._rules.append((re.compile(r"\b\d+\b"), _fmt("#B5CEA8")))
    self._rules.append((re.compile(r"->"), _fmt("#D4D4D4")))
    self._rules.append((re.compile(r"[{}()\[\];,:]"), _fmt("#D4D4D4")))

    # Identifiants (apres keywords pour ne pas ecraser)
    self._rules.append((re.compile(r"\b[A-Z][a-zA-Z0-9_]*\b"), _fmt("#4EC9B0")))
    self._rules.append((re.compile(r"\b[a-z_][a-zA-Z0-9_]*\b"), _fmt("#9CDCFE")))

  def highlightBlock(self, text: str) -> None:
    # Couleur de base du texte
    base = QTextCharFormat()
    base.setForeground(QColor("#D4D4D4"))
    self.setFormat(0, len(text), base)

    for pattern, fmt in self._rules:
      for m in pattern.finditer(text):
        self.setFormat(m.start(), m.end() - m.start(), fmt)
