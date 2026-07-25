"""Compiler for slidedown AST to HTML.

Transforms parsed AST nodes into complete HTML presentation.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import cast

from ..models.compiler import (
    CompileResult,
    ConfigValue,
    PlaceholderMap,
    JumpRefs,
    PresentationMetaConfig,
    SlideAddresses,
    SlideCounters,
)
from ..models.handlers import CompilerContext, DirectiveNode
from . import compiler_assets, compiler_rendering, nexus
from .directives import DirectiveRegistry
from .log import LOG
from .parser import ASTNode
from .theme import Theme


class Compiler:
    """
    Compiles slidedown AST to standalone HTML presentation

    Responsibilities:
    - Transform AST nodes to HTML
    - Apply directives (typewriter, snippets, etc.)
    - Inject CSS/JS
    - Copy runtime assets
    - Generate final output
    """

    def __init__(
        self,
        ast: list[ASTNode],
        output_dir: str,
        assets_dir: str,
        verbosity: int = 1,
        protected_code_blocks: PlaceholderMap | None = None,
        escaped_sequences: PlaceholderMap | None = None,
        theme_name: str = "default",
        input_dir: str = ".",
        watch: bool = False,
        standalone: bool = False,
    ) -> None:
        """
        Initialize compiler

        Args:
            ast: Parsed abstract syntax tree
            output_dir: Directory for compiled output
            assets_dir: Directory containing runtime assets (css/js/html)
            verbosity: Output verbosity level (0-3)
            protected_code_blocks: Protected .code{} blocks from parser
            escaped_sequences: Dict of backslash-escaped content from parser
            theme_name: Name of theme to use (default: "default")
            input_dir: Input directory for resolving relative paths
            watch: Whether compiled output should include live-reload script
            standalone: Inline all local assets into a single HTML file
        """
        self.ast = ast
        self.output_dir = Path(output_dir)
        self.assets_dir = Path(assets_dir)
        self.input_dir = Path(input_dir)
        self.verbosity = verbosity
        self.protected_code_blocks = protected_code_blocks or {}
        self.escaped_sequences = escaped_sequences or {}
        self.watch = watch
        self.standalone = standalone
        self._include_stack: set[Path] = set()
        self.directives = DirectiveRegistry()

        # Load theme
        self.theme = Theme(theme_name)
        LOG(f"Loaded theme: {self.theme.name}", level=2)

        self.slide_count = 0
        # Nexus addressing: address -> slide_num. Populated by slide_handler
        # as slides compile; consumed by jump resolution (see lib/nexus.py).
        self.slide_addresses: SlideAddresses = {}
        # .jump{} references, resolved after the walk so that a jump may
        # legitimately point forward to a slide compiled later.
        self.jump_refs: JumpRefs = []
        self.snippet_counters: SlideCounters = {}  # slide_num -> snippet_count
        self.typewriter_counters: SlideCounters = (
            {}
        )  # slide_num -> typewriter_count
        self.meta_config: PresentationMetaConfig = (
            {}
        )  # Configuration from .meta{} directive

    def compile(self) -> CompileResult:
        """
        Compile AST to HTML presentation

        Returns:
            dict with compilation results and statistics
        """
        LOG("Starting compilation...", level=2)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Process AST
        html_content = self.ast_compile(self.ast)

        # Every slide address is known only now, so jump targets are
        # resolved here rather than during the walk. An unresolved target
        # fails the build: a dead jump must not be discovered at a lectern.
        nexus.jumpRefs_validate(self.jump_refs, self.slide_addresses)

        # Build complete HTML document
        full_html = self.htmlDocument_build(html_content)

        if self.standalone:
            source_map = compiler_assets.assets_sourceMap_build(
                cast(compiler_assets.CompilerAssets, self)
            )
            full_html = compiler_assets.html_inline(full_html, source_map)
            LOG("Standalone mode: assets inlined, skipping copy", level=2)
        else:
            self.assets_copy()

        # Write output file
        output_file = self.output_dir / "index.html"
        output_file.write_text(full_html, encoding="utf-8")
        LOG(f"Wrote {output_file}", level=2)

        LOG("HTML document assembled", level=2)

        return {
            "status": True,
            "output_file": str(output_file),
            "slide_count": self.slide_count,
        }

    def ast_compile(self, nodes: list[ASTNode]) -> str:
        """
        Recursively compile AST nodes to HTML

        Compiles each node by:
        1. Recursively compiling children first (inside-out)
        2. Substituting placeholders in content with compiled children
        3. Applying directive handler to transform to HTML

        Args:
            nodes: List of AST nodes to compile

        Returns:
            Compiled HTML string with all placeholders substituted
        """
        html_parts: list[str] = []

        for node in nodes:
            # Compile this node (which recursively compiles children)
            compiled_node_html = self.node_compile(node)
            html_parts.append(compiled_node_html)

        return "\n".join(html_parts)

    def codeblocks_expand(self, content: str) -> str:
        """
        Expand protected .code{} block placeholders to highlighted HTML

        Finds \x00CODE_N\x00 placeholders in content and replaces them with
        syntax-highlighted HTML by processing the stored raw content.

        Args:
            content: String potentially containing CODE placeholders

        Returns:
            Content with placeholders replaced by highlighted code blocks
        """
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexer import Lexer
        from pygments.lexers import TextLexer, get_lexer_by_name
        from pygments.util import ClassNotFound

        from .lexer import SlidedownLexer

        def expand_code_placeholder(match: re.Match[str]) -> str:
            """Expand a CODE_N placeholder with syntax-highlighted content"""
            code_id = int(match.group(1))
            if code_id not in self.protected_code_blocks:
                return match.group(0)  # Leave placeholder if not found

            raw_content = self.protected_code_blocks[code_id]

            # Extract .syntax{language=X} modifier if present
            syntax_match = re.match(r"^\s*\.syntax\{([^}]+)\}\s*", raw_content)
            if syntax_match:
                language_spec = syntax_match.group(1)
                # Remove .syntax{} from content
                code_content = raw_content[syntax_match.end() :]

                # Parse language=value
                if "=" in language_spec:
                    language = language_spec.split("=", 1)[1].strip()
                else:
                    language = language_spec.strip()
            else:
                # No .syntax{} modifier, treat as plain text
                language = "text"
                code_content = raw_content

            # Get lexer
            lexer: Lexer
            try:
                if language.lower() in ["slidedown", "sd"]:
                    lexer = SlidedownLexer()
                else:
                    lexer = get_lexer_by_name(language)
            except ClassNotFound:
                lexer = TextLexer()

            # Generate highlighted HTML (use theme's Pygments style)
            pygments_style = self.theme.pygmentsStyle_get()
            formatter = HtmlFormatter(style=pygments_style, noclasses=True)
            highlighted = cast(str, highlight(code_content, lexer, formatter))

            return highlighted

        # Replace all \x00CODE_N\x00 placeholders
        result = re.sub(
            r"\x00CODE_(\d+)\x00", expand_code_placeholder, content
        )
        return result

    def escapes_expand(self, content: str) -> str:
        """
        Expand backslash-escaped sequence placeholders to literal text

        Finds \x00ESCAPE_N\x00 placeholders in content and replaces them with
        the stored escaped content. For example, ".directive{...}" becomes
        literal text.

        Args:
            content: String potentially containing ESCAPE placeholders

        Returns:
            Content with placeholders replaced by literal escaped text
        """
        import html

        def expand_escape_placeholder(match: re.Match[str]) -> str:
            """Expand an ESCAPE_N placeholder with literal escaped content"""
            escape_id = int(match.group(1))
            if escape_id not in self.escaped_sequences:
                return match.group(0)  # Leave placeholder if not found

            # Return the literal content, HTML-escaped for safety
            escaped_content = self.escaped_sequences[escape_id]
            return html.escape(escaped_content)

        result = re.sub(
            r"\x00ESCAPE_(\d+)\x00", expand_escape_placeholder, content
        )
        return result

    def node_compile(self, node: ASTNode) -> str:
        """
        Compile a single AST node to HTML

        Uses inside-out compilation:
        1. Recursively compile all children
        2. Process line breaks in this node's raw text content
        3. Substitute placeholders in content with compiled children
        4. Apply directive handler to produce final HTML

        Args:
            node: AST node to compile

        Returns:
            Compiled HTML for this node
        """
        from ..config import appsettings

        # PRE-COMPILATION: increment slide counter for real slides.
        # Do this before children compile so child counters are correct.
        if node.directive == "slide" and (
            node.children or (node.content and node.content.strip())
        ):
            self.slide_count += 1

        # Step 1: Recursively compile children (inside-out)
        compiled_children: list[str] = []
        for child in node.children:
            compiled_child_html = self.node_compile(child)
            compiled_children.append(compiled_child_html)

        # Step 2: Process raw text for line breaks BEFORE substituting children
        processed_content: str = node.content
        if node.directive == "body":

            def line_break_replacer(match: re.Match[str]) -> str:
                blank_lines: str | None = match.group(1)
                single_newline: str | None = match.group(2)

                if blank_lines:
                    # It's a block of 2 or more newlines.
                    # Count newlines and emit one <br /> line per newline.
                    newline_count: int = blank_lines.count("\n")
                    return "\n" + ("<br />\n" * newline_count)
                elif single_newline:
                    # It's a single newline, convert to a space.
                    return " "
                else:
                    return ""

            # This single regex handles both cases:
            # 1. A block of 2 or more newlines (and optional whitespace)
            # 2. A single newline
            processed_content = re.sub(
                r"((?:\n\s*){2,})|(\n)", line_break_replacer, processed_content
            )

        # Step 2b: Substitute placeholders in content with compiled children
        content_with_children: str = processed_content
        for i, compiled_child in enumerate(compiled_children):
            placeholder: str = appsettings.placeHolder_make(i)
            content_with_children = content_with_children.replace(
                placeholder, compiled_child
            )

        # Step 2c: Expand protected .code{} placeholders
        content_with_children = self.codeblocks_expand(content_with_children)

        # Step 2d: Expand backslash-escaped sequence placeholders
        content_with_children = self.escapes_expand(content_with_children)

        # Step 3: Create a modified node with substituted content.
        node_with_content = replace(node, content=content_with_children)

        # Step 4: Apply directive handler
        handler = self.directives.get(node.directive)

        if handler:
            result: str = handler(
                cast(DirectiveNode, node_with_content),
                cast(CompilerContext, self),
            )
        else:
            # This case handles raw text which the parser leaves in the content
            # of parent directives. After line break processing and child
            # substitution, this is just the final content.
            result = content_with_children

        return result

    def lcarsFrame_generate(self, content: str, navbar_html: str) -> str:
        """Generate LCARS frame structure wrapping slidedown content."""
        return compiler_rendering.lcarsFrame_generate(
            cast(compiler_rendering.CompilerRenderer, self),
            content,
            navbar_html,
        )

    def htmlDocument_build(self, content: str) -> str:
        """Build complete HTML document with head, nav, and footer."""
        return compiler_rendering.htmlDocument_build(
            cast(compiler_rendering.CompilerRenderer, self), content
        )

    def template_load(self, filename: str) -> str:
        """Load HTML template file"""
        return compiler_assets.template_load(
            cast(compiler_assets.CompilerAssets, self), filename
        )

    def assets_copy(self) -> None:
        """Copy CSS/JS/image assets and theme files to output directory"""
        compiler_assets.assets_copy(cast(compiler_assets.CompilerAssets, self))

    def config_getMerged(
        self, key: str, default: ConfigValue = None
    ) -> ConfigValue:
        """Get configuration value with .meta{} overrides."""
        return compiler_rendering.config_getMerged(
            cast(compiler_rendering.CompilerRenderer, self), key, default
        )

    def customCSS_generate(self) -> str:
        """Generate custom CSS from .meta{css: {...}} configuration."""
        return compiler_rendering.customCSS_generate(
            cast(compiler_rendering.CompilerRenderer, self)
        )

    def watermarks_generate(self) -> str:
        """Generate watermark HTML from merged configuration."""
        return compiler_rendering.watermarks_generate(
            cast(compiler_rendering.CompilerRenderer, self)
        )

    def footer_generate(self) -> str:
        """Generate footer HTML from .meta{footer: {...}} or template."""
        return compiler_rendering.footer_generate(
            cast(compiler_rendering.CompilerRenderer, self)
        )

    def navbar_generate(self) -> str:
        """Generate navbar HTML from .meta{navbar: {...}} or template."""
        return compiler_rendering.navbar_generate(
            cast(compiler_rendering.CompilerRenderer, self)
        )

    def blankLines_insertBreaks(self, html: str) -> str:
        """Post-process HTML to insert <br> tags for blank lines."""
        return compiler_rendering.blankLines_insertBreaks(html)
