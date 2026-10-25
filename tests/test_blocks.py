"""
.term{}, .takeaway{} and .source{}: named blocks instead of classed divs
"""

from .test_nexus_addressing import html_compile


def deck(body: str) -> str:
    return ".slide{\n  .title{T}\n  .body{\n" + body + "\n  }\n}\n"


def test_term_is_a_div_with_class_term() -> None:
    html, _ = html_compile(deck(".term{.o{line}}"))
    assert '<div class="term">' in html


def test_takeaway_and_source() -> None:
    html, _ = html_compile(deck(".takeaway{REMEMBER THIS.}\n.source{ASTP 2025}"))
    assert '<div class="takeaway">REMEMBER THIS.</div>' in html
    assert '<div class="source">ASTP 2025</div>' in html


def test_extra_class_still_allowed() -> None:
    html, _ = html_compile(deck(".takeaway{.class{loud} X}"))
    assert '<div class="takeaway loud">' in html
