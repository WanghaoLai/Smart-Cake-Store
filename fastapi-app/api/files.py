# 文件上传与下载
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from starlette.responses import FileResponse

from common.auth import get_current_admin, get_current_user
from common.exception_handler import CustomException
from common.result import Result

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


async def _save(file: UploadFile, category: str) -> str:
    """把上传文件按类别分块落盘，返回相对子目录的文件名（UUID，杜绝覆盖与路径穿越）。

    分块读写而非 file.read() 一次性读全量：既限制总大小（超限即中止并清理半成品），
    又避免大文件先整块进内存；await 异步读不阻塞事件循环。"""
    subdir = CATEGORY_DIRS.get(category)
    if subdir is None:
        raise CustomException(f"未知类别: {category}，可用: {', '.join(CATEGORY_DIRS)}")

    dir_path = UPLOAD_DIR / subdir
    os.makedirs(dir_path, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise CustomException(f"仅支持图片文件: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = dir_path / stored_name
    size = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise CustomException(f"文件超过 {MAX_UPLOAD_BYTES // 1024 // 1024}MB 大小限制")
                buffer.write(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
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


@router.post("/upload_review", dependencies=[Depends(get_current_user)])
async def upload_review_file(
    file: UploadFile = File(...),
):
    """用户上传评价图。任何登录用户均可调用，但仅限 review 子目录、仅限图片。
    不接受外部 category 参数，避免被滥用写入 avatar/goods。"""
    rel_path = await _save(file, "review")
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