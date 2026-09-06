"""Provider-agnostic, bounded, safety-validated LLM gateway for Cyber Saathi."""

from __future__ import annotations

import argparse
import json
import re
import time
from difflib import SequenceMatcher
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, get_settings
from app.schemas.cyber_saathi import (
    ConversationState,
    CrimeDomain,
    Intent,
    LLMGenerationResult,
    LLMProvider,
    LLMProviderAttempt,
    LLMProviderHealth,
    LLMStructuredResponse,
    LLMWorkflowAction,
    ReportingMode,
    Urgency,
)


PROMPTS_PATH = Path(__file__).resolve().parents[1] / "data" / "cyber_saathi" / "llm_prompts.json"
MAX_RECENT_TURNS = 6
MAX_RECENT_TURN_CHARS = 420
MAX_OLDER_SUMMARY_CHARS = 900
MAX_KNOWLEDGE_CHARS = 2200
MAX_PLAYBOOK_CHARS = 1200
CHARS_PER_TOKEN_ESTIMATE = 4
STREAM_CHUNK_CHARS = 120

RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "urgency": {
            "type": "string",
            "enum": [urgency.value for urgency in Urgency],
        },
        "suggested_actions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
        "clarification_needed": {"type": "boolean"},
        "workflow_action": {
            "type": "string",
            "enum": [action.value for action in LLMWorkflowAction],
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "safety_flags": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 10,
        },
    },
    "required": [
        "answer",
        "confidence",
        "urgency",
        "suggested_actions",
        "clarification_needed",
        "workflow_action",
        "sources",
        "safety_flags",
    ],
    "additionalProperties": False,
}

# Gemini's generateContent responseSchema dialect rejects additionalProperties.
# Strict extra-field rejection still happens after generation in LLMStructuredResponse.
GEMINI_RESPONSE_JSON_SCHEMA = {
    key: value for key, value in RESPONSE_JSON_SCHEMA.items() if key != "additionalProperties"
}


class ProviderFailure(Exception):
    def __init__(self, status: str, *, retryable: bool | None = None) -> None:
        self.status = status
        self.retryable = status == "rate_limited" if retryable is None else retryable
        super().__init__(status)


class SafetyValidationFailure(Exception):
    def __init__(self, flags: list[str]) -> None:
        self.flags = flags
        super().__init__("LLM response failed safety validation")


@dataclass(frozen=True)
class GenerationProfile:
    temperature: float
    top_p: float
    max_output_tokens: int
    label: str


@dataclass(frozen=True)
class PromptPackage:
    system_prompt: str
    user_prompt: str
    estimated_input_tokens: int
    profile: GenerationProfile
    allowed_source_ids: tuple[str, ...]
    grounding_text: str


class ProviderAdapter(Protocol):
    provider: LLMProvider
    model: str

    @property
    def configured(self) -> bool: ...

    def generate(self, package: PromptPackage, timeout_seconds: float) -> str: ...

    def health_check(self, timeout_seconds: float) -> bool: ...


def _secret_value(secret: SecretStr | None) -> str:
    return secret.get_secret_value().strip() if secret is not None else ""


