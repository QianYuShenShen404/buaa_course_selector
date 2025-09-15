#!/usr/bin/env python3
"""
北航选课系统自动化工具 - 方案二（混合架构）

方案二特性：
- 🔐 Playwright自动登录获取最新认证信息  
- 🚀 HTTP请求方式执行高效选课
- ⚡ 智能重试机制（登录重试 + HTTP重试）
- 📝 简化配置文件，只需用户名密码和课程信息
- 🎯 与现有main.py相同的CLI界面体验

使用方法:
    python main_v2_hybrid.py              # 开始选课
    python main_v2_hybrid.py --help       # 显示帮助信息
    python main_v2_hybrid.py --version    # 显示版本信息
    python main_v2_hybrid.py --test       # 测试配置和连接

作者: Assistant
版本: 2.0.0 (Hybrid Architecture)
创建时间: 2025-09-12
"""

import sys
import argparse
import asyncio
import os
import time
from pathlib import Path
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hybrid_course_selector import HybridCourseSelector, create_hybrid_course_selector, HybridCourseSelectorError
from simplified_config_manager import SimplifiedConfigValidationError


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="北航选课系统自动化工具 - 方案二（混合架构）",
        description="自动获取认证信息并执行高效选课，支持智能重试机制",
        epilog="配置文件: config_simple.json | 日志文件: logs/hybrid_course_selector.log"
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config_simple.json',
        help='简化配置文件路径 (默认: config_simple.json)'
    )
    
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='测试配置和网络连接'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s 2.0.0 (Hybrid Architecture)'
    )
    
    parser.add_argument(
        '--help-config',
        action='store_true',
        help='显示配置帮助信息'
    )
    
    parser.add_argument(
        '--username', '-u',
        type=str,
        help='用户名（覆盖配置文件）'
    )
    
    parser.add_argument(
        '--password', '-p',
        type=str,
        help='密码（覆盖配置文件）'
    )
    
    parser.add_argument(
        '--course-id',
        type=str,
        help='课程ID（覆盖配置文件）'
    )
    
    parser.add_argument(
        '--batch-id',
        type=str,
        help='批次ID（覆盖配置文件）'
    )
    
    return parser.parse_args()


def show_config_help():
    """显示配置帮助信息"""
    help_text = """
🔧 方案二配置文件帮助 (config_simple.json)

📋 简化配置结构：
{
  "user_credentials": {
    "username": "your_username_here",    // 你的用户名
    "password": "your_password_here"     // 你的密码
  },
  "course_info": {
    "course_id": "202520261B060032020001",           // 目标课程ID
    "batch_id": "d6d090c4364342bc94de17a22eaf7068",  // 批次ID
    "course_name": "计算机工程中最优化的方法"         // 课程名称（可选）
  },
  "browser_config": {
    "headless": false,      // 是否隐藏浏览器窗口
    "timeout": 30000        // 超时时间（毫秒）
  },
  "logging": {
    "level": "INFO",
    "file_path": "logs/hybrid_course_selector.log"
  }
}

🎯 方案二特点：
✅ 只需配置用户名密码和课程信息
✅ 无需手动获取Token/Cookie
✅ 自动处理认证信息过期
✅ 混合架构：Playwright登录 + HTTP选课

🚀 配置步骤：
1. 复制 config_simple.json 模板
2. 填入你的用户名和密码
3. 填入目标课程ID和批次ID
4. 运行: python main_v2_hybrid.py

❓ 获取课程ID和批次ID：
1. 手动登录选课系统
2. 找到想选的课程
3. 打开浏览器开发者工具(F12)
4. 点击选课按钮，查看网络请求
5. 在请求中找到 clazzId 和 batchid

🔧 测试配置：
python main_v2_hybrid.py --test
    """
    print(help_text)


def test_configuration(config_path: str) -> bool:
    """
    测试配置文件和连接
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        测试是否通过
    """
    print("🔍 开始混合架构配置和连接测试...")
    print()
    
    try:
        # 1. 测试配置文件
        print("📋 测试简化配置文件...")
        selector = create_hybrid_course_selector(config_path)
        print("✅ 简化配置文件加载成功")
        
        # 2. 测试网络连接
        print("🌐 测试网络连接...")
        if selector.test_connection():
            print("✅ 网络连接正常")
        else:
            print("❌ 网络连接测试失败")
            selector.close()
            return False
        
        # 3. 显示配置摘要
        print("📊 配置摘要:")
        course_info = selector.get_course_info()
        print(f"  课程ID: {course_info.get('course_id', '未设置')}")
        print(f"  课程名称: {course_info.get('course_name', '未设置')}")
        print(f"  批次ID: {course_info.get('batch_id', '未设置')}")
        
        # 4. 清理资源
        selector.close()
        
        print()
        print("🎉 所有测试通过！混合架构配置正确，可以开始选课。")
        print()
        print("💡 提示：方案二特点")
        print("  ✨ 自动获取最新认证信息，无需手动配置Token")
        print("  🚀 使用HTTP请求进行高效选课")
        print("  🔄 智能重试机制，登录失败和网络异常都会自动重试")
        print("  📝 简化配置，只需用户名密码和课程信息")
        
        return True
        
    except SimplifiedConfigValidationError as e:
        print(f"❌ 配置文件错误: {e}")
        print()
        print("💡 解决方案:")
        print("  1. 检查config_simple.json格式是否正确")
        print("  2. 确认用户名和密码已正确填写")
        print("  3. 确认课程ID和批次ID已正确填写")
        print("  4. 运行 'python main_v2_hybrid.py --help-config' 查看配置帮助")
        return False
        
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_path}")
        print()
        print("💡 解决方案:")
        print("  复制 config_simple.json 模板并填写你的信息")
        return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print()
        print("💡 请检查错误信息并修复相关问题")
        return False


