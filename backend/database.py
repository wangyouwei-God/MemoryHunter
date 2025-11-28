"""
ChromaDB 向量数据库封装 (V2.0 Pro)
支持双集合架构: visual (CLIP) + semantic (BGE)
"""

import chromadb
from chromadb.config import Settings
import logging
import hashlib
from typing import List, Dict, Any, Optional
from .config import CHROMA_DIR, ENABLE_HYBRID_SEARCH

logger = logging.getLogger(__name__)


class VectorDatabase:
    """向量数据库管理器 (V2.0 Pro - Dual Collections)"""
    
    def __init__(self):
        """初始化 ChromaDB with 双集合"""
        try:
            logger.info(f"初始化 ChromaDB (V2.0 Pro)，存储路径: {CHROMA_DIR}")
            
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
            
            # Collection 1: Visual Vectors (CLIP embeddings)
            self.visual_collection = self.client.get_or_create_collection(
                name="images_visual",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Collection 2: Semantic Vectors (BGE embeddings of VLM captions)
            self.semantic_collection = self.client.get_or_create_collection(
                name="images_semantic",
                metadata={"hnsw:space": "cosine"}
            )
            
            visual_count = self.visual_collection.count()
            semantic_count = self.semantic_collection.count()
            
            logger.info(f"✅ ChromaDB 初始化成功")
            logger.info(f"   - Visual Collection: {visual_count} images")
            logger.info(f"   - Semantic Collection: {semantic_count} images")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB 初始化失败: {e}")
            raise
    
    def _generate_image_id(self, path: str) -> str:
        """
        生成稳定且唯一的图片ID
        
        使用MD5而非hash()以确保:
        1. 跨平台/跨会话稳定性
        2. 无碰撞风险（MD5碰撞概率极低）
        3. 同一路径始终生成相同ID
        
        Args:
            path: 图片文件路径
            
        Returns:
            32位十六进制MD5字符串
        """
        return hashlib.md5(path.encode('utf-8')).hexdigest()
    
    def add_image(
        self,
        path: str,
        visual_embedding: List[float],
        metadata: Dict[str, Any],
        semantic_embedding: Optional[List[float]] = None,
        pro_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        添加单张图片 (支持双向量)
        
        Args:
            path: 图片路径
            visual_embedding: CLIP视觉向量
            metadata: 基础元数据 {path, filename, timestamp, ...}
            semantic_embedding: (Optional) BGE语义向量
            pro_metadata: (Optional) Pro扩展元数据 {caption, ocr_text, objects_json, ...}
        """
        try:
            image_id = self._generate_image_id(path)
            
            # 添加到 Visual Collection
            self.visual_collection.add(
                ids=[image_id],
                embeddings=[visual_embedding],
                metadatas=[metadata]
            )
            
            # 如果提供了语义向量和Pro元数据, 添加到 Semantic Collection
            if semantic_embedding is not None and pro_metadata is not None:
                # 合并基础元数据和Pro元数据
                full_metadata = {**metadata, **pro_metadata}
                
                self.semantic_collection.add(
                    ids=[image_id],
                    embeddings=[semantic_embedding],
                    metadatas=[full_metadata]
                )
                
                logger.debug(f"添加图片 (双向量): {path}")
            else:
                logger.debug(f"添加图片 (仅视觉): {path}")
                
        except Exception as e:
            logger.error(f"添加图片失败: {e}")
            raise
    
    def add_images_batch(
        self,
        paths: List[str],
        visual_embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        semantic_embeddings: Optional[List[List[float]]] = None,
        pro_metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        批量添加图片 (兼容V1.0和V2.0)
        
        Args:
            paths: 图片路径列表
            visual_embeddings: CLIP向量列表
            metadatas: 元数据列表
            semantic_embeddings: (Optional) BGE向量列表
            pro_metadatas: (Optional) Pro元数据列表
        """
        try:
            ids = [self._generate_image_id(p) for p in paths]
            
            # 添加到 Visual Collection
            self.visual_collection.add(
                ids=ids,
                embeddings=visual_embeddings,
                metadatas=metadatas
            )
            
            # 如果是Pro模式, 添加到Semantic Collection
            if semantic_embeddings and pro_metadatas:
                full_metadatas = [
                    {**meta, **pro_meta} 
                    for meta, pro_meta in zip(metadatas, pro_metadatas)
                ]
                
                self.semantic_collection.add(
                    ids=ids,
                    embeddings=semantic_embeddings,
                    metadatas=full_metadatas
                )
            
            logger.debug(f"批量添加 {len(paths)} 张图片")
            
        except Exception as e:
            logger.error(f"批量添加失败: {e}")
            raise
    
    def search_visual(self, query_embedding: List[float], top_k: int = 50, threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        视觉路径搜索 (CLIP)
        
        Args:
            query_embedding: CLIP查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            [{path, filename, score}, ...]
        """
        try:
            if self.visual_collection.count() == 0:
                logger.warning("Visual collection 为空")
                return []
            
            results = self.visual_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.visual_collection.count())
            )
            
            return self._process_results(results, threshold)
            
        except Exception as e:
            logger.error(f"视觉搜索失败: {e}")
            return []
    
    def search_semantic(self, query_embedding: List[float], top_k: int = 50, threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        语义路径搜索 (BGE + VLM Caption)
        
        Args:
            query_embedding: BGE查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值
            
        Returns:
            [{path, filename, score, caption, ocr_text, objects}, ...]
        """
        try:
            if self.semantic_collection.count() == 0:
                logger.warning("Semantic collection 为空")
                return []
            
            results = self.semantic_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.semantic_collection.count())
            )
            
            return self._process_results(results, threshold, include_pro_fields=True)
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []
    
    def _process_results(self, results: Dict, threshold: float, include_pro_fields: bool = False) -> List[Dict[str, Any]]:
        """
        处理ChromaDB查询结果
        
        Args:
            results: ChromaDB原始结果
            threshold: 相似度阈值
            include_pro_fields: 是否包含Pro字段(caption, ocr_text, objects)
            
        Returns:
            处理后的结果列表
        """
        filtered_results = []
        
        if results['distances'] and len(results['distances'][0]) > 0:
            for i, distance in enumerate(results['distances'][0]):
                similarity = 1.0 - distance
                
                if similarity >= threshold:
                    result_item = {
                        'path': results['metadatas'][0][i]['path'],
                        'filename': results['metadatas'][0][i]['filename'],
                        'score': round(similarity, 4)
                    }
                    
                    # 如果是Semantic搜索, 添加Pro字段
                    if include_pro_fields:
                        metadata = results['metadatas'][0][i]
                        if 'caption' in metadata:
                            result_item['caption'] = metadata.get('caption', '')
                        if 'ocr_text' in metadata:
                            result_item['ocr_text'] = metadata.get('ocr_text', '')
                        if 'objects' in metadata:
                            result_item['objects'] = metadata.get('objects', '[]')
                    
                    filtered_results.append(result_item)
        
        return filtered_results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            return {
                'total_images_visual': self.visual_collection.count(),
                'total_images_semantic': self.semantic_collection.count(),
                'hybrid_mode': ENABLE_HYBRID_SEARCH
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'total_images_visual': 0,
                'total_images_semantic': 0,
                'hybrid_mode': False
            }
    
    def clear(self):
        """清空所有集合"""
        try:
            self.client.delete_collection("images_visual")
            self.client.delete_collection("images_semantic")
            
            self.visual_collection = self.client.create_collection(
                name="images_visual",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.semantic_collection = self.client.create_collection(
                name="images_semantic",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("✅ 所有集合已清空")
        except Exception as e:
            logger.error(f"清空数据库失败: {e}")
            raise
    
    def check_image_exists(self, path: str) -> bool:
        """
        检查图片是否已索引 (检查visual collection)
        
        Args:
            path: 图片文件路径
            
        Returns:
            True if exists, False otherwise
        """
        try:
            image_id = self._generate_image_id(path)
            result = self.visual_collection.get(ids=[image_id])
            exists = len(result['ids']) > 0
            
            if exists:
                logger.debug(f"图片已存在: {path} (ID: {image_id[:8]}...)")
            
            return exists
            
        except Exception as e:
            logger.warning(f"检查图片存在性失败 {path}: {e}")
            return False
