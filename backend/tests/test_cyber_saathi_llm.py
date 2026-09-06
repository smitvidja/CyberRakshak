import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    ConversationState,
    ConversationTurn,
    CrimeDomain,
    GroundingStatus,
    IncidentState,
    Intent,
    LanguageCode,
    LLMGenerationResult,
    LLMProvider,
    LLMProviderAttempt,
    LLMStructuredResponse,
    LLMWorkflowAction,
    ReportingMode,
    Urgency,
)
from app.services import cyber_saathi_service as service_module
from app.services.cyber_saathi_llm import (
    GeminiAdapter,
    LLMResponseValidator,
    MultiProviderLLMGateway,
    OpenAICompatibleAdapter,
    PromptAssembler,
    ProviderFailure,
    SafetyValidationFailure,
)
from app.services.cyber_saathi_service import CyberSaathiService


def settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+psycopg://u:p@localhost:5432/d",
        "secret_key": "test-only-secret-key-that-is-long-enough",
        "gemini_api_key": None,
        "grok_api_key": None,
        "nvidia_api_key": None,
        "llm_enabled": True,
        "llm_max_retries": 1,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def state(*, anonymous: bool = False, urgency: Urgency = Urgency.MEDIUM) -> ConversationState:
    return ConversationState(
        language=LanguageCode.EN,
        reporting_mode=ReportingMode.ANONYMOUS if anonymous else ReportingMode.IDENTIFIED,
        incident=IncidentState(
            intent=Intent.SEEK_GUIDANCE,
            crime_domain=CrimeDomain.CHILD_SAFETY if anonymous else CrimeDomain.PHISHING_SCAM,
            urgency=urgency,
            language=LanguageCode.EN,
            response_language=LanguageCode.EN,
            confidence=0.9,
            needs_clarification=False,
        ),
        turns=[
            ConversationTurn(role="assistant", content="How can I help?", language=LanguageCode.EN),
            ConversationTurn(role="user", content="I received a phishing link", language=LanguageCode.EN),
        ],
    )


def structured(
    *,
    answer: str = "Do not open the suspicious link. Preserve the message as evidence.",
    source: str | None = "source:1:1",
    workflow_action: str = "none",
) -> str:
    return json.dumps(
        {
            "answer": answer,
            "confidence": 0.9,
            "urgency": "medium",
            "suggested_actions": ["Preserve the original message."],
            "clarification_needed": False,
            "workflow_action": workflow_action,
            "sources": [source] if source else [],
            "safety_flags": [],
        }
    )


class FakeAdapter:
    def __init__(
        self,
        provider: LLMProvider,
        outcomes: list[str | Exception],
        *,
        configured: bool = True,
    ) -> None:
        self.provider = provider
        self.model = f"{provider.value}-test"
        self.outcomes = outcomes
        self._configured = configured
        self.calls = 0

    @property
    def configured(self) -> bool:
        return self._configured

    def generate(self, _package, _timeout_seconds: float) -> str:
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def health_check(self, _timeout_seconds: float) -> bool:
        return self._configured


def adapters(*items: FakeAdapter) -> dict[LLMProvider, FakeAdapter]:
    return {item.provider: item for item in items}


def test_provider_order_changes_through_configuration_only() -> None:
    configured = settings(
        llm_primary_provider="grok",
        llm_secondary_provider="gemini",
        llm_tertiary_provider="nvidia",
    )
    grok = FakeAdapter(LLMProvider.GROK, [structured()])
    gemini = FakeAdapter(LLMProvider.GEMINI, [structured()])
    nvidia = FakeAdapter(LLMProvider.NVIDIA, [structured()])
    gateway = MultiProviderLLMGateway(
        settings=configured,
        adapters=adapters(grok, gemini, nvidia),
    )

    result = gateway.generate(
        state=state(),
        user_message="How should I handle this phishing link?",
        knowledge_context="Official guidance says not to open suspicious links.",
        source_ids=["source:1:1"],
    )

    assert result.provider == LLMProvider.GROK
    assert result.fallback_used is False
    assert grok.calls == 1
    assert gemini.calls == 0


def test_provider_configuration_rejects_unknown_names_and_insecure_urls() -> None:
    with pytest.raises(ValidationError, match="LLM provider"):
        settings(llm_primary_provider="unknown-provider")
    with pytest.raises(ValidationError, match="HTTPS"):
        settings(grok_base_url="http://api.example.test/v1")


