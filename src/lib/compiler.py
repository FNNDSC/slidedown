"""
Compiler for slidedown AST to HTML

Transforms parsed AST nodes into complete HTML presentation.
"""

import os
import shutil
from typing import List, Dict
from pathlib import Path

from .parser import ASTNode
from .directives import DirectiveRegistry
from .log import LOG


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
        verbosity: int = 1
    ):
        """
        Initialize compiler

        Args:
            ast: Parsed abstract syntax tree
            output_dir: Directory for compiled output
            assets_dir: Directory containing runtime assets (css/js/html)
            verbosity: Output verbosity level (0-3)
        """
        self.ast = ast
        self.output_dir = Path(output_dir)
        self.assets_dir = Path(assets_dir)
        self.verbosity = verbosity
        self.directives = DirectiveRegistry()

        self.slide_count = 0
        self.snippet_counters: Dict[int, int] = {}  # slide_num -> snippet_count
        self.typewriter_counters: Dict[int, int] = {}  # slide_num -> typewriter_count

    def compile(self) -> Dict:
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
        navbar_html = self.template_load('navbar.html')
        footer_html = self.template_load('footer.html')

        # Assemble document with presentation viewport wrapper
        html = f"""<!DOCTYPE html>
<html>
{head_html}
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
        """Copy CSS/JS/image assets to output directory"""
        for asset_dir in ['css', 'js', 'images', 'logos']:
            src = self.assets_dir / asset_dir
            dst = self.output_dir / asset_dir

            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                LOG(f"Copied {asset_dir}/ to output", level=3)
