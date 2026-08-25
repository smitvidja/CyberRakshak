from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.errors import APIError
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

password_hash = PasswordHash.recommended()
dummy_password_hash = password_hash.hash("not-a-real-password")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except ValueError:
        return False


def verify_missing_user_password(password: str) -> None:
    password_hash.verify(password, dummy_password_hash)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    token = jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def get_optional_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> User | None:
    if credentials is None:
        return None

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise APIError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Could not validate credentials.",
        ) from None

    user = UserRepository.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise APIError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Could not validate credentials.",
        )

    return user


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[Session, Depends(get_db_session)],
) -> User:
    current_user = get_optional_current_user(credentials, session)
    if current_user is None:
        raise APIError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Authentication is required.",
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise APIError(
                status_code=403,
                code="FORBIDDEN",
                message="You do not have permission to perform this action.",
            )
        return current_user

    return role_dependency


def ensure_resource_owner(
    resource_user_id: UUID | None,
    current_user: User,
) -> None:
    if current_user.role is UserRole.ADMIN:
        return
    if resource_user_id is None or resource_user_id != current_user.id:
        raise APIError(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have permission to access this resource.",
        )
