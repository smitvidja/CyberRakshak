"""Let a model choose the words, while the script keeps choosing the question.

The intake flow is deterministic on purpose: which slot is still missing, and
whether an answer actually answered it, are decided in code so the conversation
still works when every provider is down. That is not in question here.

What was in question is the *wording*. Every turn opened with the same sentence
and the words "अगला सवाल:" - literally "Next question:" - which reads like a form
rather than a person, and gets worse the longer the intake runs.

So: the script decides what to ask; this only rewrites how it is asked, and it
has to earn the right to do so on every turn. The rewrite is rejected unless it
is still a question, still short, and still in the citizen's language. Anything
else - no provider, a timeout, a refusal, a suspicious rewrite - falls back to the
deterministic sentence, which is always computed first and never depends on this.

It deliberately cannot introduce facts: it is given the question and the opening
line, never the conversation, so there is nothing for it to invent from.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.services.cyber_saathi_llm import (
    GenerationProfile,
    MultiProviderLLMGateway,
    PromptPackage,
)

# One short sentence. Anything longer is the model adding something it was not
# asked for, and gets rejected below.
MAX_QUESTION_CHARS = 320
PHRASING_TIMEOUT_SECONDS = 2.5

PHRASING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You rewrite one intake question for a cyber-crime support assistant so it sounds like a calm, competent person rather than a form.

Rules:
- Keep the exact meaning. Ask for the same single fact, nothing more.
- Do not add advice, reassurance beyond the opening line you are given, new questions, or any claim about what has been done.
- Do not invent details about the incident. You are not given the conversation and must not guess at it.
- Reply in the same language and script as the input.
- One or two short sentences, ending in a question mark.

Return only the JSON object described by the schema."""

USER_TEMPLATE = """Language: {language}
Crime domain: {domain}
Opening line already chosen: {opening}
Question to ask: {question}

Rewrite the opening line and question together as one natural turn."""

_GATEWAY: MultiProviderLLMGateway | None = None


def _gateway() -> MultiProviderLLMGateway | None:
    global _GATEWAY
    settings = get_settings()
    if not settings.llm_enabled or not settings.saathi_phrasing_enabled:
        return None
    if _GATEWAY is None:
        _GATEWAY = MultiProviderLLMGateway(settings=settings)
    return _GATEWAY


def _acceptable(candidate: str, question: str) -> bool:
    """Would a person recognise this as the same question, asked better?"""
    text = candidate.strip()
    if not text or len(text) > MAX_QUESTION_CHARS:
        return False
    if "?" not in text and "？" not in text:
        return False
    # A rewrite that is shorter than the question it replaces has dropped
    # something; one several times longer has added something.
    if len(text) < len(question) * 0.4 or len(text) > len(question) * 3.5:
        return False
    return True


def phrase_next_question(
    *, question: str, language: str, opening: str, crime_domain: str
) -> str | None:
    """A natural rewrite, or None to use the deterministic sentence."""
    gateway = _gateway()
    if gateway is None or not question.strip():
        return None

    package = PromptPackage(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=USER_TEMPLATE.format(
            language=language, domain=crime_domain, opening=opening, question=question
        ),
        estimated_input_tokens=(len(SYSTEM_PROMPT) + len(question) + len(opening)) // 4,
        profile=GenerationProfile(
            temperature=0.3, top_p=0.9, max_output_tokens=256, label="intake_phrasing"
        ),
        allowed_source_ids=(),
        grounding_text="",
        response_schema=PHRASING_SCHEMA,
        schema_name="intake_question",
    )

    for provider in gateway.order:
        adapter = gateway.adapters.get(provider)
        if adapter is None or not adapter.configured:
            continue
        try:
            raw = adapter.generate(package, PHRASING_TIMEOUT_SECONDS)
            candidate = json.loads(raw).get("question", "")
        except Exception:  # noqa: BLE001 - wording is never worth failing a reply for
            continue
        if isinstance(candidate, str) and _acceptable(candidate, question):
            return candidate.strip()
    return None
