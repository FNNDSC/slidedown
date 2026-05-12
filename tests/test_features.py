"""Tests for live-reload (--watch) and multi-file include (.include{}) features."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from slidedown.lib.compiler import Compiler
from slidedown.lib.parser import Parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile(source: str, tmpdir: str, watch: bool = False) -> str:
    """Compile source string to HTML and return the result."""
    parser = Parser(source, debug=False)
    ast = parser.parse()
    assets_dir = Path(__file__).parent.parent / "assets"
    compiler = Compiler(
        ast=ast,
        output_dir=tmpdir,
        assets_dir=str(assets_dir),
        verbosity=0,
        protected_code_blocks=parser.protected_code_blocks,
        escaped_sequences=parser.escaped_sequences,
        theme_name="default",
        input_dir=tmpdir,
        watch=watch,
    )
    compiler.compile()
    return (Path(tmpdir) / "index.html").read_text()


# ---------------------------------------------------------------------------
# Watch mode — SSE script injection
# ---------------------------------------------------------------------------

class TestWatchSSEInjection:
    """SSE live-reload script is injected iff watch=True."""

    def test_sse_script_present_in_watch_mode(self) -> None:
        source = ".slide{\n  .title{Hello}\n  .body{World}\n}"
        with tempfile.TemporaryDirectory() as tmpdir:
            html = _compile(source, tmpdir, watch=True)
        assert "EventSource" in html
        assert "/events" in html

    def test_sse_script_absent_in_normal_mode(self) -> None:
        source = ".slide{\n  .title{Hello}\n  .body{World}\n}"
        with tempfile.TemporaryDirectory() as tmpdir:
            html = _compile(source, tmpdir, watch=False)
        assert "EventSource" not in html

    def test_sse_script_fires_reload_event(self) -> None:
        """The injected script listens for the 'reload' event specifically."""
        source = ".slide{\n  .title{A}\n  .body{B}\n}"
        with tempfile.TemporaryDirectory() as tmpdir:
            html = _compile(source, tmpdir, watch=True)
        assert "event: reload" in html or "reload" in html
        assert "location.reload" in html


# ---------------------------------------------------------------------------
# .include{} directive
# ---------------------------------------------------------------------------

class TestIncludeDirective:
    """Multi-file include via .include{}."""

    def test_include_basic(self) -> None:
        """Included file's slides appear in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a child file
            child = Path(tmpdir) / "child.sd"
            child.write_text(
                ".slide{\n  .title{Included}\n  .body{From child file}\n}\n"
            )
            # Parent references it
            parent_source = (
                ".slide{\n  .title{Parent}\n  .body{First slide}\n}\n"
                f".include{{child.sd}}\n"
            )
            html = _compile(parent_source, tmpdir)
        assert "From child file" in html
        assert "First slide" in html

    def test_include_slide_count_continues(self) -> None:
        """Slide counter continues across the include boundary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            child = Path(tmpdir) / "extra.sd"
            child.write_text(
                ".slide{\n  .title{S2}\n  .body{second}\n}\n"
                ".slide{\n  .title{S3}\n  .body{third}\n}\n"
            )
            parent_source = (
                ".slide{\n  .title{S1}\n  .body{first}\n}\n"
                ".include{extra.sd}\n"
            )
            parser = Parser(parent_source, debug=False)
            ast = parser.parse()
            assets_dir = Path(__file__).parent.parent / "assets"
            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0,
                protected_code_blocks=parser.protected_code_blocks,
                escaped_sequences=parser.escaped_sequences,
                theme_name="default",
                input_dir=tmpdir,
            )
            result = compiler.compile()
        assert result["slide_count"] == 3

    def test_include_strips_meta(self) -> None:
        """Top-level .meta{} in included file does not override parent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            child = Path(tmpdir) / "child_meta.sd"
            child.write_text(
                ".meta{\n  title: \"Child Title\"\n}\n"
                ".slide{\n  .title{Child}\n  .body{body}\n}\n"
            )
            parent_source = (
                ".meta{\n  title: \"Parent Title\"\n}\n"
                ".slide{\n  .title{Parent}\n  .body{p}\n}\n"
                ".include{child_meta.sd}\n"
            )
            parser = Parser(parent_source, debug=False)
            ast = parser.parse()
            assets_dir = Path(__file__).parent.parent / "assets"
            compiler = Compiler(
                ast=ast,
                output_dir=tmpdir,
                assets_dir=str(assets_dir),
                verbosity=0,
                protected_code_blocks=parser.protected_code_blocks,
                escaped_sequences=parser.escaped_sequences,
                theme_name="default",
                input_dir=tmpdir,
            )
            compiler.compile()
            # meta_config should have parent's title, not child's
            assert compiler.meta_config.get("title") == "Parent Title"

    def test_include_file_not_found(self) -> None:
        """Missing included file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = ".include{nonexistent.sd}\n"
            with pytest.raises(FileNotFoundError, match="nonexistent.sd"):
                _compile(source, tmpdir)

    def test_include_circular_raises(self) -> None:
        """Circular include raises RecursionError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # a.sd includes b.sd, b.sd includes a.sd
            a = Path(tmpdir) / "a.sd"
            b = Path(tmpdir) / "b.sd"
            a.write_text(".include{b.sd}\n")
            b.write_text(".include{a.sd}\n")

            source = ".include{a.sd}\n"
            with pytest.raises(RecursionError):
                _compile(source, tmpdir)

    def test_include_empty_path_returns_empty(self) -> None:
        """Empty .include{} path produces no output and does not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = (
                ".slide{\n  .title{A}\n  .body{B}\n}\n"
                ".include{}\n"
            )
            html = _compile(source, tmpdir)
        assert "A" in html  # parent slide still renders
