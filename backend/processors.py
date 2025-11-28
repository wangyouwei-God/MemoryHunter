"""
MemoryHunter V2.0 Pro - AI Processors
包含 MiniCPM-V 2.5 (Int4) 和 YOLOv8-X 的封装
"""

import torch
from PIL import Image
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

# 设置日志
logger = logging.getLogger(__name__)


class GlobalAIProcessor:
    """
    全局AI处理器 (单例模式)
    负责加载和管理所有大模型
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.info("🚀 Initializing GlobalAIProcessor for V2.0 Pro...")
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Device: {self.device}")
        
        # 模型占位符
        self.vlm_model = None
        self.vlm_tokenizer = None
        self.yolo_model = None
        
        self._initialized = True
        
    def load_models(self):
        """
        加载所有模型到GPU
        按顺序加载以优化显存使用
        """
        try:
            # ========== 加载 YOLOv8-X ==========
            logger.info("📦 Loading YOLOv8-X...")
            from ultralytics import YOLO
            self.yolo_model = YOLO('yolov8x.pt')  # 会自动下载
            if self.device == "cuda":
                self.yolo_model.to(self.device)
            logger.info("✅ YOLOv8-X loaded successfully")
            
            # ========== 加载 MiniCPM-V 2.5 Int4 ==========
            logger.info("📦 Loading MiniCPM-V 2.5 (Int4 Quantized)...")
            from transformers import AutoModel, AutoTokenizer
            
            model_name = "openbmb/MiniCPM-V-2_5-int4"
            
            self.vlm_tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True
            )
            
            self.vlm_model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            if self.device == "cuda":
                self.vlm_model = self.vlm_model.to(self.device)
            
            logger.info("✅ MiniCPM-V 2.5 (Int4) loaded successfully")
            
            # 显存占用检查
            if self.device == "cuda":
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"💾 GPU Memory: Allocated={allocated:.2f}GB, Reserved={reserved:.2f}GB")
                
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    def detect_objects(self, image_path: str, conf_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        使用 YOLOv8 检测图片中的物体
        
        Args:
            image_path: 图片路径
            conf_threshold: 置信度阈值
            
        Returns:
            [{label: str, box: [x1, y1, x2, y2], score: float}, ...]
        """
        if self.yolo_model is None:
            logger.warning("YOLO model not loaded, skipping object detection")
            return []
        
        try:
            results = self.yolo_model(image_path, conf=conf_threshold, verbose=False)
            
            objects = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # YOLO 返回的坐标格式: xyxy
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    label = result.names[cls_id]
                    
                    objects.append({
                        "label": label,
                        "box": [float(x1), float(y1), float(x2), float(y2)],
                        "score": conf
                    })
            
            logger.debug(f"Detected {len(objects)} objects in {Path(image_path).name}")
            return objects
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return []
    
    def analyze_image_with_vlm(self, image_path: str) -> Dict[str, str]:
        """
        使用 MiniCPM-V 分析图片,生成描述和OCR
        
        Args:
            image_path: 图片路径
            
        Returns:
            {caption: str, ocr_text: str}
        """
        if self.vlm_model is None or self.vlm_tokenizer is None:
            logger.warning("VLM model not loaded, returning empty analysis")
            return {"caption": "", "ocr_text": ""}
        
        try:
            image = Image.open(image_path).convert('RGB')
            
            # Prompt 设计: 要求详细描述 + OCR
            question = """请详细分析这张图片:
1. 描述画面中的主要内容、物体、人物、动作、场景和氛围
2. 如果图片中包含文字,请完整提取出来

请按照以下格式回答:
【描述】...
【文字】...(如果没有文字则写"无")"""
            
            # 调用 VLM (参考 MiniCPM-V 官方API)
            msgs = [{'role': 'user', 'content': question}]
            
            # 生成回答
            response = self.vlm_model.chat(
                image=image,
                msgs=msgs,
                tokenizer=self.vlm_tokenizer,
                sampling=True,
                temperature=0.7
            )
            
            # 解析输出
            caption = ""
            ocr_text = ""
            
            if "【描述】" in response:
                parts = response.split("【描述】")
                if len(parts) > 1:
                    desc_part = parts[1].split("【文字】")[0].strip()
                    caption = desc_part
                    
                if "【文字】" in response:
                    ocr_part = response.split("【文字】")[1].strip()
                    if ocr_part and ocr_part != "无":
                        ocr_text = ocr_part
            else:
                # 兜底: 如果解析失败,整个回答作为描述
                caption = response.strip()
            
            logger.debug(f"VLM analysis complete for {Path(image_path).name}")
            return {"caption": caption, "ocr_text": ocr_text}
            
        except Exception as e:
            logger.error(f"VLM analysis failed: {e}")
            return {"caption": "", "ocr_text": ""}
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        完整处理一张图片: YOLO + VLM
        
        Args:
            image_path: 图片路径
            
        Returns:
            {
                objects: List[{label, box, score}],
                caption: str,
                ocr_text: str
            }
        """
        logger.info(f"Processing image: {Path(image_path).name}")
        
        # Step 1: 物体检测
        objects = self.detect_objects(image_path)
        
        # Step 2: VLM 深度分析
        vlm_result = self.analyze_image_with_vlm(image_path)
        
        return {
            "objects": objects,
            "caption": vlm_result["caption"],
            "ocr_text": vlm_result["ocr_text"]
        }


# 全局单例实例
_global_processor: Optional[GlobalAIProcessor] = None


def get_processor() -> GlobalAIProcessor:
    """获取全局处理器实例"""
    global _global_processor
    if _global_processor is None:
        _global_processor = GlobalAIProcessor()
        _global_processor.load_models()
    return _global_processor
