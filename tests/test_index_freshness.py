"""Regression for the index-freshness gap.

A session written ~90 minutes ago is older than the 30-min hot window, but if
it hasn't been appended to the daemon SessionIndex yet, it's also absent from
the cold FTS index. It used to fall into a gap and be invisible to keyword
search — this is exactly how the same-day "nevereatalone" codex session
disappeared.

search_sessions now supplements the live hot scan with a bounded filesystem
scan of fresh-but-unindexed sessions, so a same-day session is findable by
keyword without waiting for a background ingestion pass.
"""

from __future__ import annotations

import time

from resume_resume import mcp_server as ms


def test_fresh_unindexed_session_is_findable(tmp_path, monkeypatch):
    # A session written 90 minutes ago: past the 30-min hot window, but well
    # within the 6h freshness window. Crucially, NOT in the daemon index.
    mtime = time.time() - 90 * 60
    session_file = tmp_path / "rollout-fresh-nevereatalone.jsonl"
    session_file.write_text(
        '{"type":"message","role":"user","content":"let us talk about nevereatalone"}\n'
    )
    session_file.touch()
    import os as _os

    _os.utime(session_file, (mtime, mtime))

    fresh_session = {
        "session_id": "fresh-nevereatalone",
        "file": session_file,
        "project_dir": "/Users/test/repos/demo",
        "mtime": mtime,
        "size": session_file.stat().st_size,
    }

    # Hot scan (daemon index) does NOT know about this session — the gap.
    monkeypatch.setattr(ms, "_hot_sessions", lambda *a, **k: [])
    # Filesystem scan DOES discover it (as find_all_sessions does for codex).
    monkeypatch.setattr(ms, "_find_all_sessions_cached", lambda: [fresh_session])
    # Cold index has nothing for it.
    monkeypatch.setattr(ms, "search_cold_index", lambda *a, **k: [])

    result = ms.search_sessions.fn("nevereatalone", limit=10)

    ids = [item["id"] for item in result["items"]]
    assert "fresh-nevereatalone" in ids, result
    hit = next(i for i in result["items"] if i["id"] == "fresh-nevereatalone")
    assert hit["source"] == "hot-live"
    assert hit["hits"] >= 1


def test_fresh_sessions_respects_window_and_cap(tmp_path, monkeypatch):
    # Older than the freshness window -> excluded; fresh -> included.
    old = {
        "session_id": "too-old",
        "file": tmp_path / "a",
        "project_dir": "",
        "mtime": time.time() - ms._FRESH_WINDOW_SECONDS - 60,
        "size": 200,
    }
    new = {
        "session_id": "fresh",
        "file": tmp_path / "b",
        "project_dir": "",
        "mtime": time.time() - 60,
        "size": 200,
    }
    monkeypatch.setattr(ms, "_find_all_sessions_cached", lambda: [old, new])

    out = ms._fresh_sessions()
    ids = {s["session_id"] for s in out}
    assert "fresh" in ids
    assert "too-old" not in ids
