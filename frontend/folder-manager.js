// ============ Phase 6: 文件夹管理功能 ============

/**
 * 文件夹浏览器对话框
 */
class FolderBrowser {
    constructor() {
        this.currentPath = null;
        this.createDialog();
    }

    createDialog() {
        const dialog = document.createElement('div');
        dialog.id = 'folderBrowserDialog';
        dialog.className = 'modal-overlay';
        dialog.style.display = 'none';

        dialog.innerHTML = `
            <div class="modal-content folder-browser">
                <div class="modal-header">
                    <h2>📁 选择文件夹</h2>
                    <button class="modal-close" onclick="folderBrowser.close()">✕</button>
                </div>
                
                <div class="breadcrumb" id="folderBreadcrumb">
                    <button class="breadcrumb-item" onclick="folderBrowser.browse(null)">
                        💻 此电脑
                    </button>
                </div>
                
                <div class="folder-list" id="folderList">
                    <div class="loading-spinner"></div>
                    <p>正在加载...</p>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="folderBrowser.close()">取消</button>
                    <button class="btn btn-primary" id="confirmFolderBtn" onclick="folderBrowser.confirm()" disabled>
                        确定选择
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);
        this.dialog = dialog;
    }

    async open() {
        this.dialog.style.display = 'flex';
        await this.browse(null); // 浏览根目录
    }

    close() {
        this.dialog.style.display = 'none';
        this.currentPath = null;
    }

    async browse(path) {
        const folderList = document.getElementById('folderList');
        folderList.innerHTML = '<div class="loading-spinner"></div><p>正在加载...</p>';

        try {
            const url = path ? `${API_BASE}/api/folders/browse?path=${encodeURIComponent(path)}` : `${API_BASE}/api/folders/browse`;
            const response = await fetch(url);

            if (!response.ok) throw new Error('获取文件夹列表失败');

            const data = await response.json();
            this.currentPath = data.current_path;

            // 更新面包屑
            this.updateBreadcrumb(data);

            // 渲染文件夹列表
            this.renderFolders(data.folders);

        } catch (error) {
            console.error('浏览文件夹失败:', error);
            folderList.innerHTML = `<p class="error-message">❌ 加载失败: ${error.message}</p>`;
        }
    }

    updateBreadcrumb(data) {
        const breadcrumb = document.getElementById('folderBreadcrumb');
        let html = '<button class="breadcrumb-item" onclick="folderBrowser.browse(null)">💻 此电脑</button>';

        if (data.current_path) {
            const separator = '<span class="breadcrumb-separator">›</span>';
            html += separator;
            html += `<button class="breadcrumb-item active">${data.current_path}</button>`;
        }

        breadcrumb.innerHTML = html;
    }

    renderFolders(folders) {
        const folderList = document.getElementById('folderList');

        if (folders.length === 0) {
            folderList.innerHTML = '<p class="empty-message">此文件夹为空或无权访问</p>';
            return;
        }

        folderList.innerHTML = folders.map(folder => {
            const icon = folder.accessible === false ? '🔒' : '📁';
            const imageCountText = folder.image_count > 0 ? `${folder.image_count} 张图片` : '无图片';
            const disabled = folder.accessible === false ? 'disabled' : '';

            return `
                <div class="folder-item ${disabled}" onclick="folderBrowser.browse('${folder.path.replace(/'/g, "\\'")}')">
                    <div class="folder-icon">${icon}</div>
                    <div class="folder-details">
                        <div class="folder-name">${folder.name}</div>
                        <div class="folder-meta">${imageCountText}</div>
                    </div>
                    <div class="folder-actions">
                        <button class="btn-icon" onclick="event.stopPropagation(); folderBrowser.selectFolder('${folder.path.replace(/'/g, "\\'")}', '${folder.name.replace(/'/g, "\\'")}')">
                            ✓ 选择
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    selectFolder(path, name) {
        this.currentPath = path;
        this.currentName = name || path.split(/[/\\]/).pop();
        document.getElementById('confirmFolderBtn').disabled = false;
    }

    async confirm() {
        if (!this.currentPath) {
            showNotification('请选择一个文件夹', 'warning');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/folders`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: this.currentPath,
                    name: this.currentName
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            const folder = await response.json();
            showNotification(`✅ 已添加文件夹: ${folder.name}`, 'success');

            this.close();

            // 刷新文件夹列表
            if (window.folderManager) {
                window.folderManager.loadFolders();
            }

        } catch (error) {
            console.error('添加文件夹失败:', error);
            showNotification(`添加失败: ${error.message}`, 'error');
        }
    }
}

// 初始化文件夹浏览器
const folderBrowser = new FolderBrowser();


/**
 * 文件夹管理面板
 */
class FolderManager {
    constructor() {
        this.folders = [];
        this.createPanel();
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'folderManagerPanel';
        panel.className = 'management-panel';
        panel.style.display = 'none';

        panel.innerHTML = `
            <div class="panel-header">
                <h3>📂 文件夹管理</h3>
                <button class="btn-icon" onclick="folderManager.close()">✕</button>
            </div>
            
            <div class="panel-actions">
                <button class="btn btn-primary" onclick="folderBrowser.open()">
                    ➕ 添加文件夹
                </button>
            </div>
            
            <div class="panel-content" id="folderManagerContent">
                <div class="loading-spinner"></div>
                <p>正在加载...</p>
            </div>
        `;

        document.body.appendChild(panel);
        this.panel = panel;
    }

    async open() {
        this.panel.style.display = 'block';
        await this.loadFolders();
    }

    close() {
        this.panel.style.display = 'none';
    }

    async loadFolders() {
        const content = document.getElementById('folderManagerContent');
        content.innerHTML = '<div class="loading-spinner"></div><p>正在加载...</p>';

        try {
            const response = await fetch(`${API_BASE}/api/folders`);
            if (!response.ok) throw new Error('获取文件夹列表失败');

            this.folders = await response.json();
            this.renderFolders();

        } catch (error) {
            console.error('加载文件夹失败:', error);
            content.innerHTML = `<p class="error-message">❌ 加载失败: ${error.message}</p>`;
        }
    }

    renderFolders() {
        const content = document.getElementById('folderManagerContent');

        if (this.folders.length === 0) {
            content.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 3rem; margin-bottom: 1rem;">📁</p>
                    <p>还没有添加文件夹</p>
                    <p style="font-size: 0.9rem; color: var(--text-muted); margin-top: 0.5rem;">
                        点击"添加文件夹"开始索引您的图片
                    </p>
                </div>
            `;
            return;
        }

        content.innerHTML = this.folders.map(folder => {
            const statusIcon = {
                'pending': '⏸️',
                'indexing': '🔄',
                'active': '✅',
                'paused': '⏸️',
                'error': '❌'
            }[folder.status] || '❓';

            const statusText = {
                'pending': '待索引',
                'indexing': '索引中',
                'active': '已激活',
                'paused': '已暂停',
                'error': '错误'
            }[folder.status] || '未知';

            const lastScan = folder.last_scan ?
                new Date(folder.last_scan).toLocaleString('zh-CN') :
                '从未扫描';

            return `
                <div class="folder-card">
                    <div class="folder-card-header">
                        <div class="folder-card-icon">📂</div>
                        <div class="folder-card-info">
                            <div class="folder-card-name">${folder.name}</div>
                            <div class="folder-card-path">${folder.path}</div>
                        </div>
                        <div class="folder-card-status ${folder.status}">
                            ${statusIcon} ${statusText}
                        </div>
                    </div>
                    
                    <div class="folder-card-stats">
                        <div class="stat-item">
                            <span class="stat-label">图片总数</span>
                            <span class="stat-value">${folder.image_count}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">已索引</span>
                            <span class="stat-value">${folder.indexed_count}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">最后扫描</span>
                            <span class="stat-value-small">${lastScan}</span>
                        </div>
                    </div>
                    
                    <div class="folder-card-actions">
                        <button class="btn btn-small btn-secondary" 
                                onclick="folderManager.scanFolder('${folder.id}')"
                                ${folder.status === 'indexing' ? 'disabled' : ''}>
                            🔍 扫描
                        </button>
                        <button class="btn btn-small btn-primary" 
                                onclick="folderManager.indexFolder('${folder.id}')"
                                ${folder.status === 'indexing' ? 'disabled' : ''}>
                            🚀 索引
                        </button>
                        <button class="btn btn-small btn-danger" 
                                onclick="folderManager.removeFolder('${folder.id}')">
                            🗑️ 移除
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async scanFolder(folderId) {
        showNotification('正在扫描文件夹...', 'info');

        try {
            const response = await fetch(`${API_BASE}/api/folders/${folderId}/scan`, {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            const result = await response.json();
            showNotification(
                `✅ 扫描完成: 找到 ${result.valid_images} 张有效图片`,
                'success'
            );

            await this.loadFolders();

        } catch (error) {
            console.error('扫描失败:', error);
            showNotification(`扫描失败: ${error.message}`, 'error');
        }
    }

    async indexFolder(folderId) {
        showNotification('正在启动索引任务...', 'info');

        try {
            const response = await fetch(`${API_BASE}/api/folders/${folderId}/index`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force_reindex: false })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            const result = await response.json();
            showNotification(`✅ ${result.message}`, 'success');

            // 定期刷新状态
            const interval = setInterval(async () => {
                await this.loadFolders();
                const folder = this.folders.find(f => f.id === folderId);
                if (folder && folder.status !== 'indexing') {
                    clearInterval(interval);
                    showNotification('索引任务已完成', 'success');
                }
            }, 3000);

        } catch (error) {
            console.error('索引失败:', error);
            showNotification(`索引失败: ${error.message}`, 'error');
        }
    }

    async removeFolder(folderId) {
        if (!confirm('确定要移除此文件夹吗？（不会删除实际文件）')) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/folders/${folderId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            showNotification('✅ 文件夹已移除', 'success');
            await this.loadFolders();

        } catch (error) {
            console.error('移除失败:', error);
            showNotification(`移除失败: ${error.message}`, 'error');
        }
    }
}

// 初始化文件夹管理器
const folderManager = new FolderManager();


// 导出到全局
window.folderBrowser = folderBrowser;
window.folderManager = folderManager;
