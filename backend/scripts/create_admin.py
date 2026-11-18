"""Create (or reset the password of) an administrator account for local use.

The app never creates admins itself - mock identity verification only issues citizen
and Cyber Warrior roles - so a fresh database has no way into the admin console.
This is a development tool: scripts/ is excluded from the Docker image.

    # from backend/, with DATABASE_URL pointing at the database to change
    ADMIN_PASSWORD='<choose one>' ./.venv/Scripts/python.exe -m scripts.create_admin admin@example.com

The password is read from the ADMIN_PASSWORD environment variable, never from the
command line, so it does not end up in shell history or process listings. It is
never printed.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole

MIN_PASSWORD_LENGTH = 12


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: ADMIN_PASSWORD=... python -m scripts.create_admin <email>", file=sys.stderr)
        return 2
    email = argv[0].strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if "@" not in email:
        print("error: the first argument must be an email address", file=sys.stderr)
        return 2
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"error: set ADMIN_PASSWORD (at least {MIN_PASSWORD_LENGTH} characters)", file=sys.stderr)
        return 2

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            session.add(User(email=email, password_hash=hash_password(password), role=UserRole.ADMIN))
            action = "created"
        elif user.role is not UserRole.ADMIN:
            # Never silently promote an existing citizen or warrior account.
            print(f"error: {email} already exists with role {user.role.value}", file=sys.stderr)
            return 1
        else:
            user.password_hash = hash_password(password)
            action = "password reset for"
        session.commit()
    print(f"admin {action} {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
