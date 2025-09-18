# 🎓 北航选课系统自动化工具

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

北航选课系统自动化工具，采用模块化架构设计，支持自动登录、课程搜索和选课操作。专为北航学生打造的智能选课助手，解决选课高峰期手动操作效率低、成功率低的问题。

## ✨ 核心功能

- **自动登录**: CAS认证登录，自动获取BatchID和Token
- **课程搜索**: 支持关键词搜索，自动获取课程信息和选课参数
- **自动选课**: 支持单次选课和循环重试选课
- **配置管理**: JSON配置文件，支持命令行参数覆盖
- **日志记录**: 多级别日志，文件轮转管理

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置信息

复制配置模板：

```bash
cp config_template.json config.json
```

编辑 `config.json`：

```json
{
  "user": {
    "student_id": "您的学号",
    "password": "您的密码",
    "target_course_name": "目标课程名称"
  },
  "system": {
    "log_level": "INFO",
    "retry_interval": 1,
    "course_selection_mode": "once",
    "max_log_files": 10,
    "log_file_size": "10MB"
  }
}
```

### 3. 运行程序

**使用配置文件：**
```bash
python main.py
```

**使用命令行参数：**
```bash
python main.py -u 学号 -p 密码 -c 课程名称
```

## 📁 项目结构

```
.
├── src/
│   ├── auth_service.py      # CAS认证服务
│   ├── course_search.py     # 课程搜索
│   ├── course_selector.py   # 选课操作
│   ├── course_service.py    # 统一服务接口
│   ├── config_loader.py     # 配置管理
│   └── logger.py           # 日志管理
├── sample/
│   └── all_in_one.py       # 简化版本（单文件版）
├── main.py                 # 主程序入口
├── config.json            # 配置文件
├── requirements.txt       # 依赖清单
└── README.md
```

### 🔧 简化版本说明

`sample/all_in_one.py` 是该项目的简化版本，将所有核心功能模块整合到一个Python文件中，适合以下场景：

- **快速体验**: 无需了解复杂的模块结构，直接运行即可
- **学习参考**: 所有代码逻辑集中在一处，便于理解选课流程
- **轻量部署**: 只需一个文件即可完成选课功能
- **自定义修改**: 方便直接在文件中修改用户名、密码等配置

**使用方法：**
```bash
# 直接运行简化版本
python sample/all_in_one.py
```

**注意：** 使用前请在文件中修改 `USERNAME`、`PASSWORD` 和 `CLASSNAME` 变量。

## ⚙️ 配置说明

### 用户配置 (user)
- `student_id`: 学号
- `password`: 密码
- `target_course_name`: 目标课程名称

### 系统配置 (system)
- `log_level`: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `retry_interval`: 重试间隔（秒）
- `course_selection_mode`: 选课模式 ("once" 单次 / "loop" 循环)
- `max_log_files`: 最大日志文件数
- `log_file_size`: 单个日志文件大小

## 📋 命令行参数

- `-u, --username`: 学号
- `-p, --password`: 密码
- `-c, --course`: 课程名称
- `--config`: 配置文件路径（默认: config.json）

## 📊 执行流程

1. **登录认证**: 访问选课系统，执行CAS认证，获取Token和BatchID
2. **搜索课程**: 根据课程名称搜索，获取课程ID和secretVal
3. **执行选课**: 提交选课请求，处理选课结果
4. **循环重试**: 根据配置决定是否循环重试选课

## 🔍 故障排除

### 常见问题

1. **登录失败**
   - 检查学号密码是否正确
   - 确认网络连接正常

2. **搜索无结果**
   - 确认课程名称拼写正确
   - 检查是否在选课时间段内

3. **选课失败**
   - 查看错误信息（余量不足、时间不对等）
   - 检查网络状况

### 日志查看

日志文件位于 `log/` 目录下，可以查看详细的执行信息和错误日志。

## ⚖️ 免责声明

本工具仅供学习交流使用，请遵守学校相关规定，使用者需自行承担使用风险。

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 📅 版本历史

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新信息。

## 🚀 快速部署

1. 克隆仓库：
```bash
git clone https://github.com/your-username/buaa-course-selection.git
cd buaa-course-selection
```

2. 安装依赖：
```bash
pip install -r requirements.txt
playwright install chromium
```

3. 配置信息：
```bash
cp config_template.json config.json
# 编辑 config.json 填入您的信息
```

4. 运行程序：
```bash
python main.py
```