from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="新会话", max_length=255)


class ConversationUpdateRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)


class ConversationDeleteRequest(BaseModel):
    conversation_ids: list[str] = Field(min_length=1)


class ConversationItem(BaseModel):
    conversation_id: str
    title: str
    status: str
    last_message_at: datetime | None


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    status: str


class ConversationDeleteResponse(BaseModel):
    deleted: int


class MessageAttachmentItem(BaseModel):
    attachment_id: str
    file_name: str
    file_type: str | None
    file_size: int
    parse_status: str


class MessageItem(BaseModel):
    message_id: int
    role: str
    message_type: str
    content: str
    tool_name: str | None
    tool_status: str | None
    attachments: list[MessageAttachmentItem]
    created_at: datetime


class AttachmentUploadResponse(BaseModel):
    attachment_id: str
    file_name: str
    file_path: str


class AttachmentDeleteRequest(BaseModel):
    attachment_id: str = Field(min_length=1)


class AttachmentDeleteResponse(BaseModel):
    deleted: bool


class AttachmentItem(BaseModel):
    attachment_id: str
    file_name: str
    file_type: str | None
    file_size: int
    parse_status: str
    created_at: datetime


class WebSocketTokenRequest(BaseModel):
    conversation_id: str = Field(min_length=1)


class WebSocketTokenResponse(BaseModel):
    websocket_token: str
    expires_in: int
