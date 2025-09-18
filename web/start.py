#!/usr/bin/env python3
"""
北航选课系统 Web应用启动脚本
一键启动脚本，自动处理依赖安装与服务拉起
"""

import os
import sys
import subprocess
import webbrowser
import threading
import time
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

def check_dependencies():
    """检查Web应用依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        from pydantic import BaseModel
        print("✅ 所有Web依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("正在安装依赖...")
        
        # 安装依赖
        try:
            requirements_path = PROJECT_ROOT / "web" / "requirements.txt"
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "-r", str(requirements_path)
            ])
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            print(f"请手动运行: pip install -r {requirements_path}")
            return False

def check_project_structure():
    """检查项目结构完整性"""
    required_files = [
        "web/app.py",
        "src/course_service.py", 
        "templates/index.html",
        "static/css/app.css",
        "static/js/app.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (PROJECT_ROOT / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 项目文件不完整，缺少以下文件:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ 项目结构检查通过")
    return True

def open_browser_delayed():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务启动
    try:
        webbrowser.open("http://localhost:8000")
        print("🌐 浏览器已自动打开")
    except Exception as e:
        print(f"⚠️ 自动打开浏览器失败: {e}")

def main():
    """主启动函数"""
    print("🎓 北航选课系统 Web版 启动器")
    print("=" * 50)
    
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    
    # 检查项目结构
    if not check_project_structure():
        print("\n💡 解决方案:")
        print("   1. 确认在正确的项目目录下运行")
        print("   2. 检查项目文件是否完整")
        print("   3. 重新下载或重置项目")
        return
    
    # 检查依赖
    if not check_dependencies():
        return
    
    print("\n🚀 正在启动Web服务...")
    print("📱 Web界面将在浏览器中自动打开")
    print("🔗 手动访问地址: http://localhost:8000")
    print("📊 API文档地址: http://localhost:8000/api/docs")
    print("⚠️  按 Ctrl+C 停止服务\n")
    
    try:
        # 启动浏览器线程
        browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
        browser_thread.start()
        
        # 启动Web服务
        import uvicorn
        from web.app import app
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000, 
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n⚠️ 服务已停止")
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确认项目结构和依赖安装是否正确")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n💡 故障排除建议:")
        print("   1. 检查端口8000是否被占用")
        print("   2. 确认所有依赖已正确安装")
        print("   3. 检查src目录下的所有模块文件")
        print("   4. 查看上方错误信息的详细描述")

if __name__ == "__main__":
    main()