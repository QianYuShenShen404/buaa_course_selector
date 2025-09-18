#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北航自动选课系统 - Vue版本状态检查器

检查前后端服务运行状态
"""

import psutil
import requests
import socket
from urllib.parse import urlparse

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

def check_port(host, port):
    """检查端口是否被占用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def check_http_service(url):
    """检查HTTP服务是否正常"""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def find_processes_by_port(port):
    """根据端口查找进程"""
    processes = []
    try:
        connections = psutil.net_connections(kind='inet')
        for conn in connections:
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                try:
                    proc = psutil.Process(conn.pid)
                    processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception:
        pass
    return processes

def check_frontend_status():
    """检查前端状态"""
    print_styled("🔍 检查前端服务状态...", "info")
    
    # 检查常见的前端端口
    frontend_ports = [5173, 3000, 8080]
    frontend_running = False
    
    for port in frontend_ports:
        if check_port('localhost', port):
            processes = find_processes_by_port(port)
            if processes:
                proc = processes[0]
                print_styled(f"前端服务运行中 - 端口: {port}, 进程: {proc.name()} (PID: {proc.pid})", "success")
                print_styled(f"访问地址: http://localhost:{port}", "info")
                frontend_running = True
                break
    
    if not frontend_running:
        print_styled("前端服务未运行", "warning")
    
    return frontend_running

def check_backend_status():
    """检查后端状态"""
    print_styled("🔍 检查后端服务状态...", "info")
    
    backend_port = 8000
    backend_running = False
    
    if check_port('localhost', backend_port):
        processes = find_processes_by_port(backend_port)
        if processes:
            proc = processes[0]
            print_styled(f"后端服务运行中 - 端口: {backend_port}, 进程: {proc.name()} (PID: {proc.pid})", "success")
            print_styled(f"API地址: http://localhost:{backend_port}", "info")
            print_styled(f"文档地址: http://localhost:{backend_port}/docs", "info")
            backend_running = True
            
            # 尝试访问健康检查接口
            try:
                if check_http_service(f"http://localhost:{backend_port}"):
                    print_styled("后端API响应正常", "success")
                else:
                    print_styled("后端API无响应", "warning")
            except:
                print_styled("无法验证后端API状态", "warning")
    
    if not backend_running:
        print_styled("后端服务未运行", "warning")
    
    return backend_running

def check_system_resources():
    """检查系统资源"""
    print_styled("🔍 检查系统资源...", "info")
    
    # 检查CPU使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent < 50:
        print_styled(f"CPU使用率: {cpu_percent}% - 正常", "success")
    elif cpu_percent < 80:
        print_styled(f"CPU使用率: {cpu_percent}% - 中等", "warning")
    else:
        print_styled(f"CPU使用率: {cpu_percent}% - 较高", "error")
    
    # 检查内存使用率
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    if memory_percent < 70:
        print_styled(f"内存使用率: {memory_percent}% - 正常", "success")
    elif memory_percent < 85:
        print_styled(f"内存使用率: {memory_percent}% - 中等", "warning")
    else:
        print_styled(f"内存使用率: {memory_percent}% - 较高", "error")

def show_quick_commands():
    """显示快速命令"""
    print_styled("🚀 快速操作命令:", "info")
    print("  启动系统: python start_vue_system.py")
    print("  关闭系统: python stop_vue_system.py")
    print("  查看状态: python check_system_status.py")
    print("  Windows快捷: 启动系统.bat / 关闭系统.bat")

def main():
    """主函数"""
    print("=" * 50)
    print("📊 北航选课系统 - 状态检查器")
    print("=" * 50)
    
    try:
        # 检查前端状态
        frontend_ok = check_frontend_status()
        print()
        
        # 检查后端状态
        backend_ok = check_backend_status()
        print()
        
        # 检查系统资源
        check_system_resources()
        print()
        
        # 总体状态
        print("=" * 50)
        if frontend_ok and backend_ok:
            print_styled("🎉 系统运行正常！所有服务都在线", "success")
        elif frontend_ok or backend_ok:
            print_styled("⚠️ 部分服务运行中", "warning")
            if not frontend_ok:
                print_styled("前端服务需要启动", "warning")
            if not backend_ok:
                print_styled("后端服务需要启动", "warning")
        else:
            print_styled("❌ 系统未启动", "error")
        
        print()
        show_quick_commands()
        print("=" * 50)
        
    except KeyboardInterrupt:
        print_styled("\n检查被中断", "warning")
    except Exception as e:
        print_styled(f"检查过程中出现错误: {e}", "error")

if __name__ == "__main__":
    main()