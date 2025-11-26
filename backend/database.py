"""
ChromaDB 向量数据库封装
提供图片向量的存储和检索功能
"""

import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Any
from .config import CHROMA_DIR

logger = logging.getLogger(__name__)


class VectorDatabase:
    """向量数据库管理器"""
    
    def __init__(self):
        """初始化 ChromaDB"""
        try:
            logger.info(f"初始化 ChromaDB，存储路径: {CHROMA_DIR}")
            
            # 确保目录存在
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            
            # 创建持久化客户端
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="images",
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
            
            logger.info(f"✅ ChromaDB 初始化成功，当前图片数: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB 初始化失败: {e}")
            raise
    
    def add_images(self, paths: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        """
        批量添加图片向量
        
        Args:
            paths: 图片路径列表
            embeddings: 特征向量列表
            metadatas: 元数据列表
        """
        try:
            # 使用路径的哈希作为 ID（确保唯一性）
            ids = [str(abs(hash(p))) for p in paths]
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.debug(f"添加 {len(paths)} 张图片到数据库")
            
        except Exception as e:
            logger.error(f"添加图片失败: {e}")
            raise
    
    def search(self, query_embedding: List[float], top_k: int = 20, threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        搜索相似图片
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值 (0.0-1.0)
            
        Returns:
            搜索结果列表，每项包含 path 和 score
        """
        try:
            if self.collection.count() == 0:
                logger.warning("数据库为空，请先索引图片")
                return []
            
            # ChromaDB 查询
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count())
            )
            
            # 处理结果
            filtered_results = []
            
            if results['distances'] and len(results['distances'][0]) > 0:
                for i, distance in enumerate(results['distances'][0]):
                    # ChromaDB 使用距离，越小越相似
                    # 对于余弦距离: similarity = 1 - distance
                    similarity = 1.0 - distance
                    
                    if similarity >= threshold:
                        filtered_results.append({
                            'path': results['metadatas'][0][i]['path'],
                            'filename': results['metadatas'][0][i]['filename'],
                            'score': round(similarity, 4)
                        })
            
            logger.info(f"搜索完成，返回 {len(filtered_results)} 个结果")
            return filtered_results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            return {
                'total_images': self.collection.count(),
                'collection_name': self.collection.name
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'total_images': 0, 'collection_name': 'unknown'}
    
    def clear(self):
        """清空数据库"""
        try:
            self.client.delete_collection("images")
            self.collection = self.client.create_collection(
                name="images",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("✅ 数据库已清空")
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            raise
    
    def check_image_exists(self, path: str) -> bool:
        """检查图片是否已索引"""
        try:
            image_id = str(abs(hash(path)))
            result = self.collection.get(ids=[image_id])
            return len(result['ids']) > 0
        except:
            return False
