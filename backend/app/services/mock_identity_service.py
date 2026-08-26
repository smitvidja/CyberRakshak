from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import CitizenProfile, MockIdentityProfile, User
from app.models.enums import UserRole
from app.schemas.auth import (
    MockIdentityOtpRequest,
    MockIdentityOtpRequestResponse,
    MockIdentityProfileResponse,
    MockIdentityOtpVerificationRequest,
    MockIdentityVerificationResponse,
)

DEMO_IDENTITIES = (
    {
        "demo_identity_id": "99000000000001",
        "synthetic_email": "rahul.kumar@demo.cyberrakshak.local",
        "registered_mobile": "+91 90000 00001",
        "full_name": "Rahul Kumar",
        "date_of_birth": date(1995, 8, 15),
        "gender": "Male",
        "address": "42 Demo Park, Sector 8",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110024",
        "otp": "123456",
    },
    {
        "demo_identity_id": "99000000000002",
        "synthetic_email": "ananya.shah@demo.cyberrakshak.local",
        "registered_mobile": "+91 90000 00002",
        "full_name": "Ananya Shah",
        "date_of_birth": date(1998, 3, 9),
        "gender": "Female",
        "address": "18 Sample Avenue, Vastrapur",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "postal_code": "380015",
        "otp": "654321",
    },
)


