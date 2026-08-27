"""Reset Cyber Warrior demo data for the synthetic identities in DEMO_IDENTITIES.

Manual browser/E2E verification against the real dev database creates genuine
rows (cyber warrior profile, application, resume parsing results, skills,
education, experience, certifications) for the demo identities in
DEMO-CREDENTIALS.md. Those rows can later collide with backend tests that
assume a "fresh" identity (e.g. a 201-on-first-profile-creation test getting a
409 instead). This script clears just that Cyber Warrior demo data so the
backend test suite's assumptions hold again, without touching any other data.

Safe to run at any time: it is idempotent and only ever removes rows tied to
the synthetic identities in DEMO_IDENTITIES. It never touches citizen
profiles/complaints or any non-demo user.

Usage (from the backend/ directory, with the project virtualenv active):
    python scripts/reset_demo_warrior_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.mock_identity_service import DEMO_IDENTITIES

WARRIOR_CHILD_TABLES = (
    "warrior_skills",
    "warrior_education",
    "warrior_experience",
    "warrior_certifications",
    "warrior_applications",
    "resume_parsing_results",
)


def _warrior_email(synthetic_email: str) -> str:
    local_part, separator, _ = synthetic_email.partition("@")
    if not separator:
        raise ValueError(f"Unexpected synthetic email shape: {synthetic_email!r}")
    return f"{local_part}.warrior@cyberrakshak.example.com"


def reset_demo_warrior_data() -> None:
    session = SessionLocal()
    try:
        for demo_identity in DEMO_IDENTITIES:
            email = _warrior_email(demo_identity["synthetic_email"])
            user_id = session.execute(
                text("select id from users where email = :email"),
                {"email": email},
            ).scalar()
            if user_id is None:
                print(f"skip  {email}: no Cyber Warrior user found")
                continue

            profile_id = session.execute(
                text("select id from cyber_warrior_profiles where user_id = :u"),
                {"u": user_id},
            ).scalar()

            if profile_id is not None:
                report_ids = [
                    row[0]
                    for row in session.execute(
                        text("select id from warrior_reports where warrior_id = :w"),
                        {"w": profile_id},
                    ).fetchall()
                ]
                if report_ids:
                    result = session.execute(
                        text("delete from evidence where warrior_report_id = any(:ids)"),
                        {"ids": report_ids},
                    )
                    if result.rowcount:
                        print(f"  deleted {result.rowcount} row(s) from evidence")
                result = session.execute(
                    text("delete from warrior_reports where warrior_id = :w"),
                    {"w": profile_id},
                )
                if result.rowcount:
                    print(f"  deleted {result.rowcount} row(s) from warrior_reports")
                for table in WARRIOR_CHILD_TABLES:
                    result = session.execute(
                        text(f"delete from {table} where warrior_id = :w"),
                        {"w": profile_id},
                    )
                    if result.rowcount:
                        print(f"  deleted {result.rowcount} row(s) from {table}")
                session.execute(
                    text("delete from cyber_warrior_profiles where id = :c"),
                    {"c": profile_id},
                )
                print(f"  deleted cyber_warrior_profiles row for {email}")

            session.execute(text("delete from users where id = :u"), {"u": user_id})
            print(f"reset {email}: user + Cyber Warrior data removed")

        session.commit()
        print("Demo Cyber Warrior data reset complete.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    reset_demo_warrior_data()
