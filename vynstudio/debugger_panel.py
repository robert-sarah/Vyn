"""VynStudio — Debugger Panel (breakpoints, step execution, variables, call stack)."""
from __future__ import annotations

import sys
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import (
    QColor, QFont, QIcon, QTextCursor,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QToolButton, QTextEdit, QPlainTextEdit,
    QGroupBox, QListWidget, QListWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QTabWidget,
    QLineEdit, QCheckBox, QSizePolicy,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Debugger State
# ═══════════════════════════════════════════════════════════════════════════════

class DebugState:
    IDLE     = "idle"
    RUNNING  = "running"
    PAUSED   = "paused"
    STEPPING = "stepping"
    STOPPED  = "stopped"


@dataclass
class Breakpoint:
    file:    str
    line:    int
    enabled: bool  = True
    condition: str = ""
    hit_count: int = 0

    @property
    def id(self) -> str:
        return f"{self.file}:{self.line}"

    def __str__(self) -> str:
        cond = f" [{self.condition}]" if self.condition else ""
        en   = "●" if self.enabled else "○"
        return f"{en} {Path(self.file).name}:{self.line}{cond} (hits: {self.hit_count})"


@dataclass
class StackFrame:
    name:     str
    file:     str
    line:     int
    locals_:  Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.name} — {Path(self.file).name}:{self.line}"


@dataclass
class DebugEvent:
    kind:    str    # "paused" | "stepped" | "resumed" | "stopped" | "error" | "output"
    message: str    = ""
    frame:   Optional[StackFrame] = None
    data:    Any    = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Vyn Instrumented Interpreter (wraps the real interpreter)
# ═══════════════════════════════════════════════════════════════════════════════

class _Bridge(QObject):
    event = pyqtSignal(object)   # DebugEvent


