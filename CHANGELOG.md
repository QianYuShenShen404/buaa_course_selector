# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-18

### Added
- 🎉 初始版本发布
- ✨ 自动登录功能：支持CAS认证登录，自动获取BatchID和Token
- 🔍 课程搜索功能：支持关键词搜索，自动获取课程信息和选课参数
- 🎯 自动选课功能：支持单次选课和循环重试选课
- ⚙️ 配置管理：JSON配置文件，支持命令行参数覆盖
- 📝 日志记录：多级别日志，文件轮转管理
- 🔄 智能重试机制：认证失败和网络异常自动重试
- 📋 模块化架构：配置管理、认证、执行、重试等模块分离

### Features
- 支持Python 3.8+
- 基于Playwright和Requests构建
- 支持Windows 10/11系统
- 完整的错误处理和日志记录
- 灵活的配置文件和命令行参数支持

### Technical
- Playwright >= 1.20.0 用于浏览器自动化
- Requests >= 2.28.0 用于HTTP请求
- Rich >= 10.0.0 用于美化终端输出
- 内置Python logging模块用于日志管理