def _compact(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


@lru_cache(maxsize=1)
def _load_prompt_contract() -> dict[str, str]:
    payload = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    for field in ("version", "system_policy", "assistant_role", "output_rules"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"Cyber Saathi LLM prompt contract is missing {field}")
    return payload


class PromptAssembler:
    @staticmethod
    def _profile(state: ConversationState, settings: Settings) -> GenerationProfile:
        if state.incident.urgency in {Urgency.HIGH, Urgency.CRITICAL}:
            return GenerationProfile(
                settings.llm_safety_temperature,
                settings.llm_top_p,
                settings.llm_max_output_tokens,
                "safety",
            )
        if state.incident.intent in {Intent.SEEK_GUIDANCE, Intent.GENERAL_AWARENESS}:
            return GenerationProfile(
                settings.llm_explanation_temperature,
                settings.llm_top_p,
                settings.llm_max_output_tokens,
                "explanation",
            )
        return GenerationProfile(
            settings.llm_conversation_temperature,
            settings.llm_top_p,
            settings.llm_max_output_tokens,
            "conversation",
        )

    @staticmethod
    def build(
        *,
        state: ConversationState,
        user_message: str,
        knowledge_context: str,
        source_ids: list[str],
        deterministic_playbook: str,
        settings: Settings,
    ) -> PromptPackage:
        contract = _load_prompt_contract()
        history = state.turns[:-1] if state.turns and state.turns[-1].role == "user" else state.turns
        older = history[:-MAX_RECENT_TURNS]
        recent = history[-MAX_RECENT_TURNS:]
        older_summary = _compact(
            " | ".join(
                f"{turn.role}: {_compact(turn.content, 140)}" for turn in older
            ),
            MAX_OLDER_SUMMARY_CHARS,
        ) or "none"
        recent_text = "\n".join(
            f"{turn.role}: {_compact(turn.content, MAX_RECENT_TURN_CHARS)}"
            for turn in recent
        ) or "none"
        incident = state.incident.model_dump(mode="json", exclude={"summary"})
        incident["reporting_mode"] = state.reporting_mode.value
        incident["pending_confirmation_count"] = len(state.pending_confirmation_entity_ids)
        incident["turn_purpose"] = (
            state.last_turn_purpose.value if state.last_turn_purpose is not None else None
        )
        active_record = next(
            (item for item in state.incidents if item.id == state.active_incident_id),
            None,
        )
        if active_record is not None:
            incident["completed_actions"] = active_record.completed_actions
            incident["blocked_actions"] = active_record.blocked_actions
            incident["report_missing_fields"] = active_record.report_preparation.missing_required_keys
        user_prompt = "\n\n".join(
            (
                "[INCIDENT_STATE]\n" + json.dumps(incident, ensure_ascii=False),
                "[OLDER_TURN_SUMMARY]\n" + older_summary,
                "[RECENT_CONVERSATION]\n" + recent_text,
                "[CURRENT_USER_MESSAGE]\n" + _compact(user_message, 1200),
                "[RETRIEVED_KNOWLEDGE]\n" + (_compact(knowledge_context, MAX_KNOWLEDGE_CHARS) or "none"),
                "[ALLOWED_SOURCE_CHUNK_IDS]\n" + (", ".join(source_ids[:3]) or "none"),
                "[DETERMINISTIC_PLAYBOOK]\n" + (_compact(deterministic_playbook, MAX_PLAYBOOK_CHARS) or "none"),
                "[OUTPUT_SCHEMA]\n" + json.dumps(RESPONSE_JSON_SCHEMA, ensure_ascii=False),
                "[OUTPUT_RULES]\n" + contract["output_rules"],
            )
        )
        system_prompt = contract["system_policy"] + "\n\n" + contract["assistant_role"]
        estimated_tokens = (len(system_prompt) + len(user_prompt) + 3) // CHARS_PER_TOKEN_ESTIMATE
        if estimated_tokens > settings.llm_max_input_tokens:
            raise ValueError("Cyber Saathi LLM context exceeds the configured token budget")
        return PromptPackage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            estimated_input_tokens=estimated_tokens,
            profile=PromptAssembler._profile(state, settings),
            allowed_source_ids=tuple(source_ids[:3]),
            grounding_text="\n".join((user_message, knowledge_context, deterministic_playbook)),
        )


