"""
Slide transition tests

Motion is opt-in, and the compiler decides once — at build time — which
transition a deck gets, so the runtime never has to interpret a value it
might not understand.

See ``docs/nexus-navigation.adoc``.
"""

from typing import Any

import pytest
from slidedown.lib.compiler_rendering import (
    TRANSITION_DEFAULT,
    transition_resolve,
)

from .test_nexus_addressing import html_compile

DECK_PLAIN = """
.slide{
  .title{Only Slide}
  .body{
    Nothing to see here.
  }
}
"""

DECK_ZOOM = """
.meta{
transition: zoom
}

.slide{
  .title{Only Slide}
  .body{
    Nothing to see here.
  }
}
"""


@pytest.mark.parametrize(
    "requested,expected",
    [
        ("zoom", "zoom"),
        ("none", "none"),
        # Case and stray whitespace are an author's business, not an error.
        ("ZOOM", "zoom"),
        ("  zoom  ", "zoom"),
    ],
)
def test_knownTransitions_accepted(requested: str, expected: str) -> None:
    """A transition the runtime can drive survives resolution."""
    assert transition_resolve({"transition": requested}) == expected


@pytest.mark.parametrize(
    "requested",
    ["swirl", "", "   ", "cube", "3"],
)
def test_unknownTransition_fallsBackToNone(requested: str) -> None:
    """An unrecognised transition degrades rather than reaching the DOM."""
    assert transition_resolve({"transition": requested}) == TRANSITION_DEFAULT


def test_absentKey_fallsBackToNone() -> None:
    """A deck that says nothing keeps the instant swap it always had."""
    assert transition_resolve({}) == TRANSITION_DEFAULT


def test_nonStringValue_fallsBackToNone() -> None:
    """YAML hands over whatever was written; a bad type is not a crash."""
    meta: Any = {"transition": 7}
    assert transition_resolve(meta) == TRANSITION_DEFAULT


def test_defaultDeck_emitsNoMotion() -> None:
    """Every existing deck compiles to the transition it already had."""
    html, _ = html_compile(DECK_PLAIN)
    assert 'id="slideTransition"' in html
    assert ">none</div>" in html


def test_zoomDeck_emitsZoom() -> None:
    """An opted-in deck carries its choice into the compiled page."""
    html, _ = html_compile(DECK_ZOOM)
    assert 'id="slideTransition"' in html
    assert ">zoom</div>" in html
