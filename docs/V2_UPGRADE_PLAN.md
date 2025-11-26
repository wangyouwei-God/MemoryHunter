# MemoryHunter V2.0 升级计划

> Mini-CPM-V 集成 + 性能优化方案
> 
> 日期: 2025-11-26
> 目标配置: 8GB RAM, 双核 i5

---

## 🎯 升级目标

将 MemoryHunter 从 V1.0 (Chinese-CLIP) 升级到 V2.0 (Mini-CPM-V)，同时确保在 8GB 内存的电脑上流畅运行。

## 📊 性能目标

| 指标 | V1.0 | V2.0 目标 |
|------|------|----------|
| OCR 准确率 | 20% | **90%+** |
| 索引速度 | 0.1s/张 | 1.5-2s/张 |
| 内存占用 | 2GB | 4-5GB (优化后) |
| 搜索延迟 | 50ms | <100ms |

---

## 🔧 核心优化方案

### 1. 模型量化 (关键优化)

```python
# INT8 量化 - 内存减半
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0
)

model = MiniCPMV.from_pretrained(
    "openbmb/MiniCPM-V-2_6",
    quantization_config=quantization_config,
    torch_dtype=torch.float16,
    device_map="auto"
)

# 效果:
# - 内存: 4GB → 2.5GB
# - 速度: 几乎无损失
# - 准确率: 损失 <2%
```

### 2. Metal 加速 (macOS 特有)

```python
# 利用 Intel Iris Plus 640 GPU
import torch

# 检测 MPS (Metal Performance Shaders)
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("✅ 使用 Metal GPU 加速")
else:
    device = torch.device("cpu")

model = model.to(device)

# 效果:
# CPU: 2.5秒/张
# MPS: 1.5秒/张 (快 40%)
```

### 3. 分离部署架构

```yaml
方案: 索引服务 vs 搜索服务分离

索引时 (离线):
  加载: Mini-CPM-V + SigLIP + BGE-M3
  内存: 5-6 GB
  可以: 关闭其他应用
  
搜索时 (常驻):
  加载: SigLIP + BGE-M3 (不加载 VLM)
  内存: 2-3 GB
  体验: 流畅响应
  
好处:
  ✅ 索引时专注处理
  ✅ 查询时轻量流畅
  ✅ 内存利用最优
```

### 4. 按需加载策略

```python
class LazyVLM:
    """懒加载 VLM - 用时才加载"""
    
    def __init__(self):
        self.model = None
    
    def analyze(self, image):
        # 需要时才加载
        if self.model is None:
            self.model = self._load_model()
        
        result = self.model.generate(image)
        
        # 用完立即卸载
        del self.model
        self.model = None
        torch.cuda.empty_cache()  # 清理缓存
        
        return result
```

### 5. 智能批处理

```python
# 批量处理提升效率
batch_size = 4  # 4张图片一起处理

images = collect_images(batch_size)
results = model.batch_generate(images)

# 效果:
# 单张: 2秒/张 × 10张 = 20秒
# 批处理: 1.5秒/张 × 10张 = 15秒
# 节省: 25% 时间
```

---

## 📝 实施步骤

### Phase 1: 环境准备 (30分钟)

```bash
# 1. 安装 MPS 支持的 PyTorch
pip install torch torchvision torchaudio

# 2. 安装 Mini-CPM-V 依赖
pip install transformers accelerate bitsandbytes

# 3. 安装优化库
pip install onnxruntime pillow-simd

# 4. 验证 MPS
python -c "import torch; print(torch.backends.mps.is_available())"
```

### Phase 2: 模型下载 (10-20分钟)

```python
# 下载 Mini-CPM-V-2.6
from transformers import AutoModel

model = AutoModel.from_pretrained(
    "openbmb/MiniCPM-V-2_6",
    trust_remote_code=True,
    cache_dir="/Users/wangyouwei/.cache/huggingface"
)

# 模型大小: ~8GB
# 下载时间: 10-20分钟 (取决于网速)
```

### Phase 3: 代码升级 (2-3小时)

**3.1 新建 VLM 模块** (`backend/vlm.py`):
```python
- VLM 管理器
- Prompt 工程
- 批处理优化
- 懒加载逻辑
```

