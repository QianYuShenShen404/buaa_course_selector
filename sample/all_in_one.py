import requests
import re
import json

class BUAA_LoginAndSearch:
    def __init__(self, username, password, batch_id=""):
        self.username = username
        self.password = password
        self.batch_id = batch_id
        self.session = requests.Session()
        self.authorization_token = None

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
        """CAS登录并获取Token"""
        print("🚀 开始登录...")

        try:
            # 步骤1: 访问选课系统，自动跳转到profile页面
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
                    self._setup_api_headers()
                    return self._test_token()
                else:
                    print("⚠️ 未发现Token，重新触发认证")
                    return self._trigger_cas_auth()
            else:
                print("❓ 非预期页面状态")
                return False

        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            return False

    def _get_batch_id_automatically(self):
        """登录后自动获取当前活跃的BatchID"""
        print("🔍 自动获取BatchID...")

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
                                return batch_id
                            else:
                                print("❌ electiveBatchList第一项中没有code字段")
                                print(
                                    f"🔍 第一项内容: {json.dumps(elective_batch_list[0], ensure_ascii=False, indent=2)}")
                                return None
                        else:
                            print("❌ electiveBatchList为空或不存在")
                            print(f"🔍 data字段内容: {list(data.keys())}")
                            print(f"🔍 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)[:1000]}...")
                            return None
                    else:
                        error_msg = result.get('msg') or result.get('message', '未知错误')
                        print(f"❌ studentInfo请求失败: {error_msg}")
                        return None

                except json.JSONDecodeError:
                    print(f"❌ studentInfo响应格式错误")
                    print(f"响应内容: {response.text[:500]}...")
                    return None
            else:
                print(f"❌ studentInfo请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                return None

        except Exception as e:
            print(f"❌ 获取BatchID过程出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _trigger_cas_auth(self):
        """触发CAS认证获取Token"""
        print("🔐 触发CAS认证...")

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

                    # 获取Token
                    cookies = self.session.cookies.get_dict()
                    if 'token' in cookies:
                        self.authorization_token = cookies['token']
                        print(f"🔑 Token获取成功: {self.authorization_token[:50]}...")

                        print("🔄 开始自动获取BatchID...")
                        auto_batch_id = self._get_batch_id_automatically()

                        if auto_batch_id:
                            self.batch_id = auto_batch_id
                            print(f"✅ BatchID自动获取成功: {self.batch_id}")
                        else:
                            print("❌ BatchID自动获取失败")
                            # 可以设置一个默认值或要求用户手动提供
                            print("💡 请检查studentInfo响应结构，或手动指定BatchID")
                            return False

                        self._setup_api_headers()
                        return self._test_token()
                    else:
                        print("❌ 登录成功但未获得Token")
                        return False
                else:
                    print(f"❌ 登录失败，当前URL: {login_response.url}")
                    return False
            else:
                print(f"❌ CAS重定向异常: {response.url}")
                return False

        except Exception as e:
            print(f"❌ CAS认证失败: {e}")
            return False

    def _setup_api_headers(self):
        """设置API访问所需的请求头"""
        print("⚙️ 设置API请求头...")

        # 根据您提供的真实请求头设置
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
        """测试Token是否有效 - 使用正确的接口"""
        print("🧪 测试Token有效性...")

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
                        return True
                    else:
                        error_msg = result.get('message') or result.get('msg', '未知错误')
                        print(f"❌ API返回错误: {error_msg}")
                        return False

                except json.JSONDecodeError:
                    print("❌ JSON解析失败")
                    print(f"原始响应: {response.text[:200]}...")
                    return False
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                return False

        except Exception as e:
            print(f"❌ Token测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search_courses(self, keyword=""):
        """搜索课程 - 使用固定参数+关键词"""
        if keyword:
            print(f"🔍 搜索关键词: {keyword}")
        else:
            print("🔍 获取所有课程...")

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

                        # 尝试获取classid

                        class_id = data.get('rows')[0].get('JXBID')
                        if class_id:
                            print(f"🔑 获取到classid: {class_id}")
                            self.classid = class_id
                        else:
                            print("⚠️ 未发现classid字段")
                            print(f"🔍 data结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                        # 尝试获取secretVal字段内容
                        secret_val = data.get('rows')[0].get('secretVal')
                        if secret_val:
                            print(f"🔑 获取到secretVal: {secret_val}")
                            # 保存secretVal供后续选课使用
                            self.secret_val = secret_val
                        else:
                            print("⚠️ 未发现secretVal字段")
                            # 打印data结构以便调试
                            print(f"🔍 data结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    else:
                        error_msg = result.get('message') or result.get('msg', '未知错误')
                        print(f"❌ 搜索失败: {error_msg}")
                        print(f"🔍 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        return {'success': False, 'error': error_msg}

                except json.JSONDecodeError:
                    print(f"❌ 搜索响应格式错误")
                    print(f"响应内容: {response.text[:500]}...")
                    return {'success': False, 'error': '响应格式错误'}
            else:
                print(f"❌ 搜索请求失败，HTTP状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"❌ 搜索过程出错: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    # 🎯 新增选课功能
    def select_course(self, clazz_id, secret_val, clazz_type="FANKC"):
        """选课功能 - 根据课程ID和secretVal进行选课"""
        print(f"📚 开始选课...")
        print(f"🆔 课程ID: {clazz_id}")
        print(f"🔑 SecretVal: {secret_val[:50]}...")
        print(f"📋 课程类型: {clazz_type}")

        try:
            # 设置选课专用的请求头（注意Content-Type变更）
            select_headers = self.session.headers.copy()
            select_headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',  # 选课用form格式
                'Accept': 'application/json, text/plain, */*',
                'Authorization': self.authorization_token,
                'batchid': self.batch_id,
                'Origin': 'https://byxk.buaa.edu.cn',
                'Referer': f'https://byxk.buaa.edu.cn/xsxk/elective/grablessons?batchId={self.batch_id}',
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
                        return {'success': True, 'message': success_msg}
                    else:
                        error_msg = result.get('message') or result.get('msg', '未知错误')
                        print(f"❌ 选课失败: {error_msg}")
                        return {'success': False, 'error': error_msg}

                except json.JSONDecodeError:
                    print(f"❌ 选课响应格式错误")
                    print(f"响应内容: {response.text[:500]}...")
                    return {'success': False, 'error': '响应格式错误'}
            else:
                print(f"❌ 选课请求失败，HTTP状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}...")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            print(f"❌ 选课过程出错: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def auto_select_by_keyword(self, keyword, max_attempts=5):
        """根据关键词自动搜索并选课"""
        print(f"🎯 自动选课功能启动")
        print(f"🔍 搜索关键词: {keyword}")
        print(f"🔄 最大尝试次数: {max_attempts}")

        for attempt in range(1, max_attempts + 1):
            print(f"\n🔄 第 {attempt} 次尝试...")

            # 搜索课程
            search_result = self.search_courses(keyword=keyword)

            if not search_result.get('success', True):  # 如果搜索失败
                print(f"❌ 第 {attempt} 次搜索失败")
                continue

            # 检查是否有secretVal
            if not hasattr(self, 'secret_val') or not self.secret_val:
                print(f"❌ 第 {attempt} 次未获取到secretVal")
                continue

            # 模拟获取课程ID（这里需要根据实际搜索结果调整）
            # 假设课程ID为固定值，实际使用时需要从搜索结果中提取
            clazz_id = "202520261B060032039001"  # 这个需要从搜索结果中动态获取

            print(f"🎯 尝试选课 - 课程ID: {clazz_id}")

            # 进行选课
            select_result = self.select_course(clazz_id, self.secret_val)

            if select_result['success']:
                print(f"🎉 自动选课成功！")
                return True
            else:
                print(f"❌ 第 {attempt} 次选课失败: {select_result['error']}")

                # 如果是余量不足，可以继续尝试
                if "余量不足" in select_result['error'] or "已满" in select_result['error']:
                    print(f"⏳ 课程已满，等待下次尝试...")
                    import time
                    time.sleep(2)  # 等待2秒再试
                else:
                    print(f"💔 选课失败，原因: {select_result['error']}")
                    break

        print(f"❌ 自动选课失败，已尝试 {max_attempts} 次")
        return False


def main():
    """主程序"""
    print("🎓 北航选课系统 - 登录&搜索版")
    print("=" * 50)

    # 配置信息 - 请修改这里
    USERNAME = "23371020"  # 👈 请修改
    PASSWORD = "cc2005012"  # 👈 请修改
    CLASSNAME = "虚拟现实技术"

    # 创建实例
    searcher = BUAA_LoginAndSearch(USERNAME, PASSWORD)

    # 第一步：登录
    print("=" * 30)
    if not searcher.login():
        print("❌ 登录失败，程序终止")
        return

    # 第二步：搜索课程获取secretVal
    print("\n" + "=" * 30)
    print("🎉 登录成功！现在可以搜索课程了")

    searcher.search_courses(keyword=CLASSNAME)

    # 第三步：选课测试
    if hasattr(searcher, 'secret_val') and searcher.secret_val:
        print("\n" + "=" * 30)
        print("🎯 开始选课测试...")

        result = searcher.select_course(searcher.classid, searcher.secret_val)

        if result['success']:
            print("🎉 手动选课成功！")
        else:
            print(f"❌ 手动选课失败: {result['error']}")

        # 自动选课示例（可选）
        print("\n" + "-" * 40)
        auto_choice = input("是否启动自动选课？(y/n): ").strip().lower()
        if auto_choice == 'y':
            searcher.auto_select_by_keyword(CLASSNAME, max_attempts=10)
    else:
        print("❌ 未获取到secretVal，无法进行选课")


if __name__ == "__main__":
    main()
