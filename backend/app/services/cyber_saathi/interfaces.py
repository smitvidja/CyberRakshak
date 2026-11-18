from collections.abc import AsyncIterator, Iterator
from typing import Protocol

from app.schemas.cyber_saathi import (
    ConversationState,
    LanguageCode,
    LLMGenerationResult,
    LLMProviderHealth,
)


class LLMGateway(Protocol):
    def generate(self, **kwargs: object) -> LLMGenerationResult: ...

    def stream(self, **kwargs: object) -> Iterator[str]: ...

    def healthCheck(self) -> list[LLMProviderHealth]: ...  # noqa: N802


class VoiceAdapter(Protocol):
    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        content_type: str,
        language: LanguageCode,
    ) -> object: ...

    async def synthesize(self, *, text: str, language: LanguageCode) -> object: ...


class SafetyPlaybook(Protocol):
    def applies(self, state: ConversationState) -> bool: ...

    def guidance(self, language: LanguageCode) -> str: ...
