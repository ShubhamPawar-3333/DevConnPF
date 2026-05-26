"""
Code parsing module using tree-sitter for multi-language AST extraction.

Provides the CodeParser class which detects file languages, determines
summarizability, and extracts code blocks (functions, classes, methods)
from source files.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from tree_sitter_language_pack import get_language, get_parser

logger = logging.getLogger(__name__)


@dataclass
class CodeBlockData:
    """A discrete code block extracted from a source file.

    Attributes:
        name: The name of the code block (function/class/method name).
        kind: The type of block - "function", "class", "method", or "module_construct".
        start_line: The 1-based starting line number.
        end_line: The 1-based ending line number.
        content: The source code text of the block.
        parent_block: The name of the parent class (for methods), or None.
    """

    name: str
    kind: str  # "function", "class", "method", "module_construct"
    start_line: int
    end_line: int
    content: str
    parent_block: str | None = None


# Mapping of file extensions to tree-sitter language names
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".md": "markdown",
    ".markdown": "markdown",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".dart": "dart",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".cs": "c_sharp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".clj": "clojure",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".vue": "vue",
    ".svelte": "svelte",
}

# Extensions that are recognized as programming/markup languages (summarizable)
SUMMARIZABLE_EXTENSIONS: set[str] = {
    ".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".rs", ".c", ".h", ".cpp", ".cc", ".cxx",
    ".hpp", ".hxx", ".rb", ".php", ".html", ".htm", ".css",
    ".scss", ".sass", ".less", ".md", ".markdown",
    ".swift", ".kt", ".kts", ".scala", ".r", ".R",
    ".lua", ".dart", ".sh", ".bash", ".zsh",
    ".cs", ".fs", ".ex", ".exs", ".erl", ".hs", ".clj",
    ".sql", ".yaml", ".yml", ".toml", ".json", ".xml",
    ".vue", ".svelte", ".ini", ".cfg",
}

# Extensions for binary/media/non-text files
NON_SUMMARIZABLE_EXTENSIONS: set[str] = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    # Audio/Video
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm", ".flac", ".ogg",
    # Documents (binary)
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz",
    # Executables/Libraries
    ".exe", ".dll", ".so", ".dylib", ".o", ".a", ".lib",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Compiled
    ".pyc", ".pyo", ".class", ".jar", ".war",
    # Databases
    ".db", ".sqlite", ".sqlite3",
    # Other binary
    ".bin", ".dat", ".iso", ".img",
}

# Lock files and auto-generated filenames
NON_SUMMARIZABLE_FILENAMES: set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
    "poetry.lock",
    "Gemfile.lock",
    "composer.lock",
    "Cargo.lock",
    "go.sum",
    "shrinkwrap.json",
    "npm-shrinkwrap.json",
}

# Node types that represent functions in various languages
FUNCTION_NODE_TYPES: set[str] = {
    # Python
    "function_definition",
    # JavaScript/TypeScript
    "function_declaration",
    "generator_function_declaration",
    # Java
    "method_declaration",
    "constructor_declaration",
    # Go
    "function_declaration",
    "method_declaration",
    # Rust
    "function_item",
    # C/C++
    "function_definition",
    # Ruby
    "method",
    "singleton_method",
    # PHP
    "function_definition",
    "method_declaration",
}

# Node types that represent classes
CLASS_NODE_TYPES: set[str] = {
    "class_definition",  # Python
    "class_declaration",  # JS/TS/Java/C#/PHP
    "class_specifier",  # C++
    "struct_item",  # Rust
    "impl_item",  # Rust
    "class",  # Ruby
    "module",  # Ruby (module acts like a class)
}

# Node types that represent methods within classes
METHOD_NODE_TYPES: set[str] = {
    "function_definition",  # Python (inside class)
    "method_definition",  # JS/TS
    "method_declaration",  # Java/PHP
    "function_item",  # Rust (inside impl)
    "method",  # Ruby
}


class CodeParser:
    """Parses source code files using tree-sitter to extract code blocks.

    Supports multiple programming languages and extracts functions, classes,
    methods, and module-level constructs.
    """

    @staticmethod
    def detect_language(filename: str) -> str | None:
        """Detect the tree-sitter language name from a filename.

        Args:
            filename: The filename (or path) to detect language for.

        Returns:
            The tree-sitter language name string, or None if unsupported.
        """
        basename = os.path.basename(filename)
        _, ext = os.path.splitext(basename)

        if not ext:
            return None

        # Handle case-sensitive .R extension
        if ext == ".R":
            return EXTENSION_TO_LANGUAGE.get(".R")

        return EXTENSION_TO_LANGUAGE.get(ext.lower())

    @staticmethod
    def is_summarizable_file(filename: str) -> bool:
        """Determine if a file should be summarized based on its filename.

        Returns True for recognized programming/markup extensions.
        Returns False for binary files, media assets, lock files,
        minified bundles, and auto-generated files.

        Args:
            filename: The filename to check.

        Returns:
            True if the file is summarizable, False otherwise.
        """
        basename = os.path.basename(filename)

        # Check exact filename matches (lock files, auto-generated)
        if basename in NON_SUMMARIZABLE_FILENAMES:
            return False

        # Check for minified files
        if ".min." in basename:
            return False

        # Check for source map files
        if basename.endswith(".map"):
            return False

        _, ext = os.path.splitext(basename)

        if not ext:
            return False

        # Check if it's a known non-summarizable extension
        if ext.lower() in NON_SUMMARIZABLE_EXTENSIONS:
            return False

        # Handle case-sensitive .R extension
        if ext == ".R":
            return True

        # Check if it has a recognized programming/markup extension
        return ext.lower() in SUMMARIZABLE_EXTENSIONS

    def parse_file(self, content: str, language: str) -> list[CodeBlockData]:
        """Parse a source file and extract code blocks.

        Uses tree-sitter to parse the AST and extract functions, classes,
        methods, and module-level constructs.

        Args:
            content: The source code content as a string.
            language: The tree-sitter language name (e.g., "python", "javascript").

        Returns:
            A list of CodeBlockData instances representing extracted code blocks.
        """
        if not content or not content.strip():
            return []

        try:
            parser = get_parser(language)
        except Exception:
            logger.warning("Unsupported language for parsing: %s", language)
            return []

        try:
            tree = parser.parse(content.encode("utf-8"))
        except Exception as e:
            logger.warning("Failed to parse content for language %s: %s", language, e)
            return []

        root = tree.root_node
        blocks: list[CodeBlockData] = []

        self._extract_blocks(root, content, language, blocks, parent_class=None)

        return blocks

    def _extract_blocks(
        self,
        node,
        content: str,
        language: str,
        blocks: list[CodeBlockData],
        parent_class: str | None,
    ) -> None:
        """Recursively extract code blocks from the AST.

        Args:
            node: The current tree-sitter node.
            content: The full source code content.
            language: The language being parsed.
            blocks: The list to append extracted blocks to.
            parent_class: The name of the parent class if inside a class body.
        """
        for child in node.children:
            node_type = child.type

            # Handle class definitions
            if node_type in CLASS_NODE_TYPES:
                class_name = self._get_node_name(child, language)
                if class_name:
                    start_line = child.start_point[0] + 1
                    end_line = child.end_point[0] + 1
                    block_content = self._get_node_content(child, content)

                    blocks.append(
                        CodeBlockData(
                            name=class_name,
                            kind="class",
                            start_line=start_line,
                            end_line=end_line,
                            content=block_content,
                            parent_block=parent_class,
                        )
                    )

                    # Extract methods within the class
                    class_body = self._get_class_body(child, language)
                    if class_body is not None:
                        self._extract_blocks(
                            class_body, content, language, blocks, parent_class=class_name
                        )

            # Handle function/method definitions
            elif node_type in FUNCTION_NODE_TYPES or node_type in METHOD_NODE_TYPES:
                func_name = self._get_node_name(child, language)
                if func_name:
                    start_line = child.start_point[0] + 1
                    end_line = child.end_point[0] + 1
                    block_content = self._get_node_content(child, content)

                    kind = "method" if parent_class else "function"

                    blocks.append(
                        CodeBlockData(
                            name=func_name,
                            kind=kind,
                            start_line=start_line,
                            end_line=end_line,
                            content=block_content,
                            parent_block=parent_class,
                        )
                    )

            # Handle arrow functions / variable declarations with function values
            elif node_type in ("lexical_declaration", "variable_declaration"):
                self._extract_arrow_functions(
                    child, content, language, blocks, parent_class
                )

            # Handle Go-style top-level declarations
            elif node_type == "type_declaration" and language == "go":
                # Go struct/interface type declarations
                for type_spec in child.children:
                    if type_spec.type == "type_spec":
                        type_name = self._get_node_name(type_spec, language)
                        if type_name:
                            start_line = child.start_point[0] + 1
                            end_line = child.end_point[0] + 1
                            block_content = self._get_node_content(child, content)
                            blocks.append(
                                CodeBlockData(
                                    name=type_name,
                                    kind="class",
                                    start_line=start_line,
                                    end_line=end_line,
                                    content=block_content,
                                    parent_block=parent_class,
                                )
                            )

            # Handle Rust impl blocks
            elif node_type == "impl_item" and language == "rust":
                impl_name = self._get_impl_name(child)
                if impl_name:
                    start_line = child.start_point[0] + 1
                    end_line = child.end_point[0] + 1
                    block_content = self._get_node_content(child, content)
                    blocks.append(
                        CodeBlockData(
                            name=impl_name,
                            kind="class",
                            start_line=start_line,
                            end_line=end_line,
                            content=block_content,
                            parent_block=parent_class,
                        )
                    )
                    # Extract methods inside impl
                    for impl_child in child.children:
                        if impl_child.type == "declaration_list":
                            self._extract_blocks(
                                impl_child, content, language, blocks, parent_class=impl_name
                            )

    def _extract_arrow_functions(
        self,
        node,
        content: str,
        language: str,
        blocks: list[CodeBlockData],
        parent_class: str | None,
    ) -> None:
        """Extract arrow functions and function expressions from variable declarations.

        Args:
            node: A lexical_declaration or variable_declaration node.
            content: The full source code content.
            language: The language being parsed.
            blocks: The list to append extracted blocks to.
            parent_class: The name of the parent class if inside a class body.
        """
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if name_node and value_node:
                    if value_node.type in (
                        "arrow_function",
                        "function_expression",
                        "generator_function",
                    ):
                        func_name = name_node.text.decode("utf-8")
                        start_line = node.start_point[0] + 1
                        end_line = node.end_point[0] + 1
                        block_content = self._get_node_content(node, content)

                        kind = "method" if parent_class else "function"

                        blocks.append(
                            CodeBlockData(
                                name=func_name,
                                kind=kind,
                                start_line=start_line,
                                end_line=end_line,
                                content=block_content,
                                parent_block=parent_class,
                            )
                        )

    def _get_node_name(self, node, language: str) -> str | None:
        """Extract the name from a function/class/method node.

        Args:
            node: The tree-sitter node.
            language: The language being parsed.

        Returns:
            The name string, or None if not found.
        """
        # Try field-based access first (works for most languages)
        name_node = node.child_by_field_name("name")
        if name_node:
            return name_node.text.decode("utf-8")

        # For C/C++ function definitions, the name is nested in declarator
        declarator = node.child_by_field_name("declarator")
        if declarator:
            # function_declarator -> identifier/field_identifier
            inner = declarator.child_by_field_name("declarator")
            if inner:
                return inner.text.decode("utf-8")
            # Direct identifier in declarator
            for child in declarator.children:
                if child.type in ("identifier", "field_identifier"):
                    return child.text.decode("utf-8")

        # Fallback: look for identifier children
        for child in node.children:
            if child.type in ("identifier", "property_identifier", "type_identifier"):
                return child.text.decode("utf-8")
            # For Ruby classes/modules, name is in a constant node
            if child.type == "constant":
                return child.text.decode("utf-8")

        return None

    def _get_class_body(self, node, language: str):
        """Get the body node of a class definition.

        Args:
            node: The class definition node.
            language: The language being parsed.

        Returns:
            The body node, or None if not found.
        """
        # Try field-based access
        body = node.child_by_field_name("body")
        if body:
            return body

        # Look for common body node types
        body_types = {
            "block",  # Python
            "class_body",  # JS/TS/Java
            "declaration_list",  # Rust, PHP
            "field_declaration_list",  # Go, C++
            "body_statement",  # Ruby
        }

        for child in node.children:
            if child.type in body_types:
                return child

        return None

    def _get_impl_name(self, node) -> str | None:
        """Extract the type name from a Rust impl block.

        Args:
            node: The impl_item node.

        Returns:
            The impl type name, or None.
        """
        # Look for type_identifier in impl block
        for child in node.children:
            if child.type == "type_identifier":
                return child.text.decode("utf-8")
            if child.type == "generic_type":
                # Get the base type name
                for sub in child.children:
                    if sub.type == "type_identifier":
                        return sub.text.decode("utf-8")
        return None

    def _get_node_content(self, node, content: str) -> str:
        """Extract the source text for a node from the original content.

        Args:
            node: The tree-sitter node.
            content: The full source code content.

        Returns:
            The source text of the node.
        """
        start_byte = node.start_byte
        end_byte = node.end_byte
        return content.encode("utf-8")[start_byte:end_byte].decode("utf-8")


def store_code_blocks(repository_file, code_blocks: list[CodeBlockData]) -> None:
    """Store extracted CodeBlockData instances in the database.

    Creates CodeBlock model instances for each extracted block and
    associates them with the given RepositoryFile.

    Args:
        repository_file: The RepositoryFile model instance.
        code_blocks: List of CodeBlockData instances to store.
    """
    from explorer.models import CodeBlock

    # Remove existing code blocks for this file (in case of re-parsing)
    CodeBlock.objects.filter(file=repository_file).delete()

    # Bulk create new code blocks
    db_blocks = [
        CodeBlock(
            file=repository_file,
            name=block.name,
            kind=block.kind,
            start_line=block.start_line,
            end_line=block.end_line,
            content=block.content,
            parent_block_name=block.parent_block,
        )
        for block in code_blocks
    ]

    if db_blocks:
        CodeBlock.objects.bulk_create(db_blocks)

    return db_blocks
