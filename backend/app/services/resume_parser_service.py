from typing import Protocol


class ResumeParser(Protocol):
    async def parse(self, *, storage_key: str, file_name: str) -> dict[str, object]: ...


class MockResumeParser:
    async def parse(self, *, storage_key: str, file_name: str) -> dict[str, object]:
        return {
            "source": "mock_parser",
            "review_required": True,
            "file_name": file_name,
            "profile": {},
            "skills": [],
            "education": [],
            "experience": [],
            "certifications": [],
        }


def get_resume_parser() -> ResumeParser:
    return MockResumeParser()
