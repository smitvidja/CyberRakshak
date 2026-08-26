from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import CitizenProfile, User
from app.schemas.user import CitizenProfileInput


class UserService:
    @staticmethod
    def get_citizen_profile(session: Session, user: User) -> CitizenProfile | None:
        return user.citizen_profile

    @staticmethod
    def upsert_citizen_profile(
        session: Session,
        user: User,
        payload: CitizenProfileInput,
    ) -> CitizenProfile:
        identity = user.mock_identity_profile
        if identity is not None and payload.full_name != identity.full_name:
            raise APIError(
                status_code=400,
                code="PROFILE_IDENTITY_LOCKED",
                message="The verified name cannot be changed in this prototype.",
            )

        profile = user.citizen_profile
        if profile is None:
            profile = CitizenProfile(user_id=user.id, **payload.model_dump())
            session.add(profile)
        else:
            for field, value in payload.model_dump().items():
                setattr(profile, field, value)
        session.commit()
        session.refresh(profile)
        return profile