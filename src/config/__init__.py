"""
Configuration package for slidedown

Provides application settings via environment variables using pydantic-settings.
"""

from .settings import appsettings, AppSettings

__all__ = ["appsettings", "AppSettings"]
