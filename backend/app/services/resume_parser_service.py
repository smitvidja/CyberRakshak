from typing import Protocol


class ResumeParser(Protocol):
    async def parse(self, *, storage_key: str, file_name: str) -> dict[str, object]: ...


class MockResumeParser:
    async def parse(self, *, storage_key: str, file_name: str) -> dict[str, object]:
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
    return MockResumeParser()
