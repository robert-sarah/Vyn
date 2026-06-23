"""Pipeline compilateur Vyn — orchestration complète."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from vyn.codegen import compile_to_ir
from vyn.parser import Parser, ParseError
from vyn.lexer import LexError
from vyn.semantic import SemanticError


ROOT = Path(__file__).resolve().parent.parent
RUNTIME_C = Path(__file__).resolve().parent / "runtime" / "vyn_rt.c"


@dataclass
class CompileResult:
    ir_path: str
    exe_path: Optional[str]
    semantic_info: object


class VynCompiler:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="vyn_"))

    def compile_source(self, source: str, name: str = "module") -> CompileResult:
        ir_code, sem = compile_to_ir(source)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ir_path = self.output_dir / f"{name}.ll"
        ir_path.write_text(ir_code, encoding="utf-8")
        return CompileResult(str(ir_path), None, sem)

    def build_executable(
        self,
        source_path: str,
        output: Optional[str] = None,
        optimize: int = 2,
    ) -> str:
        source_path = Path(source_path)
        source = source_path.read_text(encoding="utf-8")
        name = source_path.stem
        result = self.compile_source(source, name)
        exe_path = Path(output) if output else self.output_dir / (name + (".exe" if sys.platform == "win32" else ""))
        runtime_o = self._compile_runtime()
        clang = self._find_clang()
        cmd = [
            clang,
            f"-O{optimize}",
            result.ir_path,
            runtime_o,
            "-o", str(exe_path),
        ]
        if sys.platform == "win32":
            cmd.extend(["-luser32"])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Échec liaison LLVM:\n{proc.stderr}")
        return str(exe_path)

    def run_jit(self, source: str) -> int:
        """Exécution via clang + exe temporaire."""
        with tempfile.TemporaryDirectory(prefix="vyn_run_") as tmp:
            src = Path(tmp) / "main.vyn"
            src.write_text(source, encoding="utf-8")
            exe = self.build_executable(str(src), str(Path(tmp) / "out.exe"))
            proc = subprocess.run([exe], capture_output=True, text=True)
            if proc.stdout:
                print(proc.stdout, end="")
            if proc.stderr:
                print(proc.stderr, end="", file=sys.stderr)
            return proc.returncode

    def _compile_runtime(self) -> str:
        clang = self._find_clang()
        out = self.output_dir / "vyn_rt.o"
        cmd = [clang, "-c", str(RUNTIME_C), "-o", str(out)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Échec compilation runtime:\n{proc.stderr}")
        return str(out)

    def _find_clang(self) -> str:
        for candidate in ("clang", "clang-18", "clang-17", "clang-16"):
            if shutil.which(candidate):
                return candidate
        raise RuntimeError(
            "Clang/LLVM introuvable. Installez LLVM et ajoutez clang au PATH."
        )


def compile_file(path: str, output: Optional[str] = None) -> str:
    return VynCompiler().build_executable(path, output)
