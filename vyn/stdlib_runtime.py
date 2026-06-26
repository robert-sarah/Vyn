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
_threads: Dict[int, threading.Thread] = {}
_thread_counter = 0


def _thread_next_id() -> int:
    global _thread_counter
    _thread_counter += 1
    return _thread_counter


def _fnv1a_hash(data: str) -> int:
    h = 2166136261
    for byte in str(data).encode("utf-8"):
        h ^= byte
        h = (h * 16777619) & 0xFFFFFFFF
    return h if h < 0x80000000 else h - 0x100000000


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
            return _fnv1a_hash(str(args[0]))
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
        if method in ("yield_task", "sleep"):
            time.sleep(float(args[0]) / 1000.0 if args else 0.001)
            return 0

    if mod == "thread":
        if method == "spawn":
            fn_name = str(args[0]) if args else ""
            handle = _thread_next_id()

            def _run():
                if interpreter and fn_name in interpreter.functions:
                    interpreter._call_fn(interpreter.functions[fn_name], [])

            t = threading.Thread(target=_run, daemon=True)
            _threads[handle] = t
            t.start()
            return handle
        if method == "join":
            handle = int(args[0]) if args else 0
            t = _threads.pop(handle, None)
            if t:
                t.join(timeout=30.0)
            return 0
        if method == "sleep_ms":
            time.sleep(int(args[0]) / 1000.0)
            return 0

    # ── hashmap ───────────────────────────────────────────────────────────────
    if mod == "hashmap":
        if method == "new":
            return {}
        if method == "with_capacity":
            return {}
        m = args[0] if args and isinstance(args[0], dict) else {}
        if method == "insert" or method == "set":
            if len(args) >= 3:
                m[args[1]] = args[2]
            return 0
        if method == "insert_str":
            if len(args) >= 3:
                m[args[1]] = str(args[2])
            return 0
        if method == "insert_f32":
            if len(args) >= 3:
                m[args[1]] = float(args[2])
            return 0
        if method == "insert_bool":
            if len(args) >= 3:
                m[args[1]] = bool(args[2])
            return 0
        if method == "get":
            key = args[1] if len(args) > 1 else None
            if key in m:
                return {"__type__": "Option", "__tag__": "Some", "__value__": m[key]}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "get_str":
            return str(m.get(args[1], "")) if len(args) > 1 else ""
        if method == "get_f32":
            return float(m.get(args[1], 0.0)) if len(args) > 1 else 0.0
        if method == "get_or":
            key = args[1] if len(args) > 1 else None
            default = args[2] if len(args) > 2 else 0
            return m.get(key, default)
        if method == "get_or_str":
            key = args[1] if len(args) > 1 else None
            default = args[2] if len(args) > 2 else ""
            return m.get(key, default)
        if method == "get_or_insert":
            key = args[1] if len(args) > 1 else None
            default = args[2] if len(args) > 2 else 0
            if key not in m:
                m[key] = default
            return m.get(key, default)
        if method == "remove":
            key = args[1] if len(args) > 1 else None
            existed = key in m
            if existed:
                del m[key]
            return existed
        if method == "remove_entry":
            key = args[1] if len(args) > 1 else None
            return m.pop(key, 0)
        if method == "contains":
            key = args[1] if len(args) > 1 else None
            return key in m
        if method == "contains_value":
            val = args[1] if len(args) > 1 else None
            return val in m.values()
        if method == "len":
            return len(m)
        if method == "is_empty":
            return len(m) == 0
        if method == "keys":
            return list(m.keys())
        if method == "values":
            return list(m.values())
        if method == "entries":
            return [[k, v] for k, v in m.items()]
        if method == "key_at":
            idx = int(args[1]) if len(args) > 1 else 0
            ks = list(m.keys())
            return ks[idx] if 0 <= idx < len(ks) else ""
        if method == "value_at":
            idx = int(args[1]) if len(args) > 1 else 0
            vs = list(m.values())
            return vs[idx] if 0 <= idx < len(vs) else 0
        if method == "clear":
            m.clear()
            return 0
        if method == "merge":
            src = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            m.update(src)
            return 0
        if method == "merge_copy":
            src = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            result = dict(m)
            result.update(src)
            return result
        if method == "clone":
            return dict(m)
        if method == "to_json":
            try:
                return json.dumps(m)
            except Exception:
                return "{}"
        if method == "from_json":
            try:
                return json.loads(str(args[0]))
            except Exception:
                return {}
        if method == "sum_values":
            try:
                return sum(v for v in m.values() if isinstance(v, (int, float)))
            except Exception:
                return 0
        if method == "min_value":
            try:
                nums = [v for v in m.values() if isinstance(v, (int, float))]
                return min(nums) if nums else 0
            except Exception:
                return 0
        if method == "max_value":
            try:
                nums = [v for v in m.values() if isinstance(v, (int, float))]
                return max(nums) if nums else 0
            except Exception:
                return 0
        if method == "equals":
            other = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            return m == other
        if method == "diff_keys":
            other = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            return [k for k in m if k not in other]
        if method == "intersect_keys":
            other = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            return [k for k in m if k in other]
        if method == "to_str":
            try:
                return json.dumps(m)
            except Exception:
                return str(m)
        if method == "debug_print":
            try:
                print(json.dumps(m, indent=2))
            except Exception:
                print(str(m))
            return 0
        if method == "append":
            key = args[1] if len(args) > 1 else None
            val = args[2] if len(args) > 2 else 0
            if key not in m:
                m[key] = []
            if isinstance(m[key], list):
                m[key].append(val)
            return 0
        if method == "get_list":
            key = args[1] if len(args) > 1 else None
            return m.get(key, [])
        if method == "get_nested":
            k1 = args[1] if len(args) > 1 else None
            k2 = args[2] if len(args) > 2 else None
            inner = m.get(k1, {})
            if isinstance(inner, dict):
                return inner.get(k2, 0)
            return 0
        if method == "insert_nested":
            k1 = args[1] if len(args) > 1 else None
            k2 = args[2] if len(args) > 2 else None
            val = args[3] if len(args) > 3 else 0
            if k1 not in m:
                m[k1] = {}
            if isinstance(m[k1], dict):
                m[k1][k2] = val
            return 0
        if method == "version":
            return "std.hashmap 1.0.0"
        if method == "init":
            return 0

    # ── option ────────────────────────────────────────────────────────────────
    if mod == "option":
        def _is_some(v):
            if isinstance(v, dict) and v.get("__type__") == "Option":
                return v.get("__tag__") == "Some"
            return v is not None and v != 0

        def _inner(v):
            if isinstance(v, dict) and v.get("__type__") == "Option":
                return v.get("__value__")
            return v

        opt = args[0] if args else None
        if method == "some":
            val = args[0] if args else None
            return {"__type__": "Option", "__tag__": "Some", "__value__": val}
        if method == "none":
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "is_some":
            return _is_some(opt)
        if method == "is_none":
            return not _is_some(opt)
        if method == "unwrap":
            if not _is_some(opt):
                raise RuntimeError("unwrap() called on None")
            return _inner(opt)
        if method == "unwrap_or":
            default = args[1] if len(args) > 1 else 0
            return _inner(opt) if _is_some(opt) else default
        if method == "expect":
            msg = str(args[1]) if len(args) > 1 else "expect() on None"
            if not _is_some(opt):
                raise RuntimeError(msg)
            return _inner(opt)
        if method == "flatten":
            return _inner(opt) if _is_some(opt) else opt
        if method == "or_else":
            other = args[1] if len(args) > 1 else None
            return opt if _is_some(opt) else other
        if method == "contains":
            val = args[1] if len(args) > 1 else None
            return _is_some(opt) and _inner(opt) == val
        if method == "map":
            if not _is_some(opt):
                return opt
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    mapped = interpreter._call_closure(fn, [_inner(opt)])
                    return {"__type__": "Option", "__tag__": "Some", "__value__": mapped}
            return opt
        if method == "and_then":
            if not _is_some(opt):
                return opt
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    return interpreter._call_closure(fn, [_inner(opt)])
            return opt
        if method == "filter":
            if not _is_some(opt):
                return opt
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    keep = interpreter._call_closure(fn, [_inner(opt)])
                    if not keep:
                        return {"__type__": "Option", "__tag__": "None", "__value__": None}
            return opt
        if method == "version":
            return "std.option 1.0.0"
        if method == "init":
            return 0

    # ── result ────────────────────────────────────────────────────────────────
    if mod == "result":
        def _is_ok(v):
            if isinstance(v, dict) and v.get("__type__") == "Result":
                return v.get("__tag__") == "Ok"
            return isinstance(v, (int, float)) and v >= 0

        def _ok_val(v):
            if isinstance(v, dict) and v.get("__type__") == "Result":
                return v.get("__value__")
            return v

        def _err_val(v):
            if isinstance(v, dict) and v.get("__type__") == "Result":
                return v.get("__value__")
            return None

        res = args[0] if args else None
        if method == "ok":
            val = args[0] if args else None
            return {"__type__": "Result", "__tag__": "Ok", "__value__": val}
        if method == "err":
            val = args[0] if args else None
            return {"__type__": "Result", "__tag__": "Err", "__value__": val}
        if method == "is_ok":
            return _is_ok(res)
        if method == "is_err":
            return not _is_ok(res)
        if method == "unwrap":
            if not _is_ok(res):
                raise RuntimeError(f"unwrap() on Err: {_err_val(res)}")
            return _ok_val(res)
        if method == "unwrap_err":
            if _is_ok(res):
                raise RuntimeError("unwrap_err() on Ok value")
            return _err_val(res)
        if method == "unwrap_or":
            default = args[1] if len(args) > 1 else 0
            return _ok_val(res) if _is_ok(res) else default
        if method == "expect":
            msg = str(args[1]) if len(args) > 1 else "expect() on Err"
            if not _is_ok(res):
                raise RuntimeError(msg)
            return _ok_val(res)
        if method == "expect_err":
            msg = str(args[1]) if len(args) > 1 else "expect_err() on Ok"
            if _is_ok(res):
                raise RuntimeError(msg)
            return _err_val(res)
        if method == "map":
            if not _is_ok(res):
                return res
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    mapped = interpreter._call_closure(fn, [_ok_val(res)])
                    return {"__type__": "Result", "__tag__": "Ok", "__value__": mapped}
            return res
        if method == "map_err":
            if _is_ok(res):
                return res
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    mapped = interpreter._call_closure(fn, [_err_val(res)])
                    return {"__type__": "Result", "__tag__": "Err", "__value__": mapped}
            return res
        if method == "and_then":
            if not _is_ok(res):
                return res
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    return interpreter._call_closure(fn, [_ok_val(res)])
            return res
        if method == "or_else":
            if _is_ok(res):
                return res
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure":
                if interpreter:
                    return interpreter._call_closure(fn, [_err_val(res)])
            return res
        if method == "ok_to_option":
            if _is_ok(res):
                return {"__type__": "Option", "__tag__": "Some", "__value__": _ok_val(res)}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "err_to_option":
            if not _is_ok(res):
                return {"__type__": "Option", "__tag__": "Some", "__value__": _err_val(res)}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "version":
            return "std.result 1.0.0"
        if method == "init":
            return 0

    # ── iter ──────────────────────────────────────────────────────────────────
    if mod == "iter":
        iterable = args[0] if args else []
        # Normalize to list
        if isinstance(iterable, dict):
            if iterable.get("__type__") == "Range":
                start = iterable.get("__start__", 0)
                end   = iterable.get("__end__", 0)
                inc   = iterable.get("__inclusive__", False)
                iterable = list(range(start, end + (1 if inc else 0)))
            else:
                iterable = list(iterable.values())
        elif not isinstance(iterable, list):
            iterable = list(iterable) if hasattr(iterable, '__iter__') else []

        if method == "map":
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                return [interpreter._call_closure(fn, [x]) for x in iterable]
            return iterable
        if method == "filter":
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                return [x for x in iterable if interpreter._truthy(interpreter._call_closure(fn, [x]))]
            return iterable
        if method == "fold" or method == "reduce":
            init = args[1] if len(args) > 1 else 0
            fn   = args[2] if len(args) > 2 else None
            acc  = init
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                for x in iterable:
                    acc = interpreter._call_closure(fn, [acc, x])
            return acc
        if method == "collect":
            return list(iterable)
        if method == "enumerate":
            return [[i, v] for i, v in enumerate(iterable)]
        if method == "zip":
            other = args[1] if len(args) > 1 else []
            if not isinstance(other, list):
                other = list(other)
            return [[a, b] for a, b in zip(iterable, other)]
        if method == "take":
            n = int(args[1]) if len(args) > 1 else 0
            return iterable[:n]
        if method == "skip":
            n = int(args[1]) if len(args) > 1 else 0
            return iterable[n:]
        if method == "chain":
            other = args[1] if len(args) > 1 else []
            if not isinstance(other, list):
                other = list(other)
            return list(iterable) + other
        if method == "flat_map":
            fn = args[1] if len(args) > 1 else None
            result = []
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                for x in iterable:
                    sub = interpreter._call_closure(fn, [x])
                    if isinstance(sub, list):
                        result.extend(sub)
                    else:
                        result.append(sub)
            return result
        if method == "any":
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                return any(interpreter._truthy(interpreter._call_closure(fn, [x])) for x in iterable)
            return len(iterable) > 0
        if method == "all":
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                return all(interpreter._truthy(interpreter._call_closure(fn, [x])) for x in iterable)
            return True
        if method == "count":
            return len(iterable)
        if method == "find":
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                for x in iterable:
                    if interpreter._truthy(interpreter._call_closure(fn, [x])):
                        return {"__type__": "Option", "__tag__": "Some", "__value__": x}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "position":
            fn = args[1] if len(args) > 1 else None
            if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                for i, x in enumerate(iterable):
                    if interpreter._truthy(interpreter._call_closure(fn, [x])):
                        return {"__type__": "Option", "__tag__": "Some", "__value__": i}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "min":
            if not iterable:
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
            try:
                return {"__type__": "Option", "__tag__": "Some", "__value__": min(iterable)}
            except Exception:
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "max":
            if not iterable:
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
            try:
                return {"__type__": "Option", "__tag__": "Some", "__value__": max(iterable)}
            except Exception:
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "sum":
            try:
                return sum(iterable)
            except Exception:
                return 0
        if method == "product":
            result = 1
            for x in iterable:
                result *= x
            return result
        if method == "last":
            if not iterable:
                return {"__type__": "Option", "__tag__": "None", "__value__": None}
            return {"__type__": "Option", "__tag__": "Some", "__value__": iterable[-1]}
        if method == "nth":
            n = int(args[1]) if len(args) > 1 else 0
            if 0 <= n < len(iterable):
                return {"__type__": "Option", "__tag__": "Some", "__value__": iterable[n]}
            return {"__type__": "Option", "__tag__": "None", "__value__": None}
        if method == "step_by":
            n = int(args[1]) if len(args) > 1 else 1
            return iterable[::n]
        if method == "cycle":
            n = int(args[1]) if len(args) > 1 else 1
            return list(iterable) * n
        if method == "peekable":
            return list(iterable)
        if method == "reverse":
            return list(reversed(iterable))
        if method == "sort":
            try:
                return sorted(iterable)
            except Exception:
                return list(iterable)
        if method == "sort_by":
            fn = args[1] if len(args) > 1 else None
            try:
                if fn and isinstance(fn, dict) and fn.get("__type__") == "Closure" and interpreter:
                    return sorted(iterable, key=lambda x: interpreter._call_closure(fn, [x]))
                return sorted(iterable)
            except Exception:
                return list(iterable)
        if method == "dedup":
            seen = []
            result = []
            for x in iterable:
                if x not in seen:
                    seen.append(x)
                    result.append(x)
            return result
        if method == "flatten":
            result = []
            for x in iterable:
                if isinstance(x, list):
                    result.extend(x)
                else:
                    result.append(x)
            return result
        if method == "version":
            return "std.iter 1.0.0"
        if method == "init":
            return 0

    return _MISSING
