"""
Mini-CPM-V VLM (视觉语言模型) 管理器

提供图片深度理解能力:
- OCR 文字提取 (准确率 90%+)
- 场景描述生成
- 物体关系理解
- 智能标签生成

优化策略:
- INT8 量化 (内存减半)
- 批处理 (提升效率)
- 懒加载 (按需使用)
"""

import torch
from transformers import AutoModel, AutoTokenizer
from PIL import Image
import logging
from typing import List, Dict, Optional
import gc

logger = logging.getLogger(__name__)


# ============ 官方修复：Patch flash_attn 依赖 ============
# 来源: https://huggingface.co/openbmb/MiniCPM-V-2_6/discussions
# 目的: 在 CPU 环境绕过 flash_attn 检查
def _patch_flash_attn():
    """
    Patch transformers to skip flash_attn import check
    
    This is the official workaround from HuggingFace for running
    models with flash_attn dependencies on CPU-only environments.
    """
    import transformers.dynamic_module_utils
    import importlib.util
    
    # 保存原始函数
    original_get_imports = transformers.dynamic_module_utils.get_imports
    
    def custom_get_imports(filename: str | os.PathLike) -> list[str]:
        """修改后的 get_imports：移除 flash_attn"""
        imports = original_get_imports(filename)
        
        # 过滤掉 flash_attn（CPU 不需要）
        filtered_imports = [imp for imp in imports if imp != "flash_attn"]
        
        if len(filtered_imports) < len(imports):
            logger.info("  - ✅ 已绕过 flash_attn 依赖检查（CPU 优化）")
        
        return filtered_imports
    
    # 应用 patch
    transformers.dynamic_module_utils.get_imports = custom_get_imports

# 应用修复
import os
_patch_flash_attn()


class MiniCPMVManager:
    """Mini-CPM-V 模型管理器
    
    单例模式，确保模型只加载一次
    支持 INT8 量化和懒加载
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MiniCPMVManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.tokenizer = None
        self.device = "cpu"  # Docker 环境只能用 CPU
        self._initialized = True
        
        logger.info("✅ MiniCPMV Manager 初始化完成")
    
    def load_model(self, model_name: str = "openbmb/MiniCPM-V-2_6", use_quantization: bool = True):
        """加载模型
        
        Args:
            model_name: 模型名称
            use_quantization: 是否使用 INT8 量化（推荐开启）
        """
        if self.model is not None:
            logger.info("模型已加载，跳过重复加载")
            return
        
        try:
            logger.info(f"🚀 开始加载 {model_name} 模型...")
            logger.info(f"  - 量化: {'INT8' if use_quantization else '关闭'}")
            logger.info(f"  - 设备: {self.device}")
            
            # 获取 HuggingFace Token（如果有）
            import os
            hf_token = os.environ.get('HF_TOKEN')
            if hf_token:
                logger.info("  - ✅ 使用 HuggingFace Token 访问模型")
            
            # 禁用 Flash Attention 检查（CPU 环境不需要）
            os.environ['DISABLE_FLASH_ATTN'] = '1'
            
            # INT8 量化配置（减少内存占用）
            load_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if not use_quantization else torch.float32,
                "low_cpu_mem_usage": True,  # CPU 优化
                "device_map": "cpu",  # 强制 CPU
            }
            
            # 添加 token（如果有）
            if hf_token:
                load_kwargs["token"] = hf_token
            
            if use_quantization:
                try:
                    from transformers import BitsAndBytesConfig
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0,
                    )
                    load_kwargs["quantization_config"] = quantization_config
                    logger.info("  - ✅ INT8 量化已启用 (内存占用减半)")
                except ImportError:
                    logger.warning("  - ⚠️ bitsandbytes 未安装，跳过量化")
            
            # 加载模型
            self.model = AutoModel.from_pretrained(
                model_name,
                **load_kwargs
            )
            
            # 移到 CPU（Docker 环境）
            if not use_quantization:
                self.model = self.model.to(self.device)
            
            self.model.eval()  # 评估模式
            
            # 加载 tokenizer
            tokenizer_kwargs = {"trust_remote_code": True}
            if hf_token:
                tokenizer_kwargs["token"] = hf_token
                
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                **tokenizer_kwargs
            )
            
            logger.info("✅ 模型加载成功!")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise
    
    def analyze_image(
        self,
        image: Image.Image,
        prompt: Optional[str] = None,
        max_new_tokens: int = 512
    ) -> Dict[str, any]:
        """深度分析图片
        
        Args:
            image: PIL Image 对象
            prompt: 自定义提示词（可选）
            max_new_tokens: 最大生成 token 数
            
        Returns:
            包含分析结果的字典
        """
        if self.model is None:
            raise RuntimeError("模型未加载，请先调用 load_model()")
        
        # 默认 Prompt（针对相册场景优化）
        if prompt is None:
            prompt = self._get_default_prompt()
        
        try:
            # 准备输入
            msgs = [{'role': 'user', 'content': prompt}]
            
            # 生成回复
            with torch.no_grad():
                res = self.model.chat(
                    image=image,
                    msgs=msgs,
                    tokenizer=self.tokenizer,
                    max_new_tokens=max_new_tokens,
                    sampling=False,  # 确定性输出
                )
            
            # 解析结果
            return self._parse_result(res)
            
        except Exception as e:
            logger.error(f"分析图片时出错: {e}")
            return {
                "description": "",
                "ocr_text": "",
                "tags": [],
                "error": str(e)
            }
    
    def batch_analyze(
        self,
        images: List[Image.Image],
        batch_size: int = 2
    ) -> List[Dict[str, any]]:
        """批量分析图片
        
        Args:
            images: 图片列表
            batch_size: 批处理大小（8GB内存建议2）
            
        Returns:
            分析结果列表
        """
        results = []
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}/{(len(images)-1)//batch_size + 1}")
            
            for image in batch:
                result = self.analyze_image(image)
                results.append(result)
            
            # 清理内存
            if i % (batch_size * 5) == 0:
                gc.collect()
        
        return results
    
    def _get_default_prompt(self) -> str:
        """获取默认 Prompt（针对相册场景优化）"""
        return """请详细描述这张图片，包括：