def create_banner():
    """创建程序横幅"""
    return """
╔════════════════════════════════════════════════ BUAA Course Selector v2 ═════════════════════════════════════════════════════╗
║                                                                                                                               ║
║                                    🎓 北航选课系统自动化工具 - 方案二（混合架构）                                              ║
║                                                                                                                               ║
║                            🔐 自动认证   🚀 高效选课   ⚡ 智能重试   📝 简化配置                                               ║
║                                                                                                                               ║
╚════════════════════════════════════════════════ v2.0.0 - Hybrid Architecture ════════════════════════════════════════════════╝
    """


def show_course_info(selector: HybridCourseSelector):
    """显示课程信息"""
    try:
        course_info = selector.get_course_info()
        print("╭────────────────────────────────────────────────────────── 课程信息 ───────────────────────────────────────────────────────────╮")
        print("│                                                                                                                               │")
        print(f"│   📚 课程ID      {course_info.get('course_id', 'Unknown'):<80} │")
        print(f"│   📖 课程名称    {course_info.get('course_name', 'Unknown'):<80} │")
        print(f"│   🏷️  批次ID      {course_info.get('batch_id', 'Unknown'):<80} │")
        print("│                                                                                                                               │")
        print("╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯")
    except Exception:
        print("⚠️ 无法获取课程信息")


def show_selection_result(result):
    """显示选课结果"""
    if result.success:
        # 成功结果
        print()
        print("╔══════════════════════════════════════════════════════════ 选课成功 ═══════════════════════════════════════════════════════════╗")
        print("║                                                                                                                               ║")
        print("║ 🎉 选课成功                                                                                                                   ║")
        print("║                                                                                                                               ║")
        print(f"║ 📚 课程: {result.course_name:<90} ║")
        print(f"║ 📖 课程ID: {result.course_id:<88} ║")
        print(f"║ ⏱️  总用时: {result.total_time:.1f}s (认证: {result.auth_time:.1f}s + 选课: {result.selection_time:.1f}s)                                        ║")
        print(f"║ 🔄 重试次数: 认证{result.auth_attempts}次, 选课{result.selection_attempts}次                                                                      ║")
        print("║                                                                                                                               ║")
        print("╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝")
    else:
        # 失败结果
        print()
        print("╔══════════════════════════════════════════════════════════ 选课失败 ═══════════════════════════════════════════════════════════╗")
        print("║                                                                                                                               ║")
        print("║ 💔 选课失败                                                                                                                   ║")
        print("║                                                                                                                               ║")
        print(f"║ ❌ 原因: {result.message:<94} ║")
        print(f"║ ⏱️  总用时: {result.total_time:.1f}s                                                                                              ║")
        print("║                                                                                                                               ║")
        if result.auth_error:
            print(f"║ 🔐 认证错误: {result.auth_error:<86} ║")
        if result.selection_error:
            print(f"║ 🚀 选课错误: {result.selection_error:<86} ║")
        print("║                                                                                                                               ║")
        print("║ 请检查配置或网络连接后重试                                                                                                        ║")
        print("║                                                                                                                               ║")
        print("╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝")


async def main_async():
    """异步主函数"""
    args = parse_arguments()
    
    # 处理特殊命令
    if args.help_config:
        show_config_help()
        return 0
    
    # 检查配置文件
    config_path = args.config
    if not Path(config_path).exists():
        print(f"❌ 简化配置文件不存在: {config_path}")
        print()
        print("💡 请先创建配置文件:")
        print("   1. 复制 config_simple.json 模板")
        print("   2. 填写用户名、密码和课程信息")
        print("   3. 运行: python main_v2_hybrid.py --help-config 查看详细帮助")
        return 1
    
    # 测试模式
    if args.test:
        success = test_configuration(config_path)
        return 0 if success else 1
    
    # 正常选课模式
    try:
        # 显示程序横幅
        print(create_banner())
        
        # 创建选课器
        selector = create_hybrid_course_selector(config_path)
        
        # 显示课程信息
        show_course_info(selector)
        
        print()
        print("🚀 开始混合架构选课流程...")
        print("   阶段1: 🔐 Playwright自动登录获取认证信息")
        print("   阶段2: 🚀 HTTP请求执行高效选课")
        print()
        
        # 开始计时
        start_time = time.time()
        
        # 执行选课
        result = await selector.execute_course_selection(
            course_id=args.course_id,
            batch_id=args.batch_id,
            username=args.username,
            password=args.password
        )
        
        # 显示结果
        show_selection_result(result)
        
        # 清理资源
        selector.close()
        
        # 返回状态码
        return 0 if result.success else 1
        
    except SimplifiedConfigValidationError as e:
        print(f"❌ 配置错误: {e}")
        print()
        print("💡 请检查config_simple.json文件:")
        print("   python main_v2_hybrid.py --help-config")
        return 1
        
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        return 0
        
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        print()
        print("💡 请检查错误信息，必要时查看日志文件:")
        print("   logs/hybrid_course_selector.log")
        return 1


def main():
    """主函数"""
    try:
        # 在Windows上设置事件循环策略
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序启动异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
