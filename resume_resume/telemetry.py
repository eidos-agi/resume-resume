"""Telemetry middleware for resume-resume MCP server.

Captures every MCP tool call (full args, full result, timing, errors) to
a per-user JSONL file so resume-resume can answer questions about its own
usage and we can learn what to improve next.

Storage: ~/.resume-resume/telemetry/<username>/YYYY-MM-DD.jsonl
Disable: RESUME_RESUME_TELEMETRY=0
"""

from __future__ import annotations

import getpass
import json
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext


def telemetry_enabled() -> bool:
    return os.environ.get("RESUME_RESUME_TELEMETRY", "1") != "0"


def telemetry_root() -> Path:
    return Path.home() / ".resume-resume" / "telemetry" / getpass.getuser()


def _today_path(root: Path | None = None) -> Path:
    root = root or telemetry_root()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return root / f"{day}.jsonl"


def _safe_size(obj: Any) -> int:
    try:
        return len(json.dumps(obj, default=str))
    except Exception:
        return -1


def _jsonable(obj: Any) -> Any:
    """Coerce anything to something json.dumps can handle.

    Tool results can contain MCP content objects, pydantic models, dataclasses,
    bytes, or arbitrary objects. We want telemetry capture to never fail.
    """
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        pass

    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            return obj.dict()
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {k: _jsonable(v) for k, v in vars(obj).items()}
        except Exception:
            pass
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    return repr(obj)


def write_event(event: dict, *, path: Path | None = None) -> None:
    """Append a telemetry event to today's per-user JSONL file.

    Never raises — telemetry must not break the MCP server.
    """
    try:
        target = path or _today_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, default=str, ensure_ascii=False)
        with target.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _session_id(context: MiddlewareContext) -> str | None:
    ctx = getattr(context, "fastmcp_context", None)
    if ctx is None:
        return None
    try:
        if getattr(ctx, "request_context", None) is not None:
            return getattr(ctx, "session_id", None)
    except Exception:
        return None
    return None


def _request_id(context: MiddlewareContext) -> str | None:
    ctx = getattr(context, "fastmcp_context", None)
    if ctx is None:
        return None
    try:
        if getattr(ctx, "request_context", None) is not None:
            return str(getattr(ctx, "request_id", None))
    except Exception:
        return None
    return None


class TelemetryMiddleware(Middleware):
    """Capture every MCP tool call to per-user JSONL."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if not telemetry_enabled():
            return await call_next(context)

        msg = context.message
        tool_name = getattr(msg, "name", None)
        args = getattr(msg, "arguments", None) or {}
        started_ns = time.perf_counter_ns()
        started_iso = datetime.now(timezone.utc).isoformat()

        status = "ok"
        error_type: str | None = None
        error_msg: str | None = None
        error_tb: str | None = None
        result: Any = None

        try:
            result = await call_next(context)
            return result
        except Exception as e:
            status = "error"
            error_type = type(e).__name__
            error_msg = str(e)
            error_tb = traceback.format_exc()
            raise
        finally:
            duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
            event = {
                "ts": started_iso,
                "session_id": _session_id(context),
                "request_id": _request_id(context),
                "tool": tool_name,
                "args": _jsonable(args),
                "duration_ms": round(duration_ms, 3),
                "status": status,
                "error_type": error_type,
                "error_msg": error_msg,
                "error_tb": error_tb,
                "result_size": _safe_size(result) if status == "ok" else 0,
                "result": _jsonable(result) if status == "ok" else None,
                "pid": os.getpid(),
            }
            write_event(event)