class MockIdentityService:
    """A local-only, synthetic stand-in for identity verification and SMS OTP delivery."""

    @staticmethod
    def request_otp(
        session: Session,
        payload: MockIdentityOtpRequest,
    ) -> MockIdentityOtpRequestResponse:
        identity = MockIdentityService._get_identity(session, payload.demo_identity_id)
        now = datetime.now(timezone.utc)
        identity.otp_requested_at = now
        identity.otp_expires_at = now + timedelta(minutes=10)
        identity.otp_consumed_at = None
        identity.otp_attempts = 0
        session.commit()
        session.refresh(identity)
        return MockIdentityOtpRequestResponse(
            masked_mobile=MockIdentityService._masked_mobile(identity.registered_mobile),
            expires_at=identity.otp_expires_at,
        )

    @staticmethod
    def verify_otp(
        session: Session,
        payload: MockIdentityOtpVerificationRequest,
    ) -> MockIdentityVerificationResponse:
        identity = MockIdentityService._get_identity(session, payload.demo_identity_id)
        now = datetime.now(timezone.utc)
        if identity.otp_requested_at is None or identity.otp_expires_at is None:
            raise APIError(
                status_code=400,
                code="OTP_NOT_REQUESTED",
                message="Request a demo OTP before verification.",
            )
        if identity.otp_consumed_at is not None:
            raise APIError(
                status_code=409,
                code="OTP_ALREADY_USED",
                message="This demo OTP was already used. Request a new one.",
            )
        if identity.otp_expires_at <= now:
            raise APIError(
                status_code=400,
                code="OTP_EXPIRED",
                message="This demo OTP has expired. Request a new one.",
            )
        if identity.otp_attempts >= 5:
            raise APIError(
                status_code=429,
                code="OTP_ATTEMPTS_EXCEEDED",
                message="Too many incorrect attempts. Request a new demo OTP.",
            )
        if not verify_password(payload.otp, identity.otp_code_hash):
            identity.otp_attempts += 1
            session.commit()
            raise APIError(
                status_code=422,
                code="INVALID_OTP",
                message="The demo OTP is incorrect.",
            )

        user = MockIdentityService._get_or_create_user(session, identity, payload.role)
        if payload.role is UserRole.CITIZEN:
            MockIdentityService._create_profile_if_missing(session, user, identity)
        identity.otp_consumed_at = now
        session.commit()
        session.refresh(identity)
        access_token, expires_in = create_access_token(user.id)
        return MockIdentityVerificationResponse(
            access_token=access_token,
            expires_in=expires_in,
            profile=MockIdentityService._profile_response(identity),
        )

    @staticmethod
    def ensure_demo_identities(session: Session) -> None:
        for demo_identity in DEMO_IDENTITIES:
            identity = session.scalar(
                select(MockIdentityProfile).where(
                    MockIdentityProfile.synthetic_email == demo_identity["synthetic_email"]
                )
            )
            if identity is None:
                identity = MockIdentityProfile(
                    synthetic_email=demo_identity["synthetic_email"],
                    otp_code_hash=hash_password(demo_identity["otp"]),
                )
                session.add(identity)
            identity.demo_identity_id = demo_identity["demo_identity_id"]
            identity.registered_mobile = demo_identity["registered_mobile"]
            identity.full_name = demo_identity["full_name"]
            identity.date_of_birth = demo_identity["date_of_birth"]
            identity.gender = demo_identity["gender"]
            identity.address = demo_identity["address"]
            identity.city = demo_identity["city"]
            identity.state = demo_identity["state"]
            identity.postal_code = demo_identity["postal_code"]
        session.commit()

    @staticmethod
    def _get_identity(session: Session, demo_identity_id: str) -> MockIdentityProfile:
        MockIdentityService.ensure_demo_identities(session)
        identity = session.scalar(
            select(MockIdentityProfile).where(
                MockIdentityProfile.demo_identity_id == demo_identity_id
            )
        )
        if identity is None:
            raise APIError(
                status_code=404,
                code="DEMO_IDENTITY_NOT_FOUND",
                message="The synthetic demo identity was not found.",
            )
        return identity

    @staticmethod
    def _get_or_create_user(
        session: Session,
        identity: MockIdentityProfile,
        role: UserRole,
    ) -> User:
        if role is UserRole.CITIZEN and identity.user is not None:
            return identity.user

        email = (
            identity.synthetic_email
            if role is UserRole.CITIZEN
            else MockIdentityService._warrior_email(identity.synthetic_email)
        )
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                phone=identity.registered_mobile if role is UserRole.CITIZEN else None,
                password_hash=hash_password(token_urlsafe(32)),
                role=role,
            )
            session.add(user)
            session.flush()
        if role is UserRole.CITIZEN:
            identity.user = user
        return user

    @staticmethod
    def _warrior_email(synthetic_email: str) -> str:
        local_part, separator, _ = synthetic_email.partition("@")
        if not separator:
            raise ValueError("Synthetic identity email is invalid.")
        return f"{local_part}.warrior@cyberrakshak.example.com"

    @staticmethod
    def _create_profile_if_missing(
        session: Session,
        user: User,
        identity: MockIdentityProfile,
    ) -> CitizenProfile:
        if user.citizen_profile is not None:
            return user.citizen_profile
        profile = CitizenProfile(
            user_id=user.id,
            full_name=identity.full_name,
            date_of_birth=identity.date_of_birth,
            gender=identity.gender,
            address=identity.address,
            city=identity.city,
            state=identity.state,
            postal_code=identity.postal_code,
        )
        session.add(profile)
        return profile

    @staticmethod
    def _profile_response(identity: MockIdentityProfile) -> MockIdentityProfileResponse:
        today = date.today()
        age = today.year - identity.date_of_birth.year - (
            (today.month, today.day) < (identity.date_of_birth.month, identity.date_of_birth.day)
        )
        return MockIdentityProfileResponse(
            full_name=identity.full_name,
            date_of_birth=identity.date_of_birth,
            age=age,
            gender=identity.gender,
            address=identity.address,
            city=identity.city,
            state=identity.state,
            postal_code=identity.postal_code,
            registered_mobile=identity.registered_mobile,
        )

    @staticmethod
    def _masked_mobile(mobile: str) -> str:
        digits = "".join(character for character in mobile if character.isdigit())
        return f"+91 ***** {digits[-5:]}" if len(digits) >= 5 else "Hidden"