import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from urllib.parse import urlencode

import httpx
from fastapi import WebSocket, WebSocketDisconnect
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from app.core.config import Settings, get_settings
from app.schemas.cyber_saathi import LanguageCode, VoiceCapabilities, VoiceTranscription


LOGGER = logging.getLogger(__name__)
SUPPORTED_AUDIO_TYPES = {
    "audio/aac",
    "audio/flac",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/webm",
    "video/webm",
}
ALLOWED_CLIENT_EVENTS = {"audio_input", "speech_start", "speech_end", "flush", "end", "ping"}
ALLOWED_PROVIDER_EVENTS = {
    "session.begin",
    "vad.speech_start",
    "vad.speech_end",
    "transcript.partial",
    "transcript.final",
    "pong",
    "session.end",
    "error",
}


class VoiceProviderError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class PreparedSpeechStream:
    body: AsyncIterator[bytes]
    content_type: str
    first_audio_ms: float


class SarvamVoiceAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.voice_enabled and self.settings.sarvam_api_key)

    def capabilities(self) -> VoiceCapabilities:
        configured = self.configured
        return VoiceCapabilities(
            enabled=self.settings.voice_enabled,
            configured=configured,
            realtime_stt=configured,
            rest_stt_fallback=configured,
            streaming_tts=configured,
            stt_model=self.settings.sarvam_stt_model,
            realtime_stt_model=self.settings.sarvam_realtime_stt_model,
            tts_model=self.settings.sarvam_tts_model,
            max_recording_seconds=self.settings.voice_max_recording_seconds,
        )

    @staticmethod
    def stt_options(language: LanguageCode, *, realtime: bool) -> tuple[str, str]:
        if language == LanguageCode.EN:
            return "en-IN", "transcribe"
        if language in {LanguageCode.HI, LanguageCode.HINGLISH}:
            return "hi-IN", "codemix"
        return ("auto" if realtime else "unknown"), "codemix"

    @staticmethod
    def tts_language(language: LanguageCode) -> str:
        return "en-IN" if language == LanguageCode.EN else "hi-IN"

    def _api_key(self) -> str:
        if not self.configured or self.settings.sarvam_api_key is None:
            raise VoiceProviderError(
                "VOICE_PROVIDER_UNAVAILABLE",
                "Voice is unavailable. The conversation can continue through text.",
            )
        return self.settings.sarvam_api_key.get_secret_value()

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        content_type: str,
        language: LanguageCode,
    ) -> VoiceTranscription:
        key = self._api_key()
        if not audio or len(audio) > self.settings.voice_max_audio_bytes:
            raise VoiceProviderError("INVALID_AUDIO", "The recording is empty or too large.", 422)
        normalized_type = content_type.split(";", 1)[0].casefold()
        if normalized_type not in SUPPORTED_AUDIO_TYPES:
            raise VoiceProviderError("UNSUPPORTED_AUDIO", "This audio format is not supported.", 422)

        language_code, mode = self.stt_options(language, realtime=False)
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.settings.voice_provider_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.sarvam_base_url}/speech-to-text",
                    headers={"api-subscription-key": key},
                    data={
                        "language_code": language_code,
                        "model": self.settings.sarvam_stt_model,
                        "mode": mode,
                    },
                    files={"file": (filename or "recording.webm", audio, normalized_type)},
                )
        except httpx.TimeoutException as exc:
            raise VoiceProviderError("VOICE_TIMEOUT", "Voice transcription timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise VoiceProviderError("VOICE_NETWORK_ERROR", "Voice transcription could not be reached.") from exc

        self._raise_for_provider_status(response)
        try:
            payload = response.json()
            transcript = str(payload["transcript"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise VoiceProviderError("INVALID_VOICE_RESPONSE", "Voice transcription returned an invalid response.") from exc
        if not transcript:
            raise VoiceProviderError("NO_SPEECH_DETECTED", "No speech was detected in the recording.", 422)
        return VoiceTranscription(
            transcript=transcript[:4000],
            detected_language_code=payload.get("language_code"),
            language_probability=payload.get("language_probability"),
            model=self.settings.sarvam_stt_model,
            stt_latency_ms=round((perf_counter() - started) * 1000, 3),
        )

    async def synthesize(self, *, text: str, language: LanguageCode) -> PreparedSpeechStream:
        key = self._api_key()
        started = perf_counter()
        client = httpx.AsyncClient(timeout=self.settings.voice_provider_timeout_seconds)
        request = client.build_request(
            "POST",
            f"{self.settings.sarvam_base_url}/text-to-speech/stream",
            headers={"api-subscription-key": key},
            json={
                "text": text,
                "language_code": self.tts_language(language),
                "speaker": self.settings.sarvam_tts_speaker,
                "model": self.settings.sarvam_tts_model,
                "output_audio_codec": "mp3",
                "output_audio_bitrate": "64k",
                "pace": 1.0,
                "temperature": 0.4,
            },
        )
        try:
            response = await client.send(request, stream=True)
            self._raise_for_provider_status(response)
            iterator = response.aiter_bytes()
            first_chunk = await anext(iterator)
        except (httpx.TimeoutException, StopAsyncIteration) as exc:
            await client.aclose()
            raise VoiceProviderError("VOICE_TIMEOUT", "Speech synthesis timed out.", 504) from exc
        except httpx.HTTPError as exc:
            await client.aclose()
            raise VoiceProviderError("VOICE_NETWORK_ERROR", "Speech synthesis could not be reached.") from exc
        except VoiceProviderError:
            await response.aclose()
            await client.aclose()
            raise

        async def body() -> AsyncIterator[bytes]:
            try:
                yield first_chunk
                async for chunk in iterator:
                    if chunk:
                        yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return PreparedSpeechStream(
            body=body(),
            content_type=response.headers.get("content-type", "audio/mpeg").split(";", 1)[0],
            first_audio_ms=round((perf_counter() - started) * 1000, 3),
        )

    async def relay_realtime_transcription(self, client_socket: WebSocket, language: LanguageCode) -> None:
        await client_socket.accept()
        try:
            key = self._api_key()
        except VoiceProviderError as error:
            await client_socket.send_json({"event": "voice.error", "code": error.code, "message": error.message})
            await client_socket.close(code=1013)
            return

        language_code, mode = self.stt_options(language, realtime=True)
        query = urlencode(
            {
                "language_code": language_code,
                "model": self.settings.sarvam_realtime_stt_model,
                "mode": mode,
                "stream_type": "balanced",
                "endpointing": "manual",
                "encoding": "linear16",
                "sample_rate": 16000,
                "return_timestamps": "false",
            }
        )
        ws_base = self.settings.sarvam_base_url.replace("https://", "wss://", 1)
        provider_url = f"{ws_base}/speech-to-text-realtime/ws?{query}"
        try:
            async with connect(
                provider_url,
                additional_headers={"api-subscription-key": key},
                open_timeout=self.settings.voice_provider_timeout_seconds,
                ping_interval=15,
                ping_timeout=10,
                max_size=256 * 1024,
            ) as provider_socket:
                await client_socket.send_json({"event": "voice.ready", "sample_rate": 16000})
                await self._relay_sockets(client_socket, provider_socket)
        except (OSError, TimeoutError, ConnectionClosed) as exc:
            LOGGER.warning("Sarvam realtime voice connection ended: %s", type(exc).__name__)
            try:
                await client_socket.send_json(
                    {"event": "voice.error", "code": "VOICE_PROVIDER_UNAVAILABLE", "message": "Live transcription is unavailable. You can retry or type your message."}
                )
            except (RuntimeError, WebSocketDisconnect):
                pass
        finally:
            try:
                await client_socket.close()
            except (RuntimeError, WebSocketDisconnect):
                pass

    async def _relay_sockets(self, client_socket: WebSocket, provider_socket: object) -> None:
        total_audio_bytes = 0

        async def send_to_provider() -> None:
            nonlocal total_audio_bytes
            while True:
                message = await client_socket.receive_json()
                event = message.get("event")
                if event not in ALLOWED_CLIENT_EVENTS:
                    continue
                if event == "audio_input":
                    encoded = message.get("audio")
                    if not isinstance(encoded, str) or len(encoded) > 128 * 1024:
                        raise VoiceProviderError("INVALID_AUDIO_CHUNK", "An invalid audio chunk was received.", 422)
                    try:
                        decoded_size = len(base64.b64decode(encoded, validate=True))
                    except ValueError as exc:
                        raise VoiceProviderError("INVALID_AUDIO_CHUNK", "An invalid audio chunk was received.", 422) from exc
                    total_audio_bytes += decoded_size
                    maximum = self.settings.voice_max_recording_seconds * 16000 * 2
                    if total_audio_bytes > maximum:
                        raise VoiceProviderError(
                            "RECORDING_TOO_LONG",
                            f"The recording reached the {self.settings.voice_max_recording_seconds} second limit.",
                            422,
                        )
                await provider_socket.send(json.dumps({key: value for key, value in message.items() if key in {"event", "audio"}}))
                if event == "end":
                    return

        async def send_to_client() -> None:
            async for raw in provider_socket:
                try:
                    payload = json.loads(raw)
                except (TypeError, json.JSONDecodeError):
                    continue
                if payload.get("event") not in ALLOWED_PROVIDER_EVENTS:
                    continue
                safe = {key: payload[key] for key in ("event", "text", "language", "language_confidence", "code", "is_fatal", "message", "audio_duration_s") if key in payload}
                await client_socket.send_json(safe)

        sender = asyncio.create_task(send_to_provider())
        receiver = asyncio.create_task(send_to_client())
        done, pending = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_EXCEPTION)
        for task in pending:
            task.cancel()
        for task in done:
            error = task.exception()
            if isinstance(error, VoiceProviderError):
                await client_socket.send_json({"event": "voice.error", "code": error.code, "message": error.message})
            elif error and not isinstance(error, (WebSocketDisconnect, ConnectionClosed)):
                raise error

    @staticmethod
    def _raise_for_provider_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        status_map = {
            400: ("INVALID_VOICE_REQUEST", 422),
            403: ("VOICE_PROVIDER_UNAVAILABLE", 503),
            422: ("INVALID_AUDIO", 422),
            429: ("VOICE_RATE_LIMITED", 503),
            500: ("VOICE_PROVIDER_UNAVAILABLE", 503),
            503: ("VOICE_PROVIDER_UNAVAILABLE", 503),
        }
        code, status = status_map.get(response.status_code, ("VOICE_PROVIDER_UNAVAILABLE", 503))
        raise VoiceProviderError(code, "The voice provider could not complete this request.", status)
