"""Progress emitter for resume-resume MCP tools.

Spawns a floating HUD window (NSPanel + WKWebView) and streams progress
events to it. The HUD is a long-lived subprocess that accepts JSON-lines
on stdin. Multiple MCP tools reuse the same HUD via a socket multiplexer.

The MCP server runs as a child of Claude Code in the user's GUI session,
so it has WindowServer access and can display native windows.

Usage:
    from .progress import progress

    @mcp.tool()
    def search_sessions(query: str) -> list[dict]:
        with progress(f"search: {query}") as p:
            p.update("Scanning sessions...", icon="search")
            p.result("Auth rewrite", "ciso | 3d ago", session_id="abc")
            p.update("Done", icon="done", highlight=True)
        return results
"""

import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

SOCKET_PATH = "/tmp/resume-hud.sock"
PID_PATH = Path("/tmp/resume-hud.pid")


class _ProgressChannel:
    """Emits events to a single channel in the HUD."""

    def __init__(self, channel: str, sock: socket.socket | None):
        self._ch = channel
        self._sock = sock

    def update(self, text: str, icon: str = "info", highlight: bool = False):
        self._send({"channel": self._ch, "text": text, "icon": icon, "highlight": highlight})

    def result(self, title: str, meta: str, session_id: str = ""):
        self._send({
            "channel": self._ch,
            "result": {"title": title, "meta": meta, "session_id": session_id},
        })

    def clear(self):
        self._send({"channel": self._ch, "clear": True})

    def _send(self, event: dict):
        if not self._sock:
            return
        try:
            self._sock.sendall(json.dumps(event).encode() + b"\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            self._sock = None


def _hud_alive() -> bool:
    """Check if HUD process is running."""
    if not PID_PATH.exists():
        return False
    try:
        pid = int(PID_PATH.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def _ensure_hud() -> bool:
    """Start HUD if not running. Returns True if available."""
    # Fast path: socket exists and we can connect — HUD is already running
    if Path(SOCKET_PATH).exists():
        test = _connect()
        if test is not None:
            test.close()
            return True
        # Socket exists but can't connect — stale, clean up
        Path(SOCKET_PATH).unlink(missing_ok=True)

    if _hud_alive():
        # Process alive but no socket yet — wait briefly
        for _ in range(10):
            if Path(SOCKET_PATH).exists():
                return True
            time.sleep(0.1)
        return False

    # Spawn HUD in socket mode as a fully detached process.
    # start_new_session=True + explicit double-fork ensures the HUD
    # survives MCP server restarts (it's not a child of this process).
    try:
        subprocess.Popen(
            [sys.executable, "-m", "resume_resume.hud", "--listen", SOCKET_PATH],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        for _ in range(20):  # 2s max
            if Path(SOCKET_PATH).exists():
                return True
            time.sleep(0.1)
    except OSError:
        pass
    return False


def _connect() -> socket.socket | None:
    """Connect to HUD socket."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCKET_PATH)
        return s
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        return None


@contextmanager
def progress(channel: str):
    """Context manager yielding a ProgressChannel connected to the HUD.

    Spawns the HUD if needed (inherits GUI from MCP server's session).
    Falls back to no-op if HUD can't start.
    """
    _ensure_hud()
    sock = _connect()
    ch = _ProgressChannel(channel, sock)
    try:
        yield ch
    finally:
        if sock:
            try:
                sock.close()
            except OSError:
                pass
