"""Tests unitaires Vyn."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vyn.ast.nodes import AssignStmt, IfStmt, TryStmt
from vyn.lexer import Lexer, TokenKind
from vyn.parser import Parser
from vyn.semantic import SemanticAnalyzer
from vyn.interpreter import run_source
from vyn.ast.nodes import AssignStmt, IfStmt, TryStmt


class TestLexer(unittest.TestCase):
    def test_keywords(self):
        tokens = Lexer("let mut fn hot return").tokenize()
        kinds = [t.kind for t in tokens if t.kind != TokenKind.EOF]
        self.assertEqual(kinds[:5], [TokenKind.LET, TokenKind.MUT, TokenKind.FN, TokenKind.HOT, TokenKind.RETURN])

    def test_comments(self):
        src = "// commentaire avec apostrophe '\nlet x = 1;"
        tokens = Lexer(src).tokenize()
        kinds = [t.kind for t in tokens if t.kind != TokenKind.EOF]
        self.assertEqual(kinds[0], TokenKind.LET)

    def test_block_comment(self):
        src = "/* bloc */ fn main() -> i32 { return 0; }"
        prog = Parser(src).parse()
        self.assertEqual(prog.functions[0].name, "main")


class TestParser(unittest.TestCase):
    def test_fn_named_loop(self):
        src = "fn loop() -> i32 { return 0; } fn main() -> i32 { return 0; }"
        prog = Parser(src).parse()
        self.assertEqual(prog.functions[0].name, "loop")

    def test_module_level_log_call(self):
        src = 'fn main() -> i32 { return 0; }\nlog.info("init");'
        prog = Parser(src).parse()
        self.assertEqual(len(prog.init_stmts), 1)

    def test_let_named_loop(self):
        src = "fn main() -> i32 { let loop: i32 = 0; return loop; }"
        prog = Parser(src).parse()
        self.assertEqual(prog.functions[0].body[0].name, "loop")

    def test_hot_function(self):
        src = "hot fn calc(x: f32) -> f32 { return x; } fn main() -> i32 { return 0; }"
        prog = Parser(src).parse()
        hot = [f for f in prog.functions if f.is_hot]
        self.assertEqual(len(hot), 1)
        self.assertEqual(hot[0].name, "calc")

    def test_profile_attribute(self):
        src = "@[profile]\nfn task_fn() -> void { return; }\nfn main() -> i32 { return 0; }"
        prog = Parser(src).parse()
        self.assertTrue(any(a.name == "profile" for a in prog.functions[0].attributes))

    def test_compound_assign(self):
        src = "fn main() -> i32 { let mut x: i32 = 0; x += 2; return x; }"
        prog = Parser(src).parse()
        self.assertIsInstance(prog.functions[0].body[1], type(prog.functions[0].body[0]).__bases__[0] if False else object)
        from vyn.ast.nodes import AssignStmt, IfStmt, TryStmt
        self.assertIsInstance(prog.functions[0].body[1], AssignStmt)

    def test_loop_in(self):
        src = """fn f(input: [f32; 3]) -> f32 {
            let mut sum: f32 = 0.0;
            loop val in input { sum += val; }
            return sum;
        }
        fn main() -> i32 { return 0; }"""
        prog = Parser(src).parse()
        self.assertEqual(prog.functions[0].name, "f")


class TestSemantic(unittest.TestCase):
    def test_immut_assign_error(self):
        src = "fn main() -> i32 { let x = 1; x = 2; return 0; }"
        prog = Parser(src).parse()
        sem = SemanticAnalyzer()
        with self.assertRaises(Exception):
            sem.analyze(prog)


class TestStdlibRuntime(unittest.TestCase):
    def test_html_page(self):
        from vyn.stdlib_runtime import html_page, html_body, html_h1, css_stylesheet, css_rule
        css = css_stylesheet(css_rule("body", "color", "red"))
        page = html_page("Test", html_body(html_h1("Hello")), css)
        self.assertIn("<!DOCTYPE html>", page)
        self.assertIn("Hello", page)

    def test_fs_write_read(self):
        from vyn.stdlib_runtime import dispatch, _MISSING
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            dispatch("fs", "write", [path, "vyn-test"])
            content = dispatch("fs", "read", [path])
            self.assertEqual(content, "vyn-test")
        finally:
            os.unlink(path)

    def test_json_roundtrip(self):
        from vyn.stdlib_runtime import dispatch
        s = dispatch("json", "stringify", [42])
        self.assertEqual(s, "42")
        n = dispatch("json", "parse_int", [s])
        self.assertEqual(n, 42)


class TestParserFlexible(unittest.TestCase):
    def test_match_without_parens(self):
        src = """fn main() -> i32 {
            let json: i32 = 1;
            match json {
                case 0: return 0;
                default: return 1;
            }
            return 0;
        }"""
        prog = Parser(src).parse()
        self.assertEqual(prog.functions[0].name, "main")

    def test_if_without_parens(self):
        src = "fn main() -> i32 { if x == 0 { return 1; } return 0; }"
        prog = Parser(src).parse()
        self.assertIsInstance(prog.functions[0].body[0], IfStmt)

    def test_try_catch_flexible(self):
        src = """fn main() -> i32 {
            try { throw 0; } catch e { return 0; }
            return 0;
        }"""
        prog = Parser(src).parse()
        self.assertIsInstance(prog.functions[0].body[0], TryStmt)

    def test_match_json_variable(self):
        src = """fn f(json: i32) -> i32 {
            match json {
                case 1: return 10;
                else: return 0;
            }
            return 0;
        }
        fn main() -> i32 { return f(1); }"""
        prog = Parser(src).parse()
        self.assertEqual(len(prog.functions), 2)


class TestVPM(unittest.TestCase):
    def test_vpm_install(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "vpm", "install"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("installed", r.stdout)


class TestLanguageFeatures(unittest.TestCase):
    def test_match_enum_try(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "match_demo.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 0)

    def test_db_demo(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "db_demo.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 0)


class TestLanguageServer(unittest.TestCase):
    def test_member_completion_io(self):
        from vynstudio.language_server import SERVER
        names = [s.name for s in SERVER.complete_member("io")]
        self.assertIn("println", names)
        self.assertIn("print", names)

    def test_namespace_before_dot(self):
        from vynstudio.language_server import SERVER
        self.assertEqual(SERVER.namespace_before_dot("    io."), "io")
        self.assertIsNone(SERVER.namespace_before_dot("    io.println"))

    def test_vendor_serde(self):
        from vynstudio.language_server import SERVER
        names = [s.name for s in SERVER.complete_member("serde")]
        self.assertIn("serialize", names)

    def test_numpy_members(self):
        from vynstudio.language_server import SERVER
        names = [s.name for s in SERVER.complete_member("numpy")]
        self.assertIn("array", names)
        self.assertIn("mean", names)
        self.assertGreaterEqual(len(names), 8)

    def test_call_snippet_with_args(self):
        from vynstudio.language_server import VynLanguageServer
        text, pos = VynLanguageServer.call_snippet("relu", "relu(x: i32) -> i32")
        self.assertEqual(text, "relu()")
        self.assertEqual(pos, 5)

    def test_call_snippet_no_args(self):
        from vynstudio.language_server import VynLanguageServer
        text, pos = VynLanguageServer.call_snippet("run", "run() -> void")
        self.assertEqual(text, "run()")
        self.assertEqual(pos, 4)

    def test_std_member_completion(self):
        from vynstudio.language_server import SERVER
        names = [s.name for s in SERVER.complete_member("std")]
        self.assertIn("io", names)
        self.assertIn("numpy", names)

    def test_unified_prefix_filter(self):
        from vynstudio.language_server import SERVER
        names = [s.name for s in SERVER.complete_unified("io")]
        self.assertIn("io", names)
        io_names = [s.insert or s.name for s in SERVER.complete_unified("io")]
        self.assertTrue(any("println" in n for n in io_names))

    def test_hover_lookup(self):
        from vynstudio.language_server import SERVER
        sym = SERVER.lookup_hover("println")
        self.assertIsNotNone(sym)
        self.assertEqual(sym.name, "println")

    def test_string_escape(self):
        tokens = Lexer(r'"line\n"').tokenize()
        self.assertEqual(tokens[0].value, "line\n")


class TestInterpreter(unittest.TestCase):
    def test_break_continue(self):
        src = """fn main() -> i32 {
            let mut i: i32 = 0;
            loop {
                i += 1;
                if (i == 3) { break; }
                continue;
            }
            return i;
        }"""
        self.assertEqual(run_source(src), 3)

    def test_html_page_example(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "html_page.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 0)
        out = os.path.join(os.path.dirname(__file__), "..", "dist", "page.html")
        self.assertTrue(os.path.exists(out))

    def test_package_demo(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "package_demo.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 0)

    def test_ai_train(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "ai_train.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 0)

    def test_ml_numpy(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy not installed")
        code = run_source(
            'import std.io;\nimport std.numpy;\n'
            'fn main() -> i32 { let a = numpy.array([1.0,2.0,3.0]); io.println(numpy.mean(a)); return 0; }'
        )
        self.assertEqual(code, 0)

    def test_ffi_run(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "ffi.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 202)

    def test_profile_run(self):
        path = os.path.join(os.path.dirname(__file__), "..", "examples", "profile.vyn")
        with open(path, encoding="utf-8") as f:
            code = run_source(f.read())
        self.assertEqual(code, 0)


class TestLanguageMajor(unittest.TestCase):
    def test_const_and_type_alias(self):
        src = """
        const MAX: i32 = 0xFF;
        type UserId = i32;
        fn main() -> i32 {
            let id: UserId = MAX;
            return id;
        }
        """
        self.assertEqual(run_source(src), 255)

    def test_trait_parse(self):
        src = """
        trait Drawable {
            fn draw(self) -> void;
        }
        fn main() -> i32 { return 0; }
        """
        prog = Parser(src).parse()
        self.assertEqual(prog.traits[0].name, "Drawable")
        self.assertEqual(prog.traits[0].methods[0].name, "draw")

    def test_enum_payload(self):
        src = """
        enum Result {
            Ok(i32),
            Err(str),
        }
        fn main() -> i32 {
            let r = Ok(42);
            match r {
                case Result.Ok: return 1;
                default: return 0;
            }
            return 0;
        }
        """
        self.assertEqual(run_source(src), 1)

    def test_array_index_assign(self):
        src = """
        fn main() -> i32 {
            let mut arr: [i32; 3] = [0, 0, 0];
            arr[1] = 99;
            return arr[1];
        }
        """
        self.assertEqual(run_source(src), 99)

    def test_hex_literal(self):
        tokens = Lexer("0xFF 0x10").tokenize()
        vals = [t.value for t in tokens if t.kind == TokenKind.INT]
        self.assertEqual(vals, ["255", "16"])

    def test_hash_fnv1a(self):
        from vyn.stdlib_runtime import dispatch
        h = dispatch("hash", "fnv1a", ["test"])
        self.assertIsInstance(h, int)
        self.assertNotEqual(h, 0)

    def test_thread_spawn_join(self):
        src = """
        import std.thread;
        fn worker() -> void { return; }
        fn main() -> i32 {
            let h = thread.spawn("worker");
            thread.join(h);
            return 0;
        }
        """
        self.assertEqual(run_source(src), 0)

    def test_hot_fn_logs(self):
        import io
        import sys
        src = """
        hot fn calc(x: f32) -> f32 { return x; }
        fn main() -> i32 { calc(1.0); return 0; }
        """
        buf = io.StringIO()
        old = sys.stderr
        sys.stderr = buf
        try:
            run_source(src)
        finally:
            sys.stderr = old
        self.assertIn("[VynHot]", buf.getvalue())


class TestVynComplete(unittest.TestCase):
    def test_mod_namespace(self):
        src = """
        mod utils {
            fn answer() -> i32 { return 42; }
        }
        fn main() -> i32 { return utils.answer(); }
        """
        self.assertEqual(run_source(src), 42)

    def test_ownership_move(self):
        src = """
        fn main() -> i32 {
            let x: own i32 = 10;
            let y = x;
            return y;
        }
        """
        self.assertEqual(run_source(src), 10)
        src2 = """
        fn main() -> i32 {
            let x: own i32 = 10;
            let y = x;
            return x;
        }
        """
        with self.assertRaises(Exception):
            run_source(src2)

    def test_hot_reload_swap(self):
        from vyn.interpreter import Interpreter
        from vyn.parser import Parser
        from vyn.semantic import SemanticAnalyzer
        src1 = "hot fn f() -> i32 { return 1; } fn main() -> i32 { return f(); }"
        prog1 = Parser(src1).parse()
        SemanticAnalyzer().analyze(prog1)
        interp = Interpreter(prog1)
        self.assertEqual(interp._call_fn(interp.functions["f"], []), 1)
        src2 = "hot fn f() -> i32 { return 99; } fn main() -> i32 { return f(); }"
        prog2 = Parser(src2).parse()
        SemanticAnalyzer().analyze(prog2)
        interp.reload_hot_functions(prog2)
        self.assertEqual(interp._call_fn(interp.functions["f"], []), 99)

    def test_llvm_match_ir(self):
        from vyn.codegen.llvm_gen import LLVMGenerator
        from vyn.parser import Parser
        from vyn.semantic import SemanticAnalyzer
        src = """
        enum Status { Ready, Done, }
        fn main() -> i32 {
            let x: i32 = 0;
            match x {
                case Status.Ready: return 1;
                default: return 0;
            }
            return 0;
        }
        """
        program = Parser(src).parse()
        sem = SemanticAnalyzer()
        sem.analyze(program)
        ir_code = LLVMGenerator(program, sem).generate()
        self.assertIn("match_case", ir_code)

    def test_mod_const(self):
        src = """
        mod cfg {
            const LIMIT: i32 = 5;
        }
        fn main() -> i32 { return cfg.LIMIT; }
        """
        self.assertEqual(run_source(src), 5)


    def test_context_import(self):
        from vynstudio.language_server import SERVER
        from vynstudio.completion_context import detect_context
        ctx = detect_context("import ")
        syms = SERVER.complete_contextual(ctx)
        names = [s.name for s in syms]
        self.assertIn("std.io", names)
        self.assertIn("std.fs", names)
        self.assertIn("serde", names)

    def test_context_let(self):
        from vynstudio.language_server import SERVER
        from vynstudio.completion_context import detect_context
        ctx = detect_context("let ")
        syms = SERVER.complete_contextual(ctx)
        inserts = [s.insert for s in syms]
        self.assertTrue(any("mut" in (i or "") for i in inserts))
        self.assertTrue(any("i32" in (i or "") for i in inserts))

    def test_context_type(self):
        from vynstudio.language_server import SERVER
        from vynstudio.completion_context import detect_context
        ctx = detect_context("let x: ")
        syms = SERVER.complete_contextual(ctx)
        names = [s.name for s in syms]
        self.assertIn("i32", names)
        self.assertIn("f32", names)
        self.assertIn("str", names)

    def test_context_use_symbol(self):
        from vynstudio.language_server import SERVER
        from vynstudio.completion_context import CompletionContext
        ctx = CompletionContext("use_symbol", "", 0, "io", "")
        syms = SERVER.complete_contextual(ctx)
        names = [s.name for s in syms]
        self.assertIn("println", names)
        self.assertIn("print", names)


if __name__ == "__main__":
    unittest.main()