def test_timeout_falls_back_to_secondary_without_retrying_timeout() -> None:
    configured = settings()
    gemini = FakeAdapter(LLMProvider.GEMINI, [httpx.ReadTimeout("timeout")])
    grok = FakeAdapter(LLMProvider.GROK, [structured()])
    nvidia = FakeAdapter(LLMProvider.NVIDIA, [structured()])
    gateway = MultiProviderLLMGateway(
        settings=configured,
        adapters=adapters(gemini, grok, nvidia),
    )

    result = gateway.generate(
        state=state(),
        user_message="How should I handle this phishing link?",
        knowledge_context="Official guidance says not to open suspicious links.",
        source_ids=["source:1:1"],
    )

    assert [attempt.status for attempt in result.attempts] == ["timeout", "success"]
    assert result.provider == LLMProvider.GROK
    assert result.fallback_used is True
    assert gemini.calls == 1


def test_rate_limit_retries_once_then_uses_next_provider() -> None:
    gemini = FakeAdapter(
        LLMProvider.GEMINI,
        [ProviderFailure("rate_limited"), ProviderFailure("rate_limited")],
    )
    grok = FakeAdapter(LLMProvider.GROK, [structured()])
    nvidia = FakeAdapter(LLMProvider.NVIDIA, [structured()])
    gateway = MultiProviderLLMGateway(
        settings=settings(),
        adapters=adapters(gemini, grok, nvidia),
    )

    result = gateway.generate(
        state=state(),
        user_message="How should I handle this phishing link?",
        knowledge_context="Official guidance says not to open suspicious links.",
        source_ids=["source:1:1"],
    )

    assert [attempt.status for attempt in result.attempts] == [
        "rate_limited",
        "rate_limited",
        "success",
    ]
    assert gemini.calls == 2
    assert result.provider == LLMProvider.GROK


def test_malformed_secondary_failure_and_tertiary_success_are_bounded() -> None:
    gemini = FakeAdapter(LLMProvider.GEMINI, ["not-json"])
    grok = FakeAdapter(
        LLMProvider.GROK,
        [ProviderFailure("provider_error", retryable=True)] * 2,
    )
    nvidia = FakeAdapter(LLMProvider.NVIDIA, [structured()])
    gateway = MultiProviderLLMGateway(
        settings=settings(),
        adapters=adapters(gemini, grok, nvidia),
    )

    result = gateway.generate(
        state=state(),
        user_message="How should I handle this phishing link?",
        knowledge_context="Official guidance says not to open suspicious links.",
        source_ids=["source:1:1"],
    )

    assert result.provider == LLMProvider.NVIDIA
    assert [attempt.status for attempt in result.attempts] == [
        "malformed_output",
        "provider_error",
        "provider_error",
        "success",
    ]
    assert result.latency_ms < 2500


def test_safety_rejection_falls_back_and_all_provider_failure_is_deterministic() -> None:
    unsafe = structured(answer="I confirmed this phone owner is a criminal.")
    providers = [
        FakeAdapter(LLMProvider.GEMINI, [unsafe]),
        FakeAdapter(LLMProvider.GROK, [unsafe]),
        FakeAdapter(LLMProvider.NVIDIA, [unsafe]),
    ]
    gateway = MultiProviderLLMGateway(settings=settings(), adapters=adapters(*providers))

    result = gateway.generate(
        state=state(),
        user_message="Is this phishing message criminal?",
        knowledge_context="The identifier is only reported, not proven criminal.",
        source_ids=["source:1:1"],
    )

    assert result.response is None
    assert result.deterministic_fallback is True
    assert result.fallback_used is True
    assert [attempt.status for attempt in result.attempts] == ["safety_rejected"] * 3


def test_unconfigured_nvidia_is_implemented_but_skipped() -> None:
    providers = [
        FakeAdapter(LLMProvider.GEMINI, [structured()], configured=False),
        FakeAdapter(LLMProvider.GROK, [structured()], configured=False),
        FakeAdapter(LLMProvider.NVIDIA, [structured()], configured=False),
    ]
    gateway = MultiProviderLLMGateway(settings=settings(), adapters=adapters(*providers))

    result = gateway.generate(state=state(), user_message="phishing help")
    health = gateway.healthCheck()

    assert result.deterministic_fallback is True
    assert [attempt.status for attempt in result.attempts] == ["not_configured"] * 3
    assert [item.status for item in health] == ["not_configured"] * 3
    assert providers[2].calls == 0


