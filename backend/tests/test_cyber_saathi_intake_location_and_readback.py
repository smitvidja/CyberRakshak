"""Where the citizen is, and what they agreed to before anything was filed.

Three changes are covered here:

- the city and state are asked for, and recognised beyond the twenty-three cities
  that used to be hard-coded;
- the facts collected are read back and confirmed before a packet is prepared;
- each question carries one line of guidance, so the intake teaches while it
  collects.

The location tests are deliberately adversarial about false positives. A wrong city
on a police complaint sends it to the wrong cybercrime unit, which is worse than a
blank field, so the cases that must NOT match matter more than the ones that must.
"""

from __future__ import annotations

import pytest

from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    EntityType,
    LanguageCode,
)
from app.services.cyber_saathi_locations import (
    looks_like_place_name,
    resolve_answer,
    resolve_location,
    state_for_city,
)
from app.services.cyber_saathi_service import QUESTION_GUIDANCE, CyberSaathiService


# --------------------------------------------------------------- the gazetteer

@pytest.mark.parametrize(
    ("message", "city", "state"),
    [
        ("I live in Bilaspur and lost money", "Bilaspur", "Chhattisgarh"),
        ("मैं जामताड़ा में हूँ", "Jamtara", "Jharkhand"),
        ("the fraud happened in navi mumbai", "Navi Mumbai", "Maharashtra"),
        ("main new delhi me rehta hu", "New Delhi", "Delhi"),
        ("I am from Kozhikode", "Kozhikode", "Kerala"),
    ],
)
def test_cities_far_beyond_the_old_list_are_recognised_with_their_state(
    message: str, city: str, state: str
) -> None:
    """Twenty-three cities had a name and nine had a state; everywhere else in
    India produced an empty city field."""
    resolved = resolve_location(message)
    assert resolved.city == city
    assert resolved.state == state


def test_a_state_named_without_a_city_is_still_recorded() -> None:
    """It still routes the complaint to the right state cybercrime cell."""
    resolved = resolve_location("yeh Chhattisgarh me hua")
    assert resolved.state == "Chhattisgarh"
    assert resolved.city is None


def test_the_longer_name_wins_over_the_shorter_one_it_contains() -> None:
    assert resolve_location("new delhi").city == "New Delhi"
    assert resolve_location("navi mumbai").city == "Navi Mumbai"


@pytest.mark.parametrize(
    "message",
    [
        "mera paisa gaya",          # "gaya" is the Hindi for "went", and a city in Bihar
        "paise chale gaye",
        "wo banda mujhe dhamka raha hai",   # "banda" is "guy", and a city in UP
        "maine sagar dekha",
        "puri khatam ho gayi",
    ],
)
def test_a_town_that_is_also_an_ordinary_word_is_not_matched_mid_sentence(
    message: str,
) -> None:
    """"mera paisa gaya" - my money went - used to put Gaya, Bihar on the complaint
    of a citizen who had never been there."""
    assert resolve_location(message).city is None


@pytest.mark.parametrize(
    ("message", "city"),
    [
        ("I live in Gaya", "Gaya"),
        ("main Gaya me rehta hu", "Gaya"),
        ("I am from Puri", "Puri"),
        ("Gaya", "Gaya"),
    ],
)
def test_the_same_town_is_matched_when_the_sentence_places_you_there(
    message: str, city: str
) -> None:
    assert resolve_location(message).city == city


def test_every_known_city_carries_a_state() -> None:
    """A city without a state is half a location, and the old table had nine of
    thirty-six."""
    for name in ("Bilaspur", "Kozhikode", "Jamtara", "Port Blair", "Itanagar"):
        assert state_for_city(name) is not None


# ------------------------------------------------- answers to the question itself

def test_a_town_in_no_list_is_still_accepted_as_the_answer() -> None:
    """The point of asking is that the place may not be in any list. Refusing to
    record it would make the question pointless."""
    resolved = resolve_answer("Tundla")
    assert resolved.city == "Tundla"
    assert resolved.state is None


@pytest.mark.parametrize(
    "answer",
    ["yes correct", "theek hai", "sahi hai", "pata nahi", "no idea", "ok", "9876543210", "https://x.test"],
)
def test_an_answer_that_is_not_a_place_is_never_written_into_the_city_field(
    answer: str,
) -> None:
    """"yes correct" reached the free-text fallback and was recorded as the city of
    Yes Correct."""
    assert resolve_answer(answer).city is None
    assert not looks_like_place_name(answer) or resolve_answer(answer).city is None


