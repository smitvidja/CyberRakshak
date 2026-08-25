import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, configure_mappers

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from database.seeds.seed_reference_data import (
    COMPLAINT_CATEGORIES,
    SKILLS,
    seed_reference_data,
)

from app.core.database import SessionLocal, engine
from app.models import Base, Complaint, ComplaintCategory, Evidence, Skill, User
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

REQUIRED_QUERY_INDEXES = {
    "audit_logs": {
        "ix_audit_logs_created_at",
        "ix_audit_logs_entity_id",
        "ix_audit_logs_entity_type",
        "ix_audit_logs_user_id",
    },
    "complaint_status_history": {"ix_complaint_status_history_complaint_id"},
    "complaint_suspects": {"ix_complaint_suspects_complaint_id"},
    "complaints": {
        "ix_complaints_category_id",
        "ix_complaints_created_at",
        "ix_complaints_status",
        "ix_complaints_user_id",
    },
    "cyber_warrior_profiles": {"ix_cyber_warrior_profiles_verification_status"},
    "evidence": {
        "ix_evidence_complaint_id",
        "ix_evidence_suspect_report_id",
        "ix_evidence_warrior_report_id",
    },
    "notifications": {"ix_notifications_is_read", "ix_notifications_user_id"},
    "reported_suspects": {
        "ix_reported_suspects_identifier_type",
        "ix_reported_suspects_identifier_value",
        "ix_reported_suspects_status",
    },
    "users": {"ix_users_role"},
    "warrior_applications": {
        "ix_warrior_applications_status",
        "ix_warrior_applications_warrior_id",
    },
    "warrior_reports": {"ix_warrior_reports_status", "ix_warrior_reports_warrior_id"},
}

REQUIRED_UNIQUE_INDEX_COLUMNS = {
    "users": {("email",), ("phone",)},
    "complaints": {("complaint_number",)},
    "cyber_warrior_profiles": {("user_id",)},
    "warrior_applications": {("application_number",)},
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


def test_postgresql_accepts_anonymous_complaint_without_user() -> None:
    session: Session = SessionLocal()
    suffix = uuid4().hex

    try:
        category = ComplaintCategory(
            code=f"TEST-{suffix}",
            name=f"Test category {suffix}",
        )
        complaint = Complaint(
            complaint_number=f"CR-{suffix}",
            category=category,
            is_anonymous=True,
            title="Anonymous complaint",
            description="Anonymous complaint constraint test.",
        )
        session.add(complaint)
        session.flush()

        assert complaint.id is not None
        assert complaint.user_id is None
    finally:
        session.rollback()
        session.close()


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


def test_postgresql_rejects_evidence_without_supported_parent() -> None:
    session: Session = SessionLocal()

    try:
        session.add(
            Evidence(
                file_name="synthetic.txt",
                file_url="https://example.invalid/synthetic.txt",
                storage_key="tests/synthetic.txt",
                mime_type="text/plain",
                file_size=1,
            )
        )

        with pytest.raises(IntegrityError):
            session.flush()
    finally:
        session.rollback()
        session.close()


def test_required_query_indexes_exist_in_postgresql() -> None:
    inspector = inspect(engine)

    for table_name, expected_indexes in REQUIRED_QUERY_INDEXES.items():
        actual_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        assert expected_indexes <= actual_indexes

    for table_name, expected_columns in REQUIRED_UNIQUE_INDEX_COLUMNS.items():
        unique_columns = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)
        }
        assert expected_columns <= unique_columns


def test_reference_data_seed_is_idempotent() -> None:
    session: Session = SessionLocal()
    category_codes = {category["code"] for category in COMPLAINT_CATEGORIES}
    skill_names = {skill["name"] for skill in SKILLS}

    try:
        seed_reference_data(session)
        session.flush()

        first_category_count = session.scalar(
            select(func.count())
            .select_from(ComplaintCategory)
            .where(ComplaintCategory.code.in_(category_codes))
        )
        first_skill_count = session.scalar(
            select(func.count()).select_from(Skill).where(Skill.name.in_(skill_names))
        )

        added_on_second_run = seed_reference_data(session)
        session.flush()

        second_category_count = session.scalar(
            select(func.count())
            .select_from(ComplaintCategory)
            .where(ComplaintCategory.code.in_(category_codes))
        )
        second_skill_count = session.scalar(
            select(func.count()).select_from(Skill).where(Skill.name.in_(skill_names))
        )

        assert first_category_count == len(COMPLAINT_CATEGORIES)
        assert first_skill_count == len(SKILLS)
        assert added_on_second_run == (0, 0)
        assert second_category_count == first_category_count
        assert second_skill_count == first_skill_count
    finally:
        session.rollback()
        session.close()
