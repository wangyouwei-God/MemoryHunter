"""
文件夹管理 API
提供子文件夹扫描、验证和索引控制功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from pathlib import Path
import logging

from .config import PHOTOS_DIR

router = APIRouter(prefix="/api/folders", tags=["folders"])
logger = logging.getLogger(__name__)


class SubfolderInfo(BaseModel):
    """子文件夹信息"""
    path: str  # 相对路径，如 "Vacation" 或 "2024/Summer"
    full_path: str  # 完整路径 (容器内)
    exists: bool
    image_count: int
    indexed: bool
    enabled: bool


class AddSubfolderRequest(BaseModel):
    """添加子文件夹请求"""
    subfolder_path: str = Field(..., description="子文件夹相对路径，如 'Vacation' 或 '2024/Summer'")
    
    @validator('subfolder_path')
    def validate_subfolder_path(cls, v):
        """验证路径安全性"""
        # 不允许绝对路径
        if v.startswith('/') or v.startswith('~'):
            raise ValueError("只能使用相对路径，不能以 / 或 ~ 开头")
        
        # 不允许父目录引用
        if '..' in v:
            raise ValueError("路径不能包含 '..'")
        
        # 不允许包含特殊字符
        if any(char in v for char in ['*', '?', '<', '>', '|', '\x00']):
            raise ValueError("路径包含非法字符")
        
        return v.strip()


class ToggleSubfolderRequest(BaseModel):
    """启用/禁用子文件夹索引请求"""
    subfolder_path: str
    enabled: bool


def validate_subfolder(subfolder_path: str) -> Path:
    """
    验证子文件夹是否存在
    
    Args:
        subfolder_path: 相对路径
        
    Returns:
        完整Path对象
        
    Raises:
        HTTPException: 路径不存在或无权限
    """
    try:
        full_path = PHOTOS_DIR / subfolder_path
        resolved = full_path.resolve()
        
        # 确保解析后的路径仍在 PHOTOS_DIR 内 (防止路径穿越攻击)
        if not str(resolved).startswith(str(PHOTOS_DIR.resolve())):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_PATH",
                    "message": "路径超出允许范围",
                    "subfolder": subfolder_path
                }
            )
        
        # 检查路径是否存在
        if not resolved.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "SUBFOLDER_NOT_FOUND",
                    "message": f"子文件夹不存在: {subfolder_path}",
                    "suggestion": "请确认路径拼写正确，或在 Pictures 目录下创建该文件夹",
                    "expected_full_path": str(full_path)
                }
            )
        
        # 检查是否为目录
        if not resolved.is_dir():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "NOT_A_DIRECTORY",
                    "message": f"路径不是文件夹: {subfolder_path}",
                    "path": str(resolved)
                }
            )
        
        return resolved
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"路径验证失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "VALIDATION_ERROR",
                "message": "路径验证失败",
                "details": str(e)
            }
        )


@router.get("/", response_model=List[SubfolderInfo])
async def list_subfolders():
    """
    自动扫描 Pictures 目录下的一级子文件夹
    
    Returns:
        子文件夹列表
    """
    try:
        if not PHOTOS_DIR.exists():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "PHOTOS_DIR_NOT_FOUND",
                    "message": "照片根目录不存在",
                    "path": str(PHOTOS_DIR),
                    "suggestion": "请检查 docker-compose.yml 中的 volumes 配置"
                }
            )
        
        subfolders = []
        
        # 扫描一级子目录
        for item in PHOTOS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # 计算图片数量 (简化版, 只统计直接子文件)
                from .config import SUPPORTED_FORMATS
                image_count = sum(1 for f in item.rglob('*') if f.suffix in SUPPORTED_FORMATS)
                
                relative_path = str(item.relative_to(PHOTOS_DIR))
                
                subfolders.append(SubfolderInfo(
                    path=relative_path,
                    full_path=str(item),
                    exists=True,
                    image_count=image_count,
                    indexed=False,  # TODO: 从数据库读取索引状态
                    enabled=True     # TODO: 从配置读取启用状态
                ))
        
        logger.info(f"扫描到 {len(subfolders)} 个子文件夹")
        return subfolders
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫描子文件夹失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SCAN_FAILED",
                "message": "扫描子文件夹失败",
                "details": str(e)
            }
        )


@router.post("/validate")
async def validate_subfolder_api(request: AddSubfolderRequest):
    """
    验证子文件夹是否存在
    
    Args:
        request: 包含 subfolder_path 的请求
        
    Returns:
        验证结果
    """
    try:
        full_path = validate_subfolder(request.subfolder_path)
        
        # 统计图片数量
        from .config import SUPPORTED_FORMATS
        image_count = sum(1 for f in full_path.rglob('*') if f.suffix in SUPPORTED_FORMATS)
        
        return {
            "valid": True,
            "subfolder": request.subfolder_path,
            "full_path": str(full_path),
            "image_count": image_count,
            "message": "文件夹验证成功"
        }
        
    except HTTPException as e:
        # 返回友好的错误信息
        return {
            "valid": False,
            "subfolder": request.subfolder_path,
            "error": e.detail
        }


@router.get("/status")
async def get_photos_dir_status():
    """
    获取 Pictures 根目录状态
    
    Returns:
        目录状态信息
    """
    try:
        exists = PHOTOS_DIR.exists()
        accessible = PHOTOS_DIR.is_dir() if exists else False
        
        total_images = 0
        if accessible:
            from .config import SUPPORTED_FORMATS
            total_images = sum(1 for f in PHOTOS_DIR.rglob('*') if f.suffix in SUPPORTED_FORMATS)
        
        return {
            "path": str(PHOTOS_DIR),
            "exists": exists,
            "accessible": accessible,
            "total_images": total_images,
            "platform_default": "~/Pictures",
            "message": "根目录状态正常" if accessible else "根目录不可访问"
        }
        
    except Exception as e:
        logger.error(f"获取根目录状态失败: {e}")
        return {
            "path": str(PHOTOS_DIR),
            "exists": False,
            "accessible": False,
            "error": str(e)
        }
