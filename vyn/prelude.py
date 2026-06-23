"""Injection automatique std + use + dependances VPM."""
from __future__ import annotations

from pathlib import Path

STDLIB = Path(__file__).resolve().parent.parent / "stdlib"
VENDOR = Path(__file__).resolve().parent.parent / "vendor"
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "vyn.toml"

USE_SYMBOLS = {
    "print", "println", "sleep", "clamp", "lerp", "window", "run",
    "label", "button", "abs", "sqrt", "len", "parse", "exists", "read", "write",
    "escape", "page", "h1", "route", "listen", "get", "post", "stringify",
    "now_ms", "sha256", "serialize", "version", "train", "predict", "model_new",
}


def _load_module(mod: str) -> str:
    for base in (STDLIB, VENDOR):
        p = base / mod.replace(".", "/")
        vyn = p.with_suffix(".vyn")
        lib = p / "lib.vyn"
        if vyn.exists():
            return vyn.read_text(encoding="utf-8")
        if lib.exists():
            return lib.read_text(encoding="utf-8")
    return ""


def _manifest_deps() -> list[str]:
    if not MANIFEST.exists():
        return []
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        return list(data.get("dependencies", {}).keys())
    except Exception:
        return []


def inject_prelude(source: str) -> str:
    lines: list[str] = []
    injected_deps: set[str] = set()

    # Auto-install imports depuis vyn.toml (packages VPM)
    for dep in _manifest_deps():
        if dep not in injected_deps and f"import {dep}" not in source:
            code = _load_module(dep)
            if code:
                lines += [f"// --- vpm: {dep} ---", code, f"// --- fin {dep} ---"]
                injected_deps.add(dep)

    for line in source.splitlines():
        s = line.strip()
        if s.startswith("import "):
            mod = s.replace("import", "").replace(";", "").strip()
            code = _load_module(mod)
            if code:
                lines += [f"// --- import {mod} ---", code, f"// --- fin {mod} ---"]
            continue
        if s.startswith("use "):
            rest = s.replace("use", "").replace(";", "").strip()
            parts = rest.split(".")
            if len(parts) >= 2 and parts[-1] in USE_SYMBOLS:
                mod = ".".join(parts[:-1])
            else:
                mod = rest
            code = _load_module(mod)
            if code:
                lines += [f"// --- use {rest} ---", code, f"// --- fin use ---"]
            continue
        lines.append(line)
    return "\n".join(lines)
