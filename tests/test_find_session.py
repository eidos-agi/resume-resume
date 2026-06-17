"""Tests for _find_session — resolves both Claude-Code and Codex sessions.

Regression coverage for the bug where search_sessions surfaced Codex
`rollout-*` ids but _find_session (UUID-gated, ~/.claude/projects-only glob)
returned None for them, breaking read_session / session_summary / resume etc.
"""

from __future__ import annotations

import json

import pytest

from resume_resume import mcp_server as ms


CLAUDE_UUID = "019ed161-140f-7791-872c-c752174d4a55"
CODEX_ID = "rollout-2026-06-16T12-01-00-019ed161-140f-7791-872c-c752174d4a55"
EXPECTED_KEYS = {"file", "session_id", "project_dir", "mtime", "size"}


@pytest.fixture
def session_roots(tmp_path, monkeypatch):
    """Mirror the real on-disk layout under a temp dir and point the
    module's PROJECTS_DIR / CODEX_SESSIONS_DIR at it."""
    # Claude: ~/.claude/projects/<encoded>/<uuid>.jsonl
    projects = tmp_path / "projects"
    proj_dir = projects / "-Users-dshanklinbv-repos-eidos-agi-resume-resume"
    proj_dir.mkdir(parents=True)
    claude_file = proj_dir / f"{CLAUDE_UUID}.jsonl"
    claude_file.write_text(
        json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n"
    )

    # Codex: ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
    codex_root = tmp_path / "codex"
    day_dir = codex_root / "2026" / "06" / "16"
    day_dir.mkdir(parents=True)
    codex_file = day_dir / f"{CODEX_ID}.jsonl"
    codex_file.write_text(
        json.dumps(
            {
                "type": "session_meta",
                "payload": {"cwd": "/Users/dshanklinbv/repos-jetta-operating"},
            }
        )
        + "\n"
    )

    monkeypatch.setattr(ms, "PROJECTS_DIR", projects)
    monkeypatch.setattr(ms, "CODEX_SESSIONS_DIR", codex_root)
    return {"claude": claude_file, "codex": codex_file}


def test_codex_rollout_id_resolves(session_roots):
    result = ms._find_session(CODEX_ID)
    assert result is not None, "Codex rollout id should resolve"
    assert set(result.keys()) == EXPECTED_KEYS
    assert result["file"] == session_roots["codex"]
    assert result["session_id"] == CODEX_ID
    # project_dir derived from the session_meta cwd, matching scan_codex_sessions
    assert result["project_dir"] == "/Users/dshanklinbv/repos-jetta-operating"
    assert result["size"] > 0


def test_normal_uuid_still_resolves(session_roots):
    result = ms._find_session(CLAUDE_UUID)
    assert result is not None, "Claude UUID should still resolve"
    assert set(result.keys()) == EXPECTED_KEYS
    assert result["file"] == session_roots["claude"]
    assert result["session_id"] == CLAUDE_UUID
    assert "resume-resume" in result["project_dir"]


@pytest.mark.parametrize(
    "bad_id",
    [
        "*",
        "rollout-*",
        "abc?def",
        "id[0-9]",
        "../../etc/passwd",
        "foo/bar",
        "rollout-2026/06/16",
    ],
)
def test_glob_injection_rejected(session_roots, bad_id):
    assert ms._find_session(bad_id) is None
