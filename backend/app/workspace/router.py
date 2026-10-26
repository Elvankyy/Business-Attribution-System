from json import JSONDecodeError
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse

from app.analysis.coordinator import analysis_coordinator
from app.analysis.schemas import ResultResponse
from app.analysis.service import (
    AnalysisResultService,
    ResultNotFound,
    TaskAlreadyRunning,
    TaskNotFound,
)
from app.core import events as realtime_events
from app.core.database import SessionLocal
from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.models import Attachment, Conversation, Message
from app.core.realtime import connection_manager
from app.workspace.schemas import (
    AttachmentDeleteRequest,
    AttachmentDeleteResponse,
    AttachmentItem,
    AttachmentUploadResponse,
    ConversationCreateRequest,
    ConversationDeleteRequest,
    ConversationDeleteResponse,
    ConversationItem,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageAttachmentItem,
    MessageItem,
    WebSocketTokenRequest,
    WebSocketTokenResponse,
)
from app.workspace.service import (
    AttachmentNotFound,
    AttachmentService,
    ConversationNotFound,
    ConversationService,
    MessageService,
    WebSocketTokenService,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
attachment_router = APIRouter(prefix="/api/attachment", tags=["attachment"])
result_router = APIRouter(prefix="/api/results", tags=["results"])


def _to_item(conversation: Conversation) -> ConversationItem:
    return ConversationItem(
        conversation_id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        last_message_at=conversation.last_message_at,
    )


def _to_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        status=conversation.status,
    )


def _to_message_item(message: Message, attachments: list[Attachment]) -> MessageItem:
    return MessageItem(
        message_id=message.id,
        role=message.role,
        message_type=message.message_type,
        content=message.content,
        tool_name=message.tool_name,
        tool_status=message.tool_status,
        attachments=[
            MessageAttachmentItem(
                attachment_id=attachment.id,
                file_name=attachment.file_name,
                file_type=attachment.file_type,
                file_size=attachment.file_size,
                parse_status=attachment.parse_status,
            )
            for attachment in attachments
        ],
        created_at=message.created_at,
    )