**3.2 升级索引器** (`backend/indexer.py`):
```python
- 集成 VLM 分析
- 双向量存储 (visual + text)
- 进度追踪优化
```

**3.3 升级检索器** (`backend/searcher.py`):
```python
- 混合检索逻辑
- 多路召回
- 结果融合
```

**3.4 更新配置** (`backend/config.py`):
```python
- VLM 配置参数
- 优化开关
- 批处理大小
```

### Phase 4: 测试验证 (1小时)

```bash
# 1. 小规模测试 (10张图片)
- 验证 OCR 准确率
- 测试索引速度
- 检查内存占用

# 2. 中等规模测试 (50张)
- 压力测试
- 性能监控
- 稳定性验证

# 3. 对比测试
- V1.0 vs V2.0
- 准确率提升
- 性能对比
```

---

## 🎛️ 配置建议

### 针对 8GB 内存的优化配置

```python
# config.py

# VLM 配置
VLM_CONFIG = {
    "model_name": "openbmb/MiniCPM-V-2_6",
    "quantization": "int8",  # 关键：INT8 量化
    "device": "mps",  # Metal GPU
    "max_memory": "3GB",  # 限制 VLM 内存
    "batch_size": 2,  # 小批量
    "lazy_load": True,  # 懒加载
}

# 视觉编码
VISUAL_CONFIG = {
    "model_name": "google/siglip-so400m-patch14-384",
    "device": "mps",
    "batch_size": 8,
}

# 文本编码
TEXT_CONFIG = {
    "model_name": "BAAI/bge-m3",
    "device": "cpu",  # BGE 在 CPU 上也很快
    "batch_size": 16,
}

# 性能优化
PERFORMANCE = {
    "enable_cache": True,
    "cache_size": 100,  # 缓存 100 个结果
    "num_workers": 2,  # 双核 CPU
    "prefetch": True,
}
```

---

## 🚀 预期效果

### 功能提升

```yaml
OCR 搜索:
  V1.0: "招商银行" → 找不到 ❌
  V2.0: "招商银行" → 找到 5 张 ✅
  
场景理解:
  V1.0: "夕阳" → 模糊匹配
  V2.0: "海边的日落" → 精准匹配 + 描述
  
智能标签:
  V1.0: 手动打标签
  V2.0: AI 自动生成 ["风景", "海滩", "日落", "自然"]
```

### 性能指标

```yaml
索引性能:
  200 张图片:
    V1.0: 20 秒
    V2.0: 5-6 分钟 (可接受，一次性任务)
  
  内存占用:
    峰值: 5GB (留 3GB 给系统)
    平均: 4GB
  
  CPU 使用:
    V1.0: 40%
    V2.0: 70-80% (索引时)

搜索性能:
  延迟: <100ms
  内存: 2-3GB (VLM 已卸载)
  体验: 流畅
```

---

## ⚠️ 注意事项

### 使用建议

1. **索引时关闭其他应用**
   - 释放内存给 VLM
   - 避免系统卡顿

2. **分批索引**
   - 50-100 张一批
   - 避免一次性处理太多

3. **监控内存**
   - 使用 Activity Monitor
   - 发现问题及时调整

4. **保留 V1.0 数据**
   - 备份现有数据库
   - 对比测试效果

### 回退方案

如果 V2.0 太慢或太卡：
```python
# 快速切换回 V1.0
USE_VLM = False  # config.py

# 或者混合模式
USE_VLM_FOR_IMPORTANT = True  # 只对重要图片用 VLM
```

---

## 📅 时间估算

```
环境准备: 30 分钟
模型下载: 20 分钟
代码开发: 3 小时
测试验证: 1 小时
────────────────────
总计: ~5 小时
```

---

## ✅ 验收标准

升级成功的标准：

- [ ] Mini-CPM-V 成功加载
- [ ] 量化和 MPS 加速生效
- [ ] OCR 准确率 > 85%
- [ ] 索引速度 < 2秒/张
- [ ] 内存占用 < 5GB
- [ ] 搜索延迟 < 100ms
- [ ] 系统保持流畅

---

**准备好了吗？让我们开始升级！** 🚀