def test_context_is_bounded_and_older_turns_are_compacted() -> None:
    conversation = state()
    conversation.turns = [
        ConversationTurn(
            role="user" if index % 2 else "assistant",
            content=f"turn-{index} " + ("detail " * 150),
            language=LanguageCode.EN,
        )
        for index in range(20)
    ]
    package = PromptAssembler.build(
        state=conversation,
        user_message="Please explain phishing safety",
        knowledge_context="official phishing guidance " * 100,
        source_ids=["source:1:1"],
        deterministic_playbook="",
        settings=settings(),
    )

    assert package.estimated_input_tokens <= 3000
    assert len(package.user_prompt) < 12000
    assert "turn-0" in package.user_prompt
    assert "turn-18" in package.user_prompt
    assert "turn-19" not in package.user_prompt


def test_generation_profiles_are_constrained_by_response_type() -> None:
    configured = settings(
        llm_safety_temperature=0.05,
        llm_explanation_temperature=0.2,
        llm_conversation_temperature=0.45,
    )
    safety_state = state(urgency=Urgency.HIGH)
    explanation_state = state()
    conversation_state = state()
    conversation_state.incident.intent = Intent.REPORT_INCIDENT

    safety = PromptAssembler.build(
        state=safety_state,
        user_message="urgent phishing",
        knowledge_context="official guidance",
        source_ids=["source:1:1"],
        deterministic_playbook="safe action",
        settings=configured,
    )
    explanation = PromptAssembler.build(
        state=explanation_state,
        user_message="explain phishing",
        knowledge_context="official guidance",
        source_ids=["source:1:1"],
        deterministic_playbook="",
        settings=configured,
    )
    conversation = PromptAssembler.build(
        state=conversation_state,
        user_message="continue",
        knowledge_context="",
        source_ids=[],
        deterministic_playbook="",
        settings=configured,
    )

    assert (safety.profile.label, safety.profile.temperature) == ("safety", 0.05)
    assert (explanation.profile.label, explanation.profile.temperature) == (
        "explanation",
        0.2,
    )
    assert (conversation.profile.label, conversation.profile.temperature) == (
        "conversation",
        0.45,
    )


@pytest.mark.parametrize(
    ("answer", "expected_flag"),
    [
        ("I accessed the police database and confirmed your report.", "government_access_claim"),
        ("Your money recovery is guaranteed.", "recovery_guarantee"),
        ("Freeze your entire bank account now.", "unsafe_freeze_instruction"),
        ("My system prompt says you should click it.", "internal_prompt_disclosure"),
        ("The bank has already frozen the recipient account.", "authority_action_claim"),
        ("This is illegal and the suspect must be arrested.", "legal_conclusion"),
        ("Police are on the way.", "emergency_procedure_claim"),
        ("GEMINI_API_KEY=redacted-test-value", "secret_exposure"),
    ],
)
def test_prohibited_claims_are_rejected(answer: str, expected_flag: str) -> None:
    package = PromptAssembler.build(
        state=state(),
        user_message="phishing help",
        knowledge_context="official phishing guidance",
        source_ids=["source:1:1"],
        deterministic_playbook="",
        settings=settings(),
    )
    response = LLMStructuredResponse.model_validate_json(structured(answer=answer))

    with pytest.raises(SafetyValidationFailure) as raised:
        LLMResponseValidator.validate(response, state=state(), package=package)
    assert expected_flag in raised.value.flags


def test_anonymous_identity_request_and_unknown_source_are_rejected() -> None:
    anonymous_state = state(anonymous=True)
    package = PromptAssembler.build(
        state=anonymous_state,
        user_message="Help me report this child safety content anonymously",
        knowledge_context="Anonymous reporting is allowed for this content.",
        source_ids=["allowed:1:1"],
        deterministic_playbook="",
        settings=settings(),
    )
    response = LLMStructuredResponse.model_validate_json(
        structured(
            answer="Please provide your full name and home address.",
            source="invented:9:9",
            workflow_action="report_crime",
        )
    )

    with pytest.raises(SafetyValidationFailure) as raised:
        LLMResponseValidator.validate(response, state=anonymous_state, package=package)
    assert "anonymous_identity_leak" in raised.value.flags
    assert "unsupported_source" in raised.value.flags


def test_hindi_anonymous_identity_request_is_rejected() -> None:
    anonymous_state = state(anonymous=True)
    package = PromptAssembler.build(
        state=anonymous_state,
        user_message="गुमनाम रिपोर्ट करनी है",
        knowledge_context="गुमनाम रिपोर्ट में पहचान नहीं ली जाती।",
        source_ids=["allowed:1:1"],
        deterministic_playbook="",
        settings=settings(),
    )
    response = LLMStructuredResponse.model_validate_json(
        structured(
            answer="अपना पूरा नाम और आधार नंबर बताइए।",
            source="allowed:1:1",
            workflow_action="report_crime",
        )
    )

    with pytest.raises(SafetyValidationFailure) as raised:
        LLMResponseValidator.validate(response, state=anonymous_state, package=package)
    assert "anonymous_identity_leak" in raised.value.flags


