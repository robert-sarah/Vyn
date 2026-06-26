"""Fenêtre flottante de complétion — menu sans bordure sous le curseur."""
from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFrame, QListWidget, QListWidgetItem, QVBoxLayout

from vynstudio.language_server import SymbolInfo
from vynstudio.theme import LIGHT as T


_KIND_TAG = {
    "import": "📦 import",
    "use": "🔗 use",
    "type": "◆ type",
    "function": "ƒ fn",
    "keyword": "🔑",
    "module": "📁 mod",
    "snippet": "✂ snippet",
    "variable": "𝑥 var",
    "struct": "▣ struct",
    "enum": "▸ enum",
}


class VynCompletionPopup(QFrame):
    """Popup frameless sous le curseur — ne vole jamais le focus à l'éditeur."""

    itemChosen = pyqtSignal(object)  # SymbolInfo

    def __init__(self, editor=None):
        super().__init__(
            None,
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus,
        )
        self.setObjectName("VynCompletionPopup")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._editor = editor

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget(self)
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setFont(QFont("Cascadia Code", 10))
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setStyleSheet(
            f"QListWidget {{ background: {T['bg']}; color: {T['text']}; "
            f"border: 1px solid {T['border']}; outline: none; }}"
            f"QListWidget::item {{ padding: 3px 8px; }}"
            f"QListWidget::item:selected {{ background: {T['accent']}; color: white; }}"
        )
        self._list.itemActivated.connect(self._on_activate)
        self._list.itemClicked.connect(self._on_activate)
        lay.addWidget(self._list)

    def set_symbols(self, symbols: List[SymbolInfo]) -> None:
        self._list.clear()
        for sym in symbols:
            tag = _KIND_TAG.get(sym.kind, sym.kind)
            label = sym.name
            if sym.detail and sym.detail != sym.signature:
                label = f"{sym.name}  —  {sym.detail}"
            elif sym.signature:
                label = f"{sym.name}  —  {sym.signature}"
            item = QListWidgetItem(f"  {tag}  {label}")
            item.setData(Qt.UserRole, sym)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def filter_prefix(self, prefix: str) -> bool:
        prefix_lower = prefix.lower()
        visible = 0
        first_visible = -1
        for i in range(self._list.count()):
            item = self._list.item(i)
            sym: SymbolInfo = item.data(Qt.UserRole)
            if not sym:
                continue
            haystack = " ".join(filter(None, [
                sym.name, sym.insert or "", sym.detail or "", sym.signature or "",
            ])).lower()
            match = not prefix_lower or haystack.startswith(prefix_lower) or prefix_lower in haystack
            item.setHidden(not match)
            if match:
                visible += 1
                if first_visible < 0:
                    first_visible = i
        if visible == 0:
            return False
        if first_visible >= 0:
            self._list.setCurrentRow(first_visible)
        return True

    def show_below(self, global_pos, width: int = 460) -> None:
        if self._list.count() == 0:
            self.destroy_popup()
            return
        row_h = max(self._list.sizeHintForRow(0), 22)
        count = max(1, min(self._list.count(), 12))
        self.setFixedSize(width, row_h * count + 4)
        self.move(global_pos)
        self.show()
        self.raise_()
        if self._editor is not None:
            self._editor.setFocus()

    def is_active(self) -> bool:
        return self.isVisible() and self._list.count() > 0

    def current_symbol(self) -> Optional[SymbolInfo]:
        item = self._list.currentItem()
        if item and not item.isHidden():
            sym = item.data(Qt.UserRole)
            if isinstance(sym, SymbolInfo):
                return sym
        return None

    def handle_key(self, key: int) -> bool:
        if not self.is_active():
            return False
        if key == Qt.Key_Escape:
            self.destroy_popup()
            return True
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
            self._choose_current()
            return True
        if key == Qt.Key_Up:
            self._move_row(-1)
            return True
        if key == Qt.Key_Down:
            self._move_row(1)
            return True
        if key == Qt.Key_PageUp:
            self._move_row(-5)
            return True
        if key == Qt.Key_PageDown:
            self._move_row(5)
            return True
        return False

    def _move_row(self, delta: int) -> None:
        row = self._list.currentRow()
        n = self._list.count()
        step = 1 if delta > 0 else -1
        for _ in range(abs(delta)):
            nxt = row + step
            while 0 <= nxt < n and self._list.item(nxt).isHidden():
                nxt += step
            if 0 <= nxt < n:
                row = nxt
        if 0 <= row < n:
            self._list.setCurrentRow(row)

    def _on_activate(self, item: QListWidgetItem):
        sym = item.data(Qt.UserRole) if item else None
        if sym:
            self.itemChosen.emit(sym)
        self.destroy_popup()

    def _choose_current(self):
        sym = self.current_symbol()
        if sym:
            self.itemChosen.emit(sym)
        self.destroy_popup()

    def destroy_popup(self) -> None:
        """Ferme et vide immédiatement la boîte bleue."""
        self._list.clear()
        self.hide()
