"""
文件夹扫描器
提供健壮的图片文件扫描、验证和去重功能
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .config import SUPPORTED_FORMATS
from .utils import (
    calculate_file_hash,
    get_file_metadata,
    verify_image_file,
    is_valid_image_extension,
    file_exists_and_accessible
)

logger = logging.getLogger(__name__)


class FolderScanner:
    """文件夹扫描器 - 健壮的图片扫描"""
    
    def __init__(self, vector_db):
        """
        初始化扫描器
        
        Args:
            vector_db: VectorDatabase实例（用于去重检查）
        """
        self.db = vector_db
        self.logger = logging.getLogger(__name__)
    
    def scan_folder(
        self,
        folder_path: Path,
        check_duplicates: bool = True,
        verify_images: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        扫描文件夹，返回所有有效图片及错误列表
        
        Args:
            folder_path: 要扫描的文件夹路径
            check_duplicates: 是否检查重复（通过文件哈希）
            verify_images: 是否验证图片完整性
        
        Returns:
            (valid_images, errors): 有效图片列表和错误信息列表
        """
        valid_images = []
        errors = []
        
        if not folder_path.exists():
            errors.append(f"文件夹不存在: {folder_path}")
            return valid_images, errors
        
        if not folder_path.is_dir():
            errors.append(f"路径不是文件夹: {folder_path}")
            return valid_images, errors
        
        self.logger.info(f"开始扫描文件夹: {folder_path}")
        
        # 递归查找所有文件
        file_count = 0
        for file_path in folder_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            file_count += 1
            
            # 检查1: 文件扩展名
            if not is_valid_image_extension(file_path, SUPPORTED_FORMATS):
                continue
            
            # 检查2: 文件可访问性
            if not file_exists_and_accessible(file_path):
                errors.append(f"无权访问: {file_path}")
                continue
            
            try:
                # 检查3: 图片完整性验证（可选）
                if verify_images and not verify_image_file(file_path):
                    errors.append(f"图片文件损坏: {file_path}")
                    continue
                
                # 检查4: 计算文件哈希
                try:
                    file_hash = calculate_file_hash(file_path)
                except Exception as e:
                    errors.append(f"计算哈希失败 {file_path}: {str(e)}")
                    continue
                
                # 检查5: 去重检查（可选）
                if check_duplicates:
                    existing_path = self.db.check_hash_exists(file_hash)
                    if existing_path:
                        self.logger.debug(f"跳过重复文件: {file_path} (已存在: {existing_path})")
                        continue
                
                # 获取文件元数据
                try:
                    metadata = get_file_metadata(file_path)
                except Exception as e:
                    errors.append(f"获取元数据失败 {file_path}: {str(e)}")
                    continue
                
                # 添加到有效图片列表
                valid_images.append({
                    'path': str(file_path.absolute()),
                    'filename': file_path.name,
                    'file_hash': file_hash,
                    'file_size': metadata['file_size'],
                    'last_modified': metadata['last_modified'],
                    'exists': True
                })
                
            except Exception as e:
                errors.append(f"处理文件失败 {file_path}: {str(e)}")
                continue
        
        self.logger.info(
            f"✅ 扫描完成: 文件总数={file_count}, "
            f"有效图片={len(valid_images)}, 错误={len(errors)}"
        )
        
        return valid_images, errors
    
    def quick_count(self, folder_path: Path, max_depth: int = None) -> int:
        """
        快速统计文件夹中图片数量（不做详细验证）
        
        Args:
            folder_path: 文件夹路径
            max_depth: 最大递归深度，None表示无限制
        
        Returns:
            图片数量估计
        """
        try:
            count = 0
            
            if max_depth == 0:
                # 仅统计当前层级
                for file_path in folder_path.iterdir():
                    if file_path.is_file() and is_valid_image_extension(file_path, SUPPORTED_FORMATS):
                        count += 1
            else:
                # 递归统计
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file() and is_valid_image_extension(file_path, SUPPORTED_FORMATS):
                        count += 1
                        # 限制深度
                        if max_depth and len(file_path.relative_to(folder_path).parts) > max_depth:
                            continue
            
            return count
        
        except Exception as e:
            self.logger.error(f"统计图片数量失败 {folder_path}: {e}")
            return 0
    
    def scan_multiple_folders(
        self,
        folder_paths: List[Path],
        check_duplicates: bool = True,
        verify_images: bool = True
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[str]]]:
        """
        扫描多个文件夹
        
        Args:
            folder_paths: 文件夹路径列表
            check_duplicates: 是否检查重复
            verify_images: 是否验证图片
        
        Returns:
            (folder_images, folder_errors): 每个文件夹的图片和错误
        """
        all_images = {}
        all_errors = {}
        
        for folder_path in folder_paths:
            folder_key = str(folder_path)
            images, errors = self.scan_folder(
                folder_path,
                check_duplicates=check_duplicates,
                verify_images=verify_images
            )
            all_images[folder_key] = images
            all_errors[folder_key] = errors
        
        return all_images, all_errors
