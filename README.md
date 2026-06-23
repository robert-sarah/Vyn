# Vyn — Langage système haute performance

**Philosophie :** Transparence totale, performance native, web intégré, packages réutilisables.

## Installation

```bash
pip install -r requirements.txt
```

## Commandes

```bash
# Exécuter (interpréteur intégré)
python -m vyn.cli run examples/web_server.vyn
python -m vyn.cli run examples/html_page.vyn
python -m vyn.cli run examples/package_demo.vyn
python -m vyn.cli run examples/gui_app.vyn

# IDE VynStudio
python -m vynstudio.main

# Packages VPM (comme npm / cargo)
python -m vpm list
python -m vpm add serde
python -m vpm add web
python -m vpm install
python -m vpm build
```

## Packages VPM — à quoi ça sert ?

Les **packages** sont des bibliothèques réutilisables (comme `npm` ou `pip`) :

| Package | Rôle |
|---------|------|
| `serde` | Sérialisation JSON `serialize()` / `deserialize()` |
| `collections` | Stack, Queue |
| `neural` | ReLU hot-swap, sigmoid |
| `async` | `defer_ms`, `yield_now` |
| `web` | Helpers page HTML |

```vyn
import serde;
let json = serialize(42);  // "42"
```

Les dépendances dans `vyn.toml` sont **auto-chargées** à l'exécution :

```toml
[dependencies]
serde = "1.0"
collections = "1.0"
```

## Bibliothèque standard (22 modules)

| Module | Fonctions |
|--------|-----------|
| `std.io` | print, println |
| `std.sys` | sleep |
| `std.math` | abs, sqrt, clamp, lerp |
| `std.str` | len, upper, lower, trim, contains, replace |
| `std.fs` | exists, read, write, remove, list_dir |
| `std.net` | ping, resolve, get, post |
| `std.http` | get, post, ok, not_found |
| `std.server` | route, listen, serve_static |
| `std.html` | page, h1, p, div, a, escape, style |
| `std.css` | rule, class, stylesheet |
| `std.json` | parse, stringify, parse_int |
| `std.time` | now_ms, now_sec, format |
| `std.log` | info, warn, error, debug |
| `std.gui` | window, label, button, run (tkinter) |
| `std.vec` | new, push, len, get, set |
| `std.rand` | seed, next_f32, next_i32 |
| `std.hash` | fnv1a, md5 |
| `std.crypto` | sha256 |
| `std.array` | len, sum_f32, fill, push |
| `std.thread` | sleep_ms |
| `std.sync` | yield_task |
| `std.mem` | size_of |

## Serveur web intégré

```vyn
import std.server;
import std.html;

fn home() -> str {
    return html.page("Accueil", html.body(html.h1("Hello Vyn")));
}

fn main() -> i32 {
    server.route("/", "home");
    server.listen(8080);
    return 0;
}
```

## Architecture

| Module | Rôle |
|--------|------|
| `vyn/lexer` | Analyse lexicale |
| `vyn/parser` | Parser (`hot fn`, `@[profile]`, top-level stmts) |
| `vyn/semantic` | Typage & ownership |
| `vyn/interpreter` | Exécution Python |
| `vyn/stdlib_runtime` | Runtime natif fs/net/html/css/server |
| `vyn/codegen` | LLVM IR |
| `vynstudio/` | IDE PyQt5 |
| `stdlib/std/` | API Vyn |
| `vendor/` | Packages VPM |

## Exemples

- `examples/web_server.vyn` — serveur HTTP + HTML + CSS
- `examples/html_page.vyn` — génération HTML fichier
- `examples/package_demo.vyn` — packages VPM
- `examples/gui_app.vyn` — interface tkinter
- `examples/profile.vyn` — profilage `@[profile]`
- `examples/hot_swap.vyn` — `hot fn`
- `examples/ffi.vyn` — FFI C
