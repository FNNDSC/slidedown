"""
Basic parser tests - simplest cases

Tests empty source, single directives, and plain text.
"""

import pytest
from slidedown.lib.parser import Parser


class TestEmptyAndSimple:
    """Test empty source and simplest directives"""

    def test_empty_source(self) -> None:
        """Empty string should parse to empty list"""
        parser = Parser("")
        nodes = parser.parse()
        assert nodes == []

    def test_whitespace_only(self) -> None:
        """Only whitespace should parse to empty list"""
        parser = Parser("   \n\n  \t  ")
        nodes = parser.parse()
        assert nodes == []

    def test_single_directive_empty_content(self) -> None:
        """Single directive with no content"""
        parser = Parser(".slide{}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].directive == "slide"
        assert nodes[0].content == ""
        assert nodes[0].children == []
        assert nodes[0].modifiers == {}

    def test_single_directive_simple_text(self) -> None:
        """Single directive with plain text content"""
        parser = Parser(".title{Hello World}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].directive == "title"
        assert nodes[0].content == "Hello World"
        assert nodes[0].children == []

    def test_single_directive_multiline_text(self) -> None:
        """Single directive with multiline content"""
        parser = Parser(".body{Line 1\nLine 2\nLine 3}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].directive == "body"
        assert nodes[0].content == "Line 1\nLine 2\nLine 3"

    def test_directive_with_html(self) -> None:
        """Directive containing HTML tags"""
        parser = Parser(".body{<p>Paragraph</p><em>emphasis</em>}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].content == "<p>Paragraph</p><em>emphasis</em>"

    def test_multiple_top_level_directives(self) -> None:
        """Multiple directives at top level (multiple slides)"""
        parser = Parser(".slide{First}\n.slide{Second}")
        nodes = parser.parse()

        assert len(nodes) == 2
        assert nodes[0].directive == "slide"
        assert nodes[0].content == "First"
        assert nodes[1].directive == "slide"
        assert nodes[1].content == "Second"


class TestDirectiveNames:
    """Test various directive name formats"""

    def test_simple_name(self) -> None:
        """Simple lowercase directive"""
        parser = Parser(".bf{bold}")
        nodes = parser.parse()
        assert nodes[0].directive == "bf"

    def test_hyphenated_name(self) -> None:
        """Directive with hyphen (e.g., font-doom)"""
        parser = Parser(".font-doom{DOOM}")
        nodes = parser.parse()
        assert nodes[0].directive == "font-doom"

    def test_multiple_hyphens(self) -> None:
        """Unknown directive with multiple hyphens is ignored."""
        parser = Parser(".my-custom-directive{content}")
        nodes = parser.parse()
        assert nodes == []


class TestBraceHandling:
    """Test brace matching and nesting"""

    def test_braces_in_content(self) -> None:
        """Content containing literal braces (like code)"""
        parser = Parser(".code{function() { return {a: 1}; }}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].content == "function() { return {a: 1}; }"

    def test_unmatched_opening_brace(self) -> None:
        """Unmatched opening brace should raise SyntaxError"""
        parser = Parser(".slide{no closing brace")
        with pytest.raises(SyntaxError, match="Unmatched brace"):
            parser.parse()

    def test_unmatched_closing_brace(self) -> None:
        """Extra closing brace - should be treated as text or error"""
        # This is an edge case - for now, let's say it's just invalid
        parser = Parser(".slide{content}}")
        # May not raise if parsing stops after the complete directive.
        # But let's document expected behavior
        nodes = parser.parse()
        # Should parse first directive successfully, ignore extra }
        assert len(nodes) == 1


class TestWhitespace:
    """Test whitespace handling"""

    def test_whitespace_around_directive(self) -> None:
        """Whitespace before/after directive"""
        parser = Parser("   .slide{content}   ")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].directive == "slide"
        # Content whitespace preserved
        assert nodes[0].content == "content"

    def test_whitespace_in_content(self) -> None:
        """Whitespace inside content should be preserved"""
        parser = Parser(".body{  spaced  content  }")
        nodes = parser.parse()

        assert nodes[0].content == "  spaced  content  "

    def test_newlines_between_directives(self) -> None:
        """Newlines between top-level directives"""
        parser = Parser(".slide{First}\n\n\n.slide{Second}")
        nodes = parser.parse()

        assert len(nodes) == 2
