"""Tests for the telemetry writer + middleware."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from resume_resume import telemetry


def test_telemetry_enabled_default(monkeypatch):
    monkeypatch.delenv("RESUME_RESUME_TELEMETRY", raising=False)
    assert telemetry.telemetry_enabled() is True


def test_telemetry_disabled_by_env(monkeypatch):
    monkeypatch.setenv("RESUME_RESUME_TELEMETRY", "0")
    assert telemetry.telemetry_enabled() is False


def test_telemetry_root_uses_username():
    root = telemetry.telemetry_root()
    assert root.parts[-3:] == (".resume-resume", "telemetry", root.parts[-1])
    # username should be the last segment
    import getpass
    assert root.parts[-1] == getpass.getuser()


def test_write_event_appends_jsonl(tmp_path: Path):
    target = tmp_path / "test.jsonl"
    telemetry.write_event({"tool": "a", "status": "ok"}, path=target)
    telemetry.write_event({"tool": "b", "status": "error"}, path=target)

    lines = target.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["tool"] == "a"
    assert second["tool"] == "b"


def test_write_event_creates_parent_dir(tmp_path: Path):
    target = tmp_path / "nested" / "deeper" / "day.jsonl"
    telemetry.write_event({"tool": "x"}, path=target)
    assert target.exists()
    assert json.loads(target.read_text().strip())["tool"] == "x"


def test_write_event_never_raises(tmp_path: Path, monkeypatch):
    # Non-writable path should be swallowed, not raise.
    bad = tmp_path / "readonly"
    bad.mkdir()
    bad.chmod(0o400)
    try:
        telemetry.write_event({"tool": "x"}, path=bad / "nope" / "f.jsonl")
    finally:
        bad.chmod(0o700)


def test_jsonable_passthrough_for_primitives():
    assert telemetry._jsonable({"a": 1, "b": [2, 3]}) == {"a": 1, "b": [2, 3]}
    assert telemetry._jsonable("hello") == "hello"
    assert telemetry._jsonable(42) == 42


def test_jsonable_handles_objects_with_dict():
    class Foo:
        def __init__(self):
            self.x = 1
            self.y = "two"

    out = telemetry._jsonable(Foo())
    assert out == {"x": 1, "y": "two"}


def test_jsonable_handles_nested_unserializable():
    class Bar:
        def __init__(self, v):
            self.v = v

    out = telemetry._jsonable([Bar(1), Bar(2)])
    assert out == [{"v": 1}, {"v": 2}]


def test_jsonable_falls_back_to_repr():
    class Weird:
        __slots__ = ()

        def __repr__(self):
            return "<weird>"

    assert telemetry._jsonable(Weird()) == "<weird>"


def test_safe_size_returns_length():
    assert telemetry._safe_size({"a": 1}) == len('{"a": 1}')
    assert telemetry._safe_size("hi") == len('"hi"')


def test_today_path_uses_date(tmp_path: Path):
    p = telemetry._today_path(tmp_path)
    expected_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert p.name == f"{expected_day}.jsonl"
    assert p.parent == tmp_path


@pytest.mark.asyncio
async def test_middleware_captures_successful_call(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(telemetry, "_today_path", lambda: tmp_path / "today.jsonl")

    class FakeMsg:
        name = "test_tool"
        arguments = {"q": "hello"}

    class FakeCtx:
        message = FakeMsg()
        fastmcp_context = None

    async def fake_next(ctx):
        return {"result": "ok", "items": [1, 2, 3]}

    mw = telemetry.TelemetryMiddleware()
    out = await mw.on_call_tool(FakeCtx(), fake_next)
    assert out == {"result": "ok", "items": [1, 2, 3]}

    lines = (tmp_path / "today.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["tool"] == "test_tool"
    assert event["args"] == {"q": "hello"}
    assert event["status"] == "ok"
    assert event["error_type"] is None
    assert event["result"] == {"result": "ok", "items": [1, 2, 3]}
    assert event["duration_ms"] >= 0
    assert event["pid"] == os.getpid()


@pytest.mark.asyncio
async def test_middleware_captures_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(telemetry, "_today_path", lambda: tmp_path / "today.jsonl")

    class FakeMsg:
        name = "broken_tool"
        arguments = {}

    class FakeCtx:
        message = FakeMsg()
        fastmcp_context = None

    async def fake_next(ctx):
        raise ValueError("boom")

    mw = telemetry.TelemetryMiddleware()
    with pytest.raises(ValueError):
        await mw.on_call_tool(FakeCtx(), fake_next)

    lines = (tmp_path / "today.jsonl").read_text().strip().splitlines()
    event = json.loads(lines[0])
    assert event["tool"] == "broken_tool"
    assert event["status"] == "error"
    assert event["error_type"] == "ValueError"
    assert event["error_msg"] == "boom"
    assert event["result"] is None
    assert "Traceback" in (event["error_tb"] or "")


@pytest.mark.asyncio
async def test_middleware_respects_disable_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESUME_RESUME_TELEMETRY", "0")
    monkeypatch.setattr(telemetry, "_today_path", lambda: tmp_path / "today.jsonl")

    class FakeMsg:
        name = "test_tool"
        arguments = {}

    class FakeCtx:
        message = FakeMsg()
        fastmcp_context = None

    async def fake_next(ctx):
        return "ok"

    mw = telemetry.TelemetryMiddleware()
    await mw.on_call_tool(FakeCtx(), fake_next)
    assert not (tmp_path / "today.jsonl").exists()
