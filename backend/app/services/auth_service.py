from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import hash_password, verify_missing_user_password, verify_password
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegistrationRequest


class AuthService:
    @staticmethod
    def register(session: Session, payload: RegistrationRequest) -> User:
        if payload.role is UserRole.ADMIN:
            raise APIError(
                status_code=403,
                code="FORBIDDEN",
                message="Administrator accounts cannot be self-registered.",
            )

        if UserRepository.get_by_email(session, str(payload.email)) is not None:
            raise APIError(
                status_code=409,
                code="CONFLICT",
                message="An account with these details already exists.",
            )
        if (
            payload.phone is not None
            and UserRepository.get_by_phone(session, payload.phone) is not None
        ):
            raise APIError(
                status_code=409,
                code="CONFLICT",
                message="An account with these details already exists.",
            )

        user = User(
            email=str(payload.email),
            phone=payload.phone,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        UserRepository.add(session, user)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise APIError(
                status_code=409,
                code="CONFLICT",
                message="An account with these details already exists.",
            ) from None

        session.refresh(user)
        return user

    @staticmethod
    def authenticate(session: Session, payload: LoginRequest) -> User | None:
        user = UserRepository.get_by_email(session, str(payload.email))

        if user is None:
            verify_missing_user_password(payload.password)
            return None

        password_is_valid = verify_password(payload.password, user.password_hash)
        if not password_is_valid or not user.is_active:
            return None

        return user
