"""
Configuration package for slidedown

Provides application settings via environment variables using
pydantic-settings.
"""

from .settings import AppSettings, appsettings

__all__ = ["appsettings", "AppSettings"]
