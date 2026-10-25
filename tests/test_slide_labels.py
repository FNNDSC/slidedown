"""
Slide labels: derived from the navigation graph, overridable per slide

A deck sets one template in ``.meta{label: ...}``; every slide's label is
filled in from where it sits -- the spoke it belongs to and that spoke's
number in its menu -- so labels follow slides when they move. ``.label{}``
on a slide replaces its label.
"""

import re

from slidedown.lib.nexus import slideLabels_compute, slideLabelsCSS_generate

from .test_nexus_addressing import html_compile

DECK = """
.meta{
  label: "me@host: ~ {n} {spoke}"
}

.slide{.id{intro}
  .title{Intro}
  .body{hi}
}

.slide{.id{menu}
  .title{Menu}
  .body{
    .nexus{.id{m}
      .div{.jump{.target{alpha-beta} A}}
      .div{.jump{.target{gamma} G}}
    }
  }
}

.slide{.id{alpha-beta}
  .title{A1}
  .body{a1}
}

.slide{
  .title{A2}
  .body{a2}
}

.slide{.id{gamma}.label{custom {spoke} {n}}
  .title{G}
  .body{g}
}
"""


def labels_extract(html: str) -> dict[int, str]:
    """Pull the emitted --sd-label values out of compiled HTML."""
    return {
        int(n): text
        for n, text in re.findall(
            r"#slide-(\d+) \{ --sd-label: '((?:[^'\\]|\\.)*)'; \}", html
        )
    }


class TestDerivedLabels:
    def test_every_slide_gets_a_label(self) -> None:
        html, _ = html_compile(DECK)
        assert sorted(labels_extract(html)) == [1, 2, 3, 4, 5]

    def test_slide_outside_a_spoke_uses_its_own_address(self) -> None:
        labels = labels_extract(html_compile(DECK)[0])
        assert labels[1] == "me@host: ~ intro"
        assert labels[2] == "me@host: ~ menu"

    def test_spoke_slides_carry_number_and_name(self) -> None:
        labels = labels_extract(html_compile(DECK)[0])
        assert labels[3] == "me@host: ~ 01 alpha beta"
        # The spoke's second slide has no .id{} of its own.
        assert labels[4] == "me@host: ~ 01 alpha beta"

    def test_override_replaces_and_still_fills_placeholders(self) -> None:
        labels = labels_extract(html_compile(DECK)[0])
        assert labels[5] == "custom gamma 02"

    def test_no_template_no_labels(self) -> None:
        html, _ = html_compile(DECK.replace('label: "me@host: ~ {n} {spoke}"', ""))
        assert labels_extract(html) == {5: "custom gamma 02"}


class TestLabelHelpers:
    def test_empty_inputs(self) -> None:
        assert slideLabels_compute("", {}, [], [], 0) == {}

    def test_css_escapes_quotes_and_angle_brackets(self) -> None:
        css = slideLabelsCSS_generate({1: "it's </style>"})
        assert css == "#slide-1 { --sd-label: 'it\\'s \\3c /style>'; }"
