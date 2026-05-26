"""
Unit tests for the code parsing module.

Tests CodeParser.detect_language(), CodeParser.is_summarizable_file(),
and CodeParser.parse_file() across multiple languages.
"""

import pytest

from explorer.parsing import CodeBlockData, CodeParser, store_code_blocks


@pytest.fixture
def parser():
    return CodeParser()


class TestDetectLanguage:
    """Tests for CodeParser.detect_language()."""

    def test_python(self, parser):
        assert parser.detect_language("main.py") == "python"

    def test_javascript(self, parser):
        assert parser.detect_language("app.js") == "javascript"
        assert parser.detect_language("module.mjs") == "javascript"
        assert parser.detect_language("component.jsx") == "javascript"

    def test_typescript(self, parser):
        assert parser.detect_language("index.ts") == "typescript"
        assert parser.detect_language("component.tsx") == "typescript"

    def test_java(self, parser):
        assert parser.detect_language("Main.java") == "java"

    def test_go(self, parser):
        assert parser.detect_language("main.go") == "go"

    def test_rust(self, parser):
        assert parser.detect_language("lib.rs") == "rust"

    def test_c(self, parser):
        assert parser.detect_language("main.c") == "c"
        assert parser.detect_language("header.h") == "c"

    def test_cpp(self, parser):
        assert parser.detect_language("main.cpp") == "cpp"
        assert parser.detect_language("main.cc") == "cpp"
        assert parser.detect_language("header.hpp") == "cpp"

    def test_ruby(self, parser):
        assert parser.detect_language("app.rb") == "ruby"

    def test_php(self, parser):
        assert parser.detect_language("index.php") == "php"

    def test_html(self, parser):
        assert parser.detect_language("page.html") == "html"
        assert parser.detect_language("page.htm") == "html"

    def test_css(self, parser):
        assert parser.detect_language("style.css") == "css"

    def test_markdown(self, parser):
        assert parser.detect_language("README.md") == "markdown"

    def test_unsupported_extension(self, parser):
        assert parser.detect_language("image.png") is None
        assert parser.detect_language("data.bin") is None

    def test_no_extension(self, parser):
        assert parser.detect_language("Makefile") is None
        assert parser.detect_language("noext") is None

    def test_path_with_directories(self, parser):
        assert parser.detect_language("src/main.py") == "python"
        assert parser.detect_language("lib/utils/helper.ts") == "typescript"

    def test_case_insensitive(self, parser):
        assert parser.detect_language("FILE.PY") == "python"
        assert parser.detect_language("App.JS") == "javascript"


class TestIsSummarizableFile:
    """Tests for CodeParser.is_summarizable_file()."""

    def test_programming_files_are_summarizable(self, parser):
        assert parser.is_summarizable_file("main.py") is True
        assert parser.is_summarizable_file("app.js") is True
        assert parser.is_summarizable_file("index.ts") is True
        assert parser.is_summarizable_file("Main.java") is True
        assert parser.is_summarizable_file("main.go") is True
        assert parser.is_summarizable_file("lib.rs") is True

    def test_markup_files_are_summarizable(self, parser):
        assert parser.is_summarizable_file("page.html") is True
        assert parser.is_summarizable_file("style.css") is True
        assert parser.is_summarizable_file("README.md") is True

    def test_binary_files_not_summarizable(self, parser):
        assert parser.is_summarizable_file("image.png") is False
        assert parser.is_summarizable_file("photo.jpg") is False
        assert parser.is_summarizable_file("app.exe") is False
        assert parser.is_summarizable_file("lib.dll") is False
        assert parser.is_summarizable_file("archive.zip") is False

    def test_media_files_not_summarizable(self, parser):
        assert parser.is_summarizable_file("song.mp3") is False
        assert parser.is_summarizable_file("video.mp4") is False
        assert parser.is_summarizable_file("clip.wav") is False

    def test_lock_files_not_summarizable(self, parser):
        assert parser.is_summarizable_file("package-lock.json") is False
        assert parser.is_summarizable_file("yarn.lock") is False
        assert parser.is_summarizable_file("Pipfile.lock") is False
        assert parser.is_summarizable_file("poetry.lock") is False
        assert parser.is_summarizable_file("Cargo.lock") is False
        assert parser.is_summarizable_file("go.sum") is False

    def test_minified_files_not_summarizable(self, parser):
        assert parser.is_summarizable_file("bundle.min.js") is False
        assert parser.is_summarizable_file("style.min.css") is False

    def test_no_extension_not_summarizable(self, parser):
        assert parser.is_summarizable_file("Makefile") is False
        assert parser.is_summarizable_file("Dockerfile") is False

    def test_source_map_not_summarizable(self, parser):
        assert parser.is_summarizable_file("bundle.js.map") is False


