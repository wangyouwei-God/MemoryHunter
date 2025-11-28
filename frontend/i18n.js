// ============ i18n (Internationalization) ============
const i18n = {
    currentLang: 'zh', // 默认中文

    translations: {
        zh: {
            subtitle: '最智能的相册检索系统',
            indexedImages: '已索引图片',
            systemStatus: '系统就绪',
            startIndex: '开始索引',
            indexing: '索引中',
            searchPlaceholder: '输入中文描述搜索，例如：蓝色的裙子、夕阳海滩、那只橘猫...',
            searchBtn: '搜索',
            returnCount: '返回数量',
            similarityThreshold: '相似度阈值',
            localPrivacy: '100% 本地运行 · 数据隐私安全',
            version: '轻量版',
            // Folder drawer
            folderManagement: '文件夹管理',
            monitoredFolders: '监控目录',
            folders: '个文件夹',
            images: '张',
            indexed: '已索引',
            notIndexed: '未索引',
            addFolder: '添加文件夹',
            addNewFolder: '添加新文件夹',
            folderPath: '文件夹路径',
            folderPathPlaceholder: '例如: ~/Pictures/MyPhotos',
            cancel: '取消',
            confirmAdd: '确认添加',
            removeFolderConfirm: '确定要移除此文件夹吗？',
            settings: '设置'
        },
        en: {
            subtitle: 'Smart Photo Search System',
            indexedImages: 'Indexed Photos',
            systemStatus: 'Ready',
            startIndex: 'Start Indexing',
            indexing: 'Indexing',
            searchPlaceholder: 'Search by description, e.g.: blue dress, sunset beach, orange cat...',
            searchBtn: 'Search',
            returnCount: 'Results',
            similarityThreshold: 'Similarity',
            localPrivacy: '100% Local · Privacy Secured',
            version: 'Lite Edition',
            // Folder drawer
            folderManagement: 'Folder Management',
            monitoredFolders: 'Monitored Folders',
            folders: 'folders',
            images: 'images',
            indexed: 'Indexed',
            notIndexed: 'Not Indexed',
            addFolder: 'Add Folder',
            addNewFolder: 'Add New Folder',
            folderPath: 'Folder Path',
            folderPathPlaceholder: 'e.g.: ~/Pictures/MyPhotos',
            cancel: 'Cancel',
            confirmAdd: 'Confirm',
            removeFolderConfirm: 'Remove this folder?',
            settings: 'Settings'
        }
    },

    // 切换语言
    toggle() {
        this.currentLang = this.currentLang === 'zh' ? 'en' : 'zh';
        this.apply();
        this.saveLang();
    },

    // 应用翻译
    apply() {
        const t = this.translations[this.currentLang];

        // 更新所有带data-i18n属性的元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (t[key]) {
                // 如果是input,更新placeholder
                if (el.tagName === 'INPUT' && el.type === 'text') {
                    el.placeholder = t[key];
                } else {
                    el.textContent = t[key];
                }
            }
        });

        // 更新语言按钮文本
        const langText = document.getElementById('langText');
        if (langText) {
            langText.textContent = this.currentLang === 'zh' ? 'EN' : '中';
        }

        // 更新标题(如果需要保持MemoryHunter不翻译)
        const subtitle = document.querySelector('.subtitle');
        if (subtitle) {
            subtitle.textContent = t.subtitle;
        }

        console.log(`✅ Language switched to: ${this.currentLang}`);
    },

    // 保存语言偏好到localStorage
    saveLang() {
        try {
            localStorage.setItem('memhunter_lang', this.currentLang);
        } catch (e) {
            console.warn('Cannot save language preference');
        }
    },

    // 加载语言偏好
    loadLang() {
        try {
            const saved = localStorage.getItem('memhunter_lang');
            if (saved && (saved === 'zh' || saved === 'en')) {
                this.currentLang = saved;
                this.apply();
            }
        } catch (e) {
            console.warn('Cannot load language preference');
        }
    },

    // 初始化
    init() {
        // 加载保存的语言
        this.loadLang();

        // 绑定语言切换按钮
        const langBtn = document.getElementById('langBtn');
        if (langBtn) {
            langBtn.addEventListener('click', () => this.toggle());
        }

        console.log('✅ i18n initialized');
    }
};

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => i18n.init());
} else {
    i18n.init();
}
