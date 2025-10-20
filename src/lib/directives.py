"""
Directive implementations for slidedown

Each directive transforms AST nodes into HTML with appropriate attributes/structure.
Uses DirectiveSpec for metadata and validation.
"""

from typing import Callable, Dict, Optional
from pyfiglet import Figlet
import cowsay as cowsay_module

from ..models.directives import DirectiveSpec, DirectiveCategory, RESERVED_DIRECTIVES


class DirectiveRegistry:
    """
    Registry of directive specifications and handlers

    Maps directive names to DirectiveSpec objects containing metadata
    and compilation handlers.
    """

    def __init__(self):
        self.specs: Dict[str, DirectiveSpec] = {}
        self.coreDirectives_register()
        self.formattingDirectives_register()
        self.effectDirectives_register()
        self.transformDirectives_register()
        self.modifierDirectives_register()

    def register(self, spec: DirectiveSpec) -> None:
        """Register a directive specification"""
        self.specs[spec.name] = spec
        # Also register aliases
        for alias in spec.aliases:
            self.specs[alias] = spec

    def get(self, name: str) -> Optional[Callable]:
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

        def slide_handler(node, compiler):
            """Handle .slide{} - compile to slide div"""
            # Skip empty slides (used as examples in text, not actual slides)
            if not node.content or not node.content.strip():
                return ''

            # slide_count incremented in compiler.node_compile BEFORE children compiled
            slide_num = compiler.slide_count

            # node.content already has placeholders substituted by compiler
            content = node.content

            # Build style attribute - all slides hidden by default, JS shows slide 1
            user_style = node.modifiers.get('style', '')
            if user_style:
                style_attr = f'style="display:none; {user_style}"'
            else:
                style_attr = 'style="display:none;"'

            return f"""
                <div id="slide-{slide_num}-title" style="display: none;">
                </div>
                <div class="container slide " id="slide-{slide_num}" name="slide-{slide_num}" {style_attr}>
                    {content}
                </div>
            """

        def title_handler(node, compiler):
            """Handle .title{} - slide title metadata"""
            # node.content already has placeholders substituted
            return node.content

        def body_handler(node, compiler):
            """Handle .body{} - slide content area"""
            # node.content already has placeholders substituted by compiler
            return node.content

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

        def make_html_wrapper(tag: str):
            """Factory for simple HTML tag wrappers"""
            def handler(node, compiler):
                style = node.modifiers.get('style', '')
                style_attr = f' style="{style}"' if style else ''
                return f'<{tag}{style_attr}>{node.content}</{tag}>'
            return handler

        formatting_specs = [
            ('bf', 'strong', 'Bold/strong text', ['.bf{bold text}']),
            ('em', 'em', 'Emphasized/italic text', ['.em{italic text}']),
            ('tt', 'tt', 'Teletype/monospace text', ['.tt{monospace}']),
            ('code', 'code', 'Inline code', ['.code{function()}']),
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

    def effectDirectives_register(self) -> None:
        """Register special effect directives"""

        def typewriter_handler(node, compiler):
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

        def snippet_handler(node, compiler):
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

    def transformDirectives_register(self) -> None:
        """Register content transformation directives (ASCII art)"""

        def font_handler(node, compiler):
            """Handle .font-<name>{} - figlet ASCII art"""
            # Extract font name from directive (e.g., 'font-doom' -> 'doom')
            font_name = node.directive.split('-', 1)[1] if '-' in node.directive else 'standard'

            try:
                f = Figlet(font=font_name)
                ascii_art = f.renderText(node.content)
                return f'<pre>{ascii_art}</pre>'
            except Exception as e:
                return f'<pre>ERROR: Figlet font "{font_name}" not found\n{node.content}</pre>'

        def cowpy_handler(node, compiler):
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

    def modifierDirectives_register(self) -> None:
        """
        Register reserved modifier directives

        These are handled specially by the parser - they're extracted
        into the modifiers dict rather than creating child nodes.
        """

        def style_handler(node, compiler):
            """Should never be called - .style{} extracted by parser"""
            return ""

        def class_handler(node, compiler):
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
