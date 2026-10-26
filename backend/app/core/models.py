from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def get_utcnow() -> datetime:
    return datetime.now(UTC)


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("user"))
    external_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="analyst")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow, onupdate=get_utcnow
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("conv"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="新会话")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow, onupdate=get_utcnow
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq_no", name="uq_messages_conversation_seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("att"))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("task"))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    task_status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    current_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("res"))
    task_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_metrics_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    evidence_list_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    conclusion_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    missing_data_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_action_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )


class ContextSummary(Base):
    __tablename__ = "context_summaries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("sum"))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    end_seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )


class WebsocketToken(Base):
    __tablename__ = "websocket_tokens"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("wst"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: get_uid("cfg"))
    config_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    config_group: Mapped[str] = mapped_column(
        String(64), nullable=False, default="general", index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow, onupdate=get_utcnow
    )


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    log_type: Mapped[str] = mapped_column(String(32), nullable=False, default="system")
    log_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=get_utcnow
    )


__all__ = [
    "AnalysisResult",
    "AnalysisTask",
    "Attachment",
    "Base",
    "ContextSummary",
    "Conversation",
    "Message",
    "SystemConfig",
    "TaskLog",
    "User",
    "WebsocketToken",
    "get_uid",
    "get_utcnow",
]
