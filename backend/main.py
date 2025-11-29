"""
MemoryHunter FastAPI 应用 - V2.0 Pro
提供图片索引和搜索的 REST API

V2.0 Pro 特性:
- MiniCPM-V 2.5 (Int4) 深度图片理解
- YOLOv8-X 物体检测
- BGE-M3 语义编码
- 双路混合搜索 (RRF 融合)
- ChromaDB 双集合存储
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path

from .models import CLIPModelManager, BGEModelManager
from .database import VectorDatabase
from .indexer import ImageIndexer
from .searcher import ImageSearcher
from .processors import get_processor
from .config import (
    FRONTEND_DIR, PHOTOS_DIR,
    ENABLE_VLM, ENABLE_OBJECT_DETECTION
)

# 导入文件夹管理路由
from .folders import router as folders_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ============ FastAPI 应用 ============
app = FastAPI(
    title="MemoryHunter API",
    description="智能相册搜索系统 - V2.0 Pro (VLM + Hybrid Search)",
    version="2.0.0-pro"
)

# 注册文件夹管理路由
app.include_router(folders_router)

# ============ 全局组件初始化 ============
logger.info(" 正在启动 MemoryHunter V2.0 Pro...")

try:
    # 1. 初始化 CLIP 模型管理器 (视觉编码)
    clip_model = CLIPModelManager()
    logger.info("✅ Chinese-CLIP 模型已加载")
    
    # 2. 初始化向量数据库 (双集合)
    vector_db = VectorDatabase()
    logger.info("✅ 向量数据库已初始化 (双集合模式)")
    
    # 3. (可选) 初始化 Pro 组件
    bge_model = None
    ai_processor = None
    
    if ENABLE_VLM:
        try:
            # 3a. 初始化 BGE 语义编码器
            bge_model = BGEModelManager()
            logger.info("✅ BGE-M3 语义编码器已加载")
            
            # 3b. 初始化 AI 处理器 (VLM + YOLO)
            ai_processor = get_processor()
            logger.info("✅ GlobalAIProcessor 已加载 (MiniCPM-V + YOLO)")
            
        except Exception as e:
            logger.warning(f"⚠️ Pro 组件加载失败,将回退到 V1.0 模式: {e}")
            bge_model = None
            ai_processor = None
    
    # 4. 初始化索引器和搜索器
    indexer = ImageIndexer(
        visual_model=clip_model,
        vector_db=vector_db,
        semantic_model=bge_model,
        ai_processor=ai_processor
    )
    
    searcher = ImageSearcher(
        visual_model=clip_model,
        vector_db=vector_db,
        semantic_model=bge_model
    )
    
    mode_info = "V2.0 Pro (VLM + Hybrid Search)" if bge_model else "V1.0 兼容模式 (CLIP Only)"
    logger.info(f"✅ MemoryHunter 初始化完成!")
    logger.info(f"📌 运行模式: {mode_info}")
    
except Exception as e:
    logger.error(f"❌ 初始化失败: {e}")
    raise

# ============ 全局状态管理 ============
indexing_status = {
    "is_indexing": False,
    "progress": 0,
    "total": 0,
    "message": "就绪"
}

# 索引取消标志
cancel_indexing_flag = False


# ============ Pydantic 模型 ============
class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="中文搜索查询", min_length=1)
    top_k: int = Field(20, description="返回结果数量", ge=1, le=100)
    threshold: float = Field(0.0, description="相似度阈值", ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: List[Dict[str, Any]]
    count: int


class IndexResponse(BaseModel):
    """索引响应"""
    status: str
    message: str


class StatsResponse(BaseModel):
    """统计信息响应"""
    total_images_visual: int
    total_images_semantic: int
    hybrid_mode: bool
    model_info: Dict[str, Any]
    indexing_status: Dict[str, Any]


# ============ API 端点 ============

@app.get("/")
async def root():
    """根路径，重定向到前端"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/index", response_model=IndexResponse)
