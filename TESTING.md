# MemoryHunter-MVP 测试指南

## 📋 测试前准备

### 1. 检查 Docker 构建状态

首先确认 Docker 镜像是否构建完成：

```bash
# 查看构建进度（如果还在构建中）
docker ps -a

# 查看已有的镜像
docker images | grep memory-hunter
```

如果镜像构建尚未完成，等待完成后再继续。

---

## 🧪 完整测试流程

### 步骤 1: 准备测试数据

**创建测试图片目录**（如果还没有）：

```bash
# 创建测试目录
mkdir -p ~/Pictures/TestDataset

# 复制一些测试图片到该目录
# 建议准备 20-100 张不同类型的图片：
# - 风景照片（海滩、山、天空）
# - 人物照片
# - 动物照片（猫、狗等）
# - 美食照片
# - 其他各种主题
```

**测试图片要求**：
- ✅ 支持格式：JPG, PNG, WEBP, HEIC
- ✅ 建议数量：20-100 张（首次测试）
- ✅ 多样化：不同主题、颜色、场景

---

### 步骤 2: 运行 Docker 容器

```bash
# 进入项目目录
cd /Users/wangyouwei/Projects/vector_photo

# 确保之前的容器已停止和删除（如果有）
docker stop memory-hunter 2>/dev/null || true
docker rm memory-hunter 2>/dev/null || true

# 运行容器
docker run -d \
  --name memory-hunter \
  -p 8000:8000 \
  -v ~/Pictures/TestDataset:/app/photos:ro \
  -v ~/memory-hunter-data:/app/chroma_db \
  memory-hunter:latest

# 查看启动日志
docker logs -f memory-hunter
```

**日志中应该看到**：
```
🚀 正在启动 MemoryHunter...
正在加载模型: OFA-Sys/chinese-clip-vit-base-patch16
设备: cpu
✅ 模型加载成功!
初始化 ChromaDB，存储路径: /app/chroma_db
✅ ChromaDB 初始化成功，当前图片数: 0
✅ MemoryHunter 初始化完成!
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**按 `Ctrl+C` 退出日志查看**（容器会继续在后台运行）

---

### 步骤 3: 访问 Web 界面

打开浏览器，访问：**http://localhost:8000**

您应该看到：
- 📸 MemoryHunter 标题
- 统计卡片显示 "已索引图片: 0"
- "🔄 开始索引" 按钮
- 搜索输入框（灰色禁用状态，因为还没索引）

---

### 步骤 4: 执行图片索引

#### 4.1 通过 Web 界面索引

1. **点击 "🔄 开始索引" 按钮**
2. **观察进度**：
   - 按钮文字变为 "⏳ 索引中 X/Y"
   - 进度条显示实时进度
   - 统计卡片中的 "已索引图片" 数字逐渐增加

3. **等待完成**：
   - 100 张图片约需 **5-10 分钟**（CPU 模式）
   - 完成后按钮恢复为 "🔄 开始索引"
   - "索引状态" 显示 "索引完成! 成功: X, 失败: 0"

#### 4.2 通过 API 索引（可选）

```bash
# 触发索引
curl -X POST http://localhost:8000/api/index

# 查看索引状态
curl http://localhost:8000/api/index/status

