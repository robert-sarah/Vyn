"""Runtime natif Python pour la bibliotheque standard Vyn."""
from __future__ import annotations

import hashlib
import html as html_lib
import json
import random
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from vyn.interpreter import Interpreter

_db_conns: Dict[str, sqlite3.Connection] = {}
_db_counter = 0


def _db_new_id() -> str:
    global _db_counter
    _db_counter += 1
    return f"db_{_db_counter}"


# --- HTTP Server ---

class _VynHttpServer:
    def __init__(self):
        self.routes: Dict[str, str] = {}
        self.static_dir: Optional[str] = None
        self.port: int = 8080
        self._interpreter: Optional["Interpreter"] = None
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def bind(self, interpreter: "Interpreter") -> None:
        self._interpreter = interpreter

    def route(self, path: str, handler: str) -> int:
        self.routes[path if path.startswith("/") else f"/{path}"] = handler
        return 0

    def static(self, directory: str) -> int:
        self.static_dir = directory
        return 0

    def listen(self, port: int) -> int:
        self.port = int(port)
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                print(f"[server] {self.address_string()} {fmt % args}")

            def _respond(self, code: int, body: str, ctype: str = "text/html; charset=utf-8"):
                data = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Server", "Vyn/1.0")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = self.path.split("?")[0]
                if server_ref.static_dir and path.startswith("/static/"):
                    rel = path[len("/static/"):]
                    fp = Path(server_ref.static_dir) / rel
                    if fp.is_file():
                        ext = fp.suffix.lower()
                        ct = {
                            ".html": "text/html", ".css": "text/css",
                            ".js": "application/javascript", ".json": "application/json",
                            ".png": "image/png", ".jpg": "image/jpeg",
                        }.get(ext, "application/octet-stream")
                        self._respond(200, fp.read_text(encoding="utf-8", errors="replace"), ct)
                        return
                handler = server_ref.routes.get(path) or server_ref.routes.get("/")
                if handler and server_ref._interpreter:
                    fn = server_ref._interpreter.functions.get(handler)
                    if fn:
                        try:
                            result = server_ref._interpreter._call_fn(fn, [])
                            body = str(result if result is not None else "")
                            self._respond(200, body)
                            return
                        except Exception as e:
                            self._respond(500, html_lib.escape(str(e)))
                            return
                self._respond(404, html_page("404", html_body(html_h1("Page introuvable"))))

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
                handler = server_ref.routes.get(self.path.split("?")[0] + "#POST")
                if not handler:
                    handler = server_ref.routes.get(self.path.split("?")[0])
                if handler and server_ref._interpreter:
                    fn = server_ref._interpreter.functions.get(handler)
                    if fn:
                        try:
                            result = server_ref._interpreter._call_fn(fn, [body])
                            self._respond(200, str(result if result is not None else ""))
                            return
                        except Exception as e:
                            self._respond(500, html_lib.escape(str(e)))
                            return
                self._respond(405, "Method Not Allowed")

        self._httpd = HTTPServer(("0.0.0.0", self.port), Handler)
        print(f"[server] Ecoute sur http://127.0.0.1:{self.port}")
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self._httpd.server_close()
        return 0

    def listen_async(self, port: int) -> int:
        self.port = int(port)
        self._thread = threading.Thread(target=self.listen, args=(port,), daemon=True)
        self._thread.start()
        time.sleep(0.05)
        return 0

    def stop(self) -> int:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None
        return 0


_http_server = _VynHttpServer()


def get_http_server() -> _VynHttpServer:
    return _http_server


def reset_http_server() -> None:
    global _http_server
    if _http_server._httpd:
        try:
            _http_server._httpd.shutdown()
        except Exception:
            pass
    _http_server = _VynHttpServer()


# --- HTML helpers ---

def html_escape(s: str) -> str:
    return html_lib.escape(str(s))


def html_tag(name: str, content: str, attrs: str = "") -> str:
    attr = f" {attrs}" if attrs else ""
    void = name in ("meta", "link", "br", "hr", "input", "img")
    if void:
        return f"<{name}{attr} />"
    return f"<{name}{attr}>{content}</{name}>"


def html_doc(*parts: str) -> str:
    return "<!DOCTYPE html>\n" + "".join(parts)


def html_head(*parts: str) -> str:
    return html_tag("head", "".join(parts))


def html_body(*parts: str) -> str:
    return html_tag("body", "".join(parts))


def html_title(text: str) -> str:
    return html_tag("title", html_escape(text))


def html_h1(text: str) -> str:
    return html_tag("h1", html_escape(text))


def html_h2(text: str) -> str:
    return html_tag("h2", html_escape(text))


def html_p(text: str) -> str:
    return html_tag("p", html_escape(text))


def html_div(content: str, class_name: str = "") -> str:
    attrs = f'class="{html_escape(class_name)}"' if class_name else ""
    return html_tag("div", content, attrs)


