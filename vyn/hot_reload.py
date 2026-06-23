"""Hot-reload pour fonctions `hot fn` — recompilation à chaud."""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from vyn.compiler import VynCompiler


HOT_FN_PATTERN = re.compile(
    r"hot\s+fn\s+(\w+)\s*\([^)]*\)\s*->\s*(\w+)\s*\{([^}]*)\}",
    re.DOTALL,
)


class HotReloadManager:
    """Surveille un fichier .vyn et recompile les fonctions hot."""

    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        self.compiler = VynCompiler()
        self._hashes: Dict[str, str] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._observer: Optional[Observer] = None
        self.on_reload: Optional[Callable[[str, str], None]] = None

    def extract_hot_functions(self, source: str) -> Dict[str, str]:
        result = {}
        for m in HOT_FN_PATTERN.finditer(source):
            name, ret, body = m.group(1), m.group(2), m.group(3)
            digest = hashlib.sha256(body.encode()).hexdigest()[:12]
            result[name] = digest
        return result

    def check_and_reload(self) -> list[str]:
        source = self.source_path.read_text(encoding="utf-8")
        current = self.extract_hot_functions(source)
        reloaded = []
        for name, digest in current.items():
            if self._hashes.get(name) != digest:
                self._hashes[name] = digest
                reloaded.append(name)
                if self.on_reload:
                    self.on_reload(name, digest)
        return reloaded

    def start_watching(self, interval: float = 1.0) -> None:
        self._running = True
        self.check_and_reload()

        class Handler(FileSystemEventHandler):
            def __init__(self, mgr: HotReloadManager):
                self.mgr = mgr

            def on_modified(self, event):
                if Path(event.src_path).resolve() == self.mgr.source_path.resolve():
                    changed = self.mgr.check_and_reload()
                    for fn in changed:
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
    """Compile et exécute avec surveillance hot fn."""
    path = Path(source_path)
    mgr = HotReloadManager(str(path))
    print(f"[Vyn] Hot-reload actif sur {path.name}")
    mgr.start_watching()
    compiler = VynCompiler()
    try:
        exe = compiler.build_executable(str(path))
        proc = subprocess.Popen([exe])
        while proc.poll() is None:
            time.sleep(0.5)
        sys.exit(proc.returncode or 0)
    finally:
        mgr.stop()
