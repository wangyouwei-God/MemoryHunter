"""
查询扩展模块 - Phase 1优化
通过同义词扩展和多查询融合提升搜索准确率
"""

import jieba
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class QueryExpander:
    """查询扩展器 - 提升搜索召回率"""
    
    def __init__(self):
        # 中文同义词词典
        self.synonyms = {
            # 颜色相关
            "蓝色": ["天蓝", "湛蓝", "蔚蓝", "青蓝"],
            "红色": ["大红", "朱红", "crimson"],
            "绿色": ["翠绿", "碧绿", "青绿"],
            "黄色": ["金黄", "鹅黄", "嫩黄"],
            
            # 建筑相关
            "建筑": ["房屋", "大楼", "建筑物", "楼房", "楼宇"],
            "房子": ["房屋", "民居", "住宅"],
            "高楼": ["大楼", "摩天大楼", "高层建筑"],
            
            # 人物相关
            "人物": ["人", "人像", "肖像", "面孔", "人士"],
            "人": ["人物", "人员", "人士"],
            
            # 自然景观
            "天空": ["苍穹", "天际", "云天"],
            "大海": ["海洋", "海", "大洋"],
            "山": ["山峰", "高山", "山岳", "山脉"],
            "树": ["树木", "乔木", "林木"],
            
            # 动物相关
            "猫": ["猫咪", "小猫", "喵星人"],
            "狗": ["狗狗", "犬", "汪星人"],
            
            # 食物相关
            "食物": ["美食", "食品", "吃的"],
            "美食": ["食物", "佳肴", "菜肴"],
        }
        
        # 停用词
        self.stopwords = {"的", "是", "在", "了", "和", "与", "或", "等", "啊", "呢", "吗"}
        
        logger.info("✅ 查询扩展器初始化完成")
    
    def expand_query(self, query: str) -> List[str]:
        """
        扩展查询  
        
        Args:
            query: 原始查询字符串
            
        Returns:
            扩展后的查询列表
        """
        expanded_queries = [query]  # 始终包含原始查询
        
        # 1. 同义词扩展
        for word, synonyms in self.synonyms.items():
            if word in query:
                for syn in synonyms[:2]:  # 限制每个词最多2个同义词
                    expanded_query = query.replace(word, syn)
                    if expanded_query not in expanded_queries:
                        expanded_queries.append(expanded_query)
        
        # 2. 分词扩展 - 提取关键词
        tokens = list(jieba.cut(query))
        keywords = [t for t in tokens if t not in self.stopwords and len(t) > 1]
        
        # 添加主要关键词作为独立查询
        for keyword in keywords[:2]:  # 最多添加2个关键词
            if keyword != query and keyword not in expanded_queries:
                expanded_queries.append(keyword)
        
        logger.info(f"📝 查询扩展: '{query}' → {len(expanded_queries)} 个查询")
        logger.debug(f"   扩展查询: {expanded_queries}")
        
        return expanded_queries
    
    def add_synonym(self, word: str, synonyms: List[str]):
        """动态添加同义词"""
        if word not in self.synonyms:
            self.synonyms[word] = []
        self.synonyms[word].extend(synonyms)
        logger.info(f"✅ 添加同义词: {word} → {synonyms}")
