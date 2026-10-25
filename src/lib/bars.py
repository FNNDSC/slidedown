"""
Bar charts: ``.bars{}`` and its parts

A chart is written as data and the compiler draws it::

    .bars{.unit{%} .max{100}
      .key{.color{accent} predictive}
      .key{.color{magenta} generative}
      .bar{all hospitals .value{71} .value{31.5}}
      .caption{a dim heading row; starts a new scale}
      .bar{.color{red} OpenAI lost .value{20.9} .show{$20.9B}}
    }

Inside ``.bar{}``, ``.key{}`` and ``.caption{}``, anything in a modifier
is data and the bare text left over is the label. ``.value{}`` is a plain
number setting the bar's length; ``.show{}`` is the text printed at its end
(default: the value plus the chart's ``.unit{}``); ``.color{}`` is a theme
palette name (``accent``, ``red``, ...) or any CSS colour.

Children compile before their parent, so each part hands its data up as an
inert token in its parent's content; ``.bars{}`` collects the tokens in
order and emits the chart. Each row is a progressive-reveal snippet.
Horizontal rows are emitted directly (no wrapper), so a theme's rules for
snippets inside a container -- a cursor following the last revealed line,
say -- apply to chart rows as to any other.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from ..models.directives import DirectiveCategory, DirectiveSpec
from ..models.handlers import CompilerContext, DirectiveNode

# Total character width of a horizontal chart's bars; grouped bars share it.
BAR_WIDTH_CH = 20
# Height of the tallest column in a vertical chart.
COLUMN_HEIGHT_EM = 5.0

_TOKEN_RE = re.compile(r"\x01sdbar (.*?)\x02", re.S)


class BarsError(ValueError):
    """A chart that cannot be drawn as written."""


def _token(kind: str, **data: Any) -> str:
    """Wrap a part's data as an inert token for its parent to collect."""
    return "\x01sdbar " + json.dumps({"kind": kind, **data}) + "\x02"


def _tokens_split(content: str) -> tuple[list[dict[str, Any]], str]:
    """Separate child tokens from the bare text around them.

    Returns:
        The tokens in order, and the leftover text with whitespace collapsed.
    """
    tokens: list[dict[str, Any]] = [
        json.loads(m.group(1)) for m in _TOKEN_RE.finditer(content)
    ]
    text: str = re.sub(r"\s+", " ", _TOKEN_RE.sub(" ", content)).strip()
    return tokens, text


def color_resolve(name: str) -> str:
    """A palette name becomes the theme's variable, falling back to itself.

    ``red`` -> ``var(--sd-color-red, red)``; ``#ff8800`` stays as written.
    """
    name = name.strip()
    if re.fullmatch(r"[A-Za-z][\w-]*", name):
        return f"var(--sd-color-{name}, {name})"
    return name


def _number(raw: str, where: str) -> float:
    try:
        return float(raw.replace(",", ""))
    except ValueError as exc:
        raise BarsError(f"{where}: .value{{{raw}}} is not a number") from exc


def _show_default(raw: str, unit: str) -> str:
    """Value as written plus the unit: ``71`` + ``%`` -> ``71%``; ``6.4 GW``."""
    if not unit:
        return raw
    return f"{raw}{unit}" if not unit[0].isalnum() else f"{raw} {unit}"


def _fill(units: float) -> str:
    """Block characters for a bar, in half-character steps."""
    whole: int = int(units)
    return "█" * whole + ("▌" if units - whole >= 0.5 else "")


def _halves(value: float, top: float, width: float) -> float:
    """Bar length in characters, floored to a half."""
    if top <= 0 or value <= 0:
        return 0.0
    return math.floor(value / top * width * 2) / 2


def _style(**props: str) -> str:
    body: str = "; ".join(f"{k}: {v}" for k, v in props.items() if v)
    return f' style="{body}"' if body else ""


# ---------------------------------------------------------------------------
# Part handlers: each returns a token for its parent.
# ---------------------------------------------------------------------------


def _scalar_handler(kind: str):
    def handler(node: DirectiveNode, compiler: CompilerContext) -> str:
        return _token(kind, text=node.content.strip())

    return handler


def bar_handler(node: DirectiveNode, compiler: CompilerContext) -> str:
    """``.bar{}``: a label, one ``.value{}`` per series, optional show/color."""
    tokens, label = _tokens_split(node.content)
    values: list[str] = [t["text"] for t in tokens if t["kind"] == "value"]
    shows: list[str] = [t["text"] for t in tokens if t["kind"] == "show"]
    colors: list[str] = [t["text"] for t in tokens if t["kind"] == "color"]
    if not values:
        raise BarsError(
            f".bar{{{label}}} has no .value{{}} (to write a directive name "
            "literally in text, escape it: \\.bar\\{\\})"
        )
    return _token(
        "bar",
        label=label,
        values=values,
        shows=shows,
        color=colors[0] if colors else "",
    )


