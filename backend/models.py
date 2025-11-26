"""
Chinese-CLIP 模型管理器
使用单例模式确保模型只被加载一次
"""

import torch
from transformers import ChineseCLIPModel, ChineseCLIPProcessor
import logging
from .config import MODEL_NAME, DEVICE

logger = logging.getLogger(__name__)


class CLIPModelManager:
    """Chinese-CLIP 模型管理器 (单例模式)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            logger.info("初始化 Chinese-CLIP 模型管理器...")
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """加载模型和处理器"""
        try:
            logger.info(f"正在加载模型: {MODEL_NAME}")
            logger.info(f"设备: {DEVICE}")
            
            # 加载处理器
            self.processor = ChineseCLIPProcessor.from_pretrained(MODEL_NAME)
            
            # 加载模型
            self.model = ChineseCLIPModel.from_pretrained(MODEL_NAME)
            self.model.to(DEVICE)
            self.model.eval()  # 设置为评估模式
            
            logger.info("✅ 模型加载成功!")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise
    
    @torch.no_grad()
    def encode_image(self, image):
        """
        编码图片为特征向量
        
        Args:
            image: PIL Image 对象
            
        Returns:
            numpy.ndarray: 图片特征向量
        """
        try:
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            
            features = self.model.get_image_features(**inputs)
            
            # 归一化
            features = features / features.norm(dim=-1, keepdim=True)
            
            return features.cpu().numpy()[0]
            
        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            raise
    
    @torch.no_grad()
    def encode_text(self, text):
        """
        编码文本为特征向量
        
        Args:
            text: 中文查询文本
            
        Returns:
            numpy.ndarray: 文本特征向量
        """
        try:
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            
            features = self.model.get_text_features(**inputs)
            
            # 归一化
            features = features / features.norm(dim=-1, keepdim=True)
            
            return features.cpu().numpy()[0]
            
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            raise
    
    def get_info(self):
        """获取模型信息"""
        return {
            "model_name": MODEL_NAME,
            "device": DEVICE,
            "loaded": self._initialized
        }
