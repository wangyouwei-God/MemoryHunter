// ============ Phase 6: 系统维护功能 ============

/**
 * 系统维护面板
 */
class MaintenanceManager {
    constructor() {
        this.createPanel();
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'maintenancePanel';
        panel.className = 'management-panel';
        panel.style.display = 'none';

        panel.innerHTML = `
            <div class="panel-header">
                <h3>🔧 系统维护</h3>
                <button class="btn-icon" onclick="maintenanceManager.close()">✕</button>
            </div>
            
            <div class="panel-content">
                <!-- 健康检查部分 -->
                <div class="maintenance-section">
                    <h4>🏥 数据库健康检查</h4>
                    <p class="section-desc">检查数据库中是否存在已删除文件的记录</p>
                    
                    <div id="healthCheckResults" class="health-results" style="display: none;">
                        <!-- 动态填充 -->
                    </div>
                    
                    <button class="btn btn-primary" onclick="maintenanceManager.runHealthCheck()">
                        运行健康检查
                    </button>
                </div>
                
                <!-- 清理部分 -->
                <div class="maintenance-section">
                    <h4>🧹 数据库清理</h4>
                    <p class="section-desc">清理已删除文件的向量记录</p>
                    
                    <div id="cleanupResults" class="cleanup-results" style="display: none;">
                        <!-- 动态填充 -->
                    </div>
                    
                    <div class="button-group">
                        <button class="btn btn-secondary" onclick="maintenanceManager.previewCleanup()">
                            📋 预览清理
                        </button>
                        <button class="btn btn-danger" onclick="maintenanceManager.autoCleanup()">
                            🗑️ 自动清理
                        </button>
                    </div>
                </div>
                
                <!-- 优化部分 -->
                <div class="maintenance-section">
                    <h4>⚡ 数据库优化</h4>
                    <p class="section-desc">自动执行健康检查和清理（后台任务）</p>
                    
                    <button class="btn btn-primary" onclick="maintenanceManager.optimize()">
                        开始优化
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
        this.panel = panel;
    }

    open() {
        this.panel.style.display = 'block';
        this.loadStats();
    }

    close() {
        this.panel.style.display = 'none';
    }

    async loadStats() {
        try {
            const response = await fetch(`${API_BASE}/api/maintenance/stats`);
            if (!response.ok) throw new Error('获取统计失败');

            const stats = await response.json();
            console.log('维护统计:', stats);

        } catch (error) {
            console.error('加载统计失败:', error);
        }
    }

    async runHealthCheck() {
        const resultsDiv = document.getElementById('healthCheckResults');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="loading-spinner"></div><p>正在检查...</p>';

        try {
            const response = await fetch(`${API_BASE}/api/maintenance/health-check`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('健康检查失败');

            const result = await response.json();

            // 渲染结果
            const deletionRateClass = result.deletion_rate > 20 ? 'danger' :
                result.deletion_rate > 5 ? 'warning' : 'success';

            resultsDiv.innerHTML = `
                <div class="health-report">
                    <div class="health-stats">
                        <div class="stat-box">
                            <div class="stat-number">${result.total_records}</div>
                            <div class="stat-label">总记录数</div>
                        </div>
                        <div class="stat-box success">
                            <div class="stat-number">${result.valid_files}</div>
                            <div class="stat-label">有效文件</div>
                        </div>
                        <div class="stat-box ${deletionRateClass}">
                            <div class="stat-number">${result.deleted_files}</div>
                            <div class="stat-label">已删除文件</div>
                        </div>
                        <div class="stat-box ${deletionRateClass}">
                            <div class="stat-number">${result.deletion_rate}%</div>
                            <div class="stat-label">删除率</div>
                        </div>
                    </div>
                    
                    <div class="health-recommendations">
                        <h5>📌 建议</h5>
                        <ul>
                            ${result.recommendations.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;

            showNotification('✅ 健康检查完成', 'success');

        } catch (error) {
            console.error('健康检查失败:', error);
            resultsDiv.innerHTML = `<p class="error-message">❌ 检查失败: ${error.message}</p>`;
            showNotification(`检查失败: ${error.message}`, 'error');
        }
    }

    async previewCleanup() {
        const resultsDiv = document.getElementById('cleanupResults');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="loading-spinner"></div><p>正在分析...</p>';

        try {
            const response = await fetch(`${API_BASE}/api/maintenance/cleanup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_remove: false })
            });

            if (!response.ok) throw new Error('预览失败');

            const result = await response.json();

            if (result.found === 0) {
                resultsDiv.innerHTML = `
                    <div class="info-message">
                        ✅ 数据库健康，没有需要清理的记录
                    </div>
                `;
                return;
            }

            resultsDiv.innerHTML = `
                <div class="cleanup-preview">
                    <div class="preview-header">
                        <strong>发现 ${result.found} 个已删除文件的记录：</strong>
                    </div>
                    <div class="preview-list">
                        ${result.deleted_files.slice(0, 10).map(file => `
                            <div class="preview-item">
                                <span class="file-icon">🗑️</span>
                                <span class="file-name">${file.filename}</span>
                                <span class="file-path-small">${file.path}</span>
                            </div>
                        `).join('')}
                        ${result.found > 10 ? `<div class="preview-more">...还有 ${result.found - 10} 个文件</div>` : ''}
                    </div>
                </div>
            `;

            showNotification(`📋 发现 ${result.found} 个可清理记录`, 'info');

        } catch (error) {
            console.error('预览失败:', error);
            result.innerHTML = `<p class="error-message">❌ 预览失败: ${error.message}</p>`;
            showNotification(`预览失败: ${error.message}`, 'error');
        }
    }

    async autoCleanup() {
        if (!confirm('确定要清理所有已删除文件的记录吗？此操作不可撤销。')) {
            return;
        }

        const resultsDiv = document.getElementById('cleanupResults');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="loading-spinner"></div><p>正在清理...</p>';

        try {
            const response = await fetch(`${API_BASE}/api/maintenance/cleanup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_remove: true })
            });

            if (!response.ok) throw new Error('清理失败');

            const result = await response.json();

            resultsDiv.innerHTML = `
                <div class="success-message">
                    ✅ 清理完成！已删除 ${result.cleaned} 条记录
                </div>
            `;

            showNotification(`✅ 已清理 ${result.cleaned} 条记录`, 'success');

            // 刷新统计
            loadStats();

        } catch (error) {
            console.error('清理失败:', error);
            resultsDiv.innerHTML = `<p class="error-message">❌ 清理失败: ${error.message}</p>`;
            showNotification(`清理失败: ${error.message}`, 'error');
        }
    }

    async optimize() {
        if (!confirm('确定要开始数据库优化吗？这将在后台执行。')) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/maintenance/optimize`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('优化失败');

            const result = await response.json();
            showNotification(`✅ ${result.message}`, 'success');

        } catch (error) {
            console.error('优化失败:', error);
            showNotification(`优化失败: ${error.message}`, 'error');
        }
    }
}

// 初始化维护管理器
const maintenanceManager = new MaintenanceManager();

// 导出到全局
window.maintenanceManager = maintenanceManager;
