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
    "serde": {"version": "1.0.0", "desc": "JSON serialize / deserialize"},
    "collections": {"version": "1.0.0", "desc": "Stack, Queue data structures"},
    "async": {"version": "0.9.0", "desc": "defer_ms, yield_now"},
    "neural": {"version": "0.1.0", "desc": "ReLU hot-swap, sigmoid"},
    "ai": {"version": "1.0.0", "desc": "Train & deploy neural networks"},
    "db": {"version": "1.0.0", "desc": "SQLite database ORM-lite"},
}

PACKAGE_TEMPLATES = {
    "serde": """// Package serde — JSON serialization
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
    "ai": """// Package ai — neural network training
import std.ai;
import std.io;
pub fn version() -> str { return "1.0.0"; }
pub fn create_classifier(name: str) -> str { return ai.model_new(name, 2, 8, 1); }
pub fn train_classifier(model: str, epochs: i32) -> f32 { return ai.train(model, epochs, 0.15); }
pub fn predict_score(model: str, x: f32) -> f32 { return ai.predict(model, x); }
pub fn report(model: str) -> i32 { io.println(ai.loss(model)); return 0; }
pub fn init() -> i32 { return 0; }
""",
    "db": """// Package db — SQLite wrapper
import std.db;
pub fn version() -> str { return "1.0.0"; }
pub fn open(path: str) -> str { return db.open(path); }
pub fn exec(conn: str, sql: str) -> i32 { return db.exec(conn, sql); }
pub fn query(conn: str, sql: str) -> str { return db.query(conn, sql); }
pub fn close(conn: str) -> i32 { return db.close(conn); }
pub fn init() -> i32 { return 0; }
""",
}


def _default_manifest(name: str = "my-project") -> dict[str, Any]:
    return {
        "package": {"name": name, "version": "0.1.0", "authors": ["Vyn Developer"],
                    "description": "Vyn project"},
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
    meta = PACKAGES.get(name, {"version": version, "desc": "Third-party package"})
    lib = vendor / "lib.vyn"
    if not lib.exists():
        template = PACKAGE_TEMPLATES.get(name)
        if template:
            lib.write_text(template, encoding="utf-8")
        else:
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
        print(f"{MANIFEST} already exists."); return 1
    save_manifest(_default_manifest(args.name))
    src = Path("src"); src.mkdir(exist_ok=True)
    main = src / "main.vyn"
    if not main.exists():
        main.write_text('fn main() -> i32 {\n    io.println("Hello Vyn!");\n    return 0;\n}\n')
    print(f"Project initialized — {MANIFEST}"); return 0


def cmd_add(args):
    data = load_manifest()
    ver = args.version or PACKAGES.get(args.name, {}).get("version", "1.0.0")
    data.setdefault("dependencies", {})[args.name] = ver
    save_manifest(data)
    _install_pkg(args.name, ver)
    print(f"Added {args.name}@{ver}"); return 0


def cmd_install(args):
    data = load_manifest()
    deps = data.get("dependencies", {})
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    reg = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    for name, ver in deps.items():
        _install_pkg(name, ver)
        reg[name] = ver
        print(f"  installed {name}@{ver}")
    REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    print(f"Installed {len(deps)} package(s)"); return 0


def cmd_list(args):
    print("Available VPM packages:\n")
    for name, info in PACKAGES.items():
        installed = " [installed]" if (Path("vendor") / name / "lib.vyn").exists() else ""
        print(f"  {name:15} v{info['version']:8} {info['desc']}{installed}")
    print("\nUsage:")
    print("  vpm add serde       # add dependency to vyn.toml")
    print("  vpm install         # install all deps to vendor/")
    print("  vpm info ai         # show package API")
    print("  import serde;       # use in Vyn code")
    return 0


def cmd_info(args):
    info = PACKAGES.get(args.name)
    if not info:
        print(f"Unknown package: {args.name}")
        print("Run: vpm list")
        return 1
    print(f"Package : {args.name}")
    print(f"Version : {info['version']}")
    print(f"About   : {info['desc']}")
    lib = Path("vendor") / args.name / "lib.vyn"
    if lib.exists():
        print(f"Status  : installed at vendor/{args.name}/")
        print("\n--- lib.vyn ---")
        print(lib.read_text(encoding="utf-8"))
    else:
        print("Status  : not installed — run: vpm add", args.name)
    return 0


def cmd_build(args):
    from vyn.interpreter import run_source
    data = load_manifest()
    entry = data.get("build", {}).get("entry", "src/main.vyn")
    if not Path(entry).exists():
        print(f"Entry not found: {entry}"); return 1
    if args.native:
        from vyn.compiler import compile_file
        name = data.get("package", {}).get("name", "app")
        Path("dist").mkdir(exist_ok=True)
        out = f"dist/{name}" + (".exe" if sys.platform == "win32" else "")
        print(f"Native build: {compile_file(entry, out)}")
    else:
        code = run_source(Path(entry).read_text(encoding="utf-8"))
        print(f"Interpreted run — exit {code}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="vpm",
        description="Vyn Package Manager — reusable libraries for your project",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a new Vyn project")
    p_init.add_argument("name", nargs="?", default="my-project")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="Add a package dependency")
    p_add.add_argument("name")
    p_add.add_argument("version", nargs="?", default=None)
    p_add.set_defaults(func=cmd_add)

    p_install = sub.add_parser("install", help="Install dependencies from vyn.toml")
    p_install.set_defaults(func=cmd_install)

    p_list = sub.add_parser("list", help="List available packages")
    p_list.set_defaults(func=cmd_list)

    p_info = sub.add_parser("info", help="Show package details")
    p_info.add_argument("name")
    p_info.set_defaults(func=cmd_info)

    p_build = sub.add_parser("build", help="Build and run project entry")
    p_build.add_argument("--native", action="store_true", help="LLVM native build")
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
