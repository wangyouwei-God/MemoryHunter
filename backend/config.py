"""
配置文件
所有系统配置集中管理
"""

from pathlib import Path

# ============ 路径配置 ============
PHOTOS_DIR = Path("f:/MemoryHunter/temp2/test_photos")  # 本地相册目录
CHROMA_DIR = Path("f:/MemoryHunter/temp2/chroma_db")     # ChromaDB 存储目录
FRONTEND_DIR = Path("f:/MemoryHunter/temp2/frontend")    # 前端静态文件目录

# ============ V2.0 功能开关 ============
ENABLE_VLM = True                          # ✅ 启用VLM深度理解 (Phase 1优化)
ENABLE_HYBRID_SEARCH = True                # ✅ 启用混合检索 (Phase 1优化)
ENABLE_LAZY_LOAD = True                    # VLM 懒加载（节省内存）

# ============ 模型配置 - V1.0 ============
MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"
DEVICE = "cuda"                            # 启用 CUDA 加速 (RTX 4080)
BATCH_SIZE = 32                            # 增加批处理以利用GPU

# ============ VLM 配置 - V2.0 ============
VLM_MODEL_NAME = "openbmb/MiniCPM-Llama3-V-2_5"  # V2.5（transformers 4.40兼容）
VLM_USE_QUANTIZATION = False               # 关闭量化（12GB VRAM充足）
VLM_BATCH_SIZE = 4                         # 增加VLM批处理（12GB VRAM）
VLM_MAX_NEW_TOKENS = 512                   # 最大生成token数
VLM_DEVICE = "cuda"                        # 启用GPU加速

# ============ 搜索配置 ============
TOP_K = 20                                 # 默认返回结果数量
SIMILARITY_THRESHOLD = 0.0                 # 相似度阈值 (0.0-1.0)

# V2.0 混合检索权重 (Phase 1优化)
HYBRID_SEARCH_WEIGHTS = {
    "visual": 0.35,      # 视觉相似度权重 (CLIP)
    "semantic": 0.35,    # 语义相似度权重 (VLM)
    "keyword": 0.30,     # 关键词匹配权重 (提升精确匹配)
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
CACHE_SIZE = 200                           # 增加缓存（充足内存）
NUM_WORKERS = 4                            # 增加工作线程（GPU环境）
PREFETCH = True                            # 预取数据

# ============ 内存管理 ============
MAX_MEMORY_GB = 5                          # 最大内存使用（GB）
GC_THRESHOLD = 50                          # 垃圾回收阈值（处理图片数）

# ============ 日志配置 ============
LOG_LEVEL = "INFO"

