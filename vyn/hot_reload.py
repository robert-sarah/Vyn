"""Hot-reload pour fonctions `hot fn` — swap en mémoire via l'interpréteur."""
from __future__ import annotations

import hashlib
import re
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from vyn.interpreter import Interpreter
from vyn.parser import Parser
from vyn.prelude import inject_prelude
from vyn.semantic import SemanticAnalyzer


HOT_FN_PATTERN = re.compile(
    r"hot\s+fn\s+(\w+)\s*\([^)]*\)\s*->\s*(\w+)\s*\{([^}]*)\}",
    re.DOTALL,
)


def _load_program(source_path: Path):
    source = inject_prelude(source_path.read_text(encoding="utf-8"))
    program = Parser(source).parse()
    SemanticAnalyzer().analyze(program)
    return program


class HotReloadManager:
    """Surveille un fichier .vyn et recharge les fonctions hot en mémoire."""

    def __init__(self, source_path: str, interpreter: Optional[Interpreter] = None):
        self.source_path = Path(source_path)
        self.interpreter = interpreter
        self._hashes: Dict[str, str] = {}
        self._running = False
        self._observer: Optional[Observer] = None
        self.on_reload: Optional[Callable[[str, str], None]] = None

    def extract_hot_functions(self, source: str) -> Dict[str, str]:
        result = {}
        for m in HOT_FN_PATTERN.finditer(source):
            name, _, body = m.group(1), m.group(2), m.group(3)
            digest = hashlib.sha256(body.encode()).hexdigest()[:12]
            result[name] = digest
        return result

    def check_and_reload(self) -> List[str]:
        source = self.source_path.read_text(encoding="utf-8")
        current = self.extract_hot_functions(source)
        reloaded: List[str] = []
        changed = any(self._hashes.get(n) != d for n, d in current.items())
        self._hashes.update(current)

        if changed and self.interpreter is not None:
            try:
                program = _load_program(self.source_path)
                swapped = self.interpreter.reload_hot_functions(program)
                reloaded.extend(swapped)
                for name in swapped:
                    if self.on_reload:
                        self.on_reload(name, self._hashes.get(name, ""))
            except Exception as exc:
                print(f"[HotSwap] Erreur rechargement: {exc}", file=sys.stderr)
        elif changed:
            for name, digest in current.items():
                reloaded.append(name)
                if self.on_reload:
                    self.on_reload(name, digest)
        return reloaded

    def start_watching(self) -> None:
        self._running = True
        self.check_and_reload()

        class Handler(FileSystemEventHandler):
            def __init__(self, mgr: "HotReloadManager"):
                self.mgr = mgr

            def on_modified(self, event):
                if Path(event.src_path).resolve() == self.mgr.source_path.resolve():
                    for fn in self.mgr.check_and_reload():
                        print(f"[HotSwap] Fonction '{fn}' rechargée à chaud.")

        handler = Handler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.source_path.parent), recursive=False)
        self._observer.start()

    def stop(self) -> None:
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)


def run_with_hot_reload(source_path: str) -> None:
    """Exécute via interpréteur avec swap à chaud des hot fn en mémoire."""
    path = Path(source_path)
    program = _load_program(path)
    interp = Interpreter(program)
    mgr = HotReloadManager(str(path), interpreter=interp)

    print(f"[Vyn] Hot-reload actif (interpréteur) sur {path.name}")
    mgr.start_watching()
    try:
        code = interp.run()
    finally:
        mgr.stop()
    sys.exit(int(code or 0))
