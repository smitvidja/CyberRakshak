from collections.abc import AsyncIterator
from typing import Protocol

from app.schemas.cyber_saathi import ConversationState, LanguageCode


class LLMGateway(Protocol):
    async def stream_response(
        self, *, state: ConversationState, system_prompt: str
    ) -> AsyncIterator[str]: ...


class VoiceAdapter(Protocol):
    async def transcribe(self, *, audio: bytes, language: LanguageCode) -> str: ...

    async def synthesize(
        self, *, text: str, language: LanguageCode
    ) -> AsyncIterator[bytes]: ...


class SafetyPlaybook(Protocol):
    def applies(self, state: ConversationState) -> bool: ...

    def guidance(self, language: LanguageCode) -> str: ...