@router.post("/create", response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ConversationResponse:
    conversation = await ConversationService(session).create(current_user.id, payload.title)
    return _to_response(conversation)


@router.post("/update", response_model=ConversationResponse)
async def update_conversation(
    payload: ConversationUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ConversationResponse:
    try:
        conversation = await ConversationService(session).update_title(
            current_user.id,
            payload.conversation_id,
            payload.title,
        )
    except ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_response(conversation)


@router.post("/delete", response_model=ConversationDeleteResponse)
async def delete_conversations(
    payload: ConversationDeleteRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ConversationDeleteResponse:
    deleted = await ConversationService(session).delete(
        current_user.id,
        payload.conversation_ids,
    )
    return ConversationDeleteResponse(deleted=deleted)


@router.get("/ls", response_model=list[ConversationItem])
async def list_conversations(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[ConversationItem]:
    conversations = await ConversationService(session).list_for_user(current_user.id)
    return [_to_item(conversation) for conversation in conversations]


@router.get("/ls/{conversation_id}", response_model=list[MessageItem])
async def list_messages(
    conversation_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[MessageItem]:
    try:
        history = await MessageService(session).list_history_with_attachments(
            current_user.id, conversation_id
        )
    except ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问",
        ) from exc
    return [_to_message_item(message, attachments) for message, attachments in history]


@attachment_router.post("/upload", response_model=AttachmentUploadResponse)
async def upload_attachment(
    current_user: CurrentUserDep,
    session: SessionDep,
    conversation_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> AttachmentUploadResponse:
    content = await file.read()
    try:
        attachment = await AttachmentService(session).upload(
            current_user.id,
            conversation_id,
            file.filename or "upload.bin",
            content,
            file.content_type,
        )
    except ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return AttachmentUploadResponse(
        attachment_id=attachment.id,
        file_name=attachment.file_name,
        file_path=attachment.file_path,
    )


@attachment_router.post("/delete", response_model=AttachmentDeleteResponse)
async def delete_attachment(
    payload: AttachmentDeleteRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> AttachmentDeleteResponse:
    try:
        await AttachmentService(session).delete(current_user.id, payload.attachment_id)
    except AttachmentNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="附件不存在或无权访问",
        ) from exc
    return AttachmentDeleteResponse(deleted=True)


@attachment_router.get("/ls", response_model=list[AttachmentItem])
async def list_attachments(
    conversation_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[AttachmentItem]:
    try:
        rows = await AttachmentService(session).list_for_conversation(
            current_user.id, conversation_id
        )
    except ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问",
        ) from exc

    return [
        AttachmentItem(
            attachment_id=row.id,
            file_name=row.file_name,
            file_type=row.file_type,
            file_size=row.file_size,
            parse_status=row.parse_status,
            created_at=row.created_at,
        )
        for row in rows
    ]


@attachment_router.get("/get")
async def get_attachment(
    attachment_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> FileResponse:
    try:
        attachment, path = await AttachmentService(session).get_download(
            current_user.id, attachment_id
        )
    except AttachmentNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="附件不存在或无权访问",
        ) from exc

    return FileResponse(
        path,
        filename=attachment.file_name,
        media_type=attachment.file_type or "application/octet-stream",
    )


@router.post("/ws-token", response_model=WebSocketTokenResponse)
async def issue_websocket_token(
    payload: WebSocketTokenRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> WebSocketTokenResponse:
    try:
        token, ttl = await WebSocketTokenService(session).issue(
            current_user.id, payload.conversation_id
        )
    except ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问",
        ) from exc
    return WebSocketTokenResponse(websocket_token=token, expires_in=ttl)


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    websocket_token: str,
    conversation_id: str,
) -> None:
    async with SessionLocal() as session:
        token_row = await WebSocketTokenService(session).authenticate(
            websocket_token, conversation_id
        )
    if token_row is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await connection_manager.connect(conversation_id, websocket)
    await websocket.send_json(realtime_events.connected(conversation_id))
    user_id = token_row.user_id

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except JSONDecodeError:
                continue

            message_type = data.get("type")
            if message_type == "ping":
                await websocket.send_json(realtime_events.pong())
            elif message_type == "user_message":
                content = str(data.get("content", "")).strip()
                if not content:
                    await websocket.send_json(
                        realtime_events.error("", "消息内容不能为空")
                    )
                    continue
                try:
                    async with SessionLocal() as session:
                        await MessageService(session).append(
                            user_id, conversation_id, "user", content
                        )
                    await analysis_coordinator.start_analysis(
                        user_id, conversation_id, content
                    )
                except TaskAlreadyRunning:
                    await websocket.send_json(
                        realtime_events.error("", "当前会话已有运行中的分析任务")
                    )
                except ConversationNotFound as exc:
                    await websocket.send_json(
                        realtime_events.error("", str(exc))
                    )
            elif message_type == "cancel":
                task_id = str(data.get("task_id", "")).strip()
                if not task_id:
                    await websocket.send_json(
                        realtime_events.error("", "缺少 task_id")
                    )
                    continue
                try:
                    await analysis_coordinator.cancel(task_id, user_id)
                except TaskNotFound:
                    await websocket.send_json(
                        realtime_events.error(task_id, "任务不存在或无权访问")
                    )
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(conversation_id, websocket)


@result_router.get("/{task_id}", response_model=ResultResponse)
async def get_result(
    task_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ResultResponse:
    result = await AnalysisResultService(session).get_for_user(
        task_id, current_user.id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="结果不存在或无权访问",
        )

    return ResultResponse(
        task_id=result.task_id,
        problem_definition=result.problem_definition,
        key_metrics=result.key_metrics_json,
        evidence_list=result.evidence_list_json,
        conclusion_text=result.conclusion_text,
        missing_data_text=result.missing_data_text,
        next_action_text=result.next_action_text,
    )


@result_router.get("/{task_id}/file")
async def get_result_file(
    task_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> FileResponse:
    try:
        _, path = await AnalysisResultService(session).get_file_for_user(
            task_id, current_user.id
        )
    except ResultNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="结果文件不存在或无权访问",
        ) from exc

    return FileResponse(
        path,
        filename=f"{task_id}.md",
        media_type="text/markdown",
    )
