/**
 * 北航选课系统 Web应用 JavaScript
 * 处理前端交互逻辑、WebSocket通信、API调用
 */

class CourseSystemUI {
    constructor() {
        this.sessionId = null;
        this.websocket = null;
        this.isOperating = false;
        this.initEventListeners();
        this.addLog('🚀 系统初始化完成，请登录开始使用', 'info');
    }

    /**
     * 初始化事件监听器
     */
    initEventListeners() {
        // 登录表单
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });

        // 搜索相关
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.searchCourses();
        });
        
        // 搜索框回车
        document.getElementById('searchKeyword').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchCourses();
            }
        });

        // 选课操作
        document.getElementById('selectOnceBtn').addEventListener('click', () => {
            this.selectCourse(false);
        });

        document.getElementById('selectAutoBtn').addEventListener('click', () => {
            this.selectCourse(true);
        });

        // 停止按钮事件（初始化时添加）
        document.getElementById('stopSelectBtn').addEventListener('click', () => {
            this.confirmAndShutdown();
        });

        // 其他操作
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });
        
        document.getElementById('statusBtn').addEventListener('click', () => {
            this.getStatus();
        });
        
        document.getElementById('clearLogBtn').addEventListener('click', () => {
            document.getElementById('statusLog').innerHTML = '';
            this.addLog('🗑️ 日志已清空', 'info');
        });
    }

    /**
     * 添加日志信息
     * @param {string} message - 日志消息
     * @param {string} level - 日志级别 (info, success, error, warning)
     */
    addLog(message, level = 'info') {
        const logArea = document.getElementById('statusLog');
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        
        let className = 'status-info';
        let icon = 'ℹ️';
        
        if (level === 'success') {
            className = 'status-success';
            icon = '✅';
        } else if (level === 'error') {
            className = 'status-error';
            icon = '❌';
        } else if (level === 'warning') {
            className = 'status-warning';
            icon = '⚠️';
        }
        
        logEntry.className = className;
        logEntry.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${icon} ${message}`;
        
        logArea.appendChild(logEntry);
        logArea.scrollTop = logArea.scrollHeight;
    }
    
    /**
     * 设置按钮加载状态
     * @param {string} elementId - 元素ID
     * @param {boolean} isLoading - 是否加载中
     * @param {string} loadingText - 加载文本
     */
    setLoading(elementId, isLoading, loadingText = '处理中...') {
        const element = document.getElementById(elementId);
        if (isLoading) {
            element.disabled = true;
            element.innerHTML = `${loadingText} <div class="spinner-border spinner-border-sm ms-2" role="status"></div>`;
        } else {
            element.disabled = false;
        }
    }

    /**
     * 用户登录
     */
    async login() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        if (!username || !password) {
            this.addLog('请输入完整的学号和密码', 'error');
            return;
        }

        this.setLoading('loginBtnText', true, '正在登录...');
        document.getElementById('loginSpinner').style.display = 'inline-block';
        
        try {
            this.addLog(`🔐 开始登录，用户: ${username}`, 'info');
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const result = await response.json();
            
            if (result.success) {
                this.sessionId = result.data.session_id;
                this.showMainPanel(result.data);
                this.initWebSocket();
                this.addLog('🎉 登录成功！系统已就绪', 'success');
            } else {
                this.addLog(`❌ 登录失败: ${result.message}`, 'error');
            }
        } catch (error) {
            this.addLog(`💥 登录异常: ${error.message}`, 'error');
        } finally {
            document.getElementById('loginBtnText').textContent = '登录';
            document.getElementById('loginSpinner').style.display = 'none';
            document.querySelector('#loginForm button').disabled = false;
        }
    }

    /**
     * 显示主操作面板
     * @param {object} loginData - 登录返回的数据
     */
    showMainPanel(loginData) {
        document.getElementById('loginPanel').style.display = 'none';
        document.getElementById('mainPanel').style.display = 'block';
        
        // 更新用户信息
        const userInfoText = document.getElementById('userInfoText');
        userInfoText.innerHTML = `<strong>${loginData.username}</strong> 已成功登录，会话ID: <code>${loginData.session_id.substring(0, 8)}...</code>`;
        
        // 设置默认搜索词
        document.getElementById('searchKeyword').placeholder = '例如：计算机图形学';
    }

    /**
     * 初始化WebSocket连接
     */
    initWebSocket() {
        if (!this.sessionId) return;
        
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${this.sessionId}`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            this.addLog('📡 WebSocket连接建立，实时监控已启动', 'success');
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'status_update') {
                    this.addLog(message.message, message.level);
                    
                    // 处理特殊的状态更新
                    if (message.data) {
                        switch (message.data.type) {
                            case 'auto_select_stopped':
                                this.switchToAutoButton(); // 恢复按钮状态
                                this.addLog('✅ 自动选课已停止，按钮状态已恢复', 'success');
                                break;
                            case 'stop_auto_select_requested':
                                this.addLog('🛑 停止信号已发送，正在等待任务完成...', 'warning');
                                break;
                            case 'task_completed':
                                this.switchToAutoButton(); // 任务完成后恢复按钮
                                this.addLog('✅ 任务已完成，按钮状态已恢复', 'info');
                                break;
                        }
                    }
                }
            } catch (e) {
                console.error('WebSocket消息解析失败:', e);
            }
        };
        
        this.websocket.onclose = () => {
            this.addLog('📡 WebSocket连接断开', 'warning');
        };
        
        this.websocket.onerror = (error) => {
            this.addLog('📡 WebSocket连接错误', 'error');
        };
    }

    /**
     * 搜索课程
     * @param {string} keyword - 搜索关键词
     */
    async searchCourses(keyword = null) {
        if (keyword === null) {
            keyword = document.getElementById('searchKeyword').value.trim();
        }
        
        if (!this.sessionId) {
            this.addLog('❌ 请先登录系统', 'error');
            return;
        }

        const searchBtn = document.getElementById('searchBtn');
        const originalText = searchBtn.innerHTML;
        searchBtn.innerHTML = '🔍 搜索中...';
        searchBtn.disabled = true;

        try {
            this.addLog(`🔍 开始搜索课程: "${keyword || '所有课程'}"`, 'info');
            
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    keyword: keyword
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.displaySearchResults(result.data);
                this.addLog(`✅ 搜索完成，找到 ${result.data.courses.length} 门课程`, 'success');
            } else {
                this.addLog(`❌ 搜索失败: ${result.message}`, 'error');
                this.clearSearchResults();
            }
        } catch (error) {
            this.addLog(`💥 搜索异常: ${error.message}`, 'error');
            this.clearSearchResults();
        } finally {
            searchBtn.innerHTML = originalText;
            searchBtn.disabled = false;
        }
    }

    /**
     * 显示搜索结果
     * @param {object} data - 搜索结果数据
     */
    displaySearchResults(data) {
        const resultsDiv = document.getElementById('courseResults');
        
        if (data.has_results && data.courses.length > 0) {
            const course = data.courses[0]; // 显示第一个结果
            const hasSecretVal = data.secret_val && data.secret_val.length > 0;
            
            resultsDiv.innerHTML = `
                <div class="card course-card fade-in">
                    <div class="card-header bg-success text-white">
                        <h6 class="mb-0">📚 找到匹配课程</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <p class="mb-2"><strong>📖 课程名称:</strong> ${course.KCM || '未知课程'}</p>
                                <p class="mb-2"><strong>👨‍🏫 授课教师:</strong> ${course.JSXM || course.SKJS || '未知教师'}</p>
                                <p class="mb-2"><strong>🆔 课程ID:</strong> <code>${course.JXBID || course.classId || '未知'}</code></p>
                                <p class="mb-0"><strong>👥 选课情况:</strong> 
                                    <span class="badge bg-primary">${course.numberOfSelected || course.YXRS || 0} 人已选</span>
                                    <span class="badge bg-secondary">${course.classCapacity || course.KRL || 0} 人容量</span>
                                </p>
                            </div>
                            <div class="col-md-4">
                                <div class="text-center">
                                    ${hasSecretVal ? 
                                        `<div class="alert alert-success p-2 mb-2">
                                            <i class="text-success">✅ 选课密钥已获取</i><br>
                                            <small class="text-muted">可以开始选课</small>
                                        </div>` : 
                                        `<div class="alert alert-warning p-2 mb-2">
                                            <i class="text-warning">⚠️ 未获取选课密钥</i><br>
                                            <small class="text-muted">无法选课</small>
                                        </div>`
                                    }
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 启用选课按钮
            if (hasSecretVal) {
                const selectOnceBtn = document.getElementById('selectOnceBtn');
                const selectAutoBtn = document.getElementById('selectAutoBtn');
                
                if (selectOnceBtn) {
                    selectOnceBtn.disabled = false;
                } else {
                    console.error('selectOnceBtn 元素未找到');
                }
                
                if (selectAutoBtn) {
                    selectAutoBtn.disabled = false;
                } else {
                    console.error('selectAutoBtn 元素未找到');
                }
            }
            
        } else {
            resultsDiv.innerHTML = `
                <div class="alert alert-warning fade-in">
                    <h6>⚠️ 未找到匹配的课程</h6>
                    <p class="mb-0">请尝试：</p>
                    <ul class="mb-0">
                        <li>使用更精确的课程名称关键词</li>
                        <li>点击"获取所有课程"查看完整列表</li>
                        <li>确认课程是否在当前批次开放选课</li>
                    </ul>
                </div>
            `;
            this.disableSelectButtons();
        }
    }
    
    /**
     * 清空搜索结果
     */
    clearSearchResults() {
        document.getElementById('courseResults').innerHTML = '';
        this.disableSelectButtons();
    }
    
    /**
     * 禁用选课按钮
     */
    disableSelectButtons() {
        const selectOnceBtn = document.getElementById('selectOnceBtn');
        const selectAutoBtn = document.getElementById('selectAutoBtn');
        
        if (selectOnceBtn) {
            selectOnceBtn.disabled = true;
        } else {
            console.error('selectOnceBtn 元素未找到');
        }
        
        if (selectAutoBtn) {
            selectAutoBtn.disabled = true;
        } else {
            console.error('selectAutoBtn 元素未找到');
        }
    }

    /**
     * 选课操作
     * @param {boolean} autoMode - 是否自动模式
     */
    async selectCourse(autoMode = false) {
        if (!this.sessionId) {
            this.addLog('❌ 请先登录系统', 'error');
            return;
        }
        
        if (this.isOperating) {
            this.addLog('⚠️ 操作进行中，请等待完成', 'warning');
            return;
        }
        
        // 如果是自动模式，先显示确认对话框
        if (autoMode) {
            const confirmed = confirm(
                '🚨 确认启动自动重试选课？\n\n' +
                '🔄 系统将持续尝试选课直到成功\n' +
                '🛑 启动后按钮将变为红色“停止”按钮\n' +
                '⚠️ 点击停止按钮可优雅停止自动选课\n' +
                '👀 可通过实时日志监控选课进度\n\n' +
                '确定要继续吗？'
            );
            
            if (!confirmed) {
                return;
            }
            
            // 切换按钮状态
            this.switchToStopButton();
        }
        
        this.isOperating = true;
        const btnId = autoMode ? 'selectAutoBtn' : 'selectOnceBtn';
        
        // 只有非自动模式才更新按钮状态（自动模式已经切换了）
        if (!autoMode) {
            const originalText = document.getElementById(btnId).innerHTML;
            document.getElementById(btnId).innerHTML = `🎯 选课中...`;
            document.getElementById(btnId).disabled = true;
        }
        
        try {
            this.addLog(`🎯 启动${autoMode ? '自动' : '单次'}选课模式...`, 'info');
            
            const response = await fetch('/api/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    auto_retry: autoMode
                })
            });

            const result = await response.json();
            
            if (result.success) {
                if (autoMode) {
                    // 异步自动选课已启动，不需要立即恢复按钮
                    this.addLog('🚀 异步自动选课已启动，请通过日志监控进度', 'success');
                } else {
                    this.addLog('🎉 单次选课成功！', 'success');
                }
            } else {
                this.addLog(`❌ ${autoMode ? '异步自动' : '单次'}选课失败: ${result.message}`, 'error');
                if (autoMode) {
                    this.switchToAutoButton(); // 失败后恢复按钮状态
                }
            }
        } catch (error) {
            this.addLog(`💥 选课异常: ${error.message}`, 'error');
            if (autoMode) {
                this.switchToAutoButton(); // 异常后恢复按钮状态
            }
        } finally {
            if (!autoMode) {
                document.getElementById(btnId).innerHTML = '🎯 单次选课';
                document.getElementById(btnId).disabled = false;
            }
            this.isOperating = false;
        }
    }
    
    /**
     * 获取系统状态
     */
    async getStatus() {
        if (!this.sessionId) {
            this.addLog('❌ 请先登录系统', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/status/${this.sessionId}`);
            const result = await response.json();
            
            if (result.success) {
                const status = result.data;
                this.addLog(`📊 系统状态: 认证=${status.authenticated ? '✅' : '❌'}, 搜索=${status.search_ready ? '✅' : '❌'}, 选课=${status.selector_ready ? '✅' : '❌'}`, 'info');
            }
        } catch (error) {
            this.addLog(`💥 状态查询失败: ${error.message}`, 'error');
        }
    }

    /**
     * 用户登出
     */
    async logout() {
        if (this.sessionId) {
            try {
                await fetch(`/api/logout/${this.sessionId}`, { method: 'DELETE' });
                this.addLog('👋 已安全登出', 'info');
            } catch (error) {
                this.addLog('⚠️ 登出请求失败，但将继续本地清理', 'warning');
            }
        }
        
        if (this.websocket) {
            this.websocket.close();
        }
        
        // 重置界面
        document.getElementById('loginPanel').style.display = 'block';
        document.getElementById('mainPanel').style.display = 'none';
        document.getElementById('loginForm').reset();
        document.getElementById('statusLog').innerHTML = '';
        document.getElementById('courseResults').innerHTML = '';
        
        this.sessionId = null;
        this.isOperating = false;
        this.disableSelectButtons();
        
        this.addLog('🔄 系统已重置，请重新登录', 'info');
    }

    /**
     * 切换到停止按钮
     */
    switchToStopButton() {
        const autoBtn = document.getElementById('selectAutoBtn');
        const stopBtn = document.getElementById('stopSelectBtn');
        
        if (autoBtn && stopBtn) {
            autoBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            this.addLog('🛑 按钮已切换为停止模式', 'warning');
        } else {
            console.error('无法找到按钮元素');
        }
    }

    /**
     * 切换到自动选课按钮
     */
    switchToAutoButton() {
        const autoBtn = document.getElementById('selectAutoBtn');
        const stopBtn = document.getElementById('stopSelectBtn');
        
        if (autoBtn && stopBtn) {
            autoBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            this.addLog('🔄 按钮已恢复为自动选课模式', 'info');
        } else {
            console.error('无法找到按钮元素');
        }
    }

    /**
     * 确认并停止自动选课
     */
    async confirmAndShutdown() {
        const confirmed = confirm(
            '🚨 确认停止自动选课？\n\n' +
            '🛑 系统将执行：\n' +
            '1. 优雅停止当前自动选课任务\n' +
            '2. 等待当前操作完成后停止\n' +
            '3. 恢复按钮状态为可操作\n\n' +
            '✅ 注意：Web程序将继续运行，不会关闭\n\n' +
            '确定要停止自动选课吗？'
        );
        
        if (confirmed) {
            try {
                this.addLog('🛑 用户确认停止自动选课，正在执行...', 'warning');
                
                // 优雅停止自动选课
                await this.stopAutoSelect();
                
                // 等待一下再恢复按钮状态
                setTimeout(() => {
                    this.switchToAutoButton();
                    this.addLog('✅ 自动选课已停止，可以重新开始', 'success');
                }, 1500);
                
            } catch (error) {
                this.addLog(`❌ 停止过程失败: ${error.message}`, 'error');
                // 失败后也要恢复按钮状态
                this.switchToAutoButton();
            }
        }
    }

    /**
     * 优雅停止自动选课
     */
    async stopAutoSelect() {
        if (!this.sessionId) {
            this.addLog('❌ 无效的会话 ID', 'error');
            return;
        }
        
        try {
            this.addLog('🛑 正在发送停止信号...', 'warning');
            
            const response = await fetch(`/api/stop-select/${this.sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.addLog('✅ 停止信号已发送，等待任务完成', 'info');
            } else {
                this.addLog(`❌ 停止失败: ${result.message}`, 'error');
            }
        } catch (error) {
            this.addLog(`❌ 停止请求失败: ${error.message}`, 'error');
        }
    }

}

// 初始化系统
window.addEventListener('DOMContentLoaded', function() {
    new CourseSystemUI();
});