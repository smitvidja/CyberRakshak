"""Seed synthetic reference data used by the local CyberRakshak prototype."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.models import ComplaintCategory, Skill

COMPLAINT_CATEGORIES = (
    {
        "code": "ONLINE_FINANCIAL_FRAUD",
        "name": "Online Financial Fraud",
        "description": "Synthetic category for online payment and account fraud reports.",
    },
    {
        "code": "PHISHING_AND_IMPERSONATION",
        "name": "Phishing and Impersonation",
        "description": "Synthetic category for phishing, spoofing, and impersonation reports.",
    },
    {
        "code": "ACCOUNT_COMPROMISE",
        "name": "Account Compromise",
        "description": "Synthetic category for compromised accounts and unauthorized access.",
    },
    {
        "code": "MALWARE_AND_RANSOMWARE",
        "name": "Malware and Ransomware",
        "description": "Synthetic category for malware and ransomware incidents.",
    },
    {
        "code": "ONLINE_HARASSMENT",
        "name": "Online Harassment",
        "description": "Synthetic category for harassment and abusive online conduct.",
    },
)

SKILLS = (
    {
        "name": "Application Security",
        "category": "Security Engineering",
        "description": "Synthetic reference skill for secure application assessment.",
    },
    {
        "name": "Digital Forensics",
        "category": "Investigation",
        "description": "Synthetic reference skill for evidence-focused technical investigation.",
    },
    {
        "name": "Incident Response",
        "category": "Operations",
        "description": "Synthetic reference skill for incident triage and response.",
    },
    {
        "name": "Malware Analysis",
        "category": "Investigation",
        "description": "Synthetic reference skill for safe malware analysis.",
    },
    {
        "name": "Network Security",
        "category": "Security Engineering",
        "description": "Synthetic reference skill for network defense.",
    },
    {
        "name": "OSINT",
        "category": "Investigation",
        "description": "Synthetic reference skill for open-source intelligence.",
    },
    {
        "name": "Threat Intelligence",
        "category": "Investigation",
        "description": "Synthetic reference skill for cyber threat research.",
    },
    {
        "name": "Vulnerability Assessment",
        "category": "Security Engineering",
        "description": "Synthetic reference skill for authorized vulnerability assessment.",
    },
)


def seed_reference_data(session: Session) -> tuple[int, int]:
    """Insert missing reference rows and return added category and skill counts."""

    existing_category_codes = set(
        session.scalars(select(ComplaintCategory.code)).all()
    )
    existing_skill_names = set(session.scalars(select(Skill.name)).all())

    categories_added = 0
    for category in COMPLAINT_CATEGORIES:
        if category["code"] not in existing_category_codes:
            session.add(ComplaintCategory(**category))
            categories_added += 1

    skills_added = 0
    for skill in SKILLS:
        if skill["name"] not in existing_skill_names:
            session.add(Skill(**skill))
            skills_added += 1

    return categories_added, skills_added


def main() -> None:
    session = SessionLocal()

    try:
        with session.begin():
            categories_added, skills_added = seed_reference_data(session)
    finally:
        session.close()

    print(
        "Reference data seeded: "
        f"{categories_added} complaint categories, {skills_added} skills added."
    )


if __name__ == "__main__":
    main()
