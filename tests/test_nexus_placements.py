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


class TestSpokeExtents:
    """Where a spoke ends, which is what the mirror rule turns on"""

    def test_single_slide_spokes_are_the_common_case(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "depth", "start": 2, "end": 2},
            {"address": "registry", "start": 3, "end": 3},
        ]

    def test_spoke_runs_until_the_next_boundary(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{.nexus{.id{menu} .jump{.target{first} First}}}
}

.slide{
  .id{first}
  .title{First Spoke Slide}
  .body{One.}
}

.slide{
  .title{Still In The First Spoke}
  .body{Two.}
}

.slide{
  .title{Also In The First Spoke}
  .body{Three.}
}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        # Nothing else is a target or a placement, so the spoke runs to
        # the end of the deck.
        assert graph["spokes"] == [
            {"address": "first", "start": 2, "end": 4}
        ]

    def test_next_target_bounds_the_previous_spoke(self) -> None:
        source = """
.slide{
  .title{Menu}
  .body{
    .nexus{.id{menu}
      .jump{.target{a} A}
      .jump{.target{b} B}
    }
  }
}

.slide{
  .id{a}
  .title{Spoke A}
  .body{One.}
}

.slide{
  .title{Continues A}
  .body{Two.}
}

.slide{
  .id{b}
  .title{Spoke B}
  .body{Three.}
}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "a", "start": 2, "end": 3},
            {"address": "b", "start": 4, "end": 4},
        ]

    def test_closing_nexus_bounds_the_last_spoke(self) -> None:
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        # The registry spoke stops at slide 3 because slide 4 places a
        # nexus, rather than running to the end of the deck.
        assert graph["spokes"][-1]["end"] == 3


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


class TestNestedSpokes:
    """Spokes containing menus of their own, to any depth"""

    def test_subMenu_onTheSpokesOwnSlide(self) -> None:
        """A spoke whose first slide is itself a menu."""
        source = """
.slide{
  .title{Top}
  .body{.nexus{.id{top} .jump{.target{alpha} Alpha} .jump{.target{beta} Beta}}}
}

.slide{
  .id{alpha}
  .title{Alpha}
  .body{.nexus{.id{sub} .jump{.target{one} One} .jump{.target{two} Two}}}
}

.slide{.id{one} .title{One} .body{1}}
.slide{.id{two} .title{Two} .body{2}}
.slide{.id{beta} .title{Beta} .body{B}}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "alpha", "start": 2, "end": 2},
            {"address": "one", "start": 3, "end": 3},
            {"address": "two", "start": 4, "end": 4},
            {"address": "beta", "start": 5, "end": 5},
        ]

    def test_subMenu_midSpoke_doesNotOrphanTheSlidesBeforeIt(self) -> None:
        """
        A menu partway through a spoke belongs to that spoke.

        The flat rule stopped the spoke dead at the menu, so advancing
        off the slide before it returned to the top and the menu slide
        could not be reached at all.
        """
        source = """
.slide{
  .title{Top}
  .body{.nexus{.id{top} .jump{.target{alpha} Alpha}}}
}

.slide{.id{alpha} .title{Alpha} .body{A}}

.slide{
  .id{alpha2}
  .title{Alpha Continued}
  .body{.nexus{.id{sub} .jump{.target{deep} Deep}}}
}

.slide{.id{deep} .title{Deep} .body{D}}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "alpha", "start": 2, "end": 3},
            {"address": "deep", "start": 4, "end": 4},
        ]

    def test_nesting_goesThreeDeep(self) -> None:
        """Depth is not capped; the rule is the same at every level."""
        source = """
.slide{
  .title{L0}
  .body{.nexus{.id{n0} .jump{.target{l1} Level One}}}
}

.slide{
  .id{l1}
  .title{L1}
  .body{.nexus{.id{n1} .jump{.target{l2} Level Two}}}
}

