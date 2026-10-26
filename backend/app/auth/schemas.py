from pydantic import BaseModel, ConfigDict


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_user_id: str | None
    username: str
    display_name: str | None
    role: str
    status: str
