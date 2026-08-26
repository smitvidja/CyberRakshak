from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Complaint, ComplaintCategory, ComplaintStatusHistory


class ComplaintRepository:
    @staticmethod
    def list_active_categories(session: Session) -> list[ComplaintCategory]:
        statement = (
            select(ComplaintCategory)
            .where(ComplaintCategory.is_active.is_(True))
            .order_by(ComplaintCategory.name)
        )
        return list(session.scalars(statement))

    @staticmethod
    def get_category(session: Session, category_id: UUID) -> ComplaintCategory | None:
        return session.get(ComplaintCategory, category_id)

    @staticmethod
    def get_with_details(session: Session, complaint_id: UUID) -> Complaint | None:
        statement = (
            select(Complaint)
            .options(
                selectinload(Complaint.category),
                selectinload(Complaint.location),
                selectinload(Complaint.suspects),
                selectinload(Complaint.status_history),
            )
            .where(Complaint.id == complaint_id)
        )
        return session.scalar(statement)

    @staticmethod
    def get_by_number(session: Session, complaint_number: str) -> Complaint | None:
        statement = (
            select(Complaint)
            .options(selectinload(Complaint.status_history))
            .where(Complaint.complaint_number == complaint_number)
        )
        return session.scalar(statement)

    @staticmethod
    def list_for_user(session: Session, user_id: UUID) -> list[Complaint]:
        statement = (
            select(Complaint)
            .where(Complaint.user_id == user_id)
            .order_by(Complaint.created_at.desc())
        )
        return list(session.scalars(statement))

    @staticmethod
    def add(session: Session, complaint: Complaint) -> Complaint:
        session.add(complaint)
        return complaint

    @staticmethod
    def add_status_history(
        session: Session,
        status_history: ComplaintStatusHistory,
    ) -> ComplaintStatusHistory:
        session.add(status_history)
        return status_history
