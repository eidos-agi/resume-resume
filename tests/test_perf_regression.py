"""Performance regression tests.

These tests encode the wins from commit 29d2f73 (and future perf work) so
that if someone removes a cache, un-optimizes a scan, or otherwise drags
performance backwards, CI catches it.

Philosophy: assert *relative* speedups (cache hit is N× faster than cold)
and *generous absolute ceilings* (cold path < 5s). Relative assertions are
hardware-independent; absolute ceilings catch catastrophic regressions.

Each test maps to an entry in `docs/known-issues.md`.
"""

from __future__ import annotations

import time

import pytest
import pytest_asyncio
from fastmcp import Client

from resume_resume import mcp_server as ms


def _bust_dirty_repos_cache() -> None:
    ms._DIRTY_REPOS_CACHE["data"] = None
    ms._DIRTY_REPOS_CACHE["ts"] = 0.0


async def _time_call(client: Client, tool: str, args: dict) -> float:
    """Return duration in ms for one MCP tool call."""
    t0 = time.perf_counter()
    await client.call_tool(tool, args)
    return (time.perf_counter() - t0) * 1000.0


@pytest_asyncio.fixture
async def client():
    async with Client(ms.mcp) as c:
        # one warm-up to absorb import + client setup overhead
        await c.call_tool("self_insights", {"days": 1})
        yield c


# ---------------------------------------------------------------------------
# dirty_repos — perf-001
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dirty_repos_cached_is_dramatically_faster_than_cold(client):
    """perf-001a: the 30s TTL cache must give a near-instant second call.

    Covers the cache added in 29d2f73. Cold path is hardware-dependent, but
    cached should always be within a few ms regardless of disk speed.
    """
    _bust_dirty_repos_cache()
    cold_ms = await _time_call(client, "dirty_repos", {})
    cached_ms = await _time_call(client, "dirty_repos", {})
    assert cold_ms > 50, f"cold path suspiciously fast ({cold_ms:.0f}ms) — is scan short-circuiting?"
    assert cached_ms < 50, f"cached path too slow ({cached_ms:.0f}ms) — is cache working?"
    assert cold_ms / cached_ms >= 20, (
        f"cache speedup insufficient: cold={cold_ms:.0f}ms cached={cached_ms:.0f}ms "
        f"ratio={cold_ms/cached_ms:.1f}x (expected >=20x)"
    )


@pytest.mark.asyncio
async def test_dirty_repos_cold_under_generous_ceiling(client):
    """perf-001b: cold path ceiling. A1's original flag was 3071ms on a real
    machine; the 29d2f73 optimization dropped it to ~2000ms. Assert a
    generous 5000ms ceiling so we catch catastrophic regressions without
    being flaky on slow CI."""
    _bust_dirty_repos_cache()
    cold_ms = await _time_call(client, "dirty_repos", {})
    assert cold_ms < 5000, (
        f"dirty_repos cold path {cold_ms:.0f}ms exceeds 5000ms ceiling. "
        "Check _scan_repo_git for new subprocess calls or blocking I/O."
    )


@pytest.mark.asyncio
async def test_dirty_repos_cache_reports_cached_flag(client):
    """perf-001c: cached result must be tagged so callers can distinguish it
    from a fresh scan. Regression guard for the response shape."""
    _bust_dirty_repos_cache()
    await client.call_tool("dirty_repos", {})
    result = await client.call_tool("dirty_repos", {})
    data = result.data
    assert data.get("cached") is True
    assert "cache_age_s" in data


# ---------------------------------------------------------------------------
# self_* response-shape normalization — correctness-002
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_self_list_tools_return_wrapped_dict(client):
    """correctness-002: list-returning self_* tools must return
    {items, count}, not a bare list that fastmcp wraps as {result: [...]}."""
    list_tools = [
        ("self_recent_calls", {"limit": 3}),
        ("self_slow_calls", {"threshold_ms": 1}),
        ("self_errors", {}),
        ("self_search", {"query": "anything"}),
        ("self_bundles", {}),
        ("self_a1_output", {}),
        ("self_a1_auto_applied", {}),
        ("self_process_proposals", {}),
        ("self_proposal_history", {}),
    ]
    for tool, args in list_tools:
        result = await client.call_tool(tool, args)
        data = result.data
        assert isinstance(data, dict), f"{tool} returned {type(data).__name__}, expected dict"
        assert "items" in data, f"{tool} missing 'items' key: {list(data.keys())}"
        assert "count" in data, f"{tool} missing 'count' key: {list(data.keys())}"
        assert isinstance(data["items"], list), f"{tool}['items'] is not a list"
        assert data["count"] == len(data["items"]), f"{tool}['count'] != len(items)"


# ---------------------------------------------------------------------------
# self_insights — perf-003
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_self_insights_fast(client):
    """perf-003: self_insights is hit repeatedly by A1/A2/human. Must stay
    fast even as telemetry grows.

    Generous 500ms ceiling; current is ~5ms. If this starts failing, JSONL
    scanning has become a bottleneck and we need a daily index."""
    dur_ms = await _time_call(client, "self_insights", {"days": 30})
    assert dur_ms < 500, (
        f"self_insights took {dur_ms:.0f}ms — suggests telemetry scan has "
        "become a hot path. Consider daily index or in-memory cache."
    )


# ---------------------------------------------------------------------------
# recent_sessions — perf-004 (currently slow, no fix shipped yet)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recent_sessions_under_generous_ceiling(client):
    """perf-004: recent_sessions was observed at 1132ms in telemetry and
    ~1200ms when remeasured. No optimization shipped yet — this test
    documents the current state with a generous ceiling. Tighten when a
    fix lands."""
    dur_ms = await _time_call(client, "recent_sessions", {"hours": 24, "limit": 5})
    assert dur_ms < 3000, (
        f"recent_sessions took {dur_ms:.0f}ms — regression beyond the "
        "known-slow baseline (~1200ms)."
    )
