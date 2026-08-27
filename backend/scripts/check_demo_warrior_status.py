"""Read-only status check: which demo identities have registered as a Cyber
Warrior, and how far they've gotten.

This never modifies any data - it only reports what already exists, so you
can see at a glance which of the 11 identities in DEMO-CREDENTIALS.md are
still "fresh" (safe to demo a first-time registration with) versus already
registered (will go straight to their dashboard on the next login).

Usage (from the backend/ directory, with the project virtualenv active):
    python scripts/check_demo_warrior_status.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.mock_identity_service import DEMO_IDENTITIES


def _warrior_email(synthetic_email: str) -> str:
    local_part, separator, _ = synthetic_email.partition("@")
    if not separator:
        raise ValueError(f"Unexpected synthetic email shape: {synthetic_email!r}")
    return f"{local_part}.warrior@cyberrakshak.example.com"


def check_demo_warrior_status() -> None:
    session = SessionLocal()
    try:
        print(f"{'Identity ID':<16} {'Name':<20} {'Registered?':<12} {'Application status':<20} Reports")
        print("-" * 90)
        for demo_identity in DEMO_IDENTITIES:
            email = _warrior_email(demo_identity["synthetic_email"])
            user_id = session.execute(
                text("select id from users where email = :email"),
                {"email": email},
            ).scalar()

            if user_id is None:
                print(
                    f"{demo_identity['demo_identity_id']:<16} {demo_identity['full_name']:<20} "
                    f"{'no':<12} {'-':<20} -"
                )
                continue

            profile_id = session.execute(
                text("select id from cyber_warrior_profiles where user_id = :u"),
                {"u": user_id},
            ).scalar()

            application_status = session.execute(
                text(
                    "select status from warrior_applications "
                    "where warrior_id = :w order by created_at desc limit 1"
                ),
                {"w": profile_id},
            ).scalar() if profile_id else None

            report_count = session.execute(
                text("select count(*) from warrior_reports where warrior_id = :w"),
                {"w": profile_id},
            ).scalar() if profile_id else 0

            print(
                f"{demo_identity['demo_identity_id']:<16} {demo_identity['full_name']:<20} "
                f"{'yes':<12} {str(application_status or 'no application'):<20} {report_count}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    check_demo_warrior_status()
