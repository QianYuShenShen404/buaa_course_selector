import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger


class CourseSelector:
    """选课操作类 - 选课请求执行、结果状态解析、重试逻辑"""
    
    def __init__(self, auth_service):
        """
        初始化选课服务
        
        Args:
            auth_service: 认证服务实例，包含已认证的session
        """
        self.auth_service = auth_service
        self.session = auth_service.get_session()
        self.logger = get_logger()

    def select_course(self, clazz_id, secret_val, clazz_type="FANKC"):
        """选课功能 - 根据课程ID和secretVal进行选课"""
        print(f"📚 开始选课...")
        print(f"🆔 课程ID: {clazz_id}")
        print(f"🔑 SecretVal: {secret_val[:50]}...")
        print(f"📋 课程类型: {clazz_type}")
        self.logger.info(f"开始选课 - 课程ID: {clazz_id}, 类型: {clazz_type}")

        try:
            # 设置选课专用的请求头（注意Content-Type变更）
            select_headers = self.session.headers.copy()
            select_headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',  # 选课用form格式
                'Accept': 'application/json, text/plain, */*',
                'Authorization': self.auth_service.get_token(),
                'batchid': self.auth_service.get_batch_id(),
                'Origin': 'https://byxk.buaa.edu.cn',
                'Referer': f'https://byxk.buaa.edu.cn/xsxk/elective/grablessons?batchId={self.auth_service.get_batch_id()}',
                'Priority': 'u=1, i'
            })

            # 构建选课请求数据（form格式）
            select_data = {
                'clazzType': clazz_type,
                'clazzId': clazz_id,
                'secretVal': secret_val
            }

            print(f"📤 选课请求数据: {select_data}")

            # 发送选课请求
            response = self.session.post(
                'https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/add',
                data=select_data,  # 使用data而非json
                headers=select_headers
            )

            print(f"📊 选课响应状态: {response.status_code}")
            print(f"📊 响应类型: {response.headers.get('content-type', '')}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📊 选课响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

                    # 检查选课结果
                    if result.get('code') == 200 or result.get('success') == True:
                        print("🎉 选课成功！")
                        success_msg = result.get('message') or result.get('msg', '选课成功')
                        print(f"✅ {success_msg}")
                        self.logger.info(f"选课成功: {success_msg}")
                        return {'success': True, 'message': success_msg}
                    else:
                        error_msg = result.get('message') or result.get('msg', '未知错误')
                        print(f"❌ 选课失败: {error_msg}")
                        self.logger.error(f"选课失败: {error_msg}")
                        return {'success': False, 'error': error_msg}

                except json.JSONDecodeError:
                    print(f"❌ 选课响应格式错误")
                    print(f"响应内容: {response.text[:500]}...")
                    self.logger.error("选课响应格式错误")
                    return {'success': False, 'error': '响应格式错误'}
            else:
                print(f"❌ 选课请求失败，HTTP状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}...")
                self.logger.error(f"选课请求失败，HTTP状态码: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"❌ 选课过程出错: {e}")
            self.logger.error(f"选课过程出错: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def auto_select(self, course_search, retry_interval = 1):
        """根据关键词自动搜索并选课"""
        print(f"🎯 自动选课功能启动")
        print(f"🔄 无限循环选课")
        self.logger.info(f"自动选课启动")

        # # 搜索课程
        # search_result = course_search.search_courses()
        #
        # if not search_result.get('success', True):  # 如果搜索失败
        #     print(f"❌ 搜索失败")
        #     self.logger.error(f"搜索失败")
        #     return False

        # 检查是否有secretVal
        if not course_search.get_secret_val():
            print(f"❌ 未获取到secretVal")
            self.logger.error(f"未获取到secretVal")
            return False

        # 获取课程ID
        clazz_id = course_search.get_classid()
        if not clazz_id:
            print(f"❌ 未获取到课程ID")
            self.logger.error(f"未获取到课程ID")
            return False

        attempt = 0
        while True:
            # 在每次循环开始时检查停止标志
            if hasattr(self.auth_service, 'course_service'):
                course_service = getattr(self.auth_service, 'course_service')
                if course_service and course_service.should_stop_auto_select():
                    print("🛑 用户请求停止自动选课")
                    self.logger.info("用户请求停止自动选课")
                    return False
            
            attempt += 1
            print(f"\n🔄 第 {attempt} 次尝试...")
            self.logger.info(f"第 {attempt} 次尝试自动选课")
            print(f"🎯 尝试选课 - 课程名字: {course_search.get_class_name()}")

            # 进行选课
            select_result = self.select_course(clazz_id, course_search.get_secret_val())

            if select_result['success']:
                print(f"🎉 自动选课成功！")
                self.logger.info("自动选课成功")
                return True
            else:
                print(f"❌ 第 {attempt} 次选课失败: {select_result['error']}")
                self.logger.error(f"第 {attempt} 次选课失败: {select_result['error']}")

                # 如果是余量不足，可以继续尝试
                if "课容量已满" in select_result['error']:
                    print(f"⏳ 课程已满，等待{retry_interval}s后进行下次尝试...")
                    # 实现高频停止检查的等待
                    self._interruptible_sleep(retry_interval)
                else:
                    print(f"💔 选课失败，原因: {select_result['error']}")
                    break

        print(f"❌ 自动选课失败，已尝试 {attempt} 次")
        self.logger.error(f"自动选课失败，已尝试 {attempt} 次")
        return False

    def _interruptible_sleep(self, total_seconds):
        """可中断的睡眠，实现高频停止检查"""
        sleep_interval = 0.1  # 每次睡眠0.1秒
        elapsed = 0
        
        while elapsed < total_seconds:
            # 检查停止标志
            if hasattr(self.auth_service, 'course_service'):
                course_service = getattr(self.auth_service, 'course_service')
                if course_service and course_service.should_stop_auto_select():
                    print("🛑 在等待期间检测到停止信号")
                    return  # 立即返回，不继续等待
            
            # 短时间睡眠
            actual_sleep = min(sleep_interval, total_seconds - elapsed)
            time.sleep(actual_sleep)
            elapsed += actual_sleep

    async def auto_select_async(self, course_search, retry_interval=1, websocket_manager=None, session_id=None):
        """异步自动选课，支持实时状态推送"""
        self.logger.info(f"异步自动选课启动")
        
        # 通过WebSocket发送状态更新
        async def send_status(message, level='info'):
            if websocket_manager and session_id:
                await websocket_manager.send_personal_message(json.dumps({
                    "type": "status_update",
                    "message": message,
                    "level": level
                }, ensure_ascii=False), session_id)

        await send_status("🎯 异步自动选课启动", "info")
        
        # 检查是否有secretVal
        if not course_search.get_secret_val():
            await send_status("❌ 未获取到secretVal", "error")
            return False

        # 获取课程ID
        clazz_id = course_search.get_classid()
        if not clazz_id:
            await send_status("❌ 未获取到课程ID", "error")
            return False

        attempt = 0
        while True:
            # 在每次循环开始时检查停止标志
            if hasattr(self.auth_service, 'course_service'):
                course_service = getattr(self.auth_service, 'course_service')
                if course_service and course_service.should_stop_auto_select():
                    await send_status("🛑 用户请求停止自动选课", "warning")
                    return False
            
            attempt += 1
            await send_status(f"🔄 第 {attempt} 次尝试选课 - {course_search.get_class_name()}", "info")

            # 在线程池中执行选课操作
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                select_result = await loop.run_in_executor(
                    executor, 
                    self.select_course, 
                    clazz_id, 
                    course_search.get_secret_val()
                )

            if select_result['success']:
                await send_status("🎉 自动选课成功！", "success")
                return True
            else:
                await send_status(f"❌ 第 {attempt} 次选课失败: {select_result['error']}", "error")

                # 如果是余量不足，可以继续尝试
                if "课容量已满" in select_result['error'] or "该课程已在选课结果中" in select_result['error']:
                    await send_status(f"⏳ 课程已满，等待{retry_interval}s后进行下次尝试...", "warning")
                    # 异步等待并高频检查停止标志
                    if not await self._async_interruptible_sleep(retry_interval):
                        await send_status("🛑 在等待期间检测到停止信号", "warning")
                        return False
                else:
                    await send_status(f"💔 选课失败，原因: {select_result['error']}", "error")
                    return False

        await send_status(f"❌ 自动选课失败，已尝试 {attempt} 次", "error")
        return False

    async def _async_interruptible_sleep(self, total_seconds):
        """异步可中断的睡眠，实现高频停止检查"""
        sleep_interval = 0.1  # 每次睡眠0.1秒
        elapsed = 0
        
        while elapsed < total_seconds:
            # 检查停止标志
            if hasattr(self.auth_service, 'course_service'):
                course_service = getattr(self.auth_service, 'course_service')
                if course_service and course_service.should_stop_auto_select():
                    return False  # 返回false表示被中断
            
            # 异步短时间睡眠
            actual_sleep = min(sleep_interval, total_seconds - elapsed)
            await asyncio.sleep(actual_sleep)
            elapsed += actual_sleep
        
        return True  # 返回true表示正常完成