.slide{
  .id{l2}
  .title{L2}
  .body{.nexus{.id{n2} .jump{.target{l3} Level Three}}}
}

.slide{.id{l3} .title{L3} .body{bottom}}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "l1", "start": 2, "end": 2},
            {"address": "l2", "start": 3, "end": 3},
            {"address": "l3", "start": 4, "end": 4},
        ]

    def test_menuShownAgain_stillEndsTheSpokeItSitsIn(self) -> None:
        """
        A nexus that only points backwards is not opening a section.

        This is what separates a sub-menu from the same menu placed a
        second time at the end of a deck, which the sandwich deck does
        and which must keep its old extents.
        """
        html, _ = html_compile(SANDWICH_DECK)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "depth", "start": 2, "end": 2},
            {"address": "registry", "start": 3, "end": 3},
        ]

    def test_spokeExtents_neverOverlap(self) -> None:
        """
        Nesting must not put a slide in two spokes at once.

        The runtime asks only "which spoke is this slide in", so two
        answers would mean returning to whichever was found first.
        """
        source = """
.slide{
  .title{Top}
  .body{.nexus{.id{top} .jump{.target{alpha} Alpha} .jump{.target{beta} Beta}}}
}

.slide{
  .id{alpha}
  .title{Alpha}
  .body{.nexus{.id{sub} .jump{.target{one} One}}}
}

.slide{.id{one} .title{One} .body{1}}
.slide{.title{One Continued} .body{1b}}
.slide{.id{beta} .title{Beta} .body{B}}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        claimed: dict[int, str] = {}
        for spoke in graph["spokes"]:
            for slide in range(spoke["start"], spoke["end"] + 1):
                assert slide not in claimed, (
                    f"slide {slide} claimed by both "
                    f"{claimed.get(slide)} and {spoke['address']}"
                )
                claimed[slide] = spoke["address"]

    def test_twoMenus_listingTheSameTopics_declareOneSpokeEach(self) -> None:
        """
        A topic listed by two menus is one spoke, not two.

        The demo deck opens with a live menu and follows it with the same
        topics revealed one at a time. Both point forward, so both would
        derive a spoke for every topic — and the two derivations do not
        agree on where those spokes end, because the second runs after
        the sub-menus have been accounted for. The runtime asks only
        which spoke a slide is in, so two answers is one too many.
        """
        source = """
.slide{
  .title{Quick}
  .body{.nexus{.id{quick}
    .jump{.target{alpha} Alpha}
    .jump{.target{beta} Beta}
  }}
}

.slide{
  .title{Revealed}
  .body{.nexus{.id{topics}
    .jump{.target{alpha} Alpha}
    .jump{.target{beta} Beta}
  }}
}

.slide{.id{alpha} .title{Alpha} .body{A}}

.slide{
  .id{alpha2}
  .title{Alpha Continued}
  .body{.nexus{.id{sub} .jump{.target{deep} Deep}}}
}

.slide{.id{deep} .title{Deep} .body{D}}
.slide{.id{beta} .title{Beta} .body{B}}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        assert graph["spokes"] == [
            {"address": "alpha", "start": 3, "end": 4},
            {"address": "deep", "start": 5, "end": 5},
            {"address": "beta", "start": 6, "end": 6},
        ]

    def test_everySpokeStart_isDeclaredOnce(self) -> None:
        """No slide begins two spokes, however many menus name it."""
        source = """
.slide{.title{One} .body{.nexus{.id{a} .jump{.target{t} T}}}}
.slide{.title{Two} .body{.nexus{.id{b} .jump{.target{t} T}}}}
.slide{.title{Three} .body{.nexus{.id{c} .jump{.target{t} T}}}}
.slide{.id{t} .title{T} .body{target}}
"""
        html, _ = html_compile(source)
        graph = graph_extract(html)

        starts = [spoke["start"] for spoke in graph["spokes"]]
        assert starts == sorted(set(starts))
