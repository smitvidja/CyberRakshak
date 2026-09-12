"""Conversation quality: never blank, never robotic, and the choice a victim is owed."""

from __future__ import annotations

import pytest

from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    ConversationState,
    CrimeDomain,
    LanguageCode,
    ReportingMode,
)
from app.services import cyber_saathi_phrasing as phrasing
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_understanding import UnderstandingEngine


def _start(language: LanguageCode = LanguageCode.HI) -> ConversationState:
    return CyberSaathiService.start(ConversationCreate(language=language)).state


def _say(state: ConversationState, message: str) -> ConversationState:
    return CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state


def _replies(state: ConversationState) -> list[str]:
    return [turn.content for turn in state.turns if turn.role != "user"]


# ------------------------------------------------------------ never go blank

def test_an_empty_retrieval_still_gives_real_guidance() -> None:
    """"मुझे पर्याप्त आधिकारिक मार्गदर्शन नहीं मिला" must never reach a citizen.

    Retrieval finding nothing is our problem, not theirs, and a frightened person
    told that is left with nothing at the moment they most need something. The
    domain playbook is reviewed guidance we already hold.
    """
    answer = CyberSaathiService._domain_safety_copy(
        CrimeDomain.ONLINE_HARASSMENT, LanguageCode.HI
    )
    assert "मार्गदर्शन नहीं मिला" not in answer
    assert answer.strip()


def test_even_an_unknown_domain_asks_something_useful() -> None:
    """With no domain it degrades to a question, not an admission of emptiness."""
    answer = CyberSaathiService._domain_safety_copy(CrimeDomain.UNKNOWN, LanguageCode.HI)
    assert "?" in answer


# ------------------------------------------------------------ never robotic

def test_the_intake_does_not_announce_its_own_bookkeeping() -> None:
    """It used to open every turn with "अगला सवाल:" - literally "Next question:"."""
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर परेशान कर रहा है")
    state = _say(state, "नहीं कोई खतरा नहीं है")
    state = _say(state, "हाँ screenshot ले लिए")

    joined = " ".join(_replies(state))
    assert "अगला सवाल" not in joined
    assert "Next question" not in joined


def test_consecutive_turns_do_not_open_identically() -> None:
    """One fixed sentence per category still reads like a machine by the third turn."""
    state = _start()
    state.incident.crime_domain = CrimeDomain.ONLINE_HARASSMENT
    record = CyberSaathiService._active_record(state)
    seen = []
    for index in range(3):
        record.completed_actions.append(f"answered:slot{index}")
        seen.append(
            CyberSaathiService._acknowledge_and_ask(state, "slot", "yes", "क्या हुआ?")
        )
    assert len(set(seen)) > 1, f"the same opening every turn: {seen}"


def test_a_danger_answer_is_acknowledged_the_right_way_round() -> None:
    """"No danger" is relief; "yes" is not something to be cheerful about."""
    state = _start()
    state.incident.crime_domain = CrimeDomain.ONLINE_HARASSMENT
    safe = CyberSaathiService._acknowledge_and_ask(state, "immediate_danger", "no", "आगे?")
    unsafe = CyberSaathiService._acknowledge_and_ask(state, "immediate_danger", "yes", "आगे?")
    assert safe != unsafe


# ------------------------------------------------- the model only picks words

@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        ("", "empty"),
        ("Theek hai.", "not a question"),
        ("ok?", "far shorter than the question it replaces"),
        ("x" * 400, "longer than one question could be"),
    ],
)
def test_a_bad_rewrite_is_rejected(candidate: str, reason: str) -> None:
    question = "Did you preserve the original messages, dates and screenshots before blocking?"
    assert not phrasing._acceptable(candidate, question), reason


def test_a_good_rewrite_is_accepted() -> None:
    question = "Did you preserve the original messages, dates and screenshots before blocking?"
    candidate = "Before you blocked them, were you able to save the messages, dates and screenshots?"
    assert phrasing._acceptable(candidate, question)


