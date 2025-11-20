"""
Compiler for slidedown AST to HTML

Transforms parsed AST nodes into complete HTML presentation.
"""

import os
import re
import shutil
from typing import List, Dict, Optional, Any
from pathlib import Path

from .parser import ASTNode
from .directives import DirectiveRegistry
from .log import LOG
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
        ast: List[ASTNode],
        output_dir: str,
        assets_dir: str,
        verbosity: int = 1,
        protected_code_blocks: Optional[Dict[int, str]] = None,
        escaped_sequences: Optional[Dict[int, str]] = None,
        theme_name: str = "default",
        input_dir: str = "."
    ) -> None:
        """
        Initialize compiler

        Args:
            ast: Parsed abstract syntax tree
            output_dir: Directory for compiled output
            assets_dir: Directory containing runtime assets (css/js/html)
            verbosity: Output verbosity level (0-3)
            protected_code_blocks: Dict of protected .code{} block content from parser
            escaped_sequences: Dict of backslash-escaped content from parser
            theme_name: Name of theme to use (default: "default")
            input_dir: Input directory for resolving relative paths (default: ".")
        """
        self.ast = ast
        self.output_dir = Path(output_dir)
        self.assets_dir = Path(assets_dir)
        self.input_dir = Path(input_dir)
        self.verbosity = verbosity
        self.protected_code_blocks = protected_code_blocks or {}
        self.escaped_sequences = escaped_sequences or {}
        self.directives = DirectiveRegistry()

        # Load theme
        self.theme = Theme(theme_name)
        LOG(f"Loaded theme: {self.theme.name}", level=2)

        self.slide_count = 0
        self.snippet_counters: Dict[int, int] = {}  # slide_num -> snippet_count
        self.typewriter_counters: Dict[int, int] = {}  # slide_num -> typewriter_count
        self.meta_config: Dict[str, Any] = {}  # Configuration from .meta{} directive

    def compile(self) -> Dict[str, Any]:
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

        # Build complete HTML document
        full_html = self.htmlDocument_build(html_content)

        # Write output file
        output_file = self.output_dir / "index.html"
        output_file.write_text(full_html, encoding='utf-8')
        LOG(f"Wrote {output_file}", level=2)

        # Copy runtime assets
        self.assets_copy()

        LOG("HTML document assembled", level=2)

        return {
            'status': True,
            'output_file': str(output_file),
            'slide_count': self.slide_count,
        }

    def ast_compile(self, nodes: List[ASTNode]) -> str:
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
        html_parts = []

        for node in nodes:
            # Compile this node (which recursively compiles children)
            compiled_node_html = self.node_compile(node)
            html_parts.append(compiled_node_html)

        return '\n'.join(html_parts)

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
        import re
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.lexer import Lexer
        from pygments.formatters import HtmlFormatter
        from pygments.util import ClassNotFound
        from .lexer import SlidedownLexer

        def expand_code_placeholder(match: re.Match[str]) -> str:
            """Expand a CODE_N placeholder with syntax-highlighted content"""
            code_id = int(match.group(1))
            if code_id not in self.protected_code_blocks:
                return match.group(0)  # Leave placeholder if not found

            raw_content = self.protected_code_blocks[code_id]

            # Extract .syntax{language=X} modifier if present
            syntax_match = re.match(r'^\s*\.syntax\{([^}]+)\}\s*', raw_content)
            if syntax_match:
                language_spec = syntax_match.group(1)
                # Remove .syntax{} from content
                code_content = raw_content[syntax_match.end():]

                # Parse language=value
                if '=' in language_spec:
                    language = language_spec.split('=', 1)[1].strip()
                else:
                    language = language_spec.strip()
            else:
                # No .syntax{} modifier, treat as plain text
                language = 'text'
                code_content = raw_content

            # Get lexer
            lexer: Lexer
            try:
                if language.lower() in ['slidedown', 'sd']:
                    lexer = SlidedownLexer()
                else:
                    lexer = get_lexer_by_name(language)
            except ClassNotFound:
                lexer = TextLexer()

            # Generate highlighted HTML (use theme's Pygments style)
            pygments_style = self.theme.pygmentsStyle_get()
            formatter = HtmlFormatter(style=pygments_style, noclasses=True)
            highlighted = highlight(code_content, lexer, formatter)

            return highlighted

        # Replace all \x00CODE_N\x00 placeholders
        result = re.sub(r'\x00CODE_(\d+)\x00', expand_code_placeholder, content)
        return result

    def escapes_expand(self, content: str) -> str:
        """
        Expand backslash-escaped sequence placeholders to literal text

        Finds \x00ESCAPE_N\x00 placeholders in content and replaces them with
        the stored escaped content (e.g., ".directive{...}" becomes literal text).

        Args:
            content: String potentially containing ESCAPE placeholders

        Returns:
            Content with placeholders replaced by literal escaped text
        """
        import re
        import html

        def expand_escape_placeholder(match: re.Match[str]) -> str:
            """Expand an ESCAPE_N placeholder with literal escaped content"""
            escape_id = int(match.group(1))
            if escape_id not in self.escaped_sequences:
                return match.group(0)  # Leave placeholder if not found

            # Return the literal content, HTML-escaped for safety
            escaped_content = self.escaped_sequences[escape_id]
            return html.escape(escaped_content)

        result = re.sub(r'\x00ESCAPE_(\d+)\x00', expand_escape_placeholder, content)
        return result

    def node_compile(self, node: ASTNode) -> str:
        """
        Compile a single AST node to HTML

        Uses inside-out compilation:
        1. Recursively compile all children
        2. Substitute placeholders in content with compiled children
        3. Apply directive handler to produce final HTML

        Args:
            node: AST node to compile

        Returns:
            Compiled HTML for this node
        """
        from ..config import appsettings

        # PRE-COMPILATION: Increment slide counter for real slides (not empty examples)
        # Must happen BEFORE children compile so snippets/typewriters see correct number
        if node.directive == 'slide' and (node.children or (node.content and node.content.strip())):
            self.slide_count += 1

        # Step 1: Recursively compile children (inside-out)
        compiled_children = []
        for child in node.children:
            compiled_child_html = self.node_compile(child)
            compiled_children.append(compiled_child_html)

        # Step 2: Substitute placeholders in content with compiled children
        content_with_children = node.content
        for i, compiled_child in enumerate(compiled_children):
            placeholder = appsettings.placeHolder_make(i)
            content_with_children = content_with_children.replace(
                placeholder, compiled_child
            )

        # Step 2b: Expand protected .code{} placeholders
        content_with_children = self.codeblocks_expand(content_with_children)

        # Step 2c: Expand backslash-escaped sequence placeholders
        content_with_children = self.escapes_expand(content_with_children)

        # Step 3: Create a modified node with substituted content
        # (We don't modify original node, create view with substituted content)
        node_with_content = node
        original_content = node.content
        node.content = content_with_children

        # Step 4: Apply directive handler
        handler = self.directives.get(node.directive)

        if handler:
            result = handler(node, self)
        else:
            LOG(f"Warning: Unknown directive '{node.directive}'", level=2)
            # Fallback: just wrap in div with class
            result = f'<div class="directive-{node.directive}">{content_with_children}</div>'

        # Restore original content (in case node is reused)
        node.content = original_content

        return result

    def htmlDocument_build(self, content: str) -> str:
        """
        Build complete HTML document with head, nav, footer

        Args:
            content: Compiled slide content

        Returns:
            Complete HTML document
        """
        # Load HTML templates
        head_html = self.template_load('head.html')
        footer_html = self.footer_generate()
        navbar_html = self.navbar_generate()

        # Generate custom CSS from .meta{css: ...}
        custom_css = self.customCSS_generate()

        # Assemble document with presentation viewport wrapper
        html = f"""<!DOCTYPE html>
<html>
{head_html}{custom_css}
<body>
    <div class="presentation-viewport">
        <div class="metaData" id="numberOfSlides" style="display: none;">{self.slide_count}</div>
        <div class="metaData" id="slideIDprefix" style="display: none;">slide-</div>

        {navbar_html}

        <div class="formLayout">
            {content}
        </div>

        {footer_html}
    </div>

    <script src="js/slidedown.js"></script>
</body>
</html>"""

        return html

    def template_load(self, filename: str) -> str:
        """Load HTML template file"""
        template_path = self.assets_dir / 'html' / filename
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        else:
            LOG(f"Warning: Template {filename} not found", level=2)
            return ""

    def assets_copy(self) -> None:
        """Copy CSS/JS/image assets and theme files to output directory"""
        # Copy standard slidedown assets
        for asset_dir in ['css', 'js', 'images', 'logos']:
            src = self.assets_dir / asset_dir
            dst = self.output_dir / asset_dir

            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                LOG(f"Copied {asset_dir}/ to output", level=3)

        # Copy theme CSS
        theme_css_path = self.theme.cssPath_get()
        if theme_css_path and theme_css_path.exists():
            dst_css = self.output_dir / "css" / "theme.css"
            dst_css.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(theme_css_path, dst_css)
            LOG(f"Copied theme CSS: {self.theme.name}", level=2)

        # Copy theme assets
        theme_assets_dir = self.theme.assetsDir_get()
        if theme_assets_dir and theme_assets_dir.exists():
            dst_theme_assets = self.output_dir / "theme-assets"
            shutil.copytree(theme_assets_dir, dst_theme_assets, dirs_exist_ok=True)
            LOG(f"Copied theme assets: {theme_assets_dir}", level=3)

    def config_getMerged(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with .meta{} overrides.

        Precedence: .meta{} config > theme config > default

        Args:
            key: Configuration key (supports dot notation like 'slide_master.watermarks')
            default: Default value if key not found

        Returns:
            Configuration value from meta or theme, or default
        """
        # Check meta_config first (highest priority)
        keys = key.split('.')
        value = self.meta_config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Not found in meta, check theme
                return self.theme.config_get(key, default)
        return value

    def customCSS_generate(self) -> str:
        """
        Generate custom CSS from .meta{css: {...}} configuration.

        Supports two formats:

        1. Flat format (backward compatible - applies to .container):
            .meta{
              css:
                font-size: "24px"
                line-height: "1.6"
            }

        2. Selector-based format (new - custom selectors):
            .meta{
              css:
                ".container":
                  font-size: "36px"
                  line-height: "1.6"
                ".container p":
                  font-size: "24px"
                "code":
                  font-size: "18px"
            }

        Returns:
            HTML <style> tag with CSS rules, or empty string if no custom CSS
        """
        css_config = self.meta_config.get('css', {})

        if not css_config or not isinstance(css_config, dict):
            return ""

        # Detect format: flat (values are strings) vs nested (values are dicts/lists)
        # Check if we have @import or any selector keys (indicates nested format)
        # or if first value is a dict (also nested format)
        has_selectors = any(key.startswith('.') or key.startswith('#') or
                           key.startswith('@') or ',' in key
                           for key in css_config.keys())
        first_value = next(iter(css_config.values()), None)
        is_nested_format = has_selectors or isinstance(first_value, (dict, list))

        css_rules = []
        import_statements = []

        if is_nested_format:
            # NESTED FORMAT: keys are selectors, values are property dicts
            for selector, properties in css_config.items():
                # Special handling for @import
                if selector == "@import":
                    # Can be a single string or list of strings
                    if isinstance(properties, str):
                        import_statements.append(f"    @import url('{properties}');")
                    elif isinstance(properties, list):
                        for url in properties:
                            import_statements.append(f"    @import url('{url}');")
                    continue

                if not isinstance(properties, dict):
                    continue

                # Generate properties for this selector
                property_lines = []
                for property_name, value in properties.items():
                    # Convert snake_case or camelCase to kebab-case for CSS
                    css_property = property_name.replace('_', '-')
                    property_lines.append(f"    {css_property}: {value};")

                if property_lines:
                    properties_str = "\n".join(property_lines)
                    css_rules.append(f"    {selector} {{\n{properties_str}\n    }}")
        else:
            # FLAT FORMAT: apply all properties to .container (backward compatible)
            css_properties = []
            for property_name, value in css_config.items():
                # Convert snake_case or camelCase to kebab-case for CSS
                css_property = property_name.replace('_', '-')
                css_properties.append(f"    {css_property}: {value};")

            if css_properties:
                properties_str = "\n".join(css_properties)
                css_rules.append(f"    .container {{\n{properties_str}\n    }}")

        if not css_rules and not import_statements:
            return ""

        # Build the style block
        style_content = []
        if import_statements:
            style_content.append("\n".join(import_statements))
        if css_rules:
            style_content.append("\n\n".join(css_rules))

        content_str = "\n\n".join(style_content)

        return f"""
    <!-- Custom CSS from .meta{{css: ...}} -->
    <style>
{content_str}
    </style>"""

    def watermarks_generate(self) -> str:
        """
        Generate watermark HTML from merged configuration.

        Reads watermark settings from .meta{} if present, otherwise theme.yaml.
        Validates file paths and generates appropriate HTML img tags.

        Returns:
            HTML string with watermark img tags, or empty string if no watermarks
        """
        # Use merged config (meta overrides theme)
        watermarks = self.config_getMerged('watermarks', [])
        if not watermarks:
            watermarks = self.config_getMerged('slide_master.watermarks', [])

        if not watermarks:
            return ""

        html_parts = []
        for wm in watermarks:
            # Required: image path
            image = wm.get('image', '')
            if not image:
                continue

            # Validate image path (relative to input directory)
            image_full_path = self.input_dir / image
            if not image_full_path.exists():
                LOG(f"Warning: Watermark image not found: {image}", level=1)
                LOG(f"         Expected at: {image_full_path}", level=1)
                continue

            # Optional: position (default: bottom-right)
            position = wm.get('position', 'bottom-right')

            # Optional: opacity (default: 0.3)
            opacity = wm.get('opacity', 0.3)

            # Optional: size (width with CSS unit: px, %, em, rem, etc., default: 100px)
            size = wm.get('size', '100px')

            # Validate size has a CSS unit
            if not re.match(r'^[\d.]+(?:px|%|em|rem|vw|vh|vmin|vmax|ch|ex)$', str(size)):
                LOG(f"Warning: Watermark size '{size}' may be invalid. Use CSS units like px, %, em, rem", level=1)

            # Optional: offset (X, Y offset from anchor point)
            # Format: "10px, 20px" or "-10px, 20px" (negative moves off-screen)
            offset = wm.get('offset', None)
            offset_x, offset_y = None, None

            if offset:
                # Parse offset - accept "X, Y" string or [X, Y] list
                if isinstance(offset, str):
                    # Split by comma and parse
                    parts = [p.strip() for p in offset.split(',')]
                    if len(parts) == 2:
                        offset_x = parts[0]
                        offset_y = parts[1]
                elif isinstance(offset, (list, tuple)) and len(offset) == 2:
                    offset_x = str(offset[0]) if not isinstance(offset[0], str) else offset[0]
                    offset_y = str(offset[1]) if not isinstance(offset[1], str) else offset[1]
                    # Add px if no unit specified (handle negative numbers)
                    if re.match(r'^-?[\d.]+$', offset_x):
                        offset_x = f"{offset_x}px"
                    if re.match(r'^-?[\d.]+$', offset_y):
                        offset_y = f"{offset_y}px"

            # Apply offset based on position
            # Position format: "vertical-horizontal" (e.g., "top-left", "bottom-right")
            # Offset values use their literal sign (negative = move off-screen, positive = inward)
            style_parts = [
                f"opacity: {opacity}",
                f"width: {size}"
            ]

            if offset_x or offset_y:
                # Parse position to determine which CSS properties to use
                pos_parts = position.split('-')
                vertical = pos_parts[0] if len(pos_parts) > 0 else 'bottom'
                horizontal = pos_parts[1] if len(pos_parts) > 1 else 'right'

                # Apply offsets directly (respect user's sign)
                # Positive: moves away from edge (inward)
                # Negative: moves toward edge (can go off-screen)
                if vertical == 'top' and offset_y:
                    style_parts.append(f"top: {offset_y}")
                elif vertical == 'bottom' and offset_y:
                    style_parts.append(f"bottom: {offset_y}")

                if horizontal == 'left' and offset_x:
                    style_parts.append(f"left: {offset_x}")
                elif horizontal == 'right' and offset_x:
                    style_parts.append(f"right: {offset_x}")

            style_attr = '; '.join(style_parts)

            # Generate img tag
            html_parts.append(
                f'<img src="{image}" class="watermark {position}" '
                f'style="{style_attr}" alt="watermark">'
            )

        return '\n        '.join(html_parts)

    def footer_generate(self) -> str:
        """
        Generate footer HTML from .meta{footer: {...}} or default template.

        Supports custom left/right text with counter templates:
        - Static text: "© 2025 My Company"
        - Counter template: "Slide {current} / {total}"
        - Mixed: "Page {current} - My Company"

        Returns:
            HTML string with footer, or default footer.html if no config
        """
        footer_config = self.meta_config.get('footer', None)

        # No footer config → use default template
        if not footer_config:
            return self.template_load('footer.html')

        # Footer config exists → generate custom footer
        left_text = footer_config.get('left', None)
        right_text = footer_config.get('right', None)

        # Helper: detect if text contains counter template
        def is_counter_template(text):
            return '{current}' in text or '{total}' in text if text else False

        html_parts = ['<div class="footer-bar">']

        # Left side
        if left_text:
            if is_counter_template(left_text):
                # Counter template → add id for JavaScript update
                html_parts.append(
                    f'    <span class="footer" style="float: left;" '
                    f'data-template="{left_text}" id="footerLeft"></span>'
                )
            else:
                # Static text
                html_parts.append(
                    f'    <span class="footer" style="float: left;">{left_text}</span>'
                )

        # Right side
        if right_text:
            if is_counter_template(right_text):
                # Counter template → add id for JavaScript update
                html_parts.append(
                    f'    <span class="footer" style="float: right;" '
                    f'data-template="{right_text}" id="footerRight"></span>'
                )
            else:
                # Static text
                html_parts.append(
                    f'    <span class="footer" style="float: right;">{right_text}</span>'
                )

        html_parts.append('</div>')
        return '\n    '.join(html_parts)

    def navbar_generate(self) -> str:
        """
        Generate navbar HTML from .meta{navbar: {...}} or default template.

        Supports customizable navbar with:
        - Progress bar (show/hide, styling)
        - Title positioning (left/center/right)
        - Button groups (left/right) with custom styling
        - Slide counter in navbar

        Returns:
            HTML string with navbar, or default navbar.html if no config
        """
        navbar_config = self.meta_config.get('navbar', None)

        # No navbar config → use default template
        if not navbar_config:
            return self.template_load('navbar.html')

        # Check if navbar is disabled
        if navbar_config.get('show', True) is False:
            return ""

        # Button type definitions with defaults
        button_defs = {
            'slide_first': {
                'id': 'first',
                'onclick': 'page.advance_toFirst()',
                'icon': '&#xf078',  # FontAwesome chevron-down
                'class': 'pure-button pure-button-primary fas fa-chevron-down',
                'tooltip': 'First slide'
            },
            'slide_previous': {
                'id': 'previous',
                'onclick': 'page.advance_toPrevious()',
                'icon': '&#xf053',  # FontAwesome chevron-left
                'class': 'pure-button pure-button-primary fas fas-chevron-left',
                'tooltip': 'Previous slide'
            },
            'slide_next': {
                'id': 'next',
                'onclick': 'page.advance_toNext()',
                'icon': '&#xf054',  # FontAwesome chevron-right
                'class': 'pure-button pure-button-primary fas fas-chevron-right',
                'tooltip': 'Next slide'
            },
            'slide_last': {
                'id': 'last',
                'onclick': 'page.advance_toLast()',
                'icon': '&#xf077',  # FontAwesome chevron-up
                'class': 'pure-button pure-button-primary fas fa-chevron-up',
                'tooltip': 'Last slide'
            }
        }

        html_parts = []

        # Wrapper div
        html_parts.append('<div class="boxtext pure-control-group" style="margin-bottom: -3px;">')

        # Progress bar
        progress_config = navbar_config.get('progress', {})
        if progress_config.get('show', True):
            progress_style_parts = []
            if 'background' in progress_config:
                progress_style_parts.append(f"background-color: {progress_config['background']}")
            if 'height' in progress_config:
                progress_style_parts.append(f"height: {progress_config['height']}")

            bar_style_parts = []
            if 'color' in progress_config:
                bar_style_parts.append(f"background-color: {progress_config['color']}")

            progress_style = f' style="{"; ".join(progress_style_parts)}"' if progress_style_parts else ''
            bar_style = f' style="{"; ".join(bar_style_parts)}"' if bar_style_parts else ''

            html_parts.append(f'    <div id="slideProgress"{progress_style}>')
            html_parts.append(f'        <div id="slideBar"{bar_style}></div>')
            html_parts.append('    </div>')

        # Navbar container with optional styling
        container_config = navbar_config.get('container', {})
        container_style_parts = []
        if 'background' in container_config:
            container_style_parts.append(f"background: {container_config['background']}")
        if 'border' in container_config:
            container_style_parts.append(f"border: {container_config['border']}")
        if 'border-bottom' in container_config:
            container_style_parts.append(f"border-bottom: {container_config['border-bottom']}")
        if 'padding' in container_config:
            container_style_parts.append(f"padding: {container_config['padding']}")
        if 'box-shadow' in container_config:
            container_style_parts.append(f"box-shadow: {container_config['box-shadow']}")

        container_style = f' style="{"; ".join(container_style_parts)}"' if container_style_parts else ''
        html_parts.append(f'    <div class="navbar-container"{container_style}>')

        # Helper function to generate button HTML
        def generate_button(button_type, config=None):
            if button_type not in button_defs:
                return ''

            defaults = button_defs[button_type]
            config = config or {}

            # Build inline styles
            style_parts = ['float: left']  # Default float (no semicolon - added by join)
            if 'color' in config:
                style_parts.append(f"color: {config['color']}")
            if 'background' in config:
                style_parts.append(f"background: {config['background']}")
            if 'border' in config:
                style_parts.append(f"border: {config['border']}")
            if 'box-shadow' in config:
                style_parts.append(f"box-shadow: {config['box-shadow']}")
            if 'margin' in config:
                style_parts.append(f"margin: {config['margin']}")
            if 'margin-right' in config:
                style_parts.append(f"margin-right: {config['margin-right']}")
            if 'size' in config:
                style_parts.append(f"width: {config['size']}")
                style_parts.append(f"height: {config['size']}")
            if 'shape' in config:
                if config['shape'] == 'round':
                    style_parts.append('border-radius: 50%')
                    # Remove padding and center icon in circle
                    style_parts.append('padding: 0')
                    style_parts.append('display: inline-flex')
                    style_parts.append('align-items: center')
                    style_parts.append('justify-content: center')
                elif config['shape'] == 'square':
                    style_parts.append('border-radius: 0')
                else:
                    style_parts.append(f"border-radius: {config['shape']}")

            style_attr = f' style="{"; ".join(style_parts)}"'
            icon = config.get('icon', defaults['icon'])
            tooltip = config.get('tooltip', defaults.get('tooltip', ''))
            title_attr = f' title="{tooltip}"' if tooltip else ''

            return f'''        <input  type    =  "button"
                    onclick =  "{defaults['onclick']}"
                    value   =  "{icon}"{style_attr}
                    id      =  "{defaults['id']}"
                    name    =  "{defaults['id']}"
                    class   =  "{defaults['class']}"{title_attr}>
            </input>'''

        # Helper function to generate counter HTML
        def generate_counter(config):
            format_str = config.get('format', '{current} / {total}')
            style_parts = []
            if 'color' in config:
                style_parts.append(f"color: {config['color']}")
            if 'font-size' in config:
                style_parts.append(f"font-size: {config['font-size']}")

            style_attr = f' style="{"; ".join(style_parts)}"' if style_parts else ''

            return f'        <span class="navbar-counter" data-template="{format_str}"{style_attr}></span>'

        # Helper function to generate title HTML
        def generate_title(config):
            text = config.get('text', '{title}')
            style_parts = []
            if 'color' in config:
                style_parts.append(f"color: {config['color']}")
            if 'font-size' in config:
                style_parts.append(f"font-size: {config['font-size']}")

            style_attr = f' style="{"; ".join(style_parts)}"' if style_parts else ''

            return f'        <div id="pageTitle" class="navbar-title"{style_attr}></div>'

        # Process left zone
        left_config = navbar_config.get('left', [])
        for item in left_config:
            if isinstance(item, str):
                # Simple form: just button name
                if item == 'slide_counter':
                    html_parts.append(generate_counter({}))
                elif item == 'title':
                    html_parts.append(generate_title({}))
                else:
                    html_parts.append(generate_button(item))
            elif isinstance(item, dict):
                # Detailed form: {button_name: {config}}
                for button_type, config in item.items():
                    if button_type == 'slide_counter':
                        html_parts.append(generate_counter(config))
                    elif button_type == 'title':
                        html_parts.append(generate_title(config))
                    else:
                        html_parts.append(generate_button(button_type, config))

        # Process center zone
        center_config = navbar_config.get('center', [])
        for item in center_config:
            if isinstance(item, str):
                if item == 'slide_counter':
                    html_parts.append(generate_counter({}))
                elif item == 'title':
                    html_parts.append(generate_title({}))
                else:
                    html_parts.append(generate_button(item))
            elif isinstance(item, dict):
                for button_type, config in item.items():
                    if button_type == 'slide_counter':
                        html_parts.append(generate_counter(config))
                    elif button_type == 'title':
                        html_parts.append(generate_title(config))
                    else:
                        html_parts.append(generate_button(button_type, config))

        # Process right zone (buttons float right)
        right_config = navbar_config.get('right', [])
        for item in right_config:
            if isinstance(item, str):
                if item == 'slide_counter':
                    counter_html = generate_counter({})
                    html_parts.append(counter_html.replace('float: left', 'float: right'))
                elif item == 'title':
                    title_html = generate_title({})
                    html_parts.append(title_html)  # Title doesn't float
                else:
                    button_html = generate_button(item)
                    html_parts.append(button_html.replace('float: left', 'float: right'))
            elif isinstance(item, dict):
                for button_type, config in item.items():
                    if button_type == 'slide_counter':
                        counter_html = generate_counter(config)
                        html_parts.append(counter_html.replace('float: left', 'float: right') if 'float: left' in counter_html else counter_html)
                    elif button_type == 'title':
                        html_parts.append(generate_title(config))
                    else:
                        button_html = generate_button(button_type, config)
                        html_parts.append(button_html.replace('float: left', 'float: right'))

        # Close navbar container
        html_parts.append('    </div>')
        html_parts.append('    <br style="clear: both;">')
        html_parts.append('</div>')

        return '\n'.join(html_parts)