def key_handler(node: DirectiveNode, compiler: CompilerContext) -> str:
    """``.key{}``: one series of a grouped chart -- its name and colour."""
    tokens, label = _tokens_split(node.content)
    colors: list[str] = [t["text"] for t in tokens if t["kind"] == "color"]
    return _token("key", label=label, color=colors[0] if colors else "")


# ---------------------------------------------------------------------------
# The chart.
# ---------------------------------------------------------------------------


def _snippet(compiler: CompilerContext, inner: str, extra_class: str = "") -> str:
    """One progressive-reveal row, numbered like an ``.o{}``."""
    slide: int = compiler.slide_count
    compiler.snippet_counters[slide] = compiler.snippet_counters.get(slide, 0) + 1
    number: int = compiler.snippet_counters[slide]
    cls: str = f"snippet sl-hidden {extra_class}".strip()
    return f'<div class="{cls}" id="order-{slide}-{number}">{inner}</div>'


def _groups(parts: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split parts into scale groups: each caption starts a new one."""
    groups: list[list[dict[str, Any]]] = [[]]
    for part in parts:
        if part["kind"] == "caption" and groups[-1]:
            groups.append([])
        groups[-1].append(part)
    return groups


def bars_handler(node: DirectiveNode, compiler: CompilerContext) -> str:
    """``.bars{}``: collect the parts and draw the chart."""
    tokens, _stray = _tokens_split(node.content)
    options: dict[str, str] = {}
    parts: list[dict[str, Any]] = []
    for token in tokens:
        if token["kind"] in ("unit", "max", "layout"):
            options[token["kind"]] = token["text"]
        elif token["kind"] in ("bar", "key", "caption"):
            parts.append(token)

    unit: str = options.get("unit", "")
    layout: str = options.get("layout", "horizontal").lower()
    if layout not in ("horizontal", "vertical"):
        raise BarsError(f".layout{{{layout}}}: use horizontal or vertical")
    fixed_max: float | None = (
        _number(options["max"], ".bars .max") if "max" in options else None
    )
    keys: list[dict[str, Any]] = [p for p in parts if p["kind"] == "key"]
    series: int = max(len(keys), 1)

    for part in parts:
        if part["kind"] == "bar" and keys and len(part["values"]) != len(keys):
            raise BarsError(
                f".bar{{{part['label']}}} has {len(part['values'])} values "
                f"for {len(keys)} keys"
            )

    rows: list[str] = []
    legend_done: bool = False
    for group in _groups(parts):
        numbers: list[float] = [
            _number(v, f".bar{{{p['label']}}}")
            for p in group
            if p["kind"] == "bar"
            for v in p["values"]
        ]
        top: float = fixed_max if fixed_max is not None else max(numbers, default=0)
        columns: list[str] = []
        for part in group:
            if part["kind"] == "caption":
                rows.append(
                    _snippet(compiler, f'<span class="dim">{part["text"]}</span>')
                )
            elif part["kind"] == "key":
                if not legend_done:
                    rows.append(_snippet(compiler, _legend(keys, layout)))
                    legend_done = True
            elif layout == "vertical":
                columns.append(_column(part, keys, unit, top, len(columns)))
            else:
                rows.append(_snippet(compiler, _row(part, keys, unit, top, series)))
        if columns:
            # A vertical group reveals as one row; its columns rise in turn.
            rows.append(
                _snippet(
                    compiler,
                    '<span class="sd-bars--vertical">' + "".join(columns) + "</span>",
                )
            )
    return "".join(rows)


def _legend(keys: list[dict[str, Any]], layout: str) -> str:
    items: str = "".join(
        f'<span class="pair"><span{_style(color=color_resolve(k["color"]) if k["color"] else "")}>'
        f'█</span><span class="dim">{k["label"]}</span></span>'
        for k in keys
    )
    lead: str = '<span class="lbl"></span>' if layout == "horizontal" else ""
    return lead + items


def _bar_colors(part: dict[str, Any], keys: list[dict[str, Any]]) -> list[str]:
    if keys:
        return [k["color"] for k in keys]
    return [part["color"]]


def _row(
    part: dict[str, Any],
    keys: list[dict[str, Any]],
    unit: str,
    top: float,
    series: int,
) -> str:
    width: float = BAR_WIDTH_CH / series
    colors: list[str] = _bar_colors(part, keys)
    cells: list[str] = []
    for i, raw in enumerate(part["values"]):
        units: float = _halves(_number(raw, part["label"]), top, width)
        color: str = color_resolve(colors[i]) if colors[i] else ""
        show: str = part["shows"][i] if i < len(part["shows"]) else _show_default(raw, unit)
        stagger: str = f" g{i + 1}" if i else ""
        default_class: str = "" if color else " bar"
        cell: str = (
            f'<span class="grow{default_class}{stagger}"'
            f'{_style(**{"--w": f"{math.ceil(units)}ch", "color": color})}>'
            f'<span class="fill">{_fill(units)}</span></span>'
            f'<span class="pct"{_style(color=color)}>{show}</span>'
        )
        cells.append(f'<span class="pair">{cell}</span>' if keys else cell)
    return f'<span class="lbl">{part["label"]}</span>' + "".join(cells)


def _column(
    part: dict[str, Any],
    keys: list[dict[str, Any]],
    unit: str,
    top: float,
    position: int,
) -> str:
    colors: list[str] = _bar_colors(part, keys)
    cols: list[str] = []
    for i, raw in enumerate(part["values"]):
        value: float = _number(raw, part["label"])
        height: float = (value / top * COLUMN_HEIGHT_EM) if top > 0 else 0.0
        color: str = color_resolve(colors[i]) if colors[i] else ""
        show: str = part["shows"][i] if i < len(part["shows"]) else _show_default(raw, unit)
        default_class: str = "" if color else " bar"
        delay: float = 0.15 * position + 0.25 * i
        cols.append(
            f'<span class="sd-vstack">'
            f'<span class="pct"{_style(color=color)}>{show}</span>'
            f'<span class="vgrow{default_class}"'
            f'{_style(**{"--h": f"{height:.2f}em", "color": color, "transition-delay": f"{delay:.2f}s" if delay else ""})}></span>'
            f"</span>"
        )
    return (
        f'<span class="sd-vcol"><span class="sd-vbars">{"".join(cols)}</span>'
        f'<span class="vlbl">{part["label"]}</span></span>'
    )


def strayParts_check(html: str) -> None:
    """Fail the build if a chart part was used outside a ``.bars{}``.

    Its token would otherwise reach the page as invisible garbage. The
    usual cause is a directive name written in prose; escape it.
    """
    stray: list[str] = sorted(
        {json.loads(m.group(1))["kind"] for m in _TOKEN_RE.finditer(html)}
    )
    if stray:
        names: str = ", ".join(f".{kind}{{}}" for kind in stray)
        raise BarsError(
            f"{names} used outside a .bars{{}} chart (to write a directive "
            "name literally in text, escape it: \\.unit\\{\\})"
        )


def barsDirectives_register(registry: Any) -> None:
    """Register ``.bars{}`` and its parts."""
    specs: list[tuple[str, Any, str, str]] = [
        ("bars", bars_handler, "Bar chart drawn from .bar{} rows",
         ".bars{.unit{%} .bar{rural .value{56}}}"),
        ("bar", bar_handler, "One row of a .bars{} chart",
         ".bar{.color{red} OpenAI lost .value{20.9} .show{$20.9B}}"),
        ("key", key_handler, "A series of a grouped .bars{} chart (legend entry)",
         ".key{.color{magenta} generative}"),
        ("caption", _scalar_handler("caption"),
         "Dim heading row in a .bars{} chart; starts a new scale",
         ".caption{gigawatts per year}"),
        ("value", _scalar_handler("value"), "Number setting a bar's length",
         ".value{13.1}"),
        ("show", _scalar_handler("show"), "Text printed at the end of a bar",
         ".show{$13.1B}"),
        ("color", _scalar_handler("color"), "Bar or key colour: palette name or CSS",
         ".color{red}"),
        ("unit", _scalar_handler("unit"), "Unit appended to values in a chart",
         ".unit{GW}"),
        ("max", _scalar_handler("max"), "Fixed top of a chart's scale",
         ".max{100}"),
        ("layout", _scalar_handler("layout"), "Chart layout: horizontal or vertical",
         ".layout{vertical}"),
    ]
    for name, handler, description, example in specs:
        registry.register(
            DirectiveSpec(
                name=name,
                category=DirectiveCategory.LAYOUT,
                description=description,
                handler=handler,
                examples=[example],
            )
        )
