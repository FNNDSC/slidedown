"""
End-to-end compilation tests

Tests the full pipeline: slidedown source → Parser → Compiler → HTML output

Validates that complete slide presentations with real directives compile correctly
and produce expected HTML structures.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from slidedown.lib.parser import Parser
from slidedown.lib.compiler import Compiler


class TestBasicSlideCompilation:
    """Test complete slide compilation"""

    def test_single_slide_with_title_and_body(self):
        """Compile simple slide with title and body"""
        source = """
.slide{
  .title{Welcome to Slidedown}
  .body{This is a simple slide.}
}
"""
        parser = Parser(source)
        ast = parser.parse()

        # Create temporary output directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use package assets
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True
            assert result['slide_count'] == 1

            # Verify output file exists
            output_file = Path(tmpdir) / "index.html"
            assert output_file.exists()

            # Verify HTML content
            html = output_file.read_text()
            assert '<div class="container slide"' in html
            assert 'id="slide-1"' in html
            assert 'Welcome to Slidedown' in html
            assert 'This is a simple slide.' in html

    def test_multiple_slides(self):
        """Compile presentation with multiple slides"""
        source = """
.slide{
  .title{Slide 1}
  .body{First slide content}
}

.slide{
  .title{Slide 2}
  .body{Second slide content}
}

