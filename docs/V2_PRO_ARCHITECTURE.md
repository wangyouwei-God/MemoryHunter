# MemoryHunter V2.0 Pro - Technical Architecture & Execution Plan

## 1. 核心理念 (Core Philosophy)
打造**世界顶尖**的本地相册搜索工具，利用 **RTX 4080 (12G)** 的极致算力，从“特征匹配”进化为**“深度语义理解”**。通过多模型协同（VLM + Object Detection + Embedding），实现对图片信息的**全量提取**与**精准检索**。

---

## 2. 模型矩阵 (Model Matrix)

| 角色 | 模型名称 | 版本/配置 | 显存占用 (Est.) | 核心任务 |
| :--- | :--- | :--- | :--- | :--- |
| **大脑 (Brain)** | **MiniCPM-V 2.5** | **Int4 Quantized** | ~7.0 GB | 生成深度描述 (Caption)、提取 OCR 文字 |
| **眼睛 (Eyes)** | **YOLOv8** | **X (Extra Large)** | ~1.0 GB | 物体检测、生成 Bounding Box (高亮框) |
| **直觉 (Intuition)** | **SigLIP / CLIP** | **ViT-B/16** | ~0.5 GB | 提取视觉特征向量 (以图搜图) |
| **翻译 (Translator)** | **BGE-M3** | **FP16** | ~0.5 GB | 将 VLM 的描述文本转化为语义向量 |
| **总计** | | | **~9.0 GB** | **剩余 ~3GB 给系统与推理缓存** |

> **关键决策**: 必须使用 **MiniCPM-V 2.5 Int4 量化版**。FP16 版本 (16GB+) 会导致显存溢出至慢速 RAM，严重拖慢索引速度。

---

## 3. 索引流程 (Indexing Pipeline)
*目标：将非结构化的图片转化为结构化的“知识图谱”。*

此流程为**后台异步串行**执行，确保显存不爆炸。

### Step 1: 加载与预处理 (Loader)
*   **输入**: 图片文件路径 (e.g., `~/Photos/2024/party.jpg`)
*   **操作**:
    *   读取图片二进制数据。
    *   提取 **EXIF 元数据** (拍摄时间、GPS、相机型号)。
    *   生成缩略图路径。

### Step 2: 物体定位 (The Locator - YOLOv8)
*   **输入**: 原图
*   **操作**: 运行 YOLOv8-X 推理。
*   **输出**: `object_list`
    ```json
    [
      {"label": "person", "box": [100, 100, 200, 500], "score": 0.95},
      {"label": "cake", "box": [300, 400, 400, 500], "score": 0.88}
    ]
    ```

### Step 3: 深度理解 (The Describer - MiniCPM-V)
*   **输入**: 原图 + Prompt
    > *Prompt*: "请详细描述这张图片。包括画面中的主要物体、人物动作、场景氛围、颜色光影。如果图片中包含文字，请完整提取出来。"
*   **操作**: 运行 VLM 推理。
*   **输出**:
    *   `caption`: "这是一张温馨的生日派对照片..." (用于搜索)
    *   `ocr_text`: "Happy Birthday" (用于展示/搜索)

### Step 4: 向量化 (The Embedder)
*   **视觉向量**: 图片 -> **SigLIP** -> `vector_visual` (512d)
*   **语义向量**: `caption` + `ocr_text` -> **BGE-M3** -> `vector_semantic` (1024d)

### Step 5: 持久化存储 (Storage - Milvus/Chroma)
*   将上述所有数据写入数据库，构建**双向量索引**。

---

## 4. 搜索流程 (Search Pipeline)
*目标：双路召回，RRF 融合，实现“所想即所得”。*

### Step 1: 查询理解 (Query Understanding)
*   **输入**: 用户 Query (e.g., "去年那个写着Happy的蛋糕")
*   **操作**:
    *   (可选) LLM 解析时间词 "去年" -> `date_filter: 2024`。
    *   提取关键词 "Happy" (OCR意图)。

### Step 2: 双路召回 (Dual-Route Retrieval)
*   **视觉路 (Visual Route)**:
    *   Query -> SigLIP Text Encoder -> `q_vec_visual`
    *   搜索 `vector_visual` -> Top 50 结果
*   **语义路 (Semantic Route)**:
    *   Query -> BGE-M3 -> `q_vec_semantic`
    *   搜索 `vector_semantic` -> Top 50 结果

### Step 3: 融合排序 (Fusion & Re-ranking)
*   **算法**: **RRF (Reciprocal Rank Fusion)**
    *   `Score = 1 / (k + Rank_Visual) + 1 / (k + Rank_Semantic)`
*   **逻辑**: 同时在“视觉上像”和“描述上匹配”的图片排名最高。

### Step 4: 结果展示 (Frontend Presentation)
*   **列表页**: 展示融合后的 Top K 图片。
*   **详情页 (Pro Feature)**:
    *   **OCR 面板**: 展示 `ocr_text`，支持一键复制。
    *   **智能高亮**: 鼠标悬停在 `object_list` 中的标签上时，在图片上绘制 `box` 红框。
    *   **AI 描述**: 展示 `caption`，让用户知道 AI 看到了什么。

---

## 5. 硬件资源调度策略 (Resource Scheduling)

为了在 12G 显存上跑满这套流程，我们需要精细的调度：

1.  **模型常驻 (Resident)**:
    *   由于 12G 刚好能放下所有量化后的模型，建议**全部常驻显存**，避免反复加载卸载带来的 I/O 延迟。
2.  **批处理 (Batching)**:
    *   **索引时**: 建议 `Batch Size = 1`。因为 VLM 推理显存波动大，单张处理最稳。
    *   **搜索时**: 向量检索是毫秒级的，主要瓶颈在网络传输。
3.  **显存溢出保护 (OOM Protection)**:
    *   设置显存监控阈值 (e.g., 90%)。
    *   如果检测到显存危险，自动触发 `torch.cuda.empty_cache()` 或暂时卸载 YOLO。

---

## 6. 开发阶段规划 (Phases)

*   **Phase 1: 引擎验证** (在 Windows 上跑通 MiniCPM-V Int4 和 YOLOv8 的 Python Demo)。
*   **Phase 2: 后端集成** (编写 `processors.py`，改造 `indexer.py` 和数据库 Schema)。
*   **Phase 3: API 升级** (暴露 OCR 和 Object 数据给前端)。
*   **Phase 4: 前端 Pro UI** (实现 Modal、Canvas 画框、OCR 展示)。
