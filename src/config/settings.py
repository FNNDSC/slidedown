"""
Application settings and configuration

Uses pydantic-settings for type-safe configuration via environment variables.
All settings use SLIDEDOWN_ prefix (e.g., SLIDEDOWN_DEBUG_MODE=true).

Settings can also be loaded from a .env file in the project root.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application configuration via environment variables.

    Environment variables use SLIDEDOWN_ prefix.

    Examples:
        SLIDEDOWN_PLACEHOLDER_PREFIX=__CHILD_
        SLIDEDOWN_DEBUG_MODE=true
        SLIDEDOWN_DEFAULT_ASSETS_DIR=custom_assets
    """

    model_config = SettingsConfigDict(
        env_prefix="SLIDEDOWN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Parser configuration
    placeholder_prefix: str = Field(
        default="\x00CHILD_",
        description="Prefix for directive placeholders in content (uses null byte to avoid collisions)",
    )

    placeholder_suffix: str = Field(
        default="\x00",
        description="Suffix for directive placeholders in content (uses null byte to avoid collisions)",
    )

    # Compilation configuration
    debug_mode: bool = Field(
        default=False,
        description="Enable debug output during compilation",
    )

    validate_directives: bool = Field(
        default=True,
        description="Validate directive names against registry during parsing",
    )

    strict_mode: bool = Field(
        default=False,
        description="Strict mode: treat warnings as errors",
    )

    # Asset configuration
    default_assets_dir: str = Field(
        default="assets",
        description="Default assets directory name (relative to package or specified path)",
    )

    # Output configuration
    minify_output: bool = Field(
        default=False,
        description="Minify generated HTML output",
    )

    def placeHolder_make(self, index: int) -> str:
        """
        Generate a placeholder string for a child directive at given index.

        Args:
            index: Zero-based index of child directive

        Returns:
            Placeholder string (e.g., "\\x00CHILD_0\\x00")

        Example:
            >>> settings = AppSettings()
            >>> settings.placeHolder_make(0)
            '\\x00CHILD_0\\x00'
        """
        return f"{self.placeholder_prefix}{index}{self.placeholder_suffix}"

    def childIndex_extract(self, placeholder: str) -> int | None:
        """
        Extract child index from a placeholder string.

        Args:
            placeholder: Placeholder string to parse

        Returns:
            Child index if valid placeholder, None otherwise

        Example:
            >>> settings = AppSettings()
            >>> settings.childIndex_extract('\\x00CHILD_0\\x00')
            0
        """
        if not placeholder.startswith(self.placeholder_prefix):
            return None
        if not placeholder.endswith(self.placeholder_suffix):
            return None

        # Extract the middle part
        content = placeholder[len(self.placeholder_prefix) : -len(self.placeholder_suffix)]

        try:
            return int(content)
        except ValueError:
            return None


# Singleton instance - import this in your code
appsettings = AppSettings()