class LLMResponseValidator:
    PROHIBITED_PATTERNS = {
        "government_access_claim": re.compile(
            r"\b(i (?:checked|accessed)|we (?:checked|accessed)|connected to)\b.{0,45}\b(police|government|bank|aadhaar|telecom|upi)\b",
            re.IGNORECASE,
        ),
        "criminality_claim": re.compile(
            r"\b(confirmed|definitely|proven|is)\s+(?:a\s+)?criminal\b",
            re.IGNORECASE,
        ),
        "recovery_guarantee": re.compile(
            r"(?:\b(guarantee(?:d)?|certain)\b.{0,35}\b(refund|recovery|money back|recover)\b|\b(refund|recovery|money back|recover)\b.{0,35}\b(guarantee(?:d)?|certain)\b)",
            re.IGNORECASE,
        ),
        "unsafe_freeze_instruction": re.compile(
            r"\bfreeze (?:your |the )?(?:entire|whole) bank account\b",
            re.IGNORECASE,
        ),
        "internal_prompt_disclosure": re.compile(
            r"\b(system prompt|hidden instruction|internal prompt|developer message)\b",
            re.IGNORECASE,
        ),
        "authority_action_claim": re.compile(
            r"\b(police|law enforcement|government|bank|payment provider|telecom provider)\b.{0,60}\b(has|have|already|will|is|are)\s+(successfully\s+)?(filed|registered|blocked|frozen|recovered|arrested|traced|located|dispatched|investigating)\b",
            re.IGNORECASE,
        ),
        "legal_conclusion": re.compile(
            r"\b(this|that|it|you|they|the suspect|the accused)\b.{0,30}\b(is illegal|are illegal|is guilty|are guilty|violates section|must be arrested|legally entitled)\b",
            re.IGNORECASE,
        ),
        "emergency_procedure_claim": re.compile(
            r"(?:\b(official|mandatory|guaranteed)\s+(emergency|police)\s+(procedure|protocol|response)\b|\b(police|ambulance|authorities)\s+(are|is|have been)\s+(on the way|dispatched)\b)",
            re.IGNORECASE,
        ),
        "secret_exposure": re.compile(
            r"(?:\b(?:GEMINI|GROK|NVIDIA|XAI)_API_KEY\s*=|\bAIza[0-9A-Za-z_-]{20,}|\bxai-[0-9A-Za-z_-]{10,}|\bnvapi-[0-9A-Za-z_-]{10,})",
            re.IGNORECASE,
        ),
    }
    ANONYMOUS_IDENTITY_REQUEST = re.compile(
        r"(?:\b(provide|share|enter|send|tell me)\b.{0,35}\b(aadhaar|pan|full name|home address|your email|your mobile|your phone number)\b|(?:अपना|आपका|आपकी|aapka|apna).{0,25}(?:आधार|पैन|पूरा नाम|घर का पता|मोबाइल नंबर|फोन नंबर|aadhaar|pan|full name|address|mobile number|phone number).{0,25}(?:बताएं|बताइए|दें|साझा करें|batayein|share karein|dein))",
        re.IGNORECASE,
    )
    AMOUNT_TOKEN_PATTERN = re.compile(
        r"(?:₹|\b(?:rs\.?|inr)\s*)\s*[\d,]+(?:\.\d{1,2})?",
        re.IGNORECASE,
    )
    PHONE_TOKEN_PATTERN = re.compile(
        r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
    )
    ADDRESS_TOKEN_PATTERN = re.compile(
        r"\b[A-Za-z0-9._-]{2,}@[A-Za-z0-9.-]{2,}\b",
        re.IGNORECASE,
    )
    URL_TOKEN_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
    TRANSACTION_TOKEN_PATTERN = re.compile(
        r"\b(?:txn|transaction|utr|reference|ref|order)\s*(?:id|number|no\.?)?\s*[:=#-]?\s*((?=[A-Z0-9-]*\d)[A-Z0-9-]{6,})\b",
        re.IGNORECASE,
    )
    HELPLINE_TOKEN_PATTERN = re.compile(r"(?<!\d)(?:1930|112|1098)(?!\d)")

    @classmethod
    def _critical_tokens(cls, text: str) -> set[tuple[str, str]]:
        tokens: set[tuple[str, str]] = set()
        for value in cls.AMOUNT_TOKEN_PATTERN.findall(text):
            tokens.add(("amount", re.sub(r"[^0-9.]", "", value)))
        for value in cls.PHONE_TOKEN_PATTERN.findall(text):
            digits = re.sub(r"\D", "", value)
            tokens.add(("phone", digits[-10:]))
        for value in cls.ADDRESS_TOKEN_PATTERN.findall(text):
            tokens.add(("address", value.casefold().rstrip(".,)")))
        for value in cls.URL_TOKEN_PATTERN.findall(text):
            tokens.add(("url", value.casefold().rstrip(".,)")))
        for value in cls.TRANSACTION_TOKEN_PATTERN.findall(text):
            tokens.add(("transaction", re.sub(r"[^a-z0-9]", "", value.casefold())))
        for value in cls.HELPLINE_TOKEN_PATTERN.findall(text):
            tokens.add(("helpline", value))
        return tokens

    @classmethod
    def validate(
        cls,
        response: LLMStructuredResponse,
        *,
        state: ConversationState,
        package: PromptPackage,
    ) -> None:
        combined = "\n".join((response.answer, *response.suggested_actions))
        flags = [
            flag
            for flag, pattern in cls.PROHIBITED_PATTERNS.items()
            if pattern.search(combined)
        ]
        if state.reporting_mode == ReportingMode.ANONYMOUS and cls.ANONYMOUS_IDENTITY_REQUEST.search(combined):
            flags.append("anonymous_identity_leak")
        if package.allowed_source_ids:
            if not response.sources:
                flags.append("grounded_source_required")
            elif not set(response.sources).issubset(package.allowed_source_ids):
                flags.append("unsupported_source")
        elif response.sources:
            flags.append("unsupported_source")
        if (
            state.reporting_mode == ReportingMode.ANONYMOUS
            and response.workflow_action == LLMWorkflowAction.REPORT_CRIME
            and state.incident.crime_domain
            not in {
                CrimeDomain.CHILD_SAFETY,
                CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
            }
        ):
            flags.append("anonymous_workflow_violation")
        if (
            state.incident.urgency in {Urgency.HIGH, Urgency.CRITICAL}
            and response.urgency not in {Urgency.HIGH, Urgency.CRITICAL}
        ):
            flags.append("urgency_downgrade")
        if not cls._critical_tokens(combined).issubset(
            cls._critical_tokens(package.grounding_text)
        ):
            flags.append("critical_entity_mismatch")
        normalized_answer = " ".join(re.findall(r"[a-z0-9\u0900-\u097f]+", response.answer.casefold()))
        if len(normalized_answer.split()) >= 8:
            recent_answers = [
                turn.content
                for turn in state.turns
                if turn.role == "assistant"
            ][-3:]
            for earlier in recent_answers:
                normalized_earlier = " ".join(
                    re.findall(r"[a-z0-9\u0900-\u097f]+", earlier.casefold())
                )
                if normalized_earlier and SequenceMatcher(
                    None, normalized_answer, normalized_earlier
                ).ratio() >= 0.82:
                    flags.append("repetitive_response")
                    break
        if flags:
            raise SafetyValidationFailure(sorted(set(flags)))


