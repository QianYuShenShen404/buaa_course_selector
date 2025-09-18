import json
try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger


class CourseSearch:
    """课程搜索类 - 课程信息查询、搜索结果解析"""
    
    def __init__(self, auth_service):
        """
        初始化课程搜索服务
        
        Args:
            auth_service: 认证服务实例，包含已认证的session
        """
        self.auth_service = auth_service
        self.session = auth_service.get_session()
        self.logger = get_logger()
        
        # 存储搜索结果
        self.search_results = []
        self.classid = None
        self.secret_val = None
        self.class_name = None

    def search_courses(self, keyword=""):
        """搜索课程 - 使用固定参数+关键词"""
        if keyword:
            print(f"🔍 搜索关键词: {keyword}")
            self.logger.info(f"搜索关键词: {keyword}")
            self.class_name = keyword
        else:
            print("🔍 获取所有课程...")
            self.logger.info("获取所有课程")

        try:
            # 固定的请求参数
            search_data = {
                "teachingClassType": "FANKC",
                "pageNumber": 1,
                "pageSize": 10,
                "orderBy": "",
                "campus": "1",
                "SFCT": "0"
            }

            # 只有当有关键词时才添加KEY字段
            if keyword:
                search_data["KEY"] = keyword
            elif keyword == "":
                print("⚠️ 未指定关键词，请输入一个课程名称")
                return {'success': False, 'error': '未输入课程名称'}

            print(f"📤 请求数据: {json.dumps(search_data, ensure_ascii=False)}")

            response = self.session.post(
                'https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/list',
                json=search_data
            )

            print(f"📊 搜索响应状态: {response.status_code}")
            print(f"📊 响应类型: {response.headers.get('content-type', '')}")

            if response.status_code == 200:
                try:
                    result = response.json()

                    # 检查API响应结构
                    if result.get('code') == 200 or result.get('success') == True:
                        # 获取课程数据
                        data = result.get('data', {})
                        
                        # 保存搜索结果
                        self.search_results = data.get('rows', [])
                        
                        if self.search_results:
                            # 尝试获取classid
                            class_id = data.get('rows')[0].get('JXBID')
                            if class_id:
                                print(f"🔑 获取到classid: {class_id}")
                                self.logger.info(f"获取到classid: {class_id}")
                                self.classid = class_id
                            else:
                                print("⚠️ 未发现classid字段")
                                print(f"🔍 data结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                                self.logger.warning("未发现classid字段")

                            # 尝试获取secretVal字段内容
                            secret_val = data.get('rows')[0].get('secretVal')
                            if secret_val:
                                print(f"🔑 获取到secretVal: {secret_val}")
                                self.logger.info("获取到secretVal")
                                # 保存secretVal供后续选课使用
                                self.secret_val = secret_val
                            else:
                                print("⚠️ 未发现secretVal字段")
                                # 打印data结构以便调试
                                print(f"🔍 data结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                                self.logger.warning("未发现secretVal字段")
                        
                        print(f"✅ 搜索完成，找到 {len(self.search_results)} 门课程")
                        self.logger.info(f"搜索完成，找到 {len(self.search_results)} 门课程")
                        return {'success': True, 'data': self.search_results, 'count': len(self.search_results)}
                    else:
                        error_msg = result.get('message') or result.get('msg', '未知错误')
                        print(f"❌ 搜索失败: {error_msg}")
                        print(f"🔍 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        self.logger.error(f"搜索失败: {error_msg}")
                        return {'success': False, 'error': error_msg}

                except json.JSONDecodeError:
                    print(f"❌ 搜索响应格式错误")
                    print(f"响应内容: {response.text[:500]}...")
                    self.logger.error("搜索响应格式错误")
                    return {'success': False, 'error': '响应格式错误'}
            else:
                print(f"❌ 搜索请求失败，HTTP状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                self.logger.error(f"搜索请求失败，HTTP状态码: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"❌ 搜索过程出错: {e}")
            self.logger.error(f"搜索过程出错: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def get_course_info(self, course_index=0):
        """获取指定索引的课程信息"""
        if not self.search_results:
            return None
        
        if course_index >= len(self.search_results):
            return None
        
        return self.search_results[course_index]

    def get_classid(self):
        """获取课程ID"""
        return self.classid

    def get_secret_val(self):
        """获取secretVal"""
        return self.secret_val

    def get_class_name(self):
        """获取课程名字"""
        return self.class_name

    def has_search_results(self):
        """检查是否有搜索结果"""
        return len(self.search_results) > 0

    def print_search_results(self):
        """打印搜索结果"""
        if not self.search_results:
            print("📋 暂无搜索结果")
            return
        
        print(f"📋 搜索结果 (共 {len(self.search_results)} 门课程):")
        for i, course in enumerate(self.search_results):
            course_name = course.get('KCM', '未知课程')
            teacher_name = course.get('JSXM', '未知教师')
            class_id = course.get('JXBID', '未知ID')
            print(f"  {i+1}. {course_name} - {teacher_name} (ID: {class_id})")

    def clear_results(self):
        """清空搜索结果"""
        self.search_results = []
        self.classid = None
        self.secret_val = None