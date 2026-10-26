from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.adapter import AuthUserProfile
from app.core.config import get_settings
from app.core.models import User


class AuthError(Exception):
    pass


def create_state(role: str = "analyst") -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "purpose": "oauth_state",
        "demo_role": role,
        "nonce": uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_state(state: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            state,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise AuthError("授权 state 无效或已过期") from exc
    if payload.get("purpose") != "oauth_state":
        raise AuthError("授权 state 用途不正确")
    return payload


def create_access_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise AuthError("访问令牌无效或已过期") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise AuthError("访问令牌类型不正确")
    return payload


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_user(self, profile: AuthUserProfile) -> User:
        stmt = select(User).where(
            or_(
                User.external_user_id == profile.external_user_id,
                User.username == profile.username,
            )
        )
        result = await self.session.execute(stmt)
        user = result.scalars().first()

        if user is None:
            user = User(
                external_user_id=profile.external_user_id,
                username=profile.username,
                display_name=profile.display_name,
                role=profile.role,
                status="active",
            )
            self.session.add(user)
        else:
            user.external_user_id = profile.external_user_id
            user.username = profile.username
            user.display_name = profile.display_name
            user.role = profile.role
            user.status = "active"

        await self.session.commit()
        await self.session.refresh(user)
        return user