class GeminiAdapter:
    provider = LLMProvider.GEMINI

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.model = settings.gemini_model
        self.base_url = settings.gemini_base_url
        self.api_key = settings.gemini_api_key
        self.client = client or httpx.Client()

    @property
    def configured(self) -> bool:
        return bool(_secret_value(self.api_key))

    def generate(self, package: PromptPackage, timeout_seconds: float) -> str:
        response = self.client.post(
            f"{self.base_url}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": _secret_value(self.api_key)},
            json={
                "systemInstruction": {"parts": [{"text": package.system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": package.user_prompt}]}],
                "generationConfig": {
                    "temperature": package.profile.temperature,
                    "topP": package.profile.top_p,
                    "maxOutputTokens": package.profile.max_output_tokens,
                    "responseMimeType": "application/json",
                    "responseSchema": GEMINI_RESPONSE_JSON_SCHEMA,
                },
            },
            timeout=timeout_seconds,
        )
        _raise_for_provider_status(response)
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderFailure("malformed_output") from error

    def health_check(self, timeout_seconds: float) -> bool:
        response = self.client.get(
            f"{self.base_url}/models/{self.model}",
            headers={"x-goog-api-key": _secret_value(self.api_key)},
            timeout=timeout_seconds,
        )
        return response.status_code == 200


class OpenAICompatibleAdapter:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        model: str,
        base_url: str,
        api_key: SecretStr | None,
        strict_schema: bool,
        client: httpx.Client | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.strict_schema = strict_schema
        self.client = client or httpx.Client()

    @property
    def configured(self) -> bool:
        return bool(_secret_value(self.api_key))

    def generate(self, package: PromptPackage, timeout_seconds: float) -> str:
        response_format: dict[str, object]
        if self.strict_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "cyber_saathi_response",
                    "strict": True,
                    "schema": RESPONSE_JSON_SCHEMA,
                },
            }
        else:
            response_format = {"type": "json_object"}
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {_secret_value(self.api_key)}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": package.system_prompt},
                    {"role": "user", "content": package.user_prompt},
                ],
                "temperature": package.profile.temperature,
                "top_p": package.profile.top_p,
                "max_tokens": package.profile.max_output_tokens,
                "response_format": response_format,
                "stream": False,
            },
            timeout=timeout_seconds,
        )
        _raise_for_provider_status(response)
        try:
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError
            return content
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderFailure("malformed_output") from error

    def health_check(self, timeout_seconds: float) -> bool:
        response = self.client.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {_secret_value(self.api_key)}"},
            timeout=timeout_seconds,
        )
        if response.status_code != 200:
            return False
        try:
            models = response.json()["data"]
        except (KeyError, TypeError, ValueError):
            return False
        if not isinstance(models, list):
            return False
        for item in models:
            if not isinstance(item, dict):
                continue
            aliases = item.get("aliases", [])
            if item.get("id") == self.model or (
                isinstance(aliases, list) and self.model in aliases
            ):
                return True
        return False