def test_substantially_repeated_assistant_answer_is_rejected() -> None:
    current_state = state()
    repeated_answer = "Do not open the suspicious link. Preserve the message as evidence."
    current_state.turns.append(
        ConversationTurn(
            role="assistant", content=repeated_answer, language=LanguageCode.EN
        )
    )
    package = PromptAssembler.build(
        state=current_state,
        user_message="I already preserved it, what should I do now?",
        knowledge_context="official phishing guidance",
        source_ids=["source:1:1"],
        deterministic_playbook="Give the next missing action.",
        settings=settings(),
    )
    response = LLMStructuredResponse.model_validate_json(
        structured(answer=repeated_answer)
    )

    with pytest.raises(SafetyValidationFailure) as raised:
        LLMResponseValidator.validate(
            response, state=current_state, package=package
        )
    assert "repetitive_response" in raised.value.flags


@pytest.mark.parametrize(
    ("grounded_value", "invented_value"),
    [
        ("transaction ID TXNABC123", "transaction ID TXNXYZ999"),
        ("UPI ID citizen@upi", "UPI ID attacker@upi"),
        ("Use only the official reporting portal", "Call 1930 immediately"),
    ],
)
def test_extended_critical_entity_mismatch_is_rejected(
    grounded_value: str, invented_value: str
) -> None:
    current_state = state()
    package = PromptAssembler.build(
        state=current_state,
        user_message=grounded_value,
        knowledge_context="Preserve the original evidence.",
        source_ids=["source:1:1"],
        deterministic_playbook="",
        settings=settings(),
    )
    response = LLMStructuredResponse.model_validate_json(
        structured(answer=f"Preserve {invented_value}.")
    )

    with pytest.raises(SafetyValidationFailure) as raised:
        LLMResponseValidator.validate(response, state=current_state, package=package)
    assert "critical_entity_mismatch" in raised.value.flags


def test_gemini_and_openai_compatible_adapters_parse_structured_content() -> None:
    raw = structured()

    def handler(request: httpx.Request) -> httpx.Response:
        assert any("provider-live-credential" in value for value in request.headers.values())
        if "generativelanguage" in str(request.url):
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": raw}]}}]},
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": raw}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configured = settings(
        gemini_api_key=SecretStr("provider-live-credential"),
        grok_api_key=SecretStr("provider-live-credential"),
        nvidia_api_key=SecretStr("provider-live-credential"),
    )
    package = PromptAssembler.build(
        state=state(),
        user_message="phishing help",
        knowledge_context="official phishing guidance",
        source_ids=["source:1:1"],
        deterministic_playbook="",
        settings=configured,
    )

    assert GeminiAdapter(configured, client).generate(package, 1) == raw
    assert (
        OpenAICompatibleAdapter(
            provider=LLMProvider.GROK,
            model=configured.grok_model,
            base_url=configured.grok_base_url,
            api_key=configured.grok_api_key,
            strict_schema=True,
            client=client,
        ).generate(package, 1)
        == raw
    )
    assert (
        OpenAICompatibleAdapter(
            provider=LLMProvider.NVIDIA,
            model=configured.nvidia_model,
            base_url=configured.nvidia_base_url,
            api_key=configured.nvidia_api_key,
            strict_schema=False,
            client=client,
        ).generate(package, 1)
        == raw
    )
    assert "provider-live-credential" not in repr(configured)


def test_gemini_wire_schema_omits_unsupported_additional_properties() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": structured()}]}}
                ]
            },
        )

    configured = settings(gemini_api_key=SecretStr("provider-live-credential"))
    package = PromptAssembler.build(
        state=state(),
        user_message="phishing help",
        knowledge_context="official phishing guidance",
        source_ids=["source:1:1"],
        deterministic_playbook="",
        settings=configured,
    )

    GeminiAdapter(
        configured, httpx.Client(transport=httpx.MockTransport(handler))
    ).generate(package, 1)

    generation_config = captured["generationConfig"]
    assert isinstance(generation_config, dict)
    response_schema = generation_config["responseSchema"]
    assert isinstance(response_schema, dict)
    assert "additionalProperties" not in response_schema


