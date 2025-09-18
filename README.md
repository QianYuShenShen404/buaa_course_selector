# 🎓 北航自动选课系统 - Vue 3 重构版

## 📋 项目概述

本项目是北航自动选课系统的Vue 3重构版本，采用现代化的前端技术栈，提供更优雅的用户界面和更好的用户体验。

### ✨ 主要特性

- 🎨 **现代化UI设计** - 基于Element Plus，提供精美的界面体验
- ⚡ **高性能架构** - Vue 3 + Vite，极速开发和构建
- 📱 **响应式设计** - 完美适配桌面端和移动端
- 🔄 **实时通信** - WebSocket实时状态推送和日志监控
- 🛡️ **安全认证** - 保持原有的CAS认证机制
- 🎯 **智能选课** - 支持单次选课和自动重试选课
- 📊 **实时监控** - 可视化的选课进度和状态反馈

### 🏗️ 技术栈

**前端技术栈:**
- **Vue 3** - 渐进式JavaScript框架
- **Element Plus** - 基于Vue 3的组件库
- **Vite** - 下一代前端构建工具
- **Axios** - HTTP客户端
- **SCSS** - CSS预处理器

**后端技术栈:**
- **FastAPI** - 现代Python Web框架
- **WebSocket** - 实时双向通信
- **Uvicorn** - ASGI服务器

## 📦 脚本版本说明

### 📁 简化版脚本 (sample/all_in_one.py)

在 `sample` 目录下提供了一个简化版的脚本 `all_in_one.py`，这是一个单文件的选课脚本，包含了基本的登录、搜索和选课功能：

- **特点**: 单文件包含所有功能，无需复杂配置
- **适用场景**: 快速测试、临时使用、学习代码结构
- **功能**: CAS登录、课程搜索、单次选课、自动重试选课
- **优势**: 代码简单易懂，方便修改和调试

```bash
# 直接运行简化版脚本
python sample/all_in_one.py
```

### 🖥️ CLI版本脚本 (main.py)

`main.py` 是命令行界面版本的脚本，提供更专业的命令行操作体验：

- **特点**: 模块化设计，支持命令行参数和配置文件
- **适用场景**: 自动化脚本、批量操作、生产环境使用
- **配置**: 支持 `config.json` 配置文件和命令行参数
- **优势**: 功能完整，易于集成到其他系统

```bash
# 使用配置文件运行
python main.py

# 使用命令行参数运行
python main.py -u 学号 -p 密码 -c "课程名称"

# 指定配置文件
python main.py --config custom_config.json
```

**参数说明:**
- `-u, --username`: 学号
- `-p, --password`: 密码  
- `-c, --course`: 课程名称
- `--config`: 配置文件路径（默认: config.json）

## 🚀 快速开始

### 一键启动（推荐）

```bash
# 启动完整系统（前端 + 后端）
python start_vue_system.py

# 或使用批处理文件（Windows）
启动系统.bat
```

### 一键关闭

```bash
# 安全关闭所有服务
python stop_vue_system.py

# 或使用批处理文件（Windows）
关闭系统.bat
```

### 状态检查

```bash
# 检查系统运行状态
python check_system_status.py
```

### 分别启动

```bash
# 方式1: 启动原版Web系统
python start_web.py

# 方式2: 手动启动Vue版本
# 终端1: 启动后端
python -m uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload

# 终端2: 启动前端
cd frontend
npm install
npm run dev
```

### 访问地址

- 🎨 **Vue前端**: http://localhost:3000
- 🔧 **FastAPI后端**: http://localhost:8000
- 📚 **API文档**: http://localhost:8000/api/docs

## 📁 项目结构

