"""
维护与健康检查 API
提供数据库健康检查和清理功能
"""

import os
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging

from .database import VectorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    total_records: int
    valid_files: int
    deleted_files: int
    deletion_rate: float
    recommendations: list


class CleanupRequest(BaseModel):
    """清理请求"""
    auto_remove: bool = False


class CleanupResponse(BaseModel):
    """清理响应"""
    found: int
    cleaned: int
    deleted_files: list


@router.post("/health-check", response_model=HealthCheckResponse)
async def run_health_check():
    """
    运行数据库健康检查
    
    检查所有索引记录，验证文件是否仍然存在
    
    Returns:
        健康检查结果
    """
    try:
        vector_db = VectorDatabase()
        
        # 获取所有记录
        all_records = vector_db.get_all_records()
        total = len(all_records)
        
        if total == 0:
            return HealthCheckResponse(
                total_records=0,
                valid_files=0,
                deleted_files=0,
                deletion_rate=0.0,
                recommendations=["数据库为空，请先索引图片"]
            )
        
        logger.info(f"🔍 开始健康检查，共 {total} 条记录...")
        
        # 验证文件存在性
        valid_count = 0
        deleted_count = 0
        
        for record in all_records:
            file_path = Path(record['metadata'].get('path', ''))
            
            if file_path.exists():
                valid_count += 1
            else:
                deleted_count += 1
                # 标记为已删除
                try:
                    vector_db.mark_file_deleted(record['id'])
                except Exception as e:
                    logger.warning(f"标记失败 {record['id']}: {e}")
        
        # 计算删除率
        deletion_rate = (deleted_count / total) * 100 if total > 0 else 0.0
        
        # 生成建议
        recommendations = []
        if deletion_rate > 20:
            recommendations.append(f"⚠️ 删除率较高 ({deletion_rate:.1f}%)，建议运行清理")
        elif deletion_rate > 5:
            recommendations.append(f"🔔 发现部分已删除文件 ({deletion_rate:.1f}%)，可选择性清理")
        else:
            recommendations.append("✅ 数据库健康状态良好")
        
        if deleted_count > 0:
            recommendations.append(f"发现 {deleted_count} 个已删除文件，可通过清理端点移除")
        
        logger.info(
            f"✅ 健康检查完成: 总数={total}, 有效={valid_count}, "
            f"已删除={deleted_count}, 删除率={deletion_rate:.2f}%"
        )
        
        return HealthCheckResponse(
            total_records=total,
            valid_files=valid_count,
            deleted_files=deleted_count,
            deletion_rate=round(deletion_rate, 2),
            recommendations=recommendations
        )
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_database(request: CleanupRequest):
    """
    清理已删除文件的向量记录
    
    Args:
        request: 清理请求（auto_remove=True 时自动删除，False 时仅预览）
    
    Returns:
        清理结果
    """
    try:
        vector_db = VectorDatabase()
        
        # 执行清理
        result = vector_db.cleanup_deleted_files(auto_remove=request.auto_remove)
        
        if request.auto_remove:
            logger.info(f"🧹 已清理 {result['cleaned']} 个已删除文件的记录")
        else:
            logger.info(f"📋 发现 {result['found']} 个已删除文件（预览模式）")
        
        # 格式化删除文件列表
        deleted_files_info = [
            {
                'id': f['id'],
                'path': f['path'],
                'filename': f['filename']
            }
            for f in result.get('deleted_files', [])
        ]
        
        return CleanupResponse(
            found=result.get('found', 0),
            cleaned=result.get('cleaned', 0),
            deleted_files=deleted_files_info
        )
    
    except Exception as e:
        logger.error(f"清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/stats")
async def get_maintenance_stats():
    """
    获取维护统计信息
    
    Returns:
        维护相关统计
    """
    try:
        vector_db = VectorDatabase()
        
        # 获取基本统计
        db_stats = vector_db.get_stats()
        
        # 获取已删除文件数量
        deleted_files = vector_db.get_deleted_files()
        
        return {
            "total_records": db_stats.get('total_images', 0),
            "deleted_files_count": len(deleted_files),
            "database_health": "healthy" if len(deleted_files) == 0 else "needs_attention"
        }
    
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/optimize")
async def optimize_database(background_tasks: BackgroundTasks):
    """
    优化数据库（后台任务）
    
    执行完整的健康检查和自动清理
    
    Returns:
        优化任务状态
    """
    def optimize_task():
        try:
            logger.info("🔧 开始数据库优化...")
            
            vector_db = VectorDatabase()
            
            # 1. 健康检查
            all_records = vector_db.get_all_records()
            deleted_count = 0
            
            for record in all_records:
                file_path = Path(record['metadata'].get('path', ''))
                if not file_path.exists():
                    vector_db.mark_file_deleted(record['id'])
                    deleted_count += 1
            
            # 2. 自动清理
            if deleted_count > 0:
                result = vector_db.cleanup_deleted_files(auto_remove=True)
                logger.info(f"✅ 优化完成: 清理了 {result['cleaned']} 条记录")
            else:
                logger.info("✅ 数据库已是最优状态")
        
        except Exception as e:
            logger.error(f"优化失败: {e}")
    
    # 添加后台任务
    background_tasks.add_task(optimize_task)
    
    return {
        "status": "started",
        "message": "数据库优化任务已启动"
    }
