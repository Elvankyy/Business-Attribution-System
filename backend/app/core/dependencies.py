from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthError, decode_access_token
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.models import User

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未提供有效的访问令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
) -> User:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
    except AuthError as exc:
        raise _unauthorized() from exc
    user = await session.get(User, payload["sub"])
    if user is None or user.status != "active":
        raise _unauthorized()
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def require_admin(current_user: CurrentUserDep) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


AdminUserDep = Annotated[User, Depends(require_admin)]
