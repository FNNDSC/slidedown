"""Document, CSS, navigation, and watermark rendering helpers."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from subprocess import CompletedProcess
from typing import Protocol, cast

from ..models.compiler import (
    BuildInfo,
    ConfigValue,
    CSSConfig,
    CSSPropertyMap,
    FooterConfig,
    JumpRefs,
    LCARSConfig,
    NavbarConfig,
    NavbarContainerConfig,
    NavbarItemConfig,
    NavbarZoneItem,
    PresentationMetaConfig,
    ProgressConfig,
    SlideAddresses,
    SnippetsConfig,
    ThemeLike,
    TypographyConfig,
    WatermarkConfig,
    _NavbarButtonDefs,
)
from . import nexus
from .log import LOG

PACKAGE_NAME = "slidedown"
UNKNOWN_GIT_HASH = "nogit"
TYPOGRAPHY_BASELINES: dict[str, float] = {
    "compact": 0.9,
    "normal": 1.0,
    "large": 1.2,
    "xlarge": 1.35,
    "presentation": 1.5,
}


class CompilerRenderer(Protocol):
    """Compiler attributes and methods required by rendering helpers."""

    input_dir: Path
    jump_refs: JumpRefs
    meta_config: PresentationMetaConfig
    slide_addresses: SlideAddresses
    slide_count: int
    standalone: bool
    theme: ThemeLike
    watch: bool

    def config_getMerged(
        self, key: str, default: ConfigValue = None
    ) -> ConfigValue: ...

    def customCSS_generate(self) -> str: ...

    def footer_generate(self) -> str: ...

    def lcarsFrame_generate(self, content: str, navbar_html: str) -> str: ...

    def navbar_generate(self) -> str: ...

    def template_load(self, filename: str) -> str: ...


def config_getMerged(
    compiler: CompilerRenderer, key: str, default: ConfigValue = None
) -> ConfigValue:
    """Get config with .meta{} overriding theme config."""
    keys = key.split(".")
    value: ConfigValue = cast(ConfigValue, compiler.meta_config)
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return compiler.theme.config_get(key, default)
    return value


def buildInfo_resolve() -> BuildInfo:
    """Resolve build metadata for generated output.

    Returns:
        BuildInfo model containing the package version, abbreviated git hash,
        and combined LCARS display label.
    """
    version: str = version_resolve()
    git_hash: str = gitHash_resolve()
    return {
        "version": version,
        "git_hash": git_hash,
        "label": f"v{version}-{git_hash}",
    }


def version_resolve() -> str:
    """Resolve the installed slidedown package version.

    Returns:
        Package version from Python package metadata. Returns ``unknown`` when
        metadata is unavailable, such as in a raw source checkout.
    """
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return "unknown"


def gitHash_resolve() -> str:
    """Resolve the abbreviated git commit hash for this source tree.

    Returns:
        First five characters of the current git commit hash. Returns
        ``nogit`` when the source tree is unavailable or not a git checkout.
    """
    repo_root: Path = Path(__file__).resolve().parents[2]
    result: CompletedProcess[str] = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return UNKNOWN_GIT_HASH

    git_hash: str = result.stdout.strip()
    if len(git_hash) < 5:
        return UNKNOWN_GIT_HASH
    return git_hash[:5]


def lcarsFrame_generate(
    compiler: CompilerRenderer, content: str, navbar_html: str
) -> str:
    """Generate LCARS frame structure wrapping slidedown content."""
    lcars_config = cast(LCARSConfig, compiler.config_getMerged("lcars", {}))
    data_cascades: bool = lcars_config.get("data_cascades", False)

    cascade_html = ""
    if data_cascades:
        cascade_template_path = compiler.theme.templatePath_get(
            "lcars-data-cascade.html"
        )
        if cascade_template_path.exists():
            cascade_html = cascade_template_path.read_text(encoding="utf-8")
        else:
            LOG(
                (
                    "Warning: Data cascade template not found: "
                    f"{cascade_template_path}"
                ),
                level=2,
            )

    frame_template_path = compiler.theme.templatePath_get("lcars-frame.html")
    if not frame_template_path.exists():
        raise FileNotFoundError(
            f"LCARS frame template not found: {frame_template_path}"
        )

    frame_template = frame_template_path.read_text(encoding="utf-8")
    title: str = compiler.meta_config.get("title", "SLIDEDOWN")
    build_info: BuildInfo = buildInfo_resolve()

    return frame_template.format(
        content=content,
        slide_count=compiler.slide_count,
        cascade_html=cascade_html,
        title=title,
        build_info=build_info["label"],
    )


def htmlDocument_build(compiler: CompilerRenderer, content: str) -> str:
    """Build complete HTML document with head, nav, and footer."""
    is_lcars = compiler.theme.lcars_is()
    head_template = "head-lcars.html" if is_lcars else "head.html"
    head_html = compiler.template_load(head_template)
    footer_html = compiler.footer_generate()
    navbar_html = compiler.navbar_generate()
    custom_css = compiler.customCSS_generate()

    if is_lcars:
        form_layout = f'<div class="formLayout">{content}</div>'
        body_content = "\n".join(
            [
                '    <div class="presentation-viewport">',
                _metadata_html("numberOfSlides", str(compiler.slide_count)),
                _metadata_html("slideIDprefix", "slide-"),
                nexus.navigationGraph_htmlEmit(
                    compiler.slide_addresses,
                    compiler.jump_refs,
                    compiler.slide_count,
                ),
                "",
                compiler.lcarsFrame_generate(form_layout, navbar_html),
                "    </div>",
            ]
        )
    else:
        body_content = "\n".join(
            [
                '    <div class="presentation-viewport">',
                _metadata_html("numberOfSlides", str(compiler.slide_count)),
                _metadata_html("slideIDprefix", "slide-"),
                nexus.navigationGraph_htmlEmit(
                    compiler.slide_addresses,
                    compiler.jump_refs,
                    compiler.slide_count,
                ),
                "",
                f"        {navbar_html}",
                "",
                '        <div class="formLayout">',
                f"            {content}",
                "        </div>",
                "",
                f"        {footer_html}",
                "    </div>",
            ]
        )

    live_reload_script = ""
    if compiler.watch:
        live_reload_script = """
    <script>
    (function () {
        var es = new EventSource('/events');
        es.addEventListener('reload', function () {
            window.location.reload();
        });
        es.onerror = function () {
            es.close();
            setTimeout(function () { window.location.reload(); }, 1000);
        };
    })();
    </script>"""

    return f"""<!DOCTYPE html>