# --------------------------------------------------------- the intake behaviour

def _walk_to_key(state, key: str, limit: int = 12):
    """Answer questions until `key` is pending, or give up."""
    for _ in range(limit):
        if state.pending_question is None or state.pending_question.key == key:
            return state
        answer = "no" if state.pending_question.answer_type.value == "yes_no" else "not provided"
        state = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=answer, state=state)
        ).state
    return state


def test_the_citizen_is_asked_where_and_when_when_they_have_not_said() -> None:
    """Neither was ever asked. They were picked up only if volunteered, so a
    complaint from someone who did not mention them carried neither."""
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Someone keeps sending abusive threats on Instagram", state=state
        ),
    ).state
    state = _walk_to_key(state, "incident_where_when")
    assert state.pending_question is not None
    assert state.pending_question.key == "incident_where_when"


def test_the_question_is_skipped_when_the_citizen_already_said_both() -> None:
    """Asking for what they already told you is what made this read like a form."""
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Kal Mumbai mein mujhe fake call aaya aur 45000 transfer karwa liye",
            state=state,
        ),
    ).state
    for _ in range(12):
        if state.pending_question is None:
            break
        assert state.pending_question.key != "incident_where_when"
        answer = "haan" if state.pending_question.answer_type.value == "yes_no" else "pata nahi"
        state = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=answer, state=state)
        ).state


def test_the_answer_reaches_the_complaint_as_city_and_state() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Someone keeps sending abusive threats on Instagram", state=state
        ),
    ).state
    state = _walk_to_key(state, "incident_where_when")
    assert state.pending_question is not None
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="Kozhikode", state=state)
    ).state
    locations = [
        entity.normalized_value
        for entity in state.incident.entities
        if entity.type == EntityType.LOCATION
    ]
    assert "Kozhikode" in locations


def test_nothing_is_prepared_until_the_citizen_confirms_the_read_back() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Someone keeps sending abusive threats on Instagram", state=state
        ),
    ).state
    state = _walk_to_key(state, "incident_where_when")
    assert state.pending_question is not None
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="Kozhikode", state=state)
    ).state

    state = _walk_to_key(state, "confirm_summary")
    assert state.pending_question is not None
    assert state.pending_question.key == "confirm_summary"
    # The read-back quotes what was collected rather than asking a bare "is this ok?",
    # including the state inferred from the city the citizen named.
    readback = state.turns[-1].content
    assert "Kozhikode" in readback
    assert "Kerala" in readback


def test_saying_no_to_the_read_back_asks_what_to_correct_instead_of_filing() -> None:
    """A citizen who has just said the summary is wrong must not be handed a packet
    built from it."""
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Someone keeps sending abusive threats on Instagram", state=state
        ),
    ).state
    state = _walk_to_key(state, "confirm_summary")
    assert state.pending_question is not None

    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="no that is wrong", state=state)
    ).state
    assert state.pending_question is not None
    assert state.pending_question.key == "summary_correction"

    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="it was on Telegram, not Instagram", state=state),
    ).state
    # The correction is taken and the read-back is shown again, so the citizen can
    # see what their correction changed.
    assert state.pending_question is not None
    assert state.pending_question.key == "confirm_summary"


def test_a_question_carries_one_line_of_guidance_with_it() -> None:
    """Turns two onward used to be bare questions - the intake collected without
    ever telling the citizen anything."""
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Someone keeps sending abusive threats on Instagram", state=state
        ),
    ).state
    state = _walk_to_key(state, "incident_where_when")
    assert state.pending_question is not None
    guidance = QUESTION_GUIDANCE["incident_where_when"][LanguageCode.EN]
    shown = state.turns[-1].content
    # Only the half still missing may be asked, so accept either wording.
    assert guidance in shown or QUESTION_GUIDANCE["incident_location"][LanguageCode.EN] in shown


def test_every_guidance_line_exists_in_all_three_languages() -> None:
    """A missing translation would silently drop the guidance for Hindi speakers."""
    for key, translations in QUESTION_GUIDANCE.items():
        for language in (LanguageCode.EN, LanguageCode.HI, LanguageCode.HINGLISH):
            assert translations.get(language), f"{key} has no {language.value} line"
