"""Tests for _fts_query token-to-FTS5 translation.

Regression for the intolerant-search bug: a multi-word query used to join
tokens with AND, so a session matching 3 of 4 words returned zero results.
Tokens are now joined with OR (tolerant), and bm25() ranking floats the
sessions matching more terms to the top.
"""

from resume_resume.search_index import _fts_query


def test_multi_word_query_is_or_joined():
    fts = _fts_query("eat alone dinner")
    assert fts == '"eat" OR "alone" OR "dinner"'
    assert " AND " not in fts


def test_single_token_has_no_join():
    fts = _fts_query("dinner")
    assert fts == '"dinner"'
    assert " OR " not in fts and " AND " not in fts


def test_empty_query_returns_empty_string():
    # Callers rely on "" to skip the search entirely.
    assert _fts_query("") == ""
    assert _fts_query("   ") == ""
