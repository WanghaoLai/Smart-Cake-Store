# 文件上传与下载
import asyncio
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from starlette.responses import FileResponse

from common.auth import get_current_admin, get_current_customer
from common.exception_handler import CustomException
from common.rate_limit import SlidingWindowRateLimiter
from common.result import Result
from settings import (
    REVIEW_UPLOAD_GLOBAL_QUOTA_BYTES,
    REVIEW_UPLOAD_RATE_LIMIT,
    REVIEW_UPLOAD_RATE_WINDOW_SECONDS,
    REVIEW_UPLOAD_USER_QUOTA_BYTES,
)

router = APIRouter(prefix="/files")

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "files"

# 按业务类型分子目录存储，便于视图与维护
#   files/avatar/  头像
#   files/goods/   商品图
#   files/review/  评价图（用户上传）
CATEGORY_DIRS = {
    "avatar": "avatar",
    "goods": "goods",
    "review": "review",
}

# 头像/商品图等仅允许图片，降低存储被滥用风险
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# 上传容量上限：多用户公网环境下无上限 = 资源耗尽型 DoS（占满内存/磁盘拖垮整个服务）
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
CHUNK_SIZE = 1024 * 1024  # 1MB

review_upload_limiter = SlidingWindowRateLimiter(
    REVIEW_UPLOAD_RATE_LIMIT, REVIEW_UPLOAD_RATE_WINDOW_SECONDS,
)
# 单进程内把“检查配额 + 写文件”作为一个临界区，避免并发请求同时穿透配额。
_upload_quota_lock = asyncio.Lock()


def _image_kind(header: bytes) -> str | None:
    """仅信任文件签名，不信任客户端 Content-Type/扩展名。"""
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _append_chunk(path: Path, chunk: bytes) -> None:
    with path.open("ab") as buffer:
        buffer.write(chunk)


def _usage_bytes(directory: Path, prefix: str | None = None) -> int:
    if not directory.exists():
        return 0
    return sum(
        item.stat().st_size
        for item in directory.iterdir()
        if item.is_file() and (prefix is None or item.name.startswith(prefix))
    )


async def _save(file: UploadFile, category: str, owner_id: int | None = None) -> str:
    """把上传文件按类别分块落盘，返回相对子目录的文件名（UUID，杜绝覆盖与路径穿越）。

    分块读写而非 file.read() 一次性读全量：既限制总大小（超限即中止并清理半成品），
    又避免大文件先整块进内存；await 异步读不阻塞事件循环。"""
    subdir = CATEGORY_DIRS.get(category)
    if subdir is None:
        raise CustomException(f"未知类别: {category}，可用: {', '.join(CATEGORY_DIRS)}")

    dir_path = UPLOAD_DIR / subdir
    await asyncio.to_thread(os.makedirs, dir_path, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise CustomException(f"仅支持图片文件: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    owner_prefix = f"user_{owner_id}_" if category == "review" and owner_id is not None else ""
    stored_name = f"{owner_prefix}{uuid.uuid4().hex}{ext}"
    file_path = dir_path / stored_name
    size = 0
    async with _upload_quota_lock:
        global_usage = await asyncio.to_thread(_usage_bytes, dir_path) if category == "review" else 0
        user_usage = (
            await asyncio.to_thread(_usage_bytes, dir_path, owner_prefix)
            if category == "review" and owner_prefix else 0
        )
        try:
            await asyncio.to_thread(file_path.write_bytes, b"")
            first_chunk = True
            while chunk := await file.read(CHUNK_SIZE):
                if first_chunk:
                    kind = _image_kind(chunk[:16])
                    expected = "jpeg" if ext in {".jpg", ".jpeg"} else ext.removeprefix(".")
                    if kind is None or kind != expected:
                        raise CustomException("文件内容与图片格式不匹配")
                    first_chunk = False
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise CustomException(f"文件超过 {MAX_UPLOAD_BYTES // 1024 // 1024}MB 大小限制")
                if category == "review":
                    if user_usage + size > REVIEW_UPLOAD_USER_QUOTA_BYTES:
                        raise CustomException("当前用户的评价图片存储配额已用完")
                    if global_usage + size > REVIEW_UPLOAD_GLOBAL_QUOTA_BYTES:
                        raise CustomException("评价图片存储空间不足，请联系管理员")
                # 本地磁盘写入下沉到线程，避免阻塞 FastAPI 事件循环。
                await asyncio.to_thread(_append_chunk, file_path, chunk)
        except Exception:
            await asyncio.to_thread(file_path.unlink, missing_ok=True)
            raise
    if size == 0:
        await asyncio.to_thread(file_path.unlink, missing_ok=True)
        raise CustomException("文件内容为空")
    return f"{subdir}/{stored_name}"


@router.post("/upload", dependencies=[Depends(get_current_admin)])
async def upload_file(
    file: UploadFile = File(...),
    category: str = Query("goods", description="存储类别: avatar / goods"),
):
    """上传成功只返回相对路径（files/download/...）。

    历史做法用 request.base_url 拼绝对地址入库：一旦部署域名/端口变化，
    所有历史头像与商品图全部失效。入库与出参统一相对路径，
    绝对地址由前端按当前环境拼接（utils/fileUrl.js）。"""
    rel_path = await _save(file, category)
    return Result.success(f"files/download/{rel_path}")


@router.post("/upload_review")
async def upload_review_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_customer),
):
    """用户上传评价图。任何登录用户均可调用，但仅限 review 子目录、仅限图片。
    不接受外部 category 参数，避免被滥用写入 avatar/goods。"""
    limiter_key = f"{current_user['role']}:{current_user['user_id']}"
    if not review_upload_limiter.allow(limiter_key):
        raise HTTPException(
            status_code=429,
            detail=(
            f"上传过于频繁，每 {REVIEW_UPLOAD_RATE_WINDOW_SECONDS} 秒"
            f"最多 {REVIEW_UPLOAD_RATE_LIMIT} 个文件"
            ),
        )
    rel_path = await _save(file, "review", owner_id=current_user["user_id"])
    return Result.success(f"files/download/{rel_path}")


@router.get("/download/{category}/{filename}")
async def download_file(category: str, filename: str):
    subdir = CATEGORY_DIRS.get(category)
    if subdir is None:
        raise CustomException(f"未知类别: {category}")

    # 仅允许文件名本身，拒绝路径穿越（如 ../../etc/passwd）
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise CustomException("非法文件名")

    file_path = UPLOAD_DIR / subdir / safe_name
    if not file_path.exists():
        raise CustomException("文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type="application/octet-stream",
    )


@router.get("/download/{filename}")
async def download_legacy(filename: str):
    """兼容旧数据：旧 DB 中存的是 /files/download/<flat 文件名>，
    在各类别子目录中查找同名文件，保证历史 URL 仍可用。"""
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise CustomException("非法文件名")

    for subdir in CATEGORY_DIRS.values():
        candidate = UPLOAD_DIR / subdir / safe_name
        if candidate.exists():
            return FileResponse(
                path=str(candidate),
                filename=safe_name,
                media_type="application/octet-stream",
            )

    raise CustomException("文件不存在")
