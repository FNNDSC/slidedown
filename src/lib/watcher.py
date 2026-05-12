"""Live-reload watcher and HTTP server for --watch mode.

Provides a lightweight SSE-based live reload server that watches the source
.sd file for changes, recompiles on change, and signals connected browsers
to reload.

Usage (from __main__.py after initial compile):

    from .lib.watcher import watcher_serve
    watcher_serve(state)
"""

from __future__ import annotations

import posixpath
import socketserver
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.state import ProgramState

# MIME types for static file serving
_MIME: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
}

# SSE long-poll window: close and let EventSource reconnect after this many
# seconds of no change (keeps connections from piling up).
_SSE_TIMEOUT = 30.0
_POLL_INTERVAL = 0.2


class SSEBroadcaster:
    """Thread-safe generation counter polled by SSE handler threads.

    Each call to notify() increments the generation. SSE handlers compare
    the generation they saw on connection to the current value; when they
    differ they send a reload event and close.
    """

    def __init__(self) -> None:
        self._generation: int = 0
        self._lock: threading.Lock = threading.Lock()

    def notify(self) -> None:
        """Signal all waiting SSE clients to reload."""
        with self._lock:
            self._generation += 1

    def generation_current(self) -> int:
        """Return the current generation counter."""
        with self._lock:
            return self._generation


class _ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """HTTP server with one thread per connection.

    Required so that SSE long-poll connections don't block static file
    requests from the same browser.
    """

    daemon_threads = True


class SlidedownHTTPHandler(BaseHTTPRequestHandler):
    """Serve static files from output_dir and SSE events at /events.

    Class attributes are set by watcher_serve() before the server starts.
    Using class attributes (rather than instance or closure) avoids the need
    for a handler factory and keeps the code straightforward.
    """

    broadcaster: SSEBroadcaster
    output_dir: Path

    def do_GET(self) -> None:
        """Route GET requests to the SSE or static file handler."""
        if self.path == "/events" or self.path.startswith("/events?"):
            self.sse_handle()
        else:
            self.static_handle()

    def sse_handle(self) -> None:
        """Long-poll SSE endpoint. Sends one reload event then closes."""
        seen = self.broadcaster.generation_current()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            deadline = time.monotonic() + _SSE_TIMEOUT
            while time.monotonic() < deadline:
                current = self.broadcaster.generation_current()
                if current != seen:
                    self.wfile.write(b"event: reload\ndata: \n\n")
                    self.wfile.flush()
                    return
                time.sleep(_POLL_INTERVAL)

            # Timeout: send a keepalive comment so EventSource doesn't error
            self.wfile.write(b": keepalive\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def static_handle(self) -> None:
        """Serve a static file from output_dir."""
        raw_path = urllib.parse.unquote(self.path.split("?", 1)[0])
        clean = posixpath.normpath(raw_path).lstrip("/")
        full = self.output_dir / clean

        if full.is_dir():
            full = full / "index.html"

        if not full.exists():
            self.send_error(404, f"Not found: {clean}")
            return

        data = full.read_bytes()
        content_type = _MIME.get(
            full.suffix.lower(), "application/octet-stream"
        )
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        pass  # Suppress per-request noise; watcher prints its own messages


def port_findFree(start: int) -> int:
    """Return start if free, else the next free port above it.

    Args:
        start: Port number to try first.

    Returns:
        First available port number >= start.
    """
    import socket

    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("", port))
                return port
            except OSError:
                port += 1


def watcher_serve(state: ProgramState) -> None:
    """Start HTTP server and watch source file; block until Ctrl-C.

    Recompiles the deck on every detected change to the source .sd file
    and signals connected browsers to reload via SSE.

    Args:
        state: Final ProgramState after initial compilation. Must have
            inputSourceFile, htmlOutputdir, assetsInputdir, themeName,
            inputdir, port, and verbosity set.
    """
    from ..lib.compiler import Compiler
    from ..lib.parser import Parser

    broadcaster = SSEBroadcaster()
    output_dir = state.htmlOutputdir
    source_file = state.inputSourceFile

    SlidedownHTTPHandler.broadcaster = broadcaster
    SlidedownHTTPHandler.output_dir = output_dir

    port = port_findFree(state.port)
    if port != state.port:
        print(f"[watch] Port {state.port} in use, using {port} instead.")

    server = _ThreadedHTTPServer(("", port), SlidedownHTTPHandler)
    server_thread = threading.Thread(
        target=server.serve_forever, daemon=True
    )
    server_thread.start()

    print(f"[watch] Serving on http://localhost:{port}/")
    print(f"[watch] Watching {source_file.name} for changes.")
    print("[watch] Press Ctrl-C to stop.\n")

    last_mtime: float = source_file.stat().st_mtime

    try:
        while True:
            time.sleep(0.5)
            try:
                current_mtime = source_file.stat().st_mtime
            except OSError:
                continue

            if current_mtime == last_mtime:
                continue

            last_mtime = current_mtime
            print(
                f"[watch] Change detected — recompiling "
                f"{source_file.name}..."
            )

            try:
                source = source_file.read_text(encoding="utf-8")
                parser = Parser(source, debug=(state.verbosity >= 3))
                ast = parser.parse()
                compiler = Compiler(
                    ast=ast,
                    output_dir=str(output_dir),
                    assets_dir=str(state.assetsInputdir),
                    verbosity=state.verbosity,
                    protected_code_blocks=parser.protected_code_blocks,
                    escaped_sequences=parser.escaped_sequences,
                    theme_name=state.themeName,
                    input_dir=str(state.inputdir),
                    watch=True,
                )
                result = compiler.compile()
                broadcaster.notify()
                print(
                    f"[watch] OK — {result['slide_count']} slides, "
                    "browser reloading."
                )
            except Exception as exc:
                print(f"[watch] Recompile error: {exc}")

    except KeyboardInterrupt:
        print("\n[watch] Stopping.")
        server.shutdown()
