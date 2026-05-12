"""Asset and template helpers for the slidedown compiler."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Protocol

from ..models.compiler import ThemeLike
from .log import LOG

# Maps output-relative asset path → source Path for standalone inlining.
AssetSourceMap: dict[str, Path] = {}


class CompilerAssets(Protocol):
    """Compiler attributes required by asset helpers."""

    assets_dir: Path
    output_dir: Path
    standalone: bool
    theme: ThemeLike


def template_load(compiler: CompilerAssets, filename: str) -> str:
    """Load an HTML template file from the active assets directory.

    Args:
        compiler: Active compiler instance.
        filename: Template filename inside the ``html/`` subdirectory.

    Returns:
        Template file contents, or empty string if not found.
    """
    template_path = compiler.assets_dir / "html" / filename
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    LOG(f"Warning: Template {filename} not found", level=2)
    return ""


def assets_copy(compiler: CompilerAssets) -> None:
    """Copy CSS, JavaScript, image, logo, and theme assets to output.

    Args:
        compiler: Active compiler instance.
    """
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
        for script_name in [
            "lcars-scripts.js",
            "slidedown-lcars-cascade.js",
        ]:
            lcars_scripts_path = compiler.theme.templatePath_get(script_name)
            if lcars_scripts_path.exists():
                dst_js = compiler.output_dir / "js" / script_name
                dst_js.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(lcars_scripts_path, dst_js)
                LOG(f"Copied LCARS script: {script_name}", level=3)


def assets_sourceMap_build(compiler: CompilerAssets) -> dict[str, Path]:
    """Build a map of output-relative asset paths to their source locations.

    Used by ``html_inline()`` to resolve which local assets to embed.
    External CDN references (``http://``, ``https://``) are not included —
    they remain as live links in the standalone output.

    Args:
        compiler: Active compiler instance.

    Returns:
        Dict mapping output-relative path (e.g. ``"css/slidedown.css"``)
        to absolute source ``Path``.
    """
    source_map: dict[str, Path] = {}

    # Core slidedown CSS and JS
    for css_file in (compiler.assets_dir / "css").glob("*.css"):
        source_map[f"css/{css_file.name}"] = css_file
    for js_file in (compiler.assets_dir / "js").glob("*.js"):
        source_map[f"js/{js_file.name}"] = js_file

    # Theme CSS (copied to css/theme.css at build time)
    theme_css = compiler.theme.cssPath_get()
    if theme_css and theme_css.exists():
        source_map["css/theme.css"] = theme_css

    # LCARS-specific scripts
    if compiler.theme.lcars_is():
        for script_name in [
            "lcars-scripts.js",
            "slidedown-lcars-cascade.js",
        ]:
            script_path = compiler.theme.templatePath_get(script_name)
            if script_path.exists():
                source_map[f"js/{script_name}"] = script_path

    return source_map


def html_inline(html: str, source_map: dict[str, Path]) -> str:
    """Replace local asset references with inline ``<style>`` and ``<script>``.

    Scans the assembled HTML for ``<link rel="stylesheet">`` and
    ``<script src="…">`` tags that reference paths present in
    ``source_map``.  Matching tags are replaced with the file content
    inlined directly into the document.  CDN references (``http://``,
    ``https://``) are left untouched.

    Args:
        html: Fully assembled HTML string to post-process.
        source_map: Mapping from output-relative path to source ``Path``,
            as returned by ``assets_sourceMap_build()``.

    Returns:
        HTML string with local assets inlined.
    """

    def _css_inline(match: re.Match[str]) -> str:
        href = match.group(1)
        if href in source_map:
            css = source_map[href].read_text(encoding="utf-8")
            LOG(f"[standalone] Inlining CSS: {href}", level=2)
            return f"<style>\n{css}\n</style>"
        return match.group(0)  # CDN or unknown — keep as-is

    def _js_inline(match: re.Match[str]) -> str:
        src = match.group(1)
        if src in source_map:
            js = source_map[src].read_text(encoding="utf-8")
            LOG(f"[standalone] Inlining JS: {src}", level=2)
            return f"<script>\n{js}\n</script>"
        return match.group(0)  # CDN or unknown — keep as-is

    # Match <link rel="stylesheet" href="..."> in either attribute order
    html = re.sub(
        r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*\bhref=["\']([^"\']+)["\'][^>]*/?>',
        _css_inline,
        html,
    )
    html = re.sub(
        r'<link\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*\brel=["\']stylesheet["\'][^>]*/?>',
        _css_inline,
        html,
    )

    # Match <script src="..."></script>
    html = re.sub(
        r'<script\b[^>]*\bsrc=["\']([^"\']+)["\'][^>]*></script>',
        _js_inline,
        html,
    )

    return html
