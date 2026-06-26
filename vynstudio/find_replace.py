"""VynStudio — Find & Replace panel (VS Code style)."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor, QTextCharFormat, QTextCursor, QKeySequence, QFont,
)
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
    QPushButton, QLabel, QCheckBox, QToolButton,
    QFrame, QShortcut, QSizePolicy,
)


class FindReplaceBar(QWidget):
    """Floating find/replace bar (like VS Code Ctrl+H panel).

    Signals
    -------
    closed()          — user closed the panel
    match_count(int)  — emitted when match count changes
    """

    closed       = pyqtSignal()
    match_count  = pyqtSignal(int)

    # ── highlight formats ────────────────────────────────────────────────────
    _FMT_MATCH   = QTextCharFormat()
    _FMT_CURRENT = QTextCharFormat()

    def __init__(self, editor, theme: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._editor  = editor        # VynCodeEditor (QPlainTextEdit)
        self._theme   = theme
        self._matches: List[QTextCursor] = []
        self._cur_idx: int = -1
        self._replace_visible = False

        # Debounce timer for live search
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_search)

        self._setup_formats()
        self._build_ui()
        self._apply_theme()

    # ── Formats ──────────────────────────────────────────────────────────────

    def _setup_formats(self) -> None:
        T = self._theme
        FindReplaceBar._FMT_MATCH.setBackground(QColor(T.get("find_match", "#FFFF00")))
        FindReplaceBar._FMT_MATCH.setForeground(QColor(T.get("editor_text", "#000000")))
        FindReplaceBar._FMT_CURRENT.setBackground(QColor(T.get("accent", "#007ACC")))
        FindReplaceBar._FMT_CURRENT.setForeground(QColor("#FFFFFF"))

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        T = self._theme

        self.setObjectName("FindReplaceBar")
        self.setMaximumHeight(120)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        # ── Row 1 : Find ──────────────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(4)

        # Expand/collapse replace
        self._btn_toggle = QToolButton()
        self._btn_toggle.setText("▶")
        self._btn_toggle.setFixedSize(18, 18)
        self._btn_toggle.setToolTip("Toggle Replace")
        self._btn_toggle.clicked.connect(self._toggle_replace)
        row1.addWidget(self._btn_toggle)

        # Find input
        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Find")
        self._find_input.setMinimumWidth(180)
        self._find_input.textChanged.connect(self._on_text_changed)
        self._find_input.returnPressed.connect(self.find_next)
        row1.addWidget(self._find_input)

        # Option checkboxes
        self._cb_case = QCheckBox("Aa")
        self._cb_case.setToolTip("Match Case (Alt+C)")
        self._cb_case.stateChanged.connect(self._on_text_changed)
        row1.addWidget(self._cb_case)

        self._cb_word = QCheckBox("\\b")
        self._cb_word.setToolTip("Match Whole Word (Alt+W)")
        self._cb_word.stateChanged.connect(self._on_text_changed)
        row1.addWidget(self._cb_word)

        self._cb_regex = QCheckBox(".*")
        self._cb_regex.setToolTip("Use Regular Expression (Alt+R)")
        self._cb_regex.stateChanged.connect(self._on_text_changed)
        row1.addWidget(self._cb_regex)

        # Match counter
        self._lbl_count = QLabel("No results")
        self._lbl_count.setMinimumWidth(80)
        self._lbl_count.setAlignment(Qt.AlignCenter)
        self._lbl_count.setObjectName("MatchCount")
        row1.addWidget(self._lbl_count)

        # Navigation buttons
        self._btn_prev = QToolButton()
        self._btn_prev.setText("↑")
        self._btn_prev.setToolTip("Previous Match (Shift+Enter / Shift+F3)")
        self._btn_prev.setFixedSize(24, 24)
        self._btn_prev.clicked.connect(self.find_prev)
        row1.addWidget(self._btn_prev)

        self._btn_next = QToolButton()
        self._btn_next.setText("↓")
        self._btn_next.setToolTip("Next Match (Enter / F3)")
        self._btn_next.setFixedSize(24, 24)
        self._btn_next.clicked.connect(self.find_next)
        row1.addWidget(self._btn_next)

        # Close button
        self._btn_close = QToolButton()
        self._btn_close.setText("✕")
        self._btn_close.setFixedSize(22, 22)
        self._btn_close.setToolTip("Close (Esc)")
        self._btn_close.clicked.connect(self.close_bar)
        row1.addWidget(self._btn_close)

        outer.addLayout(row1)

        # ── Row 2 : Replace (hidden by default) ───────────────────────────────
        self._replace_widget = QWidget()
        row2 = QHBoxLayout(self._replace_widget)
        row2.setContentsMargins(22, 0, 0, 0)  # indent to align with find
        row2.setSpacing(4)

        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace")
        self._replace_input.setMinimumWidth(180)
        self._replace_input.returnPressed.connect(self.replace_next)
        row2.addWidget(self._replace_input)

        self._btn_replace = QPushButton("Replace")
        self._btn_replace.setFixedHeight(24)
        self._btn_replace.clicked.connect(self.replace_next)
        row2.addWidget(self._btn_replace)

        self._btn_replace_all = QPushButton("Replace All")
        self._btn_replace_all.setFixedHeight(24)
        self._btn_replace_all.clicked.connect(self.replace_all)
        row2.addWidget(self._btn_replace_all)

        row2.addStretch()

        self._replace_widget.setVisible(False)
        outer.addWidget(self._replace_widget)

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close_bar)
        QShortcut(QKeySequence(Qt.Key_F3),     self, self.find_next)
        QShortcut(QKeySequence("Shift+F3"),    self, self.find_prev)

    def _apply_theme(self) -> None:
        T = self._theme
        bg    = T.get("find_bg",     T.get("panel_bg", "#F3F3F3"))
        txt   = T.get("text",        "#333333")
        inp   = T.get("input_bg",    "#FFFFFF")
        brd   = T.get("find_border", "#007ACC")
        btn   = T.get("accent",      "#007ACC")
        btnfg = T.get("accent_fg",   "#FFFFFF")
        muted = T.get("muted",       "#6E6E6E")

        self.setStyleSheet(f"""
            FindReplaceBar {{
                background: {bg};
                border-bottom: 1px solid {T.get('border','#E5E5E5')};
            }}
            QLineEdit {{
                background: {inp};
                color: {txt};
                border: 1px solid {T.get('input_border','#BEBEBE')};
                border-radius: 3px;
                padding: 3px 6px;
                font-family: Consolas, monospace;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border-color: {brd};
            }}
            QCheckBox {{
                color: {txt};
                font-family: Consolas, monospace;
                font-size: 9pt;
                padding: 2px 4px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {T.get('input_border','#BEBEBE')};
                border-radius: 2px;
                background: {inp};
            }}
            QCheckBox::indicator:checked {{
                background: {btn};
                border-color: {btn};
            }}
            QPushButton {{
                background: {btn};
                color: {btnfg};
                border: none;
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 9pt;
            }}
            QPushButton:hover {{ background: {T.get('accent_hover', btn)}; }}
            QToolButton {{
                background: transparent;
                color: {txt};
                border: none;
                border-radius: 3px;
                font-size: 11pt;
            }}
            QToolButton:hover {{ background: {T.get('tree_hover','#E8E8E8')}; }}
            #MatchCount {{
                color: {muted};
                font-size: 9pt;
                font-family: Consolas, monospace;
            }}
        """)

    # ── Public API ────────────────────────────────────────────────────────────

    def open_find(self, initial_text: str = "") -> None:
        """Show the bar in find-only mode."""
        self._replace_visible = False
        self._replace_widget.setVisible(False)
        self._btn_toggle.setText("▶")
        self.show()
        if initial_text:
            self._find_input.setText(initial_text)
        self._find_input.setFocus()
        self._find_input.selectAll()
        self._do_search()

    def open_replace(self, initial_text: str = "") -> None:
        """Show the bar with replace row visible."""
        self._replace_visible = True
        self._replace_widget.setVisible(True)
        self._btn_toggle.setText("▼")
        self.show()
        if initial_text:
            self._find_input.setText(initial_text)
        self._find_input.setFocus()
        self._find_input.selectAll()
        self._do_search()

    def close_bar(self) -> None:
        """Hide the bar and remove highlights."""
        self._clear_highlights()
        self._matches.clear()
        self._cur_idx = -1
        self._lbl_count.setText("")
        self.hide()
        self.closed.emit()
        self._editor.setFocus()

    def find_next(self) -> None:
        """Navigate to the next match."""
        if not self._matches:
            self._do_search()
            return
        self._cur_idx = (self._cur_idx + 1) % len(self._matches)
        self._goto_current()

    def find_prev(self) -> None:
        """Navigate to the previous match."""
        if not self._matches:
            self._do_search()
            return
        self._cur_idx = (self._cur_idx - 1) % len(self._matches)
        self._goto_current()

    def replace_next(self) -> None:
        """Replace the current match and advance."""
        if not self._matches or self._cur_idx < 0:
            self.find_next()
            return
        if self._cur_idx >= len(self._matches):
            return
        cur  = self._matches[self._cur_idx]
        repl = self._resolve_replace(cur.selectedText())
        cur.insertText(repl)
        self._do_search()
        if self._matches:
            self._cur_idx = min(self._cur_idx, len(self._matches) - 1)
            self._goto_current()

    def replace_all(self) -> None:
        """Replace all matches at once."""
        self._do_search()
        if not self._matches:
            return
        doc = self._editor.document()
        macro_cursor = QTextCursor(doc)
        macro_cursor.beginEditBlock()
        # Replace in reverse to preserve positions
        for cur in reversed(self._matches):
            repl = self._resolve_replace(cur.selectedText())
            cur.insertText(repl)
        macro_cursor.endEditBlock()
        count = len(self._matches)
        self._matches.clear()
        self._cur_idx = -1
        self._lbl_count.setText(f"Replaced {count}")
        self._editor.setFocus()

    def update_theme(self, theme: dict) -> None:
        """Update colors when theme changes."""
        self._theme = theme
        self._setup_formats()
        self._apply_theme()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _toggle_replace(self) -> None:
        self._replace_visible = not self._replace_visible
        self._replace_widget.setVisible(self._replace_visible)
        self._btn_toggle.setText("▼" if self._replace_visible else "▶")
        if self._replace_visible:
            self._replace_input.setFocus()

    def _on_text_changed(self) -> None:
        # Debounce: search 150 ms after last keystroke
        self._timer.start(150)

    def _do_search(self) -> None:
        """Find all matches in the document."""
        self._clear_highlights()
        self._matches.clear()
        self._cur_idx = -1

        pattern = self._find_input.text()
        if not pattern:
            self._lbl_count.setText("No results")
            self.match_count.emit(0)
            return

        # Build regex
        try:
            regex = self._build_regex(pattern)
        except re.error as e:
            self._lbl_count.setText(f"Regex error: {e}")
            self.match_count.emit(0)
            return

        # Search document
        source = self._editor.toPlainText()
        cursors: List[QTextCursor] = []
        for m in regex.finditer(source):
            tc = QTextCursor(self._editor.document())
            tc.setPosition(m.start())
            tc.setPosition(m.end(), QTextCursor.KeepAnchor)
            cursors.append(tc)

        self._matches = cursors
        n = len(cursors)

        if n == 0:
            self._lbl_count.setText("No results")
            self._find_input.setStyleSheet(
                f"background: {self._theme.get('error_bg','#FFF0F0')};"
                f"color: {self._theme.get('error','#E51400')};"
                f"border: 1px solid {self._theme.get('error','#E51400')};"
                f"border-radius: 3px; padding: 3px 6px;"
            )
        else:
            self._find_input.setStyleSheet("")
            self._highlight_all()
            # Jump to closest match to current cursor
            cur_pos = self._editor.textCursor().position()
            self._cur_idx = self._find_closest(cur_pos)
            self._goto_current(scroll_only=False)
            self._lbl_count.setText(f"{self._cur_idx + 1} of {n}")

        self.match_count.emit(n)

    def _build_regex(self, pattern: str) -> re.Pattern:
        flags = re.MULTILINE
        if not self._cb_case.isChecked():
            flags |= re.IGNORECASE
        if self._cb_regex.isChecked():
            expr = pattern
        else:
            expr = re.escape(pattern)
        if self._cb_word.isChecked():
            expr = rf"\b{expr}\b"
        return re.compile(expr, flags)

    def _resolve_replace(self, matched: str) -> str:
        """Resolve the replacement string (supports \\1 backreferences)."""
        repl = self._replace_input.text()
        if self._cb_regex.isChecked() and self._matches and self._cur_idx >= 0:
            try:
                pattern = self._find_input.text()
                regex   = self._build_regex(pattern)
                repl    = regex.sub(repl, matched, count=1)
            except re.error:
                pass
        return repl

    def _highlight_all(self) -> None:
        """Apply highlight format to all matches (except current)."""
        extras = []
        from PyQt5.QtWidgets import QTextEdit
        for i, cur in enumerate(self._matches):
            if i == self._cur_idx:
                continue
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cur
            sel.format  = self._FMT_MATCH
            extras.append(sel)
        # Preserve editor's existing extras and add ours
        existing = self._editor.extraSelections()
        self._editor.setExtraSelections(existing + extras)

    def _clear_highlights(self) -> None:
        """Remove find highlights from editor extra selections."""
        from PyQt5.QtWidgets import QTextEdit
        # Keep only non-find extras (diagnostic squiggles etc.)
        existing = self._editor.extraSelections()
        cleaned  = [
            e for e in existing
            if e.format.background().color() != self._FMT_MATCH.background().color()
            and e.format.background().color() != self._FMT_CURRENT.background().color()
        ]
        self._editor.setExtraSelections(cleaned)

    def _goto_current(self, scroll_only: bool = False) -> None:
        """Scroll to and select the current match."""
        if not self._matches or self._cur_idx < 0:
            return
        from PyQt5.QtWidgets import QTextEdit
        cur = QTextCursor(self._matches[self._cur_idx])
        self._editor.setTextCursor(cur)
        self._editor.ensureCursorVisible()

        # Re-apply highlights so current one is colored differently
        self._clear_highlights()
        extras = []
        for i, c in enumerate(self._matches):
            sel = QTextEdit.ExtraSelection()
            sel.cursor = c
            sel.format  = self._FMT_CURRENT if i == self._cur_idx else self._FMT_MATCH
            extras.append(sel)
        existing = self._editor.extraSelections()
        self._editor.setExtraSelections(existing + extras)

        n = len(self._matches)
        self._lbl_count.setText(f"{self._cur_idx + 1} of {n}")

    def _find_closest(self, pos: int) -> int:
        """Return index of match closest to cursor position."""
        if not self._matches:
            return 0
        best_i   = 0
        best_dist = abs(self._matches[0].anchor() - pos)
        for i, cur in enumerate(self._matches):
            d = abs(cur.anchor() - pos)
            if d < best_dist:
                best_dist = d
                best_i    = i
        return best_i

    # ── Key events ────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close_bar()
        elif event.key() == Qt.Key_Return and event.modifiers() & Qt.ShiftModifier:
            self.find_prev()
        elif event.key() == Qt.Key_Return:
            self.find_next()
        else:
            super().keyPressEvent(event)
