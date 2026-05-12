"""Directive registry and HTML handlers for slidedown markup.

Each directive transforms an AST node into HTML. The registry keeps directive
metadata beside handlers so parsing, compilation, and documentation can share a
single source of truth.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, cast

import cowsay as cowsay_module
from pyfiglet import Figlet
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

from ..models.compiler import PresentationMetaConfig
from ..models.directives import DirectiveCategory, DirectiveSpec
from ..models.handlers import CompilerContext, DirectiveNode
from . import directive_groups
from .lexer import SlidedownLexer
from .log import LOG

CLASS_TOKEN_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def _ast_rebaseCodeIDs(nodes: list[Any], offset: int) -> None:
    """Rewrite CODE placeholder IDs in AST content strings by offset.

    Args:
        nodes: List of ASTNode objects to rewrite in-place.
        offset: Integer to add to every CODE_N placeholder index.
    """
    for node in nodes:
        node.content = re.sub(
            r"\x00CODE_(\d+)\x00",
            lambda m: f"\x00CODE_{int(m.group(1)) + offset}\x00",
            node.content,
        )
        _ast_rebaseCodeIDs(list(node.children), offset)


def _ast_rebaseEscapeIDs(nodes: list[Any], offset: int) -> None:
    """Rewrite ESCAPE placeholder IDs in AST content strings by offset.

    Args:
        nodes: List of ASTNode objects to rewrite in-place.
        offset: Integer to add to every ESCAPE_N placeholder index.
    """
    for node in nodes:
        node.content = re.sub(
            r"\x00ESCAPE_(\d+)\x00",
            lambda m: f"\x00ESCAPE_{int(m.group(1)) + offset}\x00",
            node.content,
        )
        _ast_rebaseEscapeIDs(list(node.children), offset)


def classNames_normalize(raw_class_names: str) -> list[str]:
    """Normalize a raw class modifier into safe CSS class tokens.

    Splits a ``.class{}`` modifier on whitespace and keeps only class names
    that are valid simple CSS tokens. Invalid tokens are dropped so user input
    cannot break the generated class attribute.

    Args:
        raw_class_names: Raw whitespace-separated class names from a parsed
            directive modifier.

    Returns:
        List of valid CSS class names in their original order.
    """
    class_names: list[str] = []
    for class_name in raw_class_names.split():
        if CLASS_TOKEN_PATTERN.fullmatch(class_name):
            class_names.append(class_name)
    return class_names


def metaYaml_dedent(yaml_content: str) -> str:
    """Dedent parser-skewed YAML metadata content.

    The parser can strip indentation from the first metadata line while later
    root-level lines keep shared indentation. This helper removes only that
    shared leading indentation after a direct YAML parse has already failed.

    Args:
        yaml_content: Raw ``.meta{}`` content after outer whitespace stripping.

    Returns:
        Dedented YAML content suitable for a second parse attempt.
    """
    lines: list[str] = yaml_content.split("\n")
    non_empty_lines: list[str] = [line for line in lines if line.strip()]

    if not non_empty_lines or len(non_empty_lines) <= 1:
        return yaml_content

    first_indent: int = len(non_empty_lines[0]) - len(
        non_empty_lines[0].lstrip()
    )
    if first_indent != 0:
        return yaml_content

    root_level_indents: list[int] = []
    for line in non_empty_lines[1:]:
        stripped: str = line.lstrip()
        if (
            stripped
            and stripped[0].isalpha()
            and ":" in stripped
            and not stripped.startswith("-")
        ):
            indent: int = len(line) - len(stripped)
            root_level_indents.append(indent)

    non_zero_indents: list[int] = [
        indent for indent in root_level_indents if indent > 0
    ]
    if not non_zero_indents:
        return yaml_content

    base_indent: int = min(non_zero_indents)
    dedented_lines: list[str] = []
    for line in lines:
        if line.strip():
            leading_spaces: int = len(line) - len(line.lstrip(" "))
            spaces_to_remove: int = min(leading_spaces, base_indent)
            dedented_lines.append(line[spaces_to_remove:])
        else:
            dedented_lines.append(line)

    return "\n".join(dedented_lines)


class DirectiveRegistry:
    """Registry of directive specifications and handlers.

    Maps directive names to DirectiveSpec objects containing metadata
    and compilation handlers.

    Attributes:
        specs: Mapping of directive names and aliases to directive specs.
    """

    def __init__(self) -> None:
        """Initialize the registry with built-in directives."""
        self.specs: dict[str, DirectiveSpec] = {}
        self.coreDirectives_register()
        self.formattingDirectives_register()
        self.effectDirectives_register()
        self.transformDirectives_register()
        self.modifierDirectives_register()
        self.metadataDirectives_register()
        self.includeDirectives_register()

    def register(self, spec: DirectiveSpec) -> None:
        """Register a directive specification.

        Args:
            spec: Directive metadata and handler to register.
        """
        self.specs[spec.name] = spec
        # Also register aliases
        for alias in spec.aliases:
            self.specs[alias] = spec

    def get(
        self, name: str
    ) -> Callable[[DirectiveNode, CompilerContext], str] | None:
        """Get a directive handler by name.

        Supports wildcard matching for pattern-based directives.

        Args:
            name: Directive name to look up.

        Returns:
            Handler function, or None when no directive matches.
        """
        # Direct match
        if name in self.specs:
            return self.specs[name].handler

        # Wildcard matching - check all specs
        for spec in self.specs.values():
            if spec.is_wildcard and spec.matches(name):
                return spec.handler

        return None

    def spec_get(self, name: str) -> DirectiveSpec | None:
        """Get full directive specification by name.

        Args:
            name: Directive name to look up.

        Returns:
            Directive specification, or None when no directive matches.
        """
        if name in self.specs:
            return self.specs[name]

        # Wildcard matching
        for spec in self.specs.values():
            if spec.is_wildcard and spec.matches(name):
                return spec

        return None

    def directives_listByCategory(
        self, category: DirectiveCategory
    ) -> list[DirectiveSpec]:
        """Get all directives in a category.

        Args:
            category: Directive category to filter by.

        Returns:
            List of directive specs in the requested category.
        """
        return [
            spec for spec in self.specs.values() if spec.category == category
        ]

    def coreDirectives_register(self) -> None:
        """Register core structural directives."""

        def slide_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a slide directive.

            Args:
                node: Parsed ``.slide{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                HTML for the slide container and hidden title metadata.
            """
            # Skip empty slides (used as examples in text, not actual slides)
            if not node.content or not node.content.strip():
                return ""

            # slide_count is incremented before children are compiled.
            slide_num: int = compiler.slide_count

            # node.content already has placeholders substituted by compiler
            content: str = node.content

            # Extract title content before title_handler returns empty.
            # Find title child node and get its content
            title_content: str = ""
            for child in node.children:
                if child.directive == "title":
                    title_content = child.content
                    break

            # Build CSS classes - add alignment class if specified
            css_classes: str = "container slide"
            align: str = node.modifiers.get("align", "")
            if align:
                css_classes += f" align-{align}"

            user_classes: list[str] = classNames_normalize(
                node.modifiers.get("class", "")
            )
            if user_classes:
                css_classes += f" {' '.join(user_classes)}"

            # Slides start hidden; JavaScript shows the active slide.
            user_style: str = node.modifiers.get("style", "")
            if user_style:
                style_attr = f'style="display:none; {user_style}"'
            else:
                style_attr = 'style="display:none;"'

            # Generate watermarks from theme config
            watermarks_html: str = compiler.watermarks_generate()

            return (
                "\n"
                f'<div id="slide-{slide_num}-title" '
                'style="display: none;">\n'
                f"    {title_content}\n"
                "</div>\n"
                f'<div class="{css_classes}" id="slide-{slide_num}" '
                f'name="slide-{slide_num}" {style_attr}>\n'
                f"    {watermarks_html}\n"
                f"    {content}\n"
                "</div>\n"
            )

        def title_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile slide title metadata.

            Args:
                node: Parsed ``.title{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Empty string because slide_handler emits title metadata.
            """
            # Title appears in a hidden slide-N-title div for navbar JS.
            return ""

        def body_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a slide body directive.

            Args:
                node: Parsed ``.body{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Compiled body HTML.
            """
            # node.content already has placeholders substituted by compiler
            content: str = node.content

            # If body contains column divs, wrap them in a flex container
            # We need to properly match nested divs by counting depth
            if '<div class="column"' in content:
                result: list[str] = []
                i: int = 0
                while i < len(content):
                    # Look for start of column
                    if content[i:].startswith('<div class="column"'):
                        # Collect all consecutive column blocks.
                        columns: list[str] = []

                        while (
                            i < len(content)
                            and '<div class="column"' in content[i : i + 20]
                        ):
                            # Match closing </div> by nesting depth.
                            tag_start: int = content.find(
                                '<div class="column"', i
                            )
                            depth: int = 0
                            j: int = tag_start

                            while j < len(content):
                                if content[j : j + 4] == "<div":
                                    depth += 1
                                elif content[j : j + 6] == "</div>":
                                    depth -= 1
                                    if depth == 0:
                                        # Found matching closing tag
                                        col_end: int = j + 6
                                        columns.append(
                                            content[tag_start:col_end]
                                        )
                                        i = col_end
                                        break
                                j += 1

                            # Skip whitespace between columns
                            while i < len(content) and content[i] in " \n\t":
                                i += 1

                            # Check if next thing is another column
                            if not content[i:].startswith(
                                '<div class="column"'
                            ):
                                break

                        # Wrap all collected columns in flex container
                        if columns:
                            result.append('<div style="display: flex;">\n')
                            result.append("\n".join(columns))
                            result.append("\n</div>\n")
                    else:
                        result.append(content[i])
                        i += 1

                content = "".join(result)

            return str(content)

        self.register(
            DirectiveSpec(
                name="slide",
                category=DirectiveCategory.STRUCTURAL,
                description="Defines a presentation slide",
                handler=slide_handler,
                requires_children=True,
                examples=[".slide{.title{Hello} .body{World}}"],
            )
        )

        self.register(
            DirectiveSpec(
                name="title",
                category=DirectiveCategory.STRUCTURAL,
                description="Slide title (metadata)",
                handler=title_handler,
                examples=[".title{My Slide Title}"],
            )
        )

        self.register(
            DirectiveSpec(
                name="body",
                category=DirectiveCategory.STRUCTURAL,
                description="Slide content container",
                handler=body_handler,
                examples=[".body{Content goes here}"],
            )
        )

    def formattingDirectives_register(self) -> None:
        """Register HTML formatting directives."""
        directive_groups.formattingDirectives_register(self)

    def effectDirectives_register(self) -> None:
        """Register special effect directives."""

        def typewriter_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a typewriter directive.

            Args:
                node: Parsed ``.typewriter{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                ``pre`` element configured for JavaScript typing.
            """
            import html

            slide_num: int = compiler.slide_count

            # node.content already has compiled child HTML.
            content: str = node.content

            # Skip empty typewriters (they break JS and serve no purpose)
            if not content or not content.strip():
                return ""

            # Track typewriter count per slide (for multiple typewriters)
            if slide_num not in compiler.typewriter_counters:
                compiler.typewriter_counters[slide_num] = 0

            compiler.typewriter_counters[slide_num] += 1
            typewriter_num: int = compiler.typewriter_counters[slide_num]

            style: str = node.modifiers.get("style", "")
            # Let CSS control inline/block display context.
            if style:
                style_attr = f' style="{style}"'
            else:
                style_attr = ""

            # Always use typewriter-{slide}-{num} format for consistency
            typewriter_id: str = f"typewriter-{slide_num}-{typewriter_num}"

            # Process backslash escapes for literal characters
            # \> → > (literal greater-than)
            # \< → < (literal less-than)
            # \& → & (literal ampersand)
            # \\ → \ (literal backslash)
            text_content: str = content.replace("\\\\", "\x00BACKSLASH\x00")
            text_content = text_content.replace("\\>", ">")
            text_content = text_content.replace("\\<", "<")
            text_content = text_content.replace("\\&", "&")
            text_content = text_content.replace("\x00BACKSLASH\x00", "\\")

            # Store text in data attribute to bypass HTML entity parsing issues
            # Escape quotes for attribute safety
            escaped_attr: str = html.escape(text_content, quote=True)

            # Typewriter content allows HTML for formatting (e.g., <b>bold</b>)
            # Use backslash escapes for literal characters (e.g., \> for >)
            return (
                f'<pre id="{typewriter_id}"{style_attr} '
                f'data-text="{escaped_attr}"></pre>'
            )

        def snippet_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a progressive reveal snippet.

            Args:
                node: Parsed ``.o{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Hidden snippet element revealed by JavaScript.
            """
            slide_num: int = compiler.slide_count

            # Skip empty snippets (they break JS and serve no purpose)
            if not node.content or not node.content.strip():
                return ""

            # Track snippet count per slide
            if slide_num not in compiler.snippet_counters:
                compiler.snippet_counters[slide_num] = 0

            compiler.snippet_counters[slide_num] += 1
            snippet_num: int = compiler.snippet_counters[slide_num]

            style: str = node.modifiers.get("style", "")
            style_attr: str = f' style="{style}"' if style else ""

            return (
                '<div class="snippet sl-hidden" '
                f'id="order-{slide_num}-{snippet_num}"'
                f"{style_attr}>{node.content}</div>"
            )

        self.register(
            DirectiveSpec(
                name="typewriter",
                category=DirectiveCategory.EFFECT,
                description="Character-by-character typing animation",
                handler=typewriter_handler,
                examples=[".typewriter{Text appears slowly}"],
            )
        )

        self.register(
            DirectiveSpec(
                name="o",
                category=DirectiveCategory.EFFECT,
                description="Progressive reveal bullet (snippet)",
                handler=snippet_handler,
                examples=[".o{First bullet}", ".o{Second bullet}"],
            )
        )

        def column_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a column layout directive.

            Args:
                node: Parsed ``.column{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Column wrapper HTML.
            """
            # Build style attribute from modifiers
            styles: list[str] = []

            # Handle align modifier
            if "align" in node.modifiers:
                styles.append(f"text-align: {node.modifiers['align']}")

            # Handle width modifier
            if "width" in node.modifiers:
                styles.append(f"width: {node.modifiers['width']}")
            else:
                # Default: flex-grow so columns split equally
                styles.append("flex: 1")

            # Add any other custom CSS from .style{}
            if "style" in node.modifiers:
                styles.append(node.modifiers["style"])

            # Build style attribute
            style_attr: str = f' style="{"; ".join(styles)}"' if styles else ""

            return f'<div class="column"{style_attr}>{node.content}</div>'

        self.register(
            DirectiveSpec(
                name="column",
                category=DirectiveCategory.EFFECT,
                description="Column layout container for side-by-side content",
                handler=column_handler,
                examples=[
                    (
                        ".column{.style{align=left; width=50%}\n"
                        "    Content here\n}"
                    ),
                    ".column{.style{width=33%}\n    Narrow column\n}",
                ],
            )
        )

    def transformDirectives_register(self) -> None:
        """Register content transformation directives."""

        def font_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a Figlet font directive.

            Args:
                node: Parsed ``.font-*{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                ``pre`` element containing rendered ASCII art.
            """
            # Extract font name from directive (e.g., 'font-doom' -> 'doom')
            font_name: str = (
                node.directive.split("-", 1)[1]
                if "-" in node.directive
                else "standard"
            )

            try:
                f: Figlet = Figlet(font=font_name)
                ascii_art: str = f.renderText(node.content)
                return f'<pre class="figlet-art">{ascii_art}</pre>'
            except Exception:
                return (
                    f'<pre class="figlet-art">'
                    f'ERROR: Figlet font "{font_name}" not found\n'
                    f"{node.content}</pre>"
                )

        def cowpy_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a cowsay-style directive.

            Args:
                node: Parsed ``.cowpy-*{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                ``pre`` element containing rendered speech bubble text.
            """
            # Extract character name (e.g., 'cowpy-tux' -> 'tux')
            char_name: str = (
                node.directive.split("-", 1)[1]
                if "-" in node.directive
                else "default"
            )

            try:
                result: str = cowsay_module.get_output_string(
                    char_name, node.content
                )
                return f"<pre>{result}</pre>"
            except Exception:
                return (
                    f'<pre>ERROR: Cowsay character "{char_name}" '
                    f"not found\n{node.content}</pre>"
                )

        # Register wildcard font directive
        self.register(
            DirectiveSpec(
                name="font-*",
                category=DirectiveCategory.TRANSFORM,
                description="ASCII art using Figlet fonts",
                handler=font_handler,
                is_wildcard=True,
                examples=[
                    ".font-standard{Text}",
                    ".font-doom{DOOM}",
                    ".font-slant{Slanted}",
                ],
            )
        )

        # Register wildcard cowsay directive
        self.register(
            DirectiveSpec(
                name="cowpy-*",
                category=DirectiveCategory.TRANSFORM,
                description="ASCII speech bubbles with characters",
                handler=cowpy_handler,
                is_wildcard=True,
                examples=[
                    ".cowpy-cow{Moo!}",
                    ".cowpy-tux{Hello from Linux}",
                    ".cowpy-dragon{Rawr!}",
                ],
            )
        )

        def code_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile inline or syntax-highlighted code.

            Args:
                node: Parsed ``.code{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Inline code HTML or Pygments-highlighted block HTML.
            """
            # Syntax-highlighted blocks carry a .syntax{} modifier.
            if "syntax" in node.modifiers:
                # SYNTAX-HIGHLIGHTED CODE BLOCK
                language: str = node.modifiers["syntax"]

                # Parse language=value if present
                if "=" in language:
                    # Handle language=python, language=c, etc.
                    language = language.split("=", 1)[1].strip()

                # Get appropriate lexer
                lexer: Lexer
                try:
                    if language.lower() in ["slidedown", "sd"]:
                        lexer = SlidedownLexer()
                    else:
                        lexer = get_lexer_by_name(language)
                except ClassNotFound:
                    # Fallback to plain text if language not found
                    lexer = TextLexer()

                # Generate highlighted HTML with inline styles
                # Inline styles keep highlighted blocks self-contained.
                pygments_style: str = compiler.theme.pygmentsStyle_get()
                formatter: HtmlFormatter = HtmlFormatter(
                    style=pygments_style, noclasses=True
                )
                highlighted: str = cast(
                    str, highlight(node.content, lexer, formatter)
                )

                return highlighted
            else:
                # INLINE CODE (no syntax highlighting, just <code> tag)
                style: str = node.modifiers.get("style", "")
                # Add !important to each CSS property to override theme styles
                if style:
                    # Split by semicolon, add !important to each property
                    properties: list[str] = [
                        p.strip() for p in style.split(";") if p.strip()
                    ]
                    important_props: list[str] = [
                        f"{p} !important" if "!important" not in p else p
                        for p in properties
                    ]
                    style = "; ".join(important_props)
                style_attr: str = f' style="{style}"' if style else ""
                return f"<code{style_attr}>{node.content}</code>"

        self.register(
            DirectiveSpec(
                name="code",
                category=DirectiveCategory.TRANSFORM,
                description="Syntax highlighted code blocks",
                handler=code_handler,
                examples=[
                    (
                        ".code{.syntax{language=python}\n"
                        "def hello():\n    print('Hi')\n}"
                    ),
                    (
                        ".code{.syntax{language=slidedown}\n"
                        ".slide{.title{Demo}}\n}"
                    ),
                    ".code{.syntax{language=c}\nint main() { return 0; }\n}",
                ],
            )
        )

        def comment_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile a comment directive.

            Args:
                node: Parsed ``.comment{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Empty string because comments are stripped from output.
            """
            return ""

        self.register(
            DirectiveSpec(
                name="comment",
                category=DirectiveCategory.STRUCTURAL,
                description="Comments that are stripped from compiled output",
                handler=comment_handler,
                examples=[
                    ".comment{This is a comment}",
                    ".comment{TODO: Fix this slide later}",
                    ".comment{Multi-line\ncomment\ntext}",
                ],
            )
        )

    def modifierDirectives_register(self) -> None:
        """Register reserved modifier directives.

        These are handled specially by the parser - they're extracted
        into the modifiers dict rather than creating child nodes.
        """
        directive_groups.modifierDirectives_register(self)

    def metadataDirectives_register(self) -> None:
        """Register metadata directives.

        These directives provide presentation-level metadata and configuration
        that overrides theme settings.
        """

        def meta_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Compile presentation metadata.

            Parses YAML content, validates file paths, and stores in compiler
            for merging with theme configuration.

            Args:
                node: Parsed ``.meta{}`` AST node.
                compiler: Active compiler instance.

            Returns:
                Empty string because metadata is not visible slide content.
            """
            import yaml

            # node.content contains the YAML configuration
            yaml_content: str = node.content.strip()

            if not yaml_content:
                return ""

            try:
                # Parse first; valid YAML should not be dedented further.
                try:
                    meta_config: PresentationMetaConfig | None = (
                        yaml.safe_load(yaml_content)
                    )
                except yaml.YAMLError:
                    meta_config = None

                # Dedent YAML content only when the direct parse fails.
                # The parser strips leading whitespace from the first line but
                # can leave it on later lines. Remove the shared indent.
                if not isinstance(meta_config, dict):
                    yaml_content = metaYaml_dedent(yaml_content)
                    meta_config = yaml.safe_load(yaml_content)

                if meta_config is None:
                    meta_config = cast(PresentationMetaConfig, {})

                # Store in compiler for later merging
                if not hasattr(compiler, "meta_config"):
                    compiler.meta_config = {}

                # Merge into compiler meta_config
                compiler.meta_config.update(meta_config)

            except yaml.YAMLError as e:
                from .log import LOG

                LOG(f"Error parsing .meta{{}} YAML: {e}", level=1)
                return ""
            except Exception as e:
                from .log import LOG

                LOG(f"Error processing .meta{{}}: {e}", level=1)
                return ""

            # .meta{} doesn't produce any output HTML
            return ""

        self.register(
            DirectiveSpec(
                name="meta",
                category=DirectiveCategory.METADATA,
                description=(
                    "Presentation metadata and configuration "
                    "(overrides theme settings)"
                ),
                handler=meta_handler,
                examples=[
                    ".meta{\n  navigation:\n    show_buttons: false\n}",
                    (
                        ".meta{\n  watermarks:\n"
                        "    - image: logos/company.svg\n"
                        "      position: bottom-right\n}"
                    ),
                ],
            )
        )

    def includeDirectives_register(self) -> None:
        """Register the .include{} directive for multi-file composition."""

        def include_handler(
            node: DirectiveNode, compiler: CompilerContext
        ) -> str:
            """Include and compile another .sd file inline.

            Reads the target file relative to the current file's directory,
            parses it, strips top-level ``.meta{}`` nodes (the parent deck's
            metadata is authoritative), rebases code-block placeholder IDs to
            avoid collisions, and compiles the result into the parent document.

            Circular includes are detected and raise ``RecursionError``.

            Args:
                node: Parsed ``.include{}`` AST node; content is the path.
                compiler: Active compiler instance.

            Returns:
                Compiled HTML for the included file's content.
            """
            from pathlib import Path as _Path

            from .parser import Parser

            relative_path = node.content.strip()
            if not relative_path:
                LOG(".include{} called with empty path — skipping", level=1)
                return ""

            # Resolve relative to the containing file's directory
            target = (compiler.input_dir / relative_path).resolve()

            if not target.exists():
                raise FileNotFoundError(
                    f".include{{{relative_path}}}: file not found at {target}"
                )

            # Circular include guard
            include_stack: set[_Path] = getattr(
                compiler, "_include_stack", set()
            )
            if target in include_stack:
                raise RecursionError(
                    f".include{{{relative_path}}}: "
                    f"circular include detected ({target})"
                )
            include_stack.add(target)
            # Persist the stack on the concrete compiler object
            try:
                object.__setattr__(compiler, "_include_stack", include_stack)
            except (AttributeError, TypeError):
                pass

            try:
                source = target.read_text(encoding="utf-8")
                parser = Parser(source, debug=False)
                included_ast = parser.parse()

                # Strip top-level .meta{} nodes — parent deck is authoritative
                filtered_ast = [
                    n for n in included_ast if n.directive != "meta"
                ]

                # Rebase code-block placeholder IDs to avoid collisions
                parent_blocks: dict[int, str] = getattr(
                    compiler, "protected_code_blocks", {}
                )
                id_offset = (
                    max(parent_blocks.keys()) + 1 if parent_blocks else 0
                )
                if parser.protected_code_blocks:
                    _ast_rebaseCodeIDs(filtered_ast, id_offset)
                    for k, v in parser.protected_code_blocks.items():
                        parent_blocks[k + id_offset] = v

                # Rebase escape-sequence placeholder IDs similarly
                parent_escapes: dict[int, str] = getattr(
                    compiler, "escaped_sequences", {}
                )
                esc_offset = (
                    max(parent_escapes.keys()) + 1 if parent_escapes else 0
                )
                if parser.escaped_sequences:
                    _ast_rebaseEscapeIDs(filtered_ast, esc_offset)
                    for k, v in parser.escaped_sequences.items():
                        parent_escapes[k + esc_offset] = v

                return compiler.ast_compile(filtered_ast)

            finally:
                include_stack.discard(target)

        self.register(
            DirectiveSpec(
                name="include",
                category=DirectiveCategory.STRUCTURAL,
                description=(
                    "Include and compile another .sd file inline. "
                    "Path is relative to the containing file's directory."
                ),
                handler=include_handler,
                examples=[
                    ".include{chapters/intro.sd}",
                    ".include{../shared/title-slide.sd}",
                ],
            )
        )
