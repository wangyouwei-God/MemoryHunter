"""
图片搜索引擎
提供基于文本的语义搜索功能
"""

import logging
from typing import List, Dict, Any
from .config import TOP_K, SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


class ImageSearcher:
    """图片搜索引擎"""
    
    def __init__(self, model_manager, vector_db):
        """
        初始化搜索引擎
        
        Args:
            model_manager: CLIPModelManager 实例
            vector_db: VectorDatabase 实例
        """
        self.model = model_manager
        self.db = vector_db
        self.logger = logging.getLogger(__name__)
    
    def search(self, query_text: str, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD) -> List[Dict[str, Any]]:
        """
        搜索图片
        
        Args:
            query_text: 中文查询文本
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            搜索结果列表
        """
        try:
            if not query_text or not query_text.strip():
                self.logger.warning("搜索文本为空")
                return []
            
            self.logger.info(f"搜索查询: '{query_text}' (Top-{top_k}, 阈值: {threshold})")
            
            # 文本编码
            query_embedding = self.model.encode_text(query_text)
            
            # 向量检索
            results = self.db.search(
                query_embedding=query_embedding.tolist(),
                top_k=top_k,
                threshold=threshold
            )
            
            self.logger.info(f"✅ 找到 {len(results)} 个相关结果")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 搜索失败: {e}")
            raise
    
    def search_batch(self, queries: List[str], top_k: int = TOP_K) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量搜索
        
        Args:
            queries: 查询文本列表
            top_k: 每个查询返回结果数量
            
        Returns:
            查询结果字典 {query: results}
        """
        results = {}
        
        for query in queries:
            try:
                results[query] = self.search(query, top_k=top_k)
            except Exception as e:
                self.logger.error(f"批量搜索失败 '{query}': {e}")
                results[query] = []
        
        return results
