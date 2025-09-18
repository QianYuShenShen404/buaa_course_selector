#!/usr/bin/env python3
"""
北航选课系统 Web应用启动脚本（已迁移）
请使用新的启动方式：python web/start.py
"""

import os
import sys
from pathlib import Path

def main():
    print("📄 此启动脚本已迁移")
    print("=" * 50)
    print("🚀 请使用新的启动方式：")
    print("   python web/start.py")
    print("📁 或者进入web目录后运行：")
    print("   cd web && python start.py")
    print("=" * 50)
    
    # 自动调用新的启动脚本
    try:
        from web.start import main as web_main
        print("🔄 自动调用新的启动脚本...\n")
        web_main()
    except ImportError:
        print("❌ 无法自动调用，请手动使用上述命令")

if __name__ == "__main__":
    main()