from typing import Any, Protocol

from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.services.resume_extraction import extract_resume_text
from app.services.resume_llm import merge_with_deterministic, structure_resume_with_model
from app.services.resume_structuring import structure_resume


class ResumeParser(Protocol):
    async def parse(self, *, content: bytes, file_name: str, known_skills: list[str]) -> dict[str, Any]: ...


class DocumentResumeParser:
    """Real parser: bounded extraction from the uploaded bytes, then structuring.

    Output is a set of *suggestions*. It is persisted untrusted and stays editable
    until the citizen explicitly confirms it, so this never writes to the profile.
    """

    async def parse(self, *, content: bytes, file_name: str, known_skills: list[str]) -> dict[str, Any]:
        extracted = extract_resume_text(content, file_name)
        structured = structure_resume(extracted.text, known_skills)

        # Optional second stage. The provider adapters are synchronous, and this
        # route is async, so calling one directly would block the event loop for
        # the whole timeout and stall every other request in the process.
        outcome = await run_in_threadpool(structure_resume_with_model, extracted.text)
        suggestions = merge_with_deterministic(structured, outcome.suggestions)

        return {
            "source": "document_parser" if outcome.status != "ok" else "document_parser+model",
            "review_required": True,
            "file_name": file_name,
            # Safe provenance only - never the extracted text itself.
            "extractor": extracted.extractor,
            "unit_count": extracted.unit_count,
            "truncated": extracted.truncated,
            "model_stage": outcome.as_metadata(),
            **suggestions,
        }


class MockResumeParser:
    """Fixed synthetic profile, for tests and an explicitly configured demo mode.

    Never selected by default: a production-shaped runtime must not return the same
    invented person for every uploaded file.
    """

    async def parse(self, *, content: bytes, file_name: str, known_skills: list[str]) -> dict[str, Any]:
        return {
            "source": "mock_parser",
            "review_required": True,
            "file_name": file_name,
            "profile": {
                "bio": "Cyber safety volunteer interested in responsible threat reporting and community awareness.",
                "location": "Ahmedabad, Gujarat",
            },
            "skills": ["Cyber Security", "Network Security", "Threat Analysis"],
            "education": [{
                "institution": "Synthetic Institute of Technology",
                "degree": "Bachelor of Technology",
                "field_of_study": "Computer Science",
            }],
            "experience": [{
                "organization": "Community Cyber Safety Lab",
                "title": "Security Volunteer",
                "description": "Supported synthetic cyber-awareness exercises and documented suspicious activity.",
                "is_current": True,
            }],
            "certifications": [{
                "name": "Foundations of Cyber Safety",
                "issuing_organization": "Synthetic Learning Centre",
            }],
        }


def get_resume_parser() -> ResumeParser:
    if get_settings().resume_parser.strip().lower() == "mock":
        return MockResumeParser()
    return DocumentResumeParser()
