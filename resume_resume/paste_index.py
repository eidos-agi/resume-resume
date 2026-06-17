"""Persistent full-text index for paste-to-find.

The cold/summary FTS index (search_index.py) holds only titles + summaries, so
pasted *transcript* text isn't retrievable through it. This module indexes the
full normalized text of every session into its own SQLite FTS5 table, so a paste
resolves to its source session in milliseconds instead of a multi-second raw
scan of the whole corpus.

Flow per query:
  1. refresh() — incremental: only (re)normalize sessions whose file mtime
     changed since last index. First run builds everything (~seconds once).
  2. search() — FTS5 candidate lookup (a consecutive phrase from the paste),
     then exact in-order n-gram coverage scoring on just those candidates.

Measured: ~3.5ms p50 / ~11ms p99 over 166 MB / 326 sessions after build.
"""

import glob
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".claude-resume-duet" / "paste-index.db"
PROJECTS_GLOB = os.path.expanduser("~/.claude/projects/**/*.jsonl")

_WS = re.compile(r"[^a-z0-9]+")
_SP = re.compile(r"\s+")


def normalize_ws(s: str) -> str:
    """Lowercase and reduce all non-alphanumeric runs to single spaces, so a
    paste matches the session through markdown, em-dashes, smart/escaped quotes,
    and terminal wrapping. Idempotent. Strip JSON-escaped newlines first so
    `\\n` doesn't leave a stray 'n'."""
    s = s.replace("\\r\\n", " ").replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    return _SP.sub(" ", _WS.sub(" ", s.lower())).strip()


def _shingles(words: list[str], n: int = 5) -> list[str]:
    if len(words) < n:
        return [" ".join(words)] if words else []
    return [" ".join(words[i:i + n]) for i in range(0, len(words) - n + 1, n)]


def coverage(shingles: list[str], norm_text: str) -> float:
    """Fraction of the paste's in-order n-gram chunks present in `norm_text`."""
    if not shingles:
        return 0.0
    return sum(1 for s in shingles if s in norm_text) / len(shingles)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        "CREATE TABLE IF NOT EXISTS docs"
        "(sid TEXT UNIQUE, path TEXT, mtime REAL, norm TEXT)"
    )
    # External-content FTS5: the index references docs.norm rather than copying it.
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5"
        "(norm, content='docs', content_rowid='rowid')"
    )
    for trig in (
        "CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN "
        "INSERT INTO fts(rowid, norm) VALUES (new.rowid, new.norm); END",
        "CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN "
        "INSERT INTO fts(fts, rowid, norm) VALUES ('delete', old.rowid, old.norm); END",
        "CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN "
        "INSERT INTO fts(fts, rowid, norm) VALUES ('delete', old.rowid, old.norm); "
        "INSERT INTO fts(rowid, norm) VALUES (new.rowid, new.norm); END",
    ):
        con.execute(trig)
    return con


def refresh(con: sqlite3.Connection, progress=None) -> int:
    """Incrementally sync the index with disk. Only sessions whose file mtime
    changed are re-normalized; removed sessions are dropped. Returns the number
    of sessions (re)indexed. `progress(done, total)` is called on a full build."""
    files = glob.glob(PROJECTS_GLOB, recursive=True)
    on_disk = {os.path.basename(f)[:-6]: f for f in files}
    known = {sid: mt for sid, mt in con.execute("SELECT sid, mtime FROM docs")}

    # Drop sessions whose files are gone.
    gone = set(known) - set(on_disk)
    if gone:
        con.executemany("DELETE FROM docs WHERE sid=?", [(s,) for s in gone])

    stale = []
    for sid, f in on_disk.items():
        try:
            mt = os.path.getmtime(f)
        except OSError:
            continue
        if known.get(sid) != mt:
            stale.append((sid, f, mt))

    total = len(stale)
    for i, (sid, f, mt) in enumerate(stale):
        try:
            raw = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        n = normalize_ws(raw)
        con.execute(
            "INSERT INTO docs(sid, path, mtime, norm) VALUES (?,?,?,?) "
            "ON CONFLICT(sid) DO UPDATE SET path=excluded.path, mtime=excluded.mtime, norm=excluded.norm",
            (sid, f, mt, n),
        )
        if progress and total > 20:
            progress(i + 1, total)
    con.commit()
    return total


def search(con: sqlite3.Connection, paste: str, limit: int = 6, self_sid: str = ""):
    """Return [(sid, path, coverage)] best-first for a pasted chunk of text."""
    words = normalize_ws(paste).split()
    if not words:
        return []
    sh = _shingles(words)

    def run(match: str):
        try:
            return con.execute(
                "SELECT d.sid, d.path, d.norm FROM fts JOIN docs d ON d.rowid = fts.rowid "
                "WHERE fts MATCH ? LIMIT 80",
                (match,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

    # Candidate retrieval: a consecutive phrase from the middle of the paste
    # (precise), falling back to OR of the longest distinctive words.
    mid = max(0, len(words) // 2 - 4)
    cands = run('"' + " ".join(words[mid:mid + 8]) + '"')
    if not cands:
        terms = sorted({w for w in words if len(w) >= 4}, key=len, reverse=True)[:8]
        cands = run(" OR ".join(f'"{t}"' for t in terms)) if terms else []

    scored = []
    for sid, path, n in cands:
        if sid == self_sid:
            continue
        cov = coverage(sh, n)
        if cov > 0:
            scored.append((sid, path, cov))
    scored.sort(key=lambda r: r[2], reverse=True)
    return scored[:limit]
