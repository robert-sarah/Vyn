"""Tests unitaires Vyn."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vyn.lexer import Lexer, TokenKind
from vyn.parser import Parser
from vyn.semantic import SemanticAnalyzer
from vyn.interpreter import run_source


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
        from vyn.ast.nodes import AssignStmt
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


if __name__ == "__main__":
    unittest.main()
