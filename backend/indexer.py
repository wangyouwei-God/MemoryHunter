"""
图片索引器 - V1.0 (CLIP Only)
扫描相册目录并提取图片特征向量
"""

from PIL import Image
from pillow_heif import register_heif_opener
import logging
from pathlib import Path
from typing import List, Callable, Optional
import gc

from .config import (
    PHOTOS_DIR, SUPPORTED_FORMATS, 
    BATCH_SIZE
)

# 注册 HEIC 格式支持
register_heif_opener()

logger = logging.getLogger(__name__)


class ImageIndexer:
    """图片索引器 - V1.0"""
    
    def __init__(self, model_manager, vector_db):
        """
        初始化索引器 - V1.0
        
        Args:
            model_manager: CLIPModelManager 实例
            vector_db: VectorDatabase 实例
        """
        self.model = model_manager
        self.db = vector_db
        self.logger = logging.getLogger(__name__)
        self.logger.info("📌 V1.0 模式：仅使用 Chinese-CLIP 进行视觉索引")
    
    def scan_photos(self) -> List[Path]:
        """扫描相册目录"""
        photos = []
        if not PHOTOS_DIR.exists():
            self.logger.warning(f"相册目录不存在: {PHOTOS_DIR}")
            return photos
        
        self.logger.info(f"正在扫描目录: {PHOTOS_DIR}")
        for photo_path in PHOTOS_DIR.rglob("*"):
            if photo_path.is_file() and photo_path.suffix in SUPPORTED_FORMATS:
                photos.append(photo_path)
        
        self.logger.info(f"✅ 找到 {len(photos)} 张图片")
        return photos
    
    def index_all(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> dict:
        """索引所有图片"""
        photos = self.scan_photos()
        total = len(photos)
        
        if total == 0:
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        self.logger.info(f"开始索引 {total} 张图片...")
        
        for i, photo_path in enumerate(photos):
            try:
                # 检查是否已索引
                if self.db.check_image_exists(str(photo_path)):
                    skipped_count += 1
                    if progress_callback: progress_callback(i + 1, total)
                    continue
                
                # 索引单张图片
                if self._index_single_internal(photo_path):
                    success_count += 1
                    if (i+1) % 10 == 0:
                        self.logger.info(f"进度: {i+1}/{total}")
                else:
                    failed_count += 1
                
            except Exception as e:
                failed_count += 1
                self.logger.warning(f"处理失败 {photo_path.name}: {e}")
                
            finally:
                if progress_callback: progress_callback(i + 1, total)
                # 定期清理内存
                if (i + 1) % 50 == 0:
                    gc.collect()
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count
        }
    
    def _index_single_internal(self, photo_path: Path) -> bool:
        """索引单张图片 (CLIP 向量化)"""
        try:
            image = Image.open(photo_path).convert("RGB")
            
            # 视觉编码
            visual_embedding = self.model.encode_image(image)
            
            # 构建元数据
            metadata = {
                'path': str(photo_path),
                'filename': photo_path.name,
                'vlm_analyzed': False # V1.0 标记
            }
            
            # 存入数据库
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
        return self._index_single_internal(photo_path)