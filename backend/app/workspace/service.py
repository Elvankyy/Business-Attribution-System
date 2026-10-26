import secrets
from datetime import timedelta
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import (
    Attachment,
    Conversation,
    Message,
    WebsocketToken,
    get_uid,
    get_utcnow,
)
from app.workspace.repository import (
    AttachmentRepository,
    ConversationRepository,
    MessageRepository,
    WebsocketTokenRepository,
)
from app.workspace.storage import (
    delete_conversation_dirs,
    delete_storage_file,
    resolve_storage_path,
    save_upload,
)

ALLOWED_MESSAGE_ROLES = {"user", "assistant", "tool", "system"}


class ConversationNotFound(Exception):
    pass


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ConversationRepository(session)

    async def create(self, user_id: str, title: str) -> Conversation:
        normalized = title.strip() or "新会话"
        return await self.repository.create(user_id, normalized)

    async def list_for_user(self, user_id: str) -> list[Conversation]:
        return await self.repository.list_for_user(user_id)

    async def update_title(
        self, user_id: str, conversation_id: str, title: str
    ) -> Conversation:
        conversation = await self.repository.get_for_user(conversation_id, user_id)
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        normalized = title.strip()
        if not normalized:
            raise ValueError("会话标题不能为空")
        return await self.repository.update_title(conversation, normalized)

    async def delete(self, user_id: str, conversation_ids: list[str]) -> int:
        conversations = await self.repository.list_by_ids_for_user(conversation_ids, user_id)
        deleted = await self.repository.delete_many(conversations)
        for conversation in conversations:
            delete_conversation_dirs(user_id, conversation.id)
        return deleted


class MessageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)

    async def list_history_with_attachments(
        self, user_id: str, conversation_id: str
    ) -> list[tuple[Message, list[Attachment]]]:
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        messages = await self.message_repository.list_for_conversation(conversation_id)
        attachments = await self.message_repository.attachments_for_messages(
            [message.id for message in messages]
        )
        return [(message, attachments.get(message.id, [])) for message in messages]

    async def append(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        *,
        message_type: str = "text",
        tool_name: str | None = None,
        tool_status: str | None = None,
    ) -> Message:
        if role not in ALLOWED_MESSAGE_ROLES:
            raise ValueError(f"不支持的消息角色：{role}")

        last_error: IntegrityError | None = None
        for _ in range(3):
            conversation = await self.conversation_repository.get_for_user(
                conversation_id, user_id
            )
            if conversation is None:
                raise ConversationNotFound(conversation_id)

            try:
                message = await self.message_repository.create(
                    conversation_id,
                    role,
                    content,
                    message_type=message_type,
                    tool_name=tool_name,
                    tool_status=tool_status,
                )
                conversation.last_message_at = message.created_at
                conversation.updated_at = message.created_at
                await self.session.commit()
                await self.session.refresh(message)
                return message
            except IntegrityError as exc:
                await self.session.rollback()
                last_error = exc

        if last_error is not None:
            raise last_error
        raise RuntimeError("消息写入失败")


class AttachmentNotFound(Exception):
    pass


class AttachmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AttachmentRepository(session)
        self.conversation_repository = ConversationRepository(session)

    async def upload(
        self,
        user_id: str,
        conversation_id: str,
        file_name: str,
        content: bytes,
        content_type: str | None,
    ) -> Attachment:
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        attachment_id = get_uid("att")
        settings = get_settings()
        relative_path, safe_name = save_upload(
            content,
            user_id,
            conversation_id,
            attachment_id,
            file_name,
            max_bytes=settings.upload_max_mb * 1024 * 1024,
        )
        try:
            return await self.repository.create(
                attachment_id=attachment_id,
                conversation_id=conversation_id,
                message_id=None,
                file_name=safe_name,
                file_path=relative_path,
                file_type=content_type,
                file_size=len(content),
                parse_status="pending",
            )
        except Exception:
            delete_storage_file(relative_path)
            raise

    async def get_download(
        self, user_id: str, attachment_id: str
    ) -> tuple[Attachment, Path]:
        attachment = await self.repository.get_for_user(attachment_id, user_id)
        if attachment is None:
            raise AttachmentNotFound(attachment_id)

        try:
            path = resolve_storage_path(attachment.file_path)
        except ValueError as exc:
            raise AttachmentNotFound(attachment_id) from exc
        if not path.exists():
            raise AttachmentNotFound(attachment_id)
        return attachment, path

    async def delete(self, user_id: str, attachment_id: str) -> None:
        attachment = await self.repository.get_for_user(attachment_id, user_id)
        if attachment is None:
            raise AttachmentNotFound(attachment_id)

        delete_storage_file(attachment.file_path)
        await self.repository.delete(attachment)

    async def list_for_conversation(
        self, user_id: str, conversation_id: str
    ) -> list[Attachment]:
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)
        return await self.repository.list_for_conversation(conversation_id)


class WebSocketTokenService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = WebsocketTokenRepository(session)
        self.conversation_repository = ConversationRepository(session)

    async def issue(self, user_id: str, conversation_id: str) -> tuple[str, int]:
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        ttl = get_settings().ws_token_ttl_seconds
        token = secrets.token_urlsafe(32)
        await self.repository.create(
            user_id,
            conversation_id,
            token,
            get_utcnow() + timedelta(seconds=ttl),
        )
        return token, ttl

    async def authenticate(
        self, token: str, conversation_id: str
    ) -> WebsocketToken | None:
        row = await self.repository.consume(token, conversation_id)
        if row is None:
            return None
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, row.user_id
        )
        if conversation is None:
            return None
        return row
