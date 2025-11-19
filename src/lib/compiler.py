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
        footer_html = self.template_load('footer.html')

        # Conditionally load navbar based on config
        show_nav_buttons = self.config_getMerged('navigation.show_buttons', True)
        navbar_html = self.template_load('navbar.html') if show_nav_buttons else ""

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

        Returns inline <style> tag with custom CSS rules for .container class.

        Example .meta{} usage:
            .meta{
              css:
                font-size: "24px"
                line-height: "1.6"
            }

        Returns:
            HTML <style> tag with CSS rules, or empty string if no custom CSS
        """
        css_config = self.meta_config.get('css', {})

        if not css_config or not isinstance(css_config, dict):
            return ""

        # Generate CSS properties for .container
        css_properties = []
        for property_name, value in css_config.items():
            # Convert snake_case or camelCase to kebab-case for CSS
            css_property = property_name.replace('_', '-')
            css_properties.append(f"    {css_property}: {value};")

        if not css_properties:
            return ""

        css_rules = "\n".join(css_properties)

        return f"""
    <!-- Custom CSS from .meta{{css: ...}} -->
    <style>
    .container {{
{css_rules}
    }}
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

            # Build inline styles
            style_parts = [
                f"opacity: {opacity}",
                f"width: {size}"
            ]
            style_attr = '; '.join(style_parts)

            # Generate img tag
            html_parts.append(
                f'<img src="{image}" class="watermark {position}" '
                f'style="{style_attr}" alt="watermark">'
            )

        return '\n        '.join(html_parts)
