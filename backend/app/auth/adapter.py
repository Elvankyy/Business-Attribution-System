from typing import Protocol
from urllib.parse import urlencode

from pydantic import BaseModel

from app.core.config import get_settings


class AuthUserProfile(BaseModel):
    external_user_id: str
    username: str
    display_name: str | None = None
    role: str = "analyst"


class AuthCenterAdapter(Protocol):
    def build_authorize_url(self, state: str) -> str: ...

    def exchange_code(self, code: str) -> AuthUserProfile: ...


class DemoAuthCenter:
    def build_authorize_url(self, state: str) -> str:
        settings = get_settings()
        query = urlencode({"code": "demo", "state": state})
        return f"{settings.auth_redirect_uri}?{query}"

    def exchange_code(self, code: str) -> AuthUserProfile:
        if code != "demo":
            raise ValueError("Demo 认证中心只接受 code=demo")
        return AuthUserProfile(
            external_user_id="demo-user",
            username="demo",
            display_name="演示用户",
            role="analyst",
        )


class HttpAuthCenter:
    def build_authorize_url(self, state: str) -> str:
        raise NotImplementedError("真实认证中心适配器待接入")

    def exchange_code(self, code: str) -> AuthUserProfile:
        raise NotImplementedError("真实认证中心适配器待接入")


def get_auth_adapter() -> AuthCenterAdapter:
    settings = get_settings()
    if settings.auth_mode == "demo":
        return DemoAuthCenter()
    return HttpAuthCenter()
