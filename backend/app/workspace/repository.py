from datetime import UTC

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import (
    AnalysisResult,
    AnalysisTask,
    Attachment,
    ContextSummary,
    Conversation,
    Message,
    TaskLog,
    WebsocketToken,
    get_utcnow,
)


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: str, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title, status="active")
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def list_for_user(self, user_id: str) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.status != "deleted")
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.status != "deleted",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_ids_for_user(
        self, conversation_ids: list[str], user_id: str
    ) -> list[Conversation]:
        if not conversation_ids:
            return []
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id.in_(conversation_ids),
                Conversation.user_id == user_id,
                Conversation.status != "deleted",
            )
        )
        return list(result.scalars().all())

    async def update_title(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title
        conversation.updated_at = get_utcnow()
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def delete_many(self, conversations: list[Conversation]) -> int:
        ids = [conversation.id for conversation in conversations]
        if not ids:
            return 0

        task_ids = select(AnalysisTask.id).where(AnalysisTask.conversation_id.in_(ids))
        await self.session.execute(
            delete(AnalysisResult).where(AnalysisResult.conversation_id.in_(ids))
        )
        await self.session.execute(delete(TaskLog).where(TaskLog.task_id.in_(task_ids)))
        await self.session.execute(
            delete(AnalysisTask).where(AnalysisTask.conversation_id.in_(ids))
        )
        await self.session.execute(
            delete(Attachment).where(Attachment.conversation_id.in_(ids))
        )
        await self.session.execute(delete(Message).where(Message.conversation_id.in_(ids)))
        await self.session.execute(
            delete(ContextSummary).where(ContextSummary.conversation_id.in_(ids))
        )
        await self.session.execute(
            delete(WebsocketToken).where(WebsocketToken.conversation_id.in_(ids))
        )
        await self.session.execute(delete(Conversation).where(Conversation.id.in_(ids)))
        await self.session.commit()
        return len(ids)


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def next_seq_no(self, conversation_id: str) -> int:
        result = await self.session.execute(
            select(func.max(Message.seq_no)).where(
                Message.conversation_id == conversation_id
            )
        )
        return (result.scalar() or 0) + 1

    async def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        message_type: str = "text",
        tool_name: str | None = None,
        tool_status: str | None = None,
        seq_no: int | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            message_type=message_type,
            content=content,
            tool_name=tool_name,
            tool_status=tool_status,
            seq_no=seq_no if seq_no is not None else await self.next_seq_no(conversation_id),
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_for_conversation(self, conversation_id: str) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.seq_no.asc())
        )
        return list(result.scalars().all())

    async def attachments_for_messages(
        self, message_ids: list[int]
    ) -> dict[int, list[Attachment]]:
        if not message_ids:
            return {}
        result = await self.session.execute(
            select(Attachment)
            .where(Attachment.message_id.in_(message_ids))
            .order_by(Attachment.created_at.asc())
        )
        attachments: dict[int, list[Attachment]] = {}
        for attachment in result.scalars().all():
            if attachment.message_id is not None:
                attachments.setdefault(attachment.message_id, []).append(attachment)
        return attachments


class AttachmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        attachment_id: str,
        conversation_id: str,
        message_id: int | None,
        file_name: str,
        file_path: str,
        file_type: str | None,
        file_size: int,
        parse_status: str = "pending",
    ) -> Attachment:
        attachment = Attachment(
            id=attachment_id,
            conversation_id=conversation_id,
            message_id=message_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            parse_status=parse_status,
        )
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment

    async def get_for_user(self, attachment_id: str, user_id: str) -> Attachment | None:
        result = await self.session.execute(
            select(Attachment)
            .join(Conversation, Conversation.id == Attachment.conversation_id)
            .where(Attachment.id == attachment_id, Conversation.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, attachment: Attachment) -> None:
        await self.session.delete(attachment)
        await self.session.commit()

    async def list_for_conversation(self, conversation_id: str) -> list[Attachment]:
        result = await self.session.execute(
            select(Attachment)
            .where(Attachment.conversation_id == conversation_id)
            .order_by(Attachment.created_at.desc())
        )
        return list(result.scalars().all())


class WebsocketTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: str,
        conversation_id: str,
        token: str,
        expires_at,
    ) -> WebsocketToken:
        row = WebsocketToken(
            user_id=user_id,
            conversation_id=conversation_id,
            token=token,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def consume(self, token: str, conversation_id: str) -> WebsocketToken | None:
        result = await self.session.execute(
            select(WebsocketToken).where(
                WebsocketToken.token == token,
                WebsocketToken.conversation_id == conversation_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None or row.consumed_at is not None:
            return None

        now = get_utcnow()
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < now:
            return None

        row.consumed_at = now
        await self.session.commit()
        await self.session.refresh(row)
        return row
