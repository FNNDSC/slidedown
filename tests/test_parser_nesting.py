"""
Nesting parser tests - verify nested directive structure

Tests nested directives at various depths and validates that:
- Children are properly extracted into children list
- Content contains placeholders for children
- Placeholder indices match children array indices
"""

import pytest

from slidedown.lib.parser import Parser, ASTNode


class TestSingleLevelNesting:
    """Test directives with one level of nesting"""

    def test_single_child(self):
        """Single nested directive"""
        parser = Parser(".body{Hello .bf{world}!}")
        nodes = parser.parse()

        assert len(nodes) == 1
        body = nodes[0]

        # Parent structure
        assert body.directive == "body"
        assert len(body.children) == 1
        assert "\x00CHILD_0\x00" in body.content
        assert body.content == "Hello \x00CHILD_0\x00!"

        # Child structure
        child = body.children[0]
        assert child.directive == "bf"
        assert child.content == "world"
        assert child.children == []

    def test_multiple_children_sequential(self):
        """Multiple nested directives in sequence"""
        parser = Parser(".body{.bf{one} .em{two} .tt{three}}")
        nodes = parser.parse()

        body = nodes[0]

        # Should have 3 children
        assert len(body.children) == 3

        # Content should have 3 placeholders
        assert "\x00CHILD_0\x00" in body.content
        assert "\x00CHILD_1\x00" in body.content
        assert "\x00CHILD_2\x00" in body.content
        assert body.content == "\x00CHILD_0\x00 \x00CHILD_1\x00 \x00CHILD_2\x00"

        # Verify children match placeholders
        assert body.children[0].directive == "bf"
        assert body.children[0].content == "one"
        assert body.children[1].directive == "em"
        assert body.children[1].content == "two"
        assert body.children[2].directive == "tt"
        assert body.children[2].content == "three"

    def test_children_with_text_between(self):
        """Nested directives with text between them"""
        parser = Parser(".body{Start .bf{bold} middle .em{italic} end}")
        nodes = parser.parse()

        body = nodes[0]

        assert len(body.children) == 2
        assert body.content == "Start \x00CHILD_0\x00 middle \x00CHILD_1\x00 end"
        assert body.children[0].directive == "bf"
        assert body.children[1].directive == "em"

    def test_nested_with_newlines(self):
        """Nested directives with newlines in content"""
        parser = Parser(".body{Line 1\n.bf{bold}\nLine 2}")
        nodes = parser.parse()

        body = nodes[0]

        assert len(body.children) == 1
        assert body.content == "Line 1\n\x00CHILD_0\x00\nLine 2"
        assert body.children[0].directive == "bf"


