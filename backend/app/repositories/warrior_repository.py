from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CyberWarriorProfile,
    ResumeParsingResult,
    Skill,
    WarriorApplication,
    WarriorReport,
)


class WarriorRepository:
    @staticmethod
    def get_profile_with_details(
        session: Session,
        user_id: UUID,
    ) -> CyberWarriorProfile | None:
        statement = (
            select(CyberWarriorProfile)
            .options(
                selectinload(CyberWarriorProfile.skills),
                selectinload(CyberWarriorProfile.education),
                selectinload(CyberWarriorProfile.experience),
                selectinload(CyberWarriorProfile.certifications),
            )
            .where(CyberWarriorProfile.user_id == user_id)
        )
        return session.scalar(statement)

    @staticmethod
    def get_skill(session: Session, skill_id: UUID) -> Skill | None:
        return session.get(Skill, skill_id)

    @staticmethod
    def list_skills(session: Session) -> list[Skill]:
        return list(session.scalars(select(Skill).order_by(Skill.name)))

    @staticmethod
    def add(session: Session, entity: object) -> object:
        session.add(entity)
        return entity

    @staticmethod
    def get_resume_result(
        session: Session,
        result_id: UUID,
    ) -> ResumeParsingResult | None:
        return session.get(ResumeParsingResult, result_id)

    @staticmethod
    def get_application(
        session: Session,
        application_id: UUID,
    ) -> WarriorApplication | None:
        return session.get(WarriorApplication, application_id)

    @staticmethod
    def list_applications(
        session: Session,
        warrior_id: UUID | None = None,
    ) -> list[WarriorApplication]:
        statement = select(WarriorApplication).order_by(WarriorApplication.created_at.desc())
        if warrior_id is not None:
            statement = statement.where(WarriorApplication.warrior_id == warrior_id)
        return list(session.scalars(statement))

    @staticmethod
    def get_report(session: Session, report_id: UUID) -> WarriorReport | None:
        return session.get(WarriorReport, report_id)

    @staticmethod
    def list_reports(session: Session, warrior_id: UUID) -> list[WarriorReport]:
        statement = (
            select(WarriorReport)
            .where(WarriorReport.warrior_id == warrior_id)
            .order_by(WarriorReport.created_at.desc())
        )
        return list(session.scalars(statement))

    @staticmethod
    def delete_report(session: Session, report: WarriorReport) -> None:
        session.delete(report)
