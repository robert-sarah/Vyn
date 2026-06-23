"""VynStudio — professional IDE (VS Code Light theme, English)."""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QKeySequence, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTextEdit, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QAction, QStatusBar, QLabel, QMessageBox, QTabWidget,
    QFrame, QPushButton, QListWidget, QListWidgetItem, QStackedWidget,
    QPlainTextEdit, QToolButton,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vynstudio.editor import VynCodeEditor
from vynstudio.highlighter import VynHighlighter
from vynstudio.theme import LIGHT as T
from vyn.diagnostics import analyze_source

T = T  # theme alias
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"


def _needs_gui_thread(src: str) -> bool:
    return any(k in src for k in ("import std.gui", "gui.run(", "gui.window(", "gui.button("))


class RunWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, src: str):
        super().__init__()
        self.src = src
        self._proc: subprocess.Popen | None = None
        self._tmp: Path | None = None

    def run(self):
        try:
            self._tmp = Path(tempfile.mkstemp(suffix=".vyn", dir=tempfile.gettempdir())[1])
            self._tmp.write_text(self.src, encoding="utf-8")
            self._proc = subprocess.Popen(
                [sys.executable, "-m", "vyn.cli", "run", str(self._tmp)],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            out, _ = self._proc.communicate()
            ok = self._proc.returncode == 0
            self.done.emit(ok, out or "")
        except Exception as e:
            self.done.emit(False, f"ERROR: {e}\n")
        finally:
            if self._tmp and self._tmp.exists():
                try:
                    self._tmp.unlink()
                except OSError:
                    pass

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()


class BuildWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, src: str, mode: str):
        super().__init__()
        self.src, self.mode = src, mode

    def run(self):
        try:
            if self.mode == "parse":
                from vyn.parser import Parser
                p = Parser(self.src).parse()
                names = [f.name for f in p.functions]
                self.done.emit(True, f"Parse OK\nFunctions: {names}\nStructs: {[s.name for s in p.structs]}\n")
            elif self.mode == "ir":
                from vyn.codegen import compile_to_ir
                ir, _ = compile_to_ir(self.src)
                self.done.emit(True, ir[:3000] + ("\n..." if len(ir) > 3000 else "\n"))
            else:
                tmp = ROOT / "examples" / "_studio_build.vyn"
                tmp.write_text(self.src, encoding="utf-8")
                r = subprocess.run(
                    [sys.executable, "-m", "vyn.cli", "build", str(tmp)],
                    capture_output=True, text=True, cwd=str(ROOT),
                )
                self.done.emit(r.returncode == 0, r.stdout + r.stderr)
        except Exception as e:
            self.done.emit(False, f"ERROR: {e}\n")


class EditorTab(QWidget):
    def __init__(self, path=None):
        super().__init__()
        self.path = path
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.breadcrumb = QLabel("")
        self.breadcrumb.setStyleSheet(
            f"background:{T['breadcrumb']};color:{T['muted']};padding:4px 12px;"
            f"border-bottom:1px solid {T['border']};font-size:9pt;"
        )
        lay.addWidget(self.breadcrumb)

        self.editor = VynCodeEditor(light=True)
        self.highlighter = VynHighlighter(self.editor.document(), light=True)
        self.editor.cursorPositionChanged.connect(self._cursor)
        self.on_cursor = None
        self.on_dirty = None
        lay.addWidget(self.editor)

        if path and os.path.exists(path):
            self.editor.setPlainText(Path(path).read_text(encoding="utf-8"))
        self._saved_snapshot = self.source()
        self.editor.textChanged.connect(self._on_text_changed)
        self._update_breadcrumb()

    def _on_text_changed(self):
        if self.on_dirty:
            self.on_dirty(self)

    def is_dirty(self) -> bool:
        return self.source() != self._saved_snapshot

    def mark_saved(self):
        self._saved_snapshot = self.source()
        if self.on_dirty:
            self.on_dirty(self)

    def display_name(self) -> str:
        if self.path:
            return Path(self.path).name
        return "untitled.vyn"

    def _update_breadcrumb(self):
        if self.path:
            self.breadcrumb.setText(str(Path(self.path)).replace("\\", "  ›  "))
        else:
            self.breadcrumb.setText("untitled.vyn")

    def _cursor(self):
        if self.on_cursor:
            c = self.editor.textCursor()
            self.on_cursor(c.blockNumber() + 1, c.columnNumber() + 1)

    def source(self):
        return self.editor.toPlainText()

    def save(self):
        if self.path:
            Path(self.path).write_text(self.source(), encoding="utf-8")
            self.mark_saved()
            return True
        return False


class VynStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VynStudio")
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.resize(1480, 920)
        self._run_worker: RunWorker | None = None
        self._build_worker: BuildWorker | None = None
        self._build_ui()
        self._diag_timer = QTimer(self)
        self._diag_timer.timeout.connect(self._diagnostics)
        self._diag_timer.start(1200)
        p = ROOT / "examples" / "profile.vyn"
        if p.exists():
            self._open(str(p))

    def _build_ui(self):
        self.setStyleSheet(f"QMainWindow{{background:{T['bg']};}}")
        cw = QWidget()
        self.setCentralWidget(cw)
        root = QHBoxLayout(cw)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Activity bar
        act = QFrame()
        act.setFixedWidth(48)
        act.setStyleSheet(f"background:{T['activity']};")
        al = QVBoxLayout(act)
        al.setAlignment(Qt.AlignTop)
        al.setSpacing(4)
        al.setContentsMargins(4, 8, 4, 4)

        if LOGO_PATH.exists():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(QPixmap(str(LOGO_PATH)).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_lbl.setToolTip("VynStudio")
            logo_lbl.setStyleSheet("background:transparent;padding:4px;")
            al.addWidget(logo_lbl, alignment=Qt.AlignHCenter)

        for icon, tip, slot in [
            ("EX", "Explorer", lambda: self._side.setCurrentIndex(0)),
            ("SR", "Search", lambda: self._side.setCurrentIndex(1)),
            ("PK", "Packages", lambda: self._side.setCurrentIndex(2)),
            ("AI", "AI / ML", lambda: self._side.setCurrentIndex(3)),
        ]:
            b = QToolButton()
            b.setText(icon)
            b.setFixedSize(40, 40)
            b.setToolTip(tip)
            b.setStyleSheet(
                "QToolButton{background:transparent;color:#CCC;font-size:10px;font-weight:bold;border:none;border-radius:4px;}"
                "QToolButton:hover{background:#505050;}"
            )
            b.clicked.connect(slot)
            al.addWidget(b, alignment=Qt.AlignHCenter)

        run_btn = QToolButton()
        run_btn.setText("RUN")
        run_btn.setFixedSize(40, 40)
        run_btn.setToolTip("Run (F5)")
        run_btn.setStyleSheet(
            f"QToolButton{{background:{T['accent']};color:white;font-size:8px;font-weight:bold;border:none;border-radius:4px;}}"
            f"QToolButton:hover{{background:{T['accent_hover']};}}"
        )
        run_btn.clicked.connect(self._run)
        al.addWidget(run_btn, alignment=Qt.AlignHCenter)
        al.addStretch()
        root.addWidget(act)

        body = QSplitter(Qt.Horizontal)

        # Sidebar
        side = QFrame()
        side.setMinimumWidth(220)
        side.setMaximumWidth(320)
        side.setStyleSheet(f"background:{T['sidebar']};border-right:1px solid {T['border']};")
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        self._side = QStackedWidget()

        # Explorer
        exp = QWidget()
        el = QVBoxLayout(exp)
        el.setContentsMargins(8, 8, 8, 8)
        el.addWidget(self._section_title("EXPLORER"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(
            f"QTreeWidget{{background:{T['sidebar']};color:{T['text']};border:none;font-size:10pt;}}"
            f"QTreeWidget::item{{padding:3px;}}"
            f"QTreeWidget::item:selected{{background:{T['tree_selected']};color:white;}}"
        )
        self._fill_tree()
        self.tree.itemDoubleClicked.connect(self._tree_open)
        el.addWidget(self.tree)
        self._side.addWidget(exp)

        # Search
        srch = QWidget()
        srl = QVBoxLayout(srch)
        srl.setContentsMargins(8, 8, 8, 8)
        srl.addWidget(self._section_title("SEARCH"))
        self.search_in = QPlainTextEdit()
        self.search_in.setMaximumHeight(32)
        self.search_in.setPlaceholderText("Search in files...")
        self.search_in.setStyleSheet(
            f"background:{T['bg']};color:{T['text']};border:1px solid {T['border']};border-radius:3px;"
        )
        srl.addWidget(self.search_in)
        self._side.addWidget(srch)

        # Packages
        pkg = QWidget()
        pkg_l = QVBoxLayout(pkg)
        pkg_l.setContentsMargins(8, 8, 8, 8)
        pkg_l.addWidget(self._section_title("VPM PACKAGES"))
        pkg_help = QLabel("Reusable libraries (like npm/cargo).\nDouble-click to import.")
        pkg_help.setWordWrap(True)
        pkg_help.setStyleSheet(f"color:{T['muted']};font-size:9pt;padding-bottom:6px;")
        pkg_l.addWidget(pkg_help)
        self.pkg_list = QListWidget()
        self.pkg_list.setStyleSheet(
            f"QListWidget{{background:{T['sidebar']};color:{T['text']};border:none;}}"
            f"QListWidget::item:selected{{background:{T['tree_selected']};color:white;}}"
        )
        for name, desc in [
            ("serde", "JSON serialize / deserialize"),
            ("collections", "Stack, Queue data structures"),
            ("neural", "ReLU, sigmoid activations"),
            ("ai", "Train & save neural networks"),
            ("async", "defer_ms, yield_now"),
            ("web", "HTML page helpers"),
        ]:
            self.pkg_list.addItem(f"{name}  —  {desc}")
        self.pkg_list.itemDoubleClicked.connect(self._insert_package)
        pkg_l.addWidget(self.pkg_list)
        self._side.addWidget(pkg)

        # AI / GGUF panel
        ai_w = QWidget()
        ai_l = QVBoxLayout(ai_w)
        ai_l.setContentsMargins(8, 8, 8, 8)
        ai_l.addWidget(self._section_title("OFFLINE AI (GGUF)"))
        self._ai_status = QLabel("No model loaded")
        self._ai_status.setWordWrap(True)
        self._ai_status.setStyleSheet(f"color:{T['muted']};font-size:9pt;")
        ai_l.addWidget(self._ai_status)
        load_btn = QPushButton("Load GGUF Model...")
        load_btn.clicked.connect(self._load_gguf)
        load_btn.setStyleSheet(
            f"QPushButton{{background:{T['accent']};color:white;border:none;padding:8px;border-radius:3px;}}"
        )
        ai_l.addWidget(load_btn)
        self._ai_prompt = QPlainTextEdit()
        self._ai_prompt.setPlaceholderText("Ask AI to write Vyn code...")
        self._ai_prompt.setMaximumHeight(80)
        ai_l.addWidget(self._ai_prompt)
        gen_btn = QPushButton("Generate Vyn Code")
        gen_btn.clicked.connect(self._ai_generate)
        ai_l.addWidget(gen_btn)
        self._ai_output = QPlainTextEdit()
        self._ai_output.setReadOnly(True)
        self._ai_output.setMaximumHeight(100)
        self._ai_output.setPlaceholderText("AI response...")
        ai_l.addWidget(self._ai_output)
        open_ai = QPushButton("Open AI Training Example")
        open_ai.clicked.connect(lambda: self._open(str(ROOT / "examples" / "ai_train.vyn")))
        ai_l.addWidget(open_ai)
        open_ml = QPushButton("Open ML Bindings Example")
        open_ml.clicked.connect(lambda: self._open(str(ROOT / "examples" / "ml_bindings.vyn")))
        ai_l.addWidget(open_ml)
        ml_help = QLabel(
            "Python ML modules: numpy, torch, tensorflow,\n"
            "cv (OpenCV), pandas, sklearn, plot (matplotlib).\n"
            "pip install numpy pandas scikit-learn matplotlib opencv-python"
        )
        ml_help.setWordWrap(True)
        ml_help.setStyleSheet(f"color:{T['muted']};font-size:9pt;padding-top:8px;")
        ai_l.addWidget(ml_help)
        ai_l.addStretch()
        self._side.addWidget(ai_w)
        from vyn.gguf_assistant import GgufAssistant
        self._gguf = GgufAssistant()

        sl.addWidget(self._side)
        body.addWidget(side)

        # Center
        center = QSplitter(Qt.Vertical)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.setStyleSheet(
            f"QTabWidget::pane{{border:none;background:{T['bg']};}}"
            f"QTabBar::tab{{background:{T['tab_inactive']};color:{T['tab_text_muted']};"
            f"padding:8px 16px;border:1px solid {T['border']};border-bottom:none;}}"
            f"QTabBar::tab:selected{{background:{T['tab_active']};color:{T['tab_text']};"
            f"border-top:2px solid {T['accent']};}}"
        )
        center.addWidget(self.tabs)

        # Bottom panel
        bot = QTabWidget()
        bot.setStyleSheet(
            f"QTabWidget::pane{{background:{T['panel_bg']};border-top:1px solid {T['border']};}}"
            f"QTabBar::tab{{background:{T['tab_inactive']};padding:6px 12px;}}"
            f"QTabBar::tab:selected{{background:{T['tab_active']};border-top:2px solid {T['accent']};}}"
        )
        self.problems = QListWidget()
        self.problems.setStyleSheet(
            f"QListWidget{{background:{T['panel_bg']};color:{T['text']};border:none;font-family:Consolas;font-size:10pt;}}"
        )
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(
            f"QTextEdit{{background:{T['panel_bg']};color:{T['text']};"
            f"font-family:Consolas;font-size:10pt;border:none;}}"
        )
        self.profile = QTextEdit()
        self.profile.setReadOnly(True)
        self.profile.setStyleSheet(
            f"QTextEdit{{background:{T['panel_bg']};color:#098658;"
            f"font-family:Consolas;font-size:10pt;border:none;}}"
        )
        bot.addTab(self.problems, "Problems")
        bot.addTab(self.output, "Terminal")
        bot.addTab(self.profile, "Profiling")
        center.addWidget(bot)
        center.setSizes([680, 220])
        body.addWidget(center)
        body.setSizes([260, 1180])
        root.addWidget(body)

        # Menu
        mb = self.menuBar()
        mb.setStyleSheet(f"background:{T['sidebar']};color:{T['text']};")
        fm = mb.addMenu("File")
        for label, slot, shortcut in [
            ("New File", self._new, QKeySequence.New),
            ("Open File...", self._open_dialog, QKeySequence.Open),
            ("Save", self._save, QKeySequence.Save),
            ("Exit", self.close, QKeySequence.Quit),
        ]:
            a = QAction(label, self)
            a.setShortcut(shortcut)
            a.triggered.connect(slot)
            fm.addAction(a)

        em = mb.addMenu("Edit")
        em.addAction(QAction("Undo", self, shortcut=QKeySequence.Undo, triggered=lambda: self._tab() and self._tab().editor.undo()))
        em.addAction(QAction("Redo", self, shortcut=QKeySequence.Redo, triggered=lambda: self._tab() and self._tab().editor.redo()))

        rm = mb.addMenu("Run")
        for label, mode in [
            ("Run", "run"), ("Stop", "stop"),
            ("Parse", "parse"), ("LLVM IR", "ir"), ("Native Build", "build"),
        ]:
            a = QAction(label, self)
            if mode == "stop":
                a.triggered.connect(self._stop_run)
            else:
                a.triggered.connect(lambda _, m=mode: self._compile(m))
            rm.addAction(a)

        hm = mb.addMenu("Help")
        hm.addAction(QAction("Open README", self, triggered=lambda: self._open(str(ROOT / "README.md"))))

        # Status bar
        self.status = QStatusBar()
        self.status.setStyleSheet(f"background:{T['statusbar']};color:white;")
        self._pos_lbl = QLabel("Ln 1, Col 1")
        self._lang_lbl = QLabel("Vyn")
        self._enc_lbl = QLabel("UTF-8")
        self._mode_lbl = QLabel("Interpreter")
        for w in (self._pos_lbl, self._lang_lbl, self._enc_lbl, self._mode_lbl):
            w.setStyleSheet("color:white;padding:0 10px;")
            self.status.addPermanentWidget(w)
        self.setStatusBar(self.status)
        self.status.showMessage("VynStudio ready — F5 Run | Ctrl+Space Complete | Ctrl+S Save")

        self._stop_action_visible = False
        QAction("Run", self, shortcut="F5", triggered=self._run)
        QAction("Stop", self, shortcut="Shift+F5", triggered=self._stop_run)

    def _load_gguf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load GGUF Model", str(Path.home()),
            "GGUF models (*.gguf);;All files (*)",
        )
        if not path:
            return
        ok, msg = self._gguf.load(path)
        self._ai_status.setText(msg)
        self.status.showMessage(msg)

    def _ai_generate(self):
        prompt = self._ai_prompt.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "AI Copilot", "Enter a prompt first.")
            return
        t = self._tab()
        ctx = t.source() if t else ""
        self.status.showMessage("Generating...")
        QApplication.processEvents()
        result = self._gguf.generate_vyn(prompt, ctx)
        self._ai_output.setPlainText(result)
        if not self._gguf.is_loaded:
            QMessageBox.warning(self, "AI Copilot", result)
            return
        reply = QMessageBox.question(
            self, "Insert AI Code?",
            "Insert generated Vyn code into the editor?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and t:
            t.editor.insertPlainText("\n" + result + "\n")
        self.status.showMessage("AI generation complete")

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{T['muted']};font-weight:bold;font-size:8pt;letter-spacing:1px;")
        return lbl

    def _fill_tree(self):
        self.tree.clear()
        root_item = QTreeWidgetItem(["VYN"])
        for folder, expand in [("examples", True), ("stdlib/std", False), ("vendor", False), ("vyn", False)]:
            node = QTreeWidgetItem([folder])
            p = ROOT / folder
            if p.exists():
                for f in sorted(p.rglob("*.vyn")):
                    rel = str(f.relative_to(ROOT)).replace("\\", "/")
                    node.addChild(QTreeWidgetItem([rel]))
            node.setExpanded(expand)
            root_item.addChild(node)
        self.tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)

    def _tree_open(self, item, _col):
        text = item.text(0)
        if text.endswith(".vyn"):
            p = ROOT / text
            if p.exists():
                self._open(str(p))

    def _insert_package(self, item: QListWidgetItem):
        t = self._tab()
        if not t:
            return
        name = item.text().split("—")[0].strip()
        t.editor.insertPlainText(f"import {name};\n")

    def _tab(self) -> EditorTab | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, EditorTab) else None

    def _open(self, path: str):
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, EditorTab) and t.path == path:
                self.tabs.setCurrentIndex(i)
                return
        t = EditorTab(path)
        t.on_cursor = self._update_pos
        t.on_dirty = self._update_tab_title
        name = Path(path).name
        self.tabs.addTab(t, name)
        self.tabs.setCurrentWidget(t)
        self.status.showMessage(f"Opened {path}")

    def _update_tab_title(self, tab: EditorTab):
        idx = self.tabs.indexOf(tab)
        if idx < 0:
            return
        name = tab.display_name()
        if tab.is_dirty():
            name = f"{name} *"
        self.tabs.setTabText(idx, name)

    def _prompt_save_if_dirty(self, tab: EditorTab) -> bool:
        """Demande d'enregistrer. True = peut fermer, False = annuler."""
        if not tab.is_dirty():
            return True
        name = tab.display_name()
        reply = QMessageBox.question(
            self,
            "VynStudio",
            f"Do you want to save changes to \"{name}\"?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.No:
            return True
        return self._save_tab(tab, force_dialog=not tab.path)

    def _save_tab(self, tab: EditorTab, *, force_dialog: bool = False) -> bool:
        """Enregistre un onglet. Retourne False si l'utilisateur annule Save As."""
        if force_dialog or not tab.path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File", str(ROOT), "Vyn files (*.vyn);;All (*)"
            )
            if not path:
                return False
            tab.path = path
            tab._update_breadcrumb()
        if tab.path:
            Path(tab.path).write_text(tab.source(), encoding="utf-8")
            tab.mark_saved()
            idx = self.tabs.indexOf(tab)
            if idx >= 0:
                self.tabs.setTabText(idx, tab.display_name())
            self.status.showMessage(f"Saved {tab.path}")
            return True
        return False

    def _close_tab(self, index: int):
        tab = self.tabs.widget(index)
        if isinstance(tab, EditorTab):
            if not self._prompt_save_if_dirty(tab):
                return
        self.tabs.removeTab(index)

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, EditorTab) and tab.is_dirty():
                self.tabs.setCurrentIndex(i)
                if not self._prompt_save_if_dirty(tab):
                    event.ignore()
                    return
        if self._run_worker and self._run_worker.isRunning():
            self._run_worker.stop()
        event.accept()

    def _update_pos(self, line: int, col: int):
        self._pos_lbl.setText(f"Ln {line}, Col {col}")

    def _new(self):
        t = EditorTab()
        t.on_cursor = self._update_pos
        t.on_dirty = self._update_tab_title
        t.editor.setPlainText(
            'import std.io;\n\nfn main() -> i32 {\n    io.println("Hello Vyn!");\n    return 0;\n}\n'
        )
        t.mark_saved()  # contenu initial = état propre
        self.tabs.addTab(t, "untitled.vyn")
        self.tabs.setCurrentWidget(t)

    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", str(ROOT), "Vyn files (*.vyn);;All (*)")
        if path:
            self._open(path)

    def _save(self):
        t = self._tab()
        if not t:
            return
        self._save_tab(t, force_dialog=not t.path)

    def _run(self):
        self._compile("run")

    def _stop_run(self):
        if self._run_worker and self._run_worker.isRunning():
            self._run_worker.stop()
            self.output.append("\n-- STOPPED --\n")
            self.status.showMessage("Run stopped")
        from vyn.stdlib_runtime import reset_http_server
        from vyn.gui_runtime import reset_gui
        reset_http_server()
        reset_gui()

    def _compile(self, mode: str):
        t = self._tab()
        if not t:
            QMessageBox.warning(self, "VynStudio", "No file open.")
            return
        if t.path and t.is_dirty():
            t.save()
            t.mark_saved()
            self._update_tab_title(t)
        src = t.source()
        self.output.append(f"\n-- {mode.upper()} --\n")
        self.status.showMessage(f"Running {mode}...")

        if mode == "run":
            if _needs_gui_thread(src):
                self._run_gui_main_thread(src)
            else:
                if self._run_worker and self._run_worker.isRunning():
                    self._stop_run()
                self._run_worker = RunWorker(src)
                self._run_worker.done.connect(self._on_run_done)
                self._run_worker.start()
            return

        self._build_worker = BuildWorker(src, mode)
        self._build_worker.done.connect(self._on_build_done)
        self._build_worker.start()

    def _run_gui_main_thread(self, src: str):
        try:
            from vyn.interpreter import run_source
            buf = StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = run_source(src)
            self._on_run_done(code == 0, buf.getvalue() + f"\nexit code: {code}\n")
        except Exception as e:
            self._on_run_done(False, f"ERROR: {e}\n")

    def _on_run_done(self, ok: bool, text: str):
        self.output.append(text)
        if "[VynProfile]" in text:
            self.profile.append(text)
        self.status.showMessage("Run OK" if ok else "Run failed — see Terminal")

    def _on_build_done(self, ok: bool, text: str):
        self.output.append(text)
        self.status.showMessage("OK" if ok else "Failed")

    def _diagnostics(self):
        t = self._tab()
        if not t:
            return
        self.problems.clear()
        diags = analyze_source(t.source())
        t.editor.set_diagnostic_markers(diags)
        err_count = sum(1 for d in diags if d.severity == "error")
        warn_count = sum(1 for d in diags if d.severity == "warning")
        for d in diags:
            prefix = {"error": "✕", "warning": "⚠", "info": "ℹ"}.get(d.severity, "?")
            color = {"error": T["error"], "warning": T["warning"], "info": T["info"]}.get(d.severity, T["text"])
            item = QListWidgetItem(f"  {prefix}  Ln {d.line}, Col {d.col}  {d.message}")
            item.setForeground(QColor(color))
            self.problems.addItem(item)
        if err_count or warn_count:
            self.status.showMessage(f"Problems: {err_count} error(s), {warn_count} warning(s)")
        elif diags:
            self.status.showMessage("No errors — see Problems for hints")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("VynStudio")
    if LOGO_PATH.exists():
        app.setWindowIcon(QIcon(str(LOGO_PATH)))
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    win = VynStudio()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
