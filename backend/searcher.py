"""
图片搜索引擎 - Phase 1 优化
提供基于文本的语义搜索功能 + 查询扩展
"""

import logging
from typing import List, Dict, Any, Optional
from .config import TOP_K, SIMILARITY_THRESHOLD, ENABLE_HYBRID_SEARCH

logger = logging.getLogger(__name__)


class ImageSearcher:
    """图片搜索引擎 (Phase 1优化: 查询扩展)"""
    
    def __init__(self, model_manager, vector_db, query_expander=None):
        """
        初始化搜索引擎
        
        Args:
            model_manager: CLIPModelManager 实例
            vector_db: VectorDatabase 实例
            query_expander: QueryExpander 实例 (可选)
        """
        self.model = model_manager
        self.db = vector_db
        self.query_expander = query_expander
        self.logger = logging.getLogger(__name__)
        
        if self.query_expander:
            self.logger.info("✅ 查询扩展已启用")
    
    def search(self, query_text: str, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD, 
               use_expansion: bool = True) -> List[Dict[str, Any]]:
        """
        搜索图片 (支持查询扩展)
        
        Args:
            query_text: 中文查询文本
            top_k: 返回结果数量
            threshold: 相似度阈值
            use_expansion: 是否使用查询扩展
            
        Returns:
            搜索结果列表
        """
        try:
            if not query_text or not query_text.strip():
                self.logger.warning("搜索文本为空")
                return []
            
            # Phase 1优化: 查询扩展
            if use_expansion and self.query_expander:
                return self._search_with_expansion(query_text, top_k, threshold)
            else:
                return self._search_single(query_text, top_k, threshold)
                
        except Exception as e:
            self.logger.error(f"❌ 搜索失败: {e}")
            raise
    
    def _search_single(self, query_text: str, top_k: int, threshold: float) -> List[Dict[str, Any]]:
        """单查询搜索 (原始方法)"""
        from pathlib import Path
        
        self.logger.info(f"🔍 搜索查询: '{query_text}' (Top-{top_k}, 阈值: {threshold})") 
        
        # 文本编码
        query_embedding = self.model.encode_text(query_text)
        
        # 向量检索（请求更多结果以补偿可能被过滤的删除文件）
        raw_results = self.db.search(
            query_embedding=query_embedding.tolist(),
            top_k=top_k * 2,  # 请求2倍数量
            threshold=threshold
        )
        
        # Phase 4: 验证文件存在性
        valid_results = []
        invalid_ids = []
        
        for result in raw_results:
            file_path = Path(result['path'])
            
            # 检查文件是否存在
            if file_path.exists():
                valid_results.append(result)
            else:
                # 文件已被删除，标记
                self.logger.debug(f"文件不存在，已标记: {result['path']}")
                # 从元数据中获取ID（如果有）
                if 'id' in result:
                    invalid_ids.append(result['id'])
        
        # 异步标记已删除的文件（不阻塞搜索）
        if invalid_ids:
            try:
                for file_id in invalid_ids:
                    self.db.mark_file_deleted(file_id)
                self.logger.info(f"⚠️ 已标记 {len(invalid_ids)} 个已删除文件")
            except Exception as e:
                self.logger.warning(f"标记删除文件失败: {e}")
        
        # 截取到请求的数量
        valid_results = valid_results[:top_k]
        
        self.logger.info(f"✅ 找到 {len(valid_results)} 个有效结果（过滤了 {len(invalid_ids)} 个已删除文件）")
        return valid_results
    
    def _search_with_expansion(self, query_text: str, top_k: int, threshold: float) -> List[Dict[str, Any]]:
        """多查询融合搜索 (Phase 1优化)"""
        # 1. 查询扩展
        expanded_queries = self.query_expander.expand_query(query_text)
        self.logger.info(f"🚀 查询扩展: '{query_text}' → {len(expanded_queries)} 个查询")
        
        # 2. 多查询检索
        all_results = {}
        for eq in expanded_queries:
            results = self._search_single(eq, top_k=top_k*2, threshold=threshold)
            for r in results:
                path = r['path']
                if path not in all_results:
                    all_results[path] = {'scores': [], 'data': r}
                all_results[path]['scores'].append(r['score'])
        
        # 3. 分数融合 (取最大分数)
        final_results = []
        for path, data in all_results.items():
            result = data['data'].copy()
            result['score'] = max(data['scores'])  # 最大分数
            result['query_count'] = len(data['scores'])  # 参与查询数
            final_results.append(result)
        
        # 4. 排序返回
        final_results = sorted(final_results, key=lambda x: x['score'], reverse=True)[:top_k]
        
        self.logger.info(f"✅ 融合搜索找到 {len(final_results)} 个结果")
        return final_results
    
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
