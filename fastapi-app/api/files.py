# 文件上传与下载
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
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


def _save(file: UploadFile, category: str) -> str:
    """把上传文件按类别落盘，返回相对子目录的文件名（UUID，杜绝覆盖与路径穿越）。"""
    subdir = CATEGORY_DIRS.get(category)
    if subdir is None:
        raise CustomException(f"未知类别: {category}，可用: {', '.join(CATEGORY_DIRS)}")

    dir_path = UPLOAD_DIR / subdir
    os.makedirs(dir_path, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise CustomException(f"仅支持图片文件: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(dir_path / stored_name, "wb") as buffer:
        buffer.write(file.file.read())
    return f"{subdir}/{stored_name}"


@router.post("/upload", dependencies=[Depends(get_current_admin)])
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Query("goods", description="存储类别: avatar / goods"),
):
    rel_path = _save(file, category)
    # 用请求的 base_url 拼绝对地址，适配任意 host/端口，前端可直接作 img src
    url = f"{request.base_url}files/download/{rel_path}"
    return Result.success(url)


@router.post("/upload_review", dependencies=[Depends(get_current_user)])
async def upload_review_file(
    request: Request,
    file: UploadFile = File(...),
):
    """用户上传评价图。任何登录用户均可调用，但仅限 review 子目录、仅限图片。
    不接受外部 category 参数，避免被滥用写入 avatar/goods。"""
    rel_path = _save(file, "review")
    url = f"{request.base_url}files/download/{rel_path}"
    return Result.success(url)


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