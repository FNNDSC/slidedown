"""
Directive implementations for slidedown

Each directive transforms AST nodes into HTML with appropriate attributes/structure.
Uses DirectiveSpec for metadata and validation.
"""

from typing import Callable, Dict, Optional, Any
from pyfiglet import Figlet
import cowsay as cowsay_module
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.lexer import Lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from ..models.directives import DirectiveSpec, DirectiveCategory, RESERVED_DIRECTIVES
from .lexer import SlidedownLexer


class DirectiveRegistry:
    """
    Registry of directive specifications and handlers

    Maps directive names to DirectiveSpec objects containing metadata
    and compilation handlers.
    """

    def __init__(self) -> None:
        """Initialize the directive registry and register all built-in directives"""
        self.specs: Dict[str, DirectiveSpec] = {}
        self.coreDirectives_register()
        self.formattingDirectives_register()
        self.effectDirectives_register()
        self.transformDirectives_register()
        self.modifierDirectives_register()
        self.metadataDirectives_register()

    def register(self, spec: DirectiveSpec) -> None:
        """Register a directive specification"""
        self.specs[spec.name] = spec
        # Also register aliases
        for alias in spec.aliases:
            self.specs[alias] = spec

    def get(self, name: str) -> Optional[Callable[[Any, Any], str]]:
        """
        Get directive handler by name

        Supports wildcard matching for pattern-based directives (font-*, cowpy-*)

        Args:
            name: Directive name to look up

        Returns:
            Handler function or None if not found
        """
        # Direct match
        if name in self.specs:
            return self.specs[name].handler

        # Wildcard matching - check all specs
        for spec in self.specs.values():
            if spec.is_wildcard and spec.matches(name):
                return spec.handler

        return None

    def spec_get(self, name: str) -> Optional[DirectiveSpec]:
        """Get full directive specification by name"""
        if name in self.specs:
            return self.specs[name]

        # Wildcard matching
        for spec in self.specs.values():
            if spec.is_wildcard and spec.matches(name):
                return spec

        return None

    def directives_listByCategory(self, category: DirectiveCategory) -> list[DirectiveSpec]:
        """Get all directives in a category"""
        return [spec for spec in self.specs.values() if spec.category == category]

    def coreDirectives_register(self) -> None:
        """Register core structural directives"""

        def slide_handler(node: Any, compiler: Any) -> str:
            """Handle .slide{} - compile to slide div"""
            # Skip empty slides (used as examples in text, not actual slides)
            if not node.content or not node.content.strip():
                return ''

            # slide_count incremented in compiler.node_compile BEFORE children compiled
            slide_num = compiler.slide_count

            # node.content already has placeholders substituted by compiler
            content = node.content

            # Extract title content from children (before title_handler returned empty)
            # Find title child node and get its content
            title_content = ""
            for child in node.children:
                if child.directive == 'title':
                    title_content = child.content
                    break

            # Build CSS classes - add alignment class if specified
            css_classes = "container slide"
            align = node.modifiers.get('align', '')
            if align:
                css_classes += f" align-{align}"

            # Build style attribute - all slides hidden by default, JS shows slide 1
            user_style = node.modifiers.get('style', '')
            if user_style:
                style_attr = f'style="display:none; {user_style}"'
            else:
                style_attr = 'style="display:none;"'

            # Generate watermarks from theme config
            watermarks_html = compiler.watermarks_generate()

            return f"""
                <div id="slide-{slide_num}-title" style="display: none;">
                    {title_content}
                </div>
                <div class="{css_classes}" id="slide-{slide_num}" name="slide-{slide_num}" {style_attr}>
                    {watermarks_html}
                    {content}
                </div>
            """

        def title_handler(node: Any, compiler: Any) -> str:
            """Handle .title{} - slide title metadata (displayed in navbar, not body)"""
            # Title content is stored in hidden slide-N-title div (see slide_handler)
            # and displayed in navbar via JS, so we return empty string here
            return ""

        def body_handler(node: Any, compiler: Any) -> str:
            """Handle .body{} - slide content area"""
            # node.content already has placeholders substituted by compiler
            content = node.content

            # If body contains column divs, wrap them in a flex container
            # We need to properly match nested divs by counting depth
            if '<div class="column"' in content:
                result = []
                i = 0
                while i < len(content):
                    # Look for start of column
                    if content[i:].startswith('<div class="column"'):
                        # Found start of columns - collect all consecutive columns
                        flex_start = i
                        columns = []

                        while i < len(content) and '<div class="column"' in content[i:i+20]:
                            # Find the opening tag
                            col_start = i

                            # Find matching closing </div> by counting nesting depth
                            tag_start = content.find('<div class="column"', i)
                            depth = 0
                            j = tag_start

                            while j < len(content):
                                if content[j:j+4] == '<div':
                                    depth += 1
                                elif content[j:j+6] == '</div>':
                                    depth -= 1
                                    if depth == 0:
                                        # Found matching closing tag
                                        col_end = j + 6
                                        columns.append(content[tag_start:col_end])
                                        i = col_end
                                        break
                                j += 1

                            # Skip whitespace between columns
                            while i < len(content) and content[i] in ' \n\t':
                                i += 1

                            # Check if next thing is another column
                            if not content[i:].startswith('<div class="column"'):
                                break

                        # Wrap all collected columns in flex container
                        if columns:
                            result.append('<div style="display: flex;">\n')
                            result.append('\n'.join(columns))
                            result.append('\n</div>\n')
                    else:
                        result.append(content[i])
                        i += 1

                content = ''.join(result)

            return content

        self.register(DirectiveSpec(
            name='slide',
            category=DirectiveCategory.STRUCTURAL,
            description='Defines a presentation slide',
            handler=slide_handler,
            requires_children=True,
            examples=['.slide{.title{Hello} .body{World}}']
        ))

        self.register(DirectiveSpec(
            name='title',
            category=DirectiveCategory.STRUCTURAL,
            description='Slide title (metadata)',
            handler=title_handler,
            examples=['.title{My Slide Title}']
        ))

        self.register(DirectiveSpec(
            name='body',
            category=DirectiveCategory.STRUCTURAL,
            description='Slide content container',
            handler=body_handler,
            examples=['.body{Content goes here}']
        ))

    def formattingDirectives_register(self) -> None:
        """Register HTML formatting directives"""

        def make_html_wrapper(tag: str) -> Callable[[Any, Any], str]:
            """Factory for simple HTML tag wrappers"""
            def handler(node: Any, compiler: Any) -> str:
                """Wrap content in HTML tag with optional style modifier"""
                style = node.modifiers.get('style', '')
                style_attr = f' style="{style}"' if style else ''
                return f'<{tag}{style_attr}>{node.content}</{tag}>'
            return handler

        formatting_specs = [
            ('bf', 'strong', 'Bold/strong text', ['.bf{bold text}']),
            ('em', 'em', 'Emphasized/italic text', ['.em{italic text}']),
            ('tt', 'tt', 'Teletype/monospace text', ['.tt{monospace}']),
            # NOTE: .code{} is registered in transformDirectives_register() for syntax highlighting
            # ('code', 'code', 'Inline code', ['.code{function()}']),
            ('underline', 'u', 'Underlined text', ['.underline{underlined}']),
        ]

        for name, tag, desc, examples in formatting_specs:
            self.register(DirectiveSpec(
                name=name,
                category=DirectiveCategory.FORMATTING,
                description=desc,
                handler=make_html_wrapper(tag),
                examples=examples
            ))

        # Heading aliases - cleaner syntax than <h1></h1>
        heading_specs = [
            ('h1', 'h1', 'Heading level 1 (largest)', ['.h1{Main Title}']),
            ('h2', 'h2', 'Heading level 2', ['.h2{Section Title}']),
            ('h3', 'h3', 'Heading level 3', ['.h3{Subsection Title}']),
            ('h4', 'h4', 'Heading level 4', ['.h4{Minor Heading}']),
            ('h5', 'h5', 'Heading level 5', ['.h5{Small Heading}']),
            ('h6', 'h6', 'Heading level 6 (smallest)', ['.h6{Tiny Heading}']),
        ]

        for name, tag, desc, examples in heading_specs:
            self.register(DirectiveSpec(
                name=name,
                category=DirectiveCategory.FORMATTING,
                description=desc,
                handler=make_html_wrapper(tag),
                examples=examples
            ))

    def effectDirectives_register(self) -> None:
        """Register special effect directives"""

        def typewriter_handler(node: Any, compiler: Any) -> str:
            """Handle .typewriter{} - character-by-character typing animation"""
            slide_num = compiler.slide_count

            # node.content already has children compiled and placeholders substituted
            content = node.content

            # Skip empty typewriters (they break JS and serve no purpose)
            if not content or not content.strip():
                return ''

            # Track typewriter count per slide (for multiple typewriters)
            if slide_num not in compiler.typewriter_counters:
                compiler.typewriter_counters[slide_num] = 0

            compiler.typewriter_counters[slide_num] += 1
            typewriter_num = compiler.typewriter_counters[slide_num]

            style = node.modifiers.get('style', '')
            style_attr = f' style="{style}"' if style else ''

            # Always use typewriter-{slide}-{num} format for consistency
            typewriter_id = f'typewriter-{slide_num}-{typewriter_num}'

            return f'<pre id="{typewriter_id}"{style_attr}>{content}</pre>'

        def snippet_handler(node: Any, compiler: Any) -> str:
            """Handle .o{} - progressive reveal bullet point"""
            slide_num = compiler.slide_count

            # Skip empty snippets (they break JS and serve no purpose)
            if not node.content or not node.content.strip():
                return ''

            # Track snippet count per slide
            if slide_num not in compiler.snippet_counters:
                compiler.snippet_counters[slide_num] = 0

            compiler.snippet_counters[slide_num] += 1
            snippet_num = compiler.snippet_counters[slide_num]

            style = node.modifiers.get('style', '')
            style_attr = f' style="{style}"' if style else ''

            return f'''<div class="snippet" id="order-{slide_num}-{snippet_num}"{style_attr}>{node.content}</div>'''

        self.register(DirectiveSpec(
            name='typewriter',
            category=DirectiveCategory.EFFECT,
            description='Character-by-character typing animation',
            handler=typewriter_handler,
            examples=['.typewriter{Text appears slowly}']
        ))

        self.register(DirectiveSpec(
            name='o',
            category=DirectiveCategory.EFFECT,
            description='Progressive reveal bullet (snippet)',
            handler=snippet_handler,
            examples=['.o{First bullet}', '.o{Second bullet}']
        ))

        def column_handler(node: Any, compiler: Any) -> str:
            """Handle .column{} - column layout container with optional styling"""
            # Build style attribute from modifiers
            styles = []

            # Handle align modifier
            if 'align' in node.modifiers:
                styles.append(f"text-align: {node.modifiers['align']}")

            # Handle width modifier
            if 'width' in node.modifiers:
                styles.append(f"width: {node.modifiers['width']}")
            else:
                # Default: flex-grow so columns split equally
                styles.append("flex: 1")

            # Add any other custom CSS from .style{}
            if 'style' in node.modifiers:
                styles.append(node.modifiers['style'])

            # Build style attribute
            style_attr = f' style="{"; ".join(styles)}"' if styles else ''

            return f'<div class="column"{style_attr}>{node.content}</div>'

        self.register(DirectiveSpec(
            name='column',
            category=DirectiveCategory.EFFECT,
            description='Column layout container for side-by-side content',
            handler=column_handler,
            examples=[
                '.column{.style{align=left; width=50%}\n    Content here\n}',
                '.column{.style{width=33%}\n    Narrow column\n}'
            ]
        ))

    def transformDirectives_register(self) -> None:
        """Register content transformation directives (ASCII art)"""

        def font_handler(node: Any, compiler: Any) -> str:
            """Handle .font-<name>{} - figlet ASCII art"""
            # Extract font name from directive (e.g., 'font-doom' -> 'doom')
            font_name = node.directive.split('-', 1)[1] if '-' in node.directive else 'standard'

            try:
                f = Figlet(font=font_name)
                ascii_art = f.renderText(node.content)
                return f'<pre>{ascii_art}</pre>'
            except Exception as e:
                return f'<pre>ERROR: Figlet font "{font_name}" not found\n{node.content}</pre>'

        def cowpy_handler(node: Any, compiler: Any) -> str:
            """Handle .cowpy-<char>{} - cowsay speech bubbles"""
            # Extract character name (e.g., 'cowpy-tux' -> 'tux')
            char_name = node.directive.split('-', 1)[1] if '-' in node.directive else 'default'

            try:
                result = cowsay_module.get_output_string(char_name, node.content)
                return f'<pre>{result}</pre>'
            except Exception as e:
                return f'<pre>ERROR: Cowsay character "{char_name}" not found\n{node.content}</pre>'

        # Register wildcard font directive
        self.register(DirectiveSpec(
            name='font-*',
            category=DirectiveCategory.TRANSFORM,
            description='ASCII art using Figlet fonts',
            handler=font_handler,
            is_wildcard=True,
            examples=[
                '.font-standard{Text}',
                '.font-doom{DOOM}',
                '.font-slant{Slanted}'
            ]
        ))

        # Register wildcard cowsay directive
        self.register(DirectiveSpec(
            name='cowpy-*',
            category=DirectiveCategory.TRANSFORM,
            description='ASCII speech bubbles with characters',
            handler=cowpy_handler,
            is_wildcard=True,
            examples=[
                '.cowpy-cow{Moo!}',
                '.cowpy-tux{Hello from Linux}',
                '.cowpy-dragon{Rawr!}'
            ]
        ))

        def code_handler(node: Any, compiler: Any) -> str:
            """Handle .code{} - inline code OR syntax highlighted code blocks"""
            # Check if this is a syntax-highlighted code block (has .syntax{} modifier)
            if 'syntax' in node.modifiers:
                # SYNTAX-HIGHLIGHTED CODE BLOCK
                language = node.modifiers['syntax']

                # Parse language=value if present
                if '=' in language:
                    # Handle language=python, language=c, etc.
                    language = language.split('=', 1)[1].strip()

                # Get appropriate lexer
                lexer: Lexer
                try:
                    if language.lower() in ['slidedown', 'sd']:
                        lexer = SlidedownLexer()
                    else:
                        lexer = get_lexer_by_name(language)
                except ClassNotFound:
                    # Fallback to plain text if language not found
                    lexer = TextLexer()

                # Generate highlighted HTML with inline styles
                # noclasses=True means styles are inline, no external CSS needed
                formatter = HtmlFormatter(style='monokai', noclasses=True)
                highlighted = highlight(node.content, lexer, formatter)

                return highlighted
            else:
                # INLINE CODE (no syntax highlighting, just <code> tag)
                style = node.modifiers.get('style', '')
                style_attr = f' style="{style}"' if style else ''
                return f'<code{style_attr}>{node.content}</code>'

        self.register(DirectiveSpec(
            name='code',
            category=DirectiveCategory.TRANSFORM,
            description='Syntax highlighted code blocks',
            handler=code_handler,
            examples=[
                '.code{.syntax{language=python}\ndef hello():\n    print("Hi")\n}',
                '.code{.syntax{language=slidedown}\n.slide{.title{Demo}}\n}',
                '.code{.syntax{language=c}\nint main() { return 0; }\n}'
            ]
        ))

        def comment_handler(node: Any, compiler: Any) -> str:
            """Handle .comment{} - stripped from output"""
            return ""

        self.register(DirectiveSpec(
            name='comment',
            category=DirectiveCategory.STRUCTURAL,
            description='Comments that are stripped from compiled output',
            handler=comment_handler,
            examples=[
                '.comment{This is a comment}',
                '.comment{TODO: Fix this slide later}',
                '.comment{Multi-line\ncomment\ntext}'
            ]
        ))

    def modifierDirectives_register(self) -> None:
        """
        Register reserved modifier directives

        These are handled specially by the parser - they're extracted
        into the modifiers dict rather than creating child nodes.
        """

        def style_handler(node: Any, compiler: Any) -> str:
            """Should never be called - .style{} extracted by parser"""
            return ""

        def class_handler(node: Any, compiler: Any) -> str:
            """Should never be called - .class{} extracted by parser"""
            return ""

        self.register(DirectiveSpec(
            name='style',
            category=DirectiveCategory.MODIFIER,
            description='Inline CSS styles (parser-extracted modifier)',
            handler=style_handler,
            examples=['.slide{.style{color: red} .body{Content}}']
        ))

        self.register(DirectiveSpec(
            name='class',
            category=DirectiveCategory.MODIFIER,
            description='CSS class name (parser-extracted modifier)',
            handler=class_handler,
            examples=['.slide{.class{special-slide} .body{Content}}']
        ))

        def syntax_handler(node: Any, compiler: Any) -> str:
            """Should never be called - .syntax{} extracted by parser"""
            return ""

        self.register(DirectiveSpec(
            name='syntax',
            category=DirectiveCategory.MODIFIER,
            description='Programming language for .code{} (parser-extracted modifier)',
            handler=syntax_handler,
            examples=['.code{.syntax{language=python} def foo(): pass}']
        ))

    def metadataDirectives_register(self) -> None:
        """
        Register metadata directives

        These directives provide presentation-level metadata and configuration
        that overrides theme settings.
        """

        def meta_handler(node: Any, compiler: Any) -> str:
            """
            Handle .meta{} - presentation metadata and configuration

            Parses YAML content, validates file paths, and stores in compiler
            for merging with theme configuration.
            """
            import yaml
            from pathlib import Path

            # node.content contains the YAML configuration
            yaml_content = node.content.strip()

            if not yaml_content:
                return ""

            try:
                # Dedent YAML content
                # The parser strips leading whitespace from the first line but may leave
                # it on subsequent lines. We need to detect and remove this base indentation.
                lines = yaml_content.split('\n')
                non_empty_lines = [line for line in lines if line.strip()]

                if non_empty_lines and len(non_empty_lines) > 1:
                    # The parser strips leading whitespace from the first line but may leave
                    # it on subsequent lines. We detect this by looking at the indentation
                    # of lines that appear to be at the root level.

                    first_indent = len(non_empty_lines[0]) - len(non_empty_lines[0].lstrip())

                    # Find lines that look like root-level YAML keys
                    # These are lines that: start with a letter (after spaces), contain :,
                    # and are not list items (don't start with -)
                    root_level_indents = []
                    for i, line in enumerate(non_empty_lines):
                        stripped = line.lstrip()
                        if (stripped and
                            stripped[0].isalpha() and
                            ':' in stripped and
                            not stripped.startswith('-')):
                            indent = len(line) - len(stripped)
                            # Skip the first line's indent, we want to find the base indent of others
                            if i > 0 or indent > 0:
                                root_level_indents.append(indent)

                    # Get the minimum non-zero indentation as base indent
                    non_zero_indents = [ind for ind in root_level_indents if ind > 0]

                    if first_indent == 0 and non_zero_indents:
                        # Find the smallest non-zero indent - this is likely the base indentation
                        # that needs to be removed from all lines
                        base_indent = min(non_zero_indents)

                        # Remove base_indent spaces from all lines (only remove actual spaces, not content)
                        dedented_lines = []
                        for line in lines:
                            if line.strip():  # Non-empty line
                                # Count leading spaces
                                leading_spaces = len(line) - len(line.lstrip(' '))
                                # Remove up to base_indent spaces (but not more than exist)
                                spaces_to_remove = min(leading_spaces, base_indent)
                                dedented_lines.append(line[spaces_to_remove:])
                            else:  # Empty line
                                dedented_lines.append(line)
                        yaml_content = '\n'.join(dedented_lines)

                # Parse YAML
                meta_config = yaml.safe_load(yaml_content)
                if meta_config is None:
                    meta_config = {}

                # Store in compiler for later merging
                if not hasattr(compiler, 'meta_config'):
                    compiler.meta_config = {}

                # Validate watermark image paths if present
                if 'watermarks' in meta_config:
                    watermarks = meta_config['watermarks']
                    if not isinstance(watermarks, list):
                        watermarks = [watermarks]

                    for wm in watermarks:
                        if isinstance(wm, dict) and 'image' in wm:
                            # Resolve path relative to input directory
                            image_path = wm['image']
                            # Input dir is the directory of the source file
                            # We'll validate this path during compilation
                            # Store it as-is for now
                            pass

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

        self.register(DirectiveSpec(
            name='meta',
            category=DirectiveCategory.METADATA,
            description='Presentation metadata and configuration (overrides theme settings)',
            handler=meta_handler,
            examples=[
                '.meta{\n  navigation:\n    show_buttons: false\n}',
                '.meta{\n  watermarks:\n    - image: logos/company.svg\n      position: bottom-right\n}'
            ]
        ))
