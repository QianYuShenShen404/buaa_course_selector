#!/usr/bin/env python3
"""
北航选课系统 - Vue版本一键启动脚本
自动启动Vue前端和FastAPI后端，提供完整的Web服务
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

def print_banner():
    """打印启动横幅"""
    print("🎓 北航自动选课系统 - Vue 3版本")
    print("=" * 60)
    print("🎨 前端: Vue 3 + Vite + Element Plus")
    print("🔧 后端: FastAPI + WebSocket")
    print("🚀 构建: 现代化组件架构")
    print("=" * 60)

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python环境
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}")
    
    # 检查Node.js
    try:
        result = subprocess.run("node --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js {result.stdout.strip()}")
        else:
            print("❌ Node.js检测失败")
            return False
    except Exception:
        print("❌ Node.js未安装")
        return False
    
    # 检查npm
    try:
        result = subprocess.run("npm --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm {result.stdout.strip()}")
        else:
            print("❌ npm检测失败")
            return False
    except Exception:
        print("❌ npm未安装")
        return False
    
    return True

def check_dependencies():
    """检查依赖"""
    print("\n📦 检查项目依赖...")
    
    # 检查后端依赖
    try:
        import fastapi
        import uvicorn
        print("✅ 后端依赖已安装")
    except ImportError:
        print("🔄 正在安装后端依赖...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 
                          'fastapi', 'uvicorn[standard]', 'websockets'], check=True)
            print("✅ 后端依赖安装完成")
        except subprocess.CalledProcessError:
            print("❌ 后端依赖安装失败")
            return False
    
    # 检查前端依赖
    if not (FRONTEND_DIR / "node_modules").exists():
        print("🔄 正在安装前端依赖...")
        try:
            subprocess.run("npm install", shell=True, cwd=FRONTEND_DIR, check=True)
            print("✅ 前端依赖安装完成")
        except subprocess.CalledProcessError:
            print("❌ 前端依赖安装失败")
            return False
    else:
        print("✅ 前端依赖已安装")
    
    return True

def start_backend():
    """启动FastAPI后端"""
    print("🔧 启动FastAPI后端服务...")
    try:
        os.chdir(PROJECT_ROOT)
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "web.app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("⚠️ 后端服务已停止")
    except Exception as e:
        print(f"❌ 后端启动失败: {e}")

def start_frontend():
    """启动Vue前端"""
    print("🎨 启动Vue前端开发服务器...")
    try:
        # 强制使用端口3000，清理缓存
        subprocess.run("npm run dev -- --force --port 3000", 
                     shell=True, cwd=FRONTEND_DIR)
    except KeyboardInterrupt:
        print("⚠️ 前端服务已停止")
    except Exception as e:
        print(f"❌ 前端启动失败: {e}")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(3)
    try:
        webbrowser.open("http://localhost:3000")
        print("🌐 浏览器已自动打开")
    except Exception as e:
        print(f"⚠️ 自动打开浏览器失败: {e}")

def main():
    """主函数"""
    print_banner()
    
    # 环境检查
    if not check_environment():
        print("\n💡 环境问题解决方案:")
        print("1. 安装Node.js: https://nodejs.org/")
        print("2. 确认Python版本 >= 3.8")
        print("3. 重启命令行窗口")
        input("按回车键退出...")
        return
    
    # 依赖检查
    if not check_dependencies():
        print("\n💡 请手动解决依赖问题后重试")
        input("按回车键退出...")
        return
    
    # 显示启动信息
    print("\n🚀 正在启动服务...")
    print("📝 访问地址:")
    print("   🖥️  Vue前端:    http://localhost:3000")
    print("   🔧 FastAPI后端: http://localhost:8000")
    print("   📚 API文档:     http://localhost:8000/api/docs")
    print("   ⚠️  按 Ctrl+C 停止所有服务")
    print("=" * 60)
    
    try:
        # 启动浏览器线程
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # 启动后端线程
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        
        # 等待后端启动
        time.sleep(2)
        
        # 启动前端（主线程）
        start_frontend()
        
    except KeyboardInterrupt:
        print("\n⚠️ 正在停止所有服务...")
        print("👋 感谢使用北航选课系统！")
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        print("\n💡 故障排除建议:")
        print("1. 检查端口3000和8000是否被占用")
        print("2. 确认所有依赖已正确安装")
        print("3. 查看上方错误信息")

if __name__ == "__main__":
    main()