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
        "code": "WOMEN_AND_CHILD_SAFETY",
        "name": "Women and Child Safety",
        "description": "Synthetic category for abuse, stalking, blackmail, and child-safety concerns.",
    },
    {
        "code": "FINANCIAL_FRAUD",
        "name": "Financial Fraud",
        "description": "Synthetic category for UPI, card, banking, investment, and payment fraud.",
    },
    {
        "code": "IDENTITY_MISUSE",
        "name": "Identity Misuse",
        "description": "Synthetic category for identity, document, and account misuse.",
    },
    {
        "code": "ONLINE_HARASSMENT",
        "name": "Online Harassment",
        "description": "Synthetic category for abusive messages, stalking, and cyberbullying.",
    },
    {
        "code": "E_COMMERCE_FRAUD",
        "name": "E-commerce Fraud",
        "description": "Synthetic category for shopping, delivery, and marketplace fraud.",
    },
    {
        "code": "OTHER_CYBER_CONCERN",
        "name": "Other Cyber Concern",
        "description": "Synthetic category for other cyber incidents needing support.",
    },
)

LEGACY_CATEGORY_CODES = {
    "PHISHING_AND_IMPERSONATION": "IDENTITY_MISUSE",
    "ONLINE_FINANCIAL_FRAUD": "FINANCIAL_FRAUD",
    "ACCOUNT_COMPROMISE": "E_COMMERCE_FRAUD",
    "MALWARE_AND_RANSOMWARE": "OTHER_CYBER_CONCERN",
}

SKILLS = (
    {"name": "Application Security", "category": "Security Engineering", "description": "Synthetic reference skill for secure application assessment."},
    {"name": "Digital Forensics", "category": "Investigation", "description": "Synthetic reference skill for evidence-focused technical investigation."},
    {"name": "Incident Response", "category": "Operations", "description": "Synthetic reference skill for incident triage and response."},
    {"name": "Malware Analysis", "category": "Investigation", "description": "Synthetic reference skill for safe malware analysis."},
    {"name": "Network Security", "category": "Security Engineering", "description": "Synthetic reference skill for network defense."},
    {"name": "OSINT", "category": "Investigation", "description": "Synthetic reference skill for open-source intelligence."},
    {"name": "Threat Intelligence", "category": "Investigation", "description": "Synthetic reference skill for cyber threat research."},
    {"name": "Vulnerability Assessment", "category": "Security Engineering", "description": "Synthetic reference skill for authorized vulnerability assessment."},
)


def seed_reference_data(session: Session) -> tuple[int, int]:
    """Insert or normalize local-only reference rows and return added counts."""

    existing_categories = {
        category.code: category
        for category in session.scalars(select(ComplaintCategory)).all()
    }
    categories_added = 0
    for category_data in COMPLAINT_CATEGORIES:
        category = existing_categories.get(category_data["code"])
        if category is None:
            legacy_code = next(
                (old_code for old_code, new_code in LEGACY_CATEGORY_CODES.items() if new_code == category_data["code"]),
                None,
            )
            category = existing_categories.get(legacy_code) if legacy_code else None
        if category is None:
            session.add(ComplaintCategory(**category_data))
            categories_added += 1
            continue
        category.code = category_data["code"]
        category.name = category_data["name"]
        category.description = category_data["description"]
        category.is_active = True

    existing_skill_names = set(session.scalars(select(Skill.name)).all())
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
    print(f"Reference data seeded: {categories_added} complaint categories, {skills_added} skills added.")


if __name__ == "__main__":
    main()