"""Theme loading and validation for slidedown presentations.

This module resolves theme directories for editable source checkouts and
installed packages. A theme provides a ``theme.yaml`` configuration file,
``theme.css`` stylesheet, optional assets, and optional templates used by
specialized themes such as LCARS.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from ..models.compiler import CSSConfig, ConfigValue


class ThemeError(Exception):
    """Raised when theme loading or validation fails."""


class Theme:
    """Represent a loaded slidedown theme.

    Attributes:
        name: Theme directory name.
        themes_dir: Base directory that contains available themes.
        theme_dir: Directory for the selected theme.
        config_path: Path to the selected theme's ``theme.yaml``.
        config: Parsed theme configuration.
        css_path: Path to the selected theme's ``theme.css``.
        assets_dir: Optional theme assets directory.
    """

    def __init__(self, theme_name: str, themes_dir: str = "themes") -> None:
        """Load a theme by name.

        Args:
            theme_name: Name of the theme directory, such as ``default``.
            themes_dir: Preferred path to the themes directory.

        Raises:
            ThemeError: If the theme directory or required files do not exist.
        """
        self.name: str = theme_name
        self.themes_dir: Path = self.themeBaseDir_resolve(themes_dir)
        self.theme_dir: Path = self.themes_dir / theme_name

        if not self.theme_dir.exists():
            raise ThemeError(
                f"Theme '{theme_name}' not found. "
                f"Expected directory: {self.theme_dir}"
            )

        self.config_path: Path = self.theme_dir / "theme.yaml"
        if not self.config_path.exists():
            raise ThemeError(f"Theme '{theme_name}' missing theme.yaml")

        self.config: CSSConfig = self._config_load()
        self.css_path: Path = self.theme_dir / "theme.css"
        self.assets_dir: Path = self.theme_dir / "assets"

    @staticmethod
    def themeBaseDir_resolve(themes_dir: str) -> Path:
        """Resolve the base directory that contains themes.

        Resolution favors the explicit/current-working-directory path first for
        development, then the editable checkout layout, then installed
        ``share/slidedown/themes`` data files.

        Args:
            themes_dir: Preferred themes directory path.

        Returns:
            Existing themes base directory if found; otherwise the preferred
            path so downstream error messages show the requested location.
        """
        requested_path: Path = Path(themes_dir)
        package_root: Path = Path(__file__).resolve().parents[1]
        candidate_paths: list[Path] = [
            requested_path,
            Path.cwd() / themes_dir,
            package_root.parent / themes_dir,
            Path(sys.prefix) / "share" / "slidedown" / "themes",
        ]

        for candidate_path in candidate_paths:
            if candidate_path.exists():
                return candidate_path

        return requested_path

    def _config_load(self) -> CSSConfig:
        """Load and parse the selected theme configuration.

        Returns:
            Parsed ``theme.yaml`` content.

        Raises:
            ThemeError: If YAML parsing or file reading fails.
        """
        try:
            with open(self.config_path) as f:
                config: ConfigValue = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ThemeError(f"Failed to parse theme.yaml: {e}") from e
        except Exception as e:
            raise ThemeError(f"Failed to load theme.yaml: {e}") from e

        if config is None:
            return {}
        if not isinstance(config, dict):
            raise ThemeError("theme.yaml must contain a mapping")
        return config

    def css_has(self) -> bool:
        """Check whether the theme has a custom CSS file.

        Returns:
            True when ``theme.css`` exists.
        """
        return self.css_path.exists()

    def assets_has(self) -> bool:
        """Check whether the theme has an assets directory.

        Returns:
            True when the optional assets directory exists.
        """
        return self.assets_dir.exists() and self.assets_dir.is_dir()

    def cssPath_get(self) -> Path | None:
        """Get path to theme CSS file.

        Returns:
            Path to ``theme.css`` if present, otherwise None.
        """
        return self.css_path if self.css_has() else None

    def assetsDir_get(self) -> Path | None:
        """Get path to theme assets directory.

        Returns:
            Path to assets directory if present, otherwise None.
        """
        return self.assets_dir if self.assets_has() else None

    def templatePath_get(self, template_name: str) -> Path:
        """Get a path to a theme-local template.

        Args:
            template_name: Template filename inside the theme's ``templates``
                directory.

        Returns:
            Path to the requested template.
        """
        return self.theme_dir / "templates" / template_name

    def lcars_is(self) -> bool:
        """Check whether the theme uses the LCARS frame integration.

        Returns:
            True when the theme name uses the LCARS prefix.
        """
        return self.name.startswith("lcars")

    def config_get(self, key: str, default: ConfigValue = None) -> ConfigValue:
        """Get a configuration value from ``theme.yaml``.

        Supports nested keys with dot notation.

        Args:
            key: Configuration key, such as ``colors.background``.
            default: Value to return when the key does not exist.

        Returns:
            Configuration value or default.
        """
        keys: list[str] = key.split(".")
        value: ConfigValue = self.config

        for key_part in keys:
            if isinstance(value, dict) and key_part in value:
                value = value[key_part]
            else:
                return default

        return value

    def pygmentsStyle_get(self) -> str:
        """Get Pygments style name for syntax highlighting.

        Returns:
            Pygments style name.
        """
        value: object = self.config_get("code.pygments_style", "monokai")
        return str(value)

    def __repr__(self) -> str:
        """Return a compact debug representation."""
        return f"Theme(name='{self.name}', path='{self.theme_dir}')"


def themes_listAvailable(themes_dir: str = "themes") -> list[str]:
    """List all available theme names.

    Args:
        themes_dir: Path to themes directory.

    Returns:
        Sorted list of theme names that contain ``theme.yaml``.
    """
    themes_path: Path = Theme.themeBaseDir_resolve(themes_dir)

    if not themes_path.exists():
        return []

    themes: list[str] = []
    for item in themes_path.iterdir():
        if item.is_dir() and (item / "theme.yaml").exists():
            themes.append(item.name)

    return sorted(themes)


def theme_validate(
    theme_name: str, themes_dir: str = "themes"
) -> tuple[bool, str]:
    """Validate a theme's structure and configuration.

    Args:
        theme_name: Name of theme to validate.
        themes_dir: Path to themes directory.

    Returns:
        Tuple containing validity and a human-readable status message.
    """
    try:
        theme: Theme = Theme(theme_name, themes_dir)

        if not theme.css_has():
            return (
                False,
                f"Warning: Theme '{theme_name}' has no theme.css file",
            )

        if not theme.config:
            return False, f"Theme '{theme_name}' has empty configuration"

        return True, f"Theme '{theme_name}' is valid"

    except ThemeError as e:
        return False, str(e)
