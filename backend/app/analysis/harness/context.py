from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Attachment, ContextSummary
from app.workspace.repository import ConversationRepository, MessageRepository
from app.workspace.service import ConversationNotFound


class ContextCompiler:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)

    async def compile(
        self,
        user_id: str,
        conversation_id: str,
        input_text: str,
        char_budget: int = 12000,
    ) -> list[dict[str, str]]:
        if not input_text.strip():
            raise ValueError("分析问题不能为空")

        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        messages = await self.message_repository.list_for_conversation(conversation_id)
        summary_result = await self.session.execute(
            select(ContextSummary)
            .where(ContextSummary.conversation_id == conversation_id)
            .order_by(ContextSummary.end_seq_no.desc())
            .limit(3)
        )
        summaries = list(summary_result.scalars().all())

        attachment_result = await self.session.execute(
            select(Attachment)
            .where(Attachment.conversation_id == conversation_id)
            .order_by(Attachment.created_at.desc())
            .limit(20)
        )
        attachments = list(attachment_result.scalars().all())

        header_parts: list[str] = []
        if summaries:
            summary_lines = [
                f"[{summary.start_seq_no}-{summary.end_seq_no}] {summary.summary_text}"
                for summary in reversed(summaries)
            ]
            header_parts.append("历史摘要：\n" + "\n".join(summary_lines))
        if attachments:
            file_names = "、".join(
                attachment.file_name for attachment in reversed(attachments)
            )
            header_parts.append(f"会话附件：{file_names}")

        history = [
            {"role": message.role, "content": message.content}
            for message in messages
            if message.role in {"user", "assistant"} and message.content.strip()
        ]
        if (
            not history
            or history[-1]["role"] != "user"
            or history[-1]["content"] != input_text
        ):
            history.append({"role": "user", "content": input_text})

        total_chars = sum(len(item["content"]) for item in history)
        while total_chars > char_budget and len(history) > 1:
            removed = history.pop(0)
            total_chars -= len(removed["content"])

        compiled: list[dict[str, str]] = []
        if header_parts:
            compiled.append({"role": "system", "content": "\n\n".join(header_parts)})
        compiled.extend(history)
        return compiled