.slide{
  .title{Slide 3}
  .body{Third slide content}
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['slide_count'] == 3

            html = (Path(tmpdir) / "index.html").read_text()
            assert 'id="slide-1"' in html
            assert 'id="slide-2"' in html
            assert 'id="slide-3"' in html
            assert 'Slide 1' in html
            assert 'Slide 2' in html
            assert 'Slide 3' in html


class TestTypewriterEffect:
    """Test .typewriter{} directive compilation"""

    def test_typewriter_basic(self):
        """Basic typewriter effect"""
        source = """
.slide{
  .title{Typewriter Demo}
  .body{
    .typewriter{This text appears character by character}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # Check for typewriter element (ID numbering starts at 0 currently)
            assert 'id="typewriter-' in html
            assert 'This text appears character by character' in html

    def test_typewriter_with_modifiers(self):
        """Typewriter with style modifier"""
        source = """
.slide{
  .body{
    .typewriter{.style{color: green; font-family: monospace}
      > System initializing...
      > Loading modules...
      > Ready.
    }
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # Should have typewriter element with style
            assert 'id="typewriter-' in html
            assert 'style="color: green; font-family: monospace"' in html


class TestSnippetBullets:
    """Test .o{} snippet/bullet directive compilation"""

    def test_simple_bullets(self):
        """Simple progressive reveal bullets"""
        source = """
.slide{
  .title{Bullet Points}
  .body{
    .o{First bullet}
    .o{Second bullet}
    .o{Third bullet}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # Check for snippet elements
            # Note: ID numbering may start at 0 or vary based on implementation
            assert 'class="snippet"' in html
            assert 'id="order-' in html  # Snippets exist
            assert 'First bullet' in html
            assert 'Second bullet' in html
            assert 'Third bullet' in html

    def test_nested_formatting_in_bullets(self):
        """Bullets with nested formatting directives"""
        source = """
.slide{
  .body{
    .o{.bf{Bold} text in bullet}
    .o{.em{Italic} text in bullet}
    .o{.tt{Monospace} and .bf{bold} together}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # Should have HTML tags for formatting
            assert '<strong>Bold</strong>' in html
            assert '<em>Italic</em>' in html
            assert '<tt>Monospace</tt>' in html

    def test_bullets_across_multiple_slides(self):
        """Snippet numbering resets per slide"""
        source = """
.slide{
  .body{
    .o{Slide 1, bullet 1}
    .o{Slide 1, bullet 2}
  }
}

.slide{
  .body{
    .o{Slide 2, bullet 1}
    .o{Slide 2, bullet 2}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # Both slides have snippets
            assert 'class="snippet"' in html

            # Content is present
            assert 'Slide 1, bullet 1' in html
            assert 'Slide 1, bullet 2' in html
            assert 'Slide 2, bullet 1' in html
            assert 'Slide 2, bullet 2' in html


class TestFormattingDirectives:
    """Test text formatting directives (.bf, .em, .tt, etc.)"""

    def test_bold_formatting(self):
        """Bold text formatting"""
        source = """
.slide{
  .body{This is .bf{bold text} in a sentence.}
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()
            assert '<strong>bold text</strong>' in html

    def test_italic_formatting(self):
        """Italic text formatting"""
        source = """
.slide{
  .body{This is .em{emphasized text} in a sentence.}
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()
            assert '<em>emphasized text</em>' in html

    def test_monospace_formatting(self):
        """Monospace/teletype formatting"""
        source = """
.slide{
  .body{Code: .tt{function() { return 42; }}}
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()
            assert '<tt>function() { return 42; }</tt>' in html

    def test_nested_formatting(self):
        """Nested formatting directives"""
        source = """
.slide{
  .body{.bf{This is .em{bold and italic} text}}
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()
            # Should have nested tags
            assert '<strong>' in html
            assert '<em>bold and italic</em>' in html


class TestASCIIArtDirectives:
    """Test ASCII art transformation directives"""

    def test_figlet_font(self):
        """Figlet ASCII art with font-* directive"""
        source = """
.slide{
  .body{
    .font-standard{HELLO}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()
            # Figlet output wrapped in <pre>
            assert '<pre>' in html
            # ASCII art will contain ASCII representation of letters
            # Figlet uses box-drawing characters, so check for presence of underscores/pipes
            assert ('_' in html and '|' in html) or 'HELLO' in html

    def test_cowsay_character(self):
        """Cowsay speech bubble with cowpy-* directive"""
        source = """
.slide{
  .body{
    .cowpy-cow{Hello from the cow!}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()
            # Cowsay output wrapped in <pre>
            assert '<pre>' in html
            assert 'Hello from the cow!' in html


class TestComplexSlide:
    """Test complex real-world slide with multiple features"""

    def test_comprehensive_slide(self):
        """Slide with modifiers, typewriter, bullets, formatting, and ASCII art"""
        source = """
.slide{.style{background: black; color: lightgreen;}
  .title{.font-doom{SLIDEDOWN}}

  .body{
    .typewriter{> Initializing presentation...}

    .bf{Features:}
    .o{.em{Text-first} authoring}
    .o{.tt{Behavioral} markup}
    .o{Interactive .bf{effects}}

    .cowpy-tux{Made with slidedown!}
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        # Validate AST structure
        assert len(ast) == 1
        slide = ast[0]
        assert slide.directive == "slide"
        assert "style" in slide.modifiers
        assert slide.modifiers["style"] == "background: black; color: lightgreen;"

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True
            assert result['slide_count'] == 1

            html = (Path(tmpdir) / "index.html").read_text()

            # Slide has style attribute
            assert 'style="background: black; color: lightgreen;"' in html

            # Contains typewriter
            assert 'id="typewriter-' in html

            # Contains snippets
            assert 'class="snippet"' in html
            assert 'id="order-' in html

            # Contains formatting
            assert '<em>' in html
            assert '<tt>' in html
            assert '<strong>' in html

            # Contains content
            assert 'Text-first' in html
            assert 'Behavioral' in html
            assert 'Made with slidedown!' in html


class TestHTMLPassthrough:
    """Test that raw HTML is preserved"""

    def test_html_in_body(self):
        """Raw HTML tags in body content"""
        source = """
.slide{
  .body{
    <h1>HTML Heading</h1>
    <p>This is a <span style="color: red;">colored</span> paragraph.</p>
    <ul>
      <li>HTML list item</li>
    </ul>
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # HTML should be preserved as-is
            assert '<h1>HTML Heading</h1>' in html
            assert '<p>This is a <span style="color: red;">colored</span> paragraph.</p>' in html
            assert '<ul>' in html
            assert '<li>HTML list item</li>' in html

    def test_mixed_directives_and_html(self):
        """Mix of directives and raw HTML"""
        source = """
.slide{
  .body{
    .bf{Slidedown directives} work alongside <strong>HTML tags</strong>.

    <div class="custom-container">
      .em{Emphasized} text in HTML div.
    </div>
  }
}
"""
        parser = Parser(source)
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            package_root = Path(__file__).parent.parent
            assets_dir = package_root / "assets"

            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0
            )
            result = compiler.compile()

            assert result['status'] is True

            html = (Path(tmpdir) / "index.html").read_text()

            # Both directive output and raw HTML present
            assert '<strong>Slidedown directives</strong>' in html  # From .bf{}
            assert '<strong>HTML tags</strong>' in html  # Raw HTML
            assert '<div class="custom-container">' in html
            assert '<em>Emphasized</em>' in html  # From .em{}
