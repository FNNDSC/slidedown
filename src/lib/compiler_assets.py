"""Asset and template helpers for the slidedown compiler."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from ..models.compiler import ThemeLike
from .log import LOG


class CompilerAssets(Protocol):
    """Compiler attributes required by asset helpers."""

    assets_dir: Path
    output_dir: Path
    theme: ThemeLike


def template_load(compiler: CompilerAssets, filename: str) -> str:
    """Load an HTML template file from the active assets directory."""
    template_path = compiler.assets_dir / "html" / filename
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    LOG(f"Warning: Template {filename} not found", level=2)
    return ""


def assets_copy(compiler: CompilerAssets) -> None:
    """Copy CSS, JavaScript, image, logo, and theme assets."""
    for asset_dir in ["css", "js", "images", "logos"]:
        src = compiler.assets_dir / asset_dir
        dst = compiler.output_dir / asset_dir

        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            LOG(f"Copied {asset_dir}/ to output", level=3)

    theme_css_path = compiler.theme.cssPath_get()
    if theme_css_path and theme_css_path.exists():
        dst_css = compiler.output_dir / "css" / "theme.css"
        dst_css.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(theme_css_path, dst_css)
        LOG(f"Copied theme CSS: {compiler.theme.name}", level=2)

    theme_assets_dir = compiler.theme.assetsDir_get()
    if theme_assets_dir and theme_assets_dir.exists():
        dst_theme_assets = compiler.output_dir / "theme-assets"
        shutil.copytree(theme_assets_dir, dst_theme_assets, dirs_exist_ok=True)
        LOG(f"Copied theme assets: {theme_assets_dir}", level=3)

    if compiler.theme.lcars_is():
        lcars_scripts_path = compiler.theme.templatePath_get(
            "lcars-scripts.js"
        )
        if lcars_scripts_path.exists():
            dst_js = compiler.output_dir / "js" / "lcars-scripts.js"
            dst_js.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(lcars_scripts_path, dst_js)
            LOG("Copied LCARS scripts from templates/", level=3)