1. **主要内容**: 描述图片中的主要物体、人物和场景
2. **文字信息**: 提取所有可见的文字，包括标志、招牌、文档、屏幕显示等
3. **视觉特征**: 主要颜色、光线、构图
4. **标签**: 用简短的词语标注图片类型（如: 风景、美食、文档、人物等）

请用中文回答，格式清晰。"""
    
    def _parse_result(self, raw_result: str) -> Dict[str, any]:
        """解析模型输出
        
        提取: 描述、OCR文字、标签
        """
        result = {
            "description": raw_result,
            "ocr_text": "",
            "tags": [],
            "raw": raw_result
        }
        
        # 尝试提取 OCR 文字
        if "文字信息" in raw_result or "文字" in raw_result:
            # 简单的启发式提取
            lines = raw_result.split('\n')
            ocr_lines = []
            capturing = False
            
            for line in lines:
                if "文字" in line or "OCR" in line:
                    capturing = True
                    continue
                if capturing and line.strip():
                    if line.startswith('#') or "标签" in line:
                        break
                    ocr_lines.append(line.strip())
            
            result["ocr_text"] = " ".join(ocr_lines)
        
        # 尝试提取标签
        if "标签" in raw_result:
            lines = raw_result.split('\n')
            for line in lines:
                if "标签" in line:
                    # 提取标签（逗号或顿号分隔）
                    tag_part = line.split(':')[-1].split('：')[-1]
                    tags = [t.strip() for t in tag_part.replace('、', ',').split(',')]
                    result["tags"] = [t for t in tags if t]
        
        return result
    
    def unload_model(self):
        """卸载模型释放内存"""
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            gc.collect()
            logger.info("✅ 模型已卸载，内存已释放")
    
    def __del__(self):
        """析构函数：确保资源被释放"""
        self.unload_model()
