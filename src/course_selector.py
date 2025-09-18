import json
import time
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

    def auto_select_by_keyword(self, course_search, keyword):
        """根据关键词自动搜索并选课"""
        print(f"🎯 自动选课功能启动")
        print(f"🔍 搜索关键词: {keyword}")
        print(f"🔄 无限循环选课")
        self.logger.info(f"自动选课启动 - 关键词: {keyword}")
        attempt = 0

        while True:
            attempt += 1
            print(f"\n🔄 第 {attempt} 次尝试...")
            self.logger.info(f"第 {attempt} 次尝试自动选课")

            # 搜索课程
            search_result = course_search.search_courses(keyword=keyword)

            if not search_result.get('success', True):  # 如果搜索失败
                print(f"❌ 第 {attempt} 次搜索失败")
                self.logger.error(f"第 {attempt} 次搜索失败")
                return False

            # 检查是否有secretVal
            if not course_search.get_secret_val():
                print(f"❌ 第 {attempt} 次未获取到secretVal")
                self.logger.error(f"第 {attempt} 次未获取到secretVal")
                return False

            # 获取课程ID
            clazz_id = course_search.get_classid()
            if not clazz_id:
                print(f"❌ 第 {attempt} 次未获取到课程ID")
                self.logger.error(f"第 {attempt} 次未获取到课程ID")
                return False

            print(f"🎯 尝试选课 - 课程ID: {clazz_id}")

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
                if "余量不足" in select_result['error'] or "已满" in select_result['error']:
                    print(f"⏳ 课程已满，等待下次尝试...")
                    time.sleep(2)  # 等待2秒再试
                else:
                    print(f"💔 选课失败，原因: {select_result['error']}")
                    break

        print(f"❌ 自动选课失败，已尝试 {attempt} 次")
        self.logger.error(f"自动选课失败，已尝试 {attempt} 次")
        return False

    def select_course_with_retry(self, clazz_id, secret_val, clazz_type="FANKC", 
                                max_retries=3, retry_interval=2):
        """带重试的选课功能"""
        print(f"🔄 启动重试选课 - 最大重试次数: {max_retries}")
        self.logger.info(f"启动重试选课 - 课程ID: {clazz_id}, 最大重试次数: {max_retries}")
        
        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 第 {attempt} 次选课尝试...")
            
            result = self.select_course(clazz_id, secret_val, clazz_type)
            
            if result['success']:
                print(f"🎉 选课成功！")
                return result
            else:
                error_msg = result['error']
                print(f"❌ 第 {attempt} 次失败: {error_msg}")
                
                # 检查是否需要重试
                if attempt < max_retries:
                    if "余量不足" in error_msg or "已满" in error_msg or "网络" in error_msg:
                        print(f"⏳ {retry_interval}秒后重试...")
                        time.sleep(retry_interval)
                    else:
                        print(f"💔 不可重试的错误，停止重试")
                        break
                else:
                    print(f"❌ 已达到最大重试次数")
        
        return {'success': False, 'error': f'重试{max_retries}次后仍然失败'}

    def batch_select_courses(self, course_list, max_attempts_per_course=3):
        """批量选课功能"""
        print(f"📚 开始批量选课 - 共 {len(course_list)} 门课程")
        self.logger.info(f"开始批量选课 - 共 {len(course_list)} 门课程")
        
        results = []
        
        for i, course_info in enumerate(course_list):
            print(f"\n📋 选课进度: {i+1}/{len(course_list)}")
            
            clazz_id = course_info.get('clazz_id')
            secret_val = course_info.get('secret_val')
            clazz_type = course_info.get('clazz_type', 'FANKC')
            course_name = course_info.get('course_name', f'课程{i+1}')
            
            if not clazz_id or not secret_val:
                error_msg = f"课程 {course_name} 缺少必要参数"
                print(f"❌ {error_msg}")
                results.append({
                    'course_name': course_name,
                    'success': False,
                    'error': error_msg
                })
                continue
            
            print(f"🎯 正在选课: {course_name}")
            
            result = self.select_course_with_retry(
                clazz_id, secret_val, clazz_type, 
                max_retries=max_attempts_per_course
            )
            
            result['course_name'] = course_name
            results.append(result)
            
            if result['success']:
                print(f"✅ {course_name} 选课成功")
            else:
                print(f"❌ {course_name} 选课失败: {result['error']}")
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        print(f"\n📊 批量选课完成:")
        print(f"  ✅ 成功: {success_count} 门")
        print(f"  ❌ 失败: {len(results) - success_count} 门")
        
        return results