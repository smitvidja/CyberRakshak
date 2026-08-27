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
profiles/complaints or any non-demo user. It only ever resets the Cyber
Warrior side of an identity (profile/application/resume/reports) - the
identity's separate citizen account, if any, is untouched.

No special app permissions ("admin role", etc.) are needed to run this - it
is a local database-maintenance script, run directly by whoever has the repo
and can reach the dev database, same as any other script under scripts/.

Usage (from the backend/ directory, with the project virtualenv active):
    # Reset every demo identity's Cyber Warrior data (all of DEMO_IDENTITIES):
    python scripts/reset_demo_warrior_data.py

    # Reset only specific identities, so you can redo the full first-time
    # Cyber Warrior journey (verify -> profile -> resume -> application) with
    # that exact demo_identity_id again, while leaving every other identity's
    # data untouched:
    python scripts/reset_demo_warrior_data.py 99000000000003
    python scripts/reset_demo_warrior_data.py 99000000000003 99000000000004
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


def reset_demo_warrior_data(identity_ids: set[str] | None = None) -> None:
    """Reset Cyber Warrior demo data. If identity_ids is given, only those
    demo_identity_id values are reset; otherwise every identity in
    DEMO_IDENTITIES is reset."""
    session = SessionLocal()
    try:
        targets = [
            demo_identity
            for demo_identity in DEMO_IDENTITIES
            if identity_ids is None or demo_identity["demo_identity_id"] in identity_ids
        ]
        if identity_ids is not None:
            found_ids = {demo_identity["demo_identity_id"] for demo_identity in targets}
            for missing in identity_ids - found_ids:
                print(f"warning: {missing!r} is not a known demo_identity_id - skipped")

        for demo_identity in targets:
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
    requested_ids = set(sys.argv[1:]) or None
    reset_demo_warrior_data(requested_ids)
