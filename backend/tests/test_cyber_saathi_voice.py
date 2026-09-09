import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import get_settings
from app.main import app
from app.schemas.cyber_saathi import LanguageCode, VoiceTranscription
from app.services.cyber_saathi_voice import (
    PreparedSpeechStream,
    SarvamVoiceAdapter,
    VoiceProviderError,
)


def configured_adapter() -> SarvamVoiceAdapter:
    settings = get_settings().model_copy(
        update={
            "voice_enabled": True,
            "sarvam_api_key": SecretStr("test-sarvam-key"),
        }
    )
    return SarvamVoiceAdapter(settings)


def test_voice_language_mapping_is_tolerant_and_code_mix_aware() -> None:
    assert configured_adapter().settings.sarvam_realtime_stt_model == "saaras:v4"
    assert SarvamVoiceAdapter.stt_options(LanguageCode.EN, realtime=True) == (
        "en-IN",
        "transcribe",
    )
    assert SarvamVoiceAdapter.stt_options(LanguageCode.HI, realtime=True) == (
        "hi-IN",
        "codemix",
    )
    assert SarvamVoiceAdapter.stt_options(LanguageCode.HINGLISH, realtime=True) == (
        "hi-IN",
        "codemix",
    )
    assert SarvamVoiceAdapter.stt_options(LanguageCode.MIXED, realtime=False) == (
        "unknown",
        "codemix",
    )
    assert SarvamVoiceAdapter.tts_language(LanguageCode.EN) == "en-IN"
    assert SarvamVoiceAdapter.tts_language(LanguageCode.HINGLISH) == "hi-IN"


def test_voice_capabilities_fail_closed_without_a_server_key() -> None:
    settings = get_settings().model_copy(
        update={"voice_enabled": True, "sarvam_api_key": None}
    )
    capabilities = SarvamVoiceAdapter(settings).capabilities()
    assert capabilities.enabled is True
    assert capabilities.configured is False
    assert capabilities.realtime_stt is False
    assert capabilities.streaming_tts is False


def test_capability_api_never_exposes_credentials() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/cyber-saathi/voice/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["provider"] == "sarvam"
    assert "key" not in response.text.casefold()


def test_rest_transcription_route_preserves_provider_metadata(monkeypatch) -> None:
    async def fake_transcribe(self, **kwargs):
        assert kwargs["language"] == LanguageCode.HINGLISH
        assert kwargs["content_type"] == "audio/webm"
        return VoiceTranscription(
            transcript="Mere UPI se 10,000 rupaye cut gaye",
            detected_language_code="hi-IN",
            language_probability=0.97,
            model="saaras:v4",
            stt_latency_ms=321.5,
        )

    monkeypatch.setattr(SarvamVoiceAdapter, "transcribe", fake_transcribe)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cyber-saathi/voice/transcriptions",
            data={"language": "HINGLISH"},
            files={"file": ("recording.webm", b"webm-audio", "audio/webm")},
        )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "transcript": "Mere UPI se 10,000 rupaye cut gaye",
        "detected_language_code": "hi-IN",
        "language_probability": 0.97,
        "provider": "sarvam",
        "model": "saaras:v4",
        "stt_latency_ms": 321.5,
    }


def test_streaming_tts_route_returns_audio_and_safe_latency_header(monkeypatch) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"first"
        yield b"second"

    async def fake_synthesize(self, **kwargs):
        assert kwargs == {"text": "Aap surakshit hain.", "language": LanguageCode.HI}
        return PreparedSpeechStream(chunks(), "audio/mpeg", 87.25)

    monkeypatch.setattr(SarvamVoiceAdapter, "synthesize", fake_synthesize)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cyber-saathi/voice/speech",
            json={"text": "Aap surakshit hain.", "language": "HI"},
        )
    assert response.status_code == 200
    assert response.content == b"firstsecond"
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["x-tts-first-audio-ms"] == "87.25"
    assert response.headers["cache-control"] == "no-store"


def test_provider_error_becomes_a_controlled_api_error(monkeypatch) -> None:
    async def unavailable(self, **kwargs):
        raise VoiceProviderError(
            "VOICE_PROVIDER_UNAVAILABLE",
            "Voice is unavailable. The conversation can continue through text.",
        )

    monkeypatch.setattr(SarvamVoiceAdapter, "synthesize", unavailable)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cyber-saathi/voice/speech",
            json={"text": "Please type instead.", "language": "EN"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "VOICE_PROVIDER_UNAVAILABLE"


def test_realtime_socket_reports_unavailable_without_losing_the_client() -> None:
    with TestClient(app) as client:
        with client.websocket_connect(
            "/api/v1/cyber-saathi/conversations/00000000-0000-0000-0000-000000000001/voice/transcriptions/stream?language=EN"
        ) as websocket:
            message = websocket.receive_json()
    assert message["event"] == "voice.error"
    assert message["code"] == "VOICE_PROVIDER_UNAVAILABLE"


def test_rest_adapter_rejects_unsupported_audio_before_network() -> None:
    async def exercise() -> None:
        with pytest.raises(VoiceProviderError) as caught:
            await configured_adapter().transcribe(
                audio=b"not audio",
                filename="voice.txt",
                content_type="text/plain",
                language=LanguageCode.EN,
            )
        assert caught.value.code == "UNSUPPORTED_AUDIO"

    asyncio.run(exercise())
