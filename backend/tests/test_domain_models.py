from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, configure_mappers

from app.core.database import SessionLocal
from app.models import Base, Complaint, ComplaintCategory, User
from app.models.enums import ComplaintPriority, ComplaintStatus, UserRole

APPROVED_TABLES = {
    "audit_logs",
    "citizen_profiles",
    "complaint_categories",
    "complaint_locations",
    "complaint_status_history",
    "complaint_suspects",
    "complaints",
    "cyber_warrior_profiles",
    "evidence",
    "notifications",
    "reported_suspects",
    "resume_parsing_results",
    "skills",
    "users",
    "warrior_applications",
    "warrior_certifications",
    "warrior_education",
    "warrior_experience",
    "warrior_reports",
    "warrior_skills",
}


def test_models_match_the_approved_table_set() -> None:
    configure_mappers()

    assert set(Base.metadata.tables) == APPROVED_TABLES


def test_identified_complaint_relationship_is_configured() -> None:
    category = ComplaintCategory(code="FRAUD", name="Fraud")
    user = User(
        email="citizen@example.test",
        password_hash="not-a-real-password",
        role=UserRole.CITIZEN,
    )
    complaint = Complaint(
        complaint_number="CR-TEST-001",
        category=category,
        user=user,
        is_anonymous=False,
        title="Test complaint",
        description="Relationship configuration test.",
        status=ComplaintStatus.DRAFT,
        priority=ComplaintPriority.NORMAL,
    )

    assert complaint.user is user
    assert complaint in user.complaints
    assert complaint.category is category
    assert complaint in category.complaints


def test_postgresql_rejects_identified_complaint_without_user() -> None:
    session: Session = SessionLocal()
    suffix = uuid4().hex

    try:
        category = ComplaintCategory(
            code=f"TEST-{suffix}",
            name=f"Test category {suffix}",
        )
        session.add(category)
        session.flush()

        invalid_complaint = Complaint(
            complaint_number=f"CR-{suffix}",
            category_id=category.id,
            is_anonymous=False,
            title="Invalid identified complaint",
            description="Database constraint test.",
        )
        session.add(invalid_complaint)

        with pytest.raises(IntegrityError):
            session.flush()
    finally:
        session.rollback()
        session.close()
