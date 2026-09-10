import hashlib
import hmac
import re
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import ensure_resource_owner
from app.core.config import get_settings
from app.models import ReportedSuspect, SuspectCorrectionRequest, User
from app.models.enums import ReportedSuspectIdentifierType, ReportedSuspectStatus, SuspectCorrectionStatus
from app.repositories.reported_suspect_repository import ReportedSuspectRepository
from app.schemas.suspect import ReportedSuspectCreate, SuspectCorrectionCreate, SuspectSearchRequest, SuspectSearchResponse


def normalize_identifier(identifier_type: ReportedSuspectIdentifierType, value: str) -> str:
    candidate = value.strip()
    if identifier_type is ReportedSuspectIdentifierType.PHONE:
        prefix = "+" if candidate.startswith("+") else ""
        digits = re.sub(r"\D", "", candidate)
        if len(digits) == 10:
            return "+91" + digits
        if len(digits) == 12 and digits.startswith("91"):
            return "+" + digits
        if not 8 <= len(digits) <= 15:
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid phone number with 8 to 15 digits.")
        return prefix + digits
    if identifier_type is ReportedSuspectIdentifierType.EMAIL:
        candidate = candidate.casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", candidate):
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid email address.")
        return candidate
    if identifier_type is ReportedSuspectIdentifierType.UPI:
        candidate = candidate.casefold()
        if not re.fullmatch(r"[a-z0-9._-]{2,}@[a-z]{2,}", candidate):
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid UPI ID.")
        return candidate
    if identifier_type is ReportedSuspectIdentifierType.BANK_ACCOUNT:
        candidate = re.sub(r"[\s-]", "", candidate).casefold()
        if not re.fullmatch(r"[a-z0-9]{6,34}", candidate):
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid account identifier.")
        return candidate
    if identifier_type is ReportedSuspectIdentifierType.WEBSITE:
        try:
            parts = urlsplit(candidate)
        except ValueError as exc:
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid http or https URL.") from exc
        if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid http or https URL without credentials.")
        host = parts.hostname.casefold()
        port = f":{parts.port}" if parts.port else ""
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.casefold(), host + port, path, parts.query, ""))
    if identifier_type is ReportedSuspectIdentifierType.SOCIAL_MEDIA:
        candidate = candidate.lstrip("@").casefold()
        if not re.fullmatch(r"[a-z0-9._-]{2,100}", candidate):
            raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid social media handle.")
        return candidate
    candidate = " ".join(candidate.casefold().split())
    if len(candidate) < 2:
        raise APIError(status_code=422, code="INVALID_IDENTIFIER", message="Enter a valid identifier.")
    return candidate


def mask_identifier(identifier_type: ReportedSuspectIdentifierType, normalized: str) -> str:
    if identifier_type in {ReportedSuspectIdentifierType.EMAIL, ReportedSuspectIdentifierType.UPI}:
        local, domain = normalized.split("@", 1)
        return local[:2] + "***@" + domain
    if identifier_type is ReportedSuspectIdentifierType.WEBSITE:
        parts = urlsplit(normalized)
        return parts.scheme + "://" + (parts.hostname or "") + "/…"
    if identifier_type is ReportedSuspectIdentifierType.SOCIAL_MEDIA:
        return "@" + normalized[:2] + "***"
    visible = normalized[-4:]
    return "••••" + visible


class ReportedSuspectService:
    @staticmethod
    def create(
        session: Session,
        payload: ReportedSuspectCreate,
        current_user: User,
    ) -> ReportedSuspect:
        report = ReportedSuspect(
            user_id=current_user.id,
            identifier_type=payload.identifier_type,
            identifier_value=payload.identifier_value,
            normalized_identifier=normalize_identifier(payload.identifier_type, payload.identifier_value),
            description=payload.description,
            status=ReportedSuspectStatus.SUBMITTED,
        )
        ReportedSuspectRepository.add(session, report)
        session.commit()
        session.refresh(report)
        return report

    @staticmethod
    def search(session: Session, payload: SuspectSearchRequest) -> SuspectSearchResponse:
        normalized = normalize_identifier(payload.identifier_type, payload.identifier_value)
        count = ReportedSuspectRepository.count_eligible_exact_matches(session, payload.identifier_type, normalized)
        return SuspectSearchResponse(
            identifier_type=payload.identifier_type,
            masked_identifier=mask_identifier(payload.identifier_type, normalized),
            match_state="REPORTED_SIGNAL_FOUND" if count else "NO_ELIGIBLE_SIGNAL_FOUND",
            eligible_report_count=min(count, 5),
            count_capped=count > 5,
            disclosure_code="VERIFIED_REPORT_AGGREGATE_ONLY",
        )

    @staticmethod
    def create_correction(session: Session, payload: SuspectCorrectionCreate) -> SuspectCorrectionRequest:
        normalized = normalize_identifier(payload.identifier_type, payload.identifier_value)
        fingerprint = hmac.new(
            get_settings().secret_key.encode("utf-8"),
            f"{payload.identifier_type.value}:{normalized}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        correction = SuspectCorrectionRequest(
            identifier_type=payload.identifier_type,
            identifier_fingerprint=fingerprint,
            masked_identifier=mask_identifier(payload.identifier_type, normalized),
            reason=payload.reason.strip(),
            status=SuspectCorrectionStatus.SUBMITTED,
        )
        ReportedSuspectRepository.add_correction(session, correction)
        session.commit()
        session.refresh(correction)
        return correction

    @staticmethod
    def list_my_reports(
        session: Session,
        current_user: User,
    ) -> list[ReportedSuspect]:
        return ReportedSuspectRepository.list_for_user(session, current_user.id)

    @staticmethod
    def get_owned_report(
        session: Session,
        report_id: UUID,
        current_user: User,
    ) -> ReportedSuspect:
        report = ReportedSuspectRepository.get_by_id(session, report_id)
        if report is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Reported suspect entry not found.",
            )
        ensure_resource_owner(report.user_id, current_user)
        return report
