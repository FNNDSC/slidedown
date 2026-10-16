"""Tests for wrapping slidedown/theme CSS in a cascade layer."""

from __future__ import annotations

from slidedown.lib.compiler_assets import CSS_LAYER, css_layerWrap


def test_rules_wrapped_in_layer() -> None:
    out = css_layerWrap(".slide h1 { text-align: center; }")
    assert out.startswith(f"@layer {CSS_LAYER} {{")
    assert ".slide h1 { text-align: center; }" in out
    assert out.rstrip().endswith("}")


def test_charset_and_import_hoisted_above_layer() -> None:
    css = (
        '@charset "utf-8";\n'
        "/* fonts */\n"
        "@import url('https://example.com/font.css');\n"
        ".a { color: red; }\n"
    )
    out = css_layerWrap(css)
    layer_at = out.index("@layer")
    assert out.index("@charset") < layer_at
    assert out.index("@import") < layer_at
    assert out.count("@import") == 1
    assert out.index(".a { color: red; }") > layer_at


def test_import_with_semicolon_in_url_kept_whole() -> None:
    url = "https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;700&display=swap"
    out = css_layerWrap(f"@import url('{url}');\n.a {{ color: red; }}\n")
    assert f"@import url('{url}');" in out
    assert out.index("@import") < out.index("@layer")
