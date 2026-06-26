"""Infobulle flottante au survol — documentation des symboles Vyn."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout

from vynstudio.language_server import SymbolInfo
from vynstudio.theme import LIGHT as T

_KIND_LABELS = {
    "keyword": "Mot-clé",
    "function": "Fonction",
    "module": "Module",
    "import": "Import",
    "snippet": "Snippet",
    "variable": "Variable",
    "struct": "Struct",
    "enum": "Enum",
    "field": "Champ",
    "type": "Type",
}


class VynHoverTooltip(QFrame):
    """Petite boîte flottante sans bordure affichée au survol d'un symbole."""

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setObjectName("VynHoverTooltip")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        self._title = QLabel(self)
        self._title.setFont(QFont("Cascadia Code", 10, QFont.Bold))
        self._sig = QLabel(self)
        self._sig.setFont(QFont("Cascadia Code", 9))
        self._sig.setWordWrap(True)
        self._detail = QLabel(self)
        self._detail.setFont(QFont("Segoe UI", 9))
        self._detail.setWordWrap(True)

        lay.addWidget(self._title)
        lay.addWidget(self._sig)
        lay.addWidget(self._detail)

        self.setStyleSheet(
            f"QFrame#VynHoverTooltip {{ background: #FFFBEB; color: {T['text']}; "
            f"border: 1px solid #D4A017; border-radius: 4px; }}"
            f"QLabel {{ background: transparent; border: none; }}"
        )
        self._sig.setStyleSheet("color: #005A9E;")
        self._detail.setStyleSheet(f"color: {T['muted']};")

    def show_symbol(self, sym: SymbolInfo, global_pos) -> None:
        kind = _KIND_LABELS.get(sym.kind, sym.kind)
        self._title.setText(f"{sym.name}  ·  {kind}")
        sig = sym.signature or ""
        self._sig.setText(sig)
        self._sig.setVisible(bool(sig))
        detail = sym.detail or ""
        self._detail.setText(detail)
        self._detail.setVisible(bool(detail and detail != sig))
        self.adjustSize()
        self.move(global_pos)
        self.show()
        self.raise_()

    def hide_tooltip(self) -> None:
        self.hide()
