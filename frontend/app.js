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

        // 更新统计数字
        elements.totalImages.textContent = data.total_images;

        // 更新索引状态
        if (data.indexing_status.is_indexing) {
            elements.indexStatus.textContent = '索引中...';
            elements.indexStatus.style.color = 'var(--warning)';

            // 显示进度
            showProgress(
                data.indexing_status.progress,
                data.indexing_status.total
            );
        } else {
            elements.indexStatus.textContent = data.indexing_status.message || '就绪';
            elements.indexStatus.style.color = 'var(--success)';
            hideProgress();
        }

    } catch (error) {
        console.error('加载统计信息失败:', error);
        elements.indexStatus.textContent = '连接失败';
        elements.indexStatus.style.color = 'var(--danger)';
    }
}

/**
 * 触发索引
 */
async function handleIndex() {
    try {
        elements.indexBtn.disabled = true;
        elements.indexBtnText.textContent = '⏳ 正在启动索引...';

        const response = await fetch(`${API_BASE}/api/index`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail);
        }

        const data = await response.json();

        // 显示成功消息
        showNotification('索引任务已启动，将在后台执行', 'success');

        // 开始轮询状态
        pollIndexStatus();

    } catch (error) {
        console.error('启动索引失败:', error);
        showNotification(`索引启动失败: ${error.message}`, 'error');
        elements.indexBtn.disabled = false;
        elements.indexBtnText.textContent = '🔄 开始索引';
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
                elements.indexBtnText.textContent = `⏳ 索引中 ${status.progress}/${status.total}`;
            } else {
                clearInterval(interval);
                hideProgress();
                elements.indexBtn.disabled = false;
                elements.indexBtnText.textContent = '🔄 开始索引';

                // 刷新统计
                loadStats();
            }
        } catch (error) {
            console.error('获取索引状态失败:', error);
            clearInterval(interval);
            elements.indexBtn.disabled = false;
            elements.indexBtnText.textContent = '🔄 开始索引';
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
        showNotification('请输入搜索内容', 'warning');
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
                <p style="font-size: 1.2rem;">未找到相关图片</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem;">试试其他搜索词或降低相似度阈值</p>
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
            onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22280%22 height=%22220%22%3E%3Crect fill=%22%231e293b%22 width=%22280%22 height=%22220%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%2394a3b8%22 font-family=%22sans-serif%22%3E图片加载失败%3C/text%3E%3C/svg%3E'"
        >
        <div class="result-info">
            <div class="result-score">相似度: ${(result.score * 100).toFixed(1)}%</div>
            <div class="result-filename" title="${result.filename}">${result.filename}</div>
        </div>
    `;

    // 添加点击放大功能
    card.addEventListener('click', () => {
        window.open(imageUrl, '_blank');
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
