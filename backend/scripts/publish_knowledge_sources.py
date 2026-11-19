"""Publish approved knowledge-source proposals into the authoritative corpus.

The last step of the knowledge-gap loop (see app/services/knowledge_source_service.py):
every proposal a second administrator APPROVED is written into
app/data/cyber_saathi/authoritative_knowledge/sources.json, the index is rebuilt,
and the proposals (and their gaps) are marked published / actioned.

The two changed files are then reviewed and committed like any other change - that
commit is what makes the new guidance reach production. Run from backend/:

    # see what would be published, change nothing
    ./.venv/Scripts/python.exe -m scripts.publish_knowledge_sources --dry-run

    # publish; --semantic is required while the committed index has semantic
    # embeddings (only the new sections are embedded - the rest are reused)
    ./.venv/Scripts/python.exe -m scripts.publish_knowledge_sources --semantic

Never run by the API or on startup.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.core.database import SessionLocal
from app.services.knowledge_source_service import KnowledgeSourceService


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="validate and list what would be published; write nothing")
    parser.add_argument("--semantic", action="store_true", help="also generate semantic embeddings for new sections")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        try:
            result = KnowledgeSourceService.publish(session, semantic_embeddings=args.semantic, dry_run=args.dry_run)
        except ValueError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    print(json.dumps(result, indent=2))
    if result["status"] == "published":
        print(
            "\nNext: review and commit backend/app/data/cyber_saathi/authoritative_knowledge/"
            "sources.json and knowledge_index.json - the deploy is what makes it live.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
