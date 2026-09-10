"""Authorize a complaint-copy request and build a sanitized document model.

Two things are deliberately separated here:

1. **Authorization.** An identified complaint needs the owner's session. An
   anonymous complaint needs a scoped capability that was issued at submission.
   A complaint number is never sufficient for either - it is a tracking reference,
   not a secret.
2. **Sanitization.** The renderer only ever sees this typed view model, so
   storage keys, internal ids, tokens and reporter identity cannot reach a PDF
   even by accident.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import Complaint, ComplaintAccessGrant, User
from app.models.enums import ComplaintStatus
from app.services.complaint_service import ComplaintService

# Long enough that guessing is hopeless, short enough to read back over a phone.
TOKEN_BYTES = 32
GRANT_TTL_DAYS = 180


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DocumentField:
    label: str
    value: str


@dataclass(frozen=True)
class DocumentSection:
    title: str
    fields: list[DocumentField] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    note: str | None = None


@dataclass(frozen=True)
class ComplaintDocument:
    complaint_number: str
    reporting_mode: str
    status: str
    generated_at: datetime
    sections: list[DocumentSection]
    document_version: str = "1.0"


def _text(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    # Strip control characters so citizen-controlled text cannot disturb the
    # rendered document; the renderer treats everything else as literal text.
    cleaned = "".join(ch for ch in text if ch == "\n" or ch >= " ")
    return cleaned or "-"


def _readable_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _stamp(value: datetime | None) -> str:
    return value.strftime("%d %b %Y, %H:%M UTC") if value else "-"


class ComplaintDocumentService:
    @staticmethod
    def issue_anonymous_grant(session: Session, complaint: Complaint) -> str | None:
        """Mint a one-off capability for an anonymous complaint at submission.

        Returns the plaintext exactly once; only its digest is stored. Identified
        complaints get None - they already have an authenticated owner.
        """
        if not complaint.is_anonymous or complaint.user_id is not None:
            return None
        token = secrets.token_urlsafe(TOKEN_BYTES)
        session.add(
            ComplaintAccessGrant(
                complaint_id=complaint.id,
                token_hash=hash_token(token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=GRANT_TTL_DAYS),
            )
        )
        return token

    @staticmethod
    def authorize(
        session: Session,
        complaint_id: UUID,
        current_user: User | None,
        access_token: str | None,
    ) -> Complaint:
        complaint = ComplaintService._get_details_or_not_found(session, complaint_id)
        if complaint.status is ComplaintStatus.DRAFT:
            # A draft has no submitted copy to issue.
            raise APIError(status_code=404, code="NOT_FOUND", message="Complaint not found.")

        if complaint.user_id is not None:
            if current_user is None:
                raise APIError(status_code=401, code="UNAUTHORIZED", message="Sign in to download this complaint copy.")
            if complaint.user_id != current_user.id:
                raise APIError(status_code=404, code="NOT_FOUND", message="Complaint not found.")
            return complaint

        if not access_token:
            raise APIError(
                status_code=401,
                code="COMPLAINT_ACCESS_TOKEN_REQUIRED",
                message="This anonymous complaint needs its access code. A complaint number alone cannot open it.",
            )
        grant = session.scalar(
            select(ComplaintAccessGrant).where(ComplaintAccessGrant.token_hash == hash_token(access_token))
        )
        now = datetime.now(timezone.utc)
        if (
            grant is None
            or grant.complaint_id != complaint.id
            or grant.revoked_at is not None
            or (grant.expires_at is not None and grant.expires_at <= now)
        ):
            # One shape of failure for wrong, expired, revoked or other-complaint
            # codes, so the response cannot be used to probe which is which.
            raise APIError(status_code=403, code="COMPLAINT_ACCESS_DENIED", message="This access code is not valid for this complaint.")
        grant.last_used_at = now
        session.commit()
        return complaint

    @staticmethod
    def build(complaint: Complaint) -> ComplaintDocument:
        anonymous = complaint.user_id is None
        sections: list[DocumentSection] = []

        sections.append(
            DocumentSection(
                title="Complaint reference",
                fields=[
                    DocumentField("Complaint number", _text(complaint.complaint_number)),
                    DocumentField("Current status", _text(complaint.status.value.replace("_", " ").title())),
                    DocumentField("Reporting mode", "Anonymous" if anonymous else "Identified"),
                    DocumentField("Report concerns", _text(complaint.reporting_for.replace("_", " ").title())),
                    DocumentField("Created", _stamp(complaint.created_at)),
                    DocumentField("Submitted", _stamp(complaint.submitted_at)),
                ],
            )
        )

        incident_fields = [
            DocumentField("Category", _text(complaint.category.name if complaint.category else None)),
            DocumentField("Title", _text(complaint.title)),
            DocumentField("Incident date and time", _stamp(complaint.incident_at)),
        ]
        if complaint.financial_loss_amount is not None:
            incident_fields.append(DocumentField("Reported financial loss", f"INR {complaint.financial_loss_amount:,.2f}"))
        if not anonymous and complaint.affected_person_name:
            incident_fields.append(DocumentField("Affected person", _text(complaint.affected_person_name)))
        sections.append(
            DocumentSection(title="Incident details", fields=incident_fields, paragraphs=[_text(complaint.description)])
        )

        location = complaint.location
        if location is not None and any([location.address, location.city, location.district, location.state, location.postal_code]):
            sections.append(
                DocumentSection(
                    title="Reported location",
                    fields=[
                        DocumentField("Address", _text(location.address)),
                        DocumentField("City", _text(location.city)),
                        DocumentField("District", _text(location.district)),
                        DocumentField("State", _text(location.state)),
                        DocumentField("PIN code", _text(location.postal_code)),
                    ],
                )
            )

        if complaint.suspects:
            suspect_fields: list[DocumentField] = []
            for index, suspect in enumerate(complaint.suspects, start=1):
                suspect_fields.append(DocumentField(f"{index}. Name or alias", _text(suspect.name or suspect.alias)))
                if suspect.contact_details:
                    suspect_fields.append(DocumentField("   Reported identifier", _text(suspect.contact_details)))
                if suspect.description:
                    suspect_fields.append(DocumentField("   Reported details", _text(suspect.description)))
            sections.append(
                DocumentSection(
                    title="Suspect information as reported",
                    fields=suspect_fields,
                    note="This is information supplied by the reporter. It is an allegation, not a finding, and does not establish that any person committed an offence.",
                )
            )

        if complaint.evidence_items:
            # Safe user-facing metadata only. Storage keys and private URLs never
            # appear in a document that leaves the system.
            evidence_fields = [
                DocumentField(
                    f"{index}. {_text(item.file_name)}",
                    f"{_text(item.mime_type)} - {_readable_size(item.file_size)}",
                )
                for index, item in enumerate(complaint.evidence_items, start=1)
            ]
            sections.append(
                DocumentSection(
                    title="Evidence attached",
                    fields=evidence_fields,
                    note="Files are stored with the complaint. This page lists what was attached; it does not contain the files themselves.",
                )
            )

        sections.append(
            DocumentSection(
                title="What happens next",
                paragraphs=[
                    "Keep the complaint number safe. It lets you check the current status on the tracking page of this prototype.",
                    "If money was lost recently, call the national cyber helpline on 1930 and inform your bank immediately. This prototype does not contact your bank, the police, or any government system for you.",
                ],
                note="Anonymous copies can only be downloaded again with the access code shown at submission. If that code is lost, the full copy cannot be recovered - this is deliberate, so that a complaint number alone can never expose a complaint."
                if anonymous
                else None,
            )
        )

        return ComplaintDocument(
            complaint_number=complaint.complaint_number,
            reporting_mode="Anonymous" if anonymous else "Identified",
            status=complaint.status.value,
            generated_at=datetime.now(timezone.utc),
            sections=sections,
        )
