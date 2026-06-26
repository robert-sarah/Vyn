"""VynStudio — File Explorer Panel (VS Code style)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSortFilterProxyModel
from PyQt5.QtGui import QIcon, QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel,
    QLabel, QLineEdit, QToolButton, QPushButton, QMenu, QAction,
    QInputDialog, QMessageBox, QShortcut, QSizePolicy, QFrame,
    QAbstractItemView, QHeaderView,
)


class FileExplorer(QWidget):
    """File explorer panel with context menu and file operations.

    Signals
    -------
    file_opened(path: str)     — user double-clicked a file
    file_renamed(old, new)     — file was renamed
    file_deleted(path)         — file was deleted
    folder_changed(path)       — root folder changed
    """

    file_opened    = pyqtSignal(str)
    file_renamed   = pyqtSignal(str, str)
    file_deleted   = pyqtSignal(str)
    folder_changed = pyqtSignal(str)

    # Extensions shown with a special icon/marker
    VYN_EXTS  = {".vyn"}
    CODE_EXTS = {".py", ".c", ".cpp", ".h", ".hpp", ".js", ".ts",
                 ".json", ".toml", ".md", ".txt", ".yaml", ".yml"}

    def __init__(
        self,
        theme:   dict,
        root:    Optional[str] = None,
        parent:  Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._theme = theme
        self._root  = root or str(Path.cwd())
        self._build_ui()
        self._set_root(self._root)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        T   = self._theme
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header bar ───────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(34)
        h_lay  = QHBoxLayout(header)
        h_lay.setContentsMargins(8, 4, 6, 4)
        h_lay.setSpacing(4)

        lbl = QLabel("EXPLORER")
        lbl.setStyleSheet(
            f"color:{T.get('muted','#6E6E6E')};"
            f"font-size:9pt;font-weight:bold;letter-spacing:1px;"
        )
        h_lay.addWidget(lbl)
        h_lay.addStretch()

        for icon, tip, slot in [
            ("📄", "New File",   self._new_file),
            ("📁", "New Folder", self._new_folder),
            ("⟳",  "Refresh",   self._refresh),
            ("⋯",  "Open Folder…", self._open_folder),
        ]:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(24, 24)
            btn.clicked.connect(slot)
            h_lay.addWidget(btn)

        header.setStyleSheet(f"background:{T.get('sidebar','#F3F3F3')};")
        lay.addWidget(header)

        # ── Search bar ────────────────────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search files…")
        self._search.setFixedHeight(28)
        self._search.textChanged.connect(self._on_search)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background:{T.get('input_bg','#FFFFFF')};
                color:{T.get('text','#333')};
                border:none;
                border-bottom:1px solid {T.get('border','#E5E5E5')};
                padding:2px 8px;
                font-size:10pt;
            }}
        """)
        lay.addWidget(self._search)

        # ── Root label ────────────────────────────────────────────────────────
        self._root_lbl = QLabel()
        self._root_lbl.setFixedHeight(22)
        self._root_lbl.setStyleSheet(
            f"color:{T.get('accent','#007ACC')};"
            f"font-size:8pt;font-weight:bold;"
            f"padding:0 8px;"
            f"background:{T.get('sidebar','#F3F3F3')};"
        )
        lay.addWidget(self._root_lbl)

        # ── File system model ─────────────────────────────────────────────────
        self._model = QFileSystemModel()
        self._model.setReadOnly(False)
        self._model.setNameFilterDisables(False)

        # Filter proxy for search
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setRecursiveFilteringEnabled(True)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # ── Tree view ─────────────────────────────────────────────────────────
        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setAnimated(True)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.AscendingOrder)
        self._tree.setEditTriggers(QAbstractItemView.SelectedClicked)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.doubleClicked.connect(self._on_double_click)
        self._tree.setDragDropMode(QAbstractItemView.DragDrop)
        self._tree.setDefaultDropAction(Qt.MoveAction)
        self._tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tree.setIndentation(16)
        self._tree.setUniformRowHeights(True)

        # Hide columns except Name
        for col in range(1, 4):
            self._tree.hideColumn(col)
        self._tree.header().hide()

        self._tree.setStyleSheet(self._tree_stylesheet())
        lay.addWidget(self._tree, stretch=1)

        # ── Status bar ────────────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setFixedHeight(20)
        self._status.setStyleSheet(
            f"color:{T.get('muted','#6E6E6E')};"
            f"font-size:8pt;padding:0 8px;"
            f"background:{T.get('sidebar','#F3F3F3')};"
        )
        lay.addWidget(self._status)

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        QShortcut(QKeySequence(Qt.Key_Delete),    self._tree, self._delete_selected)
        QShortcut(QKeySequence(Qt.Key_F2),        self._tree, self._rename_selected)
        QShortcut(QKeySequence("Ctrl+N"),         self._tree, self._new_file)
        QShortcut(QKeySequence("Ctrl+Shift+N"),   self._tree, self._new_folder)

    # ── Root management ───────────────────────────────────────────────────────

    def _set_root(self, path: str) -> None:
        self._root = path
        root_idx   = self._model.setRootPath(path)
        proxy_idx  = self._proxy.mapFromSource(root_idx)
        self._tree.setRootIndex(proxy_idx)
        short = Path(path).name or path
        self._root_lbl.setText(f"  📂 {short}")
        self._root_lbl.setToolTip(path)
        self._status.setText(f"{self._count_items(path)} items")
        self.folder_changed.emit(path)

    def set_root(self, path: str) -> None:
        if Path(path).is_dir():
            self._set_root(path)

    def root(self) -> str:
        return self._root

    # ── File operations ───────────────────────────────────────────────────────

    def _new_file(self) -> None:
        parent_dir = self._selected_dir()
        name, ok   = QInputDialog.getText(
            self, "New File", "File name:", text="untitled.vyn"
        )
        if ok and name.strip():
            path = Path(parent_dir) / name.strip()
            try:
                path.touch()
                self._refresh()
                self._status.setText(f"Created: {path.name}")
                self.file_opened.emit(str(path))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot create file:\n{e}")

    def _new_folder(self) -> None:
        parent_dir = self._selected_dir()
        name, ok   = QInputDialog.getText(
            self, "New Folder", "Folder name:", text="new_folder"
        )
        if ok and name.strip():
            path = Path(parent_dir) / name.strip()
            try:
                path.mkdir(parents=True, exist_ok=True)
                self._refresh()
                self._status.setText(f"Created folder: {path.name}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot create folder:\n{e}")

    def _rename_selected(self) -> None:
        path = self._selected_path()
        if not path:
            return
        old_name = Path(path).name
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_path = str(Path(path).parent / new_name.strip())
            try:
                Path(path).rename(new_path)
                self._refresh()
                self._status.setText(f"Renamed: {old_name} → {new_name}")
                self.file_renamed.emit(path, new_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot rename:\n{e}")

    def _delete_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            return
        names = "\n".join(Path(p).name for p in paths[:5])
        if len(paths) > 5:
            names += f"\n… and {len(paths)-5} more"
        reply = QMessageBox.question(
            self, "Delete",
            f"Delete the following?\n\n{names}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        for p in paths:
            try:
                if Path(p).is_dir():
                    shutil.rmtree(p)
                else:
                    Path(p).unlink()
                self.file_deleted.emit(p)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot delete {Path(p).name}:\n{e}")
        self._refresh()
        self._status.setText(f"Deleted {len(paths)} item(s)")

    def _duplicate_selected(self) -> None:
        path = self._selected_path()
        if not path:
            return
        p    = Path(path)
        stem = p.stem
        ext  = p.suffix
        n    = 1
        while True:
            new_path = p.parent / f"{stem}_copy{n}{ext}"
            if not new_path.exists():
                break
            n += 1
        try:
            if p.is_dir():
                shutil.copytree(str(p), str(new_path))
            else:
                shutil.copy2(str(p), str(new_path))
            self._refresh()
            self._status.setText(f"Duplicated: {new_path.name}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot duplicate:\n{e}")

    def _copy_path(self) -> None:
        path = self._selected_path()
        if path:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(path)
            self._status.setText(f"Copied path: {path}")

    def _copy_relative_path(self) -> None:
        path = self._selected_path()
        if path:
            try:
                rel = str(Path(path).relative_to(self._root))
            except ValueError:
                rel = path
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(rel)
            self._status.setText(f"Copied relative path: {rel}")

    def _reveal_in_explorer(self) -> None:
        path = self._selected_path()
        if not path:
            return
        import subprocess, sys
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", str(Path(path).parent)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot reveal:\n{e}")

    def _open_in_terminal(self) -> None:
        path = self._selected_path()
        if not path:
            return
        d = str(Path(path).parent if Path(path).is_file() else Path(path))
        import subprocess, sys
        try:
            if sys.platform == "win32":
                subprocess.Popen(["cmd.exe", "/K", f"cd /d {d}"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Terminal", d])
            else:
                subprocess.Popen(["xterm", "-e", f"cd {d} && bash"])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot open terminal:\n{e}")

    def _refresh(self) -> None:
        self._model.setRootPath("")
        self._model.setRootPath(self._root)
        root_idx  = self._model.index(self._root)
        proxy_idx = self._proxy.mapFromSource(root_idx)
        self._tree.setRootIndex(proxy_idx)
        n = self._count_items(self._root)
        self._status.setText(f"{n} items")

    def _open_folder(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self, "Open Folder", self._root
        )
        if path:
            self._set_root(path)

    # ── Context menu ─────────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        path = self._selected_path()
        T    = self._theme

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background:{T.get('popup_bg','#FFFFFF')};
                color:{T.get('text','#333')};
                border:1px solid {T.get('popup_border','#C8C8C8')};
                padding:4px 0;
            }}
            QMenu::item {{
                padding:5px 24px;
                border-radius:2px;
            }}
            QMenu::item:selected {{
                background:{T.get('popup_selected','#0060C0')};
                color:{T.get('popup_selected_fg','#FFFFFF')};
            }}
            QMenu::separator {{ height:1px; background:{T.get('border','#E5E5E5')}; margin:4px 8px; }}
        """)

        def _add(text, slot, shortcut=""):
            a = menu.addAction(text)
            if shortcut:
                a.setShortcutVisibleInContextMenu(True)
                a.setShortcut(QKeySequence(shortcut))
            a.triggered.connect(slot)
            return a

        # ── New ───────────────────────────────────────────────────────────────
        new_sub = menu.addMenu("New")
        new_sub.addAction("📄 File").triggered.connect(self._new_file)
        new_sub.addAction("📁 Folder").triggered.connect(self._new_folder)
        new_sub.addSeparator()
        for tmpl, content in [
            ("Vyn Source (.vyn)",   'fn main() -> i32 {\n    io.println("Hello Vyn!");\n    return 0;\n}\n'),
            ("Vyn Module (.vyn)",   '// Module\n\npub fn init() -> i32 {\n    return 0;\n}\n'),
            ("README (.md)",        "# Project\n\nDescription.\n"),
        ]:
            name = tmpl
            c    = content
            def _make_from_template(n=name, c=c):
                self._new_from_template(n, c)
            new_sub.addAction(name).triggered.connect(_make_from_template)

        menu.addSeparator()

        if path:
            is_file = Path(path).is_file()
            is_dir  = Path(path).is_dir()

            # ── Open ─────────────────────────────────────────────────────────
            if is_file:
                _add("Open", lambda: self.file_opened.emit(path), "Enter")

            # ── Edit group ───────────────────────────────────────────────────
            menu.addSeparator()
            _add("Rename", self._rename_selected, "F2")
            _add("Duplicate", self._duplicate_selected)
            _add("Delete", self._delete_selected, "Del")

            menu.addSeparator()

            # ── Clipboard ─────────────────────────────────────────────────────
            copy_sub = menu.addMenu("Copy")
            copy_sub.addAction("Copy Name").triggered.connect(
                lambda: self._copy_to_clipboard(Path(path).name)
            )
            copy_sub.addAction("Copy Path").triggered.connect(self._copy_path)
            copy_sub.addAction("Copy Relative Path").triggered.connect(self._copy_relative_path)

            menu.addSeparator()

            # ── Navigation ────────────────────────────────────────────────────
            if is_dir:
                menu.addAction("Set as Root").triggered.connect(
                    lambda: self._set_root(path)
                )
            menu.addAction("Reveal in Explorer").triggered.connect(self._reveal_in_explorer)
            menu.addAction("Open in Terminal").triggered.connect(self._open_in_terminal)

            menu.addSeparator()

            # ── Vyn actions ───────────────────────────────────────────────────
            if is_file and path.endswith(".vyn"):
                vyn_sub = menu.addMenu("▶ Run Vyn")
                vyn_sub.addAction("Run (interpreter)").triggered.connect(
                    lambda: self._run_vyn(path, "run")
                )
                vyn_sub.addAction("Parse (AST)").triggered.connect(
                    lambda: self._run_vyn(path, "parse")
                )
                vyn_sub.addAction("Show LLVM IR").triggered.connect(
                    lambda: self._run_vyn(path, "ir")
                )
                vyn_sub.addAction("Build (native)").triggered.connect(
                    lambda: self._run_vyn(path, "build")
                )

        menu.addSeparator()
        menu.addAction("Refresh").triggered.connect(self._refresh)

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _selected_path(self) -> Optional[str]:
        idx = self._tree.currentIndex()
        if not idx.isValid():
            return None
        src_idx = self._proxy.mapToSource(idx)
        return self._model.filePath(src_idx)

    def _selected_paths(self) -> list[str]:
        paths = []
        for idx in self._tree.selectedIndexes():
            if idx.column() == 0:
                src_idx = self._proxy.mapToSource(idx)
                paths.append(self._model.filePath(src_idx))
        return paths

    def _selected_dir(self) -> str:
        path = self._selected_path()
        if path and Path(path).is_dir():
            return path
        if path:
            return str(Path(path).parent)
        return self._root

    def _count_items(self, path: str) -> int:
        try:
            return sum(1 for _ in Path(path).iterdir())
        except Exception:
            return 0

    def _copy_to_clipboard(self, text: str) -> None:
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self._status.setText(f"Copied: {text}")

    def _new_from_template(self, label: str, content: str) -> None:
        parent_dir = self._selected_dir()
        # Extract default extension from label
        import re
        m = re.search(r'\((\.\w+)\)', label)
        ext  = m.group(1) if m else ".vyn"
        name, ok = QInputDialog.getText(
            self, "New File", "File name:", text=f"untitled{ext}"
        )
        if ok and name.strip():
            path = Path(parent_dir) / name.strip()
            try:
                path.write_text(content, encoding="utf-8")
                self._refresh()
                self._status.setText(f"Created: {path.name}")
                self.file_opened.emit(str(path))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Cannot create file:\n{e}")

    def _run_vyn(self, path: str, mode: str) -> None:
        """Emit a signal to open a terminal and run the file."""
        # Parent should connect to this via the terminal panel
        import subprocess, sys
        cmd = f"{sys.executable} -m vyn.cli {mode} \"{path}\""
        self._status.setText(f"Running: {mode} {Path(path).name}")
        # Notify parent (if they listen on file_opened with a special prefix)
        self.file_opened.emit(f"__run__:{mode}:{path}")

    # ── Search ────────────────────────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        if text.strip():
            # Filter by filename pattern
            self._proxy.setFilterWildcard(f"*{text}*")
            self._tree.expandAll()
        else:
            self._proxy.setFilterWildcard("")

    # ── Double click ──────────────────────────────────────────────────────────

    def _on_double_click(self, proxy_idx) -> None:
        src_idx = self._proxy.mapToSource(proxy_idx)
        path    = self._model.filePath(src_idx)
        if Path(path).is_file():
            self.file_opened.emit(path)
        else:
            if self._tree.isExpanded(proxy_idx):
                self._tree.collapse(proxy_idx)
            else:
                self._tree.expand(proxy_idx)

    # ── Stylesheet ────────────────────────────────────────────────────────────

    def _tree_stylesheet(self) -> str:
        T = self._theme
        return f"""
            QTreeView {{
                background:{T.get('sidebar','#F3F3F3')};
                color:{T.get('tree_text','#333')};
                border:none;
                font-size:10pt;
                selection-background-color:{T.get('tree_selected','#0060C0')};
                selection-color:{T.get('tree_selected_fg','white')};
                outline:none;
            }}
            QTreeView::item {{
                padding:2px 4px;
                border-radius:2px;
            }}
            QTreeView::item:hover {{
                background:{T.get('tree_hover','#E8E8E8')};
            }}
            QTreeView::item:selected {{
                background:{T.get('tree_selected','#0060C0')};
                color:{T.get('tree_selected_fg','white')};
            }}
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                image:none;
            }}
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {{
                image:none;
            }}
        """

    # ── Theme update ──────────────────────────────────────────────────────────

    def update_theme(self, theme: dict) -> None:
        self._theme = theme
        self._tree.setStyleSheet(self._tree_stylesheet())
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background:{theme.get('input_bg','#FFFFFF')};
                color:{theme.get('text','#333')};
                border:none;
                border-bottom:1px solid {theme.get('border','#E5E5E5')};
                padding:2px 8px;
                font-size:10pt;
            }}
        """)
        self._root_lbl.setStyleSheet(
            f"color:{theme.get('accent','#007ACC')};"
            f"font-size:8pt;font-weight:bold;"
            f"padding:0 8px;"
            f"background:{theme.get('sidebar','#F3F3F3')};"
        )
        self._status.setStyleSheet(
            f"color:{theme.get('muted','#6E6E6E')};"
            f"font-size:8pt;padding:0 8px;"
            f"background:{theme.get('sidebar','#F3F3F3')};"
        )

    # ── External API ──────────────────────────────────────────────────────────

    def select_file(self, path: str) -> None:
        """Highlight the given file path in the tree."""
        idx       = self._model.index(path)
        proxy_idx = self._proxy.mapFromSource(idx)
        if proxy_idx.isValid():
            self._tree.setCurrentIndex(proxy_idx)
            self._tree.scrollTo(proxy_idx, QAbstractItemView.PositionAtCenter)

    def expand_to(self, path: str) -> None:
        """Expand the tree to show the given path."""
        idx       = self._model.index(path)
        proxy_idx = self._proxy.mapFromSource(idx)
        if proxy_idx.isValid():
            self._tree.expand(proxy_idx)
            parent = proxy_idx.parent()
            while parent.isValid():
                self._tree.expand(parent)
                parent = parent.parent()

    def selected_file(self) -> Optional[str]:
        return self._selected_path()