class TestMultiLevelNesting:
    """Test directives with multiple levels of nesting"""

    def test_two_level_nesting(self):
        """Directive nested inside directive"""
        parser = Parser(".body{.o{First .bf{bold} word}}")
        nodes = parser.parse()

        body = nodes[0]

        # Body has one child (.o)
        assert len(body.children) == 1
        assert body.content == "\x00CHILD_0\x00"

        o_node = body.children[0]
        assert o_node.directive == "o"

        # .o has one child (.bf)
        assert len(o_node.children) == 1
        assert o_node.content == "First \x00CHILD_0\x00 word"

        bf_node = o_node.children[0]
        assert bf_node.directive == "bf"
        assert bf_node.content == "bold"
        assert bf_node.children == []

    def test_three_level_nesting(self):
        """Deep nesting: three levels"""
        parser = Parser(".slide{.body{.o{.bf{deeply nested}}}}")
        nodes = parser.parse()

        slide = nodes[0]
        assert slide.directive == "slide"
        assert len(slide.children) == 1

        body = slide.children[0]
        assert body.directive == "body"
        assert len(body.children) == 1

        o_node = body.children[0]
        assert o_node.directive == "o"
        assert len(o_node.children) == 1

        bf_node = o_node.children[0]
        assert bf_node.directive == "bf"
        assert bf_node.content == "deeply nested"
        assert bf_node.children == []

    def test_multiple_children_at_each_level(self):
        """Each level has multiple children"""
        parser = Parser(".slide{.title{Hi} .body{.o{One} .o{Two}}}")
        nodes = parser.parse()

        slide = nodes[0]
        assert len(slide.children) == 2
        assert slide.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"

        # First child: .title (no children)
        title = slide.children[0]
        assert title.directive == "title"
        assert title.content == "Hi"
        assert len(title.children) == 0

        # Second child: .body (has 2 children)
        body = slide.children[1]
        assert body.directive == "body"
        assert len(body.children) == 2
        assert body.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"

        # Body's children
        assert body.children[0].directive == "o"
        assert body.children[0].content == "One"
        assert body.children[1].directive == "o"
        assert body.children[1].content == "Two"

    def test_complex_nested_structure(self):
        """Complex real-world example"""
        parser = Parser(
            ".slide{"
            "  .title{Welcome}"
            "  .body{"
            "    Welcome to .bf{slidedown}!"
            "    .o{.bf{First} .em{bullet}}"
            "    .o{Second bullet}"
            "  }"
            "}"
        )
        nodes = parser.parse()

        slide = nodes[0]
        assert len(slide.children) == 2

        title = slide.children[0]
        assert title.directive == "title"
        assert title.content == "Welcome"

        body = slide.children[1]
        assert body.directive == "body"
        assert len(body.children) == 3  # .bf{slidedown}, .o{...}, .o{...}

        # Body content has placeholders
        assert "\x00CHILD_0\x00" in body.content
        assert "\x00CHILD_1\x00" in body.content
        assert "\x00CHILD_2\x00" in body.content

        # First child of body is .bf{slidedown}
        assert body.children[0].directive == "bf"
        assert body.children[0].content == "slidedown"

        # Second child is .o with nested .bf and .em
        o1 = body.children[1]
        assert o1.directive == "o"
        assert len(o1.children) == 2
        assert o1.children[0].directive == "bf"
        assert o1.children[0].content == "First"
        assert o1.children[1].directive == "em"
        assert o1.children[1].content == "bullet"

        # Third child is simple .o
        o2 = body.children[2]
        assert o2.directive == "o"
        assert o2.content == "Second bullet"
        assert len(o2.children) == 0


class TestPlaceholderFormat:
    """Test placeholder format and positioning"""

    def test_placeholder_uses_null_bytes(self):
        """Placeholders use \\x00 null bytes to avoid collisions"""
        parser = Parser(".body{.bf{text}}")
        nodes = parser.parse()

        body = nodes[0]

        # Should use \x00 as delimiter
        assert body.content.startswith("\x00CHILD_")
        assert body.content.endswith("\x00")
        assert body.content == "\x00CHILD_0\x00"

    def test_placeholder_indices_match_children(self):
        """CHILD_N placeholder corresponds to children[N]"""
        parser = Parser(".body{.a{} .b{} .c{} .d{} .e{}}")
        nodes = parser.parse()

        body = nodes[0]

        # Should have 5 children with indices 0-4
        assert len(body.children) == 5
        assert "\x00CHILD_0\x00" in body.content
        assert "\x00CHILD_1\x00" in body.content
        assert "\x00CHILD_2\x00" in body.content
        assert "\x00CHILD_3\x00" in body.content
        assert "\x00CHILD_4\x00" in body.content

        # Verify each placeholder matches its child
        for i in range(5):
            placeholder = f"\x00CHILD_{i}\x00"
            assert placeholder in body.content
            # Children should be in order a, b, c, d, e
            expected_directive = chr(ord('a') + i)
            assert body.children[i].directive == expected_directive

    def test_nested_placeholders_independent(self):
        """Each node has its own placeholder numbering starting from 0"""
        parser = Parser(".body{.o{.a{} .b{}} .o{.c{} .d{}}}")
        nodes = parser.parse()

        body = nodes[0]

        # Body has 2 children (two .o directives)
        assert len(body.children) == 2
        assert body.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"

        # First .o has its own CHILD_0 and CHILD_1
        o1 = body.children[0]
        assert o1.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"
        assert o1.children[0].directive == "a"
        assert o1.children[1].directive == "b"

        # Second .o also has CHILD_0 and CHILD_1 (independent numbering)
        o2 = body.children[1]
        assert o2.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"
        assert o2.children[0].directive == "c"
        assert o2.children[1].directive == "d"

    def test_whitespace_preserved_around_placeholders(self):
        """Whitespace around nested directives is preserved in placeholders"""
        parser = Parser(".body{  .bf{text}  }")
        nodes = parser.parse()

        body = nodes[0]

        # Leading and trailing spaces should be preserved
        assert body.content == "  \x00CHILD_0\x00  "
