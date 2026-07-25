"""
Nexus navigation: nexus placement tests

Covers the stage-3 contract — ``.nexus{}`` marks a deck as a nexus deck,
a nexus can be placed more than once, and each placement drives its own
slide's reveals.

See ``docs/nexus-navigation.adoc``.
"""

import pytest
from slidedown.lib.nexus import (
    UnresolvedNexusRef,
    jumpAddresses_extract,
    nexusBody_rebase,
)

from .test_nexus_addressing import html_compile
from .test_nexus_jumps import graph_extract

SANDWICH_DECK = """
.slide{
  .title{The Menu}
  .body{
    .nexus{.id{menu}
      .o{.jump{.target{depth} Thread 3 -- depth}}
      .o{.jump{.target{registry} Thread 5 -- registry}}
    }
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

.slide{
  .title{Back to the Menu}
  .body{.nexus{.ref{menu}}}
}
"""


class TestNexusRendering:
    """Markup a .nexus{} produces"""

    def test_renders_a_nav_element(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)

        assert '<nav class="sd-nexus" data-nexus="menu">' in html

    def test_nexus_without_id_still_places(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{.nexus{.jump{.target{spoke} Go}}}
}

.slide{
  .id{spoke}
  .title{Spoke}
  .body{Content.}
}
"""
        _, compiler = html_compile(source)

        assert len(compiler.nexus_placements) == 1
        assert compiler.nexus_placements[0][1] == 1


class TestDeckMode:
    """A nexus is what makes a deck a nexus deck"""

    def test_nexus_deck_is_flagged(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        assert graph["isNexusDeck"] is True

    def test_placements_are_listed_in_document_order(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        assert [n["slide"] for n in graph["nexuses"]] == [1, 4]

    def test_placement_carries_ordered_jumps(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        # Order is document order, which is what the digit keys follow.
        assert graph["nexuses"][0]["jumps"] == ["depth", "registry"]


class TestSecondPlacement:
    """.ref{} places an already-defined nexus again"""

    def test_both_placements_share_the_nexus_id(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        assert [n["id"] for n in graph["nexuses"]] == ["menu", "menu"]

    def test_both_placements_offer_the_same_jumps(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        assert graph["nexuses"][0]["jumps"] == graph["nexuses"][1]["jumps"]

    def test_copy_drives_its_own_slide_reveals(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)

        # The copy on slide 4 must not carry slide 1's snippet ids, or it
        # would reveal the wrong slide's content.
        assert 'id="order-4-1"' in html
        assert 'id="order-4-2"' in html
        assert html.count('id="order-1-1"') == 1

    def test_unknown_ref_fails_the_build(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{.nexus{.ref{does-not-exist}}}
}
"""
        with pytest.raises(UnresolvedNexusRef) as excinfo:
            html_compile(source)

        assert "does-not-exist" in str(excinfo.value)

    def test_forward_ref_fails_because_definition_must_precede(
        self,
    ) -> None:
        source = """
.slide{
  .title{Opening Menu}
  .body{.nexus{.ref{menu}}}
}

.slide{
  .title{Real Menu}
  .body{.nexus{.id{menu} .jump{.target{spoke} Go}}}
}

.slide{
  .id{spoke}
  .title{Spoke}
  .body{Content.}
}
"""
        with pytest.raises(UnresolvedNexusRef):
            html_compile(source)


class TestBodyRebase:
    """Unit-level id rewriting"""

    def test_snippet_ids_are_reissued(self) -> None:
        body = '<div class="snippet" id="order-1-1">a</div>'
        snippets: dict[int, int] = {}

        rebased = nexusBody_rebase(body, 4, snippets, {})

        assert 'id="order-4-1"' in rebased
        assert snippets == {4: 1}

    def test_ids_continue_an_existing_count(self) -> None:
        body = '<div id="order-1-1">a</div><div id="order-1-2">b</div>'
        snippets: dict[int, int] = {4: 2}

        rebased = nexusBody_rebase(body, 4, snippets, {})

        assert 'id="order-4-3"' in rebased
        assert 'id="order-4-4"' in rebased
        assert snippets == {4: 4}

    def test_typewriter_ids_are_reissued(self) -> None:
        body = '<pre id="typewriter-1-1"></pre>'
        typewriters: dict[int, int] = {}

        rebased = nexusBody_rebase(body, 4, {}, typewriters)

        assert 'id="typewriter-4-1"' in rebased
        assert typewriters == {4: 1}


class TestJumpAddressExtraction:
    """Reading jump order out of a compiled body"""

    def test_returns_document_order(self) -> None:
        body = '<a data-jump="b"></a><a data-jump="a"></a>'

        assert jumpAddresses_extract(body) == ["b", "a"]

    def test_deduplicates(self) -> None:
        body = '<a data-jump="a"></a><a data-jump="a"></a>'

        assert jumpAddresses_extract(body) == ["a"]

    def test_empty_body_yields_nothing(self) -> None:
        assert jumpAddresses_extract("<p>no jumps</p>") == []
