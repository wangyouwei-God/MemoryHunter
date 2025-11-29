// ============ API 配置 ============
const API_BASE = '';  // 相对路径，自动使用当前域名

// ============ DOM 元素 ============
const elements = {
    // 统计信息
    totalImages: document.getElementById('totalImages'),
    indexStatus: document.getElementById('indexStatus'),

    // 索引控制
    indexBtn: document.getElementById('indexBtn'),
    indexBtnText: document.getElementById('indexBtnText'),
    indexProgress: document.getElementById('indexProgress'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText'),

    // 搜索
    searchForm: document.getElementById('searchForm'),
    queryInput: document.getElementById('queryInput'),
    topK: document.getElementById('topK'),
    topKValue: document.getElementById('topKValue'),
    threshold: document.getElementById('threshold'),
    thresholdValue: document.getElementById('thresholdValue'),

    // 结果展示
    resultsSection: document.getElementById('resultsSection'),
    resultsCount: document.getElementById('resultsCount'),
    resultsGrid: document.getElementById('resultsGrid'),

    // 加载动画
    loadingOverlay: document.getElementById('loadingOverlay')
};

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 MemoryHunter 前端已加载');

    // 加载统计信息
    loadStats();

    // 定期刷新统计
    setInterval(loadStats, 5000);

    // 监听滑块变化
    elements.topK.addEventListener('input', (e) => {
        elements.topKValue.textContent = e.target.value;
    });

    elements.threshold.addEventListener('input', (e) => {
        elements.thresholdValue.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // 监听索引按钮
    elements.indexBtn.addEventListener('click', handleIndex);

    // 监听搜索表单
    elements.searchForm.addEventListener('submit', handleSearch);
});

// ============ API 调用 ============

/**
 * 加载统计信息
 */
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const data = await response.json();

        // 更新统计数字和仪表盘动画
        const totalImages = data.total_images;
        elements.totalImages.textContent = totalImages;

        // 更新仪表盘进度 (假设最大值500张图片，可调整)
        updateGauge(totalImages, 500);

        // 更新索引状态
        if (data.indexing_status.is_indexing) {
            elements.indexStatus.textContent = i18n.t('indexingNow');
            elements.indexStatus.classList.add('status-indexing');

            // 显示进度
            showProgress(
                data.indexing_status.progress,
                data.indexing_status.total
            );
        } else {
            elements.indexStatus.textContent = i18n.t('systemStatus');
            elements.indexStatus.classList.remove('status-indexing');
            hideProgress();
        }

    } catch (error) {
        console.error('加载统计信息失败:', error);
        elements.indexStatus.textContent = i18n.t('connectionFailed');
        elements.indexStatus.classList.add('status-error');
    }
}

/**
 * 更新仪表盘进度
 */
function updateGauge(current, max) {
    const gaugeProgress = document.getElementById('gaugeProgress');
    if (!gaugeProgress) return;

    // 计算百分比 (0-1)
    const percentage = Math.min(current / max, 1);

    // 弧线总长度 (半圆周长的一半)
    const totalLength = 251.2;

    // 计算 stroke-dashoffset (从右往左填充)
    const offset = totalLength * (1 - percentage);

    gaugeProgress.style.strokeDashoffset = offset;
}

/**
 * 触发索引
 */
async function handleIndex() {
    try {
        elements.indexBtn.disabled = true;
        elements.indexBtnText.textContent = i18n.t('startingIndex');

        const response = await fetch(`${API_BASE}/api/index`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail);
        }

        const data = await response.json();

        // 显示成功消息
        showNotification(i18n.t('indexTaskStarted'), 'success');

        // 开始轮询状态
        pollIndexStatus();

    } catch (error) {
        console.error('启动索引失败:', error);
        showNotification(`索引启动失败: ${error.message}`, 'error');
        elements.indexBtn.disabled = false;
        elements.indexBtnText.textContent = i18n.t('startIndex');
    }
}

/**
 * 轮询索引状态
 */
