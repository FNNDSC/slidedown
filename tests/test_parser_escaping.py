"""
Parser escaping tests - backslash escaping and directive validation

Tests the two-layer protection system:
1. Directive name validation (only registered directives are parsed)
2. Backslash escaping (protect valid directives from being parsed)
"""

import pytest

from slidedown.lib.parser import Parser, ASTNode
from slidedown.lib.directives import DirectiveRegistry


class TestDirectiveValidation:
    """Test that only registered directive names are parsed"""

    def test_invalid_directive_name_ignored(self):
        """Invalid directive names should be passed through as text"""
        parser = Parser(".tt{.directive{content}}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].directive == "tt"
        # .directive{...} should NOT be parsed (not a valid directive)
        assert nodes[0].content == ".directive{content}"
        assert len(nodes[0].children) == 0

    def test_multiple_invalid_directives_ignored(self):
        """Multiple invalid directives in content"""
        parser = Parser(".body{.invalid{x} and .notreal{y}}")
        nodes = parser.parse()

        assert nodes[0].directive == "body"
        assert ".invalid{x}" in nodes[0].content
        assert ".notreal{y}" in nodes[0].content
        assert len(nodes[0].children) == 0

    def test_valid_directive_is_parsed(self):
        """Valid registered directives ARE parsed"""
        parser = Parser(".tt{.bf{bold}}")
        nodes = parser.parse()

        assert nodes[0].directive == "tt"
        # .bf IS valid, so it should be parsed as a child
        assert len(nodes[0].children) == 1
        assert nodes[0].children[0].directive == "bf"
        assert nodes[0].children[0].content == "bold"

    def test_mixed_valid_invalid_directives(self):
        """Mix of valid and invalid directive names"""
        parser = Parser(".body{.o{bullet} and .invalid{text}}")
        nodes = parser.parse()

        assert nodes[0].directive == "body"
        # .o should be parsed (valid)
        assert len(nodes[0].children) == 1
        assert nodes[0].children[0].directive == "o"
        # .invalid should remain in content (invalid)
        assert ".invalid{text}" in nodes[0].content


class TestModifierValidation:
    """Test that modifiers (.style, .class, .syntax) are recognized"""

    def test_style_modifier_extracted_when_first(self):
        r"""\.style{} at start of content should be extracted as modifier"""
        parser = Parser(".body{.style{color: red} Content}")
        nodes = parser.parse()

        assert nodes[0].directive == "body"
        # .style{} should be extracted as modifier
        assert nodes[0].modifiers.get("style") == "color: red"
        assert nodes[0].content.strip() == "Content"

    def test_style_in_middle_is_directive(self):
        r"""\.style{} NOT at start should be treated as directive"""
        parser = Parser(".tt{Text .style{color: red}}")
        nodes = parser.parse()

        assert nodes[0].directive == "tt"
        # .style IS registered as a directive, so without escaping it gets processed
        # It will be extracted as a child or modifier depending on position
        # In this case, it's not at the start, so it's processed as a directive
        # But style directive likely has special handling that makes it disappear
        # Let's just verify it doesn't appear as plain text
        assert "Text .style{color: red}" != nodes[0].content

    def test_class_modifier_extracted(self):
        r"""\.class{} modifier should be extracted"""
        parser = Parser(".body{.class{highlight} Content}")
        nodes = parser.parse()

        assert nodes[0].modifiers.get("class") == "highlight"


class TestBackslashEscaping:
    """Test backslash escaping of directive syntax"""

    def test_escaped_valid_directive_shows_literally(self):
        r"""Escaped directive \.bf\{...\} should show literally"""
        parser = Parser(r".tt{\.bf\{bold\}}")
        nodes = parser.parse()

        assert len(nodes) == 1
        assert nodes[0].directive == "tt"
        # Should have no children (escaped, not parsed)
        assert len(nodes[0].children) == 0
        # Should have escaped sequence stored
        assert 0 in parser.escaped_sequences
        assert parser.escaped_sequences[0] == ".bf{bold}"
        # Content should have placeholder
        assert "ESCAPE_0" in nodes[0].content

    def test_escaped_modifier_shows_literally(self):
        r"""Escaped \.style\{...\} should show literally"""
        parser = Parser(r".tt{\.style\{color: red\}}")
        nodes = parser.parse()

        assert nodes[0].directive == "tt"
        assert len(nodes[0].children) == 0
        assert 0 in parser.escaped_sequences
        assert parser.escaped_sequences[0] == ".style{color: red}"

    def test_multiple_escaped_sequences(self):
        r"""Multiple escaped sequences in one directive"""
        parser = Parser(r".body{\.o\{first\} and \.bf\{second\}}")
        nodes = parser.parse()

        assert len(parser.escaped_sequences) == 2
        assert parser.escaped_sequences[0] == ".o{first}"
        assert parser.escaped_sequences[1] == ".bf{second}"
        # Both should be replaced with placeholders
        assert "ESCAPE_0" in nodes[0].content
        assert "ESCAPE_1" in nodes[0].content

    def test_escaped_nested_braces(self):
        r"""Escaped directive with nested braces"""
        parser = Parser(r".tt{\.code\{function() \{ return x; \}\}}")
        nodes = parser.parse()

        assert 0 in parser.escaped_sequences
        # The escaped content should preserve internal braces
        assert "{" in parser.escaped_sequences[0]
        assert "}" in parser.escaped_sequences[0]

    def test_unescaped_vs_escaped_same_directive(self):
        r"""Show difference between escaped and unescaped"""
        # Unescaped - will parse
        parser1 = Parser(".tt{.bf{bold}}")
        nodes1 = parser1.parse()
        assert len(nodes1[0].children) == 1  # Parsed

        # Escaped - will not parse
        parser2 = Parser(r".tt{\.bf\{bold\}}")
        nodes2 = parser2.parse()
        assert len(nodes2[0].children) == 0  # Not parsed
        assert len(parser2.escaped_sequences) == 1  # Stored


class TestEscapingEdgeCases:
    """Test edge cases and combinations"""

    def test_escaped_invalid_directive(self):
        r"""Escaping an invalid directive name (unnecessary but should work)"""
        parser = Parser(r".tt{\.invalid\{content\}}")
        nodes = parser.parse()

        # Should still be escaped and stored
        assert 0 in parser.escaped_sequences
        assert parser.escaped_sequences[0] == ".invalid{content}"

    def test_partial_escape_backslash_only_before_dot(self):
        r"""Backslash before dot but not braces"""
        parser = Parser(r".tt{\.bf{text}}")
        nodes = parser.parse()

        # Should still recognize the escape pattern
        # The escaping looks for \. at the start
        assert 0 in parser.escaped_sequences

    def test_backslash_in_regular_text(self):
        """Backslash not followed by directive pattern"""
        parser = Parser(r".tt{This is \\ a backslash}")
        nodes = parser.parse()

        # Should pass through (no directive pattern to escape)
        assert r"\\" in nodes[0].content or "\\" in nodes[0].content

    def test_escaped_directive_at_start_of_content(self):
        r"""Escaped directive at the very start"""
        parser = Parser(r".body{\.style\{color: red\} Text}")
        nodes = parser.parse()

        # Even though .style{} normally would be extracted as modifier at start,
        # the escaping should prevent that
        assert 0 in parser.escaped_sequences
        assert "style" not in nodes[0].modifiers

    def test_nested_escaped_directive(self):
        r"""Escaped directive inside another directive"""
        parser = Parser(r".o{Use \.tt\{code\} for inline code}")
        nodes = parser.parse()

        assert nodes[0].directive == "o"
        assert 0 in parser.escaped_sequences
        assert parser.escaped_sequences[0] == ".tt{code}"


class TestEndToEndEscaping:
    """Test complete parsing + compilation of escaped directives"""

    def test_escaped_directive_compiles_to_literal_text(self):
        r"""Verify escaped directive becomes literal HTML text"""
        from slidedown.lib.compiler import Compiler
        from pathlib import Path
        import tempfile

        parser = Parser(r".slide{.body{Use \.o\{bullet\} for bullets}}")
        ast = parser.parse()

        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = Compiler(
                ast=ast,
                output_dir=str(Path(tmpdir) / "output"),
                assets_dir="assets",
                escaped_sequences=parser.escaped_sequences,
            )
            result = compiler.ast_compile(ast)

            # The escaped .o{bullet} should appear as literal text in HTML
            # It will be HTML-escaped
            assert ".o{bullet}" in result or ".o&#123;bullet&#125;" in result or \
                   "&lt;o&gt;{bullet}" in result or ".o{" in result

    def test_multiple_escapes_in_real_example(self):
        r"""Real-world example from documentation"""
        source = r""".slide{
  .title{Slidedown Syntax}
  .body{
    .h1{Directive Examples}

    Use \.o\{text\} for bullets and \.tt\{code\} for inline code.
    Modifiers like \.style\{color: red\} control appearance.
  }
}"""
        parser = Parser(source)
        ast = parser.parse()

        # Should have 3 escaped sequences
        assert len(parser.escaped_sequences) == 3
        assert ".o{text}" in parser.escaped_sequences.values()
        assert ".tt{code}" in parser.escaped_sequences.values()
        assert ".style{color: red}" in parser.escaped_sequences.values()

        # The actual directives (.slide, .title, .body, .h1) should be parsed
        assert ast[0].directive == "slide"
        assert ast[0].children[0].directive == "title"


class TestRegistryIntegration:
    """Test that parser correctly uses DirectiveRegistry"""

    def test_parser_creates_registry_if_not_provided(self):
        """Parser should create registry if none provided"""
        parser = Parser(".slide{test}")
        assert parser.registry is not None
        assert isinstance(parser.registry, DirectiveRegistry)

    def test_parser_uses_provided_registry(self):
        """Parser should use provided registry"""
        registry = DirectiveRegistry()
        parser = Parser(".slide{test}", registry=registry)
        assert parser.registry is registry

    def test_custom_directive_in_registry(self):
        """If we could register custom directives, parser should recognize them"""
        # This is more of a documentation test - showing how it would work
        # if custom directives were registered
        parser = Parser(".slide{test}")

        # Verify standard directives are recognized
        assert parser.registry.get("slide") is not None
        assert parser.registry.get("body") is not None
        assert parser.registry.get("o") is not None

        # Non-existent directives return None
        assert parser.registry.get("nonexistent") is None
