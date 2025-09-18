try:
    from .auth_service import AuthService
    from .course_search import CourseSearch
    from .course_selector import CourseSelector
    from .config_loader import get_config
    from .logger import get_logger
except ImportError:
    from auth_service import AuthService
    from course_search import CourseSearch
    from course_selector import CourseSelector
    from config_loader import get_config
    from logger import get_logger


class CourseService:
    """统一课程服务 - 编排各个模块按流程执行"""
    
    def __init__(self, username=None, password=None, config_file="config.json"):
        """
        初始化课程服务
        
        Args:
            username: 用户名 (学号)
            password: 密码
            config_file: 配置文件路径
        """
        self.config = get_config(config_file)
        self.logger = get_logger(system_config=self.config.get_system_config())
        
        # 获取用户配置
        user_config = self.config.get_user_config()
        
        # 使用参数或配置文件中的用户信息
        self.username = username or user_config.get('student_id', '')
        self.password = password or user_config.get('password', '')
        
        if not self.username or not self.password:
            raise ValueError("❌ 缺少用户名或密码，请在配置文件中设置或通过参数传入")
        
        # 初始化各个服务模块
        self.auth_service = None
        self.course_search = None
        self.course_selector = None
        
        # 停止标志位控制
        self.stop_auto_select_flag = False
        
        self.logger.info("课程服务初始化完成")

    def login(self):
        """登录认证"""
        print("=" * 30)
        print("🚀 开始登录认证...")
        self.logger.info("开始登录认证")
        
        try:
            # 创建认证服务实例
            self.auth_service = AuthService(self.username, self.password)
            
            # 执行登录
            success = self.auth_service.login()
            
            if success:
                print("✅ 登录认证成功！")
                self.logger.info("登录认证成功")
                
                # 初始化其他服务模块
                self.course_search = CourseSearch(self.auth_service)
                self.course_selector = CourseSelector(self.auth_service)
                
                return True
            else:
                print("❌ 登录认证失败")
                self.logger.error("登录认证失败")
                return False
                
        except Exception as e:
            print(f"❌ 登录过程异常: {e}")
            self.logger.error(f"登录过程异常: {e}")
            return False

    def search_course(self, course_name):
        """搜索课程"""
        if not self.course_search:
            print("❌ 请先完成登录认证")
            return {'success': False, 'error': '未登录'}
        
        print("\n" + "=" * 30)
        print(f"🔍 搜索课程: {course_name}")
        self.logger.info(f"搜索课程: {course_name}")
        
        try:
            # 调用搜索功能
            result = self.course_search.search_courses(keyword=course_name)
            
            if result.get('success', True):
                print(f"✅ 课程搜索完成")
                self.course_search.print_search_results()
                return result
            else:
                print(f"❌ 课程搜索失败: {result.get('error', '未知错误')}")
                return result
                
        except Exception as e:
            print(f"❌ 搜索过程异常: {e}")
            self.logger.error(f"搜索过程异常: {e}")
            return {'success': False, 'error': str(e)}

    def select_course(self):
        """选择课程"""
        if not self.course_selector or not self.course_search:
            print("❌ 请先完成登录和搜索")
            return {'success': False, 'error': '服务未初始化'}
        
        # 检查搜索结果
        if not self.course_search.has_search_results():
            print("❌ 没有可选择的课程")
            return {'success': False, 'error': '没有搜索结果'}
        
        clazz_id = self.course_search.get_classid()
        secret_val = self.course_search.get_secret_val()
        
        if not clazz_id or not secret_val:
            print("❌ 缺少必要的选课参数")
            return {'success': False, 'error': '缺少选课参数'}
        
        print("\n" + "=" * 30)
        print("📚 开始选课...")
        self.logger.info("开始选课")
        
        try:
            # 调用选课功能
            result = self.course_selector.select_course(clazz_id, secret_val)
            
            if result['success']:
                print("🎉 选课成功！")
                self.logger.info("选课成功")
            else:
                print(f"❌ 选课失败: {result['error']}")
                self.logger.error(f"选课失败: {result['error']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 选课过程异常: {e}")
            self.logger.error(f"选课过程异常: {e}")
            return {'success': False, 'error': str(e)}

    def auto_select_course(self, retry_interval=1):
        """自动选课 - 整合搜索和选课（同步版本）"""
        if not self.auth_service:
            login_success = self.login()
            if not login_success:
                return {'success': False, 'error': '登录失败'}
        
        print("\n" + "=" * 30)
        print("🎯 启动自动选课模式")
        self.logger.info(f"启动自动选课模式 - 课程: {self.course_search.get_class_name()}")
        
        try:
            # 调用自动选课功能
            success = self.course_selector.auto_select(
                self.course_search, retry_interval
            )
            
            if success:
                return {'success': True, 'message': '自动选课成功'}
            else:
                return {'success': False, 'error': '自动选课失败'}
                
        except Exception as e:
            print(f"❌ 自动选课异常: {e}")
            self.logger.error(f"自动选课异常: {e}")
            return {'success': False, 'error': str(e)}

    async def auto_select_course_async(self, retry_interval=1, websocket_manager=None, session_id=None):
        """异步自动选课 - 整合搜索和选课（异步版本）"""
        if not self.auth_service:
            login_success = self.login()
            if not login_success:
                return {'success': False, 'error': '登录失败'}
        
        self.logger.info(f"启动异步自动选课模式 - 课程: {self.course_search.get_class_name() if self.course_search else '未知'}")
        
        try:
            # 调用异步自动选课功能
            success = await self.course_selector.auto_select_async(
                self.course_search, retry_interval, websocket_manager, session_id
            )
            
            if success:
                return {'success': True, 'message': '异步自动选课成功'}
            else:
                return {'success': False, 'error': '异步自动选课失败'}
                
        except Exception as e:
            self.logger.error(f"异步自动选课异常: {e}")
            return {'success': False, 'error': str(e)}

    def cleanup(self):
        """清理资源"""
        if self.course_search:
            self.course_search.clear_results()
        
        self.logger.info("课程服务资源清理完成")

    def set_stop_auto_select_flag(self):
        """设置停止自动选课标志"""
        self.stop_auto_select_flag = True
        self.logger.info("停止自动选课标志已设置")

    def should_stop_auto_select(self):
        """检查是否应该停止自动选课"""
        return self.stop_auto_select_flag

    def clear_stop_auto_select_flag(self):
        """清除停止标志"""
        self.stop_auto_select_flag = False
        self.logger.info("停止自动选课标志已清除")