function pollIndexStatus() {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/index/status`);
            const status = await response.json();

            if (status.is_indexing) {
                showProgress(status.progress, status.total);
                elements.indexBtnText.textContent = i18n.t("indexingProgress", { current: status.progress, total: status.total });
            } else {
                clearInterval(interval);
                hideProgress();
                elements.indexBtn.disabled = false;
                elements.indexBtnText.textContent = i18n.t('startIndex');

                // 刷新统计
                loadStats();
            }
        } catch (error) {
            console.error('获取索引状态失败:', error);
            clearInterval(interval);
            elements.indexBtn.disabled = false;
            elements.indexBtnText.textContent = i18n.t('startIndex');
        }
    }, 1000);
}

/**
 * 处理搜索
 */
async function handleSearch(e) {
    e.preventDefault();

    const query = elements.queryInput.value.trim();
    if (!query) {
        showNotification(i18n.t('pleaseEnterSearch'), 'warning');
        return;
    }

    const topK = parseInt(elements.topK.value);
    const threshold = parseFloat(elements.threshold.value);

    try {
        // 显示加载动画
        elements.loadingOverlay.style.display = 'flex';

        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: topK,
                threshold: threshold
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail);
        }

        const data = await response.json();

        // 显示结果
        displayResults(data);

    } catch (error) {
        console.error('搜索失败:', error);
        showNotification(`搜索失败: ${error.message}`, 'error');
    } finally {
        // 隐藏加载动画
        elements.loadingOverlay.style.display = 'none';
    }
}

/**
 * 显示搜索结果
 */
function displayResults(data) {
    const { query, results, count } = data;

    // 显示结果区域
    elements.resultsSection.style.display = 'block';

    // 更新结果计数
    elements.resultsCount.textContent = `找到 ${count} 个相关结果，查询: "${query}"`;

    // 清空之前的结果
    elements.resultsGrid.innerHTML = '';

    if (count === 0) {
        elements.resultsGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
                <p style="font-size: 3rem; margin-bottom: 1rem;">🔍</p>
                <p style="font-size: 1.2rem;">${i18n.t('noResults')}</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem;">${i18n.t('tryOtherKeywords')}</p>
            </div>
        `;
        return;
    }

    // 渲染结果卡片
    results.forEach((result, index) => {
        const card = createResultCard(result, index);
        elements.resultsGrid.appendChild(card);
    });

    // 滚动到结果区域
    elements.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * 创建结果卡片
 */
function createResultCard(result, index) {
    const card = document.createElement('div');
    card.className = 'result-card';

    // 构建图片路径（相对于 /app/photos 的路径）
    const imagePath = result.path.replace('/app/photos/', '');
    const imageUrl = `/photos/${imagePath}`;

    card.innerHTML = `
        <img 
            src="${imageUrl}" 
            alt="${result.filename}" 
            class="result-image"
            loading="lazy"
            onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22280%22 height=%22220%22%3E%3Crect fill=%22%231e293b%22 width=%22280%22 height=%22220%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%2394a3b8%22 font-family=%22sans-serif%22%3E${i18n.t('imageLoadFailed')}%3C/text%3E%3C/svg%3E'"
        >
        <div class="result-info">
            <div class="result-score">${i18n.t('similarity')}: ${(result.score * 100).toFixed(1)}%</div>
            <div class="result-filename" title="${result.filename}">${result.filename}</div>
        </div>
    `;

    // 添加点击功能 - Pro模式优先打开Modal
    card.addEventListener('click', () => {
        // 检查是否有Pro元数据 (objects or ocr_text)
        const hasProData = (result.objects && result.objects !== '[]') || result.ocr_text;

        if (hasProData && typeof window.openProModal === 'function') {
            // Pro模式: 打开Modal显示详情
            window.openProModal({
                path: imageUrl,
                filename: result.filename,
                objects: result.objects || '[]',
                ocr_text: result.ocr_text || ''
            });
        } else {
            // V1.0 兼容: 新标签页打开图片
            window.open(imageUrl, '_blank');
        }
    });

    // 添加入场动画
    card.style.animation = `fadeIn 0.5s ease ${index * 0.05}s both`;

    return card;
}

// ============ UI 辅助函数 ============

/**
 * 显示进度条
 */
function showProgress(current, total) {
    elements.indexProgress.style.display = 'block';

    const percentage = total > 0 ? (current / total) * 100 : 0;
    elements.progressFill.style.width = `${percentage}%`;
    elements.progressText.textContent = `${current} / ${total}`;
}

/**
 * 隐藏进度条
 */
