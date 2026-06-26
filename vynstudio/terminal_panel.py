"""VynStudio — Integrated Terminal Panel."""
from __future__ import annotations

import os
import sys
import subprocess
import threading
import shlex
from pathlib import Path
from typing import Optional, List

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import (
    QColor, QTextCharFormat, QFont, QKeySequence, QTextCursor,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QLineEdit, QPushButton, QLabel, QToolButton, QSizePolicy,
    QComboBox, QShortcut,
)


# ─── Signal bridge (thread → Qt) ─────────────────────────────────────────────

class _Bridge(QObject):
    output   = pyqtSignal(str, str)   # (text, kind)  kind = "stdout"|"stderr"|"info"|"error"
    finished = pyqtSignal(int)        # exit code


# ═══════════════════════════════════════════════════════════════════════════════
#  Terminal Output Widget
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalOutput(QPlainTextEdit):
    """Read-only ANSI-aware output pane."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setReadOnly(True)
        self.setMaximumBlockCount(10_000)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        font = QFont("Cascadia Code", 10)
        if not font.exactMatch():
            font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self._apply_theme()

    def _apply_theme(self) -> None:
        T = self._theme
        bg  = T.get("terminal_bg",   T.get("panel_bg", "#1E1E1E"))
        fg  = T.get("terminal_text", T.get("text",     "#CCCCCC"))
        sel = T.get("terminal_selection", T.get("selection", "#264F78"))
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {fg};
                border: none;
                selection-background-color: {sel};
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 10pt;
            }}
        """)

    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        self._apply_theme()

    def append_output(self, text: str, kind: str = "stdout") -> None:
        T      = self._theme
        colors = {
            "stdout": T.get("terminal_text",  "#CCCCCC"),
            "stderr": T.get("error",          "#F14C4C"),
            "info":   T.get("info",           "#3794FF"),
            "error":  T.get("error",          "#F14C4C"),
            "cmd":    T.get("accent",         "#007ACC"),
            "prompt": T.get("success",        "#89D185"),
        }
        color = colors.get(kind, colors["stdout"])

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)

        # Strip ANSI escape sequences for simplicity
        clean = _strip_ansi(text)
        cursor.insertText(clean)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_output(self) -> None:
        self.clear()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    import re
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)


# ═══════════════════════════════════════════════════════════════════════════════
#  Command Input Bar
# ═══════════════════════════════════════════════════════════════════════════════