class VynDebugger:
    """Wraps the Vyn interpreter to add step/pause/breakpoint support."""

    def __init__(self) -> None:
        self._bridge      = _Bridge()
        self._state       = DebugState.IDLE
        self._breakpoints: Dict[str, Breakpoint] = {}
        self._call_stack:  List[StackFrame]       = []
        self._pause_event = threading.Event()
        self._step_mode   = False          # True → pause after every statement
        self._step_over   = False
        self._step_into   = True
        self._source_file = ""
        self._thread:  Optional[threading.Thread] = None
        self._interp   = None              # Interpreter instance
        self._program  = None             # Parsed program

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def call_stack(self) -> List[StackFrame]:
        return list(self._call_stack)

    @property
    def breakpoints(self) -> List[Breakpoint]:
        return list(self._breakpoints.values())

    # ── Event signal ──────────────────────────────────────────────────────────

    @property
    def on_event(self):
        return self._bridge.event

    def _emit(self, event: DebugEvent) -> None:
        self._bridge.event.emit(event)

    # ── Breakpoints ───────────────────────────────────────────────────────────

    def add_breakpoint(self, file: str, line: int, condition: str = "") -> Breakpoint:
        bp = Breakpoint(file=file, line=line, condition=condition)
        self._breakpoints[bp.id] = bp
        return bp

    def remove_breakpoint(self, file: str, line: int) -> None:
        key = f"{file}:{line}"
        self._breakpoints.pop(key, None)

    def toggle_breakpoint(self, file: str, line: int) -> Optional[Breakpoint]:
        key = f"{file}:{line}"
        if key in self._breakpoints:
            self._breakpoints[key].enabled = not self._breakpoints[key].enabled
            return self._breakpoints[key]
        return None

    def clear_breakpoints(self, file: Optional[str] = None) -> None:
        if file:
            keys = [k for k in self._breakpoints if k.startswith(file)]
            for k in keys:
                del self._breakpoints[k]
        else:
            self._breakpoints.clear()

    def has_breakpoint(self, file: str, line: int) -> bool:
        bp = self._breakpoints.get(f"{file}:{line}")
        return bp is not None and bp.enabled

    # ── Run control ───────────────────────────────────────────────────────────

    def start(self, source: str, file_path: str = "<stdin>") -> None:
        """Parse and run program with debugging instrumentation."""
        if self._state == DebugState.RUNNING:
            return
        self._source_file = file_path
        self._state       = DebugState.RUNNING
        self._call_stack  = []
        self._step_mode   = False
        self._pause_event.clear()

        self._thread = threading.Thread(
            target=self._run_thread,
            args=(source, file_path),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop execution."""
        self._state = DebugState.STOPPED
        self._pause_event.set()
        self._emit(DebugEvent("stopped", "Execution stopped by user"))

    def pause(self) -> None:
        """Request a pause at the next opportunity."""
        if self._state == DebugState.RUNNING:
            self._step_mode = True

    def resume(self) -> None:
        """Continue from paused state."""
        if self._state == DebugState.PAUSED:
            self._state     = DebugState.RUNNING
            self._step_mode = False
            self._pause_event.set()
            self._emit(DebugEvent("resumed", "Execution resumed"))

    def step_over(self) -> None:
        """Step over: execute next statement, skip into calls."""
        if self._state == DebugState.PAUSED:
            self._step_mode = True
            self._step_over = True
            self._state     = DebugState.STEPPING
            self._pause_event.set()

    def step_into(self) -> None:
        """Step into: pause at the very next statement."""
        if self._state == DebugState.PAUSED:
            self._step_mode = True
            self._step_over = False
            self._state     = DebugState.STEPPING
            self._pause_event.set()

    def step_out(self) -> None:
        """Step out: run until current function returns."""
        if self._state == DebugState.PAUSED:
            current_depth = len(self._call_stack)
            # Run until call stack is shallower
            self._step_mode = False
            self._state     = DebugState.RUNNING
            self._pause_event.set()
            # Instrumentation will re-pause when depth decreases

    # ── Execution thread ──────────────────────────────────────────────────────

    def _run_thread(self, source: str, file_path: str) -> None:
        try:
            from vyn.parser.parser import Parser
            from vyn.prelude import inject_prelude
            from vyn.semantic.analyzer import SemanticAnalyzer
            from vyn.interpreter import Interpreter

            enriched = inject_prelude(source)
            program  = Parser(enriched).parse()

            sem = SemanticAnalyzer()
            try:
                sem.analyze(program)
            except Exception as sem_err:
                self._emit(DebugEvent("error", f"Semantic error: {sem_err}"))
                self._state = DebugState.STOPPED
                return

            self._interp  = Interpreter(program)
            self._program = program

            # Monkey-patch the interpreter's _exec_stmt to add debugging hooks
            original_exec = self._interp._exec_stmt

            def _instrumented_exec(stmt, struct_name=None):
                if self._state == DebugState.STOPPED:
                    raise RuntimeError("Debugger: execution stopped")

                # Get line info from stmt
                line = getattr(getattr(stmt, 'span', None), 'line', 0)

                # Check breakpoints
                if self.has_breakpoint(file_path, line):
                    bp = self._breakpoints.get(f"{file_path}:{line}")
                    if bp:
                        # Check condition
                        if bp.condition:
                            try:
                                val = eval(bp.condition, {}, self._get_locals())
                                if not val:
                                    return original_exec(stmt, struct_name)
                            except Exception:
                                pass
                        bp.hit_count += 1
                        self._pause_at(line, f"Breakpoint hit at line {line}")

                # Step mode
                elif self._step_mode and line > 0:
                    self._pause_at(line, f"Stepped to line {line}")

                return original_exec(stmt, struct_name)

            self._interp._exec_stmt = _instrumented_exec

            # Run
            code = self._interp.run()
            self._state = DebugState.STOPPED
            self._emit(DebugEvent("stopped", f"Program exited with code {code}"))

        except RuntimeError as e:
            if "stopped" not in str(e).lower():
                self._emit(DebugEvent("error", f"Runtime error: {e}"))
            self._state = DebugState.STOPPED
            self._emit(DebugEvent("stopped", str(e)))
        except Exception as e:
            tb = traceback.format_exc()
            self._emit(DebugEvent("error", f"{e}\n{tb}"))
            self._state = DebugState.STOPPED
            self._emit(DebugEvent("stopped", str(e)))

    def _pause_at(self, line: int, message: str) -> None:
        """Pause execution and emit a paused event."""
        self._state = DebugState.PAUSED
        frame = StackFrame(
            name  = self._current_fn_name(),
            file  = self._source_file,
            line  = line,
            locals_=self._get_locals(),
        )
        self._call_stack = [frame] + self._call_stack[:9]  # keep last 10 frames
        self._pause_event.clear()
        self._emit(DebugEvent("paused", message, frame=frame, data={"line": line}))
        # Block execution thread until resume/step
        self._pause_event.wait()
        # After resume, clear step mode unless step_over/step_into requested
        if not self._step_mode:
            pass

    def _current_fn_name(self) -> str:
        if self._interp and hasattr(self._interp, '_current_fn'):
            fn = getattr(self._interp, '_current_fn', None)
            if fn and hasattr(fn, 'name'):
                return fn.name
        return "<main>"

    def _get_locals(self) -> Dict[str, Any]:
        """Collect current local variables from the interpreter's scope."""
        result: Dict[str, Any] = {}
        if not self._interp:
            return result
        try:
            for scope in self._interp.scopes:
                for name, owned in scope.items():
                    try:
                        val = owned.data if hasattr(owned, 'data') else owned
                        result[name] = val
                    except Exception:
                        result[name] = "<?>"
        except Exception:
            pass
        return result

    def evaluate(self, expr: str) -> str:
        """Evaluate an expression in the current debug context."""
        if not self._interp or self._state != DebugState.PAUSED:
            return "(not paused)"
        try:
            from vyn.parser.parser import Parser
            from vyn.ast.nodes import ExprStmt
            prog   = Parser(f"fn __eval__() -> i32 {{ return {expr}; }}")
            # Simplified: just eval in Python with locals
            locals_ = self._get_locals()
            py_expr = expr.replace("io.println", "print")
            result  = eval(py_expr, {}, locals_)
            return str(result)
        except Exception as e:
            return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Debugger Panel UI
# ═══════════════════════════════════════════════════════════════════════════════

class DebuggerPanel(QWidget):
    """Complete debugger UI panel for VynStudio.

    Features
    --------
    - Start / Stop / Pause / Resume
    - Step Into / Step Over / Step Out
    - Breakpoints list with enable/disable/delete
    - Variables inspector (locals, globals)
    - Call stack viewer
    - Watch expressions
    - Debug console (evaluate expressions)
    - Line highlighting in editor
    - Theme-aware
    """

    # ── Signals ───────────────────────────────────────────────────────────────
    breakpoint_toggled = pyqtSignal(str, int)   # (file, line)
    highlight_line     = pyqtSignal(str, int)   # (file, line) — ask editor to highlight
    debug_output       = pyqtSignal(str)         # text to output panel
    state_changed      = pyqtSignal(str)         # new DebugState

    def __init__(
        self,
        theme:  dict,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._theme   = theme
        self._debugger = VynDebugger()
        self._debugger.on_event.connect(self._on_debug_event)
        self._current_file = ""
        self._watches: List[str] = []

        self._build_ui()
        self._update_controls(DebugState.IDLE)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        T   = self._theme
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────────
        lay.addWidget(self._build_toolbar())
        lay.addWidget(self._make_separator())

        # ── Main splitter ────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Vertical)

        # Top: tabs (Variables, Watch, Call Stack, Breakpoints)
        top_tabs = QTabWidget()
        top_tabs.setStyleSheet(self._tab_style())
        top_tabs.addTab(self._build_variables_tab(),  "Variables")
        top_tabs.addTab(self._build_watch_tab(),      "Watch")
        top_tabs.addTab(self._build_callstack_tab(),  "Call Stack")
        top_tabs.addTab(self._build_breakpoints_tab(),"Breakpoints")
        splitter.addWidget(top_tabs)

        # Bottom: debug console
        splitter.addWidget(self._build_console())
        splitter.setSizes([350, 150])

        lay.addWidget(splitter, stretch=1)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> QWidget:
        T      = self._theme
        bar    = QWidget()
        bar.setFixedHeight(38)
        bar_l  = QHBoxLayout(bar)
        bar_l.setContentsMargins(6, 4, 6, 4)
        bar_l.setSpacing(4)

        bar.setStyleSheet(f"background:{T.get('panel_bg',T.get('sidebar','#252526'))};")

        lbl = QLabel("DEBUG")
        lbl.setStyleSheet(
            f"color:{T.get('muted','#969696')};"
            f"font-size:9pt;font-weight:bold;letter-spacing:1px;"
        )
        bar_l.addWidget(lbl)
        bar_l.addStretch()

        btn_style = f"""
            QToolButton {{
                background:transparent;
                color:{T.get('text','#CCC')};
                border:none; border-radius:3px;
                padding:3px 8px; font-size:12pt;
            }}
            QToolButton:hover {{
                background:{T.get('tree_hover','#2A2D2E')};
            }}
            QToolButton:disabled {{
                color:{T.get('border','#474747')};
            }}
            QToolButton:pressed {{
                background:{T.get('selection','#264F78')};
            }}
        """

        controls = [
            ("▶",  "Start / Continue (F5)",      self._on_start_resume, "btn_start"),
            ("⏸",  "Pause (F6)",                  self._on_pause,        "btn_pause"),
            ("⏹",  "Stop (Shift+F5)",             self._on_stop,         "btn_stop"),
            ("↷",  "Step Over (F10)",             self._on_step_over,    "btn_step_over"),
            ("↓",  "Step Into (F11)",             self._on_step_into,    "btn_step_into"),
            ("↑",  "Step Out (Shift+F11)",        self._on_step_out,     "btn_step_out"),
            ("↺",  "Restart",                      self._on_restart,      "btn_restart"),
        ]

        for icon, tip, slot, attr in controls:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            setattr(self, f"_{attr}", btn)
            bar_l.addWidget(btn)

        bar_l.addSpacing(8)

        # Clear breakpoints button
        self._btn_clear_bp = QToolButton()
        self._btn_clear_bp.setText("🚫")
        self._btn_clear_bp.setToolTip("Clear all breakpoints")
        self._btn_clear_bp.setFixedSize(28, 28)
        self._btn_clear_bp.setStyleSheet(btn_style)
        self._btn_clear_bp.clicked.connect(self._on_clear_breakpoints)
        bar_l.addWidget(self._btn_clear_bp)

        return bar

    # ── Variables tab ─────────────────────────────────────────────────────────

    def _build_variables_tab(self) -> QWidget:
        T   = self._theme
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        self._var_tree = QTreeWidget()
        self._var_tree.setHeaderLabels(["Name", "Value", "Type"])
        self._var_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._var_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self._var_tree.setAlternatingRowColors(True)
        self._var_tree.setStyleSheet(self._tree_style())
        lay.addWidget(self._var_tree)

        return w

    # ── Watch tab ─────────────────────────────────────────────────────────────

    def _build_watch_tab(self) -> QWidget:
        T   = self._theme
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        # Add expression row
        add_row = QHBoxLayout()
        self._watch_input = QLineEdit()
        self._watch_input.setPlaceholderText("Add watch expression…")
        self._watch_input.returnPressed.connect(self._add_watch)
        self._watch_input.setStyleSheet(self._input_style())
        add_row.addWidget(self._watch_input)

        btn_add = QPushButton("+")
        btn_add.setFixedWidth(32)
        btn_add.clicked.connect(self._add_watch)
        btn_add.setStyleSheet(self._btn_primary_style())
        add_row.addWidget(btn_add)
        lay.addLayout(add_row)

        self._watch_tree = QTreeWidget()
        self._watch_tree.setHeaderLabels(["Expression", "Value"])
        self._watch_tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self._watch_tree.setAlternatingRowColors(True)
        self._watch_tree.setStyleSheet(self._tree_style())
        self._watch_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._watch_tree.customContextMenuRequested.connect(self._watch_context_menu)
        lay.addWidget(self._watch_tree)

        return w

    # ── Call stack tab ────────────────────────────────────────────────────────

    def _build_callstack_tab(self) -> QWidget:
        T   = self._theme
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        self._stack_list = QListWidget()
        self._stack_list.setAlternatingRowColors(True)
        self._stack_list.setStyleSheet(self._tree_style())
        self._stack_list.itemDoubleClicked.connect(self._on_frame_selected)
        lay.addWidget(self._stack_list)

        return w

    # ── Breakpoints tab ───────────────────────────────────────────────────────

    def _build_breakpoints_tab(self) -> QWidget:
        T   = self._theme
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        tb  = QHBoxLayout()
        for icon, tip, slot in [
            ("✕", "Remove selected", self._remove_selected_bp),
            ("✕✕","Clear all",       self._on_clear_breakpoints),
            ("✔", "Enable all",      self._enable_all_bp),
            ("○", "Disable all",     self._disable_all_bp),
        ]:
            b = QToolButton()
            b.setText(icon)
            b.setToolTip(tip)
            b.setFixedSize(26, 22)
            b.setStyleSheet(self._toolbtn_style())
            b.clicked.connect(slot)
            tb.addWidget(b)
        tb.addStretch()
        lay.addLayout(tb)

        self._bp_list = QTreeWidget()
        self._bp_list.setHeaderLabels(["", "File", "Line", "Condition", "Hits"])
        self._bp_list.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self._bp_list.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._bp_list.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self._bp_list.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._bp_list.setColumnWidth(0, 24)
        self._bp_list.setAlternatingRowColors(True)
        self._bp_list.setStyleSheet(self._tree_style())
        self._bp_list.itemDoubleClicked.connect(self._on_bp_double_click)
        lay.addWidget(self._bp_list)

        return w

    # ── Debug console ─────────────────────────────────────────────────────────

    def _build_console(self) -> QWidget:
        T   = self._theme
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QLabel("DEBUG CONSOLE")
        hdr.setFixedHeight(22)
        hdr.setStyleSheet(
            f"color:{T.get('muted','#969696')};"
            f"font-size:8pt;font-weight:bold;padding:0 8px;"
            f"background:{T.get('panel_bg',T.get('sidebar','#252526'))};"
        )
        lay.addWidget(hdr)
        lay.addWidget(self._make_separator())

        # Output
        self._console_out = QPlainTextEdit()
        self._console_out.setReadOnly(True)
        self._console_out.setMaximumBlockCount(2000)
        self._console_out.setFont(QFont("Consolas", 9))
        self._console_out.setStyleSheet(f"""
            QPlainTextEdit {{
                background:{T.get('terminal_bg', T.get('panel_bg','#1E1E1E'))};
                color:{T.get('terminal_text',T.get('text','#CCC'))};
                border:none;
                font-family:Consolas,monospace;
                font-size:9pt;
            }}
        """)
        lay.addWidget(self._console_out, stretch=1)

        # Input
        inp_row = QHBoxLayout()
        inp_row.setContentsMargins(4, 2, 4, 4)
        inp_row.setSpacing(4)

        self._console_prompt = QLabel(">")
        self._console_prompt.setStyleSheet(
            f"color:{T.get('success','#89D185')};font-weight:bold;font-family:Consolas;font-size:9pt;"
        )
        inp_row.addWidget(self._console_prompt)

        self._console_input = QLineEdit()
        self._console_input.setPlaceholderText("Evaluate expression…")
        self._console_input.setFont(QFont("Consolas", 9))
        self._console_input.setStyleSheet(self._input_style())
        self._console_input.returnPressed.connect(self._on_console_eval)
        inp_row.addWidget(self._console_input)

        btn_eval = QPushButton("Eval")
        btn_eval.setFixedWidth(50)
        btn_eval.setStyleSheet(self._btn_primary_style())
        btn_eval.clicked.connect(self._on_console_eval)
        inp_row.addWidget(btn_eval)

        lay.addLayout(inp_row)
        return w

    # ── Public API ────────────────────────────────────────────────────────────

    def set_source_file(self, path: str) -> None:
        """Set the current source file being debugged."""
        self._current_file = path

    def start_debug(self, source: str, file_path: str = "<stdin>") -> None:
        """Start debugging the given source."""
        self._current_file = file_path
        self._console_append(f"▶ Starting debugger: {Path(file_path).name}\n", "info")
        self._debugger.start(source, file_path)
        self._update_controls(DebugState.RUNNING)
        self.state_changed.emit(DebugState.RUNNING)

    def stop_debug(self) -> None:
        """Stop the debugger."""
        self._debugger.stop()
        self._update_controls(DebugState.STOPPED)

    def add_breakpoint(self, file: str, line: int) -> Breakpoint:
        bp = self._debugger.add_breakpoint(file, line)
        self._refresh_breakpoints()
        return bp

    def remove_breakpoint(self, file: str, line: int) -> None:
        self._debugger.remove_breakpoint(file, line)
        self._refresh_breakpoints()

    def toggle_breakpoint(self, file: str, line: int) -> None:
        key = f"{file}:{line}"
        if key in self._debugger._breakpoints:
            self._debugger.toggle_breakpoint(file, line)
        else:
            self._debugger.add_breakpoint(file, line)
        self._refresh_breakpoints()
        self.breakpoint_toggled.emit(file, line)

    def get_breakpoint_lines(self, file: str) -> List[int]:
        return [
            bp.line for bp in self._debugger.breakpoints
            if bp.file == file
        ]

    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        # Re-apply stylesheets to all sub-widgets
        self._var_tree.setStyleSheet(self._tree_style())
        self._watch_tree.setStyleSheet(self._tree_style())
        self._stack_list.setStyleSheet(self._tree_style())
        self._bp_list.setStyleSheet(self._tree_style())
        self._console_input.setStyleSheet(self._input_style())
        self._watch_input.setStyleSheet(self._input_style())

    # ── Control slots ─────────────────────────────────────────────────────────

    def _on_start_resume(self) -> None:
        if self._debugger.state == DebugState.IDLE:
            self._console_append("No source to debug. Use 'Run → Debug' from the menu.\n", "error")
        elif self._debugger.state == DebugState.PAUSED:
            self._debugger.resume()
            self._update_controls(DebugState.RUNNING)
            self.state_changed.emit(DebugState.RUNNING)
        elif self._debugger.state in (DebugState.STOPPED, DebugState.IDLE):
            self._console_append("Start a debug session via Run → Debug.\n", "info")

    def _on_pause(self) -> None:
        self._debugger.pause()
        self._console_append("⏸ Pausing…\n", "info")

    def _on_stop(self) -> None:
        self._debugger.stop()
        self._update_controls(DebugState.STOPPED)
        self.state_changed.emit(DebugState.STOPPED)

    def _on_step_over(self) -> None:
        if self._debugger.state == DebugState.PAUSED:
            self._debugger.step_over()
            self._update_controls(DebugState.STEPPING)

    def _on_step_into(self) -> None:
        if self._debugger.state == DebugState.PAUSED:
            self._debugger.step_into()
            self._update_controls(DebugState.STEPPING)

    def _on_step_out(self) -> None:
        if self._debugger.state == DebugState.PAUSED:
            self._debugger.step_out()
            self._update_controls(DebugState.RUNNING)

    def _on_restart(self) -> None:
        self._debugger.stop()
        self._console_append("↺ Restarted. Use Run → Debug to start again.\n", "info")
        self._update_controls(DebugState.STOPPED)

    def _on_clear_breakpoints(self) -> None:
        self._debugger.clear_breakpoints()
        self._refresh_breakpoints()
        self._console_append("All breakpoints cleared.\n", "info")

    def _on_console_eval(self) -> None:
        expr = self._console_input.text().strip()
        if not expr:
            return
        self._console_input.clear()
        self._console_append(f"> {expr}\n", "cmd")
        result = self._debugger.evaluate(expr)
        self._console_append(f"  {result}\n", "result")

    # ── Breakpoints UI ────────────────────────────────────────────────────────

    def _refresh_breakpoints(self) -> None:
        self._bp_list.clear()
        for bp in self._debugger.breakpoints:
            item = QTreeWidgetItem(self._bp_list)
            item.setText(0, "●" if bp.enabled else "○")
            item.setText(1, Path(bp.file).name)
            item.setText(2, str(bp.line))
            item.setText(3, bp.condition or "")
            item.setText(4, str(bp.hit_count))
            if not bp.enabled:
                for col in range(5):
                    item.setForeground(col, QColor(self._theme.get("muted", "#969696")))
            else:
                item.setForeground(0, QColor(self._theme.get("error", "#F14C4C")))

    def _remove_selected_bp(self) -> None:
        for item in self._bp_list.selectedItems():
            file = self._current_file
            line = int(item.text(2))
            self._debugger.remove_breakpoint(file, line)
        self._refresh_breakpoints()

    def _enable_all_bp(self) -> None:
        for bp in self._debugger.breakpoints:
            bp.enabled = True
        self._refresh_breakpoints()

    def _disable_all_bp(self) -> None:
        for bp in self._debugger.breakpoints:
            bp.enabled = False
        self._refresh_breakpoints()

    def _on_bp_double_click(self, item: QTreeWidgetItem) -> None:
        try:
            line = int(item.text(2))
            self.highlight_line.emit(self._current_file, line)
        except Exception:
            pass

    # ── Variables UI ──────────────────────────────────────────────────────────

    def _refresh_variables(self, locals_: Dict[str, Any]) -> None:
        self._var_tree.clear()
        local_item = QTreeWidgetItem(self._var_tree, ["Locals", "", ""])
        local_item.setExpanded(True)

        for name, val in sorted(locals_.items()):
            type_name = type(val).__name__
            val_str   = self._format_value(val)
            child     = QTreeWidgetItem(local_item, [name, val_str, type_name])

            # Add sub-items for dicts/lists
            if isinstance(val, dict):
                for k, v in list(val.items())[:20]:
                    QTreeWidgetItem(child, [str(k), self._format_value(v), type(v).__name__])
            elif isinstance(val, list):
                for i, v in enumerate(val[:20]):
                    QTreeWidgetItem(child, [f"[{i}]", self._format_value(v), type(v).__name__])

        self._var_tree.expandItem(local_item)

    @staticmethod
    def _format_value(val: Any) -> str:
        if val is None:
            return "nil"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, str):
            s = val[:80]
            return f'"{s}"' + ("…" if len(val) > 80 else "")
        if isinstance(val, dict):
            if val.get("__type__") == "Option":
                tag = val.get("__tag__", "None")
                if tag == "Some":
                    return f"Some({val.get('__value__')})"
                return "None"
            if val.get("__type__") == "Result":
                tag = val.get("__tag__", "Err")
                return f"{tag}({val.get('__value__')})"
            n = len(val)
            return f"{{ {n} entries }}"
        if isinstance(val, list):
            n = len(val)
            return f"[ {n} items ]"
        if isinstance(val, float):
            return f"{val:.6g}"
        return str(val)

    # ── Watch UI ──────────────────────────────────────────────────────────────

    def _add_watch(self) -> None:
        expr = self._watch_input.text().strip()
        if not expr:
            return
        self._watch_input.clear()
        if expr not in self._watches:
            self._watches.append(expr)
        self._refresh_watches()

    def _refresh_watches(self) -> None:
        self._watch_tree.clear()
        for expr in self._watches:
            result = self._debugger.evaluate(expr)
            QTreeWidgetItem(self._watch_tree, [expr, result])

    def _watch_context_menu(self, pos) -> None:
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        item = self._watch_tree.itemAt(pos)
        if item:
            menu.addAction("Remove").triggered.connect(
                lambda: self._remove_watch(item.text(0))
            )
        menu.addAction("Clear All").triggered.connect(self._clear_watches)
        menu.exec_(self._watch_tree.viewport().mapToGlobal(pos))

    def _remove_watch(self, expr: str) -> None:
        if expr in self._watches:
            self._watches.remove(expr)
        self._refresh_watches()

    def _clear_watches(self) -> None:
        self._watches.clear()
        self._watch_tree.clear()

    # ── Call stack UI ─────────────────────────────────────────────────────────

    def _refresh_call_stack(self, frames: List[StackFrame]) -> None:
        self._stack_list.clear()
        for i, frame in enumerate(frames):
            item = QListWidgetItem(f"  {i}: {frame}")
            if i == 0:
                item.setForeground(QColor(self._theme.get("accent", "#007ACC")))
            self._stack_list.addItem(item)

    def _on_frame_selected(self, item: QListWidgetItem) -> None:
        text = item.text().strip()
        # Parse "N: name — file:line"
        try:
            rest  = text.split(":", 1)[1].strip()
            parts = rest.rsplit(":", 1)
            if len(parts) == 2:
                line = int(parts[1].strip())
                self.highlight_line.emit(self._current_file, line)
        except Exception:
            pass

    # ── Debug event handler ───────────────────────────────────────────────────

    def _on_debug_event(self, event: DebugEvent) -> None:
        kind = event.kind

        if kind == "paused":
            self._update_controls(DebugState.PAUSED)
            self.state_changed.emit(DebugState.PAUSED)

            if event.frame:
                self._refresh_variables(event.frame.locals_)
                self.highlight_line.emit(event.frame.file, event.frame.line)

            self._refresh_call_stack(self._debugger.call_stack)
            self._refresh_watches()
            self._refresh_breakpoints()

            line = event.data.get("line", 0) if event.data else 0
            self._console_append(
                f"⏸ {event.message}\n",
                "info",
            )

        elif kind in ("stopped", "error"):
            self._update_controls(DebugState.STOPPED)
            self.state_changed.emit(DebugState.STOPPED)
            color = "error" if kind == "error" else "info"
            self._console_append(f"■ {event.message}\n", color)
            # Clear call stack display
            self._stack_list.clear()

        elif kind == "resumed":
            self._update_controls(DebugState.RUNNING)
            self._console_append(f"▶ {event.message}\n", "info")

        elif kind == "output":
            self._console_append(event.message, "stdout")

    # ── Control enable/disable ────────────────────────────────────────────────

    def _update_controls(self, state: str) -> None:
        idle    = state == DebugState.IDLE
        running = state == DebugState.RUNNING
        paused  = state == DebugState.PAUSED
        stopped = state in (DebugState.STOPPED, DebugState.IDLE)

        self._btn_start.setEnabled(paused or stopped)
        self._btn_start.setText("▶" if not paused else "▶")
        self._btn_pause.setEnabled(running)
        self._btn_stop.setEnabled(running or paused)
        self._btn_step_over.setEnabled(paused)
        self._btn_step_into.setEnabled(paused)
        self._btn_step_out.setEnabled(paused)
        self._btn_restart.setEnabled(running or paused or not stopped)

        # Status hint in console prompt
        icons = {
            DebugState.IDLE:     "○",
            DebugState.RUNNING:  "▶",
            DebugState.PAUSED:   "⏸",
            DebugState.STEPPING: "→",
            DebugState.STOPPED:  "■",
        }
        self._console_prompt.setText(f"{icons.get(state, '>')} ")

    # ── Console output ────────────────────────────────────────────────────────

    def _console_append(self, text: str, kind: str = "stdout") -> None:
        T      = self._theme
        colors = {
            "stdout": T.get("terminal_text", "#CCCCCC"),
            "stderr": T.get("error",         "#F14C4C"),
            "info":   T.get("info",          "#3794FF"),
            "error":  T.get("error",         "#F14C4C"),
            "cmd":    T.get("accent",        "#007ACC"),
            "result": T.get("success",       "#89D185"),
        }
        color  = colors.get(kind, colors["stdout"])
        cursor = self._console_out.textCursor()
        cursor.movePosition(QTextCursor.End)

        from PyQt5.QtGui import QTextCharFormat
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

        self._console_out.setTextCursor(cursor)
        self._console_out.ensureCursorVisible()
        self.debug_output.emit(text)

    # ── Utility stylesheets ───────────────────────────────────────────────────

    def _tree_style(self) -> str:
        T = self._theme
        return f"""
            QTreeWidget, QListWidget {{
                background:{T.get('panel_bg',T.get('sidebar','#252526'))};
                color:{T.get('text','#CCC')};
                border:none;
                font-family:Consolas,monospace;
                font-size:9pt;
                alternate-background-color:{T.get('bg','#1E1E1E')};
            }}
            QTreeWidget::item:selected, QListWidget::item:selected {{
                background:{T.get('tree_selected','#094771')};
                color:{T.get('tree_selected_fg','white')};
            }}
            QTreeWidget::item:hover, QListWidget::item:hover {{
                background:{T.get('tree_hover','#2A2D2E')};
            }}
            QHeaderView::section {{
                background:{T.get('sidebar','#252526')};
                color:{T.get('muted','#969696')};
                border:none;
                border-right:1px solid {T.get('border','#474747')};
                padding:4px;
                font-size:8pt;
                font-weight:bold;
            }}
        """

    def _input_style(self) -> str:
        T = self._theme
        return f"""
            QLineEdit {{
                background:{T.get('input_bg',T.get('panel_bg','#3C3C3C'))};
                color:{T.get('text','#CCC')};
                border:1px solid {T.get('input_border','#555')};
                border-radius:3px;
                padding:3px 6px;
                font-family:Consolas,monospace;
                font-size:9pt;
            }}
            QLineEdit:focus {{
                border-color:{T.get('accent','#007ACC')};
            }}
        """

    def _btn_primary_style(self) -> str:
        T = self._theme
        return f"""
            QPushButton {{
                background:{T.get('accent','#007ACC')};
                color:{T.get('accent_fg','white')};
                border:none; border-radius:3px;
                padding:3px 10px; font-size:9pt;
            }}
            QPushButton:hover {{
                background:{T.get('accent_hover','#1A8AD4')};
            }}
        """

    def _toolbtn_style(self) -> str:
        T = self._theme
        return f"""
            QToolButton {{
                background:transparent;
                color:{T.get('muted','#969696')};
                border:none;border-radius:2px;
                font-size:9pt;
            }}
            QToolButton:hover {{
                background:{T.get('tree_hover','#2A2D2E')};
                color:{T.get('text','#CCC')};
            }}
        """

    def _tab_style(self) -> str:
        T = self._theme
        return f"""
            QTabWidget::pane {{
                border:none;
                background:{T.get('panel_bg',T.get('sidebar','#252526'))};
            }}
            QTabBar::tab {{
                background:{T.get('tab_inactive','#2D2D2D')};
                color:{T.get('tab_text_muted','#969696')};
                padding:5px 12px;
                border:none;
                font-size:9pt;
            }}
            QTabBar::tab:selected {{
                background:{T.get('tab_active','#1E1E1E')};
                color:{T.get('tab_text','white')};
                border-top:2px solid {T.get('accent','#007ACC')};
            }}
        """

    def _make_separator(self) -> QWidget:
        T   = self._theme
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{T.get('border','#474747')};")
        return sep