function hideProgress() {
    elements.indexProgress.style.display = 'none';
    elements.progressFill.style.width = '0%';
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    const colors = {
        success: 'var(--success)',
        error: 'var(--danger)',
        warning: 'var(--warning)',
        info: 'var(--primary)'
    };

    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: ${colors[type]};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============ CSS 动画 ============
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============ Folder Management Drawer (Commented out - Feature postponed) ============
/*
(function initFolderDrawer() {
    const settingsBtn = document.getElementById('settingsBtn');
    const folderDrawer = document.getElementById('folderDrawer');
    const drawerOverlay = document.getElementById('drawerOverlay');
    const drawerClose = document.getElementById('drawerClose');
    const folderList = document.getElementById('folderList');
    const folderLoading = document.getElementById('folderLoading');
    const folderEmpty = document.getElementById('folderEmpty');
    const folderCount = document.getElementById('folderCount');

    // New: Action buttons
    const selectAllBtn = document.getElementById('selectAllBtn');
    const refreshListBtn = document.getElementById('refreshListBtn');
    const startIndexBtn = document.getElementById('startIndexBtn');
    const selectedCount = document.getElementById('selectedCount');

    let foldersData = [];  // Store loaded folders
    let selectedFolders = new Set();  // Track selected folder paths

    // Open drawer and load folders
    if (settingsBtn) {
        settingsBtn.addEventListener('click', async () => {
            folderDrawer.classList.add('active');
            document.body.style.overflow = 'hidden';

            // Auto-load folders when drawer opens
            await loadFolders();
        });
    }

    // Close drawer
    function closeDrawer() {
        folderDrawer.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (drawerOverlay) {
        drawerOverlay.addEventListener('click', closeDrawer);
    }

    if (drawerClose) {
        drawerClose.addEventListener('click', closeDrawer);
    }

    // ESC to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && folderDrawer.classList.contains('active')) {
            closeDrawer();
        }
    });

    // Load folders from API
    async function loadFolders() {
        try {
            // Show loading state
            folderLoading.style.display = 'flex';
            folderList.style.display = 'none';
            folderEmpty.style.display = 'none';

            const response = await fetch('/api/folders');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const folders = await response.json();
            foldersData = folders;

            // Hide loading
            folderLoading.style.display = 'none';

            if (folders.length === 0) {
                // Show empty state
                folderEmpty.style.display = 'flex';
                folderList.style.display = 'none';
            } else {
                // Render folder cards with checkboxes
                renderFolders(folders);
                folderList.style.display = 'block';
                folderEmpty.style.display = 'none';

                // Update folder count
                folderCount.textContent = i18n.t('folderCountText', { count: folders.length });

                // Default: select all
                selectAll();
            }

        } catch (error) {
            console.error('Failed to load folders:', error);
            folderLoading.style.display = 'none';
            folderEmpty.style.display = 'flex';

            // Show error in empty state
            const emptyText = folderEmpty.querySelector('p');
            if (emptyText) {
                emptyText.textContent = '⚠️ ' + (i18n.t('connectionFailed') || '加载失败');
            }
        }
    }

    // Render folder cards with checkboxes
    function renderFolders(folders) {
        folderList.innerHTML = '';

        folders.forEach((folder, index) => {
            const card = createFolderCardWithCheckbox(folder, index);
            folderList.appendChild(card);
        });
    }

    // Create folder card with checkbox
    function createFolderCardWithCheckbox(folder, index) {
        const card = document.createElement('div');
        card.className = 'folder-card';
        card.dataset.folderPath = folder.path;

        const isSelected = selectedFolders.has(folder.path);

        card.innerHTML = `
            <label class="folder-checkbox-wrapper">
                <input type="checkbox" class="folder-checkbox" data-path="${folder.path}" ${isSelected ? 'checked' : ''}>
                <span class="checkbox-custom"></span>
            </label>

            <div class="folder-card-icon">
                <svg viewBox="0 0 24 24" fill="none">
                    <path d="M3 7V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V9C21 7.89543 20.1046 7 19 7H13L11 5H5C3.89543 5 3 5.89543 3 7Z" stroke="url(#folderGradient${index})" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <defs>
                        <linearGradient id="folderGradient${index}" x1="3" y1="5" x2="21" y2="19" gradientUnits="userSpaceOnUse">
                            <stop stop-color="#667eea" />
                            <stop offset="1" stop-color="#f093fb" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <div class="folder-card-info">
                <div class="folder-path">${path}</div>
                <div class="folder-stats">
                    <span class="stat-item">
                        <svg viewBox="0 0 24 24" fill="none">
                            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
                            <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor"/>
                            <path d="M21 15L16 10L5 21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        ${imageCount} ${i18n.t('images')}
                    </span>
                    <span class="stat-item" style="color: #888;">
                        <svg viewBox="0 0 24 24" fill="none">
                            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                            <path d="M12 6V12L16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                        ${i18n.t('notIndexedYet')}
                    </span>
                </div>
            </div>
            <button class="folder-remove-btn" data-folder-id="${id}" title="${i18n.t('removeFolderTitle')}">
                <svg viewBox="0 0 24 24" fill="none">
                    <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
        `;
        return card;
    }

    // Slide out animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideOutRight {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(20px);
            }
        }
    `;
    document.head.appendChild(style);

    // Initialize remove button handlers
    setupRemoveButtons();

    // Initialize folder count display
    updateFolderCount();

    // Update folder count when language changes
    window.addEventListener('languageChanged', updateFolderCount);

    function updateFolderCount() {
        const currentCount = folderList.querySelectorAll('.folder-card').length;
        folderCount.textContent = i18n.t('folderCountText', { count: currentCount });
    }

    console.log('✅ Folder drawer initialized');
})();
*/

// ============================================
// PRO DETAIL MODAL (V2.0) - Canvas & OCR
// ============================================

(function initProModal() {
    const modal = document.getElementById('proDetailModal');
    const closeBtn = document.getElementById('closeProModal');
    const canvas = document.getElementById('proImageCanvas');
    const ctx = canvas.getContext('2d');

    const tabs = document.querySelectorAll('.pro-tab');
    const tabContents = document.querySelectorAll('.pro-tab-content');

    const objectTagsContainer = document.getElementById('proObjectTags');
    const ocrTextarea = document.getElementById('proOcrText');
    const copyOcrBtn = document.getElementById('proCopyOcr');

    let currentImage = null;
    let currentObjects = [];
    let highlightedObject = null;

    // Tab Switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            // Update tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update content
            tabContents.forEach(content => {
                if (content.id === `tab-${targetTab}`) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
        });
    });

    // Close Modal
    function closeModal() {
        modal.classList.add('hidden');
        currentImage = null;
        currentObjects = [];
        highlightedObject = null;
    }

    closeBtn.addEventListener('click', closeModal);
    modal.querySelector('.pro-modal-overlay').addEventListener('click', closeModal);

    // Open Modal with Image Data
    window.openProModal = function (imageData) {
        const { path, filename, objects, ocr_text } = imageData;

        // Load and draw image
        const img = new Image();
        img.onload = function () {
            // Set canvas size to image size
            canvas.width = img.width;
            canvas.height = img.height;

            // Draw image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);

            currentImage = img;
        };
        img.src = path.startsWith('http') ? path : `/photos/${path.split('/photos/')[1] || path}`;

        // Parse and display objects (with error handling)
        try {
            currentObjects = typeof objects === 'string' ? JSON.parse(objects) : (objects || []);
            renderObjectTags(currentObjects);
        } catch (e) {
            console.error('Failed to parse objects JSON:', e, 'Raw data:', objects);
            currentObjects = [];
            renderObjectTags([]);
        }

        // Display OCR text
        ocrTextarea.value = ocr_text || '';

        // Show modal
        modal.classList.remove('hidden');
    };

    // Render Object Tags
    function renderObjectTags(objects) {
        if (!objects || objects.length === 0) {
            objectTagsContainer.innerHTML = `
                <div class="pro-empty-state">
                    <svg viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                        <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                    <p>No objects detected</p>
                </div>
            `;
            return;
        }

        objectTagsContainer.innerHTML = objects.map((obj, index) => `
            <div class="pro-object-tag" data-obj-index="${index}">
                <svg viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
                </svg>
                ${obj.label} (${(obj.score * 100).toFixed(0)}%)
            </div>
        `).join('');

        // Add hover listeners
        document.querySelectorAll('.pro-object-tag').forEach(tag => {
            tag.addEventListener('mouseenter', function () {
                const objIndex = parseInt(this.dataset.objIndex);
                highlightObject(objIndex);
                this.classList.add('highlighted');
            });

            tag.addEventListener('mouseleave', function () {
                clearHighlight();
                this.classList.remove('highlighted');
            });
        });
    }

    // Highlight Object on Canvas
    function highlightObject(objIndex) {
        if (!currentImage || !currentObjects[objIndex]) return;

        highlightedObject = currentObjects[objIndex];

        // Redraw image
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(currentImage, 0, 0);

        // Draw bounding box
        const box = highlightedObject.box;
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 4;
        ctx.shadowColor = '#EF4444';
        ctx.shadowBlur = 15;
        ctx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);

        // Reset shadow
        ctx.shadowBlur = 0;

        // Draw label
        ctx.fillStyle = '#EF4444';
        ctx.font = 'bold 16px Inter';
        const labelText = `${highlightedObject.label} ${(highlightedObject.score * 100).toFixed(0)}%`;
        const textWidth = ctx.measureText(labelText).width;

        ctx.fillRect(box[0], box[1] - 25, textWidth + 16, 25);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText(labelText, box[0] + 8, box[1] - 7);
    }

    // Clear Highlight
    function clearHighlight() {
        if (!currentImage) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(currentImage, 0, 0);
        highlightedObject = null;
    }

    // Copy OCR Text
    copyOcrBtn.addEventListener('click', async () => {
        const text = ocrTextarea.value;

        if (!text) {
            showNotification(i18n.t ? i18n.t('noTextToCopy') : 'No text to copy', 'warning');
            return;
        }

        try {
            await navigator.clipboard.writeText(text);
            showNotification(i18n.t ? i18n.t('textCopied') : 'Text copied to clipboard', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            showNotification(i18n.t ? i18n.t('copyFailed') : 'Failed to copy', 'error');
        }
    });

    console.log('✅ Pro Detail Modal initialized');
})();

// Add ESC key to close Modal (UX improvement)
document.addEventListener('keydown', function (e) {
    const modal = document.getElementById('proDetailModal');
    if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
        const closeBtn = document.getElementById('closeProModal');
        if (closeBtn) closeBtn.click();
    }
});
