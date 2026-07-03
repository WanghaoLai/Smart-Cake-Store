import faiss
import numpy as np
from dashscope import TextEmbedding


class RAGService:
    def __init__(self, embedding_model: str = "text-embedding-v2"):
        self.index = None
        self.documents = []
        self.embedding_model = embedding_model

    def build_index(self, goods_list: list):
        """从商品列表构建向量索引"""
        self.documents = []
        for goods in goods_list:
            doc = f"商品名称：{goods.name}\n价格：{goods.price}元\n描述：{goods.description}\n库存：{goods.num}{goods.unit}\n分类：{goods.category.name if goods.category else '未分类'}"
            self.documents.append(doc)

        if not self.documents:
            return

        # 获取向量
        embeddings = self._get_embeddings(self.documents)

        # 创建 FAISS 索引
        dimension = len(embeddings[0])
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))

    def search(self, query: str, top_k: int = 3) -> list:
        """检索相关文档"""
        if not self.index:
            return []

        query_embedding = self._get_embeddings([query])
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), top_k
        )

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                results.append({
                    "content": self.documents[idx],
                    "score": float(distances[0][i])
                })
        return results

    def _get_embeddings(self, texts: list) -> list:
        """获取文本向量"""
        response = TextEmbedding.call(
            model=self.embedding_model,
            input=texts
        )
        if response.status_code == 200:
            return [item['embedding'] for item in response.output['embeddings']]
        raise Exception(f"Embedding 调用失败: {response.message}")
