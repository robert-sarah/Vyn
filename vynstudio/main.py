"""VynStudio — IDE style VS Code."""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTextEdit, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QAction, QStatusBar, QLabel, QMessageBox, QTabWidget,
    QFrame, QPushButton, QListWidget, QListWidgetItem, QStackedWidget,
    QPlainTextEdit,
)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vynstudio.editor import VynCodeEditor
from vynstudio.highlighter import VynHighlighter
from vyn.diagnostics import analyze_source

BG = "#1E1E1E"
SIDEBAR = "#252526"
ACTIVITY = "#333333"
BORDER = "#3C3C3C"
ACCENT = "#007ACC"
TAB_ACTIVE = "#1E1E1E"
TAB_INACTIVE = "#2D2D2D"
TEXT = "#CCCCCC"
MUTED = "#858585"


class Worker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, src, mode):
        super().__init__()
        self.src, self.mode = src, mode

    def run(self):
        try:
            if self.mode == "run":
                from vyn.interpreter import run_source
                b = StringIO()
                with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):
                    c = run_source(self.src)
                self.done.emit(c == 0, b.getvalue() + f"\nexit code: {c}\n")
            elif self.mode == "parse":
                from vyn.prelude import inject_prelude
                from vyn.parser import Parser
                p = Parser(inject_prelude(self.src)).parse()
                self.done.emit(True, f"OK - fn: {[f.name for f in p.functions]}  struct: {[s.name for s in p.structs]}\n")
            elif self.mode == "ir":
                from vyn.codegen import compile_to_ir
                ir, _ = compile_to_ir(self.src)
                self.done.emit(True, ir[:2500] + "\n...")
            else:
                tmp = ROOT / "examples" / "_build_tmp.vyn"
                tmp.write_text(self.src, encoding="utf-8")
                r = subprocess.run(
                    [sys.executable, "-m", "vyn.cli", "build", str(tmp)],
                    capture_output=True, text=True, cwd=str(ROOT),
                )
                self.done.emit(r.returncode == 0, r.stdout + r.stderr)
        except Exception as e:
            self.done.emit(False, f"ERREUR: {e}")


class EditorTab(QWidget):
    def __init__(self, path=None):
        super().__init__()
        self.path = path
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.editor = VynCodeEditor()
        self.highlighter = VynHighlighter(self.editor.document())
        self.editor.cursorPositionChanged.connect(self._cursor)
        self.on_cursor = None
        lay.addWidget(self.editor)
        if path and os.path.exists(path):
            self.editor.setPlainText(Path(path).read_text(encoding="utf-8"))

    def _cursor(self):
        if self.on_cursor:
            c = self.editor.textCursor()
            self.on_cursor(c.blockNumber() + 1, c.columnNumber() + 1)

    def source(self):
        return self.editor.toPlainText()

    def save(self):
        if self.path:
            Path(self.path).write_text(self.source(), encoding="utf-8")
            return True
        return False


class VynStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VynStudio")
        self.resize(1440, 900)
        self.setStyleSheet(f"QMainWindow{{background:{BG};}}")
        self._worker = None
        self._build()
        self._diag = QTimer(self)
        self._diag.timeout.connect(self._diagnostics)
        self._diag.start(700)
        p = ROOT / "examples" / "profile.vyn"
        if p.exists():
            self._open(str(p))

    def _build(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        root = QHBoxLayout(cw)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Activity bar (texte, pas emoji)
        act = QFrame()
        act.setFixedWidth(48)
        act.setStyleSheet(f"background:{ACTIVITY};")
        al = QVBoxLayout(act)
        al.setAlignment(Qt.AlignTop)
        al.setSpacing(2)
        for label, tip, slot in [
            ("EX", "Explorateur", lambda: self._side.setCurrentIndex(0)),
            ("SR", "Recherche", lambda: self._side.setCurrentIndex(1)),
            ("LB", "Bibliotheques", lambda: self._side.setCurrentIndex(2)),
            ("RN", "Executer", self._run),
        ]:
            b = QPushButton(label)
            b.setFixedSize(40, 40)
            b.setToolTip(tip)
            b.setStyleSheet(
                "QPushButton{background:transparent;color:#CCC;font-size:10px;"
                "font-weight:bold;border:none;}"
                "QPushButton:hover{background:#505050;}"
            )
            b.clicked.connect(slot)
            al.addWidget(b, alignment=Qt.AlignHCenter)
        al.addStretch()
        root.addWidget(act)

        body = QSplitter(Qt.Horizontal)

        side = QFrame()
        side.setMaximumWidth(280)
        side.setStyleSheet(f"background:{SIDEBAR};border-right:1px solid {BORDER};")
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        self._side = QStackedWidget()

        exp = QWidget()
        el = QVBoxLayout(exp)
        el.addWidget(self._title("EXPLORATEUR"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(
            f"QTreeWidget{{background:{SIDEBAR};color:{TEXT};border:none;}}"
            "QTreeWidget::item:selected{background:#094771;}"
        )
        self._tree_fill()
        self.tree.itemDoubleClicked.connect(self._tree_open)
        el.addWidget(self.tree)
        self._side.addWidget(exp)

        srch = QWidget()
        srl = QVBoxLayout(srch)
        srl.addWidget(self._title("RECHERCHE"))
        self.search_in = QPlainTextEdit()
        self.search_in.setMaximumHeight(28)
        self.search_in.setPlaceholderText("Rechercher...")
        self.search_in.setStyleSheet(f"background:{BG};color:{TEXT};border:1px solid {BORDER};")
        srl.addWidget(self.search_in)
        self._side.addWidget(srch)

        ext = QWidget()
        exl = QVBoxLayout(ext)
        exl.addWidget(self._title("BIBLIOTHEQUES STD"))
        libs = QListWidget()
        libs.setStyleSheet(f"QListWidget{{background:{SIDEBAR};color:{TEXT};border:none;}}")
        for lib in [
            "std.io", "std.sys", "std.math", "std.gui", "std.log", "std.vec",
            "std.rand", "std.hash", "std.array", "std.thread", "std.crypto",
            "std.net", "std.fs", "std.json", "std.sync", "std.time", "std.str", "std.mem",
        ]:
            libs.addItem(lib)
        libs.itemDoubleClicked.connect(self._insert_import)
        exl.addWidget(libs)
        self._side.addWidget(ext)

        sl.addWidget(self._side)
        body.addWidget(side)

        center = QSplitter(Qt.Vertical)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tabs.removeTab)
        self.tabs.setStyleSheet(
            f"QTabWidget::pane{{border:none;background:{BG};}}"
            f"QTabBar::tab{{background:{TAB_INACTIVE};color:#969696;padding:6px 14px;}}"
            f"QTabBar::tab:selected{{background:{TAB_ACTIVE};color:#FFF;border-top:2px solid {ACCENT};}}"
        )
        center.addWidget(self.tabs)

        bot = QTabWidget()
        bot.setStyleSheet(f"QTabWidget::pane{{background:{BG};border-top:1px solid {BORDER};}}")
        self.problems = QListWidget()
        self.problems.setStyleSheet(f"QListWidget{{background:{BG};color:#F48771;border:none;}}")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(
            f"QTextEdit{{background:{BG};color:{TEXT};font-family:Consolas;font-size:10pt;border:none;}}"
        )
        self.profile = QTextEdit()
        self.profile.setReadOnly(True)
        self.profile.setStyleSheet(
            "QTextEdit{background:#1E1E1E;color:#4EC9B0;font-family:Consolas;border:none;}"
        )
        bot.addTab(self.problems, "Problemes")
        bot.addTab(self.output, "Terminal")
        bot.addTab(self.profile, "Profilage")
        center.addWidget(bot)
        center.setSizes([650, 200])
        body.addWidget(center)
        body.setSizes([260, 1100])
        root.addWidget(body)

        mb = self.menuBar()
        mb.setStyleSheet(f"background:{ACTIVITY};color:white;")
        fm = mb.addMenu("Fichier")
        for t, s, sc in [
            ("Nouveau", self._new, QKeySequence.New),
            ("Ouvrir", self._open_dlg, QKeySequence.Open),
            ("Enregistrer", self._save, QKeySequence.Save),
            ("Quitter", self.close, QKeySequence.Quit),
        ]:
            a = QAction(t, self)
            a.setShortcut(sc)
            a.triggered.connect(s)
            fm.addAction(a)
        bm = mb.addMenu("Executer")
        for t, m in [("Run", "run"), ("Parse", "parse"), ("LLVM IR", "ir"), ("Build natif", "build")]:
            a = QAction(t, self)
            a.triggered.connect(lambda _, m=m: self._compile(m))
            bm.addAction(a)

        self.status = QStatusBar()
        self.status.setStyleSheet(f"background:{ACCENT};color:white;")
        self._pos = QLabel("Ln 1, Col 1")
        self._lang = QLabel("Vyn")
        self._mode = QLabel("Interpreteur")
        for w in (self._pos, self._lang, self._mode):
            w.setStyleSheet("color:white;padding:0 8px;")
            self.status.addPermanentWidget(w)
        self.setStatusBar(self.status)
        self.status.showMessage("VynStudio - Ctrl+Espace: autocompletion | F5: Run")
        QAction("Run", self, shortcut="F5", triggered=self._run)

    def _title(self, t):
        l = QLabel(t)
        l.setStyleSheet(f"color:{MUTED};font-weight:bold;padding:8px;font-size:9pt;")
        return l

    def _tree_fill(self):
        self.tree.clear()
        root = QTreeWidgetItem(["VYN"])
        for folder in ["examples", "stdlib/std", "vendor", "vyn"]:
            n = QTreeWidgetItem([folder])
            p = ROOT / folder
            if p.exists():
                for f in sorted(p.rglob("*.vyn")):
                    n.addChild(QTreeWidgetItem([str(f.relative_to(ROOT)).replace("\\", "/")]))
            n.setExpanded(folder == "examples")
            root.addChild(n)
        self.tree.addTopLevelItem(root)
        root.setExpanded(True)

    def _tree_open(self, item, _):
        t = item.text(0)
        if t.endswith(".vyn"):
            p = ROOT / t
            if p.exists():
                self._open(str(p))

    def _insert_import(self, item):
        t = self._tab()
        if t:
            t.editor.insertPlainText(f"import {item.text()};\n")

    def _tab(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, EditorTab) else None

    def _open(self, path):
        for i in range(self.tabs.count()):
            t = self.tabs.widget(i)
            if isinstance(t, EditorTab) and t.path == path:
                self.tabs.setCurrentIndex(i)
                return
        t = EditorTab(path)
        t.on_cursor = self._upd_pos
        self.tabs.addTab(t, Path(path).name)
        self.tabs.setCurrentWidget(t)

    def _upd_pos(self, ln, col):
        self._pos.setText(f"Ln {ln}, Col {col}")

    def _new(self):
        t = EditorTab()
        t.on_cursor = self._upd_pos
        t.editor.setPlainText(
            'import std.io;\n\nfn main() -> i32 {\n    io.println("Hello Vyn!");\n    return 0;\n}\n'
        )
        self.tabs.addTab(t, "sans_titre.vyn")
        self.tabs.setCurrentWidget(t)

    def _open_dlg(self):
        p, _ = QFileDialog.getOpenFileName(self, "Ouvrir", str(ROOT), "Vyn (*.vyn)")
        if p:
            self._open(p)

    def _save(self):
        t = self._tab()
        if not t:
            return
        if not t.path:
            p, _ = QFileDialog.getSaveFileName(self, "Enregistrer", str(ROOT), "Vyn (*.vyn)")
            if p:
                t.path = p
                self.tabs.setTabText(self.tabs.currentIndex(), Path(p).name)
        if t.path and t.save():
            self.status.showMessage(f"Enregistre {t.path}")

    def _run(self):
        self._compile("run")

    def _compile(self, mode):
        t = self._tab()
        if not t:
            QMessageBox.warning(self, "VynStudio", "Aucun fichier.")
            return
        if t.path:
            t.save()
        src = t.source()
        self.output.append(f"\n-- {mode.upper()} --\n")
        self.status.showMessage(f"{mode}...")

        # GUI tkinter = thread principal obligatoire
        if mode == "run":
            self._run_main_thread(src)
            return

        self._worker = Worker(src, mode)
        self._worker.done.connect(self._done)
        self._worker.start()

    def _run_main_thread(self, src: str):
        try:
            from vyn.interpreter import run_source
            buf = StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                code = run_source(src)
            self._done(code == 0, buf.getvalue() + f"\nexit code: {code}\n")
        except Exception as e:
            self._done(False, f"ERREUR: {e}")

    def _done(self, ok, text):
        self.output.append(text)
        if "[VynProfile]" in text:
            self.profile.append(text)
        self.status.showMessage("OK" if ok else "Erreur")

    def _diagnostics(self):
        t = self._tab()
        if not t:
            return
        self.problems.clear()
        for d in analyze_source(t.source()):
            prefix = {"error": "[E]", "warning": "[W]", "info": "[I]"}.get(d.severity, "[?]")
            cl = {"error": "#F48771", "warning": "#CCA700", "info": "#4EC9B0"}.get(d.severity, "#CCC")
            it = QListWidgetItem(f"{prefix} L{d.line}:{d.col}  {d.message}")
            it.setForeground(QColor(cl))
            self.problems.addItem(it)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = VynStudio()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