class TestParseFilePython:
    """Tests for parsing Python source code."""

    def test_extracts_functions(self, parser):
        code = "def hello():\n    return 'world'\n\ndef goodbye():\n    pass\n"
        blocks = parser.parse_file(code, "python")
        functions = [b for b in blocks if b.kind == "function"]
        assert len(functions) == 2
        assert functions[0].name == "hello"
        assert functions[1].name == "goodbye"

    def test_extracts_classes(self, parser):
        code = "class MyClass:\n    pass\n\nclass AnotherClass:\n    pass\n"
        blocks = parser.parse_file(code, "python")
        classes = [b for b in blocks if b.kind == "class"]
        assert len(classes) == 2
        assert classes[0].name == "MyClass"
        assert classes[1].name == "AnotherClass"

    def test_extracts_methods_with_parent(self, parser):
        code = "class Foo:\n    def bar(self):\n        pass\n    def baz(self):\n        pass\n"
        blocks = parser.parse_file(code, "python")
        methods = [b for b in blocks if b.kind == "method"]
        assert len(methods) == 2
        assert all(m.parent_block == "Foo" for m in methods)
        assert methods[0].name == "bar"
        assert methods[1].name == "baz"

    def test_block_content_is_substring(self, parser):
        code = "def hello():\n    return 'world'\n"
        blocks = parser.parse_file(code, "python")
        for block in blocks:
            assert block.content in code

    def test_line_numbers_are_valid(self, parser):
        code = "def first():\n    pass\n\ndef second():\n    pass\n"
        blocks = parser.parse_file(code, "python")
        for block in blocks:
            assert block.start_line >= 1
            assert block.start_line <= block.end_line

    def test_empty_content_returns_empty(self, parser):
        assert parser.parse_file("", "python") == []
        assert parser.parse_file("   \n  ", "python") == []


class TestParseFileJavaScript:
    """Tests for parsing JavaScript source code."""

    def test_extracts_function_declarations(self, parser):
        code = "function greet(name) {\n    return 'Hello ' + name;\n}\n"
        blocks = parser.parse_file(code, "javascript")
        functions = [b for b in blocks if b.kind == "function"]
        assert len(functions) == 1
        assert functions[0].name == "greet"

    def test_extracts_arrow_functions(self, parser):
        code = "const add = (a, b) => {\n    return a + b;\n};\n"
        blocks = parser.parse_file(code, "javascript")
        functions = [b for b in blocks if b.kind == "function"]
        assert len(functions) == 1
        assert functions[0].name == "add"

    def test_extracts_class_with_methods(self, parser):
        code = (
            "class Animal {\n"
            "    constructor(name) {\n"
            "        this.name = name;\n"
            "    }\n"
            "    speak() {\n"
            "        return this.name;\n"
            "    }\n"
            "}\n"
        )
        blocks = parser.parse_file(code, "javascript")
        classes = [b for b in blocks if b.kind == "class"]
        methods = [b for b in blocks if b.kind == "method"]
        assert len(classes) == 1
        assert classes[0].name == "Animal"
        assert len(methods) == 2
        assert all(m.parent_block == "Animal" for m in methods)


class TestParseFileTypeScript:
    """Tests for parsing TypeScript source code."""

    def test_extracts_typed_functions(self, parser):
        code = "function add(a: number, b: number): number {\n    return a + b;\n}\n"
        blocks = parser.parse_file(code, "typescript")
        functions = [b for b in blocks if b.kind == "function"]
        assert len(functions) == 1
        assert functions[0].name == "add"

    def test_extracts_class_with_typed_methods(self, parser):
        code = (
            "class Service {\n"
            "    getData(): string {\n"
            "        return 'data';\n"
            "    }\n"
            "}\n"
        )
        blocks = parser.parse_file(code, "typescript")
        classes = [b for b in blocks if b.kind == "class"]
        methods = [b for b in blocks if b.kind == "method"]
        assert len(classes) == 1
        assert classes[0].name == "Service"
        assert len(methods) == 1
        assert methods[0].parent_block == "Service"


class TestParseFileRust:
    """Tests for parsing Rust source code."""

    def test_extracts_functions(self, parser):
        code = "fn main() {\n    println!(\"Hello\");\n}\n"
        blocks = parser.parse_file(code, "rust")
        functions = [b for b in blocks if b.kind == "function"]
        assert len(functions) == 1
        assert functions[0].name == "main"

    def test_extracts_impl_methods(self, parser):
        code = (
            "struct Point { x: f64, y: f64 }\n\n"
            "impl Point {\n"
            "    fn new(x: f64, y: f64) -> Self {\n"
            "        Point { x, y }\n"
            "    }\n"
            "}\n"
        )
        blocks = parser.parse_file(code, "rust")
        classes = [b for b in blocks if b.kind == "class"]
        methods = [b for b in blocks if b.kind == "method"]
        assert any(c.name == "Point" for c in classes)
        assert len(methods) >= 1
        assert methods[0].name == "new"
        assert methods[0].parent_block == "Point"