# 查看统计信息
curl http://localhost:8000/api/stats
```

---

### 步骤 5: 测试搜索功能

#### 5.1 基础搜索测试

在搜索框中输入以下查询，点击"搜索"：

**测试用例 1: 自然风光**
```
查询: 蓝色的天空
预期: 返回天空、晴天相关的照片
```

**测试用例 2: 动物**
```
查询: 猫咪
预期: 返回猫的照片
```

**测试用例 3: 颜色**
```
查询: 红色
预期: 返回主要颜色为红色的照片
```

**测试用例 4: 场景**
```
查询: 海滩
预期: 返回海边、沙滩相关照片
```

**测试用例 5: 物体**
```
查询: 食物
预期: 返回美食照片
```

#### 5.2 观察搜索结果

搜索完成后，您应该看到：
- ✅ 结果数量："找到 X 个相关结果"
- ✅ 图片网格：3 列展示
- ✅ 每张图片显示：
  - 图片缩略图
  - 相似度分数（百分比）
  - 文件名
- ✅ 点击图片可在新标签页查看大图

#### 5.3 调整搜索参数

**测试参数调整**：

1. **返回数量测试**：
   - 拖动 "返回数量" 滑块到 10
   - 搜索 "风景"
   - 确认只返回 10 个结果

2. **相似度阈值测试**：
   - 拖动 "相似度阈值" 到 0.3
   - 搜索 "天空"
   - 确认只返回相似度 ≥ 30% 的结果

---

### 步骤 6: 测试 HEIC 格式支持（macOS 用户）

如果您有 macOS 相册的 HEIC 格式照片：

```bash
# 复制一些 HEIC 照片到测试目录
cp ~/Pictures/Photos\ Library.photoslibrary/*.HEIC ~/Pictures/TestDataset/

# 重新索引（点击 "开始索引" 按钮）

# 搜索测试
# 输入描述 HEIC 照片内容的查询词
```

**预期结果**：
- ✅ HEIC 照片成功索引
- ✅ 搜索结果中能看到 HEIC 照片
- ✅ 点击能正常显示

---

### 步骤 7: API 测试（可选，适合开发者）

#### 7.1 搜索 API

```bash
# 基础搜索
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "蓝色的天空",
    "top_k": 10,
    "threshold": 0.0
  }'

# 高阈值搜索
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "猫咪",
    "top_k": 5,
    "threshold": 0.5
  }'
```

**预期响应**：
```json
{
  "query": "蓝色的天空",
  "results": [
    {
      "path": "/app/photos/IMG_001.jpg",
      "filename": "IMG_001.jpg",
      "score": 0.8732
    }
  ],
  "count": 10
}
```

#### 7.2 统计 API

```bash
curl http://localhost:8000/api/stats | jq
```

**预期响应**：
```json
{
  "total_images": 100,
  "model_info": {
    "model_name": "OFA-Sys/chinese-clip-vit-base-patch16",
    "device": "cpu",
    "loaded": true
  },
  "indexing_status": {
    "is_indexing": false,
    "progress": 100,
    "total": 100,
    "message": "索引完成! 成功: 100, 失败: 0"
  }
}
```

#### 7.3 健康检查

```bash
curl http://localhost:8000/api/health
```

---

### 步骤 8: 性能测试

#### 8.1 索引性能

记录以下指标：

```bash
# 开始时间
echo "开始索引: $(date)"

# 触发索引
curl -X POST http://localhost:8000/api/index

# 监控进度（每 10 秒查询一次）
while true; do
  curl http://localhost:8000/api/index/status | jq
  sleep 10
done

# 结束时间
echo "索引完成: $(date)"
```

**记录指标**：
- 图片数量
- 索引时间
- 成功/失败数量

#### 8.2 搜索性能

```bash
# 测试搜索响应时间
time curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "蓝色", "top_k": 20}'
```

**预期**：< 200ms

---

### 步骤 9: 压力测试（可选）

#### 9.1 并发搜索测试

```bash
# 使用 ApacheBench (如果已安装)
ab -n 100 -c 10 -p search.json -T application/json http://localhost:8000/api/search

# search.json 内容:
echo '{"query":"天空","top_k":10}' > search.json
```

#### 9.2 大数据集测试

```bash
# 测试 500-1000 张图片的索引
# 复制更多图片到测试目录
# 重新索引并记录性能
```

---

### 步骤 10: 错误处理测试

#### 10.1 损坏图片测试

```bash
# 创建一个损坏的图片文件
echo "not an image" > ~/Pictures/TestDataset/broken.jpg

# 重新索引
# 查看日志确认跳过了损坏图片
docker logs memory-hunter | grep "broken.jpg"
```

**预期**：应该看到警告日志，但不影响其他图片索引

#### 10.2 空查询测试

在 Web 界面输入空字符串搜索，应该看到提示："请输入搜索内容"

---

## ✅ 测试检查清单

| 测试项 | 状态 | 备注 |
|--------|------|------|
| ☐ Docker 容器成功启动 | | 查看日志确认 |
| ☐ Web 界面正常访问 | | http://localhost:8000 |
| ☐ 图片索引成功 | | 无失败记录 |
| ☐ 基础搜索功能 | | 至少 3 种不同查询 |
| ☐ 搜索结果准确性 | | 相似度 > 50% |
| ☐ UI 交互流畅 | | 无卡顿 |
| ☐ HEIC 格式支持 | | macOS 用户 |
| ☐ API 响应正常 | | 200 状态码 |
| ☐ 错误处理正常 | | 损坏图片跳过 |
| ☐ 性能符合预期 | | 索引 <1分钟/10张 |

---

## 🐛 常见问题处理

### 问题 1: 容器启动失败

```bash
# 查看错误日志
docker logs memory-hunter

# 检查端口占用
lsof -i :8000

# 重新构建镜像
docker build -t memory-hunter:latest .
```

### 问题 2: 索引速度很慢

**原因**：CPU 模式下正常现象

**解决**：
- 减少测试图片数量
- 耐心等待（100 张约 5-10 分钟）

### 问题 3: 搜索结果不准确

**尝试**：
- 降低相似度阈值（从 0.3 降到 0.0）
- 使用更具体的描述词
- 重新索引图片

### 问题 4: 图片无法显示

```bash
# 检查图片路径映射
docker exec memory-hunter ls -la /app/photos

# 确认图片格式支持
docker exec memory-hunter file /app/photos/xxx.jpg
```

---

## 📊 预期测试结果

**索引性能**（100张图片，CPU模式）：
- 索引时间: 5-10 分钟
- 成功率: 100%（无损坏图片）
- 内存占用: 2-3 GB

**搜索性能**：
- 响应时间: < 200ms
- 准确率: 相关度 > 60%
- Top-10 结果

**系统稳定性**：
- 无崩溃
- 无内存泄漏
- 日志无 ERROR

---

## 🎯 测试成功标准

✅ **基本功能**：
- 索引成功率 100%
- 搜索能返回相关结果
- UI 交互正常

✅ **性能要求**：
- 索引速度 ~1 分钟/10 张（CPU）
- 搜索延迟 < 200ms

✅ **用户体验**：
- 界面美观流畅
- 实时进度反馈
- 错误提示友好

---

## 📝 测试报告模板

```markdown
## MemoryHunter-MVP 测试报告

**测试时间**: 2024-XX-XX
**测试人员**: XXX
**环境**: macOS 13 (x86_64), Docker Desktop

### 测试数据
- 图片数量: XXX 张
- 图片格式: JPG/PNG/HEIC
- 测试场景: 风景/人物/动物/美食

### 测试结果

#### 功能测试
- 索引功能: ✅ 通过
- 搜索功能: ✅ 通过
- UI 交互: ✅ 通过

#### 性能测试
- 索引时间: XX 分钟
- 搜索延迟: XX ms
- 内存占用: XX GB

#### 问题记录
1. 问题描述
2. 复现步骤
3. 解决方案

### 结论
- [ ] 通过，可以投入使用
- [ ] 需要优化
- [ ] 存在阻塞问题
```

---

## 🚀 下一步

测试通过后，您可以：

1. **正式使用**：
   ```bash
   # 挂载真实相册目录
   docker run -d \
     -p 8000:8000 \
     -v ~/Pictures:/app/photos:ro \
     -v ~/memory-hunter-data:/app/chroma_db \
     --name memory-hunter \
     memory-hunter:latest
   ```

2. **性能优化**：
   - 考虑使用 GPU 加速
   - 使用 ONNX Runtime 优化推理

3. **功能扩展**：
   - 添加以图搜图
   - 实现智能相册分类
   - 支持视频搜索

---

**祝测试顺利！** 🎉

如有任何问题，请查看日志：`docker logs memory-hunter`
