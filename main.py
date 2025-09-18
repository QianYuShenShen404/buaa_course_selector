import sys
import os
import argparse
import time

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.course_service import CourseService
from src.config_loader import get_config


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="北航选课系统重构版")
    
    parser.add_argument('-u', '--username', type=str, help='学号')
    parser.add_argument('-p', '--password', type=str, help='密码')
    parser.add_argument('-c', '--course', type=str, help='课程名称')
    parser.add_argument('--config', type=str, default='config.json', help='配置文件路径')
    
    return parser.parse_args()


def main():
    """主程序入口"""
    print("🎓 北航选课系统 - 重构版")
    print("=" * 50)
    
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 加载配置
        config = get_config(args.config)
        user_config = config.get_user_config()
        system_config = config.get_system_config()
        
        # 获取用户信息 - 优先使用命令行参数，其次使用配置文件
        username = args.username or user_config.get('student_id')
        password = args.password or user_config.get('password')
        course_name = args.course or user_config.get('target_course_name')
        
        # 配置信息检查
        if not username:
            print("❌ 缺少学号，请在配置文件中设置或使用 -u 参数")
            print("💡 配置文件示例: {'user': {'student_id': '您的学号'}}")
            return
            
        if not password:
            print("❌ 缺少密码，请在配置文件中设置或使用 -p 参数")
            print("💡 配置文件示例: {'user': {'password': '您的密码'}}")
            return
            
        if not course_name:
            print("❌ 缺少课程名称，请在配置文件中设置或使用 -c 参数")
            print("💡 配置文件示例: {'user': {'target_course_name': '课程名称'}}")
            return
        
        print(f"👤 用户: {username}")
        print(f"📚 目标课程: {course_name}")
        
        # 创建服务实例
        service = CourseService(username, password, args.config)

        # 执行选课流程
        # 第一步：登录
        print("=" * 30)
        if not service.login():
            print("❌ 登录失败，程序终止")
            return

        # 第二步：搜索课程
        print("\n" + "=" * 30)
        print("🎉 登录成功！现在可以搜索课程了")

        search_result = service.search_course(course_name)

        if not search_result.get('success', True):
            print(f"❌ 搜索失败: {search_result.get('error')}")
            return

        # 第三步：选课
        if service.course_search.get_secret_val():
            attempts = 0
            while True:
                attempts += 1
                print("\n" + "=" * 30)
                print("🎯 开始选课测试...")
                print(f"第 {attempts} 次尝试选课...")

                result = service.select_course(attempts)

                if result['success']:
                    print("🎉 选课成功！")
                    break
                else:
                    print(f"❌ 第 {attempts} 次选课失败: {result['error']}")

                    # 如果是余量不足，可以继续尝试
                    if "课容量已满" in result['error']:
                        print(f"⏳ 课程已满，等待下次尝试...")
                    else:
                        print(f"💔 选课失败，原因: {result['error']}")
                        break

                if system_config.get('course_selection_mode', 'once') == 'once':
                    break
                time.sleep(system_config.get('retry_interval', 1))
        else:
            print("❌ 未获取到secretVal，无法进行选课")
        
        # 清理资源
        service.cleanup()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序执行异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()