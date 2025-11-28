"""
图片索引器 - V2.0 Pro (CLIP + VLM + YOLO)
扫描相册目录并提取多维度特征
"""

from PIL import Image
from pillow_heif import register_heif_opener
import logging
import json
from pathlib import Path
from typing import List, Callable, Optional
import gc

from .config import (
    PHOTOS_DIR, SUPPORTED_FORMATS,
    ENABLE_VLM, ENABLE_OBJECT_DETECTION
)

# 注册 HEIC 格式支持
register_heif_opener()

logger = logging.getLogger(__name__)


class ImageIndexer:
    """图片索引器 - V2.0 Pro"""
    
    def __init__(self, visual_model, vector_db, semantic_model=None, ai_processor=None):
        """
        初始化索引器 - V2.0 Pro
        
        Args:
            visual_model: CLIPModelManager 实例 (视觉编码)
            vector_db: VectorDatabase 实例 (双集合)
            semantic_model: (Optional) BGEModelManager 实例 (语义编码)
            ai_processor: (Optional) GlobalAIProcessor 实例 (VLM + YOLO)
        """
        self.visual_model = visual_model
        self.db = vector_db
        self.semantic_model = semantic_model
        self.ai_processor = ai_processor
        self.logger = logging.getLogger(__name__)
        
        # 根据配置显示模式
        if ENABLE_VLM and self.ai_processor:
            self.logger.info("🚀 V2.0 Pro 模式: CLIP + VLM + YOLO")
        else:
            self.logger.info("📌 V1.0 兼容模式: 仅 CLIP")
    
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
        """索引所有图片 (支持取消)"""
        photos = self.scan_photos()
        total = len(photos)
        
        if total == 0:
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        self.logger.info(f"开始索引 {total} 张图片...")
        
        for i, photo_path in enumerate(photos):
            # 检查取消标志 (从main.py导入)
            try:
                from .main import cancel_indexing_flag
                if cancel_indexing_flag:
                    self.logger.info(f"索引已被用户取消 (处理了 {i}/{total} 张)")
                    break
            except ImportError:
                pass  # 单元测试时可能无法导入
            
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
                
                # V2.0 Pro: 每张图处理完后清理GPU缓存
                if self.ai_processor and hasattr(self.ai_processor, 'device') and self.ai_processor.device == "cuda":
                    import torch
                    torch.cuda.empty_cache()
                
                # 定期清理内存
                if (i + 1) % 20 == 0:
                    gc.collect()
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count
        }
    
    def _index_single_internal(self, photo_path: Path) -> bool:
        """
        索引单张图片 (多模型流水线)
        
        流程:
        1. CLIP视觉编码 (必须)
        2. 如果启用VLM: VLM深度分析 + YOLO物体检测
        3. 如果有VLM结果: BGE语义编码
        4. 存入双集合数据库
        """
        try:
            image = Image.open(photo_path).convert("RGB")
            
            # ========== Step 1: CLIP 视觉编码 (必须) ==========
            visual_embedding = self.visual_model.encode_image(image)
            
            # 基础元数据
            base_metadata = {
                'path': str(photo_path),
                'filename': photo_path.name,
                'vlm_analyzed': False
            }
            
            # ========== Step 2: Pro 模式处理 ==========
            semantic_embedding = None
            pro_metadata = None
            
            if ENABLE_VLM and self.ai_processor and self.semantic_model:
                try:
                    # 2a. VLM + YOLO 分析
                    self.logger.debug(f"🧠 VLM analyzing: {photo_path.name}")
                    ai_result = self.ai_processor.process_image(str(photo_path))
                    
                    # 2b. 构建Pro元数据
                    caption = ai_result.get('caption', '')
                    ocr_text = ai_result.get('ocr_text', '')
                    objects = ai_result.get('objects', [])
                    
                    # 将objects序列化为JSON字符串 (ChromaDB不支持嵌套对象)
                    objects_json = json.dumps(objects, ensure_ascii=False)
                    
                    pro_metadata = {
                        'caption': caption,
                        'ocr_text': ocr_text,
                        'objects': objects_json,
                        'vlm_analyzed': True
                    }
                    
                    # 2c. 语义向量化 (对caption + ocr_text)
                    semantic_text = f"{caption} {ocr_text}".strip()
                    if semantic_text:
                        semantic_embedding = self.semantic_model.encode_text(semantic_text)
                    
                    self.logger.debug(f"✅ Pro analysis complete: {photo_path.name}")
                    
                except Exception as e:
                    self.logger.warning(f"Pro处理失败 (将回退到V1.0): {e}")
                    # 出错时回退到V1.0模式
                    pro_metadata = None
                    semantic_embedding = None
            
            # ========== Step 3: 存入数据库 ==========
            if semantic_embedding is not None and pro_metadata is not None:
                # Pro模式: 双向量存储
                self.db.add_image(
                    path=str(photo_path),
                    visual_embedding=visual_embedding.tolist(),
                    metadata=base_metadata,
                    semantic_embedding=semantic_embedding.tolist(),
                    pro_metadata=pro_metadata
                )
            else:
                # V1.0兼容模式: 仅视觉向量
                self.db.add_image(
                    path=str(photo_path),
                    visual_embedding=visual_embedding.tolist(),
                    metadata=base_metadata
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"索引失败 {photo_path}: {e}")
            return False
    
    def index_single(self, photo_path: Path) -> bool:
        """对外暴露的单图索引接口"""
        return self._index_single_internal(photo_path)