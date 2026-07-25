"""
Nexus navigation: slide addressing tests

Covers the stage-1 addressing contract — every slide acquires a stable
name from an explicit ``.id{}`` or a slugified ``.title{}``, collisions
are a build error, and the address is emitted for the runtime to consume.

See ``docs/nexus-navigation.adoc``.
"""

import tempfile
from pathlib import Path

import pytest
from slidedown.lib.compiler import Compiler
from slidedown.lib.nexus import (
    SlideAddressCollision,
    slideAddress_register,
    slideAddress_resolve,
    titleSlug_make,
)
from slidedown.lib.parser import Parser


def html_compile(source: str) -> tuple[str, Compiler]:
    """Compile source to HTML, returning the HTML and the compiler.

    Args:
        source: Slidedown source text.

    Returns:
        Tuple of rendered HTML and the compiler that produced it.
    """
    ast = Parser(source).parse()

    with tempfile.TemporaryDirectory() as tmpdir:
        assets_dir = Path(__file__).parent.parent / "assets"
        compiler = Compiler(
            ast=ast,
            output_dir=tmpdir,
            assets_dir=str(assets_dir),
            verbosity=0,
        )
        compiler.compile()
        html = (Path(tmpdir) / "index.html").read_text()

    return html, compiler


class TestTitleSlug:
    """Slugification of slide titles into addresses"""

    def test_lowercases_and_hyphenates(self) -> None:
        assert titleSlug_make("Does It Survive a Re-Run?") == (
            "does-it-survive-a-re-run"
        )

    def test_collapses_runs_of_punctuation(self) -> None:
        assert titleSlug_make("Gen  --  vs  --  Pred") == "gen-vs-pred"

    def test_trims_leading_and_trailing_hyphens(self) -> None:
        assert titleSlug_make("...Thread 3...") == "thread-3"

    def test_title_without_alphanumerics_yields_empty(self) -> None:
        assert titleSlug_make("!!! ???") == ""

    def test_empty_title_yields_empty(self) -> None:
        assert titleSlug_make("") == ""


class TestAddressResolution:
    """Explicit id versus slugified title"""

    def test_explicit_id_wins_over_title(self) -> None:
        assert slideAddress_resolve("rerun", "Some Long Title") == "rerun"

    def test_falls_back_to_title_when_no_id(self) -> None:
        assert slideAddress_resolve("", "The Menu") == "the-menu"

    def test_explicit_id_is_itself_slugified(self) -> None:
        assert slideAddress_resolve("Re Run!", "") == "re-run"

    def test_whitespace_only_id_falls_back_to_title(self) -> None:
        assert slideAddress_resolve("   ", "The Menu") == "the-menu"

    def test_no_id_and_no_title_is_unaddressable(self) -> None:
        assert slideAddress_resolve("", "") == ""


class TestAddressRegistration:
    """Collision detection while accumulating addresses"""

    def test_registers_address(self) -> None:
        addresses: dict[str, int] = {}
        slideAddress_register(addresses, "menu", 2)
        assert addresses == {"menu": 2}

    def test_empty_address_is_ignored(self) -> None:
        addresses: dict[str, int] = {}
        slideAddress_register(addresses, "", 2)
        assert addresses == {}

    def test_collision_raises(self) -> None:
        addresses: dict[str, int] = {"menu": 2}
        with pytest.raises(SlideAddressCollision) as excinfo:
            slideAddress_register(addresses, "menu", 5)

        message = str(excinfo.value)
        assert "menu" in message
        assert "slide 2" in message
        assert "slide 5" in message

    def test_reregistering_same_slide_is_not_a_collision(self) -> None:
        addresses: dict[str, int] = {"menu": 2}
        slideAddress_register(addresses, "menu", 2)
        assert addresses == {"menu": 2}


class TestAddressingEndToEnd:
    """Addresses through the full compile pipeline"""

    def test_title_derived_address_is_emitted(self) -> None:
        source = """
.slide{
  .title{The Menu}
  .body{Pick one.}
}
"""
        html, compiler = html_compile(source)

        assert 'data-address="the-menu"' in html
        assert compiler.slide_addresses == {"the-menu": 1}

    def test_explicit_id_overrides_title(self) -> None:
        source = """
.slide{
  .id{menu}
  .title{A Very Long Title Nobody Wants To Type}
  .body{Pick one.}
}
"""
        html, compiler = html_compile(source)

        assert 'data-address="menu"' in html
        assert compiler.slide_addresses == {"menu": 1}

    def test_id_directive_emits_no_visible_output(self) -> None:
        source = """
.slide{
  .id{menu}
  .title{The Menu}
  .body{Pick one.}
}
"""
        html, _ = html_compile(source)

        # The id is metadata: it must not leak into the slide body.
        body_start = html.find('id="slide-1"')
        body = html[body_start : body_start + 400]
        assert "menu" not in body.replace('data-address="menu"', "")

    def test_multiple_slides_each_get_addresses(self) -> None:
        source = """
.slide{
  .title{First Slide}
  .body{One.}
}

.slide{
  .id{second}
  .title{Second Slide}
  .body{Two.}
}
"""
        _, compiler = html_compile(source)

        assert compiler.slide_addresses == {
            "first-slide": 1,
            "second": 2,
        }

    def test_untitled_slide_is_unaddressable(self) -> None:
        source = """
.slide{
  .body{No title here.}
}
"""
        html, compiler = html_compile(source)

        assert "data-address" not in html
        assert compiler.slide_addresses == {}

    def test_duplicate_titles_fail_the_build(self) -> None:
        source = """
.slide{
  .title{Thread 1}
  .body{One.}
}

.slide{
  .title{Thread 1}
  .body{Also one.}
}
"""
        with pytest.raises(SlideAddressCollision):
            html_compile(source)

    def test_explicit_id_disambiguates_duplicate_titles(self) -> None:
        source = """
.slide{
  .title{Thread 1}
  .body{One.}
}

.slide{
  .id{thread-1-reprise}
  .title{Thread 1}
  .body{Also one.}
}
"""
        _, compiler = html_compile(source)

        assert compiler.slide_addresses == {
            "thread-1": 1,
            "thread-1-reprise": 2,
        }
