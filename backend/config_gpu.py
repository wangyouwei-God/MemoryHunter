"""
配置文件 (GPU 极速版)
专为 HP Z Studio (48G VRAM) 优化
"""

from pathlib import Path
import os

# ============ 路径配置 ============
PHOTOS_DIR = Path("/app/photos")
CHROMA_DIR = Path("/app/chroma_db")
FRONTEND_DIR = Path("/app/frontend")

# ============ V2.0 功能开关 ============
ENABLE_VLM = True
ENABLE_HYBRID_SEARCH = True
ENABLE_LAZY_LOAD = False               # 显存极大，不需要懒加载，直接常驻内存响应最快

# ============ 模型配置 - V1.0 ============
MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"
DEVICE = "cuda"                        # 🚀 开启 GPU 加速
BATCH_SIZE = 64                        # 🚀 批量处理能力提升 4 倍 (原 16)

# ============ VLM 配置 - V2.0 ============
VLM_MODEL_NAME = "openbmb/MiniCPM-Llama3-V-2_5"
VLM_USE_QUANTIZATION = False           # 🚀 关闭量化，使用 FP16 精度更高
VLM_BATCH_SIZE = 8                     # 🚀 VLM 批处理提升 4 倍 (原 2)
VLM_MAX_NEW_TOKENS = 1024              # 生成更详细的描述
VLM_DEVICE = "cuda"                    # 🚀 VLM 使用 GPU

# ============ 搜索配置 ============
TOP_K = 50                             # 默认返回更多结果
SIMILARITY_THRESHOLD = 0.2

HYBRID_SEARCH_WEIGHTS = {
    "visual": 0.4,
    "semantic": 0.4,
    "keyword": 0.2,
}

# ============ 图片格式 ============
SUPPORTED_FORMATS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".JPG", ".JPEG", ".PNG", ".WEBP", ".HEIC"
}

# ============ 性能优化 ============
ENABLE_CACHE = True
CACHE_SIZE = 500                       # 🚀 缓存扩大 5 倍
NUM_WORKERS = 8                        # 🚀 利用多核 CPU
PREFETCH = True

# ============ 内存管理 ============
MAX_MEMORY_GB = 32                     # 🚀 允许使用更多系统内存
GC_THRESHOLD = 200

# ============ 日志配置 ============
LOG_LEVEL = "INFO"