```
├── frontend/                 # Vue 3前端项目
│   ├── src/
│   │   ├── components/       # Vue组件
│   │   │   ├── LoginPanel.vue      # 登录面板
│   │   │   ├── MainPanel.vue       # 主操作面板
│   │   │   ├── CourseSearch.vue    # 课程搜索
│   │   │   ├── SelectCourse.vue    # 选课操作
│   │   │   └── LogMonitor.vue      # 日志监控
│   │   ├── utils/           # 工具类
│   │   │   ├── api.js             # API调用
│   │   │   └── websocket.js       # WebSocket管理
│   │   ├── style/           # 样式文件
│   │   │   ├── main.scss          # 主样式
│   │   │   └── enhanced.scss      # 增强效果
│   │   ├── App.vue          # 根组件
│   │   └── main.js          # 入口文件
│   ├── package.json         # 依赖配置
│   ├── vite.config.js       # Vite配置
│   └── index.html           # HTML模板
├── web/                     # 后端API服务
├── static/                  # 旧版静态资源
├── templates/               # 旧版模板文件
└── start_vue.py            # Vue版本启动脚本
```

## 🎯 功能特性

### 🔐 登录认证
- 支持学号密码登录
- 自动获取CAS认证令牌
- 会话管理和安全登出

### 🔍 课程搜索
- 关键词搜索课程
- 自动获取选课密钥
- 课程信息详细展示

### 🎯 智能选课
- **单次选课** - 测试选课功能
- **自动重试** - 持续尝试直到成功
- **优雅停止** - 安全终止自动选课

### 📊 实时监控
- WebSocket实时日志推送
- 选课进度可视化显示
- 系统状态实时反馈

## 🎨 界面展示

### 主要改进

1. **玻璃态设计** - 现代化的半透明效果
2. **渐变背景** - 视觉吸引力更强
3. **动画效果** - 平滑的交互反馈
4. **响应式布局** - 完美的移动端适配
5. **图标系统** - 丰富的视觉指引

### 设计亮点

- 🌈 **渐变色彩** - 从蓝紫色过渡的背景
- 💎 **玻璃效果** - 半透明毛玻璃卡片设计
- ✨ **微动效** - 悬停和点击的精细动画
- 📱 **自适应** - 桌面和移动端完美适配

## 🛑 系统关闭

### 安全关闭服务

推荐使用专门的关闭脚本来安全地终止所有服务：

```bash
# 使用Python脚本关闭
python stop_vue_system.py

# 或使用批处理文件（Windows快捷方式）
关闭系统.bat
```

### 关闭脚本功能

- 🔍 **智能进程识别** - 自动查找前后端相关进程
- 🛡️ **优雅关闭** - 首先尝试正常终止，必要时强制结束
- 📊 **端口检查** - 检查占用8000、5173等端口的进程
- 🧹 **清理临时文件** - 自动清理缓存和临时文件
- 📝 **关闭日志** - 记录关闭操作的详细信息

### 手动关闭方式

如果自动脚本无法正常工作，可以手动关闭：

```bash
# Windows
# 查找并结束Node.js进程（前端）
tasklist | findstr node
taskkill /F /IM node.exe

# 查找并结束Python进程（后端）
tasklist | findstr python
taskkill /F /IM python.exe

# Linux/Mac
# 结束占用端口的进程
sudo lsof -ti:5173 | xargs kill -9  # 前端
sudo lsof -ti:8000 | xargs kill -9  # 后端
```

## 🔧 开发指南

## 📝 更新日志

### v1.0.0 (2024-01-XX)
- 🎉 Vue 3重构版本首次发布
- ✨ 全新的用户界面设计
- ⚡ 性能优化和体验提升
- 📱 完整的响应式支持

## 🔍 故障排除

### 常见问题

**Q: 前端启动失败，提示端口被占用**
```bash
# 查看端口占用
netstat -ano | findstr :3000
# 结束进程或修改端口
```

**Q: 后端连接失败**
```bash
# 确认后端服务运行状态
curl http://localhost:8000/health
```

**Q: WebSocket连接失败**
- 检查后端WebSocket服务是否正常
- 确认防火墙设置
- 验证代理配置

---

**🎓 享受现代化的选课体验！**