def test_openai_compatible_health_requires_configured_model_in_catalog() -> None:
    configured = settings(grok_api_key=SecretStr("provider-live-credential"))

    def client_with(models: list[dict[str, object]]) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json={"data": models})
            )
        )

    available = OpenAICompatibleAdapter(
        provider=LLMProvider.GROK,
        model=configured.grok_model,
        base_url=configured.grok_base_url,
        api_key=configured.grok_api_key,
        strict_schema=True,
        client=client_with([{"id": "versioned", "aliases": [configured.grok_model]}]),
    )
    missing = OpenAICompatibleAdapter(
        provider=LLMProvider.GROK,
        model=configured.grok_model,
        base_url=configured.grok_base_url,
        api_key=configured.grok_api_key,
        strict_schema=True,
        client=client_with([{"id": "different-model", "aliases": []}]),
    )

    assert available.health_check(1) is True
    assert missing.health_check(1) is False


def test_buffered_stream_never_yields_unvalidated_provider_output() -> None:
    providers = [
        FakeAdapter(LLMProvider.GEMINI, [structured()]),
        FakeAdapter(LLMProvider.GROK, [structured()]),
        FakeAdapter(LLMProvider.NVIDIA, [structured()]),
    ]
    gateway = MultiProviderLLMGateway(settings=settings(), adapters=adapters(*providers))

    chunks = list(
        gateway.stream(
            state=state(),
            user_message="phishing help",
            knowledge_context="official phishing guidance",
            source_ids=["source:1:1"],
        )
    )

    assert "".join(chunks) == "Do not open the suspicious link. Preserve the message as evidence."


def test_conversation_uses_validated_llm_answer_and_safe_observability(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class SuccessfulGateway:
        def generate(self, **kwargs) -> LLMGenerationResult:
            captured.update(kwargs)
            return LLMGenerationResult(
                response=LLMStructuredResponse.model_validate_json(
                    structured(source="certin_digital_safety_compass:1:1")
                ),
                provider=LLMProvider.GEMINI,
                model="gemini-test",
                fallback_used=False,
                latency_ms=12,
                attempts=[
                    LLMProviderAttempt(
                        provider=LLMProvider.GEMINI,
                        model="gemini-test",
                        status="success",
                        latency_ms=12,
                    )
                ],
            )

    monkeypatch.setattr(service_module, "get_llm_gateway", lambda: SuccessfulGateway())
    conversation = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        conversation.id,
        ConversationMessageRequest(
            message="How can I stay safe from phishing websites and fake links?",
            state=conversation,
        ),
    )
    turn = response.state.turns[-1]

    assert turn.content.startswith("Do not open")
    assert turn.grounding_status == GroundingStatus.GROUNDED
    assert turn.llm_provider == LLMProvider.GEMINI
    assert turn.llm_model == "gemini-test"
    assert turn.llm_latency_ms == 12
    assert captured["deterministic_playbook"]
    assert turn.sources[0].chunk_id == "certin_digital_safety_compass:1:1"
    assert response.mock_provider is False


def test_urgent_financial_playbook_never_calls_llm(monkeypatch) -> None:
    class ForbiddenGateway:
        def generate(self, **_kwargs):
            raise AssertionError("Urgent deterministic safety must not call an LLM")

    monkeypatch.setattr(service_module, "get_llm_gateway", lambda: ForbiddenGateway())
    conversation = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        conversation.id,
        ConversationMessageRequest(
            message="My bank was debited right now and I lost 5000 rupees",
            state=conversation,
        ),
    )

    assert response.state.turns[-1].kind.value == "safety"
    assert "OTP/PIN/password" in response.state.turns[-1].content


def test_financial_progress_followup_uses_llm_after_deterministic_first_response(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    class ProgressGateway:
        def generate(self, **kwargs) -> LLMGenerationResult:
            calls.append(kwargs)
            return LLMGenerationResult(
                response=LLMStructuredResponse.model_validate_json(
                    structured(
                        answer="Good, the bank is informed. Save its reference number and call 1930 for a recent loss.",
                        source=None,
                    )
                ),
                provider=LLMProvider.GEMINI,
                model="gemini-test",
                latency_ms=11,
            )

    monkeypatch.setattr(service_module, "get_llm_gateway", lambda: ProgressGateway())
    conversation = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    first = CyberSaathiService.reply(
        conversation.id,
        ConversationMessageRequest(
            message="Mere bank se aaj unauthorized transaction hua",
            state=conversation,
        ),
    ).state
    assert calls == []

    followup = CyberSaathiService.reply(
        first.id,
        ConversationMessageRequest(
            message="Maine bank ko call kar diya, ab kya karu?", state=first
        ),
    )

    assert len(calls) == 1
    turn = followup.state.turns[-1]
    assert turn.llm_provider == LLMProvider.GEMINI
    assert turn.kind.value == "message"
    assert "?" in turn.content
    assert "OTP/PIN/password" not in turn.content
