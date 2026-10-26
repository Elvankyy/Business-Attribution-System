import shutil
from pathlib import Path

from app.core.config import get_settings

STORAGE_GROUPS = ("uploads", "exports", "workspace")


def safe_path(root: Path, *parts: str) -> Path:
    root_resolved = root.resolve()
    candidate = root_resolved.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("路径超出存储根目录") from exc
    return candidate


def sanitize_filename(name: str) -> str:
    cleaned = (name or "").replace("\\", "/").split("/")[-1].strip()
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError("文件名无效")
    return cleaned


def conversation_dir(group: str, user_id: str, conversation_id: str) -> Path:
    return safe_path(get_settings().storage_path, group, user_id, conversation_id)


def save_upload(
    content: bytes,
    user_id: str,
    conversation_id: str,
    attachment_id: str,
    file_name: str,
    *,
    max_bytes: int | None = None,
) -> tuple[str, str]:
    safe_name = sanitize_filename(file_name)
    if max_bytes is not None and len(content) > max_bytes:
        raise ValueError(f"文件超过大小限制（最大 {max_bytes} 字节）")

    directory = conversation_dir("uploads", user_id, conversation_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = safe_path(directory, f"{attachment_id}_{safe_name}")
    path.write_bytes(content)
    relative_path = path.relative_to(get_settings().storage_path.resolve()).as_posix()
    return relative_path, safe_name


def resolve_storage_path(relative_path: str) -> Path:
    parts = [part for part in relative_path.replace("\\", "/").split("/") if part]
    if any(":" in part or part.startswith(("\\", "/")) for part in parts):
        raise ValueError("路径不合法")
    return safe_path(get_settings().storage_path, *parts)


def delete_storage_file(relative_path: str) -> None:
    resolve_storage_path(relative_path).unlink(missing_ok=True)


def delete_conversation_dirs(user_id: str, conversation_id: str) -> None:
    for group in STORAGE_GROUPS:
        path = conversation_dir(group, user_id, conversation_id)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