async def trigger_index(background_tasks: BackgroundTasks):
    """
    触发图片索引
    后台异步执行，立即返回
    """
    global indexing_status, cancel_indexing_flag
    
    if indexing_status["is_indexing"]:
        raise HTTPException(status_code=409, detail="索引正在进行中，请稍后再试")
    
    def index_task():
        """后台索引任务 (支持取消)"""
        global indexing_status, cancel_indexing_flag
        
        try:
            indexing_status["is_indexing"] = True
            indexing_status["message"] = "正在索引..."
            cancel_indexing_flag = False  # 重置取消标志
            
            def progress_callback(current, total):
                indexing_status["progress"] = current
                indexing_status["total"] = total
            
            # 执行索引 (indexer内部会检查cancel_indexing_flag)
            result = indexer.index_all(progress_callback=progress_callback)
            
            indexing_status["is_indexing"] = False
            
            if cancel_indexing_flag:
                indexing_status["message"] = f"索引已取消! 成功: {result['success']}, 失败: {result['failed']}"
            else:
                indexing_status["message"] = f"索引完成! 成功: {result['success']}, 失败: {result['failed']}"
            
        except Exception as e:
            logger.error(f"索引任务失败: {e}")
            indexing_status["is_indexing"] = False
            indexing_status["message"] = f"索引失败: {str(e)}"
    
    # 添加到后台任务
    background_tasks.add_task(index_task)
    
    return IndexResponse(
        status="started",
        message="索引任务已启动，将在后台执行"
    )


@app.post("/api/index/cancel")
async def cancel_index():
    """
    取消正在进行的索引任务
    """
    global cancel_indexing_flag, indexing_status
    
    if not indexing_status["is_indexing"]:
        raise HTTPException(status_code=400, detail="当前没有正在进行的索引任务")
    
    cancel_indexing_flag = True
    logger.info("收到索引取消请求")
    
    return {"status": "cancelling", "message": "正在取消索引任务..."}


@app.get("/api/index/status")
async def get_index_status():
    """获取索引状态"""
    return indexing_status


@app.post("/api/search", response_model=SearchResponse)
async def search_images(request: SearchRequest):
    """
    搜索图片 (自动选择混合搜索或单路搜索)
    
    Args:
        request: 搜索请求
        
    Returns:
        搜索结果 (包含 Pro 元数据)
    """
    try:
        results = searcher.search(
            query_text=request.query,
            top_k=request.top_k,
            threshold=request.threshold
        )
        
        return SearchResponse(
            query=request.query,
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """获取系统统计信息"""
    try:
        db_stats = vector_db.get_stats()
        
        # 收集所有已加载模型的信息
        model_info = {
            "clip": clip_model.get_info()
        }
        
        if bge_model:
            model_info["bge"] = bge_model.get_info()
        
        if ai_processor:
            model_info["pro_enabled"] = True
        else:
            model_info["pro_enabled"] = False
        
        return StatsResponse(
            total_images_visual=db_stats.get('total_images_visual', 0),
            total_images_semantic=db_stats.get('total_images_semantic', 0),
            hybrid_mode=db_stats.get('hybrid_mode', False),
            model_info=model_info,
            indexing_status=indexing_status
        )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@app.delete("/api/database")
async def clear_database():
    """清空数据库"""
    try:
        vector_db.clear()
        return {"status": "success", "message": "数据库已清空"}
    except Exception as e:
        logger.error(f"清空数据库失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空数据库失败: {str(e)}")


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "MemoryHunter",
        "version": "2.0.0-pro",
        "mode": "Pro" if bge_model else "Lite"
    }


# ============ 静态文件服务 ============
# 挂载前端文件
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    logger.info(f"✅ 前端文件已挂载: {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ 前端目录不存在: {FRONTEND_DIR}")


# 提供图片访问接口
@app.get("/photos/{photo_path:path}")
async def serve_photo(photo_path: str):
    """提供图片文件访问"""
    full_path = PHOTOS_DIR / photo_path
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    
    return FileResponse(str(full_path))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
