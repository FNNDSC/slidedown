"""
Theme loader and manager for slidedown presentations.

Themes provide visual styling, layouts, and customization for presentations.
Each theme is a directory containing:
  - theme.yaml: Configuration (colors, fonts, layout settings)
  - theme.css: Custom CSS styles
  - assets/: Optional images, fonts, etc.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ThemeError(Exception):
    """Raised when theme loading or validation fails"""
    pass


class Theme:
    """
    Represents a slidedown theme.

    A theme consists of:
      - Configuration (colors, fonts, layout) from theme.yaml
      - Custom CSS from theme.css
      - Optional assets (images, fonts)
    """

    def __init__(self, theme_name: str, themes_dir: str = "themes"):
        """
        Load a theme by name.

        Args:
            theme_name: Name of the theme directory (e.g., "default", "terminal")
            themes_dir: Path to themes directory (default: "themes")

        Raises:
            ThemeError: If theme directory or required files don't exist
        """
        self.name = theme_name
        self.themes_dir = Path(themes_dir)
        self.theme_dir = self.themes_dir / theme_name

        # Validate theme directory exists
        if not self.theme_dir.exists():
            raise ThemeError(
                f"Theme '{theme_name}' not found. "
                f"Expected directory: {self.theme_dir}"
            )

        # Load configuration
        self.config_path = self.theme_dir / "theme.yaml"
        if not self.config_path.exists():
            raise ThemeError(
                f"Theme '{theme_name}' missing theme.yaml"
            )

        self.config = self._config_load()

        # CSS and assets paths
        self.css_path = self.theme_dir / "theme.css"
        self.assets_dir = self.theme_dir / "assets"

    def _config_load(self) -> Dict[str, Any]:
        """Load and parse theme.yaml"""
        try:
            with open(self.config_path, 'r') as f:
                config: Any = yaml.safe_load(f)
                if config is None:
                    config = {}
                return config
        except yaml.YAMLError as e:
            raise ThemeError(f"Failed to parse theme.yaml: {e}")
        except Exception as e:
            raise ThemeError(f"Failed to load theme.yaml: {e}")

    def css_has(self) -> bool:
        """Check if theme has custom CSS file"""
        return self.css_path.exists()

    def assets_has(self) -> bool:
        """Check if theme has assets directory"""
        return self.assets_dir.exists() and self.assets_dir.is_dir()

    def cssPath_get(self) -> Optional[Path]:
        """Get path to theme CSS file, or None if doesn't exist"""
        return self.css_path if self.css_has() else None

    def assetsDir_get(self) -> Optional[Path]:
        """Get path to theme assets directory, or None if doesn't exist"""
        return self.assets_dir if self.assets_has() else None

    def config_get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from theme.yaml.

        Supports nested keys with dot notation:
          theme.config_get('colors.background', '#fff')

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        keys: list[str] = key.split('.')
        value: Any = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def pygmentsStyle_get(self) -> str:
        """
        Get Pygments style name for syntax highlighting.

        Returns:
            Pygments style name (default: 'monokai')
        """
        return self.config_get('code.pygments_style', 'monokai')

    def __repr__(self) -> str:
        return f"Theme(name='{self.name}', path='{self.theme_dir}')"


def themes_listAvailable(themes_dir: str = "themes") -> list[str]:
    """
    List all available theme names.

    Args:
        themes_dir: Path to themes directory

    Returns:
        List of theme names (directory names with valid theme.yaml)
    """
    themes_path: Path = Path(themes_dir)

    if not themes_path.exists():
        return []

    themes: list[str] = []
    for item in themes_path.iterdir():
        if item.is_dir():
            # Check if it has a theme.yaml
            if (item / "theme.yaml").exists():
                themes.append(item.name)

    return sorted(themes)


def theme_validate(theme_name: str, themes_dir: str = "themes") -> tuple[bool, str]:
    """
    Validate a theme's structure and configuration.

    Args:
        theme_name: Name of theme to validate
        themes_dir: Path to themes directory

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        theme: Theme = Theme(theme_name, themes_dir)

        # Check for CSS file
        if not theme.css_has():
            return False, f"Warning: Theme '{theme_name}' has no theme.css file"

        # Basic config validation
        if not theme.config:
            return False, f"Theme '{theme_name}' has empty configuration"

        return True, f"Theme '{theme_name}' is valid"

    except ThemeError as e:
        return False, str(e)
