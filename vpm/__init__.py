"""VPM — Vyn Package Manager."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

MANIFEST = "vyn.toml"
REGISTRY = Path.home() / ".vpm" / "registry.json"

PACKAGES = {
    "serde": {"version": "1.0.0", "desc": "Serialisation JSON (serialize/deserialize)"},
    "collections": {"version": "1.0.0", "desc": "Stack, Queue via vec"},
    "async": {"version": "0.9.0", "desc": "defer_ms, yield_now"},
    "neural": {"version": "0.1.0", "desc": "ReLU hot-swap, sigmoid"},
    "web": {"version": "1.0.0", "desc": "Helpers HTML + API web"},
}

PACKAGE_TEMPLATES = {
    "serde": """// Package serde — serialisation JSON
pub fn version() -> str { return "1.0.0"; }
pub fn serialize(val: i32) -> str { return json.stringify(val); }
pub fn deserialize(text: str) -> i32 { return json.parse_int(text); }
pub fn init() -> i32 { return 0; }
""",
    "collections": """// Package collections
pub fn version() -> str { return "1.0.0"; }
pub fn stack_new() -> i32 { return vec.new(); }
pub fn stack_push(st: i32, val: i32) -> i32 { return vec.push(st, val); }
pub fn init() -> i32 { return 0; }
""",
    "async": """// Package async
pub fn version() -> str { return "0.9.0"; }
pub fn defer_ms(ms: i32) -> i32 { thread.sleep_ms(ms); return 0; }
pub fn init() -> i32 { return 0; }
""",
    "neural": """// Package neural
pub fn version() -> str { return "0.1.0"; }
hot fn activate(x: f32) -> f32 { if (x > 0.0) { return x; } return 0.0; }
pub fn relu(x: f32) -> f32 { return activate(x); }
pub fn init() -> i32 { return 0; }
""",
    "web": """// Package web
pub fn version() -> str { return "1.0.0"; }
pub fn page(title: str, body: str) -> str { return html.page(title, body); }
pub fn init() -> i32 { return 0; }
""",
}


def _default_manifest(name: str = "mon-projet") -> dict[str, Any]:
    return {
        "package": {"name": name, "version": "0.1.0", "authors": ["Vyn Developer"],
                    "description": "Projet Vyn"},
        "dependencies": {},
        "build": {"target": "native", "optimize": 2, "entry": "src/main.vyn"},
    }


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or Path(MANIFEST)
    if not p.exists():
        return _default_manifest()
    return tomllib.loads(p.read_text(encoding="utf-8"))


def save_manifest(data: dict[str, Any], path: Path | None = None) -> None:
    p = path or Path(MANIFEST)
    lines = ["[package]"]
    for k, v in data.get("package", {}).items():
        lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
    lines.append("\n[dependencies]")
    for dep, ver in data.get("dependencies", {}).items():
        lines.append(f'{dep} = "{ver}"')
    lines.append("\n[build]")
    for k, v in data.get("build", {}).items():
        lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _install_pkg(name: str, version: str) -> None:
    vendor = Path("vendor") / name
    vendor.mkdir(parents=True, exist_ok=True)
    meta = PACKAGES.get(name, {"version": version, "desc": "Package tiers"})
    lib = vendor / "lib.vyn"
    if not lib.exists() or name in PACKAGE_TEMPLATES:
        template = PACKAGE_TEMPLATES.get(name)
        if template:
            lib.write_text(template, encoding="utf-8")
        elif not lib.exists():
            lib.write_text(
                f"// Package {name} v{version} — {meta.get('desc', '')}\n"
                f"pub fn version() -> str {{ return \"{version}\"; }}\n"
                f"pub fn init() -> i32 {{ return 0; }}\n",
                encoding="utf-8",
            )
    (vendor / "vyn.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "{version}"\n', encoding="utf-8"
    )


def cmd_init(args):
    if Path(MANIFEST).exists():
        print(f"{MANIFEST} existe déjà."); return 1
    save_manifest(_default_manifest(args.name))
    src = Path("src"); src.mkdir(exist_ok=True)
    main = src / "main.vyn"
    if not main.exists():
        main.write_text('fn main() -> i32 {\n    io.println("Hello Vyn!");\n    return 0;\n}\n')
    print(f"✓ Projet initialisé — {MANIFEST}"); return 0


def cmd_add(args):
    data = load_manifest()
    ver = args.version or PACKAGES.get(args.name, {}).get("version", "1.0.0")
    data.setdefault("dependencies", {})[args.name] = ver
    save_manifest(data)
    _install_pkg(args.name, ver)
    print(f"✓ {args.name}@{ver} ajouté"); return 0


def cmd_install(args):
    data = load_manifest()
    deps = data.get("dependencies", {})
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    reg = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    for name, ver in deps.items():
        _install_pkg(name, ver)
        reg[name] = ver
        print(f"  ✓ {name}@{ver}")
    REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    print(f"✓ {len(deps)} package(s) installé(s)"); return 0


def cmd_list(args):
    print("Packages VPM disponibles :")
    print("  (comme npm/cargo — bibliotheques reutilisables pour votre projet)\n")
    for name, info in PACKAGES.items():
        installed = " [installe]" if (Path("vendor") / name / "lib.vyn").exists() else ""
        print(f"  {name:15} v{info['version']:8} {info['desc']}{installed}")
    print("\nUsage:")
    print("  vpm add serde          # ajoute une dependance")
    print("  vpm install            # installe vendor/ depuis vyn.toml")
    print("  import serde;          # dans votre code Vyn")
    return 0


def cmd_build(args):
    from vyn.interpreter import run_source
    data = load_manifest()
    entry = data.get("build", {}).get("entry", "src/main.vyn")
    if not Path(entry).exists():
        print(f"Entrée introuvable : {entry}"); return 1
    if args.native:
        from vyn.compiler import compile_file
        name = data.get("package", {}).get("name", "app")
        Path("dist").mkdir(exist_ok=True)
        out = f"dist/{name}" + (".exe" if sys.platform == "win32" else "")
        print(f"✓ Build natif : {compile_file(entry, out)}")
    else:
        code = run_source(Path(entry).read_text(encoding="utf-8"))
        print(f"✓ Exécution interprétée — exit {code}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="vpm")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, nargs in [
        ("init", cmd_init, {"name": ("?", "mon-projet")}),
        ("add", cmd_add, {"name": None, "version": ("?", None)}),
        ("install", cmd_install, {}),
        ("list", cmd_list, {}),
        ("build", cmd_build, {}),
    ]:
        p = sub.add_parser(name)
        if "name" in nargs:
            p.add_argument("name", nargs=nargs["name"][0], default=nargs["name"][1] if nargs["name"][0] == "?" else None)
        if "version" in nargs:
            p.add_argument("version", nargs="?", default=None)
        if name == "build":
            p.add_argument("--native", action="store_true")
        p.set_defaults(func=func)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main())
