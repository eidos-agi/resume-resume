"""Local web UI for resume-resume.

Serves the static site plus tiny JSON APIs backed by the same local index/card
code as the MCP. No external network, no framework, no Claude Code wait.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from claude_session_commons import decode_project_path
from claude_session_commons.session_index import SessionIndex

from .resume_card import build_card
from .sessions import shorten_path
from .search_index import (
    HOT_WINDOW_SECONDS,
    count_matches,
    recent_candidates,
    refresh_budget,
    search,
    status,
)

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"
NOISE_TITLE_PREFIXES = (
    "session metadata",
    "session summary",
    "session status",
    "summarize what",
)
_HOT_CACHE: dict = {"data": None, "ts": 0.0}
_HOT_CACHE_TTL = 5.0


def _indexed_hot_sessions(window_seconds: int = HOT_WINDOW_SECONDS) -> list[dict]:
    now = time.time()
    cached = _HOT_CACHE["data"]
    if cached is not None and now - _HOT_CACHE["ts"] < _HOT_CACHE_TTL:
        return cached

    cutoff = now - window_seconds
    sessions: list[dict] = []
    try:
        known = SessionIndex.get_default().get_all()
    except Exception:
        known = {}

    for sid, meta in known.items():
        try:
            mtime = float(meta.get("mtime") or 0.0)
            size = int(meta.get("size") or 0)
            if mtime < cutoff or size < 100:
                continue
            sessions.append(
                {
                    "session_id": sid,
                    "file": Path(meta["file_path"]),
                    "project_dir": meta.get("project_dir")
                    or decode_project_path(Path(meta["file_path"]).parent.name),
                    "mtime": mtime,
                    "size": size,
                }
            )
        except Exception:
            continue

    sessions.sort(key=lambda item: item["mtime"], reverse=True)
    _HOT_CACHE["data"] = sessions
    _HOT_CACHE["ts"] = now
    return sessions


def _query_terms(query: str) -> list[bytes]:
    phrases = re.findall(r'"([^"]+)"', query)
    remaining = re.sub(r'"[^"]*"', "", query).strip()
    words = [w for w in remaining.lower().split() if w]
    terms = [*phrases, *words]
    return [
        term.lower().encode("utf-8", errors="replace") for term in terms if term.strip()
    ]


def _read_session_bytes(session: dict, chunk_size: int = 1024 * 1024) -> bytes | None:
    try:
        path = session["file"]
        if session["size"] < chunk_size:
            return path.read_bytes().lower()
        parts = []
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                parts.append(chunk)
        return b"".join(parts).lower()
    except OSError:
        return None


def _snippet(raw: bytes, term: bytes, context_chars: int = 80) -> str:
    idx = raw.find(term)
    if idx < 0:
        return ""
    start = max(0, idx - context_chars)
    end = min(len(raw), idx + len(term) + context_chars)
    text = raw[start:end].decode("utf-8", errors="replace")
    text = text.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"')
    text = re.sub(r'["\{\}\[\]\\]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if start > 0:
        text = "..." + text
    if end < len(raw):
        text += "..."
    return text


def _hot_search(
    query: str, limit: int, cutoff_after: float, project: str
) -> tuple[list[dict], int]:
    terms = _query_terms(query)
    if not terms:
        return [], 0

    sessions = _indexed_hot_sessions()
    if cutoff_after:
        sessions = [s for s in sessions if s["mtime"] >= cutoff_after]
    if project:
        project_lower = project.lower()
        sessions = [
            s for s in sessions if project_lower in s.get("project_dir", "").lower()
        ]

    def check(session: dict) -> dict | None:
        raw = _read_session_bytes(session)
        if raw is None:
            return None
        counts = []
        for term in terms:
            count = raw.count(term)
            if count == 0:
                return None
            counts.append(count)
        rarest = terms[counts.index(min(counts))]
        title = session["file"].stem
        return {
            "id": session["session_id"],
            "title": title,
            "project": shorten_path(session.get("project_dir") or ""),
            "date": session["mtime"],
            "score": round(
                100.0 * math.exp(-0.0002 * max(time.time() - session["mtime"], 0)), 1
            ),
            "state": _snippet(raw, rarest),
            "hits": sum(counts),
            "source": "hot-live",
        }

    matches = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(sessions)))) as pool:
        futures = [pool.submit(check, session) for session in sessions]
        for future in as_completed(futures):
            item = future.result()
            if item:
                matches.append(item)
    matches.sort(key=lambda item: (item["hits"], item["date"]), reverse=True)
    return matches[:limit], len(matches)


def _json(
    handler: BaseHTTPRequestHandler, payload: dict, status_code: int = 200
) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _search_result(query: str, limit: int, hours: int, project: str, mode: str) -> dict:
    cutoff_after = 0.0
    if hours > 0:
        cutoff_after = time.time() - hours * 3600
    hot_cutoff = time.time() - HOT_WINDOW_SECONDS

    if mode == "cold":
        hot_items, hot_total = [], 0
    else:
        hot_items, hot_total = _hot_search(query, limit, cutoff_after, project)
    remaining = max(limit - len(hot_items), 0)
    if not remaining or mode == "hot":
        return {
            "items": hot_items,
            "total": hot_total,
            "hot_total": hot_total,
            "cold_total": 0,
        }

    cold_total = count_matches(
        query,
        cutoff_after=cutoff_after,
        cutoff_before=hot_cutoff,
        project=project,
        excluded_title_prefixes=NOISE_TITLE_PREFIXES,
    )

    rows = search(
        query,
        limit=min(remaining * 4, 200),
        cutoff_after=cutoff_after,
        cutoff_before=hot_cutoff,
        project=project,
    )
    items = []
    for row in rows:
        title = row.get("title") or "Untitled session"
        if title.lower().startswith(NOISE_TITLE_PREFIXES):
            continue
        items.append(
            {
                "id": row["session_id"],
                "title": title,
                "project": row.get("project_dir") or "",
                "date": row.get("mtime"),
                "score": abs(float(row.get("rank") or 0.0)),
                "state": row.get("state") or "",
                "source": "cold-index",
            }
        )
        if len(items) >= remaining:
            break
    return {
        "items": hot_items + items,
        "total": hot_total + cold_total,
        "hot_total": hot_total,
        "cold_total": cold_total,
    }


def _recent_result(limit: int, hours: int, project: str, mode: str) -> dict:
    cutoff_after = 0.0
    if hours > 0:
        cutoff_after = time.time() - hours * 3600

    hot_items = []
    if mode != "cold":
        for session in _indexed_hot_sessions():
            if cutoff_after and session["mtime"] < cutoff_after:
                continue
            if (
                project
                and project.lower() not in session.get("project_dir", "").lower()
            ):
                continue
            hot_items.append(
                {
                    "id": session["session_id"],
                    "title": session["file"].stem,
                    "project": shorten_path(session.get("project_dir") or ""),
                    "date": session["mtime"],
                    "score": 0,
                    "state": "Touched in the live hot window.",
                    "source": "hot-live",
                }
            )
            if len(hot_items) >= limit:
                return {
                    "items": hot_items,
                    "total": len(hot_items),
                    "hot_total": len(hot_items),
                    "cold_total": 0,
                }
    if mode == "hot":
        return {
            "items": hot_items,
            "total": len(hot_items),
            "hot_total": len(hot_items),
            "cold_total": 0,
        }

    cold_cutoff = time.time() - HOT_WINDOW_SECONDS
    rows = recent_candidates(
        limit=min((limit - len(hot_items)) * 4, 200),
        cutoff_after=cutoff_after,
    )
    cold_items = []
    for row in rows:
        if row["mtime"] >= cold_cutoff:
            continue
        if project and project.lower() not in (row.get("project_dir") or "").lower():
            continue
        title = row.get("title") or "Untitled session"
        if title.lower().startswith(NOISE_TITLE_PREFIXES):
            continue
        cold_items.append(
            {
                "id": row["session_id"],
                "title": title,
                "project": shorten_path(row.get("project_dir") or ""),
                "date": row["mtime"],
                "score": float(row.get("score") or 0.0),
                "state": row.get("state") or "",
                "source": "cold-index",
            }
        )
        if len(cold_items) + len(hot_items) >= limit:
            break
    # For the unqueried landing state, total is the visible, bounded recent set.
    # Counting every cold row would make "recent work" read like a global index.
    return {
        "items": hot_items + cold_items,
        "total": len(hot_items) + len(cold_items),
        "hot_total": len(hot_items),
        "cold_total": len(cold_items),
    }


def _static_target(path: str) -> Path:
    if path in ("", "/"):
        rel = "index.html"
    elif path.startswith("/assets/"):
        rel = ".." + path
    else:
        rel = path.lstrip("/")
    return (SITE_DIR / rel).resolve()


def _is_allowed_static(target: Path) -> bool:
    allowed_roots = (SITE_DIR.resolve(), (ROOT / "assets").resolve())
    return any(str(target).startswith(str(root)) for root in allowed_roots)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        target = _static_target(parsed.path)
        if not _is_allowed_static(target):
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/search":
            qs = parse_qs(parsed.query)
            query = (qs.get("q") or [""])[0].strip()
            limit = max(1, min(int((qs.get("limit") or ["20"])[0]), 50))
            hours = max(0, int((qs.get("hours") or ["0"])[0]))
            project = (qs.get("project") or [""])[0].strip()
            mode = (qs.get("mode") or ["all"])[0].strip().lower()
            if mode not in {"all", "hot", "cold"}:
                mode = "all"
            if not query:
                result = _recent_result(limit, hours, project, mode)
                index = status()
                _json(
                    self,
                    {
                        **result,
                        "count": len(result["items"]),
                        "view": "recent",
                        "hot_window_minutes": int(HOT_WINDOW_SECONDS / 60),
                        "index": index,
                    },
                )
                return
            result = _search_result(query, limit, hours, project, mode)
            _json(
                self,
                {
                    **result,
                    "count": len(result["items"]),
                    "view": "search",
                    "hot_window_minutes": int(HOT_WINDOW_SECONDS / 60),
                    "index": status(),
                },
            )
            return

        if path == "/api/index/refresh":
            result = refresh_budget(max_files=300, max_seconds=0.35)
            _json(self, {**result, "index": status()})
            return

        if path == "/api/card":
            qs = parse_qs(parsed.query)
            session_id = (qs.get("session") or [""])[0].strip() or None
            card = build_card(session_id=session_id, hours=1.0)
            _json(self, card, 404 if "error" in card else 200)
            return

        if path == "/api/status":
            _json(
                self,
                {
                    "index": status(),
                    "hot_window_minutes": int(HOT_WINDOW_SECONDS / 60),
                    "hot_sessions": len(_indexed_hot_sessions()),
                },
            )
            return

        self._serve_static(path)

    def _serve_static(self, path: str) -> None:
        target = _static_target(path)
        if not _is_allowed_static(target):
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return

        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the resume-resume local web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"resume-resume site: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
