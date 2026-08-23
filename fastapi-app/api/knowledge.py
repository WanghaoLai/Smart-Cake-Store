"""知识库管理 API（仅管理员）"""
import asyncio
import os

from fastapi import APIRouter, Depends, Request, UploadFile, File

from common.audit import client_ip, record_audit
from common.auth import get_current_admin
from common.exception_handler import CustomException
from common.pagination import clamp_page
from common.result import PageInfo, Result
from common.time import format_store_time
from models import Knowledge
from agents.rag import knowledge_service

router = APIRouter(prefix="/knowledge", dependencies=[Depends(get_current_admin)])

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}

# 知识库文档比图片略大也合理，但必须有上限：无上限的全量读入 = 内存耗尽型 DoS
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 1024 * 1024


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise CustomException(f"不支持的文件格式: {ext}，仅支持 .txt .pdf .docx")

    chunks = []
    size = 0
    while chunk := await file.read(CHUNK_SIZE):
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise CustomException(f"文件超过 {MAX_UPLOAD_BYTES // 1024 // 1024}MB 大小限制")
        chunks.append(chunk)
    file_bytes = b"".join(chunks)
    if not file_bytes:
        raise CustomException("文件内容为空")

    info = await asyncio.to_thread(knowledge_service.add_document, file_bytes, file.filename)

    knowledge = await Knowledge.create(
        filename=info["doc_id"],
        original_name=file.filename,
        file_size=info["file_size"],
        chunk_count=info["chunk_count"],
    )

    return Result.success({
        "id": knowledge.id,
        "filename": knowledge.filename,
        "original_name": knowledge.original_name,
        "file_size": knowledge.file_size,
        "chunk_count": knowledge.chunk_count,
        "created_at": format_store_time(knowledge.created_at),
    })


@router.get("/list")
async def doc_list(pageNum: int = 1, pageSize: int = 20):
    pageNum, pageSize = clamp_page(pageNum, pageSize)
    query = Knowledge.all().order_by("-created_at")
    total = await query.count()
    docs = await query.offset((pageNum - 1) * pageSize).limit(pageSize)
    result = []
    for d in docs:
        result.append({
            "id": d.id,
            "filename": d.filename,
            "original_name": d.original_name,
            "file_size": d.file_size,
            "chunk_count": d.chunk_count,
            "created_at": format_store_time(d.created_at),
        })
    return Result.success(PageInfo(total=total, list=result))


@router.delete("/delete/{doc_id}")
async def delete(doc_id: int, current_user: dict = Depends(get_current_admin), request: Request = None):
    knowledge = await Knowledge.get_or_none(id=doc_id)
    if not knowledge:
        raise CustomException("文档不存在")

    await asyncio.to_thread(knowledge_service.delete_document, knowledge.filename)
    await knowledge.delete()
    await record_audit(
        current_user, "knowledge.delete", "knowledge", doc_id,
        detail={"filename": knowledge.original_name},
        ip=client_ip(request),
    )
    return Result.success()


@router.get("/stats")
async def stats():
    stats = await asyncio.to_thread(knowledge_service.get_stats)
    doc_count = await Knowledge.all().count()
    return Result.success({"document_count": doc_count, "chunk_count": stats["total_chunks"]})
