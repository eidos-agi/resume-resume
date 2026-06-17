"""Cross-tool support: Codex messages parse for merge_context, sessions label by tool."""

from claude_session_commons.codex import session_tool
from resume_resume import mcp_server as ms

CODEX_ROLLOUT = (
    '{"timestamp":"2026-06-12T19:00:30Z","type":"session_meta",'
    '"payload":{"id":"019ebc0c-9f4f-7362-9d26-fb071dfeecbe","cwd":"/tmp/demo"}}\n'
    '{"timestamp":"2026-06-12T19:01:00Z","type":"event_msg",'
    '"payload":{"type":"user_message","message":"research the auth token refresh bug"}}\n'
    '{"timestamp":"2026-06-12T19:01:30Z","type":"event_msg",'
    '"payload":{"type":"agent_message","message":"the refresh uses a 24h presigned url"}}\n'
    '{"timestamp":"2026-06-12T19:02:00Z","type":"response_item",'
    '"payload":{"type":"function_call","name":"exec_command","arguments":"{}"}}\n'
)


def test_session_tool_labels_by_source():
    assert (
        session_tool("rollout-2026-06-12T08-36-57-019ebc0c-9f4f-7362-9d26-fb071dfeecbe")
        == "codex"
    )
    assert session_tool("ddf7fc98-6c93-40c8-9444-503d8a716dbf") == "claude"


def test_read_messages_handles_codex_schema(tmp_path):
    f = (
        tmp_path
        / "rollout-2026-06-12T19-00-30-019ebc0c-9f4f-7362-9d26-fb071dfeecbe.jsonl"
    )
    f.write_text(CODEX_ROLLOUT)

    out = ms._read_messages(f, "", 6)
    roles = [m["role"] for m in out["messages"]]
    texts = " ".join(m["text"] for m in out["messages"])

    assert roles == ["user", "assistant"], out
    assert "auth token refresh" in texts
    assert "presigned url" in texts


def test_read_messages_codex_keyword_filter(tmp_path):
    f = tmp_path / "rollout-x-019ebc0c-9f4f-7362-9d26-fb071dfeecbe.jsonl"
    f.write_text(CODEX_ROLLOUT)

    out = ms._read_messages(f, "presigned", 6)
    assert len(out["messages"]) == 1
    assert out["messages"][0]["role"] == "assistant"