class CommandInput(QWidget):
    """Single-line command input with history."""

    submitted = pyqtSignal(str)   # emitted when user presses Enter

    def __init__(self, theme: dict, cwd: str, parent=None):
        super().__init__(parent)
        self._theme   = theme
        self._cwd     = cwd
        self._history: List[str] = []
        self._hist_idx: int = -1
        self._build_ui()

    def _build_ui(self) -> None:
        T   = self._theme
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(4)

        # Prompt label
        self._prompt = QLabel("$")
        self._prompt.setFont(QFont("Consolas", 10))
        self._prompt.setStyleSheet(f"color: {T.get('success','#89D185')}; font-weight: bold;")
        lay.addWidget(self._prompt)

        # Input field
        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter command…")
        self._input.setFont(QFont("Consolas", 10))
        self._input.returnPressed.connect(self._on_submit)
        self._input.installEventFilter(self)
        lay.addWidget(self._input)

        # Run button
        self._btn_run = QPushButton("▶ Run")
        self._btn_run.setFixedWidth(70)
        self._btn_run.clicked.connect(self._on_submit)
        lay.addWidget(self._btn_run)

        self._apply_theme()

    def _apply_theme(self) -> None:
        T   = self._theme
        bg  = T.get("terminal_bg", T.get("panel_bg", "#1E1E1E"))
        inp = T.get("input_bg",    T.get("terminal_bg", "#2A2A2A"))
        fg  = T.get("text",        "#CCCCCC")
        brd = T.get("input_border","#555555")
        btn = T.get("accent",      "#007ACC")
        self.setStyleSheet(f"""
            QWidget {{ background: {bg}; }}
            QLineEdit {{
                background: {inp};
                color: {fg};
                border: 1px solid {brd};
                border-radius: 3px;
                padding: 4px 8px;
                font-family: Consolas, monospace;
                font-size: 10pt;
            }}
            QLineEdit:focus {{ border-color: {btn}; }}
            QPushButton {{
                background: {btn};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }}
            QPushButton:hover {{ background: {T.get('accent_hover', btn)}; }}
        """)

    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        self._apply_theme()

    def set_cwd(self, cwd: str) -> None:
        self._cwd = cwd
        short = Path(cwd).name or cwd
        self._prompt.setText(f"{short} $")

    def set_focus(self) -> None:
        self._input.setFocus()
        self._input.selectAll()

    def _on_submit(self) -> None:
        cmd = self._input.text().strip()
        if not cmd:
            return
        self._history.append(cmd)
        self._hist_idx = len(self._history)
        self._input.clear()
        self.submitted.emit(cmd)

    def eventFilter(self, obj, event) -> bool:
        from PyQt5.QtCore import QEvent
        if obj is self._input and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Up:
                self._navigate_history(-1)
                return True
            if key == Qt.Key_Down:
                self._navigate_history(+1)
                return True
            if key == Qt.Key_Tab:
                self._autocomplete()
                return True
        return super().eventFilter(obj, event)

    def _navigate_history(self, delta: int) -> None:
        if not self._history:
            return
        self._hist_idx = max(0, min(len(self._history) - 1, self._hist_idx + delta))
        self._input.setText(self._history[self._hist_idx])
        self._input.end(False)

    def _autocomplete(self) -> None:
        """Simple path/command autocomplete."""
        text  = self._input.text()
        parts = shlex.split(text) if text.strip() else []
        if not parts:
            return
        last  = parts[-1]
        base  = Path(self._cwd)
        try:
            if os.sep in last or "/" in last:
                parent = base / Path(last).parent
                prefix = Path(last).name
            else:
                parent = base
                prefix = last
            matches = [
                p.name for p in parent.iterdir()
                if p.name.startswith(prefix)
            ]
            if len(matches) == 1:
                completed = str(parent / matches[0])
                if len(parts) == 1:
                    self._input.setText(completed)
                else:
                    new_parts = parts[:-1] + [completed]
                    self._input.setText(" ".join(new_parts))
                self._input.end(False)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Terminal Panel  (output + input + toolbar)
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalPanel(QWidget):
    """Full integrated terminal panel for VynStudio.

    Features
    --------
    - Run arbitrary shell commands
    - Kill running process (Ctrl+C)
    - Clear output
    - Command history (↑ / ↓)
    - Tab completion
    - Multiple terminal instances via tabs
    - Theme-aware
    - Convenience shortcuts: vyn run, vyn build, python, etc.
    """

    command_started  = pyqtSignal(str)    # command text
    command_finished = pyqtSignal(int)    # exit code
    output_line      = pyqtSignal(str)    # last line of output

    def __init__(
        self,
        theme:    dict,
        cwd:      Optional[str] = None,
        parent:   Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._theme   = theme
        self._cwd     = cwd or str(Path.cwd())
        self._process: Optional[subprocess.Popen] = None
        self._bridge  = _Bridge()
        self._bridge.output.connect(self._on_output)
        self._bridge.finished.connect(self._on_finished)

        self._build_ui()
        self._welcome()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        T   = self._theme
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(32)
        tb_lay  = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 4, 8, 4)
        tb_lay.setSpacing(6)

        lbl = QLabel("TERMINAL")
        lbl.setStyleSheet(f"color: {T.get('muted','#6E6E6E')}; font-size: 9pt; font-weight: bold;")
        tb_lay.addWidget(lbl)

        # Quick commands dropdown
        self._quick = QComboBox()
        self._quick.setFixedWidth(160)
        self._quick.addItem("Quick command…")
        self._quick.addItem("vyn run …")
        self._quick.addItem("vyn build …")
        self._quick.addItem("python -m vyn.cli run …")
        self._quick.addItem("python -m pytest …")
        self._quick.addItem("pip install …")
        self._quick.addItem("vpm install")
        self._quick.addItem("vpm list")
        self._quick.currentTextChanged.connect(self._on_quick_cmd)
        tb_lay.addWidget(self._quick)

        tb_lay.addStretch()

        # Kill button
        self._btn_kill = QToolButton()
        self._btn_kill.setText("⏹ Kill")
        self._btn_kill.setToolTip("Kill running process (Ctrl+C)")
        self._btn_kill.setEnabled(False)
        self._btn_kill.clicked.connect(self.kill_process)
        tb_lay.addWidget(self._btn_kill)

        # Clear button
        self._btn_clear = QToolButton()
        self._btn_clear.setText("🗑 Clear")
        self._btn_clear.setToolTip("Clear terminal output")
        self._btn_clear.clicked.connect(self.clear)
        tb_lay.addWidget(self._btn_clear)

        # New terminal button (emits signal for parent to handle)
        self._btn_new = QToolButton()
        self._btn_new.setText("+ New")
        self._btn_new.setToolTip("New terminal")
        tb_lay.addWidget(self._btn_new)

        self._apply_toolbar_theme(toolbar, tb_lay)
        lay.addWidget(toolbar)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {T.get('border','#474747')};")
        lay.addWidget(sep)

        # ── Output area ───────────────────────────────────────────────────────
        self._output = TerminalOutput(theme=T)
        lay.addWidget(self._output, stretch=1)

        # ── Separator ─────────────────────────────────────────────────────────
        sep2 = QWidget()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background: {T.get('border','#474747')};")
        lay.addWidget(sep2)

        # ── Input bar ─────────────────────────────────────────────────────────
        self._input_bar = CommandInput(theme=T, cwd=self._cwd)
        self._input_bar.submitted.connect(self.run_command)
        lay.addWidget(self._input_bar)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+C"), self, self.kill_process)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear)

    def _apply_toolbar_theme(self, toolbar: QWidget, lay: QHBoxLayout) -> None:
        T   = self._theme
        bg  = T.get("panel_bg", T.get("sidebar", "#252526"))
        txt = T.get("muted", "#969696")
        btn = T.get("accent", "#007ACC")
        toolbar.setStyleSheet(f"""
            QWidget {{ background: {bg}; }}
            QToolButton {{
                background: transparent;
                color: {txt};
                border: none;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 9pt;
            }}
            QToolButton:hover {{ background: {T.get('tree_hover','#2A2D2E')}; color: {T.get('text','#CCC')}; }}
            QToolButton:disabled {{ color: {T.get('border','#474747')}; }}
            QComboBox {{
                background: {T.get('input_bg', bg)};
                color: {T.get('text','#CCC')};
                border: 1px solid {T.get('border','#474747')};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 9pt;
            }}
        """)

    # ── Welcome message ───────────────────────────────────────────────────────

    def _welcome(self) -> None:
        T    = self._theme
        name = T.get("name", "VynStudio")
        self._output.append_output(
            f"Vyn Integrated Terminal  ({sys.platform})\n"
            f"Working directory: {self._cwd}\n"
            f"Type a command and press Enter or click ▶ Run\n"
            f"{'─' * 60}\n",
            kind="info",
        )
        self._input_bar.set_cwd(self._cwd)

    # ── Public API ────────────────────────────────────────────────────────────

    def run_command(self, cmd: str) -> None:
        """Execute a shell command asynchronously."""
        if self._process and self._process.poll() is None:
            self._output.append_output(
                "⚠  A process is already running. Kill it first (Ctrl+C).\n",
                kind="error",
            )
            return

        # Echo command
        self._output.append_output(f"$ {cmd}\n", kind="cmd")
        self.command_started.emit(cmd)

        # Handle built-in commands
        if self._handle_builtin(cmd):
            return

        # Launch subprocess
        self._btn_kill.setEnabled(True)
        thread = threading.Thread(
            target=self._run_subprocess,
            args=(cmd,),
            daemon=True,
        )
        thread.start()

    def kill_process(self) -> None:
        """Kill the currently running process."""
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._output.append_output("\n^C  Process terminated.\n", kind="error")
            except Exception as e:
                self._output.append_output(f"\nFailed to kill: {e}\n", kind="error")
        self._btn_kill.setEnabled(False)

    def clear(self) -> None:
        """Clear terminal output."""
        self._output.clear_output()

    def set_cwd(self, path: str) -> None:
        """Change the working directory."""
        p = Path(path)
        if p.is_dir():
            self._cwd = str(p)
            self._input_bar.set_cwd(str(p))
            self._output.append_output(f"cd {path}\n", kind="info")

    def focus_input(self) -> None:
        self._input_bar.set_focus()

    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        self._output.update_theme(theme)
        self._input_bar.update_theme(theme)

    def new_terminal_btn(self):
        """Return the 'New Terminal' button so parent can connect a slot."""
        return self._btn_new

    # ── Builtins ─────────────────────────────────────────────────────────────

    def _handle_builtin(self, cmd: str) -> bool:
        """Handle shell built-in commands. Returns True if handled."""
        parts = cmd.strip().split()
        if not parts:
            return True

        # cd
        if parts[0] == "cd":
            target = " ".join(parts[1:]) if len(parts) > 1 else str(Path.home())
            try:
                new_cwd = str(Path(self._cwd) / target if not Path(target).is_absolute() else Path(target))
                new_cwd = str(Path(new_cwd).resolve())
                if Path(new_cwd).is_dir():
                    self._cwd = new_cwd
                    self._input_bar.set_cwd(new_cwd)
                    self._output.append_output(f"→ {new_cwd}\n", kind="info")
                else:
                    self._output.append_output(f"cd: {target}: No such directory\n", kind="error")
            except Exception as e:
                self._output.append_output(f"cd: {e}\n", kind="error")
            self._bridge.finished.emit(0)
            return True

        # clear / cls
        if parts[0] in ("clear", "cls"):
            self.clear()
            return True

        # pwd
        if parts[0] == "pwd":
            self._output.append_output(self._cwd + "\n", kind="stdout")
            self._bridge.finished.emit(0)
            return True

        # help
        if parts[0] == "help":
            self._output.append_output(
                "Available commands:\n"
                "  cd <dir>      — change directory\n"
                "  pwd           — print working directory\n"
                "  clear / cls   — clear terminal\n"
                "  help          — this help\n"
                "  Ctrl+C        — kill running process\n"
                "  ↑ / ↓         — navigate history\n"
                "  Tab           — autocomplete path\n"
                "\nVyn shortcuts:\n"
                "  python -m vyn.cli run <file.vyn>\n"
                "  python -m vyn.cli build <file.vyn>\n"
                "  python -m pytest\n"
                "  python -m vpm install\n",
                kind="info",
            )
            self._bridge.finished.emit(0)
            return True

        return False

    # ── Subprocess runner ─────────────────────────────────────────────────────

    def _run_subprocess(self, cmd: str) -> None:
        """Run cmd in a background thread, pipe output to the bridge."""
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["TERM"] = "dumb"

        shell = sys.platform == "win32"
        try:
            if sys.platform == "win32":
                self._process = subprocess.Popen(
                    cmd,
                    cwd=self._cwd,
                    env=env,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                self._process = subprocess.Popen(
                    shlex.split(cmd) if not shell else cmd,
                    cwd=self._cwd,
                    env=env,
                    shell=shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

            # Read stdout and stderr concurrently
            import select

            stdout_done = False
            stderr_done = False

            if sys.platform == "win32":
                # Windows: read in separate threads
                def _read_stream(stream, kind):
                    for line in stream:
                        self._bridge.output.emit(line, kind)
                    stream.close()

                t_out = threading.Thread(
                    target=_read_stream,
                    args=(self._process.stdout, "stdout"),
                    daemon=True,
                )
                t_err = threading.Thread(
                    target=_read_stream,
                    args=(self._process.stderr, "stderr"),
                    daemon=True,
                )
                t_out.start()
                t_err.start()
                self._process.wait()
                t_out.join(timeout=2)
                t_err.join(timeout=2)
            else:
                fds = {
                    self._process.stdout.fileno(): ("stdout", self._process.stdout),
                    self._process.stderr.fileno(): ("stderr", self._process.stderr),
                }
                open_fds = set(fds.keys())
                while open_fds:
                    try:
                        readable, _, _ = select.select(list(open_fds), [], [], 0.1)
                    except ValueError:
                        break
                    for fd in readable:
                        kind, stream = fds[fd]
                        line = stream.readline()
                        if line:
                            self._bridge.output.emit(line, kind)
                        else:
                            open_fds.discard(fd)
                    if self._process.poll() is not None and not readable:
                        # Drain remaining output
                        for fd in list(open_fds):
                            kind, stream = fds[fd]
                            remaining = stream.read()
                            if remaining:
                                self._bridge.output.emit(remaining, kind)
                        break

            code = self._process.wait()

        except FileNotFoundError:
            self._bridge.output.emit(
                f"Command not found: {cmd.split()[0] if cmd.split() else cmd}\n",
                "error",
            )
            code = 127
        except Exception as e:
            self._bridge.output.emit(f"Error: {e}\n", "error")
            code = 1
        finally:
            self._bridge.finished.emit(code)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_output(self, text: str, kind: str) -> None:
        self._output.append_output(text, kind)
        self.output_line.emit(text.rstrip())

    def _on_finished(self, code: int) -> None:
        self._btn_kill.setEnabled(False)
        color = "info" if code == 0 else "error"
        self._output.append_output(
            f"\n[Process exited with code {code}]\n",
            kind=color,
        )
        self.command_finished.emit(code)
        self._input_bar.set_focus()

    def _on_quick_cmd(self, text: str) -> None:
        if text == "Quick command…":
            return
        # Put it in the input bar for editing
        self._input_bar._input.setText(text)
        self._input_bar._input.end(False)
        self._input_bar.set_focus()
        # Reset combo
        self._quick.blockSignals(True)
        self._quick.setCurrentIndex(0)
        self._quick.blockSignals(False)
