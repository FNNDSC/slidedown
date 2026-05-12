"""Compiler and presentation configuration data models."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeAlias, TypedDict

ConfigPrimitive: TypeAlias = str | int | float | bool | None
ConfigValue: TypeAlias = (
    ConfigPrimitive | list["ConfigValue"] | dict[str, "ConfigValue"]
)
CSSConfig: TypeAlias = dict[str, ConfigValue]

# Placeholder maps: parser assigns integer IDs to protected code blocks and
# backslash-escaped sequences; the compiler expands them back during rendering.
PlaceholderMap: TypeAlias = dict[int, str]

# Per-slide counters (slide_number → count) for snippets and typewriters.
SlideCounters: TypeAlias = dict[int, int]

# Maps a config-key name to its CSS property name, used in style-building
# helpers (e.g. {"background": "background-color"}).
CSSPropertyMap: TypeAlias = dict[str, str]

# Internal navbar button definition map: button-type → CSS/HTML property dict.
_NavbarButtonDefs: TypeAlias = dict[str, dict[str, str]]


class CompileResult(TypedDict):
    """Result returned by Compiler.compile()."""

    status: bool
    output_file: str
    slide_count: int


class BuildInfo(TypedDict):
    """Build metadata rendered into generated presentations.

    Attributes:
        version: Slidedown package version string.
        git_hash: First five characters of the current git commit hash.
        label: Display label combining version and commit hash.
    """

    version: str
    git_hash: str
    label: str


class WatermarkConfig(TypedDict, total=False):
    """Watermark configuration from theme or .meta{}."""

    image: str
    position: str
    opacity: float | int | str
    size: str
    offset: str | list[str | int | float] | tuple[str | int | float, ...]


class SlideMasterConfig(TypedDict, total=False):
    """Slide master configuration block."""

    watermarks: list[WatermarkConfig]


class FooterConfig(TypedDict, total=False):
    """Footer text configuration."""

    left: str
    right: str


class ProgressConfig(TypedDict, total=False):
    """Navbar progress-bar configuration."""

    show: bool
    background: str
    height: str
    color: str


NavbarContainerConfig = TypedDict(
    "NavbarContainerConfig",
    {
        "background": str,
        "border": str,
        "border-bottom": str,
        "padding": str,
        "box-shadow": str,
    },
    total=False,
)
"""Navbar container style configuration."""


NavbarItemConfig = TypedDict(
    "NavbarItemConfig",
    {
        "color": str,
        "background": str,
        "border": str,
        "box-shadow": str,
        "margin": str,
        "margin-right": str,
        "size": str,
        "shape": str,
        "icon": str,
        "tooltip": str,
        "format": str,
        "font-size": str,
    },
    total=False,
)
"""Navbar item/button/counter/title configuration."""


NavbarZoneItem: TypeAlias = str | dict[str, NavbarItemConfig]


class NavbarConfig(TypedDict, total=False):
    """Navbar configuration from .meta{}."""

    show: bool
    progress: ProgressConfig
    container: NavbarContainerConfig
    left: list[NavbarZoneItem]
    center: list[NavbarZoneItem]
    right: list[NavbarZoneItem]


class LCARSConfig(TypedDict, total=False):
    """LCARS-specific configuration."""

    data_cascades: bool


class TypographyConfig(TypedDict, total=False):
    """Deck-level typography scale configuration.

    Attributes:
        baseline: Named typography scale preset.
        scale: Explicit numeric typography multiplier. Overrides baseline
            when both fields are present.
    """

    baseline: str
    scale: str | int | float


class SnippetsConfig(TypedDict, total=False):
    """Progressive reveal snippet presentation configuration.

    Attributes:
        marker: CSS content marker used before each ``.o{}`` snippet.
    """

    marker: str


class PresentationMetaConfig(TypedDict, total=False):
    """Presentation-level metadata parsed from .meta{}."""

    title: str
    css: CSSConfig
    watermarks: list[WatermarkConfig]
    slide_master: SlideMasterConfig
    footer: FooterConfig
    navbar: NavbarConfig
    lcars: LCARSConfig
    typography: TypographyConfig
    snippets: SnippetsConfig


class ThemeLike(Protocol):
    """Theme methods consumed by compiler helper modules."""

    name: str

    def assetsDir_get(self) -> Path | None: ...

    def config_get(
        self, key: str, default: ConfigValue = None
    ) -> ConfigValue: ...

    def cssPath_get(self) -> Path | None: ...

    def lcars_is(self) -> bool: ...

    def pygmentsStyle_get(self) -> str: ...

    def templatePath_get(self, template_name: str) -> Path: ...
