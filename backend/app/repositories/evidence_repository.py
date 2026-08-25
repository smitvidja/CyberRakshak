from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Evidence, WarriorReport


class EvidenceRepository:
    @staticmethod
    def add(session: Session, evidence: Evidence) -> Evidence:
        session.add(evidence)
        return evidence

    @staticmethod
    def get_by_id(session: Session, evidence_id: UUID) -> Evidence | None:
        return session.get(Evidence, evidence_id)

    @staticmethod
    def get_warrior_report_with_owner(
        session: Session,
        warrior_report_id: UUID,
    ) -> WarriorReport | None:
        statement = (
            select(WarriorReport)
            .options(selectinload(WarriorReport.warrior))
            .where(WarriorReport.id == warrior_report_id)
        )
        return session.scalar(statement)

    @staticmethod
    def delete(session: Session, evidence: Evidence) -> None:
        session.delete(evidence)
