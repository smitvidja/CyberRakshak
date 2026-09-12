"""The index must survive being checked out on a machine that rewrites newlines.

knowledge_index.json stores a hash of sources.json and refuses to load when it
stops matching. That is the right instinct - serving a stale index would answer
citizens from a corpus that is no longer there. But the hash was taken over the raw
bytes, and with no .gitattributes git rewrites the file to CRLF on checkout on
Windows: identical content, completely different hash, and every Cyber Saathi
question answered 503 KNOWLEDGE_INDEX_INVALID on a fresh clone.

Both halves of the fix are covered here: the hash ignores line endings, and it
still notices an actual change to the corpus.
"""

from __future__ import annotations

from pathlib import Path

from app.services.cyber_saathi_knowledge import (
    SOURCE_PACK_PATH,
    KnowledgeService,
    _source_pack_hash,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_a_crlf_checkout_produces_the_same_corpus_hash() -> None:
    payload = SOURCE_PACK_PATH.read_bytes()
    assert b"\r\n" not in payload, "the committed file should be stored with LF"
    as_checked_out_on_windows = payload.replace(b"\n", b"\r\n")
    assert _source_pack_hash(as_checked_out_on_windows) == _source_pack_hash(payload)


def test_the_hash_still_changes_when_the_corpus_actually_changes() -> None:
    """A line-ending-blind hash must not become a hash that notices nothing."""
    payload = SOURCE_PACK_PATH.read_bytes()
    edited = payload.replace(b'"version"', b'"Version"', 1)
    assert edited != payload
    assert _source_pack_hash(edited) != _source_pack_hash(payload)


def test_the_committed_index_loads_against_the_committed_corpus() -> None:
    """The pair that ships must actually validate together."""
    KnowledgeService.clear_cache()
    index = KnowledgeService._load_index()
    assert index["chunks"]


def test_gitattributes_pins_the_line_endings() -> None:
    """Code-side normalisation stops the damage; this stops the rewrite."""
    attributes = REPO_ROOT / ".gitattributes"
    assert attributes.exists(), "a checkout on Windows will rewrite sources.json"
    assert "eol=lf" in attributes.read_text(encoding="utf-8")
