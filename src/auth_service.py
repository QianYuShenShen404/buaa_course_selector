import requests
import re
import json
try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger


class AuthService:
    """认证服务类 - CAS登录、Session管理、Token获取"""
    
    def __init__(self, username, password, batch_id=""):
        """
        初始化认证服务
        
        Args:
            username: 用户名 (学号)
            password: 密码
            batch_id: 批次ID (可选，会自动获取)
        """
        self.username = username
        self.password = password
        self.batch_id = batch_id
        self.session = requests.Session()
        self.authorization_token = None
        self.logger = get_logger()

        # 设置基础请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Sec-Ch-Ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })

    def login(self):
        """执行CAS登录并获取Token"""
        print("🚀 开始登录...")
        self.logger.info("开始执行登录流程")

        try:
            # 访问选课系统，自动跳转到profile页面
            initial_url = f"https://byxk.buaa.edu.cn/xsxk/elective/grablessons?"
            response = self.session.get(initial_url, allow_redirects=True)

            print(f"📊 当前页面: {response.url}")

            # 检查当前状态
            if 'profile/index.html' in response.url:
                print("✅ 已在profile页面")
                # 检查是否已有token
                cookies = self.session.cookies.get_dict()
                if 'token' in cookies:
                    print("✅ 发现现有Token")
                    self.authorization_token = cookies['token']
                    print(f"🔑 Token: {self.authorization_token[:50]}...")
                    self.logger.info("发现现有Token，准备验证")
                    self._setup_api_headers()
                    return self._test_token()
                else:
                    print("⚠️ 未发现Token，重新触发认证")
                    self.logger.info("未发现Token，重新触发认证")
                    return self._trigger_cas_auth()
            else:
                print("❓ 非预期页面状态")
                self.logger.warning(f"非预期页面状态: {response.url}")
                return False

        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            self.logger.error(f"登录过程出错: {e}")
            return False

    def _get_batch_id_automatically(self):
        """登录后自动获取当前活跃的BatchID"""
        print("🔍 自动获取BatchID...")
        self.logger.info("开始自动获取BatchID")

        try:
            # 设置studentInfo请求的Headers
            student_info_headers = {
                'Authorization': self.authorization_token,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://byxk.buaa.edu.cn',
                'Referer': 'https://byxk.buaa.edu.cn/xsxk/profile/index.html',
                'Priority': 'u=1, i'
            }

            # 发送studentInfo请求
            print("📤 请求学生信息...")
            response = self.session.post(
                'https://byxk.buaa.edu.cn/xsxk/web/studentInfo',
                data={'token': self.authorization_token},
                headers=student_info_headers
            )

            print(f"📊 StudentInfo响应状态: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📊 响应结构检查: {list(result.keys())}")

                    if result.get('code') == 200:
                        data = result.get('data', {})

                        # 🎯 关键：从electiveBatchList中获取BatchID
                        elective_batch_list = data.get('student').get('electiveBatchList', [])

                        if elective_batch_list and len(elective_batch_list) > 0:
                            # 获取第一个批次的code作为BatchID
                            batch_id = elective_batch_list[0].get('code')

                            if batch_id:
                                print(f"🎯 成功获取BatchID: {batch_id}")
                                self.logger.info(f"成功获取BatchID: {batch_id}")
                                return batch_id
                            else:
                                print("❌ electiveBatchList第一项中没有code字段")
                                print(
                                    f"🔍 第一项内容: {json.dumps(elective_batch_list[0], ensure_ascii=False, indent=2)}")
                                self.logger.error("electiveBatchList第一项中没有code字段")
                                return None
                        else:
                            print("❌ electiveBatchList为空或不存在")
                            print(f"🔍 data字段内容: {list(data.keys())}")
                            print(f"🔍 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)[:1000]}...")
                            self.logger.error("electiveBatchList为空或不存在")
                            return None
                    else:
                        error_msg = result.get('msg') or result.get('message', '未知错误')
                        print(f"❌ studentInfo请求失败: {error_msg}")
                        self.logger.error(f"studentInfo请求失败: {error_msg}")
                        return None

                except json.JSONDecodeError:
                    print(f"❌ studentInfo响应格式错误")
                    print(f"响应内容: {response.text[:500]}...")
                    self.logger.error("studentInfo响应格式错误")
                    return None
            else:
                print(f"❌ studentInfo请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                self.logger.error(f"studentInfo请求失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 获取BatchID过程出错: {e}")
            self.logger.error(f"获取BatchID过程出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _trigger_cas_auth(self):
        """触发CAS认证获取Token"""
        print("🔐 触发CAS认证...")
        self.logger.info("触发CAS认证")

        try:
            # 访问CAS认证端点
            cas_url = 'https://byxk.buaa.edu.cn/xsxk/auth/cas'
            response = self.session.get(cas_url, allow_redirects=True)

            if 'sso.buaa.edu.cn' in response.url:
                print("🔐 进入CAS登录页面")

                # 提取execution参数
                execution_match = re.search(r'name="execution" value="([^"]+)"', response.text)
                if not execution_match:
                    print("❌ 无法提取execution参数")
                    self.logger.error("无法提取execution参数")
                    return False

                execution = execution_match.group(1)
                print("📋 提取登录参数成功")

                # 提交登录表单
                login_data = {
                    'username': self.username,
                    'password': self.password,
                    'execution': execution,
                    'submit': '登录',
                    'type': 'username_password',
                    '_eventId': 'submit'
                }

                print("📤 提交登录信息...")
                login_response = self.session.post(response.url, data=login_data, allow_redirects=True)

                if 'profile/index.html' in login_response.url:
                    print("✅ CAS登录成功！")
                    self.logger.info("CAS登录成功")

                    # 获取Token
                    cookies = self.session.cookies.get_dict()
                    if 'token' in cookies:
                        self.authorization_token = cookies['token']
                        print(f"🔑 Token获取成功: {self.authorization_token[:50]}...")
                        self.logger.info("Token获取成功")

                        print("🔄 开始自动获取BatchID...")
                        auto_batch_id = self._get_batch_id_automatically()

                        if auto_batch_id:
                            self.batch_id = auto_batch_id
                            print(f"✅ BatchID自动获取成功: {self.batch_id}")
                            self.logger.info(f"BatchID自动获取成功: {self.batch_id}")
                        else:
                            print("❌ BatchID自动获取失败")
                            # 可以设置一个默认值或要求用户手动提供
                            print("💡 请检查studentInfo响应结构，或手动指定BatchID")
                            self.logger.error("BatchID自动获取失败")
                            return False

                        self._setup_api_headers()
                        return self._test_token()
                    else:
                        print("❌ 登录成功但未获得Token")
                        self.logger.error("登录成功但未获得Token")
                        return False
                else:
                    print(f"❌ 登录失败，当前URL: {login_response.url}")
                    self.logger.error(f"登录失败，当前URL: {login_response.url}")
                    return False
            else:
                print(f"❌ CAS重定向异常: {response.url}")
                self.logger.error(f"CAS重定向异常: {response.url}")
                return False

        except Exception as e:
            print(f"❌ CAS认证失败: {e}")
            self.logger.error(f"CAS认证失败: {e}")
            return False

    def _setup_api_headers(self):
        """设置API访问所需的请求头"""
        print("⚙️ 设置API请求头...")
        self.logger.info("设置API请求头")

        # 根据提供的真实请求头设置
        self.session.headers.update({
            'Authorization': self.authorization_token,
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',  # 关键：JSON格式
            'Origin': 'https://byxk.buaa.edu.cn',
            'Referer': f'https://byxk.buaa.edu.cn/xsxk/elective/grablessons?batchId={self.batch_id}',
            'batchid': self.batch_id,  # 关键：添加batchid头
            'Priority': 'u=1, i'
        })

        print("✅ API请求头设置完成")

    def _test_token(self):
        """测试Token是否有效"""
        print("🧪 测试Token有效性...")
        self.logger.info("测试Token有效性")

        try:
            # 使用固定参数进行测试（不带关键词）
            test_data = {
                "teachingClassType": "FANKC",
                "pageNumber": 1,
                "pageSize": 10,
                "orderBy": "",
                "campus": "1",
                "SFCT": "0"
            }

            response = self.session.post(
                'https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/list',
                json=test_data
            )

            print(f"📊 API响应状态: {response.status_code}")
            print(f"📊 响应类型: {response.headers.get('content-type', '')}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"📊 API响应: {json.dumps(result, ensure_ascii=False, indent=2)[:300]}...")

                    if result.get('code') == 200 or result.get('success') == True:
                        print("✅ Token验证成功！")
                        self.logger.info("Token验证成功")
                        return True
                    else:
                        error_msg = result.get('message') or result.get('msg', '未知错误')
                        print(f"❌ API返回错误: {error_msg}")
                        self.logger.error(f"API返回错误: {error_msg}")
                        return False

                except json.JSONDecodeError:
                    print("❌ JSON解析失败")
                    print(f"原始响应: {response.text[:200]}...")
                    self.logger.error("JSON解析失败")
                    return False
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                self.logger.error(f"HTTP错误: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Token测试失败: {e}")
            self.logger.error(f"Token测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_session(self):
        """获取已认证的session"""
        return self.session

    def get_token(self):
        """获取授权token"""
        return self.authorization_token

    def get_batch_id(self):
        """获取批次ID"""
        return self.batch_id

    def is_authenticated(self):
        """检查是否已认证"""
        return self.authorization_token is not None and self.batch_id is not None