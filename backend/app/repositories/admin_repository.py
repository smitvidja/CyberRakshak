from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Complaint, ReportedSuspect


class AdminRepository:
    @staticmethod
    def list_complaints(session: Session) -> list[Complaint]:
        return list(session.scalars(select(Complaint).order_by(Complaint.created_at.desc())))

    @staticmethod
    def list_reported_suspects(session: Session) -> list[ReportedSuspect]:
        return list(
            session.scalars(
                select(ReportedSuspect).order_by(ReportedSuspect.created_at.desc())
            )
        )

    @staticmethod
    def list_audit_logs(session: Session) -> list[AuditLog]:
        return list(session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc())))
