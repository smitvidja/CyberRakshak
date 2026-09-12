"""Intake quality: answer what was asked, and never ask what was already said.

Every case here is taken from a real Hindi conversation a citizen walked through.
The failures it exposed were not edge cases - they were the ordinary path for
anyone typing in Devanagari.
"""

from __future__ import annotations

import pytest

from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    ConversationState,
    ConversationTurn,
    CrimeDomain,
    LanguageCode,
)
from app.services.cyber_saathi_conversation import infer_reporting_for
from app.services.cyber_saathi_service import CyberSaathiService


def _start(language: LanguageCode = LanguageCode.HI) -> ConversationState:
    return CyberSaathiService.start(ConversationCreate(language=language)).state


def _say(state: ConversationState, message: str) -> ConversationState:
    return CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state


def _pending(state: ConversationState) -> str | None:
    return state.pending_question.key if state.pending_question else None


def _actions(state: ConversationState) -> list[str]:
    record = CyberSaathiService._active_record(state)
    return list(record.completed_actions) if record else []


# ------------------------------------------------------- yes / no as a sentence

@pytest.mark.parametrize(
    ("message", "expected"),
    [
        # Answers are written as sentences. Matching the whole string against
        # {"nahi", "नहीं"} meant none of these counted as an answer at all.
        ("नहीं हम अभी कोई शारीरिक खतरे में नहीं हैं।", "no"),
        ("नहीं नहीं है कोई खतरा।", "no"),
        ("नहीं मैंने ब्लॉक नहीं किया", "no"),
        ("nahi maine kuch save nahi kiya", "no"),
        ("हाँ मैंने उसको block भी किया और report भी कर दिया।", "yes"),
        ("yes I have saved everything", "yes"),
        ("जी हाँ", "yes"),
        ("haan kar diya", "yes"),
        # Uncertainty contains a negation word but is not a "no".
        ("मुझे पता नहीं है", "uncertain"),
        ("pata nahi", "uncertain"),
        # Neither. These are the ones that used to be silently stored as answers.
        ("रुको मैं अभी screenshot खींच लेती हूँ", "other"),
        ("यह 5 सितंबर को हुआ था, मैं मुंबई में हूँ", "other"),
    ],
)
def test_a_yes_or_no_written_as_a_sentence_is_understood(message: str, expected: str) -> None:
    assert CyberSaathiService._expected_answer_class(message) == expected


def test_a_negation_anywhere_outranks_an_affirmation() -> None:
    """"haan lekin maine block nahi kiya" is a no to the question that was asked."""
    assert CyberSaathiService._expected_answer_class("haan lekin maine block nahi kiya") == "no"


# --------------------------------------------- a non-answer must not advance

def test_saying_you_are_about_to_get_evidence_is_not_a_yes() -> None:
    """The defect this prevents: "ruko main abhi screenshot kheench leti hoon" was
    stored as "yes, evidence preserved" - a yes the citizen never gave."""
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर बहुत परेशान कर रहा है")
    asked = _pending(state)
    assert asked is not None

    state = _say(state, "रुको मैं अभी screenshot खींच लेती हूँ")

    assert _pending(state) == asked, "the question must stay open"
    assert f"answer:{asked}:yes" not in _actions(state)


def test_a_citizen_gathering_proof_is_pointed_at_the_upload_control() -> None:
    """It had the Upload evidence button on screen and never mentioned it."""
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर बहुत परेशान कर रहा है")
    state = _say(state, "रुको मैं अभी screenshot खींच लेती हूँ")

    assert "Upload evidence" in state.turns[-1].content


def test_an_unclear_answer_is_only_queried_once() -> None:
    """Holding the question open must not turn into nagging - the citizen handing
    over a suspect's number got two rounds of "haan ya nahi" before this."""
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर बहुत परेशान कर रहा है")
    asked = _pending(state)

    state = _say(state, "रुको मैं अभी screenshot खींच लेती हूँ")
    assert _pending(state) == asked
    first_reask = state.turns[-1].content

    # A second message that still does not answer it. (A message carrying an
    # identifier goes to entity confirmation instead, which is its own path.)
    state = _say(state, "अच्छा")

    assert state.turns[-1].content != first_reask, "it must not ask the same way twice"
    assert _pending(state) != asked, "after one clarification it must move on"


# ------------------------------------- never ask what the citizen already said

def test_a_block_described_in_the_first_message_is_not_asked_about_again() -> None:
    state = _start()
    state = _say(
        state,
        "मुझे एक आदमी WhatsApp पर परेशान कर रहा है, मैंने उसे block भी कर दिया",
    )
    state = _say(state, "नहीं कोई खतरा नहीं है")

    assert "answered:platform_block_report" in _actions(state)
    assert _pending(state) != "platform_block_report"


def test_the_words_may_drift_apart_and_still_count() -> None:
    """"block bhi kiya" and "ब्लॉक भी कर दिया" are the same statement; a fixed
    phrase list matched neither."""
    for message in ("block bhi kiya", "ब्लॉक भी कर दिया", "maine use blocked kar diya"):
        assert CyberSaathiService._states_completed_action(
            message, ("block", "blocked", "ब्लॉक")
        ), message


def test_a_denied_action_is_never_recorded_as_done() -> None:
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर परेशान कर रहा है, मैंने ब्लॉक नहीं किया")
    state = _say(state, "नहीं कोई खतरा नहीं है")

    assert "answer:platform_block_report:yes" not in _actions(state)