def _raise_for_provider_status(response: httpx.Response) -> None:
    if response.status_code == 429:
        raise ProviderFailure("rate_limited")
    if response.status_code >= 400:
        raise ProviderFailure(
            "provider_error", retryable=response.status_code >= 500
        )


class MultiProviderLLMGateway:
    def __init__(
        self,
        *,
        settings: Settings,
        adapters: dict[LLMProvider, ProviderAdapter] | None = None,
    ) -> None:
        self.settings = settings
        self.order = self._provider_order(settings)
        self.adapters = adapters or self._default_adapters(settings)

    @staticmethod
    def _provider_order(settings: Settings) -> tuple[LLMProvider, ...]:
        configured = (
            LLMProvider(settings.llm_primary_provider),
            LLMProvider(settings.llm_secondary_provider),
            LLMProvider(settings.llm_tertiary_provider),
        )
        return tuple(dict.fromkeys(configured))

    @staticmethod
    def _default_adapters(settings: Settings) -> dict[LLMProvider, ProviderAdapter]:
        return {
            LLMProvider.GEMINI: GeminiAdapter(settings),
            LLMProvider.GROK: OpenAICompatibleAdapter(
                provider=LLMProvider.GROK,
                model=settings.grok_model,
                base_url=settings.grok_base_url,
                api_key=settings.grok_api_key,
                strict_schema=True,
            ),
            LLMProvider.NVIDIA: OpenAICompatibleAdapter(
                provider=LLMProvider.NVIDIA,
                model=settings.nvidia_model,
                base_url=settings.nvidia_base_url,
                api_key=settings.nvidia_api_key,
                strict_schema=False,
            ),
        }

    def generate(
        self,
        *,
        state: ConversationState,
        user_message: str,
        knowledge_context: str = "",
        source_ids: list[str] | None = None,
        deterministic_playbook: str = "",
    ) -> LLMGenerationResult:
        started = time.perf_counter()
        if not self.settings.llm_enabled:
            return LLMGenerationResult(
                deterministic_fallback=True,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
            )
        source_ids = source_ids or []
        try:
            package = PromptAssembler.build(
                state=state,
                user_message=user_message,
                knowledge_context=knowledge_context,
                source_ids=source_ids,
                deterministic_playbook=deterministic_playbook,
                settings=self.settings,
            )
        except ValueError:
            return LLMGenerationResult(
                fallback_used=True,
                deterministic_fallback=True,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
            )

        attempts: list[LLMProviderAttempt] = []
        configured_seen = 0
        for provider in self.order:
            adapter = self.adapters[provider]
            if not adapter.configured:
                attempts.append(
                    LLMProviderAttempt(
                        provider=provider,
                        model=adapter.model,
                        status="not_configured",
                        latency_ms=0,
                    )
                )
                continue
            configured_seen += 1
            retry_count = 0
            while True:
                elapsed = time.perf_counter() - started
                remaining = self.settings.llm_total_timeout_seconds - elapsed
                if remaining <= 0:
                    attempts.append(
                        LLMProviderAttempt(
                            provider=provider,
                            model=adapter.model,
                            status="deadline_exceeded",
                            latency_ms=0,
                        )
                    )
                    break
                attempt_started = time.perf_counter()
                retryable = False
                try:
                    raw = adapter.generate(
                        package,
                        min(self.settings.llm_provider_timeout_seconds, remaining),
                    )
                    if raw.lstrip().startswith("```"):
                        raise ProviderFailure("malformed_output")
                    response = LLMStructuredResponse.model_validate_json(raw)
                    LLMResponseValidator.validate(response, state=state, package=package)
                except httpx.TimeoutException:
                    status = "timeout"
                except httpx.HTTPError:
                    status = "provider_error"
                except ProviderFailure as error:
                    status = error.status
                    retryable = error.retryable
                except (ValidationError, json.JSONDecodeError, ValueError, TypeError):
                    status = "malformed_output"
                except SafetyValidationFailure:
                    status = "safety_rejected"
                else:
                    latency = round((time.perf_counter() - attempt_started) * 1000, 3)
                    attempts.append(
                        LLMProviderAttempt(
                            provider=provider,
                            model=adapter.model,
                            status="success",
                            latency_ms=latency,
                        )
                    )
                    return LLMGenerationResult(
                        response=response,
                        provider=provider,
                        model=adapter.model,
                        fallback_used=provider != self.order[0],
                        latency_ms=round((time.perf_counter() - started) * 1000, 3),
                        attempts=attempts,
                    )
                latency = round((time.perf_counter() - attempt_started) * 1000, 3)
                attempts.append(
                    LLMProviderAttempt(
                        provider=provider,
                        model=adapter.model,
                        status=status,
                        latency_ms=latency,
                    )
                )
                if not retryable or retry_count >= self.settings.llm_max_retries:
                    break
                retry_count += 1

        return LLMGenerationResult(
            fallback_used=bool(configured_seen),
            deterministic_fallback=True,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            attempts=attempts,
        )

    def stream(self, **kwargs: object) -> Iterator[str]:
        """Yield only a fully validated answer, avoiding unsafe partial-token display."""
        result = self.generate(**kwargs)  # type: ignore[arg-type]
        if result.response is None:
            return
        answer = result.response.answer
        for offset in range(0, len(answer), STREAM_CHUNK_CHARS):
            yield answer[offset : offset + STREAM_CHUNK_CHARS]

    def health_check(self) -> list[LLMProviderHealth]:
        results: list[LLMProviderHealth] = []
        for provider in self.order:
            adapter = self.adapters[provider]
            if not self.settings.llm_enabled or not adapter.configured:
                results.append(
                    LLMProviderHealth(
                        provider=provider,
                        model=adapter.model,
                        status="not_configured",
                        latency_ms=0,
                    )
                )
                continue
            started = time.perf_counter()
            try:
                available = adapter.health_check(self.settings.llm_provider_timeout_seconds)
            except (httpx.HTTPError, ProviderFailure, ValueError, TypeError):
                available = False
            results.append(
                LLMProviderHealth(
                    provider=provider,
                    model=adapter.model,
                    status="available" if available else "unavailable",
                    latency_ms=round((time.perf_counter() - started) * 1000, 3),
                )
            )
        return results

    def healthCheck(self) -> list[LLMProviderHealth]:  # noqa: N802
        return self.health_check()


@lru_cache(maxsize=1)
def get_llm_gateway() -> MultiProviderLLMGateway:
    return MultiProviderLLMGateway(settings=get_settings())


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Cyber Saathi LLM provider health")
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Call only configured provider health endpoints; never prints credentials",
    )
    args = parser.parse_args()
    if not args.health_check:
        parser.error("Use --health-check to make the bounded provider health request")
    result = [item.model_dump(mode="json") for item in get_llm_gateway().health_check()]
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
