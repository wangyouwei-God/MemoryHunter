"""
文件夹管理器
管理索引文件夹的配置、状态和统计信息
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FolderManager:
    """文件夹配置管理器"""
    
    def __init__(self, config_file: Path = None):
        """
        初始化文件夹管理器
        
        Args:
            config_file: 配置文件路径，默认为 ./folders_config.json
        """
        if config_file is None:
            config_file = Path("folders_config.json")
        
        self.config_file = config_file
        self.folders = self._load_config()
        logger.info(f"文件夹管理器初始化完成，已加载 {len(self.folders)} 个文件夹")
    
    def _load_config(self) -> List[Dict[str, Any]]:
        """从配置文件加载文件夹列表"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('folders', [])
            else:
                logger.info(f"配置文件不存在，创建新文件: {self.config_file}")
                return []
        
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return []
    
    def _save_config(self) -> bool:
        """保存文件夹配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({'folders': self.folders}, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"配置已保存到 {self.config_file}")
            return True
        
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def add_folder(self, folder_path: str, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        添加新文件夹
        
        Args:
            folder_path: 文件夹路径
            name: 文件夹显示名称（可选，默认使用路径最后一级）
        
        Returns:
            新添加的文件夹配置，失败返回 None
        """
        try:
            path = Path(folder_path)
            
            # 验证路径存在且是目录
            if not path.exists():
                logger.error(f"文件夹不存在: {folder_path}")
                return None
            
            if not path.is_dir():
                logger.error(f"路径不是文件夹: {folder_path}")
                return None
            
            # 检查是否已存在
            absolute_path = str(path.absolute())
            for folder in self.folders:
                if folder['path'] == absolute_path:
                    logger.warning(f"文件夹已存在: {folder_path}")
                    return folder
            
            # 创建新文件夹配置
            folder_config = {
                'id': str(uuid.uuid4()),
                'path': absolute_path,
                'name': name or path.name,
                'added_at': datetime.now().isoformat(),
                'last_scan': None,
                'image_count': 0,
                'indexed_count': 0,
                'status': 'pending'  # pending/indexing/active/paused/error
            }
            
            self.folders.append(folder_config)
            self._save_config()
            
            logger.info(f"✅ 添加文件夹: {folder_config['name']} ({folder_path})")
            return folder_config
        
        except Exception as e:
            logger.error(f"添加文件夹失败: {e}")
            return None
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """获取所有文件夹配置"""
        return self.folders
    
    def get_folder_by_id(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文件夹配置
        
        Args:
            folder_id: 文件夹ID
        
        Returns:
            文件夹配置，不存在返回 None
        """
        for folder in self.folders:
            if folder['id'] == folder_id:
                return folder
        return None
    
    def update_folder(self, folder_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新文件夹配置
        
        Args:
            folder_id: 文件夹ID
            updates: 要更新的字段
        
        Returns:
            是否更新成功
        """
        for folder in self.folders:
            if folder['id'] == folder_id:
                folder.update(updates)
                self._save_config()
                logger.debug(f"文件夹配置已更新: {folder_id}")
                return True
        
        logger.warning(f"文件夹不存在: {folder_id}")
        return False
    
    def remove_folder(self, folder_id: str) -> bool:
        """
        移除文件夹
        
        Args:
            folder_id: 文件夹ID
        
        Returns:
            是否移除成功
        """
        for i, folder in enumerate(self.folders):
            if folder['id'] == folder_id:
                removed = self.folders.pop(i)
                self._save_config()
                logger.info(f"✅ 移除文件夹: {removed['name']}")
                return True
        
        logger.warning(f"文件夹不存在: {folder_id}")
        return False
    
    def update_stats(self, folder_id: str, image_count: int = None, indexed_count: int = None) -> bool:
        """
        更新文件夹统计信息
        
        Args:
            folder_id: 文件夹ID
            image_count: 总图片数
            indexed_count: 已索引图片数
        
        Returns:
            是否更新成功
        """
        updates = {'last_scan': datetime.now().isoformat()}
        
        if image_count is not None:
            updates['image_count'] = image_count
        
        if indexed_count is not None:
            updates['indexed_count'] = indexed_count
        
        return self.update_folder(folder_id, updates)
    
    def set_folder_status(self, folder_id: str, status: str) -> bool:
        """
        设置文件夹状态
        
        Args:
            folder_id: 文件夹ID
            status: 状态 (pending/indexing/active/paused/error)
        
        Returns:
            是否设置成功
        """
        return self.update_folder(folder_id, {'status': status})
    
    def get_total_stats(self) -> Dict[str, int]:
        """
        获取所有文件夹的汇总统计
        
        Returns:
            统计信息字典
        """
        total_folders = len(self.folders)
        total_images = sum(f.get('image_count', 0) for f in self.folders)
        total_indexed = sum(f.get('indexed_count', 0) for f in self.folders)
        active_folders = sum(1 for f in self.folders if f.get('status') == 'active')
        
        return {
            'total_folders': total_folders,
            'active_folders': active_folders,
            'total_images': total_images,
            'total_indexed': total_indexed
        }
