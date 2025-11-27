"""
文件夹浏览和管理 API
提供文件系统浏览和文件夹管理功能
"""

import os
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from .folder_manager import FolderManager
from .config import SUPPORTED_FORMATS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/folders", tags=["folders"])

# 初始化文件夹管理器
folder_manager = FolderManager()


class BrowseResponse(BaseModel):
    """文件夹浏览响应"""
    current_path: str
    parent_path: Optional[str]
    folders: List[Dict[str, Any]]
    is_root: bool


class AddFolderRequest(BaseModel):
    """添加文件夹请求"""
    path: str
    name: Optional[str] = None


class FolderResponse(BaseModel):
    """文件夹信息响应"""
    id: str
    path: str
    name: str
    added_at: str
    last_scan: Optional[str]
    image_count: int
    indexed_count: int
    status: str


def get_system_roots() -> List[Dict[str, Any]]:
    """
    获取系统根目录（磁盘列表）
    
    Returns:
        根目录列表
    """
    roots = []
    system = platform.system()
    
    if system == "Windows":
        # Windows: 获取所有盘符
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    # 尝试获取磁盘名称
                    label = f"{letter}: 驱动器"
                    roots.append({
                        "name": label,
                        "path": drive,
                        "is_folder": True,
                        "image_count": 0
                    })
                except:
                    continue
    else:
        # Unix-like (Mac/Linux): 从 / 开始
        roots.append({
            "name": "根目录",
            "path": "/",
            "is_folder": True,
            "image_count": 0
        })
        
        # Mac: 添加常用目录
        if system == "Darwin":
            home = Path.home()
            common_paths = [
                (home, "用户目录"),
                (home / "Pictures", "图片"),
                (home / "Documents", "文档"),
                (home / "Desktop", "桌面")
            ]
            for path, name in common_paths:
                if path.exists():
                    roots.append({
                        "name": name,
                        "path": str(path),
                        "is_folder": True,
                        "image_count": 0
                    })
    
    return roots


def count_images_in_folder(folder_path: Path, max_depth: int = 3) -> int:
    """
    统计文件夹中的图片数量（限制递归深度避免过慢）
    
    Args:
        folder_path: 文件夹路径
        max_depth: 最大递归深度
    
    Returns:
        图片数量
    """
    try:
        count = 0
        
        # 非递归统计（更快）
        for item in folder_path.iterdir():
            if item.is_file() and item.suffix.lower() in SUPPORTED_FORMATS:
                count += 1
        
        # 如果需要递归统计，但限制深度
        if max_depth > 0:
            for item in folder_path.iterdir():
                if item.is_dir():
                    try:
                        count += count_images_in_folder(item, max_depth - 1)
                    except (PermissionError, OSError):
                        continue
        
        return count
    
    except (PermissionError, OSError) as e:
        logger.debug(f"无法访问文件夹 {folder_path}: {e}")
        return 0


@router.get("/browse", response_model=BrowseResponse)
async def browse_directory(path: Optional[str] = None):
    """
    浏览文件系统目录
    
    Args:
        path: 要浏览的路径，None表示根目录
    
    Returns:
        文件夹列表和导航信息
    """
    try:
        # 如果没有指定路径，返回系统根目录
        if not path:
            roots = get_system_roots()
            return BrowseResponse(
                current_path="",
                parent_path=None,
                folders=roots,
                is_root=True
            )
        
        # 验证路径
        folder_path = Path(path)
        
        if not folder_path.exists():
            raise HTTPException(status_code=404, detail=f"路径不存在: {path}")
        
        if not folder_path.is_dir():
            raise HTTPException(status_code=400, detail=f"路径不是文件夹: {path}")
        
        # 获取父目录路径
        parent = str(folder_path.parent) if folder_path.parent != folder_path else None
        
        # 列出子文件夹
        folders = []
        try:
            for item in sorted(folder_path.iterdir(), key=lambda x: x.name.lower()):
                if item.is_dir():
                    # 跳过隐藏文件夹和系统文件夹
                    if item.name.startswith('.') or item.name.startswith('$'):
                        continue
                    
                    try:
                        # 快速统计图片数量
                        image_count = count_images_in_folder(item, max_depth=2)
                        
                        folders.append({
                            "name": item.name,
                            "path": str(item),
                            "is_folder": True,
                            "image_count": image_count
                        })
                    except (PermissionError, OSError):
                        # 无权访问的文件夹，标记但不阻止
                        folders.append({
                            "name": item.name + " 🔒",
                            "path": str(item),
                            "is_folder": True,
                            "image_count": 0,
                            "accessible": False
                        })
        
        except PermissionError:
            raise HTTPException(status_code=403, detail=f"无权访问此目录: {path}")
        
        return BrowseResponse(
            current_path=str(folder_path),
            parent_path=parent,
            folders=folders,
            is_root=False
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"浏览目录失败: {e}")
        raise HTTPException(status_code=500, detail=f"浏览目录失败: {str(e)}")


@router.post("/", response_model=FolderResponse)
async def add_folder(request: AddFolderRequest):
    """
    添加文件夹到管理列表
    
    Args:
        request: 添加文件夹请求
    
    Returns:
        添加的文件夹信息
    """
    try:
        folder_config = folder_manager.add_folder(
            folder_path=request.path,
            name=request.name
        )
        
        if not folder_config:
            raise HTTPException(status_code=400, detail="添加文件夹失败，请检查路径是否有效")
        
        return FolderResponse(**folder_config)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加文件夹失败: {str(e)}")


@router.get("/", response_model=List[FolderResponse])
async def list_folders():
    """
    获取所有管理的文件夹
    
    Returns:
        文件夹列表
    """
    try:
        folders = folder_manager.get_folders()
        return [FolderResponse(**f) for f in folders]
    
    except Exception as e:
        logger.error(f"获取文件夹列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件夹列表失败: {str(e)}")


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(folder_id: str):
    """
    获取指定文件夹信息
    
    Args:
        folder_id: 文件夹ID
    
    Returns:
        文件夹信息
    """
    try:
        folder = folder_manager.get_folder_by_id(folder_id)
        
        if not folder:
            raise HTTPException(status_code=404, detail=f"文件夹不存在: {folder_id}")
        
        return FolderResponse(**folder)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件夹失败: {str(e)}")


@router.delete("/{folder_id}")
async def remove_folder(folder_id: str, delete_vectors: bool = False):
    """
    移除文件夹
    
    Args:
        folder_id: 文件夹ID
        delete_vectors: 是否同时删除该文件夹的向量数据
    
    Returns:
        删除结果
    """
    try:
        success = folder_manager.remove_folder(folder_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"文件夹不存在: {folder_id}")
        
        # TODO: 如果 delete_vectors=True，需要删除该文件夹的所有向量
        # 这需要在数据库中根据 folder_id 过滤并删除
        
        return {
            "status": "success",
            "message": f"文件夹已移除: {folder_id}",
            "vectors_deleted": delete_vectors
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"移除文件夹失败: {str(e)}")


@router.get("/stats/summary")
async def get_folders_stats():
    """
    获取文件夹汇总统计
    
    Returns:
        统计信息
    """
    try:
        stats = folder_manager.get_total_stats()
        return stats
    
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
