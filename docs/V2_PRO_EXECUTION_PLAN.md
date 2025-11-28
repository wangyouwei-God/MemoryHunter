# MemoryHunter V2.0 Pro - AI Agent Execution Plan

> **Target Audience**: AI Coding Agent
> **Goal**: Upgrade MemoryHunter to V2.0 Pro with VLM & Object Detection capabilities.
> **Constraint**: Preserve existing UI style (Glassmorphism) strictly. Use ChromaDB. Optimize for RTX 4080 (12G).

---

##  Phase 1: Environment & Dependencies (Windows/WSL2)

**Objective**: Prepare the Python environment for heavy AI models.

### 1.1 Update `requirements.txt`
Add the following dependencies. **Do not remove existing ones.**
```text
# Core AI
torch>=2.1.0 --index-url https://download.pytorch.org/whl/cu121
torchvision>=0.16.0 --index-url https://download.pytorch.org/whl/cu121
transformers>=4.37.0
accelerate>=0.26.0
bitsandbytes>=0.41.0  # Critical for Int4 quantization
timm>=0.9.10

# Models
ultralytics>=8.1.0    # YOLOv8
sentence-transformers>=2.3.0

# VLM Specific (MiniCPM-V)
decord
Pillow>=10.0.0
```

### 1.2 Dockerfile Adjustment (Optional but Recommended)
If building for Docker, ensure base image is `nvidia/cuda:12.1.0-runtime-ubuntu22.04`.

---

## Phase 2: Backend Core - Model Engine (`backend/processors.py`)

**Objective**: Create a new module to handle VLM and YOLO inference. Isolate this from `main.py` to keep code clean.

### 2.1 Create `backend/processors.py`
Implement a `GlobalAIProcessor` class using the **Singleton Pattern** to manage VRAM usage.

**Key Methods**:
1.  `__init__`:
    *   Load **YOLOv8-X** (`yolov8x.pt`) to GPU.
    *   Load **MiniCPM-V 2.5 Int4** (`openbmb/MiniCPM-V-2_5-int4`) to GPU using `AutoModel.from_pretrained(..., trust_remote_code=True)`.
    *   *Note*: Ensure `torch_dtype=torch.float16` for VLM.
2.  `process_image(image_path)`:
    *   **Step A (YOLO)**: Run inference. Filter results with `conf > 0.3`.
        *   Return: `objects` list `[{label, box, score}]`.
    *   **Step B (VLM)**:
        *   Prompt: *"Analyze this image in detail. Describe the scene, objects, actions, and atmosphere. If there is text, transcribe it exactly."*
        *   Run inference.
        *   Return: `caption` (string) and `ocr_text` (extracted from caption or separate prompt).
    *   **Return**: A dict `{ "objects": [...], "caption": "...", "ocr_text": "..." }`.

---

## Phase 3: Indexing Logic Upgrade (`backend/indexer.py`)

**Objective**: Integrate the new processor into the indexing loop.

### 3.1 Modify `ImageIndexer.index_images`
1.  Initialize `GlobalAIProcessor` at the start.
2.  Inside the loop (for each image):
    *   **Existing**: Compute CLIP vector.
    *   **New**: Call `GlobalAIProcessor.process_image(path)`.
    *   **New**: Compute **Semantic Vector** for the `caption` using `sentence-transformers` (BGE-M3).
3.  **Data Structure Merging**:
    *   Combine visual vector and semantic vector (concatenation or separate storage? -> **Recommendation: Separate Collections**).
    *   **Decision**: Use **Two Collections** in ChromaDB.
        *   `visual_collection`: Stores CLIP vectors. Metadata: `{path, timestamp}`.
        *   `semantic_collection`: Stores BGE vectors of captions. Metadata: `{path, caption, ocr_text, objects_json}`.

---

## Phase 4: Search Logic Upgrade (`backend/searcher.py`)

**Objective**: Implement Hybrid Search (RRF).

### 4.1 Modify `ImageSearcher.search`
1.  Accept `query_text`.
2.  **Route A (Visual)**: Search `visual_collection` with CLIP text embedding. Get Top 50.
3.  **Route B (Semantic)**: Search `semantic_collection` with BGE text embedding. Get Top 50.
4.  **Fusion (RRF)**:
    *   Combine results based on rank: `score = 1/(60+rank_A) + 1/(60+rank_B)`.
5.  **Return**: Top K results.
    *   **Crucial**: The returned JSON object **MUST** include `caption`, `ocr_text`, and `objects` for the frontend to display.

---

## Phase 5: Frontend Upgrade (The "Omni-Modal")

**Objective**: Add detailed view without breaking existing UI.

### 5.1 HTML (`frontend/index.html`)
Add a hidden Modal structure at the end of `<body>`. **Do not touch existing grid/header.**

```html
<!-- Glassmorphism Modal -->
<div id="detailModal" class="modal-overlay hidden">
    <div class="modal-content glass-panel">
        <button class="close-btn">&times;</button>
        
        <div class="modal-body">
            <!-- Left: Image Canvas -->
            <div class="image-container">
                <canvas id="imageCanvas"></canvas>
            </div>
            
            <!-- Right: Info Panel -->
            <div class="info-panel">
                <!-- Tabs -->
                <div class="tabs">
                    <button class="tab-btn active" data-tab="ai-desc">AI Analysis</button>
                    <button class="tab-btn" data-tab="ocr">Text (OCR)</button>
                </div>
                
                <!-- Tab Content -->
                <div id="ai-desc" class="tab-content active">
                    <p id="captionText" class="typing-effect"></p>
                    <div id="objectTags" class="tags-cloud"></div>
                </div>
                
                <div id="ocr" class="tab-content">
                    <textarea id="ocrResult" readonly></textarea>
                    <button id="copyOcrBtn" class="action-btn">Copy Text</button>
                </div>
            </div>
        </div>
    </div>
</div>
```

### 5.2 CSS (`frontend/style.css`)
Add styles for `.modal-overlay`, `.modal-content`, `.glass-panel`.
*   Use `backdrop-filter: blur(20px)` for the glass effect.
*   Ensure `z-index` is higher than everything else.
*   Style the `canvas` to be responsive.

### 5.3 JS (`frontend/app.js`)
1.  **Event Listener**: Add click event to `.result-card`.
2.  **Open Modal**:
    *   Fetch image details (caption, objects, OCR) from backend (if not already in search results).
    *   Draw image on `<canvas>`.
    *   **Interaction**:
        *   Render object tags in the right panel.
        *   Add `mouseenter` event to tags: Clear canvas -> Draw Image -> Draw **Red Box** for that specific object.
        *   Add `mouseleave`: Redraw clean image.
3.  **OCR Tab**: Fill textarea with `ocr_text`.

---

## 6. Verification Checklist

- [ ] **Environment**: `import torch; print(torch.cuda.is_available())` returns True.
- [ ] **VLM**: MiniCPM-V 2.5 Int4 loads without OOM.
- [ ] **Indexing**: Process 10 images. Check ChromaDB for `caption` and `objects` metadata.
- [ ] **Search**: Search for a specific object (e.g., "red cup") -> Result found via semantic path.
- [ ] **UI**: Click image -> Modal opens -> Hover "cup" tag -> Red box appears on cup.
- [ ] **Style**: Modal matches the existing "Lite Edition" aesthetic perfectly.