def test_phrasing_is_off_unless_an_operator_turns_it_on() -> None:
    """Default keeps every intake turn deterministic, with no per-turn provider call."""
    assert (
        phrasing.phrase_next_question(
            question="क्या आपने स्क्रीनशॉट सुरक्षित किए?",
            language="HI",
            opening="ठीक है।",
            crime_domain="online_harassment",
        )
        is None
    )


def test_a_phrasing_failure_never_costs_the_citizen_their_answer(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cyber_saathi_service.phrase_next_question",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    state = _start()
    # A provider that throws must not take the citizen's answer down with it.
    answer = CyberSaathiService._acknowledge_and_ask(state, "slot", "yes", "क्या हुआ?")
    assert "क्या हुआ?" in answer

    # And when it simply declines, the deterministic sentence stands.
    monkeypatch.setattr(
        "app.services.cyber_saathi_service.phrase_next_question", lambda **kwargs: None
    )
    assert "क्या हुआ?" in CyberSaathiService._acknowledge_and_ask(state, "slot", "yes", "क्या हुआ?")


# -------------------------------------------- the choice a victim is owed

def test_a_harassment_report_is_asked_how_they_want_to_be_named() -> None:
    """The product has supported anonymous reporting all along and the side panel
    offers it. The conversation never asked, so a woman reporting harassment was
    never told she had the choice."""
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर परेशान कर रहा है, मैंने उसे block कर दिया")
    for answer in ("नहीं कोई खतरा नहीं है", "उसका profile @abc hai", "हाँ screenshot ले लिए"):
        state = _say(state, answer)
        if state.pending_question and state.pending_question.key == "reporting_mode_choice":
            break

    assert state.pending_question is not None
    assert state.pending_question.key == "reporting_mode_choice"
    assert "नाम" in state.turns[-1].content


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("गुमनाम रहना है", ReportingMode.ANONYMOUS),
        ("बिना नाम के", ReportingMode.ANONYMOUS),
        ("anonymous", ReportingMode.ANONYMOUS),
        ("अपना नाम देकर", ReportingMode.IDENTIFIED),
        ("naam batake karna hai", ReportingMode.IDENTIFIED),
        ("मुझे नहीं पता", None),
    ],
)
def test_the_naming_choice_is_understood_in_either_script(message, expected) -> None:
    assert CyberSaathiService._parse_reporting_mode(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "bina naam ke",
        # These carry BOTH forms - "apna naam" and a negation - so the order the
        # two lists are checked in decides the answer. Get it wrong and a citizen
        # asking to stay unnamed is recorded as having given her name.
        "apna naam nahi batana",
        "मैं अपना नाम नहीं बताना चाहती",
        "naam mat likhna mera",
    ],
)
def test_asking_not_to_be_named_is_never_read_as_giving_a_name(message: str) -> None:
    assert CyberSaathiService._parse_reporting_mode(message) == ReportingMode.ANONYMOUS


# ------------------------------------------------ date and city are captured

@pytest.mark.parametrize(
    ("message", "kinds"),
    [
        ("यह 5 सितंबर को हुआ था, मैं मुंबई में हूँ", {"date", "location"}),
        ("it happened on 12 August, I live in Pune", {"date", "location"}),
        ("मैं नई दिल्ली से हूँ, 20 अगस्त की बात है", {"date", "location"}),
    ],
)
def test_a_volunteered_date_and_city_are_kept(message: str, kinds: set[str]) -> None:
    """Both are real complaint fields. They used to be thrown away, and in
    Devanagari nothing was extracted at all."""
    found = {entity.type.value for entity in UnderstandingEngine.extract_entities(message)}
    assert kinds <= found, f"got {found}"


def test_the_longest_city_spelling_wins() -> None:
    """"नई दिल्ली" must not also register "दिल्ली" as a second, different city."""
    entities = UnderstandingEngine.extract_entities("मैं नई दिल्ली से हूँ")
    cities = [e.normalized_value or e.value for e in entities if e.type.value == "location"]
    assert cities == ["New Delhi"]
