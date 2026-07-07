"""知识库管理 API（仅管理员）"""
import os

from fastapi import APIRouter, Depends, UploadFile, File

from common.auth import get_current_admin
from common.exception_handler import CustomException
from common.result import Result
from models import Knowledge
from services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", dependencies=[Depends(get_current_admin)])

knowledge_service = KnowledgeService()

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise CustomException(f"不支持的文件格式: {ext}，仅支持 .txt .pdf .docx")

    file_bytes = await file.read()
    if not file_bytes:
        raise CustomException("文件内容为空")

    info = knowledge_service.add_document(file_bytes, file.filename)

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
        "created_at": knowledge.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    })


@router.get("/list")
async def doc_list():
    docs = await Knowledge.all().order_by("-created_at")
    result = []
    for d in docs:
        result.append({
            "id": d.id,
            "filename": d.filename,
            "original_name": d.original_name,
            "file_size": d.file_size,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return Result.success(result)


@router.delete("/delete/{doc_id}")
async def delete(doc_id: int):
    knowledge = await Knowledge.get_or_none(id=doc_id)
    if not knowledge:
        raise CustomException("文档不存在")

    knowledge_service.delete_document(knowledge.filename)
    await knowledge.delete()
    return Result.success()


@router.get("/stats")
async def stats():
    stats = knowledge_service.get_stats()
    doc_count = await Knowledge.all().count()
    return Result.success({"document_count": doc_count, "chunk_count": stats["total_chunks"]})
