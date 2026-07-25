"""
Nexus navigation: jump and navigation-graph tests

Covers the stage-2 contract — ``.jump{}`` renders a real anchor addressed
by name, targets resolve after the walk so forward references work, dead
targets fail the build, and the graph is emitted for the runtime.

See ``docs/nexus-navigation.adoc``.
"""

import json
import re

import pytest
from slidedown.lib.nexus import (
    UnresolvedJumpTarget,
    jumpRefs_validate,
    navigationGraph_build,
)

from .test_nexus_addressing import html_compile

MENU_DECK = """
.slide{
  .title{The Menu}
  .body{
    .o{.jump{.target{depth} Thread 3 -- the danger of depth}}
    .o{.jump{.target{registry} Thread 5 -- the registry}}
  }
}

.slide{
  .id{depth}
  .title{The Danger of Depth}
  .body{.o{Orchestration is depth.}}
}

.slide{
  .id{registry}
  .title{Compute Goes to the Data}
  .body{.o{The images never move.}}
}
"""


def graph_extract(html: str) -> dict:
    """Pull the navigation graph out of compiled HTML.

    Args:
        html: Compiled presentation HTML.

    Returns:
        Parsed graph dictionary.
    """
    match = re.search(r'id="nexusGraph">(.*?)</script>', html, re.S)
    assert match is not None, "navigation graph missing from output"
    # No entity decoding: script elements are raw text, and the emitter
    # escapes "<" as <, which json.loads resolves natively.
    return json.loads(match.group(1))


class TestJumpRendering:
    """The anchor a .jump{} produces"""

    def test_renders_anchor_with_address(self) -> None:
        html, _ = html_compile(MENU_DECK)

        assert 'class="sd-jump"' in html
        assert 'data-jump="depth"' in html

    def test_href_uses_named_address(self) -> None:
        html, _ = html_compile(MENU_DECK)

        # Works without JavaScript: the runtime accepts an address here.
        assert 'href="?slide=depth"' in html

    def test_label_is_preserved(self) -> None:
        html, _ = html_compile(MENU_DECK)

        assert "Thread 3 -- the danger of depth</a>" in html

    def test_label_keeps_nested_formatting(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{.jump{.target{spoke} A .bf{bold} label}}
}

.slide{
  .id{spoke}
  .title{Spoke}
  .body{Content.}
}
"""
        html, _ = html_compile(source)

        assert "<strong>bold</strong>" in html

    def test_target_is_slugified(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{.jump{.target{The Spoke} Go}}
}

.slide{
  .title{The Spoke}
  .body{Content.}
}
"""
        html, _ = html_compile(source)

        assert 'data-jump="the-spoke"' in html

    def test_jump_without_target_is_skipped(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{.jump{no target here}}
}
"""
        html, compiler = html_compile(source)

        assert "sd-jump" not in html
        assert compiler.jump_refs == []


class TestJumpResolution:
    """Targets resolve after the walk, so forward references work"""

    def test_forward_reference_resolves(self) -> None:
        _, compiler = html_compile(MENU_DECK)

        # Both jumps sit on slide 1 and point at slides compiled later.
        assert compiler.jump_refs == [("depth", 1), ("registry", 1)]

    def test_backward_reference_resolves(self) -> None:
        source = """
.slide{
  .id{first}
  .title{First}
  .body{Content.}
}

.slide{
  .title{Second}
  .body{.jump{.target{first} Back to the start}}
}
"""
        html, _ = html_compile(source)

        assert 'data-jump="first"' in html

    def test_unresolved_target_fails_the_build(self) -> None:
        source = """
.slide{
  .title{The Menu}
  .body{.jump{.target{does-not-exist} Nowhere}}
}
"""
        with pytest.raises(UnresolvedJumpTarget) as excinfo:
            html_compile(source)

        message = str(excinfo.value)
        assert "does-not-exist" in message
        assert "slide 1" in message
        # The message lists what the author could have meant.
        assert "the-menu" in message


class TestJumpRefValidation:
    """Unit-level validation behaviour"""

    def test_valid_refs_pass(self) -> None:
        jumpRefs_validate([("menu", 2)], {"menu": 1})

    def test_empty_refs_pass(self) -> None:
        jumpRefs_validate([], {})

    def test_unknown_target_raises(self) -> None:
        with pytest.raises(UnresolvedJumpTarget):
            jumpRefs_validate([("ghost", 2)], {"menu": 1})

    def test_message_reports_no_known_addresses(self) -> None:
        with pytest.raises(UnresolvedJumpTarget) as excinfo:
            jumpRefs_validate([("ghost", 1)], {})

        assert "(none)" in str(excinfo.value)


class TestNavigationGraph:
    """The JSON graph handed to the runtime"""

    def test_graph_is_emitted(self) -> None:
        html, _ = html_compile(MENU_DECK)
        graph = graph_extract(html)

        assert graph["version"] == 1
        assert graph["slideCount"] == 3

    def test_graph_lists_every_address(self) -> None:
        html, _ = html_compile(MENU_DECK)
        graph = graph_extract(html)

        assert graph["slides"] == {
            "the-menu": 1,
            "depth": 2,
            "registry": 3,
        }

    def test_graph_resolves_jump_target_slides(self) -> None:
        html, _ = html_compile(MENU_DECK)
        graph = graph_extract(html)

        assert graph["jumps"] == [
            {"target": "depth", "targetSlide": 2, "from": 1},
            {"target": "registry", "targetSlide": 3, "from": 1},
        ]

    def test_graph_omitted_when_no_addresses(self) -> None:
        source = """
.slide{
  .body{No title, no id, nothing to address.}
}
"""
        html, _ = html_compile(source)

        assert "nexusGraph" not in html

    def test_graph_is_inert_json(self) -> None:
        html, _ = html_compile(MENU_DECK)

        assert '<script type="application/json" id="nexusGraph">' in html

    def test_script_tag_in_title_cannot_break_out(self) -> None:
        source = """
.slide{
  .title{Evil </script> Title}
  .body{Content.}
}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        # The slug strips the markup entirely, and nothing escapes the
        # script element.
        assert "evil-script-title" in graph["slides"]

    def test_angle_bracket_is_unicode_escaped_not_entity_escaped(
        self,
    ) -> None:
        # Script elements are raw text: an HTML entity here would survive
        # into the parsed payload and corrupt it.
        html, _ = html_compile(MENU_DECK)
        match = re.search(r'id="nexusGraph">(.*?)</script>', html, re.S)
        assert match is not None

        assert "&lt;" not in match.group(1)
        assert "&amp;" not in match.group(1)

    def test_graph_build_is_pure(self) -> None:
        graph = navigationGraph_build(
            {"menu": 1, "spoke": 2}, [("spoke", 1)], 2
        )

        assert graph == {
            "version": 1,
            "slideCount": 2,
            "slides": {"menu": 1, "spoke": 2},
            "jumps": [{"target": "spoke", "targetSlide": 2, "from": 1}],
            "isNexusDeck": False,
            "nexuses": [],
            # No nexus, so the spoke runs to the end of the deck.
            "spokes": [{"address": "spoke", "start": 2, "end": 2}],
        }

    def test_jumps_alone_do_not_make_a_nexus_deck(self) -> None:
        # An ordinary talk with one inline cross-reference must keep its
        # progress indicator and its click-to-advance.
        html, _ = html_compile(MENU_DECK)
        graph = graph_extract(html)

        assert graph["isNexusDeck"] is False
        assert graph["nexuses"] == []
