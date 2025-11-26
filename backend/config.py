"""
配置文件
所有系统配置集中管理
"""

from pathlib import Path

# ============ 路径配置 ============
PHOTOS_DIR = Path("/app/photos")          # 相册目录 (挂载点)
CHROMA_DIR = Path("/app/chroma_db")       # ChromaDB 存储目录
FRONTEND_DIR = Path("/app/frontend")      # 前端静态文件目录

# ============ V2.0 功能开关 ============
ENABLE_VLM = True                          # 启用 Mini-CPM-V (深度理解)
ENABLE_HYBRID_SEARCH = True                # 启用混合检索
ENABLE_LAZY_LOAD = True                    # VLM 懒加载（节省内存）

# ============ 模型配置 - V1.0 ============
MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"
DEVICE = "cpu"                             # 强制 CPU 模式（Docker）
BATCH_SIZE = 16                            # 批处理大小

# ============ VLM 配置 - V2.0 ============
VLM_MODEL_NAME = "openbmb/MiniCPM-Llama3-V-2_5"  # V2.5（transformers 4.40兼容）
VLM_USE_QUANTIZATION = False               # 关闭量化（CPU环境兼容性优先）
VLM_BATCH_SIZE = 2                         # VLM 批处理（8GB内存建议2）
VLM_MAX_NEW_TOKENS = 512                   # 最大生成token数
VLM_DEVICE = "cpu"                         # VLM 设备

# ============ 搜索配置 ============
TOP_K = 20                                 # 默认返回结果数量
SIMILARITY_THRESHOLD = 0.0                 # 相似度阈值 (0.0-1.0)

# V2.0 混合检索权重
HYBRID_SEARCH_WEIGHTS = {
    "visual": 0.4,      # 视觉相似度权重
    "semantic": 0.4,    # 语义相似度权重
    "keyword": 0.2,     # 关键词匹配权重
}

# ============ 图片格式 ============
SUPPORTED_FORMATS = {
    ".jpg", 
    ".jpeg", 
    ".png", 
    ".webp", 
    ".heic",
    ".JPG",
    ".JPEG",
    ".PNG",
    ".WEBP",
    ".HEIC"
}

# ============ 性能优化 ============
ENABLE_CACHE = True                        # 启用缓存
CACHE_SIZE = 100                           # 缓存结果数量
NUM_WORKERS = 2                            # 工作线程数（双核CPU）
PREFETCH = True                            # 预取数据

# ============ 内存管理 ============
MAX_MEMORY_GB = 5                          # 最大内存使用（GB）
GC_THRESHOLD = 50                          # 垃圾回收阈值（处理图片数）

# ============ 日志配置 ============
LOG_LEVEL = "INFO"

