"""
工具函数模块
提供文件哈希计算、文件验证等通用功能
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path, algorithm: str = 'md5') -> str:
    """
    计算文件的哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法 ('md5', 'sha256')
    
    Returns:
        文件哈希值（十六进制字符串）
    """
    try:
        hash_func = hashlib.md5() if algorithm == 'md5' else hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # 分块读取，避免大文件内存占用
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    except Exception as e:
        logger.error(f"计算文件哈希失败 {file_path}: {e}")
        raise


def get_file_metadata(file_path: Path) -> Dict[str, Any]:
    """
    获取文件基本元数据
    
    Args:
        file_path: 文件路径
    
    Returns:
        包含文件元数据的字典
    """
    try:
        stat = os.stat(file_path)
        
        return {
            'file_size': stat.st_size,
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat() if hasattr(stat, 'st_birthtime') else None,
        }
    
    except Exception as e:
        logger.error(f"获取文件元数据失败 {file_path}: {e}")
        raise


def verify_image_file(file_path: Path) -> bool:
    """
    验证图片文件完整性
    
    Args:
        file_path: 图片文件路径
    
    Returns:
        图片是否有效
    """
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    
    except Exception as e:
        logger.warning(f"图片文件验证失败 {file_path}: {e}")
        return False


def is_valid_image_extension(file_path: Path, supported_formats: set = None) -> bool:
    """
    检查文件扩展名是否为支持的图片格式
    
    Args:
        file_path: 文件路径
        supported_formats: 支持的格式集合
    
    Returns:
        是否为有效图片扩展名
    """
    if supported_formats is None:
        # 默认支持的格式
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.heic', '.heif'}
    
    return file_path.suffix.lower() in supported_formats


def file_exists_and_accessible(file_path: Path) -> bool:
    """
    检查文件是否存在且可访问
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件是否存在且可读
    """
    try:
        return file_path.exists() and os.access(file_path, os.R_OK)
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式
    
    Args:
        size_bytes: 字节大小
    
    Returns:
        格式化后的字符串（如 "1.5 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_current_timestamp() -> str:
    """
    获取当前时间戳（ISO格式）
    
    Returns:
        ISO格式的时间戳字符串
    """
    return datetime.now().isoformat()
