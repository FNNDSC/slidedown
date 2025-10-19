"""
Modifier extraction tests

Tests that .style{} and .class{} directives are:
- Extracted into the modifiers dict
- NOT present in children list
- Handled correctly at start of content
"""

import pytest

from slidedown.lib.parser import Parser, ASTNode


class TestStyleModifier:
    """Test .style{} modifier extraction"""

    def test_single_style_modifier(self):
        """Single .style{} at start of content"""
        parser = Parser(".slide{.style{color: red} Content}")
        nodes = parser.parse()

        slide = nodes[0]

        # Style should be in modifiers
        assert "style" in slide.modifiers
        assert slide.modifiers["style"] == "color: red"

        # Style should NOT be in children
        assert len(slide.children) == 0

        # Content should not have placeholder for style
        assert "\x00CHILD_0\x00" not in slide.content
        assert slide.content == "Content"

    def test_style_with_complex_css(self):
        """Style modifier with complex CSS"""
        parser = Parser(".slide{.style{background: black; color: lightgreen; font-size: 2em;} Text}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["style"] == "background: black; color: lightgreen; font-size: 2em;"
        assert slide.content == "Text"

    def test_style_only_no_content(self):
        """Directive with only style modifier, no other content"""
        parser = Parser(".slide{.style{color: blue}}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["style"] == "color: blue"
        assert slide.content == ""
        assert len(slide.children) == 0

    def test_style_with_nested_directives(self):
        """Style modifier with nested directives in content"""
        parser = Parser(".slide{.style{color: red} .title{Hello} .body{World}}")
        nodes = parser.parse()

        slide = nodes[0]

        # Style extracted
        assert slide.modifiers["style"] == "color: red"

        # Children extracted (but not style)
        assert len(slide.children) == 2
        assert slide.children[0].directive == "title"
        assert slide.children[1].directive == "body"

        # Content has placeholders for children (but not style)
        assert slide.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"


class TestClassModifier:
    """Test .class{} modifier extraction"""

    def test_single_class_modifier(self):
        """Single .class{} at start of content"""
        parser = Parser(".slide{.class{special-slide} Content}")
        nodes = parser.parse()

        slide = nodes[0]

        assert "class" in slide.modifiers
        assert slide.modifiers["class"] == "special-slide"
        assert len(slide.children) == 0
        assert slide.content == "Content"

    def test_class_with_multiple_classes(self):
        """Class modifier with space-separated class names"""
        parser = Parser(".slide{.class{big bold highlighted} Text}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["class"] == "big bold highlighted"

    def test_class_only(self):
        """Directive with only class modifier"""
        parser = Parser(".div{.class{container}}")
        nodes = parser.parse()

        div = nodes[0]

        assert div.modifiers["class"] == "container"
        assert div.content == ""


class TestMultipleModifiers:
    """Test both .style{} and .class{} together"""

    def test_style_and_class(self):
        """Both style and class modifiers"""
        parser = Parser(".slide{.style{color: red} .class{special} Content}")
        nodes = parser.parse()

        slide = nodes[0]

        assert "style" in slide.modifiers
        assert "class" in slide.modifiers
        assert slide.modifiers["style"] == "color: red"
        assert slide.modifiers["class"] == "special"
        assert slide.content == "Content"
        assert len(slide.children) == 0

    def test_class_then_style(self):
        """Class before style (order shouldn't matter)"""
        parser = Parser(".slide{.class{big} .style{font-size: 2em} Text}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["class"] == "big"
        assert slide.modifiers["style"] == "font-size: 2em"
        assert slide.content == "Text"

    def test_multiple_modifiers_with_nested_directives(self):
        """Both modifiers plus nested directives"""
        parser = Parser(".slide{.style{color: blue} .class{special} .title{Hi} .body{There}}")
        nodes = parser.parse()

        slide = nodes[0]

        # Both modifiers present
        assert slide.modifiers["style"] == "color: blue"
        assert slide.modifiers["class"] == "special"

        # Two children (title and body)
        assert len(slide.children) == 2
        assert slide.children[0].directive == "title"
        assert slide.children[1].directive == "body"

        # Content has placeholders for children only
        assert slide.content == "\x00CHILD_0\x00 \x00CHILD_1\x00"


class TestModifierPositioning:
    """Test that modifiers must be at start of content"""

    def test_modifier_at_start_with_whitespace(self):
        """Modifier can have leading whitespace"""
        parser = Parser(".slide{  .style{color: red}  Content}")
        nodes = parser.parse()

        slide = nodes[0]

        # Should extract style
        assert slide.modifiers["style"] == "color: red"
        # Content should have leading whitespace removed after modifier
        assert slide.content == "Content"

    def test_modifier_not_at_start_treated_as_directive(self):
        """Modifier in middle of content is NOT extracted"""
        parser = Parser(".slide{Content .style{color: red}}")
        nodes = parser.parse()

        slide = nodes[0]

        # Style should NOT be extracted (not at start)
        assert "style" not in slide.modifiers

        # Should be treated as a nested directive
        assert len(slide.children) == 1
        assert slide.children[0].directive == "style"
        assert slide.content == "Content \x00CHILD_0\x00"


class TestNestedModifiers:
    """Test modifiers in nested directives"""

    def test_modifier_in_nested_directive(self):
        """Child directive can have its own modifiers"""
        parser = Parser(".slide{.body{.style{font-weight: bold} Text}}")
        nodes = parser.parse()

        slide = nodes[0]
        body = slide.children[0]

        # Slide has no modifiers
        assert len(slide.modifiers) == 0

        # Body has style modifier
        assert body.modifiers["style"] == "font-weight: bold"
        assert body.content == "Text"

    def test_modifiers_at_multiple_levels(self):
        """Modifiers at both parent and child levels"""
        parser = Parser(
            ".slide{.style{background: black} "
            ".body{.style{color: green} Content}}"
        )
        nodes = parser.parse()

        slide = nodes[0]
        body = slide.children[0]

        # Slide has its own style
        assert slide.modifiers["style"] == "background: black"

        # Body has different style
        assert body.modifiers["style"] == "color: green"
        assert body.content == "Content"

    def test_complex_nested_with_modifiers(self):
        """Complex structure with modifiers at multiple levels"""
        parser = Parser(
            ".slide{.style{background: black} .class{dark} "
            ".title{.style{font-size: 3em} Big Title} "
            ".body{.class{content} Text here}}"
        )
        nodes = parser.parse()

        slide = nodes[0]

        # Slide modifiers
        assert slide.modifiers["style"] == "background: black"
        assert slide.modifiers["class"] == "dark"

        # Title has style
        title = slide.children[0]
        assert title.directive == "title"
        assert title.modifiers["style"] == "font-size: 3em"
        assert title.content == "Big Title"

        # Body has class
        body = slide.children[1]
        assert body.directive == "body"
        assert body.modifiers["class"] == "content"
        assert body.content == "Text here"


class TestModifierWhitespace:
    """Test whitespace handling with modifiers"""

    def test_whitespace_before_modifier(self):
        """Leading whitespace before modifier is skipped"""
        parser = Parser(".slide{   .style{color: red} Text}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["style"] == "color: red"
        assert slide.content == "Text"

    def test_whitespace_between_modifiers(self):
        """Whitespace between multiple modifiers"""
        parser = Parser(".slide{.style{color: red}   .class{big}   Text}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["style"] == "color: red"
        assert slide.modifiers["class"] == "big"
        assert slide.content == "Text"

    def test_whitespace_preserved_in_content(self):
        """Whitespace in content after modifiers is preserved"""
        parser = Parser(".slide{.style{color: red}  Content with  spaces  }")
        nodes = parser.parse()

        slide = nodes[0]

        # Leading space after modifier should be in content? Let's verify
        assert slide.modifiers["style"] == "color: red"
        # This test documents actual behavior
        assert slide.content == "Content with  spaces  "

    def test_newlines_after_modifiers(self):
        """Newlines after modifiers"""
        parser = Parser(".slide{.style{color: red}\n.class{big}\nContent}")
        nodes = parser.parse()

        slide = nodes[0]

        assert slide.modifiers["style"] == "color: red"
        assert slide.modifiers["class"] == "big"
        # Newlines between modifiers are stripped, but after last modifier?
        assert slide.content == "Content"


class TestEmptyModifiers:
    """Test edge cases with empty modifier values"""

    def test_empty_style_value(self):
        """Style modifier with empty value"""
        parser = Parser(".slide{.style{} Content}")
        nodes = parser.parse()

        slide = nodes[0]

        assert "style" in slide.modifiers
        assert slide.modifiers["style"] == ""
        assert slide.content == "Content"

    def test_empty_class_value(self):
        """Class modifier with empty value"""
        parser = Parser(".slide{.class{} Content}")
        nodes = parser.parse()

        slide = nodes[0]

        assert "class" in slide.modifiers
        assert slide.modifiers["class"] == ""
        assert slide.content == "Content"
