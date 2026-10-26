from urllib.parse import quote

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from app.auth.adapter import get_auth_adapter
from app.auth.schemas import CurrentUserResponse
from app.auth.service import (
    AuthError,
    AuthService,
    create_access_token,
    create_state,
    verify_state,
)
from app.core.config import get_settings
from app.core.dependencies import CurrentUserDep, SessionDep

router = APIRouter(tags=["auth"])


@router.get("/auth/login")
async def login(as_admin: bool = False) -> RedirectResponse:
    state = create_state("admin" if as_admin else "analyst")
    url = get_auth_adapter().build_authorize_url(state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/auth/callback")
async def callback(code: str, state: str, session: SessionDep) -> RedirectResponse:
    try:
        state_payload = verify_state(state)
        profile = get_auth_adapter().exchange_code(code)
        if state_payload.get("demo_role") == "admin":
            profile = profile.model_copy(
                update={
                    "external_user_id": "demo-admin",
                    "username": "demo-admin",
                    "display_name": "演示管理员",
                    "role": "admin",
                }
            )
    except (AuthError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    user = await AuthService(session).upsert_user(profile)
    token = create_access_token(user)
    settings = get_settings()
    base_url = settings.frontend_base_url.rstrip("/")
    redirect_url = f"{base_url}/auth/callback#token={quote(token, safe='')}"
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)


@router.get("/api/me", response_model=CurrentUserResponse)
async def me(current_user: CurrentUserDep) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
