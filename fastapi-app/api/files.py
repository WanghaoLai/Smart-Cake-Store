# 文件上传和下载
import os
import shutil

from fastapi import APIRouter, UploadFile, File, Depends
from starlette.responses import FileResponse

from common.auth import get_current_admin
from common.exception_handler import CustomException
from common.result import Result

UPLOAD_DIR = "files"
router = APIRouter(prefix="/files")

# 文件上传
@router.post("/upload", dependencies=[Depends(get_current_admin)])
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个文件
    """
    # 获取文件信息
    file_location = os.path.join(UPLOAD_DIR, file.filename)

    # 保存文件
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return Result.success("http://127.0.0.1:9090/files/download/" + file.filename)

# 文件下载
@router.get("/download/{filename}")
async def download_file(filename: str):
    """下载文件"""
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise CustomException("文件不存在")

    # 更新下载计数
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )
