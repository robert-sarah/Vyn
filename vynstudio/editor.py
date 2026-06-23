"""Vyn code editor — line numbers, Language Server completion, error squiggles."""
from __future__ import annotations

import re
from typing import List

from PyQt5.QtCore import Qt, QRect, QSize, QPoint, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor, QTextFormat
from PyQt5.QtWidgets import QApplication, QPlainTextEdit, QWidget, QCompleter, QTextEdit

from vynstudio.completion_popup import VynCompletionPopup
from vynstudio.completions import ALL_COMPLETIONS, SNIPPETS
from vynstudio.language_server import SERVER, VynLanguageServer, SymbolInfo
from vynstudio.theme import LIGHT as T


class LineNumberArea(QWidget):
    def __init__(self, editor: "VynCodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class VynCodeEditor(QPlainTextEdit):
    """Éditeur Vyn avec mini Language Server offline intégré."""

    def __init__(self, parent=None, light: bool = True):
        super().__init__(parent)
        self._light = light
        self._diagnostics: list = []
        self._lsp: VynLanguageServer = SERVER
        self._member_mode = False
        self._member_namespace = ""
        self._line_numbers = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_width(0)
        self._highlight_current_line()

        font = QFont("Cascadia Code", 11)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)

        bg = T["editor_bg"] if light else "#1E1E1E"
        fg = T["editor_text"] if light else "#D4D4D4"
        sel = T["selection"] if light else "#264F78"
        self.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {bg}; color: {fg}; border: none; "
            f"selection-background-color: {sel}; }}"
        )

        self._popup = VynCompletionPopup(editor=self)
        self._popup.itemChosen.connect(self._insert_member_symbol)

        self._completer = QCompleter(ALL_COMPLETIONS, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.activated.connect(self._insert_completion)

    def set_diagnostic_markers(self, diagnostics: list) -> None:
        self._diagnostics = diagnostics
        self._highlight_current_line()

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
        bg = T["line_number_bg"] if self._light else "#1E1E1E"
        painter.fillRect(event.rect(), QColor(bg))
        painter.setPen(QColor(T["line_number"] if self._light else "#858585"))
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

    def _doc_end(self) -> int:
        return max(0, self.document().characterCount() - 1)

    def _safe_squiggle(self, block, col: int, length: int) -> QTextCursor | None:
        """Curseur squiggle borné — évite QTextCursor::setPosition out of range."""
        if not block.isValid():
            return None
        line_len = len(block.text())
        if line_len == 0:
            return None
        col0 = max(0, min(col - 1, line_len - 1)) if col > 0 else 0
        span = max(length, 1) if length > 0 else line_len - col0
        end0 = min(col0 + span, line_len)
        if end0 <= col0:
            end0 = min(col0 + 1, line_len)
        start_pos = block.position() + col0
        end_pos = block.position() + end0
        doc_end = self._doc_end()
        start_pos = max(0, min(start_pos, doc_end))
        end_pos = max(start_pos, min(end_pos, doc_end))
        cur = QTextCursor(block)
        cur.setPosition(start_pos)
        if end_pos > start_pos:
            cur.setPosition(end_pos, QTextCursor.KeepAnchor)
        return cur

    def _highlight_current_line(self):
        extra: List[QTextEdit.ExtraSelection] = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            hl = T["current_line"] if self._light else "#2A2A2A"
            sel.format.setBackground(QColor(hl))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)

        for d in self._diagnostics:
            if getattr(d, "severity", "") == "info":
                continue
            block = self.document().findBlockByLineNumber(max(0, d.line - 1))
            if not block.isValid():
                continue
            cur = self._safe_squiggle(block, d.col, getattr(d, "length", 0))
            if cur is None:
                continue
            sel = QTextEdit.ExtraSelection()
            fmt = QTextCharFormat()
            color = QColor("#E51400") if d.severity == "error" else QColor("#BF8803")
            fmt.setUnderlineColor(color)
            fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            sel.format = fmt
            sel.cursor = cur
            extra.append(sel)

        self.setExtraSelections(extra)

    def _text_before_cursor(self) -> str:
        tc = self.textCursor()
        return tc.block().text()[: tc.positionInBlock()]

    def _text_under_cursor(self) -> str:
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def _completion_prefix(self) -> tuple[str, int]:
        before = self._text_before_cursor()
        m = re.search(r"([\w]+\.)+[\w]*$", before)
        if m:
            return m.group(0), len(m.group(0))
        m2 = re.search(r"[\w]+$", before)
        if m2:
            return m2.group(0), len(m2.group(0))
        return "", 0

    def _cursor_global_bottom_left(self) -> QPoint:
        rect = self.cursorRect()
        return self.viewport().mapToGlobal(QPoint(rect.left(), rect.bottom() + 2))

    def _trigger_member_completion(self) -> None:
        before = self._text_before_cursor()
        ns = self._lsp.namespace_before_dot(before)
        if not ns:
            return
        symbols = self._lsp.complete_member(ns, "", self.toPlainText())
        if not symbols:
            self._close_member_popup()
            return
        self._member_mode = True
        self._member_namespace = ns
        self._popup.set_symbols(symbols)
        pos = self._cursor_global_bottom_left()
        QTimer.singleShot(0, lambda: self._popup.show_below(pos))

    def _update_member_filter(self) -> None:
        if not self._member_mode or not self._popup.is_active():
            return
        before = self._text_before_cursor()
        if not re.search(rf"{re.escape(self._member_namespace)}\.", before):
            self._close_member_popup()
            return
        prefix = self._lsp.partial_after_dot(before)
        if not self._popup.filter_prefix(prefix):
            self._close_member_popup()

    def _close_member_popup(self) -> None:
        self._member_mode = False
        self._member_namespace = ""
        self._popup.destroy_popup()

    def _insert_member_symbol(self, sym: SymbolInfo) -> None:
        """Insère fn(...) avec curseur dans les parenthèses, puis détruit le popup."""
        self._close_member_popup()

        if not sym or not sym.name:
            return

        prefix = self._lsp.partial_after_dot(self._text_before_cursor())
        text, caret_off = VynLanguageServer.call_snippet(sym.name, sym.signature)

        tc = self.textCursor()
        for _ in range(len(prefix)):
            tc.deletePreviousChar()
        insert_pos = tc.position()
        tc.insertText(text)
        caret_pos = insert_pos + min(caret_off, len(text))
        doc_end = self._doc_end()
        caret_pos = max(insert_pos, min(caret_pos, doc_end))
        tc.setPosition(caret_pos)
        self.setTextCursor(tc)
        self.setFocus()

    def _insert_completion(self, completion: str):
        if self._completer.widget() is not self:
            return
        text = SNIPPETS.get(completion, completion)
        text = re.sub(r"\$\{\d+[^}]*\}", "", text)

        before = self._text_before_cursor()
        if "." in text and not text.startswith("import ") and not text.startswith("use "):
            mod, _, rest = text.partition(".")
            if before.endswith(mod + "."):
                text = rest
            elif before.endswith(mod) and not before.endswith("."):
                text = "." + rest

        prefix, delete_n = self._completion_prefix()
        if not delete_n:
            delete_n = len(self._completer.completionPrefix())

        tc = self.textCursor()
        if delete_n > 0:
            for _ in range(delete_n):
                tc.deletePreviousChar()
        tc.insertText(text)
        self.setTextCursor(tc)

    def _run_completer(self, force_prefix: str = ""):
        prefix, _ = self._completion_prefix()
        if force_prefix:
            prefix = force_prefix
        if not prefix:
            prefix = self._text_under_cursor()

        source = self.toPlainText()
        lsp_items = self._lsp.complete_general(prefix, source)
        if lsp_items:
            strings = [sym.insert or sym.name for sym in lsp_items]
            merged = sorted(set(ALL_COMPLETIONS + strings))
            model = self._completer.model()
            if hasattr(model, "setStringList"):
                model.setStringList(merged)

        self._completer.setCompletionPrefix(prefix)
        popup = self._completer.popup()
        popup.setStyleSheet(
            "QListView { background: #FFFFFF; color: #333; border: 1px solid #CCC; }"
            "QListView::item:selected { background: #0060C0; color: white; }"
        )
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0) + 30)
        self._completer.complete(cr)

    def _focus_in_popup(self) -> bool:
        fw = QApplication.focusWidget()
        if fw is None:
            return False
        p = fw
        while p is not None:
            if p is self._popup:
                return True
            p = p.parentWidget()
        return False

    def keyPressEvent(self, event):
        if self._popup.handle_key(event.key()):
            event.accept()
            if event.key() == Qt.Key_Escape:
                self._close_member_popup()
            return

        if self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab):
                event.ignore()
                return

        if event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            self._run_completer()
            return

        super().keyPressEvent(event)

        if event.text() == ".":
            self._trigger_member_completion()
        elif self._member_mode:
            self._update_member_filter()
        elif len(self._text_under_cursor()) >= 2:
            self._run_completer()

    def focusOutEvent(self, event):
        QTimer.singleShot(100, self._maybe_close_popup_on_focus_loss)
        super().focusOutEvent(event)

    def _maybe_close_popup_on_focus_loss(self):
        if self._focus_in_popup():
            return
        if not self.hasFocus():
            self._close_member_popup()
