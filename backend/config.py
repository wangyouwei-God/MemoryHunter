"""
配置文件 (V1.0 - Mac/CPU Optimized)
仅启用轻量级 CLIP 模型
"""

from pathlib import Path

# ============ 路径配置 ============
PHOTOS_DIR = Path("/app/photos")
CHROMA_DIR = Path("/app/chroma_db")
FRONTEND_DIR = Path("/app/frontend")

# ============ 功能开关 ============
# V1.0 不支持 VLM 和混合检索
ENABLE_VLM = False
ENABLE_HYBRID_SEARCH = False

# ============ 模型配置 ============
# 使用 Chinese-CLIP (ViT-B/16)
MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"
DEVICE = "cpu"                             # Mac 推荐使用 CPU
BATCH_SIZE = 4                             # 小批次以节省内存

# ============ 搜索配置 ============
TOP_K = 20
SIMILARITY_THRESHOLD = 0.2

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