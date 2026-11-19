from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.admin import AuditLogResponse, ComplaintStatusUpdate, ReportedSuspectStatusUpdate, SuspectCorrectionStatusUpdate, WarriorApplicationStatusUpdate
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.cyber_saathi import (
    KnowledgeGapResponse,
    KnowledgeGapStatusUpdate,
    KnowledgeSourceProposalCreate,
    KnowledgeSourceProposalResponse,
    KnowledgeSourceReview,
)
from app.schemas.complaint import ComplaintResponse, ComplaintSummaryResponse
from app.schemas.suspect import ReportedSuspectResponse, SuspectCorrectionResponse
from app.schemas.warrior import WarriorApplicationResponse
from app.services.admin_service import AdminService
from app.services.knowledge_gap_service import KnowledgeGapService
from app.services.knowledge_source_service import KnowledgeSourceService

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("/complaints", response_model=SuccessResponse[list[ComplaintSummaryResponse]], responses={403: {"model": ErrorResponse}})
def list_complaints(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([ComplaintSummaryResponse.model_validate(item) for item in AdminService.list_complaints(session)])


@router.patch("/complaints/{complaint_id}/status", response_model=SuccessResponse[ComplaintResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_complaint_status(complaint_id: UUID, payload: ComplaintStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(ComplaintResponse.model_validate(AdminService.update_complaint_status(session, complaint_id, payload, current_user)), message="Complaint status updated.")


@router.get("/suspect-reports", response_model=SuccessResponse[list[ReportedSuspectResponse]], responses={403: {"model": ErrorResponse}})
def list_suspect_reports(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([ReportedSuspectResponse.model_validate(item) for item in AdminService.list_reported_suspects(session)])


@router.patch("/suspect-reports/{report_id}/status", response_model=SuccessResponse[ReportedSuspectResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_suspect_status(report_id: UUID, payload: ReportedSuspectStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(ReportedSuspectResponse.model_validate(AdminService.update_reported_suspect_status(session, report_id, payload, current_user)), message="Reported suspect status updated.")


@router.get("/suspect-corrections", response_model=SuccessResponse[list[SuspectCorrectionResponse]], responses={403: {"model": ErrorResponse}})
def list_suspect_corrections(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([SuspectCorrectionResponse.model_validate(item) for item in AdminService.list_suspect_corrections(session)])


@router.patch("/suspect-corrections/{correction_id}/status", response_model=SuccessResponse[SuspectCorrectionResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_suspect_correction_status(correction_id: UUID, payload: SuspectCorrectionStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(SuspectCorrectionResponse.model_validate(AdminService.update_suspect_correction_status(session, correction_id, payload, current_user)), message="Correction request status updated.")


@router.get("/warrior-applications", response_model=SuccessResponse[list[WarriorApplicationResponse]], responses={403: {"model": ErrorResponse}})
def list_applications(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([WarriorApplicationResponse.model_validate(item) for item in AdminService.list_applications(session)])


@router.patch("/warrior-applications/{application_id}/status", response_model=SuccessResponse[WarriorApplicationResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_application_status(application_id: UUID, payload: WarriorApplicationStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(WarriorApplicationResponse.model_validate(AdminService.update_application_status(session, application_id, payload, current_user)), message="Application status updated.")


@router.get("/audit-logs", response_model=SuccessResponse[list[AuditLogResponse]], responses={403: {"model": ErrorResponse}})
def list_audit_logs(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([AuditLogResponse.model_validate(item) for item in AdminService.list_audit_logs(session)])


@router.get(
    "/knowledge-gaps",
    response_model=SuccessResponse[list[KnowledgeGapResponse]],
    responses={403: {"model": ErrorResponse}},
)
def list_knowledge_gaps(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: AdminUser,
    status_filter: Annotated[str | None, Query(alias="status", max_length=24)] = None,
    crime_domain: Annotated[str | None, Query(max_length=64)] = None,
    min_occurrences: Annotated[int, Query(ge=1, le=10000)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, object]:
    """Questions the corpus could not answer, most-asked first.

    The ordering is the point: it turns "we should cover more topics" into a
    ranked list of what citizens actually asked and did not get an answer to.
    """
    gaps = KnowledgeGapService.list_gaps(
        session,
        status=status_filter,
        crime_domain=crime_domain,
        min_occurrences=min_occurrences,
        limit=limit,
    )
    return success_response([KnowledgeGapResponse.model_validate(gap) for gap in gaps])


@router.patch(
    "/knowledge-gaps/{gap_id}/status",
    response_model=SuccessResponse[KnowledgeGapResponse],
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_knowledge_gap_status(
    gap_id: UUID,
    payload: KnowledgeGapStatusUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: AdminUser,
) -> dict[str, object]:
    """Mark a gap reviewed, actioned, or dismissed.

    ACTIONED means a real source was added to the authoritative pack and the
    index rebuilt - see docs/DEPLOYMENT.md section 14. Nothing here writes to the
    corpus: citizen text is not an authoritative source.
    """
    gap = KnowledgeGapService.update_status(
        session, gap_id, status=payload.status, resolution_note=payload.resolution_note
    )
    return success_response(
        KnowledgeGapResponse.model_validate(gap), message="Knowledge gap updated."
    )


@router.post(
    "/knowledge-sources",
    status_code=201,
    response_model=SuccessResponse[KnowledgeSourceProposalResponse],
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def propose_knowledge_source(
    payload: KnowledgeSourceProposalCreate,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: AdminUser,
) -> dict[str, object]:
    """Propose an excerpt from an official publication to close a knowledge gap.

    Pending until a *different* administrator approves it, and only reaches
    citizens after the publish step writes it into the versioned source pack.
    """
    proposal = KnowledgeSourceService.propose(session, payload, current_user)
    return success_response(
        KnowledgeSourceProposalResponse.model_validate(proposal), message="Source proposed for review."
    )


@router.get(
    "/knowledge-sources",
    response_model=SuccessResponse[list[KnowledgeSourceProposalResponse]],
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def list_knowledge_sources(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: AdminUser,
    status_filter: Annotated[str | None, Query(alias="status", max_length=16)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, object]:
    proposals = KnowledgeSourceService.list(session, status=status_filter, limit=limit)
    return success_response([KnowledgeSourceProposalResponse.model_validate(item) for item in proposals])


@router.patch(
    "/knowledge-sources/{proposal_id}/review",
    response_model=SuccessResponse[KnowledgeSourceProposalResponse],
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def review_knowledge_source(
    proposal_id: UUID,
    payload: KnowledgeSourceReview,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: AdminUser,
) -> dict[str, object]:
    """Approve or reject a pending proposal. The proposer cannot review their own (403)."""
    proposal = KnowledgeSourceService.review(
        session, proposal_id, decision=payload.decision, review_note=payload.review_note, admin=current_user
    )
    return success_response(
        KnowledgeSourceProposalResponse.model_validate(proposal), message="Proposal reviewed."
    )
