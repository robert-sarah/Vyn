"""Autocompletion data for VynStudio — généré depuis le Language Server."""
from __future__ import annotations

from vynstudio.language_server import SERVER

KEYWORDS = SERVER.KEYWORDS

SNIPPETS = {
    "fn": "fn name(params) -> i32 {\n    \n}",
    "main": "fn main() -> i32 {\n    \n    return 0;\n}",
    "hotfn": "hot fn name(val: f32) -> f32 {\n    return val;\n}",
    "struct": "struct Name {\n    mut field: i32;\n}",
    "enum": "enum Name {\n    VariantA,\n    VariantB,\n}",
    "impl": "impl Name {\n    fn method(self) -> void {\n        \n    }\n}",
    "loop": "loop {\n    \n}",
    "loopin": "loop val in arr {\n    \n}",
    "if": "if cond {\n    \n} else {\n    \n}",
    "ifelse": "if cond {\n    \n} else if other {\n    \n} else {\n    \n}",
    "match": "match value {\n    case 0:\n        return 0;\n    case 1:\n        return 1;\n    default:\n        return -1;\n}",
    "try": "try {\n    \n} catch (e) {\n    \n}",
    "trycatch": "try {\n    risky();\n} catch err {\n    log.error(err);\n}",
    "throw": "throw 0;",
    "profile": "@[profile]\nfn name() -> void {\n    \n}",
    "let": "let name: i32 = 0;",
    "letmut": "let mut name: f32 = 0.0;",
    "import": "import std.io;",
    "use": "use std.io.println;",
    "extern": 'extern "C" {\n    fn name(id: i32) -> i32;\n}',
    "gui": "import std.gui;\n\nfn main() -> i32 {\n    gui.window(\"App\", 480, 320);\n    gui.run();\n    return 0;\n}",
    "server": "import std.server;\nimport std.html;\n\nfn home() -> str {\n    return html.page(\"App\", html.body(html.h1(\"Hello\")));\n}\n\nfn main() -> i32 {\n    server.route(\"/\", \"home\");\n    server.listen_async(8080);\n    return 0;\n}",
    "html": "import std.html;\nimport std.css;\n\nlet page = html.page(\"Title\", html.body(html.h1(\"Content\")));",
    "package": "import serde;\n\nfn main() -> i32 {\n    let json = serialize(42);\n    return 0;\n}",
    "aitrain": "import std.ai;\nimport ai;\n\nfn main() -> i32 {\n    let model = create_classifier(\"demo\");\n    train_classifier(model, 100);\n    return 0;\n}",
    "dbdemo": "import std.db;\n\nfn main() -> i32 {\n    let conn = db.open(\"dist/app.db\");\n    db.exec(conn, \"CREATE TABLE IF NOT EXISTS t (id INTEGER)\");\n    db.close(conn);\n    return 0;\n}",
    "mldemo": "import std.numpy;\nimport std.torch;\nimport std.sklearn;\nimport std.plot;\n\nfn main() -> i32 {\n    let data = numpy.array([1.0, 2.0, 3.0]);\n    io.println(numpy.mean(data));\n    let model = sklearn.fit_linear([1.0,2.0,3.0], [2.0,4.0,6.0]);\n    io.println(sklearn.predict(model, 4.0));\n    return 0;\n}",
}

# Tous les symboles std.* depuis le Language Server
STD: list[str] = []
for mod, syms in SERVER._modules.items():
    for s in syms:
        STD.append(f"{mod}.{s.name}")

# Packages vendor
for pkg, syms in SERVER._vendor.items():
    for s in syms:
        STD.append(s.name)

IMPORTS = [f"std.{m}" for m in SERVER.module_names()] + list(SERVER._vendor.keys())

PACKAGES = list(SERVER._vendor.keys())

ALL_COMPLETIONS = sorted(set(
    KEYWORDS + STD + IMPORTS + PACKAGES +
    [f"import {m};" for m in IMPORTS + PACKAGES] +
    [f"use {m};" for m in IMPORTS] +
    list(SNIPPETS.keys())
))
