"""Éditeur Vyn avec numéros de ligne et autocomplétion."""
from __future__ import annotations

import re
from typing import Optional

from PyQt5.QtCore import Qt, QRect, QSize, QStringListModel
from PyQt5.QtGui import QColor, QFont, QPainter, QTextFormat
from PyQt5.QtWidgets import (
    QPlainTextEdit, QWidget, QCompleter, QTextEdit,
)

from vynstudio.completions import ALL_COMPLETIONS, SNIPPETS


class LineNumberArea(QWidget):
    def __init__(self, editor: "VynCodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class VynCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_numbers = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_width(0)
        self._highlight_current_line()

        font = QFont("Cascadia Code", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #1E1E1E; color: #D4D4D4; border: none; "
            "selection-background-color: #264F78; font-family: 'Consolas', 'Cascadia Code', monospace; }"
        )

        self._completer = QCompleter(ALL_COMPLETIONS, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.activated.connect(self._insert_completion)

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_numbers.scroll(0, dy)
        else:
            self._line_numbers.update(0, rect.y(), self._line_numbers.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_numbers.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_numbers)
        painter.fillRect(event.rect(), QColor("#1E1E1E"))
        painter.setPen(QColor("#858585"))
        block = self.firstVisibleBlock()
        num = block.blockNumber() + 1
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, int(top), self._line_numbers.width() - 4,
                    self.fontMetrics().height(), Qt.AlignRight, str(num)
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            num += 1

    def _highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#2A2A2A"))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
        self.setExtraSelections(extra)

    def _text_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(tc.WordUnderCursor)
        return tc.selectedText()

    def _insert_completion(self, completion: str):
        if self._completer.widget() is not self:
            return
        tc = self.textCursor()
        extra = len(self._completer.completionPrefix())
        tc.movePosition(tc.Left, tc.KeepAnchor, extra)
        text = SNIPPETS.get(completion, completion)
        text = text.replace("${0}", "").replace("${1:name}", "name").replace("${2:params}", "").replace("${3:i32}", "i32")
        text = re.sub(r"\$\{\d+[^}]*\}", "", text)
        tc.insertText(text)
        self.setTextCursor(tc)

    def _run_completer(self, prefix: str = ""):
        if not prefix:
            prefix = self._text_under_cursor()
        if len(prefix) < 1 and not prefix:
            prefix = ""
        self._completer.setCompletionPrefix(prefix)
        popup = self._completer.popup()
        popup.setStyleSheet(
            "QListView { background: #252526; color: #CCCCCC; border: 1px solid #454545; }"
            "QListView::item:selected { background: #094771; }"
        )
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0) + 30)
        self._completer.complete(cr)

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab):
                event.ignore()
                return
        if event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            self._run_completer()
            return
        super().keyPressEvent(event)
        prefix = self._text_under_cursor()
        if event.text() in (".",):
            self._run_completer(prefix)
        elif len(prefix) >= 2:
            self._run_completer(prefix)