class TestParseFileGo:
    """Tests for parsing Go source code."""

    def test_extracts_functions(self, parser):
        code = "package main\n\nfunc main() {\n    fmt.Println(\"Hello\")\n}\n"
        blocks = parser.parse_file(code, "go")
        functions = [b for b in blocks if b.kind == "function"]
        assert len(functions) == 1
        assert functions[0].name == "main"

    def test_extracts_type_declarations(self, parser):
        code = "package main\n\ntype Server struct {\n    host string\n    port int\n}\n"
        blocks = parser.parse_file(code, "go")
        classes = [b for b in blocks if b.kind == "class"]
        assert len(classes) == 1
        assert classes[0].name == "Server"


class TestParseFileEdgeCases:
    """Tests for edge cases in parsing."""

    def test_unsupported_language_returns_empty(self, parser):
        blocks = parser.parse_file("some code", "nonexistent_lang_xyz")
        assert blocks == []

    def test_syntax_errors_still_parse(self, parser):
        # tree-sitter is error-tolerant
        code = "def broken(\n    pass\n"
        blocks = parser.parse_file(code, "python")
        # Should not crash, may or may not extract blocks
        assert isinstance(blocks, list)

    def test_valid_kinds(self, parser):
        code = (
            "class Foo:\n"
            "    def bar(self):\n"
            "        pass\n\n"
            "def standalone():\n"
            "    pass\n"
        )
        blocks = parser.parse_file(code, "python")
        valid_kinds = {"function", "class", "method", "module_construct"}
        for block in blocks:
            assert block.kind in valid_kinds

    def test_names_are_non_empty(self, parser):
        code = "def hello():\n    pass\n\nclass World:\n    pass\n"
        blocks = parser.parse_file(code, "python")
        for block in blocks:
            assert block.name
            assert len(block.name) > 0


@pytest.mark.django_db
class TestStoreCodeBlocks:
    """Tests for store_code_blocks database storage."""

    def test_stores_blocks_in_database(self):
        from explorer.models import CodeBlock, Repository, RepositoryFile, User

        user = User.objects.create_user(username="testuser", password="testpass")
        repo = Repository.objects.create(
            user=user, name="test-repo", source_type="zip"
        )
        repo_file = RepositoryFile.objects.create(
            repository=repo,
            path="src/main.py",
            filename="main.py",
            language="python",
            content="def hello():\n    pass\n",
            size_bytes=20,
        )

        code_blocks = [
            CodeBlockData(
                name="hello",
                kind="function",
                start_line=1,
                end_line=2,
                content="def hello():\n    pass",
                parent_block=None,
            )
        ]

        store_code_blocks(repo_file, code_blocks)

        db_blocks = CodeBlock.objects.filter(file=repo_file)
        assert db_blocks.count() == 1
        block = db_blocks.first()
        assert block.name == "hello"
        assert block.kind == "function"
        assert block.start_line == 1
        assert block.end_line == 2
        assert block.parent_block_name is None

    def test_replaces_existing_blocks_on_reparse(self):
        from explorer.models import CodeBlock, Repository, RepositoryFile, User

        user = User.objects.create_user(username="testuser2", password="testpass")
        repo = Repository.objects.create(
            user=user, name="test-repo", source_type="zip"
        )
        repo_file = RepositoryFile.objects.create(
            repository=repo,
            path="src/main.py",
            filename="main.py",
            language="python",
            content="def hello():\n    pass\n",
            size_bytes=20,
        )

        # First parse
        store_code_blocks(
            repo_file,
            [
                CodeBlockData(
                    name="old_func",
                    kind="function",
                    start_line=1,
                    end_line=2,
                    content="def old_func():\n    pass",
                )
            ],
        )
        assert CodeBlock.objects.filter(file=repo_file).count() == 1

        # Re-parse with new blocks
        store_code_blocks(
            repo_file,
            [
                CodeBlockData(
                    name="new_func",
                    kind="function",
                    start_line=1,
                    end_line=2,
                    content="def new_func():\n    pass",
                ),
                CodeBlockData(
                    name="another_func",
                    kind="function",
                    start_line=4,
                    end_line=5,
                    content="def another_func():\n    pass",
                ),
            ],
        )

        db_blocks = CodeBlock.objects.filter(file=repo_file)
        assert db_blocks.count() == 2
        names = set(db_blocks.values_list("name", flat=True))
        assert names == {"new_func", "another_func"}