<html>
{head_html}{custom_css}
<body>
{body_content}

    <script src="js/slidedown.js"></script>{live_reload_script}
</body>
</html>"""


def customCSS_generate(compiler: CompilerRenderer) -> str:
    """Generate custom CSS from structured presentation metadata.

    Combines deck-level variables from structured metadata with free-form CSS
    rules from ``.meta{css: ...}``.

    Args:
        compiler: Active compiler instance containing parsed metadata.

    Returns:
        HTML ``style`` block, or an empty string when no custom CSS is needed.
    """
    css_config: CSSConfig = compiler.meta_config.get("css", {})

    has_selectors: bool = any(
        key.startswith(".")
        or key.startswith("#")
        or key.startswith("@")
        or "," in key
        for key in css_config.keys()
    ) if css_config and isinstance(css_config, dict) else False
    first_value: ConfigValue = (
        next(iter(css_config.values()))
        if css_config and isinstance(css_config, dict)
        else None
    )
    is_nested_format: bool = has_selectors or isinstance(
        first_value, (dict, list)
    )

    css_rules: list[str] = []
    import_statements: list[str] = []
    typography_css: str = typographyCSS_generate(compiler)
    snippets_css: str = snippetsCSS_generate(compiler)

    if css_config and isinstance(css_config, dict):
        if is_nested_format:
            _cssNested_append(css_config, css_rules, import_statements)
        else:
            _cssFlat_append(css_config, css_rules)

    if (
        not typography_css
        and not snippets_css
        and not css_rules
        and not import_statements
    ):
        return ""

    style_content: list[str] = []
    if import_statements:
        style_content.append("\n".join(import_statements))
    if typography_css:
        style_content.append(typography_css)
    if snippets_css:
        style_content.append(snippets_css)
    if css_rules:
        style_content.append("\n\n".join(css_rules))

    content_str: str = "\n\n".join(style_content)

    return f"""
    <!-- Custom CSS from .meta{{typography/snippets/css: ...}} -->
    <style>
{content_str}
    </style>"""


def typographyCSS_generate(compiler: CompilerRenderer) -> str:
    """Generate deck-level typography CSS variable overrides.

    Args:
        compiler: Active compiler instance containing parsed metadata.

    Returns:
        CSS rule that sets ``--deck-typography-scale``. Returns an empty
        string when typography metadata is absent or invalid.
    """
    typography_config: TypographyConfig | None = compiler.meta_config.get(
        "typography", None
    )
    if not isinstance(typography_config, dict):
        return ""

    scale: float | None = typographyScale_resolve(typography_config)
    if scale is None:
        return ""

    return (
        "    :root {\n"
        f"        --deck-typography-scale: {scale:g};\n"
        "    }"
    )


def typographyScale_resolve(
    typography_config: TypographyConfig,
) -> float | None:
    """Resolve final deck typography scale from metadata.

    Explicit ``scale`` values take precedence over named ``baseline`` values.

    Args:
        typography_config: Parsed typography metadata.

    Returns:
        Numeric typography scale, or None when no valid scale is configured.
    """
    explicit_scale: ConfigValue = typography_config.get("scale", None)
    scale_value: float | None = typographyScale_parse(explicit_scale)
    if scale_value is not None:
        return scale_value

    baseline_name: str = typography_config.get("baseline", "normal")
    return TYPOGRAPHY_BASELINES.get(baseline_name, None)


def typographyScale_parse(scale_value: ConfigValue) -> float | None:
    """Parse an explicit typography scale value.

    Args:
        scale_value: Raw scale value from metadata.

    Returns:
        Positive float scale, or None when the value is absent or invalid.
    """
    if isinstance(scale_value, bool) or scale_value is None:
        return None
    if isinstance(scale_value, (int, float)):
        return float(scale_value) if scale_value > 0 else None
    if isinstance(scale_value, str):
        try:
            parsed_scale: float = float(scale_value)
        except ValueError:
            return None
        return parsed_scale if parsed_scale > 0 else None
    return None


def snippetsCSS_generate(compiler: CompilerRenderer) -> str:
    """Generate deck-level snippet CSS variable overrides.

    Args:
        compiler: Active compiler instance containing parsed metadata.

    Returns:
        CSS rule that sets ``--snippet-marker``. Returns an empty string when
        snippet metadata is absent or invalid.
    """
    snippets_config: SnippetsConfig | None = compiler.meta_config.get(
        "snippets", None
    )
    if not isinstance(snippets_config, dict):
        return ""

    marker: str | None = snippets_config.get("marker", None)
    if not isinstance(marker, str) or marker == "":
        return ""

    return (
        "    :root {\n"
        f"        --snippet-marker: {cssString_quote(marker)};\n"
        "    }"
    )


def cssString_quote(value: str) -> str:
    """Quote text for use as a CSS string token.

    Args:
        value: Raw text value to place in a CSS custom property.

    Returns:
        Double-quoted CSS string with backslashes, quotes, and newlines
        escaped.
    """
    escaped_value: str = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\A ")
    )
    return f'"{escaped_value}"'


def watermarks_generate(compiler: CompilerRenderer) -> str:
    """Generate watermark HTML from merged configuration."""
    watermarks = cast(
        list[WatermarkConfig], compiler.config_getMerged("watermarks", [])
    )
    if not watermarks:
        watermarks = cast(
            list[WatermarkConfig],
            compiler.config_getMerged("slide_master.watermarks", []),
        )

    if not watermarks:
        return ""

    html_parts: list[str] = []
    for watermark in watermarks:
        watermark_html: str = _watermarkHtml_generate(compiler, watermark)
        if watermark_html:
            html_parts.append(watermark_html)

    return "\n        ".join(html_parts)


def footer_generate(compiler: CompilerRenderer) -> str:
    """Generate footer HTML from .meta{footer: {...}} or template."""
    footer_config: FooterConfig | None = compiler.meta_config.get(
        "footer", None
    )

    if not footer_config:
        return compiler.template_load("footer.html")

    left_text: str | None = footer_config.get("left", None)
    right_text: str | None = footer_config.get("right", None)

    html_parts: list[str] = ['<div class="footer-bar">']

    if left_text:
        html_parts.append(_footerSpan_generate("left", left_text))

    if right_text:
        html_parts.append(_footerSpan_generate("right", right_text))

    html_parts.append("</div>")
    return "\n    ".join(html_parts)


def navbar_generate(compiler: CompilerRenderer) -> str:
    """Generate navbar HTML from .meta{navbar: {...}} or template."""
    navbar_config: NavbarConfig | None = compiler.meta_config.get(
        "navbar", None
    )

    if not navbar_config:
        return compiler.template_load("navbar.html")

    if navbar_config.get("show", True) is False:
        return ""

    html_parts: list[str] = [
        '<div class="boxtext pure-control-group" '
        'style="margin-bottom: -3px;">'
    ]

    progress_html: str = _navbarProgress_generate(
        navbar_config.get("progress", {})
    )
    if progress_html:
        html_parts.append(progress_html)

    container_style: str = _styleAttr_build(
        cast(
            Mapping[str, ConfigValue],
            cast(NavbarContainerConfig, navbar_config.get("container", {})),
        ),
        {
            "background": "background",
            "border": "border",
            "border-bottom": "border-bottom",
            "padding": "padding",
            "box-shadow": "box-shadow",
        },
    )
    html_parts.append(f'    <div class="navbar-container"{container_style}>')

    for zone in ("left", "center", "right"):
        html_parts.extend(_navbarZone_generate(navbar_config, zone))

    html_parts.append("    </div>")
    html_parts.append('    <br style="clear: both;">')
    html_parts.append("</div>")

    return "\n".join(html_parts)


def blankLines_insertBreaks(html: str) -> str:
    """Insert <br> tags for blank lines within slides."""

    def process_slide_content(match: re.Match[str]) -> str:
        slide_html = match.group(0)
        return re.sub(r"\n\s*\n+", "\n<br>\n", slide_html)

    return re.sub(
        r'<div class="container slide"[^>]*>.*?</div>',
        process_slide_content,
        html,
        flags=re.DOTALL,
    )


def _metadata_html(element_id: str, value: str) -> str:
    return (
        '        <div class="metaData" '
        f'id="{element_id}" style="display: none;">'
        f"{value}</div>"
    )


def _cssNested_append(
    css_config: CSSConfig,
    css_rules: list[str],
    import_statements: list[str],
) -> None:
    for selector, properties in css_config.items():
        if selector == "@import":
            if isinstance(properties, str):
                import_statements.append(f"    @import url('{properties}');")
            elif isinstance(properties, list):
                for url in properties:
                    import_statements.append(f"    @import url('{url}');")
            continue

        if not isinstance(properties, dict):
            continue

        property_lines: list[str] = _cssPropertyLines_build(properties)
        if property_lines:
            properties_str: str = "\n".join(property_lines)
            css_rules.append(f"    {selector} {{\n{properties_str}\n    }}")


def _cssFlat_append(css_config: CSSConfig, css_rules: list[str]) -> None:
    css_properties: list[str] = _cssPropertyLines_build(css_config)
    if css_properties:
        properties_str: str = "\n".join(css_properties)
        css_rules.append(f"    .container {{\n{properties_str}\n    }}")


def _cssPropertyLines_build(properties: CSSConfig) -> list[str]:
    return [
        f"    {property_name.replace('_', '-')}: {value};"
        for property_name, value in properties.items()
    ]


def _watermarkHtml_generate(
    compiler: CompilerRenderer, watermark: WatermarkConfig
) -> str:
    image: str = watermark.get("image", "")
    if not image:
        return ""

    image_full_path: Path = compiler.input_dir / image
    if not image_full_path.exists():
        LOG(f"Warning: Watermark image not found: {image}", level=1)
        LOG(f"         Expected at: {image_full_path}", level=1)
        return ""

    position: str = watermark.get("position", "bottom-right")
    opacity: float | int | str = watermark.get("opacity", 0.3)
    size: str = watermark.get("size", "100px")
    _watermarkSize_warn(size)

    style_parts: list[str] = [f"opacity: {opacity}", f"width: {size}"]
    offset_x, offset_y = _watermarkOffset_parse(watermark.get("offset", None))

    if offset_x or offset_y:
        _watermarkOffset_apply(style_parts, position, offset_x, offset_y)

    style_attr: str = "; ".join(style_parts)

    return (
        f'<img src="{image}" class="watermark {position}" '
        f'style="{style_attr}" alt="watermark">'
    )


def _watermarkSize_warn(size: str) -> None:
    if re.match(r"^[\d.]+(?:px|%|em|rem|vw|vh|vmin|vmax|ch|ex)$", str(size)):
        return

    LOG(
        (
            f"Warning: Watermark size '{size}' may be invalid. "
            "Use CSS units like px, %, em, rem"
        ),
        level=1,
    )


def _watermarkOffset_parse(
    offset: (
        str | list[str | int | float] | tuple[str | int | float, ...] | None
    ),
) -> tuple[str | None, str | None]:
    offset_x: str | None = None
    offset_y: str | None = None

    if isinstance(offset, str):
        parts = [p.strip() for p in offset.split(",")]
        if len(parts) == 2:
            offset_x = parts[0]
            offset_y = parts[1]
    elif isinstance(offset, (list, tuple)) and len(offset) == 2:
        offset_x = str(offset[0])
        offset_y = str(offset[1])

        if re.match(r"^-?[\d.]+$", offset_x):
            offset_x = f"{offset_x}px"
        if re.match(r"^-?[\d.]+$", offset_y):
            offset_y = f"{offset_y}px"

    return offset_x, offset_y


def _watermarkOffset_apply(
    style_parts: list[str],
    position: str,
    offset_x: str | None,
    offset_y: str | None,
) -> None:
    pos_parts: list[str] = position.split("-")
    vertical: str = pos_parts[0] if len(pos_parts) > 0 else "bottom"
    horizontal: str = pos_parts[1] if len(pos_parts) > 1 else "right"

    if vertical == "top" and offset_y:
        style_parts.append(f"top: {offset_y}")
    elif vertical == "bottom" and offset_y:
        style_parts.append(f"bottom: {offset_y}")

    if horizontal == "left" and offset_x:
        style_parts.append(f"left: {offset_x}")
    elif horizontal == "right" and offset_x:
        style_parts.append(f"right: {offset_x}")


def _footerSpan_generate(side: str, text: str) -> str:
    if _counterTemplate_is(text):
        element_id: str = "footerLeft" if side == "left" else "footerRight"
        return (
            f'    <span class="footer" style="float: {side};" '
            f'data-template="{text}" id="{element_id}"></span>'
        )

    return f'    <span class="footer" style="float: {side};">' f"{text}</span>"


def _counterTemplate_is(text: str | None) -> bool:
    return "{current}" in text or "{total}" in text if text else False


def _navbarProgress_generate(progress_config: ProgressConfig) -> str:
    if not progress_config.get("show", True):
        return ""

    progress_style: str = _styleAttr_build(
        cast(Mapping[str, ConfigValue], progress_config),
        {"background": "background-color", "height": "height"},
    )
    bar_style: str = _styleAttr_build(
        cast(Mapping[str, ConfigValue], progress_config),
        {"color": "background-color"},
    )

    return f"""    <div id="slideProgress"{progress_style}>
        <div id="slideBar"{bar_style}></div>
    </div>"""


def _navbarZone_generate(navbar_config: NavbarConfig, zone: str) -> list[str]:
    html_parts: list[str] = []
    should_float_right: bool = zone == "right"

    zone_items = cast(list[NavbarZoneItem], navbar_config.get(zone, []))
    for item in zone_items:
        if isinstance(item, str):
            item_html: str = _navbarItem_generate(item, {}, should_float_right)
            html_parts.append(item_html)
        elif isinstance(item, dict):
            for item_type, config in item.items():
                item_html = _navbarItem_generate(
                    item_type,
                    cast(NavbarItemConfig, config),
                    should_float_right,
                )
                html_parts.append(item_html)

    return html_parts


def _navbarItem_generate(
    item_type: str, config: NavbarItemConfig, should_float_right: bool
) -> str:
    if item_type == "slide_counter":
        html: str = _navbarCounter_generate(config)
    elif item_type == "title":
        html = _navbarTitle_generate(config)
    else:
        html = _navbarButton_generate(item_type, config)

    if should_float_right:
        return html.replace("float: left", "float: right")
    return html


def _navbarButton_generate(
    button_type: str, config: NavbarItemConfig | None = None
) -> str:
    button_defs: _NavbarButtonDefs = _navbarButtonDefs_get()
    if button_type not in button_defs:
        return ""

    defaults: dict[str, str] = button_defs[button_type]  # inner dict
    config = config or {}
    style_attr: str = _navbarButtonStyle_get(config)
    icon: str = config.get("icon", defaults["icon"])
    tooltip: str = config.get("tooltip", defaults.get("tooltip", ""))
    title_attr: str = f' title="{tooltip}"' if tooltip else ""

    return f"""        <input  type    =  "button"
                    onclick =  "{defaults['onclick']}"
                    value   =  "{icon}"{style_attr}
                    id      =  "{defaults['id']}"
                    name    =  "{defaults['id']}"
                    class   =  "{defaults['class']}"{title_attr}>
            </input>"""


def _navbarCounter_generate(config: NavbarItemConfig) -> str:
    format_str: str = config.get("format", "{current} / {total}")
    style_attr: str = _textStyleAttr_build(config)
    return (
        '        <span class="navbar-counter" '
        f'data-template="{format_str}"{style_attr}></span>'
    )


def _navbarTitle_generate(config: NavbarItemConfig) -> str:
    style_attr: str = _textStyleAttr_build(config)
    return (
        '        <div id="pageTitle" '
        f'class="navbar-title"{style_attr}></div>'
    )


def _navbarButtonStyle_get(config: NavbarItemConfig) -> str:
    style_parts: list[str] = ["float: left"]
    style_parts.extend(
        _styleParts_build(
            # TypedDict is modeled above; cast to mapping for dynamic keys.
            cast(Mapping[str, ConfigValue], config),
            {
                "color": "color",
                "background": "background",
                "border": "border",
                "box-shadow": "box-shadow",
                "margin": "margin",
                "margin-right": "margin-right",
            },
        )
    )

    if "size" in config:
        style_parts.append(f"width: {config['size']}")
        style_parts.append(f"height: {config['size']}")

    if "shape" in config:
        _navbarButtonShape_apply(style_parts, config["shape"])

    return f' style="{"; ".join(style_parts)}"'


def _navbarButtonShape_apply(style_parts: list[str], shape: str) -> None:
    if shape == "round":
        style_parts.append("border-radius: 50%")
        style_parts.append("padding: 0")
        style_parts.append("display: inline-flex")
        style_parts.append("align-items: center")
        style_parts.append("justify-content: center")
    elif shape == "square":
        style_parts.append("border-radius: 0")
    else:
        style_parts.append(f"border-radius: {shape}")


def _textStyleAttr_build(config: NavbarItemConfig) -> str:
    return _styleAttr_build(
        cast(Mapping[str, ConfigValue], config),
        {"color": "color", "font-size": "font-size"},
    )


def _styleAttr_build(
    config: Mapping[str, ConfigValue],
    css_map: CSSPropertyMap,
) -> str:
    style_parts: list[str] = _styleParts_build(config, css_map)
    return f' style="{"; ".join(style_parts)}"' if style_parts else ""


def _styleParts_build(
    config: Mapping[str, ConfigValue],
    css_map: CSSPropertyMap,
) -> list[str]:
    return [
        f"{css_property}: {config[config_key]}"
        for config_key, css_property in css_map.items()
        if config_key in config
    ]


def _navbarButtonDefs_get() -> _NavbarButtonDefs:
    return {
        "slide_first": {
            "id": "first",
            "onclick": "page.advance_toFirst()",
            "icon": "&#xf078",
            "class": "pure-button pure-button-primary fas fa-chevron-down",
            "tooltip": "First slide",
        },
        "slide_previous": {
            "id": "previous",
            "onclick": "page.advance_toPrevious()",
            "icon": "&#xf053",
            "class": "pure-button pure-button-primary fas fas-chevron-left",
            "tooltip": "Previous slide",
        },
        "slide_next": {
            "id": "next",
            "onclick": "page.advance_toNext()",
            "icon": "&#xf054",
            "class": "pure-button pure-button-primary fas fas-chevron-right",
            "tooltip": "Next slide",
        },
        "slide_last": {
            "id": "last",
            "onclick": "page.advance_toLast()",
            "icon": "&#xf077",
            "class": "pure-button pure-button-primary fas fa-chevron-up",
            "tooltip": "Last slide",
        },
    }
