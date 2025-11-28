"""
配置文件 (V2.0 Pro - GPU Accelerated)
启用 VLM (MiniCPM-V) + Object Detection (YOLO) + Hybrid Search
"""

import os
from pathlib import Path

# ============ 路径配置 ============
PHOTOS_DIR = Path("/app/photos")
CHROMA_DIR = Path("/app/chroma_db")
FRONTEND_DIR = Path("/app/frontend")

# ============ 功能开关 ============
# V2.0 Pro: 启用 VLM 和混合检索
ENABLE_VLM = os.getenv("ENABLE_VLM", "true").lower() == "true"
ENABLE_HYBRID_SEARCH = True
ENABLE_OBJECT_DETECTION = True

# ============ 模型配置 ============
# Visual Encoder: Chinese-CLIP (V1.0 兼容)
CLIP_MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"

# VLM: MiniCPM-V 2.5 (Int4)
VLM_MODEL_NAME = "openbmb/MiniCPM-V-2_5-int4"
# VLM Prompt Language: 'zh' (Chinese) or 'en' (English)
VLM_PROMPT_LANGUAGE = os.getenv("VLM_LANGUAGE", "zh")  # Default: Chinese

# Semantic Encoder: BGE-M3 for text embedding
BGE_MODEL_NAME = "BAAI/bge-m3"

# Object Detection: YOLOv8-X
YOLO_MODEL_NAME = "yolov8x.pt"
YOLO_CONF_THRESHOLD = 0.3

# Device
DEVICE = "cuda"  # V2.0 Pro requires GPU
BATCH_SIZE = 1   # VLM 推理使用 batch_size=1 以节省显存

# ============ 搜索配置 ============
TOP_K = 50       # 增加召回数量以支持混合搜索
SIMILARITY_THRESHOLD = 0.2

# RRF (Reciprocal Rank Fusion) 参数
RRF_K = 60

# ============ 图片格式 ============
SUPPORTED_FORMATS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".JPG", ".JPEG", ".PNG", ".WEBP", ".HEIC"
}

# ============ 性能优化 ============
ENABLE_CACHE = True
CACHE_SIZE = 50
NUM_WORKERS = 2

# ============ 日志配置 ============
LOG_LEVEL = "INFO"