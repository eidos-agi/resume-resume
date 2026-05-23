"""Fast resume card CLI.

This is intentionally separate from the MCP server lifecycle. A running MCP can
shell out to ``python -m resume_resume.resume_card`` or ``cr card`` and get a
small JSON payload / HUD event stream without waiting on Claude Code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_session_commons import decode_project_path

from .sessions import PROJECTS_DIR, SessionCache, relative_time, shorten_path
from .search_index import recent_candidates

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)

_NOISE_TITLE_PREFIXES = (
    "summarize what",
    "session summary",
    "session status check",
    "summary request",
    "session meta",
    "session metadata",
    "session with no",
    "session idle",
    "session start with unclear",
    "activity check",
    "no activity",
    "no development",
    "classify this claude",
    "session activity",
    "session resume check",
    "session rate limited",
    "session summarization",
    "check recent claude",
    "recent claude",
)


def _indexed_sessions() -> list[dict[str, Any]]:
    try:
        from claude_session_commons.session_index import SessionIndex

        known = SessionIndex.get_default().get_all()
    except Exception:
        known = {}

    sessions = []
    for sid, meta in known.items():
        try:
            sessions.append({
                "session_id": sid,
                "file": Path(meta["file_path"]),
                "project_dir": meta.get("project_dir") or "",
                "mtime": float(meta.get("mtime") or 0.0),
                "size": int(meta.get("size") or 0),
                "last_entry_type": meta.get("last_entry_type"),
            })
        except Exception:
            continue
    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def _session_from_cold_row(row: dict[str, Any]) -> dict[str, Any]:
    sid = row["session_id"]
    path = Path(str(row.get("summary_path") or ""))
    # summary_path points at ~/.claude/resume-summaries; derive JSONL via slow
    # fallback only after choosing a small candidate row.
    jsonl_matches = list(PROJECTS_DIR.glob(f"*/{sid}.jsonl"))
    file_path = jsonl_matches[0] if jsonl_matches else path
    return {
        "session_id": sid,
        "file": file_path,
        "project_dir": row.get("project_dir") or "",
        "mtime": float(row.get("mtime") or 0.0),
        "size": file_path.stat().st_size if file_path.exists() else 0,
        "last_entry_type": None,
        "_summary": json.loads(row["summary_json"]) if row.get("summary_json") else {},
    }


def _is_noise_candidate(session: dict[str, Any]) -> bool:
    summary = _cached_summary(session)
    title = str(summary.get("title") or "").strip().lower()
    if any(title.startswith(prefix) for prefix in _NOISE_TITLE_PREFIXES):
        return True
    haystack = " ".join(
        str(summary.get(k) or "").lower()
        for k in ("title", "goal", "objective", "what_was_done", "progress", "state")
    )
    if "summarize what was happening in a claude code session" in haystack:
        return True
    if "no activity" in haystack and "tool" not in haystack and "file" not in haystack:
        return True
    return False


def _find_session(session_id: str | None, hours: float, *, include_noise: bool = False) -> dict[str, Any] | None:
    if session_id:
        sessions = _indexed_sessions()
        for s in sessions:
            if s["session_id"] == session_id:
                return s
        matches = list(PROJECTS_DIR.glob(f"*/{session_id}.jsonl"))
        if matches:
            path = matches[0]
            return {
                "session_id": session_id,
                "file": path,
                "project_dir": decode_project_path(path.parent.name),
                "mtime": path.stat().st_mtime,
                "size": path.stat().st_size,
                "last_entry_type": None,
            }
        return None

    cutoff = time.time() - hours * 3600
    for row in recent_candidates(limit=100, cutoff_after=cutoff):
        s = _session_from_cold_row(row)
        if s["file"].exists() and (include_noise or not _is_noise_candidate(s)):
            return s
    for row in recent_candidates(limit=200):
        s = _session_from_cold_row(row)
        if s["file"].exists() and (include_noise or not _is_noise_candidate(s)):
            return s

    sessions = _indexed_sessions()
    for s in sessions:
        if s["mtime"] >= cutoff and s["file"].exists() and (include_noise or not _is_noise_candidate(s)):
            return s
    if include_noise:
        return sessions[0] if sessions else None
    for s in sessions[:200]:
        if s["file"].exists() and not _is_noise_candidate(s):
            return s
    return sessions[0] if sessions else None


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(p for p in parts if p)
    return ""


def _tail_entries(path: Path, read_bytes: int = 192 * 1024) -> list[dict[str, Any]]:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - read_bytes))
            raw = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    entries = []
    for line in raw.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def _cached_summary(session: dict[str, Any]) -> dict[str, Any]:
    if isinstance(session.get("_summary"), dict):
        return session["_summary"]
    cache = SessionCache()
    sid = session["session_id"]
    try:
        ck = cache.cache_key(session["file"])
        cached = cache.get(sid, ck, "summary")
        if isinstance(cached, dict):
            return cached
    except Exception:
        pass
    try:
        data = cache._read(sid)
        summary = data.get("summary")
        return summary if isinstance(summary, dict) else {}
    except Exception:
        return {}


def _git_dirty(project_dir: str) -> dict[str, Any]:
    if not project_dir or not Path(project_dir).is_dir():
        return {"dirty": False, "files": []}
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return {"dirty": False, "files": []}
    files = [line[3:] for line in result.stdout.splitlines() if len(line) > 3]
    return {"dirty": bool(files), "files": files[:8], "count": len(files)}


def _local_t5_summary(text: str) -> str:
    try:
        from claude_session_commons.summarizer import inference

        cache_dir = inference.CACHE_DIR
        required = [cache_dir / name for name in inference.REQUIRED_FILES]
        if not all(p.exists() for p in required):
            return ""
        return inference.summarize(text[:2000], max_new_tokens=60) or ""
    except Exception:
        return ""


def build_card(
    session_id: str | None = None,
    *,
    hours: float = 1.0,
    local_summary: bool = False,
    include_noise: bool = False,
) -> dict[str, Any]:
    session = _find_session(session_id, hours, include_noise=include_noise)
    if not session:
        return {"error": "no session found", "session_id": session_id or ""}

    summary = _cached_summary(session)
    entries = _tail_entries(session["file"])

    last_user = ""
    last_assistant = ""
    last_tool = ""
    touched_files: list[str] = []
    transcript_tail: list[str] = []

    for entry in entries:
        msg = entry.get("message") if isinstance(entry.get("message"), dict) else {}
        content = msg.get("content", "")
        text = _content_text(content).strip()
        if text:
            role = entry.get("type") or "message"
            transcript_tail.append(f"{role}: {text[:500]}")

        if entry.get("type") == "user" and text:
            last_user = text
        elif entry.get("type") == "assistant":
            if text:
                last_assistant = text
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = str(block.get("name") or "")
                    inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                    label = inp.get("file_path") or inp.get("path") or inp.get("command") or ""
                    if label:
                        last_tool = f"{name}: {str(label)[:160]}"
                    else:
                        last_tool = name
                    fp = inp.get("file_path") or inp.get("path")
                    if isinstance(fp, str) and fp not in touched_files:
                        touched_files.append(fp)

    local = ""
    if local_summary:
        local = _local_t5_summary("\n".join(transcript_tail[-8:]))

    title = str(summary.get("title") or "").splitlines()
    title_text = title[0].strip() if title else ""
    project_dir = str(session.get("project_dir") or "")
    command = f"claude --resume {session['session_id']}"

    return {
        "session_id": session["session_id"],
        "project": shorten_path(project_dir),
        "project_dir": project_dir,
        "age": relative_time(session["mtime"]),
        "mtime": session["mtime"],
        "date": datetime.fromtimestamp(session["mtime"]).isoformat(timespec="seconds"),
        "title": title_text or last_user[:90] or "Untitled Claude Code session",
        "where_stopped": local or str(summary.get("state") or "").strip() or last_assistant[:240],
        "last_user": last_user[:500],
        "last_assistant": last_assistant[:500],
        "last_tool": last_tool,
        "files": touched_files[:8] or list(summary.get("files") or [])[:8],
        "git": _git_dirty(project_dir),
        "command": command,
        "source": "local-t5" if local else ("cached-summary" if summary else "tail-extractive"),
    }


def card_events(card: dict[str, Any]) -> list[dict[str, Any]]:
    channel = "resume card"
    if "error" in card:
        return [{"channel": channel, "text": card["error"], "icon": "error", "highlight": True}]
    events = [
        {"channel": channel, "clear": True},
        {
            "channel": channel,
            "text": f"{card['project']} • {card['age']}",
            "icon": "info",
            "highlight": True,
        },
        {
            "channel": channel,
            "result": {
                "title": card["title"],
                "meta": card.get("where_stopped") or "No summary yet.",
                "session_id": card["session_id"],
            },
        },
    ]
    if card.get("last_tool"):
        events.append({"channel": channel, "text": card["last_tool"], "icon": "working"})
    if card.get("git", {}).get("dirty"):
        events.append({
            "channel": channel,
            "text": f"Dirty repo: {card['git'].get('count', 0)} file(s)",
            "icon": "working",
        })
    events.append({"channel": channel, "text": card["command"], "icon": "done", "highlight": True})
    return events


def _print_human(card: dict[str, Any]) -> None:
    if "error" in card:
        print(card["error"], file=sys.stderr)
        return
    print(f"{card['title']}")
    print(f"{card['project']} • {card['age']} • {card['session_id'][:8]}")
    if card.get("where_stopped"):
        print(f"\nStopped: {card['where_stopped']}")
    if card.get("last_user"):
        print(f"\nLast ask: {card['last_user'][:240]}")
    if card.get("last_tool"):
        print(f"\nLast tool: {card['last_tool']}")
    if card.get("files"):
        print("\nFiles:")
        for path in card["files"][:5]:
            print(f"  {path}")
    print(f"\n{card['command']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Show a fast resume card for a Claude Code session")
    parser.add_argument("session", nargs="?", help="Session UUID. Defaults to latest indexed session.")
    parser.add_argument("--hours", type=float, default=1.0, help="Latest-session lookback window")
    parser.add_argument("--json", action="store_true", help="Print one JSON object")
    parser.add_argument("--events", action="store_true", help="Print HUD JSONL events")
    parser.add_argument("--hud", action="store_true", help="Send events to the resume-resume HUD")
    parser.add_argument("--local-summary", action="store_true", help="Use cached local ONNX/T5 model if present")
    parser.add_argument("--include-noise", action="store_true", help="Allow summarizer/meta sessions as latest candidates")
    args = parser.parse_args(argv)

    sid = args.session
    if sid and not UUID_RE.fullmatch(sid):
        match = UUID_RE.search(sid)
        sid = match.group(0) if match else sid

    card = build_card(sid, hours=args.hours, local_summary=args.local_summary, include_noise=args.include_noise)

    if args.hud:
        from .progress import progress

        with progress("resume card") as p:
            for event in card_events(card):
                if event.get("clear"):
                    p.clear()
                elif event.get("result"):
                    r = event["result"]
                    p.result(r["title"], r["meta"], r.get("session_id", ""))
                else:
                    p.update(event.get("text", ""), event.get("icon", "info"), event.get("highlight", False))

    if args.events:
        for event in card_events(card):
            print(json.dumps(event))
        return

    if args.json:
        print(json.dumps(card, indent=2))
        return

    _print_human(card)


if __name__ == "__main__":
    main()
