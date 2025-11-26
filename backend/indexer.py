"""
图片索引器 - V2.0
扫描相册目录并提取图片特征向量

V2.0 新增:
- VLM 深度分析（OCR + 描述 + 标签）
- 双向量存储（visual + text）
- 混合模式支持
"""

from PIL import Image
from pillow_heif import register_heif_opener
import logging
from pathlib import Path
from typing import List, Callable, Optional
import gc

from .config import (
    PHOTOS_DIR, SUPPORTED_FORMATS, 
    ENABLE_VLM, VLM_BATCH_SIZE, GC_THRESHOLD
)

# 注册 HEIC 格式支持
register_heif_opener()

logger = logging.getLogger(__name__)


class ImageIndexer:
    """图片索引器 - V2.0"""
    
    def __init__(self, model_manager, vector_db, vlm_manager=None):
        """
        初始化索引器
        
        Args:
            model_manager: CLIPModelManager 实例（视觉编码）
            vector_db: VectorDatabase 实例
            vlm_manager: MiniCPMVManager 实例（可选，V2.0）
        """
        self.model = model_manager
        self.db = vector_db
        self.vlm = vlm_manager
        self.logger = logging.getLogger(__name__)
        
        # 检查 V2.0 功能状态
        if ENABLE_VLM and self.vlm is None:
            self.logger.warning("⚠️ VLM 已启用但未提供 VLM Manager，将仅使用 CLIP")
        elif ENABLE_VLM and self.vlm is not None:
            self.logger.info("✅ V2.0 模式：CLIP + VLM 深度分析已启用")
        else:
            self.logger.info("📌 V1.0 模式：仅使用 CLIP")
    
    def scan_photos(self) -> List[Path]:
        """
        扫描相册目录，查找所有支持的图片文件
        
        Returns:
            图片路径列表
        """
        photos = []
        
        if not PHOTOS_DIR.exists():
            self.logger.warning(f"相册目录不存在: {PHOTOS_DIR}")
            return photos
        
        self.logger.info(f"正在扫描目录: {PHOTOS_DIR}")
        
        # 递归查找所有图片
        for photo_path in PHOTOS_DIR.rglob("*"):
            if photo_path.is_file() and photo_path.suffix in SUPPORTED_FORMATS:
                photos.append(photo_path)
        
        self.logger.info(f"✅ 找到 {len(photos)} 张图片")
        return photos
    
    def index_all(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> dict:
        """
        索引所有图片
        
        Args:
            progress_callback: 进度回调函数 (current, total)
            
        Returns:
            索引结果统计
        """
        photos = self.scan_photos()
        total = len(photos)
        
        if total == 0:
            self.logger.warning("没有找到图片，索引终止")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0
            }
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        self.logger.info(f"开始索引 {total} 张图片...")
        
        # V2.0: 批处理优化
        if ENABLE_VLM and self.vlm is not None:
            self.logger.info(f"使用批处理模式，批大小: {VLM_BATCH_SIZE}")
        
        for i, photo_path in enumerate(photos):
            try:
                # 检查是否已索引
                if self.db.check_image_exists(str(photo_path)):
                    self.logger.debug(f"跳过已索引图片: {photo_path.name}")
                    skipped_count += 1
                    if progress_callback:
                        progress_callback(i + 1, total)
                    continue
                
                # 索引单张图片（V2.0 会调用 VLM）
                if self._index_single_internal(photo_path):
                    success_count += 1
                    self.logger.debug(f"[{i+1}/{total}] ✅ {photo_path.name}")
                else:
                    failed_count += 1
                
            except Exception as e:
                failed_count += 1
                self.logger.warning(f"[{i+1}/{total}] ❌ 处理失败 {photo_path.name}: {e}")
                
            finally:
                # 更新进度
                if progress_callback:
                    progress_callback(i + 1, total)
                
                # 定期垃圾回收（节省内存）
                if (i + 1) % GC_THRESHOLD == 0:
                    gc.collect()
                    self.logger.debug(f"🧹 已清理内存（处理 {i+1} 张）")
        
        result = {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count
        }
        
        self.logger.info(f"索引完成! 成功: {success_count}, 失败: {failed_count}, 跳过: {skipped_count}")
        return result
    
    def _index_single_internal(self, photo_path: Path) -> bool:
        """
        索引单张图片（内部方法）
        
        V2.0: 同时提取视觉向量和 VLM 分析结果
        
        Args:
            photo_path: 图片路径
            
        Returns:
            是否成功
        """
        try:
            # 加载图片
            image = Image.open(photo_path).convert("RGB")
            
            # 1. 视觉编码（CLIP）- 快速
            visual_embedding = self.model.encode_image(image)
            
            # 2. VLM 深度分析（V2.0）
            vlm_result = None
            if ENABLE_VLM and self.vlm is not None:
                try:
                    vlm_result = self.vlm.analyze_image(image)
                    self.logger.debug(f"  VLM 分析完成: {photo_path.name}")
                except Exception as e:
                    self.logger.warning(f"  VLM 分析失败（将使用 V1.0 模式）: {e}")
            
            # 3. 构建元数据
            metadata = {
                'path': str(photo_path),
                'filename': photo_path.name,
            }
            
            if vlm_result:
                metadata.update({
                    'description': vlm_result.get('description', ''),
                    'ocr_text': vlm_result.get('ocr_text', ''),
                    'tags': ','.join(vlm_result.get('tags', [])),
                    'vlm_analyzed': True
                })
            else:
                metadata['vlm_analyzed'] = False
            
            # 4. 存入数据库
            self.db.add_images(
                paths=[str(photo_path)],
                embeddings=[visual_embedding.tolist()],
                metadatas=[metadata]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"索引失败 {photo_path}: {e}")
            return False
    
    def index_single(self, photo_path: Path) -> bool:
        """
        索引单张图片（公开接口）
        
        Args:
            photo_path: 图片路径
            
        Returns:
            是否成功
        """
        success = self._index_single_internal(photo_path)
        
        if success:
            self.logger.info(f"✅ 索引成功: {photo_path.name}")
        else:
            self.logger.error(f"❌ 索引失败: {photo_path}")
        
        return success