def html_a(text: str, href: str) -> str:
    return html_tag("a", html_escape(text), f'href="{html_escape(href)}"')


def html_link(css_href: str) -> str:
    return html_tag("link", "", f'rel="stylesheet" href="{html_escape(css_href)}"')


def html_style(css: str) -> str:
    return html_tag("style", css)


def html_script(src: str) -> str:
    return html_tag("script", "", f'src="{html_escape(src)}"')


def html_page(title: str, body: str, css: str = "") -> str:
    head = html_head(html_title(title))
    if css:
        head = html_head(html_title(title), html_style(css))
    return html_doc(html_tag("html", head + body))


# --- CSS helpers ---

def css_rule(selector: str, prop: str, value: str) -> str:
    return f"{selector} {{ {prop}: {value}; }}"


def css_rules(*rules: str) -> str:
    return "\n".join(rules)


def css_class(name: str, prop: str, value: str) -> str:
    return css_rule(f".{name}", prop, value)


def css_id(name: str, prop: str, value: str) -> str:
    return css_rule(f"#{name}", prop, value)


def css_stylesheet(*rules: str) -> str:
    return css_rules(*rules)


# --- Dispatch ---

_MISSING = object()


def dispatch(mod: str, method: str, args: list, interpreter: Optional["Interpreter"] = None) -> Any:
    """Appelle une fonction std.* native. Retourne _MISSING si non gere."""

    if mod == "fs":
        if method == "exists":
            return Path(str(args[0])).exists()
        if method == "read":
            return Path(str(args[0])).read_text(encoding="utf-8")
        if method == "write":
            p = Path(str(args[0]))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(args[1]), encoding="utf-8")
            return 0
        if method == "remove":
            p = Path(str(args[0]))
            if p.is_file():
                p.unlink()
            return 0
        if method == "list_dir":
            return [x.name for x in Path(str(args[0])).iterdir()]

    if mod == "str":
        s = str(args[0]) if args else ""
        if method == "len":
            return len(s)
        if method == "upper":
            return s.upper()
        if method == "lower":
            return s.lower()
        if method == "trim":
            return s.strip()
        if method == "contains":
            return args[1] in s if len(args) > 1 else False
        if method == "replace":
            return s.replace(str(args[1]), str(args[2])) if len(args) > 2 else s
        if method == "split":
            return s.split(str(args[1])) if len(args) > 1 else s.split()

    if mod == "time":
        if method == "now_ms":
            return int(time.time() * 1000)
        if method == "now_sec":
            return int(time.time())
        if method == "format":
            return time.strftime(str(args[0])) if args else time.strftime("%Y-%m-%d")

    if mod == "json":
        if method == "parse":
            return json.loads(str(args[0]))
        if method == "stringify":
            return json.dumps(args[0])
        if method == "parse_int":
            try:
                return int(json.loads(str(args[0])))
            except (json.JSONDecodeError, ValueError):
                return 0

    if mod == "net":
        if method == "ping":
            host = str(args[0]).split("//")[-1].split("/")[0].split(":")[0]
            try:
                socket.gethostbyname(host)
                return 1
            except socket.gaierror:
                return 0
        if method == "resolve":
            try:
                return socket.gethostbyname(str(args[0]))
            except socket.gaierror:
                return "0.0.0.0"
        if method == "get":
            try:
                with urllib.request.urlopen(str(args[0]), timeout=10) as r:
                    return r.read().decode("utf-8", errors="replace")
            except (urllib.error.URLError, TimeoutError):
                return ""
        if method == "post":
            url, data = str(args[0]), str(args[1]).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.read().decode("utf-8", errors="replace")
            except (urllib.error.URLError, TimeoutError):
                return ""

    if mod == "server":
        srv = get_http_server()
        if interpreter:
            srv.bind(interpreter)
        if method == "route":
            return srv.route(str(args[0]), str(args[1]))
        if method == "static" or method == "serve_static":
            return srv.static(str(args[0]))
        if method == "listen":
            return srv.listen(int(args[0]))
        if method == "listen_async":
            return srv.listen_async(int(args[0]))
        if method == "stop":
            return srv.stop()

    if mod == "http":
        if method == "get":
            return dispatch("net", "get", args, interpreter)
        if method == "post":
            return dispatch("net", "post", args, interpreter)
        if method == "ok":
            return str(args[0]) if args else ""
        if method == "not_found":
            return html_page("404", html_body(html_h1("404")))

    if mod == "html":
        m = {
            "escape": lambda: html_escape(str(args[0])),
            "tag": lambda: html_tag(str(args[0]), str(args[1]), str(args[2]) if len(args) > 2 else ""),
            "doc": lambda: html_doc(*[str(a) for a in args]),
            "head": lambda: html_head(*[str(a) for a in args]),
            "body": lambda: html_body(*[str(a) for a in args]),
            "title": lambda: html_title(str(args[0])),
            "h1": lambda: html_h1(str(args[0])),
            "h2": lambda: html_h2(str(args[0])),
            "p": lambda: html_p(str(args[0])),
            "div": lambda: html_div(str(args[0]), str(args[1]) if len(args) > 1 else ""),
            "a": lambda: html_a(str(args[0]), str(args[1])),
            "link": lambda: html_link(str(args[0])),
            "style": lambda: html_style(str(args[0])),
            "page": lambda: html_page(str(args[0]), str(args[1]), str(args[2]) if len(args) > 2 else ""),
        }
        if method in m:
            return m[method]()

    if mod == "css":
        m = {
            "rule": lambda: css_rule(str(args[0]), str(args[1]), str(args[2])),
            "class": lambda: css_class(str(args[0]), str(args[1]), str(args[2])),
            "id": lambda: css_id(str(args[0]), str(args[1]), str(args[2])),
            "stylesheet": lambda: css_stylesheet(*[str(a) for a in args]),
        }
        if method in m:
            return m[method]()

    if mod == "hash":
        if method == "fnv1a":
            h = 2166136261
            for b in str(args[0]).encode("utf-8"):
                h = (h ^ b) * 16777619 & 0xFFFFFFFF
            return h
        if method == "md5":
            return hashlib.md5(str(args[0]).encode()).hexdigest()

    if mod == "crypto":
        if method == "sha256":
            return hashlib.sha256(str(args[0]).encode()).hexdigest()
        if method == "sha256_stub":
            return dispatch("crypto", "sha256", args, interpreter)
        if method == "xor_bytes":
            a, b = int(args[0]), int(args[1])
            return a ^ b

    if mod == "mem":
        sizes = {"i32": 4, "f32": 4, "bool": 1, "str": 8, "void": 0}
        if method == "size_of":
            return sizes.get(str(args[0]), 4)

    if mod == "array":
        arr = args[0] if args else []
        if not isinstance(arr, list):
            arr = []
        if method == "len":
            return len(arr)
        if method == "sum_f32":
            return sum(float(x) for x in arr)
        if method == "fill":
            return [float(args[1])] * int(args[2]) if len(args) > 2 else []
        if method == "push":
            arr = list(arr)
            arr.append(args[1] if len(args) > 1 else 0)
            return arr

    if mod == "vec":
        if method == "new":
            return []
        if method == "push":
            v = list(args[0]) if isinstance(args[0], list) else []
            v.append(args[1] if len(args) > 1 else 0)
            return v
        if method == "len":
            v = args[0] if args else []
            return len(v) if isinstance(v, list) else 0
        if method == "get":
            v = args[0]
            i = int(args[1]) if len(args) > 1 else 0
            return v[i] if isinstance(v, list) and 0 <= i < len(v) else 0
        if method == "set":
            v = list(args[0]) if isinstance(args[0], list) else []
            i = int(args[1]) if len(args) > 1 else 0
            if len(args) > 2:
                while len(v) <= i:
                    v.append(0)
                v[i] = args[2]
            return v

    if mod == "db":
        if method == "open":
            path = str(args[0])
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path)
            cid = _db_new_id()
            _db_conns[cid] = conn
            return cid
        if method == "exec":
            conn = _db_conns.get(str(args[0]))
            if conn:
                conn.execute(str(args[1]))
                conn.commit()
            return 0
        if method == "query":
            conn = _db_conns.get(str(args[0]))
            if not conn:
                return "[]"
            cur = conn.execute(str(args[1]))
            rows = cur.fetchall()
            return json.dumps(rows)
        if method == "close":
            conn = _db_conns.pop(str(args[0]), None)
            if conn:
                conn.close()
            return 0

    if mod == "ai":
        from vyn.ai_runtime import dispatch_ai
        result = dispatch_ai(method, args)
        if result is not None:
            return result

    if mod in ("numpy", "torch", "tensorflow", "cv", "pandas", "sklearn", "plot"):
        from vyn.ml_runtime import dispatch_ml
        result = dispatch_ml(mod, method, args)
        if result is not None:
            return result

    if mod == "math":
        if method == "abs":
            return abs(args[0])
        if method == "sqrt":
            return args[0] ** 0.5
        if method == "clamp":
            return max(args[1], min(args[0], args[2]))
        if method == "lerp":
            return args[0] + (args[1] - args[0]) * args[2]

    if mod == "rand":
        if method == "seed":
            random.seed(int(args[0]))
            return 0
        if method == "next_f32":
            return random.random()
        if method == "next_i32":
            lo = int(args[0]) if args else 0
            hi = int(args[1]) if len(args) > 1 else lo
            return random.randint(lo, hi)

    if mod == "sync":
        if method == "yield_task":
            time.sleep(0.001)
            return 0

    if mod == "thread":
        if method == "sleep_ms":
            time.sleep(int(args[0]) / 1000.0)
            return 0

    return _MISSING
