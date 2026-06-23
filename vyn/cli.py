"""CLI officiel Vyn."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from vyn.compiler import VynCompiler, compile_file
from vyn.interpreter import run_source
from vyn.hot_reload import run_with_hot_reload
from vyn.parser import Parser
from vyn.lexer import Lexer


def cmd_build(args):
    out = compile_file(args.file, args.output)
    print(f"✓ Binaire : {out}")
    return 0


def cmd_run(args):
    source = Path(args.file).read_text(encoding="utf-8")
    if args.native and shutil.which("clang"):
        return VynCompiler().run_jit(source)
    code = run_source(source)
    print(f"exit code: {code}")
    return code


def cmd_hot(args):
    run_with_hot_reload(args.file)
    return 0


def cmd_lex(args):
    for tok in Lexer(Path(args.file).read_text(encoding="utf-8")).tokenize():
        print(f"{tok.kind.name:12} {tok.value!r:20} @ {tok.line}:{tok.col}")
    return 0


def cmd_parse(args):
    from vyn.prelude import inject_prelude
    prog = Parser(inject_prelude(Path(args.file).read_text(encoding="utf-8"))).parse()
    print(f"Functions: {[f.name for f in prog.functions]}")
    print(f"Hot: {[f.name for f in prog.functions if f.is_hot]}")
    print(f"Profiled: {[f.name for f in prog.functions if any(a.name=='profile' for a in f.attributes)]}")
    return 0


def cmd_ir(args):
    from vyn.codegen import compile_to_ir
    from vyn.prelude import inject_prelude
    ir_code, _ = compile_to_ir(inject_prelude(Path(args.file).read_text(encoding="utf-8")))
    out = args.output or Path(args.file).with_suffix(".ll")
    Path(out).write_text(ir_code, encoding="utf-8")
    print(f"✓ IR : {out}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="vync")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_ in [
        ("build", cmd_build, "Compiler en binaire"),
        ("run", cmd_run, "Exécuter (interpréteur par défaut)"),
        ("hot", cmd_hot, "Hot-reload"),
        ("lex", cmd_lex, "Tokens"),
        ("parse", cmd_parse, "AST"),
        ("ir", cmd_ir, "LLVM IR"),
    ]:
        p = sub.add_parser(name, help=help_)
        p.add_argument("file")
        if name == "build":
            p.add_argument("-o", "--output")
        if name == "ir":
            p.add_argument("-o", "--output")
        if name == "run":
            p.add_argument("--native", action="store_true", help="Forcer compilation LLVM")
        p.set_defaults(func=func)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
