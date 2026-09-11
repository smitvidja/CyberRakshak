"""Delete Cyber Saathi conversations whose retention window has passed.

A citizen consents to storage for thirty days. ``CyberSaathiPersistence.load``
already refuses to return an expired conversation, but refusing to read is not
deleting: the rows stayed in the database indefinitely, holding the conversation
state of people who were told it would be gone.

Idempotent and safe to run repeatedly - the container entrypoint runs it on every
start. Run it by hand with:

    cd backend
    ./.venv/Scripts/python.exe -m scripts.purge_expired_conversations
    ./.venv/Scripts/python.exe -m scripts.purge_expired_conversations --dry-run

Ordering note: anything that harvests conversations for later use must run
*before* this, or it will find nothing to harvest.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.repositories.cyber_saathi_repository import CyberSaathiRepository  # noqa: E402
from app.services.cyber_saathi_persistence import CyberSaathiPersistence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many conversations are past retention without deleting them.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        if args.dry_run:
            expired = CyberSaathiRepository.count_expired(session, datetime.now(timezone.utc))
            print(f"{expired} conversation(s) past retention (dry run, nothing deleted)")
            return 0
        removed = CyberSaathiPersistence.purge_expired(session)
        print(f"purged {removed} conversation(s) past retention")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
