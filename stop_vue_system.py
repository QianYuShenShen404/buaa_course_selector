#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北航自动选课系统 - Vue版本关闭器

安全关闭前后端服务
"""

import os
import sys
import signal
import psutil
import time
import json
from pathlib import Path

def print_styled(message, style="info"):
    """打印带样式的消息"""
    colors = {
        "info": "\033[94m",      # 蓝色
        "success": "\033[92m",   # 绿色
        "warning": "\033[93m",   # 黄色
        "error": "\033[91m",     # 红色
        "reset": "\033[0m"       # 重置
    }
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    color = colors.get(style, colors["info"])
    icon = icons.get(style, "")
    reset = colors["reset"]
    
    print(f"{color}{icon} {message}{reset}")

def find_processes_by_name(name_patterns):
    """根据进程名称模式查找进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_info = proc.info
            cmdline_list = proc_info.get('cmdline', [])
            cmdline = ' '.join(cmdline_list) if cmdline_list else ''
            
            for pattern in name_patterns:
                if pattern.lower() in proc_info['name'].lower() or pattern.lower() in cmdline.lower():
                    processes.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def find_processes_by_port(ports):
    """根据端口查找进程"""
    processes = []
    for port in ports:
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections:
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    try:
                        proc = psutil.Process(conn.pid)
                        if proc not in processes:
                            processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception as e:
            print_styled(f"检查端口 {port} 时出错: {e}", "warning")
    return processes

def terminate_process(proc, timeout=5):
    """优雅地终止进程"""
    try:
        proc_name = proc.name()
        proc_pid = proc.pid
        print_styled(f"正在关闭进程: {proc_name} (PID: {proc_pid})", "info")
        
        # 首先尝试优雅关闭
        proc.terminate()
        
        # 等待进程优雅退出
        try:
            proc.wait(timeout=timeout)
            print_styled(f"进程 {proc_name} 已优雅退出", "success")
            return True
        except psutil.TimeoutExpired:
            # 如果优雅关闭失败，强制终止
            print_styled(f"强制终止进程: {proc_name}", "warning")
            proc.kill()
            proc.wait(timeout=3)
            print_styled(f"进程 {proc_name} 已强制终止", "success")
            return True
            
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print_styled(f"无法终止进程: {e}", "error")
        return False

def stop_backend():
    """停止后端服务"""
    print_styled("🔍 查找后端服务进程...", "info")
    
    # 查找FastAPI/Uvicorn相关进程
    backend_patterns = ['uvicorn', 'fastapi', 'python.*main.py', 'python.*app.py']
    backend_processes = find_processes_by_name(backend_patterns)
    
    # 同时查找占用8000端口的进程
    port_processes = find_processes_by_port([8000])
    
    all_processes = list(set(backend_processes + port_processes))
    
    if not all_processes:
        print_styled("未找到运行中的后端服务", "info")
        return True
    
    success_count = 0
    for proc in all_processes:
        if terminate_process(proc):
            success_count += 1
    
    print_styled(f"后端服务关闭完成 ({success_count}/{len(all_processes)})", "success")
    return success_count == len(all_processes)

def stop_frontend():
    """停止前端服务"""
    print_styled("🔍 查找前端服务进程...", "info")
    
    # 查找Vite相关进程
    frontend_patterns = ['vite', 'node.*vite', 'npm.*dev', 'yarn.*dev']
    frontend_processes = find_processes_by_name(frontend_patterns)
    
    # 同时查找占用5173端口的进程
    port_processes = find_processes_by_port([5173, 3000, 8080])
    
    all_processes = list(set(frontend_processes + port_processes))
    
    if not all_processes:
        print_styled("未找到运行中的前端服务", "info")
        return True
    
    success_count = 0
    for proc in all_processes:
        if terminate_process(proc):
            success_count += 1
    
    print_styled(f"前端服务关闭完成 ({success_count}/{len(all_processes)})", "success")
    return success_count == len(all_processes)

def cleanup_temp_files():
    """清理临时文件"""
    print_styled("🧹 清理临时文件...", "info")
    
    cleanup_paths = [
        "frontend/.vite",
        "frontend/node_modules/.cache",
        "__pycache__",
        "*.pyc"
    ]
    
    for path_pattern in cleanup_paths:
        try:
            if "*" in path_pattern:
                # 处理通配符
                import glob
                for file_path in glob.glob(path_pattern, recursive=True):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            else:
                # 处理目录
                full_path = Path(path_pattern)
                if full_path.exists():
                    import shutil
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                    else:
                        full_path.unlink()
        except Exception as e:
            # 清理失败不影响主要功能
            pass
    
    print_styled("临时文件清理完成", "success")

def save_shutdown_log():
    """保存关闭日志"""
    try:
        log_data = {
            "shutdown_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "success"
        }
        
        with open("system_shutdown.log", "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
            
    except Exception:
        # 日志记录失败不影响主要功能
        pass

def main():
    """主函数"""
    print("=" * 50)
    print("🛑 北航选课系统 - Vue版本关闭器")
    print("=" * 50)
    
    try:
        # 检查管理员权限（Windows）
        if os.name == 'nt':
            try:
                import ctypes
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    print_styled("建议以管理员身份运行，以确保能够关闭所有进程", "warning")
            except:
                pass
        
        print_styled("开始关闭系统服务...", "info")
        
        # 关闭前端服务
        frontend_success = stop_frontend()
        time.sleep(1)
        
        # 关闭后端服务
        backend_success = stop_backend()
        time.sleep(1)
        
        # 清理临时文件
        cleanup_temp_files()
        
        # 保存关闭日志
        save_shutdown_log()
        
        print("=" * 50)
        if frontend_success and backend_success:
            print_styled("🎉 系统已完全关闭！", "success")
        else:
            print_styled("⚠️ 部分服务可能仍在运行，请手动检查", "warning")
        
        print_styled("感谢使用北航选课系统！", "info")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print_styled("\n用户中断操作", "warning")
        sys.exit(1)
    except Exception as e:
        print_styled(f"关闭过程中出现错误: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()