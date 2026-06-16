"""resume_command builds the right CLI per source (Claude Code vs Codex)."""

from claude_session_commons.codex import codex_session_uuid, is_codex_session_id
from resume_resume.session_utils import resume_command

CODEX_ID = "rollout-2026-06-12T08-36-57-019ebc0c-9f4f-7362-9d26-fb071dfeecbe"
CODEX_UUID = "019ebc0c-9f4f-7362-9d26-fb071dfeecbe"
CLAUDE_ID = "ddf7fc98-6c93-40c8-9444-503d8a716dbf"


def test_codex_uuid_extracted_from_rollout_stem():
    assert is_codex_session_id(CODEX_ID)
    assert not is_codex_session_id(CLAUDE_ID)
    assert codex_session_uuid(CODEX_ID) == CODEX_UUID


def test_codex_resume_and_fork():
    assert resume_command(CODEX_ID) == f"codex resume {CODEX_UUID}"
    assert resume_command(CODEX_ID, fork=True) == f"codex fork {CODEX_UUID}"
    # Codex has no skip-permissions flag — it's ignored, not appended.
    assert resume_command(CODEX_ID, skip_permissions=True) == f"codex resume {CODEX_UUID}"


def test_claude_resume_and_fork():
    assert resume_command(CLAUDE_ID) == f"claude --resume {CLAUDE_ID}"
    assert resume_command(CLAUDE_ID, fork=True) == f"claude --resume {CLAUDE_ID} --fork-session"
    assert resume_command(CLAUDE_ID, skip_permissions=True) == (
        f"claude --resume {CLAUDE_ID} --dangerously-skip-permissions"
    )


def test_cr_paste_parsing_covers_both_tools():
    from resume_resume.cli import _parse_resume_args

    assert _parse_resume_args(["claude", "--resume", CLAUDE_ID, "--model", "opus"]) == (
        CLAUDE_ID, ["--model", "opus"], False, "resume")
    assert _parse_resume_args(["--resume", CLAUDE_ID]) == (CLAUDE_ID, [], False, "resume")
    assert _parse_resume_args([CLAUDE_ID]) == (CLAUDE_ID, [], False, "resume")
    assert _parse_resume_args(["codex", "resume", CODEX_UUID]) == (
        CODEX_UUID, [], True, "resume")
    assert _parse_resume_args(["codex", "fork", CODEX_UUID]) == (CODEX_UUID, [], True, "fork")
    # A bare full rollout id is recognized as Codex.
    assert _parse_resume_args([CODEX_ID]) == (CODEX_ID, [], True, "resume")
