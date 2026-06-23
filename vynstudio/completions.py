"""Données d'autocomplétion VynStudio."""
KEYWORDS = [
    "let", "mut", "const", "type", "struct", "enum", "void",
    "i32", "f32", "bool", "str", "own", "ref", "fn", "pub",
    "extern", "return", "impl", "trait", "self", "hot",
    "if", "else", "loop", "break", "continue", "match", "case",
    "async", "sync", "task", "import", "mod", "use",
    "try", "catch", "throw", "in", "true", "false", "and", "or", "not",
]

SNIPPETS = {
    "fn": "fn name(params) -> i32 {\n    \n}",
    "main": "fn main() -> i32 {\n    \n    return 0;\n}",
    "hotfn": "hot fn name(val: f32) -> f32 {\n    return val;\n}",
    "struct": "struct Name {\n    mut field: i32;\n}",
    "impl": "impl Name {\n    fn method(self) -> void {\n        \n    }\n}",
    "loop": "loop {\n    \n}",
    "loopin": "loop val in arr {\n    \n}",
    "if": "if (cond) {\n    \n}",
    "profile": "@[profile]\nfn name() -> void {\n    \n}",
    "let": "let name: i32 = 0;",
    "letmut": "let mut name: f32 = 0.0;",
    "import": "import std.io;",
    "use": "use std.io.println;",
    "extern": 'extern "C" {\n    fn name(id: i32) -> i32;\n}',
    "gui": "import std.gui;\n\nfn main() -> i32 {\n    gui.window(\"App\", 480, 320);\n    gui.run();\n    return 0;\n}",
    "server": "import std.server;\nimport std.html;\n\nfn home() -> str {\n    return html.page(\"App\", html.body(html.h1(\"Hello\")));\n}\n\nfn main() -> i32 {\n    server.route(\"/\", \"home\");\n    server.listen(8080);\n    return 0;\n}",
    "html": "import std.html;\nimport std.css;\n\nlet page = html.page(\"Titre\", html.body(html.h1(\"Contenu\")));",
    "package": "import serde;\n\nfn main() -> i32 {\n    let json = serialize(42);\n    return 0;\n}",
}

STD = [
    "io.print", "io.println", "sys.sleep",
    "math.clamp", "math.lerp", "math.abs", "math.sqrt",
    "gui.window", "gui.label", "gui.button", "gui.alert", "gui.run",
    "log.info", "log.error", "log.warn", "log.debug",
    "vec.new", "vec.push", "vec.len", "vec.get", "vec.set",
    "rand.seed", "rand.next_f32", "rand.next_i32",
    "hash.fnv1a", "hash.md5", "array.len", "array.sum_f32", "array.push",
    "thread.sleep_ms", "crypto.sha256",
    "str.len", "str.upper", "str.lower", "str.trim", "str.contains", "str.replace",
    "mem.size_of", "time.now_ms", "time.now_sec", "time.format",
    "fs.exists", "fs.read", "fs.write", "fs.remove", "fs.list_dir",
    "net.ping", "net.resolve", "net.get", "net.post",
    "http.get", "http.post", "http.ok",
    "server.route", "server.listen", "server.listen_async", "server.serve_static",
    "html.page", "html.h1", "html.h2", "html.p", "html.div", "html.a", "html.escape",
    "css.rule", "css.class", "css.stylesheet",
    "json.parse", "json.stringify", "json.parse_int",
    "sync.yield_task",
]

IMPORTS = [
    "std.io", "std.sys", "std.math", "std.str", "std.mem", "std.time",
    "std.fs", "std.net", "std.http", "std.server", "std.html", "std.css",
    "std.sync", "std.json", "std.gui", "std.log",
    "std.vec", "std.rand", "std.hash", "std.array", "std.thread", "std.crypto",
]

PACKAGES = ["serde", "collections", "async", "neural", "web"]

ALL_COMPLETIONS = sorted(set(
    KEYWORDS + STD + IMPORTS + PACKAGES +
    [f"import {m};" for m in IMPORTS + PACKAGES] +
    [f"use {m};" for m in IMPORTS] +
    list(SNIPPETS.keys())
))
