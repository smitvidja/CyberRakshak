from sqlalchemy.orm import Session

from app.models import CitizenProfile, User
from app.schemas.user import CitizenProfileInput


class UserService:
    @staticmethod
    def get_citizen_profile(session: Session, user: User) -> CitizenProfile | None:
        return user.citizen_profile

    @staticmethod
    def upsert_citizen_profile(session: Session, user: User, payload: CitizenProfileInput) -> CitizenProfile:
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
