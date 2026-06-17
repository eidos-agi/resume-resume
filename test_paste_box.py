"""ponytail checks: id extraction from pasted commands, and the in-order
coverage gate that proves a chat-text paste belongs to the matched session."""
from resume_resume.cli import ID_IN_TEXT, _paste_coverage

UUID = "0c39af13-0ec4-43e2-b567-10e98de1747b"


def test_extracts_id_from_shell_wrapped_paste():
    assert ID_IN_TEXT.search(f"cd ~/repos && claude --resume {UUID}").group(0) == UUID
    assert ID_IN_TEXT.search(UUID).group(0) == UUID  # bare id
    assert ID_IN_TEXT.search("codex resume rollout-2026-06-12-abc").group(0) == "rollout-2026-06-12-abc"
    assert ID_IN_TEXT.search("just some prose I copied") is None  # -> search path


def test_coverage_distinguishes_paste_from_keyword_overlap():
    src = "the quick brown fox jumps over the lazy dog near the river bank at dawn"
    wrapped = "quick brown fox\n  jumps over the lazy dog"   # terminal-wrapped paste
    assert _paste_coverage(wrapped, src) > 0.8                # in-order subsequence
    assert _paste_coverage(wrapped, "fox dog lazy quick unrelated jumble text") < 0.5  # same words, wrong order


if __name__ == "__main__":
    test_extracts_id_from_shell_wrapped_paste()
    test_coverage_distinguishes_paste_from_keyword_overlap()
    print("ok")
