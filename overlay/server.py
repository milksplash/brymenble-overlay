"""Tiny stdlib-only HTTP server for the overlay.

Serves the static web/ payload and the current render state at /state.json.
The OBS Browser Source polls /state.json — no WebSocket is needed at this
frame rate (the meter streams at a few Hz).
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".woff2": "font/woff2",
}

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"


class StateHolder:
    """Thread-safe holder for the latest render state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = {"connected": False, "mode": "idle"}

    def set(self, state: dict) -> None:
        with self._lock:
            self._state = state

    def get(self) -> dict:
        with self._lock:
            return self._state


class OverlayHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, holder: StateHolder, web_root: Path = WEB_ROOT):
        self.state_holder = holder
        self.web_root = Path(web_root)
        super().__init__(address, OverlayHandler)


class OverlayHandler(BaseHTTPRequestHandler):
    server_version = "BM78xOverlay/1.0"

    def do_GET(self):
        try:
            self._route(self.path)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _route(self, path):
        path = path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_file(self.server.web_root / "index.html")
        elif path == "/state.json":
            self._send_json(self.server.state_holder.get())
        else:
            self._send_file(self.server.web_root / path.lstrip("/"))

    def _send_file(self, path: Path):
        try:
            target = path.resolve()
            root = self.server.web_root.resolve()
            if target != root and root not in target.parents:
                self.send_error(403, "Forbidden")
                return
            data = target.read_bytes()
        except (OSError, ValueError):
            self.send_error(404, "Not found")
            return
        self.send_response(200)
        self.send_header(
            "Content-Type",
            MIME_TYPES.get(target.suffix.lower(), "application/octet-stream"),
        )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # keep the console quiet


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """Start the overlay server in a background thread.

    Returns (server, holder). Shut down with server.shutdown().
    """
    holder = StateHolder()
    httpd = OverlayHTTPServer((host, port), holder)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, holder