# ---------------------------------------------- who was affected, in Devanagari

@pytest.mark.parametrize(
    ("message", "expected"),
    [
        # Every marker used to be romanised, so a Devanagari citizen was always
        # UNKNOWN and was asked "you, your child, or someone else?" every turn.
        ("मुझे एक आदमी बहुत परेशान कर रहा है", "SELF"),
        ("मेरे अकाउंट से पैसे कट गए", "SELF"),
        ("मेरी बेटी को कोई परेशान कर रहा है", "CHILD"),
        ("मेरी बहन के साथ यह हुआ", "OTHER"),
        ("someone is harassing me", "SELF"),
        ("someone morphed my photo", "SELF"),
    ],
)
def test_who_was_affected_is_understood_in_either_script(message: str, expected: str) -> None:
    state = ConversationState(language=LanguageCode.HI)
    state.turns.append(ConversationTurn(role="user", content=message, language=LanguageCode.HI))
    assert infer_reporting_for(state)[0] == expected


def test_addressing_the_assistant_is_not_a_statement_about_the_victim() -> None:
    """"tell me what to do" must not be read as "it happened to me"."""
    state = ConversationState(language=LanguageCode.EN)
    state.turns.append(
        ConversationTurn(role="user", content="tell me what to do", language=LanguageCode.EN)
    )
    assert infer_reporting_for(state)[0] == "UNKNOWN"


def test_a_hindi_citizen_is_not_asked_who_was_affected_after_saying_so() -> None:
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर परेशान कर रहा है")
    state = _say(state, "नहीं कोई खतरा नहीं है")

    replies = " ".join(turn.content for turn in state.turns if turn.role != "user")
    assert "आपके बच्चे के साथ" not in replies, "it was already told this happened to her"


def test_a_fact_volunteered_while_answering_something_else_is_noticed() -> None:
    """Inference used to run only on the branch that asks the next question.

    So a citizen who answered the danger question and mentioned the block in the
    same breath was asked about the block a turn later anyway.
    """
    state = _start()
    state = _say(state, "मुझे एक आदमी WhatsApp पर परेशान कर रहा है")
    assert _pending(state) == "immediate_danger"

    state = _say(state, "नहीं कोई खतरा नहीं है, मैंने उसे block भी कर दिया")

    assert "answered:platform_block_report" in _actions(state)
    assert _pending(state) != "platform_block_report"


# ------------------------------------------- take everything the message offers

RICH_FIRST_MESSAGE = (
    "मुझे एक आदमी WhatsApp पर परेशान कर रहा है, गंदे मैसेज भेजता है। "
    "मैंने उसे block कर दिया और screenshot भी ले लिए हैं। "
    "यह 5 सितंबर को हुआ था और मैं मुंबई में हूँ।"
)


def test_one_rich_message_answers_several_questions_at_once() -> None:
    """A person reads a paragraph and takes all of it in. This used to take one
    fact per turn even when the first message contained four."""
    state = _start()
    state = _say(state, RICH_FIRST_MESSAGE)

    answered = {a.split(":")[1] for a in _actions(state) if a.startswith("answered:")}
    assert {"platform_and_profile", "platform_block_report", "harassment_evidence_preserved"} <= answered


def test_the_date_and_city_in_that_message_are_kept() -> None:
    state = _start()
    state = _say(state, RICH_FIRST_MESSAGE)
    kinds = {entity.type.value for entity in state.incident.entities}
    assert {"date", "location"} <= kinds


def test_only_what_cannot_be_known_from_the_message_is_still_asked() -> None:
    """Immediate danger and how she wants to be named are genuinely unknowable
    from the text. Everything else in that paragraph was already taken."""
    state = _start()
    state = _say(state, RICH_FIRST_MESSAGE)

    asked = []
    for answer in ("नहीं कोई खतरा नहीं है", "गुमनाम रहना है", "हाँ", "हाँ"):
        if state.pending_question is None:
            break
        asked.append(state.pending_question.key)
        state = _say(state, answer)

    assert state.pending_question is None, "intake did not finish"
    assert len(asked) <= 2, f"still asking for things the message already said: {asked}"
    assert "immediate_danger" in asked


@pytest.mark.parametrize(
    "message",
    [
        # Hindi inflects for number and gender; one spelling per verb is not enough.
        "screenshot भी ले लिए हैं",
        "मैंने स्क्रीनशॉट रख लिए हैं",
        "screenshot save kar liya",
        "i have screenshots",
        "I already saved the proof",
    ],
)
def test_saying_you_have_the_evidence_counts_however_it_is_phrased(message: str) -> None:
    from app.services.cyber_saathi_service import FLOW_ACTION_SUBJECTS

    assert CyberSaathiService._states_completed_action(
        message, FLOW_ACTION_SUBJECTS["harassment_evidence_preserved"]
    ), message


def test_wider_verb_coverage_does_not_swallow_a_denial() -> None:
    from app.services.cyber_saathi_service import FLOW_ACTION_SUBJECTS

    assert not CyberSaathiService._states_completed_action(
        "मैंने स्क्रीनशॉट नहीं लिए", FLOW_ACTION_SUBJECTS["harassment_evidence_preserved"]
    )
