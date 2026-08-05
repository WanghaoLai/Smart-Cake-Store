"""知识库服务 - 文档解析、分块、向量化、ChromaDB 存储与检索"""
import asyncio
import logging
import os
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings
from dashscope import TextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import Goods, IndexTask
from settings import AI_CONFIG

logger = logging.getLogger(__name__)

CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

DOC_COLLECTION = "knowledge_base"
GOODS_COLLECTION = "goods_base"

INDEX_TASK_MAX_ATTEMPTS = 3


class KnowledgeService:
    def __init__(self, embedding_model: str = None):
        self.embedding_model = embedding_model or AI_CONFIG.get("embedding_model", "text-embedding-v2")
        self._client = None
        self._collection = None
        self._goods_collection = None
        self._text_splitter = None

    @property
    def client(self):
        if self._client is None:
            os.makedirs(CHROMA_PATH, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=CHROMA_PATH, settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(name=DOC_COLLECTION)
        return self._collection

    @property
    def goods_collection(self):
        if self._goods_collection is None:
            self._goods_collection = self.client.get_or_create_collection(name=GOODS_COLLECTION)
        return self._goods_collection

    @property
    def text_splitter(self):
        if self._text_splitter is None:
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
            )
        return self._text_splitter

    # ==================== 文档知识库 ====================

    def parse_file(self, file_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".txt":
            return file_bytes.decode("utf-8", errors="ignore")
        elif ext == ".pdf":
            return self._parse_pdf(file_bytes)
        elif ext == ".docx":
            return self._parse_docx(file_bytes)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _parse_pdf(self, file_bytes: bytes) -> str:
        from PyPDF2 import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _parse_docx(self, file_bytes: bytes) -> str:
        from docx import Document
        from io import BytesIO
        doc = Document(BytesIO(file_bytes))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n".join(text_parts)

    def split_text(self, text: str) -> list:
        return self.text_splitter.split_text(text)

    def _get_embeddings(self, texts: list) -> list:
        embeddings = []
        batch_size = 25
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = TextEmbedding.call(model=self.embedding_model, input=batch)
            if response.status_code == 200:
                for item in response.output["embeddings"]:
                    embeddings.append(item["embedding"])
            else:
                raise Exception(f"Embedding 调用失败: {response.message}")
        return embeddings

    def add_document(self, file_bytes: bytes, filename: str) -> dict:
        text = self.parse_file(file_bytes, filename)
        if not text.strip():
            raise ValueError("文档内容为空，无法解析")

        chunks = self.split_text(text)
        if not chunks:
            raise ValueError("文档分块后无有效内容")

        embeddings = self._get_embeddings(chunks)
        doc_uuid = uuid.uuid4().hex
        ids = [f"{doc_uuid}_{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_uuid, "filename": filename, "chunk_index": i, "type": "document"}
                     for i in range(len(chunks))]

        self.collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

        return {"doc_id": doc_uuid, "chunk_count": len(chunks), "file_size": len(file_bytes)}

    def delete_document(self, doc_id: str):
        results = self.collection.get(where={"doc_id": doc_id})
        if results.get("ids"):
            self.collection.delete(ids=results["ids"])

    # ==================== 商品向量库 ====================

    @staticmethod
    def _format_goods_doc(goods) -> str:
        cat_name = "未分类"
        try:
            if hasattr(goods, 'category') and goods.category:
                cat_name = goods.category.name
        except Exception:
            pass
        return (
            f"商品名称：{goods.name} | 价格：{goods.price}元 | "
            f"库存：{goods.num}{goods.unit or '个'} | 分类：{cat_name} | "
            f"描述：{goods.description}"
        )

    def sync_goods(self, goods):
        """同步单个商品到向量库（新增或更新）"""
        doc = self._format_goods_doc(goods)
        embedding = self._get_embeddings([doc])
        goods_id = str(goods.id)

        existing = self.goods_collection.get(where={"goods_id": goods_id})
        if existing.get("ids"):
            self.goods_collection.update(
                ids=existing["ids"],
                embeddings=embedding,
                documents=[doc],
            )
        else:
            self.goods_collection.add(
                ids=[f"goods_{goods_id}"],
                embeddings=embedding,
                documents=[doc],
                metadatas=[{"goods_id": goods_id, "type": "goods", "name": goods.name}],
            )

    def sync_all_goods(self, goods_list: list):
        """全量重建商品向量索引"""
        existing = self.goods_collection.get(where={"type": "goods"})
        if existing.get("ids"):
            self.goods_collection.delete(ids=existing["ids"])

        if not goods_list:
            return

        docs = [self._format_goods_doc(g) for g in goods_list]
        embeddings = self._get_embeddings(docs)
        ids = [f"goods_{g.id}" for g in goods_list]
        metadatas = [{"goods_id": str(g.id), "type": "goods", "name": g.name} for g in goods_list]

        self.goods_collection.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)
        logger.info(f"商品向量索引已重建，共 {len(goods_list)} 条")

    def remove_goods(self, goods_id: int):
        """从向量库删除指定商品"""
        existing = self.goods_collection.get(where={"goods_id": str(goods_id)})
        if existing.get("ids"):
            self.goods_collection.delete(ids=existing["ids"])

    # ==================== 统一检索 ====================

    def _query_collection(self, col, query: str, top_k: int, source_label: str) -> list:
        query_embedding = self._get_embeddings([query])
        results = col.query(query_embeddings=query_embedding, n_results=top_k)

        docs = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                docs.append({
                    "content": doc,
                    "source": source_label,
                    "filename": meta.get("filename", meta.get("name", "")),
                    "score": float(results["distances"][0][i]) if results.get("distances") else 0,
                })
        return docs

    def search_documents(self, query: str, top_k: int = 3) -> list:
        """仅检索文档知识库"""
        return self._query_collection(self.collection, query, top_k, "knowledge_base")

    def search_goods(self, query: str, top_k: int = 3) -> list:
        """仅检索商品向量库"""
        return self._query_collection(self.goods_collection, query, top_k, "goods_base")

    def search(self, query: str, top_k: int = 3) -> list:
        """同时检索文档知识库和商品向量库，合并返回"""
        doc_results = self.search_documents(query, top_k)
        goods_results = self.search_goods(query, top_k)
        return doc_results + goods_results

    # ==================== 统计 ====================

    def get_stats(self) -> dict:
        doc_count = self.collection.count()
        goods_count = self.goods_collection.count()
        return {"document_chunks": doc_count, "goods_count": goods_count, "total_chunks": doc_count + goods_count}

    # ==================== Outbox 索引任务 ====================

    async def process_index_task(self, task_id: int) -> None:
        """处理单条索引任务，带边界重试。
        - sync_goods / remove_goods 是幂等的，重试安全
        - 超过 INDEX_TASK_MAX_ATTEMPTS 后置为 failed，待管理员通过 run-pending 兜底
        """
        task = await IndexTask.get_or_none(id=task_id)
        if task is None or task.status == 'done':
            return
        if task.attempts >= INDEX_TASK_MAX_ATTEMPTS:
            return

        try:
            if task.entity_type == 'goods' and task.action == 'upsert':
                goods = await Goods.get_or_none(id=task.entity_id).prefetch_related('category')
                if goods is not None:
                    self.sync_goods(goods)
                # goods 已被删除则视为完成，避免悬空任务
            elif task.entity_type == 'goods' and task.action == 'delete':
                self.remove_goods(task.entity_id)
            # 未知 entity/action 一律视为完成，防止无限重试

            await IndexTask.filter(id=task.id).update(
                status='done',
                attempts=task.attempts + 1,
                last_error=None,
            )
        except Exception as e:
            new_attempts = task.attempts + 1
            await IndexTask.filter(id=task.id).update(
                status='failed' if new_attempts >= INDEX_TASK_MAX_ATTEMPTS else 'pending',
                attempts=new_attempts,
                last_error=str(e)[:500],
            )
            logger.warning("index task %s failed (attempt %d/%d): %s",
                           task_id, new_attempts, INDEX_TASK_MAX_ATTEMPTS, e)
            raise

    async def run_pending_tasks(self, limit: int = 100) -> dict:
        """兜底批处理：扫描 pending/failed 任务依次重跑，返回统计。"""
        tasks = await IndexTask.filter(
            status__in=['pending', 'failed']
        ).order_by('id').limit(limit)
        succeeded = 0
        failed = 0
        for t in tasks:
            try:
                await self.process_index_task(t.id)
                succeeded += 1
            except Exception:
                failed += 1
        return {'processed': len(tasks), 'succeeded': succeeded, 'failed': failed}


knowledge_service = KnowledgeService()
