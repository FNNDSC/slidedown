"""
Bar charts: .bars{} draws rows from data

Covers parsing (label vs modifiers), scaling (largest value, .max{}, a new
scale after each .caption{}), half-character fills, grouped bars against
.key{} series, colours, default shown text, vertical layout, and that every
row is a numbered progressive-reveal snippet.
"""

import re

import pytest
from slidedown.lib.bars import BarsError, color_resolve

from .test_nexus_addressing import html_compile


def deck(chart: str) -> str:
    return ".slide{\n  .title{T}\n  .body{\n" + chart + "\n  }\n}\n"


def rows(html: str) -> list[str]:
    return re.findall(r'<div class="snippet sl-hidden[^"]*" id="order-1-\d+">(.*?)</div>', html)


class TestSingleSeries:
    CHART = """
    .bars{.unit{%}
      .bar{health systems .value{75}}
      .bar{physicians .value{81}}
    }
    """

    def test_label_and_default_show(self) -> None:
        first = rows(html_compile(deck(self.CHART))[0])[0]
        assert '<span class="lbl">health systems</span>' in first
        assert '<span class="pct">75%</span>' in first

    def test_largest_value_fills_the_width(self) -> None:
        second = rows(html_compile(deck(self.CHART))[0])[1]
        assert "--w: 20ch" in second
        assert "█" * 20 + "<" in second

    def test_fill_floors_to_half_characters(self) -> None:
        first = rows(html_compile(deck(self.CHART))[0])[0]
        # 75 / 81 * 20 = 18.5..., so 18 and a half.
        assert "█" * 18 + "▌<" in first
        assert "--w: 19ch" in first

    def test_rows_are_numbered_snippets(self) -> None:
        html, _ = html_compile(deck(self.CHART))
        assert 'id="order-1-1"' in html and 'id="order-1-2"' in html


class TestScaleAndCaptions:
    def test_fixed_max(self) -> None:
        html, _ = html_compile(deck(".bars{.max{100} .bar{a .value{50}}}"))
        assert "--w: 10ch" in rows(html)[0]

    def test_caption_starts_a_new_scale(self) -> None:
        chart = """
        .bars{
          .caption{$ trillions}
          .bar{needed .value{8.5}}
          .caption{gigawatts}
          .bar{scheduled .value{13.6}}
          .bar{delivered .value{2.2}}
        }
        """
        r = rows(html_compile(deck(chart))[0])
        assert r[0] == '<span class="dim">$ trillions</span>'
        assert "--w: 20ch" in r[1]  # largest of its own group
        assert "--w: 20ch" in r[3]
        assert "--w: 3ch" in r[4]


class TestShowAndColor:
    def test_show_overrides_and_color_applies(self) -> None:
        chart = ".bars{.bar{.color{red} OpenAI lost .value{20.9} .show{$20.9B}}}"
        r = rows(html_compile(deck(chart))[0])[0]
        assert '<span class="lbl">OpenAI lost</span>' in r
        assert "$20.9B" in r
        assert r.count("var(--sd-color-red, red)") == 2  # bar and value

    def test_uncoloured_bar_uses_theme_default(self) -> None:
        r = rows(html_compile(deck(".bars{.bar{a .value{1}}}"))[0])[0]
        assert 'class="grow bar"' in r

    def test_word_unit_gets_a_space(self) -> None:
        r = rows(html_compile(deck(".bars{.unit{GW} .bar{a .value{6.4}}}"))[0])[0]
        assert "6.4 GW" in r

    def test_color_resolve(self) -> None:
        assert color_resolve("magenta") == "var(--sd-color-magenta, magenta)"
        assert color_resolve("#ff8800") == "#ff8800"


class TestGrouped:
    CHART = """
    .bars{.unit{%} .max{100}
      .key{.color{accent} predictive}
      .key{.color{magenta} generative}
      .bar{rural .value{56} .value{25.4}}
    }
    """

    def test_legend_row_from_keys(self) -> None:
        legend = rows(html_compile(deck(self.CHART))[0])[0]
        assert ">predictive<" in legend and ">generative<" in legend

    def test_values_share_the_width_and_stagger(self) -> None:
        bar = rows(html_compile(deck(self.CHART))[0])[1]
        assert "--w: 6ch" in bar  # 56% of 10ch, floored to 5.5
        assert 'class="grow g2"' in bar
        assert bar.count('class="pair"') == 2

    def test_value_count_must_match_keys(self) -> None:
        bad = self.CHART.replace(".value{25.4}", "")
        with pytest.raises(BarsError):
            html_compile(deck(bad))


class TestVertical:
    def test_columns_in_one_row(self) -> None:
        chart = ".bars{.layout{vertical} .bar{a .value{1}} .bar{b .value{2}}}"
        r = rows(html_compile(deck(chart))[0])
        assert len(r) == 1
        assert r[0].count('class="sd-vcol"') == 2
        assert "--h: 5.00em" in r[0]

    def test_unknown_layout(self) -> None:
        with pytest.raises(BarsError):
            html_compile(deck(".bars{.layout{diagonal} .bar{a .value{1}}}"))

    def test_bar_without_value(self) -> None:
        with pytest.raises(BarsError):
            html_compile(deck(".bars{.bar{a}}"))
