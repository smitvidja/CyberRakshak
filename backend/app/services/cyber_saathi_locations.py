"""Where the citizen is, in a form a police complaint can use.

Two things were wrong before. The gazetteer was twenty-three cities scanned with a
regex each, and nine of them had a state - so a complaint from Bilaspur or Jamtara
or Kozhikode carried no city at all, and most of the rest carried no state. And the
scan was linear in the size of the list, so the obvious fix of adding more cities
would have made every message slower.

This resolves in one pass over the message instead. The message is split into words
once, and each two- and three-word window is looked up before the single words, so
"new delhi" is New Delhi and not Delhi, and "navi mumbai" is not Mumbai.

The list is still not every town in India and is not meant to be. It exists to
recognise a place named in passing, mid-sentence. When Cyber Saathi asks the
citizen where this happened, the answer is taken as given - see
``looks_like_place_name`` - so an unlisted town is still recorded.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

# Deliberately not imported from the understanding engine: that module imports this
# one, and taking DATA_DIR from it would make the pair circular.
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cyber_saathi"
LOCATIONS_PATH = DATA_DIR / "india_locations.json"

# The same token rule the rest of the pipeline uses: ``\w`` splits Devanagari
# vowel signs and the virama, which would break every Hindi place name.
TOKEN_PATTERN = re.compile(r"[a-zA-Z]+|[ऀ-ॿ]+")
MAX_NAME_WORDS = 3


class ResolvedLocation(NamedTuple):
    city: str | None
    state: str | None

    @property
    def is_empty(self) -> bool:
        return self.city is None and self.state is None


@lru_cache(maxsize=1)
def _gazetteer() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    payload = json.loads(LOCATIONS_PATH.read_text(encoding="utf-8"))
    return payload["cities"], payload["states"]


# Some Indian towns are also ordinary words. "gaya" is the Hindi for "went", so
# "mera paisa gaya" - my money went - put Gaya, Bihar on the complaint of a citizen
# who had never been there. "banda", "basti", "kota", "puri", "sagar", "mandi" and
# "daman" are the same kind of trap.
#
# These are matched only when the sentence places the citizen there: directly after
# a word like "in", "from" or "mein", or when the whole message is just the name,
# which is what an answer to the location question looks like.
AMBIGUOUS_NAMES = frozenset(
    {
        "gaya", "mandi", "banda", "basti", "kota", "puri", "sagar", "pali", "daman",
        "anand", "una", "jind", "durg", "diu", "leh", "moga", "rewa", "salem",
        "गया", "मंडी", "बांदा", "बस्ती", "कोटा", "पुरी", "सागर", "पाली", "दमन",
        "आणंद", "ऊना", "जींद", "दुर्ग", "दीव", "लेह", "मोगा", "रीवा",
    }
)
LOCATION_MARKERS = frozenset(
    {
        "in", "from", "at", "near", "of", "city", "town", "district",
        "me", "mein", "se", "ka", "ki", "ke", "wale", "waale", "rehta", "rehti",
        "shahar", "sheher", "zila", "jila",
        "में", "से", "का", "की", "के", "शहर", "जिला", "रहता", "रहती", "वाला",
    }
)


def _windows(tokens: list[str]) -> list[tuple[str, int, int]]:
    """Every one-, two- and three-word window, longest first, with its position."""
    candidates: list[tuple[str, int, int]] = []
    for size in range(MAX_NAME_WORDS, 0, -1):
        for offset in range(len(tokens) - size + 1):
            candidates.append((" ".join(tokens[offset : offset + size]), offset, size))
    return candidates


def _is_placed(tokens: list[str], offset: int, size: int) -> bool:
    """Does the sentence actually put the citizen at this name?"""
    if offset == 0 and size == len(tokens):
        return True
    if offset > 0 and tokens[offset - 1] in LOCATION_MARKERS:
        return True
    # "Bilaspur mein", "Jamtara se" - Hindi puts the marker after the place.
    following = offset + size
    return following < len(tokens) and tokens[following] in LOCATION_MARKERS


def resolve_location(message: str) -> ResolvedLocation:
    """The city and state named anywhere in this text, if either is recognised."""
    if not message:
        return ResolvedLocation(None, None)
    cities, states = _gazetteer()
    tokens = TOKEN_PATTERN.findall(message.casefold())
    city: str | None = None
    state: str | None = None
    for candidate, offset, size in _windows(tokens):
        if candidate in AMBIGUOUS_NAMES and not _is_placed(tokens, offset, size):
            continue
        if city is None:
            entry = cities.get(candidate)
            if entry is not None:
                city = entry["canonical"]
                # A city carries its own state, and that is more specific than a
                # state named separately in the same sentence.
                state = entry["state"]
                continue
        if state is None:
            matched_state = states.get(candidate)
            if matched_state is not None:
                state = matched_state
    return ResolvedLocation(city, state)


def state_for_city(city: str | None) -> str | None:
    if not city:
        return None
    cities, _ = _gazetteer()
    entry = cities.get(city.casefold())
    return entry["state"] if entry else None


# A place name is short, and it is not a sentence, a number, a link or a refusal.
# These are the answers that must NOT be stored as a city, because a complaint that
# says the incident happened in "I don't remember" is worse than one that says
# nothing.
# Checked per token, not against the whole answer: "yes correct" is not the city
# of Yes Correct, and neither is "theek hai". A real place name contains none of
# these words.
_NOT_A_PLACE = {
    "yes", "no", "nope", "none", "na", "nil", "ok", "okay", "unknown", "dunno",
    "correct", "right", "wrong", "sure", "fine", "true", "false", "thanks",
    "haan", "haa", "ji", "nahi", "nahin", "nhi", "pata", "malum", "skip",
    "sahi", "theek", "thik", "galat", "bilkul", "acha", "accha", "hai", "hoon",
    "हाँ", "हां", "नहीं", "नही", "जी", "पता", "मालूम", "छोड़ो",
    "सही", "ठीक", "गलत", "बिल्कुल", "हूँ", "हूं", "है",
}
_UNCERTAIN_MARKERS = (
    "pata nahi", "pata nhi", "malum nahi", "yaad nahi", "nahi pata", "not sure",
    "don't know", "dont know", "no idea", "prefer not", "skip",
    "पता नहीं", "मालूम नहीं", "याद नहीं", "नहीं बताना",
)
_PLACE_MAX_WORDS = 5
_PLACE_MAX_CHARS = 60


def looks_like_place_name(answer: str) -> bool:
    """Can this answer be written into the city field of a complaint?

    Deliberately permissive about *which* place: an unlisted town, a locality, a
    district - all of those are useful to an investigating officer and none of them
    are things this code should second-guess. It is strict only about answers that
    are plainly not a place at all.
    """
    text = " ".join(answer.split())
    if not text or len(text) > _PLACE_MAX_CHARS:
        return False
    lowered = text.casefold()
    if any(marker in lowered for marker in _UNCERTAIN_MARKERS):
        return False
    if any(marker in lowered for marker in ("http://", "https://", "www.", "@")):
        return False
    tokens = TOKEN_PATTERN.findall(lowered)
    if not tokens or len(text.split()) > _PLACE_MAX_WORDS:
        return False
    if any(token in _NOT_A_PLACE for token in tokens):
        return False
    # "9876543210" or "500" is an identifier or an amount that landed in the wrong
    # slot, not a place.
    if not any(len(token) >= 3 for token in tokens):
        return False
    return True


def resolve_answer(answer: str) -> ResolvedLocation:
    """The city and state to record from an answer to the location question.

    A recognised place wins, because it brings its state with it. Otherwise the
    citizen's own words become the city, which is the whole point: this question is
    asked precisely because the place may not be in any list.
    """
    resolved = resolve_location(answer)
    if not resolved.is_empty:
        return resolved
    if looks_like_place_name(answer):
        return ResolvedLocation(" ".join(answer.split()).title(), None)
    return ResolvedLocation(None, None)
