from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    @staticmethod
    def get_by_id(session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    @staticmethod
    def get_by_email(session: Session, email: str) -> User | None:
        return session.scalar(select(User).where(User.email == email))

    @staticmethod
    def get_by_phone(session: Session, phone: str) -> User | None:
        return session.scalar(select(User).where(User.phone == phone))

    @staticmethod
    def add(session: Session, user: User) -> User:
        session.add(user)
        return user
