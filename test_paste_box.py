"""ponytail checks: id extraction from pasted commands, the in-order coverage
gate, and an end-to-end build+search round-trip on the persistent index."""

import tempfile
from pathlib import Path

from resume_resume.cli import ID_IN_TEXT, _paste_coverage
from resume_resume import paste_index

UUID = "0c39af13-0ec4-43e2-b567-10e98de1747b"


def test_extracts_id_from_shell_wrapped_paste():
    assert ID_IN_TEXT.search(f"cd ~/repos && claude --resume {UUID}").group(0) == UUID
    assert ID_IN_TEXT.search(UUID).group(0) == UUID  # bare id
    assert (
        ID_IN_TEXT.search("codex resume rollout-2026-06-12-abc").group(0)
        == "rollout-2026-06-12-abc"
    )
    assert ID_IN_TEXT.search("just some prose I copied") is None  # -> search path


def test_coverage_distinguishes_paste_from_keyword_overlap():
    src = "the quick brown fox jumps over the lazy dog near the river bank at dawn"
    wrapped = "quick brown fox\n  jumps over the lazy dog"  # terminal-wrapped paste
    assert _paste_coverage(wrapped, src) > 0.8  # in-order subsequence
    assert (
        _paste_coverage(wrapped, "fox dog lazy quick unrelated jumble text") < 0.5
    )  # same words, wrong order


def test_index_build_and_search_round_trip():
    """Build an index over a temp corpus, confirm a pasted chunk resolves to
    its source session and an unrelated paste does not."""
    with tempfile.TemporaryDirectory() as d:
        corpus = Path(d) / "proj"
        corpus.mkdir()
        target = "aaaaaaaa-1111-2222-3333-444444444444"
        other = "bbbbbbbb-5555-6666-7777-888888888888"
        (corpus / f"{target}.jsonl").write_text(
            '{"message":{"content":[{"type":"text",'
            '"text":"the **migration** rewrites the artemis token cache, not the knox vault — see plan"}]}}'
        )
        (corpus / f"{other}.jsonl").write_text(
            '{"message":{"content":[{"type":"text","text":"unrelated notes about lunch and the weather today"}]}}'
        )
        paste_index.PROJECTS_GLOB = str(corpus / "**" / "*.jsonl")
        paste_index.DB_PATH = Path(d) / "idx.db"
        con = paste_index._connect()
        try:
            n = paste_index.refresh(con)
            assert n == 2
            # terminal-wrapped, markdown-rendered paste of the target's text
            hit = paste_index.search(
                con,
                "the migration rewrites the artemis\n  token cache, not the knox vault",
            )
            assert hit and hit[0][0] == target and hit[0][2] >= 0.5
            # self-exclusion drops the target
            assert (
                paste_index.search(
                    con,
                    "the migration rewrites the artemis token cache",
                    self_sid=target,
                )
                == []
            )
            # unrelated paste finds nothing
            assert (
                paste_index.search(
                    con, "quarterly mango harvest exceeded forecasts in patagonia"
                )
                == []
            )
        finally:
            con.close()


if __name__ == "__main__":
    test_extracts_id_from_shell_wrapped_paste()
    test_coverage_distinguishes_paste_from_keyword_overlap()
    test_index_build_and_search_round_trip()
    print("ok")
