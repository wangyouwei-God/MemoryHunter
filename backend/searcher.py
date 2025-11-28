"""
图片搜索引擎 - V2.0 Pro (Hybrid Search with RRF)
提供双路召回 + 融合排序的混合搜索
"""

import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from .config import (
    TOP_K, SIMILARITY_THRESHOLD, RRF_K,
    ENABLE_HYBRID_SEARCH
)

logger = logging.getLogger(__name__)


class ImageSearcher:
    """图片搜索引擎 - V2.0 Pro"""
    
    def __init__(self, visual_model, vector_db, semantic_model=None):
        """
        初始化搜索引擎 - V2.0 Pro
        
        Args:
            visual_model: CLIPModelManager 实例 (视觉编码)
            vector_db: VectorDatabase 实例 (双集合)
            semantic_model: (Optional) BGEModelManager 实例 (语义编码)
        """
        self.visual_model = visual_model
        self.db = vector_db
        self.semantic_model = semantic_model
        self.logger = logging.getLogger(__name__)
        
        if ENABLE_HYBRID_SEARCH and self.semantic_model:
            self.logger.info("🚀 混合搜索模式: Visual + Semantic (RRF融合)")
        else:
            self.logger.info("📌 单路搜索模式: Visual Only")
    
    def search(
        self, 
        query_text: str, 
        top_k: int = TOP_K, 
        threshold: float = SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        智能搜索 (自动选择单路/混合)
        
        Args:
            query_text: 中文查询文本
            top_k: 最终返回结果数量
            threshold: 相似度阈值
            
        Returns:
            搜索结果列表 (已排序,包含Pro元数据)
        """
        try:
            if not query_text or not query_text.strip():
                self.logger.warning("搜索文本为空")
                return []
            
            self.logger.info(f"搜索查询: '{query_text}' (Top-{top_k}, 阈值: {threshold})")
            
            # 根据配置选择搜索策略
            if ENABLE_HYBRID_SEARCH and self.semantic_model:
                results = self._hybrid_search(query_text, top_k, threshold)
            else:
                results = self._visual_only_search(query_text, top_k, threshold)
            
            self.logger.info(f"✅ 找到 {len(results)} 个相关结果")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 搜索失败: {e}")
            raise
    
    def _visual_only_search(
        self, 
        query_text: str, 
        top_k: int, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        视觉单路搜索 (V1.0兼容)
        
        Args:
            query_text: 查询文本
            top_k: 返回数量
            threshold: 阈值
            
        Returns:
            搜索结果
        """
        # CLIP文本编码
        query_embedding = self.visual_model.encode_text(query_text)
        
        # 视觉向量检索
        results = self.db.search_visual(
            query_embedding=query_embedding.tolist(),
            top_k=top_k,
            threshold=threshold
        )
        
        return results
    
    def _hybrid_search(
        self, 
        query_text: str, 
        top_k: int, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        混合搜索 (双路召回 + RRF融合)
        
        流程:
        1. 路径A: CLIP视觉搜索 (搜图片的"样子")
        2. 路径B: BGE语义搜索 (搜VLM生成的"描述")
        3. RRF融合两路结果
        
        Args:
            query_text: 查询文本
            top_k: 最终返回数量
            threshold: 阈值
            
        Returns:
            融合后的结果 (包含Pro元数据)
        """
        # ========== 路径A: Visual Search ==========
        visual_query = self.visual_model.encode_text(query_text)
        visual_results = self.db.search_visual(
            query_embedding=visual_query.tolist(),
            top_k=TOP_K,  # 召回更多以供融合
            threshold=0.0  # 不在这里过滤,留给融合后统一过滤
        )
        
        # ========== 路径B: Semantic Search ==========
        semantic_query = self.semantic_model.encode_text(query_text)
        semantic_results = self.db.search_semantic(
            query_embedding=semantic_query.tolist(),
            top_k=TOP_K,
            threshold=0.0
        )
        
        # ========== RRF 融合 ==========
        fused_results = self._rrf_fusion(
            visual_results=visual_results,
            semantic_results=semantic_results,
            k=RRF_K
        )
        
        # ========== 过滤 + 限制数量 ==========
        filtered_results = [
            r for r in fused_results 
            if r['score'] >= threshold
        ][:top_k]
        
        self.logger.debug(
            f"混合搜索: Visual={len(visual_results)}, "
            f"Semantic={len(semantic_results)}, "
            f"Fused={len(fused_results)}, "
            f"Final={len(filtered_results)}"
        )
        
        return filtered_results
    
    def _rrf_fusion(
        self,
        visual_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        RRF (Reciprocal Rank Fusion) 算法实现
        
        公式: RRF_score(d) = Σ (1 / (k + rank_i(d)))
        
        Args:
            visual_results: 视觉路径结果 [{path, score}, ...]
            semantic_results: 语义路径结果 [{path, score, caption, ...}, ...]
            k: RRF 常数 (通常取60)
            
        Returns:
            融合排序后的结果 (按RRF分数降序)
        """
        # 构建 path -> rank 映射
        visual_ranks = {r['path']: idx + 1 for idx, r in enumerate(visual_results)}
        semantic_ranks = {r['path']: idx + 1 for idx, r in enumerate(semantic_results)}
        
        # 构建 path -> metadata 映射 (优先使用semantic的元数据,因为它包含Pro字段)
        metadata_map = {}
        for r in visual_results:
            metadata_map[r['path']] = r
        for r in semantic_results:
            metadata_map[r['path']] = r  # 覆盖,因为semantic包含更多信息
        
        # 计算 RRF 分数
        rrf_scores = defaultdict(float)
        all_paths = set(visual_ranks.keys()) | set(semantic_ranks.keys())
        
        for path in all_paths:
            score = 0.0
            
            # 来自视觉路径的贡献
            if path in visual_ranks:
                score += 1.0 / (k + visual_ranks[path])
            
            # 来自语义路径的贡献
            if path in semantic_ranks:
                score += 1.0 / (k + semantic_ranks[path])
            
            rrf_scores[path] = score
        
        # 排序并构建最终结果
        sorted_paths = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        fused_results = []
        for path, rrf_score in sorted_paths:
            result = metadata_map[path].copy()
            result['score'] = round(rrf_score, 4)  # 替换为RRF分数
            # result['rrf_visual_rank'] = visual_ranks.get(path, 0)  # Debug用
            # result['rrf_semantic_rank'] = semantic_ranks.get(path, 0)
            fused_results.append(result)
        
        return fused_results
    
    def search_batch(
        self, 
        queries: List[str], 
        top_k: int = TOP_K
    ) -> Dict[str, List[Dict[str, Any]]]:
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
