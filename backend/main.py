"""
MemoryHunter FastAPI 应用 - V2.0
提供图片索引和搜索的 REST API

V2.0 新增:
- Mini-CPM-V 深度分析
- OCR 文字识别
- 智能标签生成
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path

from .models import CLIPModelManager
from .database import VectorDatabase
from .indexer import ImageIndexer
from .searcher import ImageSearcher
from .config import FRONTEND_DIR, PHOTOS_DIR, ENABLE_VLM, VLM_MODEL_NAME, VLM_USE_QUANTIZATION

# V2.0: VLM 支持
if ENABLE_VLM:
    from .vlm import MiniCPMVManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ============ FastAPI 应用 ============
app = FastAPI(
    title="MemoryHunter API",
    description="智能相册搜索系统 - V2.0 (Chinese-CLIP + Mini-CPM-V)",
    version="2.0.0"
)

# ============ 全局组件初始化 ============
logger.info("🚀 正在启动 MemoryHunter V2.0...")

try:
    # 初始化视觉模型管理器（CLIP，单例）
    model_manager = CLIPModelManager()
    logger.info("✅ CLIP 模型已加载")
    
    # V2.0: 初始化 VLM 管理器（可选）
    vlm_manager = None
    if ENABLE_VLM:
        try:
            logger.info("🔄 正在加载 Mini-CPM-V 模型...")
            vlm_manager = MiniCPMVManager()
            vlm_manager.load_model(
                model_name=VLM_MODEL_NAME,
                use_quantization=VLM_USE_QUANTIZATION
            )
            logger.info("✅ Mini-CPM-V 模型已加载 (V2.0 功能已启用)")
        except Exception as e:
            logger.error(f"⚠️ VLM 加载失败，将仅使用 CLIP: {e}")
            vlm_manager = None
    
    # 初始化向量数据库
    vector_db = VectorDatabase()
    logger.info("✅ 向量数据库已初始化")
    
    # Phase 1优化: 初始化查询扩展器
    try:
        from .query_expander import QueryExpander
        query_expander = QueryExpander()
        logger.info("✅ 查询扩展器已初始化 (Phase 1优化)")
    except Exception as e:
        logger.warning(f"⚠️ 查询扩展器加载失败: {e}")
        query_expander = None
    
    # 初始化索引器和搜索器（传入 VLM 和 QueryExpander）
    indexer = ImageIndexer(model_manager, vector_db, vlm_manager)
    searcher = ImageSearcher(model_manager, vector_db, query_expander)
    
    logger.info("✅ MemoryHunter V2.0 初始化完成!")
    if ENABLE_VLM and vlm_manager:
        logger.info("🌟 V2.0 功能：OCR识别、智能描述、自动标签 已启用")
    
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
    total_images: int
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
    global indexing_status
    
    if indexing_status["is_indexing"]:
        raise HTTPException(status_code=409, detail="索引正在进行中，请稍后再试")
    
    def index_task():
        """后台索引任务"""
        global indexing_status
        
        try:
            indexing_status["is_indexing"] = True
            indexing_status["message"] = "正在索引..."
            
            def progress_callback(current, total):
                indexing_status["progress"] = current
                indexing_status["total"] = total
            
            # 执行索引
            result = indexer.index_all(progress_callback=progress_callback)
            
            indexing_status["is_indexing"] = False
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


@app.get("/api/index/status")
async def get_index_status():
    """获取索引状态"""
    return indexing_status


@app.post("/api/search", response_model=SearchResponse)
async def search_images(request: SearchRequest):
    """
    搜索图片
    
    Args:
        request: 搜索请求
        
    Returns:
        搜索结果
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
        model_info = model_manager.get_info()
        
        return StatsResponse(
            total_images=db_stats['total_images'],
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
    vlm_status = "enabled" if (ENABLE_VLM and vlm_manager is not None) else "disabled"
    return {
        "status": "healthy",
        "service": "MemoryHunter",
        "version": "2.0.0",
        "vlm_enabled": vlm_status
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
