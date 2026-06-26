"""Vyn code editor — line numbers, Language Server completion, error squiggles, hover docs."""
from __future__ import annotations

import re
from typing import List, Optional

from PyQt5.QtCore import Qt, QRect, QSize, QPoint, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor, QTextFormat
from PyQt5.QtWidgets import QApplication, QPlainTextEdit, QWidget

from vynstudio.completion_context import detect_context, should_auto_trigger
from vynstudio.completion_popup import VynCompletionPopup
from vynstudio.completions import SNIPPETS
from vynstudio.hover_tooltip import VynHoverTooltip
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
        self._active_prefix = ""
        self._completion_ctx = None
        self._line_numbers = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.textChanged.connect(self._on_text_changed)
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

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self._popup = VynCompletionPopup(editor=self)
        self._popup.itemChosen.connect(self._insert_chosen_symbol)

        self._tooltip = VynHoverTooltip()
        self._hover_pos = QPoint()
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._show_hover_tooltip)

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
        from PyQt5.QtWidgets import QTextEdit
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

    def _word_at_pos(self, pos: QPoint) -> str:
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText().strip()

    def _completion_prefix(self) -> tuple[str, int]:
        before = self._text_before_cursor()
        m = re.search(r"([\w]+\.)+[\w]*$", before)
        if m and not before.rstrip().endswith("."):
            return m.group(0), len(m.group(0))
        m2 = re.search(r"[\w]+$", before)
        if m2:
            return m2.group(0), len(m2.group(0))
        return "", 0

    def _cursor_global_bottom_left(self) -> QPoint:
        rect = self.cursorRect()
        return self.viewport().mapToGlobal(QPoint(rect.left(), rect.bottom() + 2))

    def _close_completion(self) -> None:
        self._member_mode = False
        self._member_namespace = ""
        self._active_prefix = ""
        self._completion_ctx = None
        self._popup.destroy_popup()

    def _current_context(self):
        before = self._text_before_cursor()
        return detect_context(before)

    def _trigger_contextual_completion(self, force: bool = False) -> None:
        """Complétion intelligente selon import / let / type / use…"""
        before = self._text_before_cursor()
        ctx = detect_context(before)
        self._completion_ctx = ctx

        if ctx.kind == "general" and not force and not should_auto_trigger(before):
            prefix, _ = self._completion_prefix()
            if not prefix:
                self._close_completion()
                return
            ctx = detect_context(before)
            self._completion_ctx = ctx

        source = self.toPlainText()
        tc = self.textCursor()
        line, col = tc.blockNumber() + 1, tc.positionInBlock() + 1
        symbols = self._lsp.complete_contextual(ctx, source, line, col)
        if not symbols and ctx.kind == "general":
            prefix, _ = self._completion_prefix()
            symbols = self._lsp.complete_unified(prefix, source, line, col)

        if not symbols:
            self._close_completion()
            return
        self._member_mode = False
        self._show_completion(symbols, ctx.prefix)

    def _show_completion(self, symbols: List[SymbolInfo], prefix: str = "") -> None:
        if not symbols:
            self._close_completion()
            return
        self._active_prefix = prefix
        self._popup.set_symbols(symbols)
        if prefix:
            if not self._popup.filter_prefix(prefix if not self._member_mode else prefix):
                self._close_completion()
                return
        pos = self._cursor_global_bottom_left()
        QTimer.singleShot(0, lambda: self._popup.show_below(pos))

    def _trigger_member_completion(self) -> None:
        before = self._text_before_cursor()
        ns = self._lsp.namespace_before_dot(before)
        if not ns:
            return
        self._member_mode = True
        self._member_namespace = ns
        symbols = self._lsp.complete_member(ns, "", self.toPlainText())
        if not symbols:
            self._close_completion()
            return
        self._show_completion(symbols)

    def _trigger_general_completion(self, force: bool = False) -> None:
        self._trigger_contextual_completion(force=force)

    def _update_member_filter(self) -> None:
        if not self._member_mode or not self._popup.is_active():
            return
        before = self._text_before_cursor()
        if not re.search(rf"{re.escape(self._member_namespace)}\.", before):
            self._close_completion()
            return
        prefix = self._lsp.partial_after_dot(before)
        if not self._popup.filter_prefix(prefix):
            self._close_completion()

    def _on_text_changed(self) -> None:
        if self._member_mode and self._popup.is_active():
            self._update_member_filter()
        elif self._popup.is_active() and not self._member_mode:
            prefix, _ = self._completion_prefix()
            if not prefix:
                self._close_completion()
            elif not self._popup.filter_prefix(prefix):
                self._close_completion()

    def _insert_chosen_symbol(self, sym: SymbolInfo) -> None:
        """Règle d'or : fonctions → parenthèses ; mots-clés/instructions → texte exact."""
        is_member = self._member_mode
        self._close_completion()
        self._tooltip.hide_tooltip()

        if not sym or not sym.name:
            return

        tc = self.textCursor()

        if is_member:
            prefix = self._lsp.partial_after_dot(self._text_before_cursor())
            for _ in range(len(prefix)):
                tc.deletePreviousChar()
            text, caret_off = VynLanguageServer.call_snippet(sym.name, sym.signature)
        else:
            ctx = self._completion_ctx
            delete_n = ctx.replace_len if ctx else 0
            if delete_n <= 0:
                prefix, delete_n = self._completion_prefix()

            if delete_n > 0:
                for _ in range(delete_n):
                    tc.deletePreviousChar()

            if sym.kind == "snippet" and sym.insert and "\n" not in sym.insert:
                text = sym.insert
                if sym.name in SNIPPETS:
                    text = re.sub(r"\$\{\d+[^}]*\}", "", SNIPPETS[sym.name])
                caret_off = len(text)
            elif sym.kind == "snippet" and sym.name in SNIPPETS:
                text = re.sub(r"\$\{\d+[^}]*\}", "", SNIPPETS[sym.name])
                caret_off = len(text)
            elif sym.kind == "function":
                name = sym.insert or sym.name
                short = name.split(".")[-1] if "." in name else name
                before = self._text_before_cursor()
                if "." in name and not before.rstrip().endswith("."):
                    mod = name.rsplit(".", 1)[0]
                    if before.endswith(mod) or before.endswith(mod + "."):
                        text, caret_off = VynLanguageServer.call_snippet(short, sym.signature)
                    else:
                        text, caret_off = VynLanguageServer.call_snippet(name, sym.signature)
                else:
                    text, caret_off = VynLanguageServer.call_snippet(short, sym.signature)
            elif sym.kind in ("keyword", "module", "import", "use", "type", "variable", "struct", "enum"):
                text = sym.insert or sym.name
                caret_off = len(text)
                if sym.kind == "keyword" and not text.endswith(";"):
                    kw_space = {"let", "mut", "if", "else", "loop", "match", "try", "return",
                                "import", "use", "break", "continue", "throw", "case", "pub"}
                    if text.strip() in kw_space:
                        text += " "
                        caret_off = len(text)
            else:
                text = sym.insert or sym.name
                caret_off = len(text)

        insert_pos = tc.position()
        tc.insertText(text)
        caret_pos = insert_pos + min(caret_off, len(text))
        doc_end = self._doc_end()
        caret_pos = max(insert_pos, min(caret_pos, doc_end))
        tc.setPosition(caret_pos)
        self.setTextCursor(tc)
        self.setFocus()

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

    def _show_hover_tooltip(self) -> None:
        word = self._word_at_pos(self._hover_pos)
        if not word or not re.match(r"[\w.]+", word):
            self._tooltip.hide_tooltip()
            return
        sym = self._lsp.lookup_hover(word, self.toPlainText())
        if sym:
            global_pos = self.viewport().mapToGlobal(self._hover_pos + QPoint(12, 20))
            self._tooltip.show_symbol(sym, global_pos)
        else:
            self._tooltip.hide_tooltip()

    def mouseMoveEvent(self, event):
        self._hover_pos = event.pos()
        self._tooltip.hide_tooltip()
        self._hover_timer.start(450)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_timer.stop()
        self._tooltip.hide_tooltip()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        self._tooltip.hide_tooltip()

        if self._popup.handle_key(event.key()):
            event.accept()
            if event.key() == Qt.Key_Escape:
                self._close_completion()
            return

        if event.key() == Qt.Key_Space and event.modifiers() & Qt.ControlModifier:
            self._trigger_general_completion(force=True)
            return

        super().keyPressEvent(event)

        before = self._text_before_cursor()

        if event.key() == Qt.Key_Escape:
            self._close_completion()
            return

        if event.text() == ".":
            self._trigger_member_completion()
        elif self._member_mode:
            self._update_member_filter()
        elif event.text() == " " or should_auto_trigger(before):
            self._trigger_contextual_completion(force=True)
        elif event.key() == Qt.Key_Backspace:
            if should_auto_trigger(before) or self._popup.is_active():
                self._trigger_contextual_completion(force=True)
            else:
                prefix, _ = self._completion_prefix()
                if not prefix:
                    self._close_completion()
        elif event.text() and (event.text().isalnum() or event.text() == "_"):
            self._trigger_contextual_completion()

    def focusOutEvent(self, event):
        QTimer.singleShot(100, self._maybe_close_popup_on_focus_loss)
        super().focusOutEvent(event)

    def _maybe_close_popup_on_focus_loss(self):
        if self._focus_in_popup():
            return
        if not self.hasFocus():
            self._close_completion()
            self._tooltip.hide_tooltip()
