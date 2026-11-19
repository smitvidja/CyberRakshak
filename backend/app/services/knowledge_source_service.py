"""Close knowledge gaps with reviewed official sources - the rest of the gap loop.

knowledge_gap_service records what Cyber Saathi could not answer. This module is
how an answer gets added without letting anyone's text become guidance on their
own say-so:

1. propose - an administrator attaches an excerpt from an official publication
   (https, allowlisted government/regulator domain; see the schema) to a gap.
2. review  - a *different* administrator approves or rejects it. The proposer can
   never approve their own proposal, so one compromised or careless account cannot
   put text in front of citizens.
3. publish - an explicit command (scripts/publish_knowledge_sources.py) writes the
   approved proposals into the version-controlled source pack and rebuilds the
   index. That change is committed and deployed like any other, so the corpus stays
   separately sourced, attributable and versioned, and every running instance
   serves the same reviewed index.

Citizen conversation text never enters this path.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import KnowledgeGapSignal, KnowledgeSourceProposal, User
from app.schemas.cyber_saathi import KnowledgeSourceProposalCreate
from app.services.audit_service import AuditService
from app.services.cyber_saathi import knowledge as knowledge_module

PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
PUBLISHED = "PUBLISHED"
STATUSES = (PENDING, APPROVED, REJECTED, PUBLISHED)


class KnowledgeSourceService:
    @staticmethod
    def propose(session: Session, payload: KnowledgeSourceProposalCreate, admin: User) -> KnowledgeSourceProposal:
        if payload.gap_id is not None and session.get(KnowledgeGapSignal, payload.gap_id) is None:
            raise APIError(status_code=404, code="KNOWLEDGE_GAP_NOT_FOUND", message="Knowledge gap signal not found.")
        proposal = KnowledgeSourceProposal(
            gap_id=payload.gap_id,
            status=PENDING,
            source_title=payload.source_title,
            source_url=payload.source_url.strip(),
            source_type=payload.source_type,
            jurisdiction=payload.jurisdiction.strip(),
            language=payload.language.value,
            domains=[domain.value for domain in payload.domains],
            published_on=payload.published_on,
            section_title=payload.section_title,
            text=payload.text,
            retrieval_terms=payload.retrieval_terms,
            proposed_by_id=admin.id,
        )
        session.add(proposal)
        session.flush()
        AuditService.record(
            session,
            action="knowledge_source.proposed",
            entity_type="knowledge_source_proposal",
            entity_id=proposal.id,
            user_id=admin.id,
            details={"gap_id": str(payload.gap_id) if payload.gap_id else None, "source_url": proposal.source_url},
        )
        session.commit()
        session.refresh(proposal)
        return proposal

    @staticmethod
    def list(session: Session, *, status: str | None = None, limit: int = 100) -> list[KnowledgeSourceProposal]:
        if status is not None and status not in STATUSES:
            raise APIError(status_code=422, code="INVALID_PROPOSAL_STATUS", message=f"Status must be one of {', '.join(STATUSES)}.")
        query = select(KnowledgeSourceProposal).order_by(KnowledgeSourceProposal.created_at.desc()).limit(limit)
        if status is not None:
            query = query.where(KnowledgeSourceProposal.status == status)
        return list(session.scalars(query))

    @staticmethod
    def review(session: Session, proposal_id: UUID, *, decision: str, review_note: str | None, admin: User) -> KnowledgeSourceProposal:
        proposal = session.get(KnowledgeSourceProposal, proposal_id)
        if proposal is None:
            raise APIError(status_code=404, code="PROPOSAL_NOT_FOUND", message="Knowledge source proposal not found.")
        if proposal.status != PENDING:
            raise APIError(status_code=409, code="PROPOSAL_ALREADY_REVIEWED", message="Only pending proposals can be reviewed.")
        if proposal.proposed_by_id == admin.id:
            raise APIError(
                status_code=403,
                code="SECOND_REVIEWER_REQUIRED",
                message="A different administrator must review this proposal.",
            )
        now = datetime.now(timezone.utc)
        proposal.status = decision
        proposal.reviewed_by_id = admin.id
        proposal.reviewed_at = now
        proposal.review_note = (review_note or "").strip()[:2000] or None
        if decision == APPROVED and proposal.gap_id is not None:
            gap = session.get(KnowledgeGapSignal, proposal.gap_id)
            # REVIEWED, not ACTIONED: ACTIONED means the source is in the published
            # pack and the index is rebuilt, which only the publish step does.
            if gap is not None and gap.status in ("OPEN", "REVIEWED"):
                gap.status = "REVIEWED"
                gap.resolution_note = f"Source approved, awaiting publish: {proposal.source_title}"[:2000]
                gap.reviewed_at = now
        AuditService.record(
            session,
            action="knowledge_source.reviewed",
            entity_type="knowledge_source_proposal",
            entity_id=proposal.id,
            user_id=admin.id,
            details={"decision": decision},
        )
        session.commit()
        session.refresh(proposal)
        return proposal

    @staticmethod
    def source_id_for(proposal: KnowledgeSourceProposal) -> str:
        return "reviewed_" + proposal.id.hex[:12]

    @staticmethod
    def source_entry(proposal: KnowledgeSourceProposal) -> dict[str, Any]:
        """The proposal as a source-pack entry, in the pack's own key order."""
        return {
            "source_id": KnowledgeSourceService.source_id_for(proposal),
            "source_title": proposal.source_title,
            "source_type": proposal.source_type,
            "source_url": proposal.source_url,
            "jurisdiction": proposal.jurisdiction,
            "domains": list(proposal.domains),
            "language": proposal.language,
            "version": f"reviewed proposal {proposal.reviewed_at:%Y-%m-%d}" if proposal.reviewed_at else "reviewed proposal",
            "published_at": proposal.published_on,
            "sections": [
                {
                    "title": proposal.section_title,
                    "domains": list(proposal.domains),
                    "text": proposal.text,
                    "retrieval_terms": list(proposal.retrieval_terms or []),
                }
            ],
        }

    @staticmethod
    def publish(session: Session, *, semantic_embeddings: bool = False, dry_run: bool = False) -> dict[str, Any]:
        """Write every APPROVED proposal into the source pack and rebuild the index.

        Run by an operator (scripts/publish_knowledge_sources.py), never by the API.
        The pack and index are restored from a backup if anything fails, and the
        database is only updated after both files are written and verified.
        """
        pack_path: Path = knowledge_module.SOURCE_PACK_PATH
        index_path: Path = knowledge_module.INDEX_PATH
        approved = list(
            session.scalars(
                select(KnowledgeSourceProposal)
                .where(KnowledgeSourceProposal.status == APPROVED)
                .order_by(KnowledgeSourceProposal.reviewed_at, KnowledgeSourceProposal.created_at)
            )
        )
        if not approved:
            return {"status": "nothing_to_publish", "published": []}

        current_index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        needs_semantic = bool(current_index.get("semantic_embedding_provider"))
        # A dry run writes nothing, so it reports this instead of refusing.
        if needs_semantic and not semantic_embeddings and not dry_run:
            raise ValueError(
                "The current index carries semantic embeddings; publishing without --semantic "
                "would silently drop them. Re-run with --semantic (needs the embedding provider configured)."
            )

        original = pack_path.read_text(encoding="utf-8")
        pack = json.loads(original)
        existing_ids = {source["source_id"] for source in pack["sources"]}
        entries = [KnowledgeSourceService.source_entry(p) for p in approved]
        new_entries = [entry for entry in entries if entry["source_id"] not in existing_ids]
        now = datetime.now(timezone.utc)
        pack["sources"].extend(new_entries)
        pack["version"] = f"{now:%Y.%m.%d}.r{len(pack['sources'])}"
        pack["reviewed_at"] = f"{now:%Y-%m-%d}"
        knowledge_module.KnowledgeSourcePack.model_validate(pack)  # the whole pack must still be valid
        source_ids = [entry["source_id"] for entry in entries]
        if dry_run:
            return {"status": "dry_run", "would_publish": source_ids, "pack_version": pack["version"], "requires_semantic": needs_semantic}

        pack_backup = pack_path.with_suffix(".json.bak")
        index_backup = index_path.with_suffix(".json.bak")
        shutil.copy2(pack_path, pack_backup)
        if index_path.exists():
            shutil.copy2(index_path, index_backup)
        try:
            pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = knowledge_module.rebuild_index(index_path, semantic_embeddings=semantic_embeddings)
        except Exception:
            shutil.copy2(pack_backup, pack_path)
            if index_backup.exists():
                shutil.copy2(index_backup, index_path)
            knowledge_module.KnowledgeService.clear_cache()
            raise
        finally:
            pack_backup.unlink(missing_ok=True)
            index_backup.unlink(missing_ok=True)

        for proposal in approved:
            source_id = KnowledgeSourceService.source_id_for(proposal)
            proposal.status = PUBLISHED
            proposal.published_source_id = source_id
            proposal.published_at = now
            if proposal.gap_id is not None:
                gap = session.get(KnowledgeGapSignal, proposal.gap_id)
                if gap is not None and gap.status != "DISMISSED":
                    gap.status = "ACTIONED"
                    gap.resolution_note = f"Published as {source_id} in source pack {pack['version']}."
                    gap.reviewed_at = now
            AuditService.record(
                session,
                action="knowledge_source.published",
                entity_type="knowledge_source_proposal",
                entity_id=proposal.id,
                details={"source_id": source_id, "pack_version": pack["version"]},
            )
        session.commit()
        return {
            "status": "published",
            "published": source_ids,
            "pack_version": pack["version"],
            "chunk_count": result["chunk_count"],
            "semantic_embeddings_generated": result["semantic_embeddings_generated"],
        }
