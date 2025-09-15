#!/usr/bin/env python3
"""
Playwright认证器

使用Playwright自动登录北航选课系统并提取认证信息，专门为方案二设计。
复用现有的playwright_auto_login.py中的成熟逻辑。

功能特性：
- 自动SSO登录
- 认证信息提取（Token、Cookie、SecretVal）
- 登录状态管理
- 异常处理和重试机制

作者: Assistant
版本: 1.0.0
创建时间: 2025-09-12
"""

import asyncio
import re
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Response

from simplified_config_manager import SimplifiedConfigManager


@dataclass
class AuthInfo:
    """认证信息数据类"""
    token: str
    cookie: str
    secret_val: str
    batch_id: str
    course_id: str
    timestamp: Optional[float] = None


class PlaywrightAuthenticationError(Exception):
    """Playwright认证异常"""
    pass


class PlaywrightAuthenticator:
    """
    Playwright认证器
    
    使用Playwright自动登录获取认证信息，为HTTP选课器提供最新的认证数据。
    """
    
    def __init__(self, config_manager: SimplifiedConfigManager, logger: Optional[logging.Logger] = None):
        """
        初始化Playwright认证器
        
        Args:
            config_manager: 简化配置管理器实例
            logger: 日志记录器（可选）
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Playwright组件
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 认证状态
        self.auth_info: Optional[AuthInfo] = None
        self.network_responses = []
        
        # URL配置 - 使用改进的登录URL，登录后直接进入选课页面
        self.sso_login_url = "https://sso.buaa.edu.cn/login?service=https%3A%2F%2Fbyxk.buaa.edu.cn%2Fxsxk%2Flogin%3F_targetUrl%3Dbase64aHR0cHM6Ly9ieXhrLmJ1YWEuZWR1LmNuL3hzeGsvZWxlY3RpdmUvYnVhYQ%3D%3D"
        self.course_selection_url = "https://byxk.buaa.edu.cn/xsxk/elective/buaa"
        
        # secretVal收集
        self.found_secrets: List[Dict[str, Any]] = []
        
    async def authenticate(self, username: str, password: str) -> AuthInfo:
        """
        执行自动登录并获取认证信息
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            AuthInfo对象，包含认证信息
            
        Raises:
            PlaywrightAuthenticationError: 认证失败时抛出
        """
        try:
            self.logger.info(f"开始Playwright自动认证，用户名: {username[:3]}***")
            
            # 1. 设置浏览器环境
            await self._setup_browser()
            
            # 2. 设置网络监听
            self._setup_network_monitoring()
            
            # 3. 执行SSO登录
            await self._perform_sso_login(username, password)
            
            # 4. 提取认证信息
            auth_info = await self._extract_auth_info()
            
            if not auth_info:
                raise PlaywrightAuthenticationError("认证信息提取失败")
            
            self.auth_info = auth_info
            self.logger.info("Playwright认证成功，认证信息提取完成")
            
            return auth_info
            
        except Exception as e:
            self.logger.error(f"Playwright认证失败: {str(e)}")
            raise PlaywrightAuthenticationError(f"认证过程失败: {str(e)}")
        finally:
            await self.cleanup()
    
    async def _setup_browser(self) -> None:
        """设置浏览器环境"""
        try:
            browser_config = self.config_manager.get_browser_config()
            
            self.playwright = await async_playwright().start()
            
            # 启动浏览器（强制headless模式，因为这是后台认证）
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # 认证器总是使用headless模式
                slow_mo=browser_config.get('slow_mo', 500),  # 认证时可以快一些
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--allow-running-insecure-content'
                ]
            )
            
            # 创建浏览器上下文
            self.context = await self.browser.new_context(
                viewport={
                    'width': browser_config.get('viewport_width', 1280), 
                    'height': browser_config.get('viewport_height', 720)
                },
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                java_script_enabled=True,
                ignore_https_errors=True
            )
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 设置超时
            timeout = browser_config.get('timeout', 30000)
            self.page.set_default_timeout(timeout)
            
            self.logger.debug("浏览器环境设置完成")
            
        except Exception as e:
            self.logger.error(f"浏览器环境设置失败: {str(e)}")
            raise
    
    def _setup_network_monitoring(self) -> None:
        """设置网络监听以捕获认证信息和secretVal"""
        try:
            self.network_responses = []
            
            async def handle_response(response: Response):
                """处理网络响应"""
                try:
                    url = response.url
                    # 记录相关的API请求
                    if any(keyword in url for keyword in [
                        '/xsxk/web/now', 
                        '/xsxk/web/studentInfo',
                        '/xsxk/auth/captcha',
                        '/xsxk/elective/user',
                        '/xsxk/elective/buaa/clazz/list'  # 添加课程列表API
                    ]):
                        self.network_responses.append(response)
                        self.logger.debug(f"捕获到认证请求: {url}")
                        
                        # 实时捕获secretVal
                        if response.status == 200 and 'json' in response.headers.get('content-type', '').lower():
                            text = await response.text()
                            if 'secretVal' in text:
                                secrets = re.findall(r'"secretVal"[:\s]*"([^"]+)"', text)
                                for secret in secrets:
                                    if len(secret) > 10:
                                        self.found_secrets.append({
                                            'value': secret,
                                            'source': f'API: {url}',
                                            'timestamp': datetime.now().timestamp()
                                        })
                                        self.logger.info(f"实时捕获到secretVal: {secret[:50]}...")
                                        
                except Exception as e:
                    self.logger.debug(f"处理网络响应时出错: {str(e)}")
            
            # 监听响应
            self.page.on("response", handle_response)
            
            self.logger.debug("网络监听设置完成")
            
        except Exception as e:
            self.logger.error(f"网络监听设置失败: {str(e)}")
            raise
    
    async def _perform_sso_login(self, username: str, password: str) -> None:
        """执行SSO登录"""
        try:
            # 1. 导航到SSO登录页面
            self.logger.info(f"导航到SSO登录页面: {self.sso_login_url}")
            await self.page.goto(self.sso_login_url)
            await asyncio.sleep(2)
            
            # 2. 在iframe中填写登录表单
            await self._fill_login_form_in_iframe(username, password)
            
            # 3. 提交登录表单
            await self._submit_login_form()
            
            # 4. 处理登录后确认页面 - 使用改进的方法
            await self._handle_post_login_confirmation_improved()
            
            # 5. 触发课程列表API以获取secretVal
            await self._trigger_course_list_api()
            
            self.logger.info("SSO登录流程完成")
            
        except Exception as e:
            self.logger.error(f"SSO登录失败: {str(e)}")
            raise
    
    async def _fill_login_form_in_iframe(self, username: str, password: str) -> None:
        """在iframe中填写登录表单"""
        try:
            self.logger.info("在iframe中填写登录表单")
            
            # 等待iframe出现
            await self.page.wait_for_selector("#loginIframe", timeout=10000)
            
            # 获取iframe的content_frame
            iframe_element = self.page.locator("#loginIframe")
            content_frame = iframe_element.content_frame
            
            if not content_frame:
                raise PlaywrightAuthenticationError("无法获取iframe的content_frame")
            
            # 填写用户名
            username_input = content_frame.get_by_role("textbox", name="请输入学工号")
            await username_input.click()
            await username_input.fill(username)
            
            # 填写密码
            password_input = content_frame.get_by_role("textbox", name="请输入密码")
            await password_input.click()
            await password_input.fill(password)
            
            self.logger.info("登录表单填写完成")
            
        except Exception as e:
            self.logger.error(f"iframe中填写登录表单失败: {str(e)}")
            raise
    
    async def _submit_login_form(self) -> None:
        """提交登录表单"""
        try:
            self.logger.info("提交登录表单")
            
            # 获取iframe的content_frame
            iframe_element = self.page.locator("#loginIframe")
            content_frame = iframe_element.content_frame
            
            if not content_frame:
                raise PlaywrightAuthenticationError("无法获取iframe的content_frame")
            
            # 点击登录按钮
            login_button = content_frame.get_by_role("button", name="登录")
            await login_button.click()
            
            # 等待登录处理
            await asyncio.sleep(3)
            
            self.logger.info("登录表单提交完成")
            
        except Exception as e:
            self.logger.error(f"提交登录表单失败: {str(e)}")
            raise
    
    async def _handle_post_login_confirmation_improved(self) -> None:
        """处理登录后确认页面 - 使用改进的XPath定位"""
        try:
            self.logger.info("处理登录后确认页面")
            
            # 等待页面加载
            # await asyncio.sleep(2)
            
            # 使用XPath定位确定按钮
            try:
                # 使用精确的XPath定位确定按钮
                confirm_button = self.page.locator('//html//body//div[1]//div[4]//div//div[3]//span//button[1]')
                await confirm_button.click(timeout=10000)
                self.logger.info("使用XPath点击确定按钮成功")
            except Exception as e:
                self.logger.debug(f"XPath点击失败，尝试其他方法: {str(e)}")
                # 备用方法
                try:
                    confirm_button = self.page.get_by_role("button", name="确定")
                    await confirm_button.click(timeout=5000)
                    self.logger.info("使用role定位点击确定按钮成功")
                except:
                    self.logger.warning("确定按钮未找到，可能已自动跳转")
            
            # 点击选课按钮（如果存在）
            try:
                await asyncio.sleep(2)
                course_button = self.page.get_by_role("button", name="选课")
                await course_button.click(timeout=5000)
                self.logger.info("点击选课按钮成功")
            except:
                self.logger.debug("选课按钮未找到")
            
            # 关闭弹窗（如果存在）
            try:
                await asyncio.sleep(1)
                popup_close = self.page.locator("#popContainer").get_by_role("img")
                await popup_close.click(timeout=3000)
                self.logger.info("关闭弹窗成功")
            except:
                self.logger.debug("没有弹窗需要关闭")
            
            # 等待页面跳转稳定
            await asyncio.sleep(2)
            
            current_url = self.page.url
            self.logger.info(f"当前页面URL: {current_url}")
            
            # 检查是否成功到达选课页面
            if "elective" in current_url or "选课" in await self.page.title():
                self.logger.info("成功到达选课页面")
            else:
                self.logger.warning(f"可能未正确到达选课页面，当前URL: {current_url}")
            
        except Exception as e:
            self.logger.error(f"处理登录后确认页面失败: {str(e)}")
            raise
    
    async def _trigger_course_list_api(self) -> None:
        """触发课程列表API以获取secretVal"""
        try:
            self.logger.info("触发课程列表API以获取secretVal...")
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 手动调用课程列表API
            response = await self.context.request.post(
                "https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/list",
                data={
                    "campus": "01",
                    "courseTypes": "TJKC",
                    "pageNumber": "1",
                    "pageSize": "20",
                    "orderBy": ""
                }
            )
            
            if response.status == 200:
                text = await response.text()
                self.logger.info(f"API响应长度: {len(text)} 字符")
                
                # 搜索secretVal
                secrets = re.findall(r'"secretVal"[:\s]*"([^"]+)"', text)
                for secret in secrets:
                    if len(secret) > 10:
                        self.found_secrets.append({
                            'value': secret,
                            'source': '手动API调用',
                            'timestamp': datetime.now().timestamp()
                        })
                        self.logger.info(f"手动API调用发现secretVal: {secret[:50]}...")
                
                # 保存响应以便调试
                with open("manual_api_response.json", "w", encoding="utf-8") as f:
                    f.write(text)
                self.logger.debug("API响应已保存到 manual_api_response.json")
            else:
                self.logger.warning(f"API调用失败，状态码: {response.status}")
                
        except Exception as e:
            self.logger.error(f"触发课程列表API失败: {str(e)}")
            # 不抛出异常，因为可能已经通过网络监听获取到secretVal
    
    async def _navigate_to_course_selection(self) -> None:
        """导航到选课页面以触发认证信息提取"""
        try:
            self.logger.info("导航到选课页面以获取更多认证信息")
            
            # 访问选课页面
            await self.page.goto(self.course_selection_url)
            await asyncio.sleep(3)
            
            # 检查页面是否加载成功
            if self.page.url.startswith("https://byxk.buaa.edu.cn"):
                self.logger.info(f"成功访问选课页面: {self.course_selection_url}")
            else:
                self.logger.warning(f"选课页面访问异常，当前URL: {self.page.url}")
            
        except Exception as e:
            self.logger.error(f"导航到选课页面失败: {str(e)}")
            # 不抛出异常，因为可能已经有足够的认证信息了
    
    async def _extract_auth_info(self) -> Optional[AuthInfo]:
        """提取认证信息"""
        try:
            self.logger.info("开始提取认证信息")
            
            # 方法1：从网络监听中提取基础认证信息
            auth_info = await self._extract_from_network_responses()
            if not auth_info:
                # 方法2：从JavaScript执行中提取
                auth_info = await self._extract_from_javascript()
            if not auth_info:
                # 方法3：从页面元素中提取
                auth_info = await self._extract_from_page_elements()
            
            if auth_info:
                self.logger.info("成功提取基础认证信息")
                
                # 从收集的secrets中获取最新的secretVal
                if self.found_secrets:
                    # 获取最新的secretVal
                    latest_secret = max(self.found_secrets, key=lambda x: x['timestamp'])
                    auth_info.secret_val = latest_secret['value']
                    self.logger.info(f"使用捕获的secretVal: {auth_info.secret_val[:50]}...")
                else:
                    # 备用方法
                    self.logger.info("尝试备用方法获取secretVal...")
                    secret_val = await self._get_secret_val_fast_method()
                    if secret_val:
                        auth_info.secret_val = secret_val
                        self.logger.info(f"备用方法获取secretVal: {secret_val[:50]}...")
                    else:
                        # 如果快速方法失败，尝试原有方法
                        self.logger.info("快速方法失败，尝试备用方法...")
                        secret_val = await self._get_secret_val()
                        if secret_val:
                            auth_info.secret_val = secret_val
                            self.logger.info(f"通过备用方法获取secretVal: {secret_val[:50]}...")
                        else:
                            self.logger.warning("所有方法都未能获取secretVal")
                            auth_info.secret_val = ''  # 设置空值
                
                return auth_info
            else:
                self.logger.error("所有认证信息提取方法都失败了")
                return None
            
        except Exception as e:
            self.logger.error(f"提取认证信息失败: {str(e)}")
            return None
    
    async def _get_secret_val(self, course_id: str = "") -> str:
        """
        获取secretVal参数
        根据深度分析结果，secretVal来自于课程列表API的响应
        
        Args:
            course_id: 课程ID（可选）
            
        Returns:
            secretVal值
        """
        try:
            self.logger.info("尝试通过API获取secretVal...")
            
            # 方法1: 通过直接从页面JavaScript中获取已加载的secretVal
            secret_val = await self._get_secret_val_from_page_js()
            if secret_val:
                self.logger.info(f"从页面JavaScript中找到secretVal: {secret_val[:50]}...")
                return secret_val
            
            # 方法2: 通过调用课程列表API获取secretVal（根据深度分析结果）
            secret_val = await self._get_secret_val_from_api()
            if secret_val:
                self.logger.info(f"从API响应中找到secretVal: {secret_val[:50]}...")
                return secret_val
            
            # 方法2: 从页面HTML中查找（备用方法）
            page_content = await self.page.content()
            secret_match = re.search(r'secretVal["\']?\s*[:=]\s*["\']([^"\']*)["\']', page_content)
            if secret_match:
                secret_val = secret_match.group(1)
                self.logger.info(f"从HTML中找到secretVal: {secret_val[:50]}...")
                return secret_val
            
            # 方法3: 执行JavaScript获取（备用方法）
            secret_script = """
            () => {
                // 查找页面中的secretVal
                const secretInputs = document.querySelectorAll('input[name="secretVal"], [data-secret]');
                if (secretInputs.length > 0) {
                    return secretInputs[0].value || secretInputs[0].getAttribute('data-secret');
                }
                
                // 查找JavaScript变量
                if (window.secretVal) {
                    return window.secretVal;
                }
                
                // 查找其他可能的变量
                for (const key in window) {
                    if (key.includes('secret') || key.includes('Secret')) {
                        const val = window[key];
                        if (typeof val === 'string' && val.length > 10) {
                            return val;
                        }
                    }
                }
                
                return '';
            }
            """
            
            secret_val = await self.page.evaluate(secret_script)
            if secret_val:
                self.logger.info(f"从JavaScript中找到secretVal: {secret_val[:50]}...")
                return secret_val
            
            self.logger.warning(f"所有方法都未能获取到secretVal")
            return ''
            
        except Exception as e:
            self.logger.error(f"获取secretVal失败: {str(e)}")
            return ''
    
    async def _get_secret_val_fast_method(self) -> str:
        """
        使用快速提取器的成功方法获取secretVal
        基于分析，通过调用课程列表API获取secretVal
        
        Returns:
            secretVal值
        """
        try:
            self.logger.info("使用快速方法获取secretVal...")
            
            # 设置网络响应监听器来捕获secretVal
            captured_secrets = []
            
            async def capture_secret(response):
                try:
                    if (response.status == 200 and 
                        'json' in response.headers.get('content-type', '').lower() and
                        'clazz/list' in response.url):
                        
                        text = await response.text()
                        if 'secretVal' in text:
                            secrets = re.findall(r'"secretVal"[:\\s]*"([^"]+)"', text)
                            for secret in secrets:
                                if len(secret) > 50:  # 只考虑长度足够的secretVal
                                    captured_secrets.append(secret)
                                    self.logger.info(f"捕获到secretVal: {secret[:50]}...")
                except Exception as e:
                    self.logger.debug(f"处理响应时出错: {e}")
            
            # 添加响应监听器
            self.page.on('response', capture_secret)
            
            try:
                # 1. 先导航到选课页面（如果还未到达）
                current_url = self.page.url
                if 'elective/buaa' not in current_url:
                    await self.page.goto('https://byxk.buaa.edu.cn/xsxk/elective/buaa', wait_until='networkidle')
                    await asyncio.sleep(2)
                
                # 2. 手动调用课程列表API
                response = await self.context.request.post(
                    "https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/list",
                    data={
                        "campus": "01",
                        "courseTypes": "TJKC",
                        "pageNumber": "1",
                        "pageSize": "20",
                        "orderBy": ""
                    }
                )
                
                if response.status == 200:
                    text = await response.text()
                    self.logger.debug(f"课程列表API响应长度: {len(text)}字符")
                    
                    # 从手动API调用的响应中提取secretVal
                    secrets = re.findall(r'"secretVal"[:\\s]*"([^"]+)"', text)
                    for secret in secrets:
                        if len(secret) > 50:
                            self.logger.info(f"从手动API调用中获取secretVal: {secret[:50]}...")
                            return secret
                
                # 等待可能的自动触发的API调用
                await asyncio.sleep(1)
                
                # 3. 返回捕获到的secretVal
                if captured_secrets:
                    return captured_secrets[-1]  # 返回最新的
                
            finally:
                # 移除监听器
                try:
                    self.page.remove_listener('response', capture_secret)
                except:
                    pass
            
            self.logger.warning("快速方法未能获取到secretVal")
            return ''
            
        except Exception as e:
            self.logger.error(f"快速方法获取secretVal失败: {str(e)}")
            return ''
    
    async def _get_secret_val_from_page_js(self) -> str:
        """
        从页面JavaScript中获取已加载的secretVal
        在选课页面加载后，secretVal可能已经存在在页面的JavaScript变量中
        
        Returns:
            secretVal值
        """
        try:
            self.logger.info("从页面JavaScript中搜索secretVal...")
            
            # 执行深度的JavaScript搜索
            search_script = """
            () => {
                // 方法1: 检查全局变量
                if (window.secretVal) return window.secretVal;
                if (window.SECRET_VAL) return window.SECRET_VAL;
                if (window._secretVal) return window._secretVal;
                
                // 方法2: 检查Vue实例中的secretVal
                if (window.Vue && window.Vue.$data) {
                    const vueData = window.Vue.$data;
                    if (vueData.secretVal) return vueData.secretVal;
                    if (vueData.secret_val) return vueData.secret_val;
                }
                
                // 方法3: 检查所有window属性
                for (const key in window) {
                    if (key.toLowerCase().includes('secret')) {
                        const val = window[key];
                        if (typeof val === 'string' && val.length > 50 && /^[A-Za-z0-9+/=]+$/.test(val)) {
                            return val;
                        }
                    }
                }
                
                // 方法4: 从页面元素中搜索
                const hiddenInputs = document.querySelectorAll('input[type="hidden"]');
                for (const input of hiddenInputs) {
                    if (input.name && input.name.toLowerCase().includes('secret')) {
                        return input.value;
                    }
                }
                
                // 方法5: 从所有表单中搜索
                const allInputs = document.querySelectorAll('input, textarea');
                for (const input of allInputs) {
                    if (input.value && input.value.length > 50 && /^[A-Za-z0-9+/=]+$/.test(input.value)) {
                        return input.value;
                    }
                }
                
                // 方法6: 从页面文本中搜索
                const pageText = document.documentElement.innerHTML;
                const secretMatch = pageText.match(/["']secretVal["']\\s*:\\s*["']([A-Za-z0-9+/=]{50,})["']/);
                if (secretMatch) return secretMatch[1];
                
                return null;
            }
            """
            
            secret_val = await self.page.evaluate(search_script)
            if secret_val:
                self.logger.info(f"从页面JavaScript中成功找到secretVal: {secret_val[:50]}...")
                return secret_val
            else:
                self.logger.debug("在页面JavaScript中未找到secretVal")
                return ""
                
        except Exception as e:
            self.logger.error(f"从页面JavaScript获取secretVal失败: {str(e)}")
            return ""
    
    async def _get_secret_val_from_api(self) -> str:
        """
        通过调用课程列表API获取secretVal
        根据深度分析，secretVal在 /xsxk/elective/buaa/clazz/list 的响应中
        
        Returns:
            secretVal值
        """
        try:
            self.logger.info("通过课程列表API获取secretVal...")
            
            # 获取必要的认证信息
            cookies = await self._get_current_cookies()
            if not cookies:
                self.logger.error("无法获取cookies，跳过API调用")
                return ""
            
            # 构造API请求
            api_url = "https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/list"
            
            # 构造请求数据
            form_data = {
                "campus": "01",
                "courseTypes": "TJKC", 
                "pageNumber": "1",
                "pageSize": "10",
                "orderBy": ""
            }
            
            # 使用Playwright的request context发送POST请求
            response = await self.context.request.post(
                api_url,
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            
            if response.status == 200:
                response_text = await response.text()
                self.logger.debug(f"API响应长度: {len(response_text)} 字符")
                
                # 使用正则表达式从响应中提取secretVal
                secret_match = re.search(r'"secretVal"\s*:\s*"([^"]+)"', response_text)
                if secret_match:
                    secret_val = secret_match.group(1)
                    self.logger.info(f"成功从API响应中提取secretVal: {secret_val[:50]}...")
                    return secret_val
                else:
                    # 尝试其他可能的格式
                    secret_patterns = [
                        r'secretVal["\']?\s*[:=]\s*["\']([^"\'\n]+)["\']',
                        r'"secret_val"\s*:\s*"([^"]+)"',
                        r'secret[Vv]al["\']?\s*[:=]\s*["\']([^"\'\n]+)["\']'
                    ]
                    
                    for pattern in secret_patterns:
                        match = re.search(pattern, response_text, re.IGNORECASE)
                        if match:
                            secret_val = match.group(1)
                            self.logger.info(f"通过模式匹配找到secretVal: {secret_val[:50]}...")
                            return secret_val
                    
                    self.logger.warning("API响应中未找到secretVal字段")
                    # 可选：记录响应的前500个字符用于调试
                    self.logger.debug(f"API响应前500字符: {response_text[:500]}")
            else:
                self.logger.error(f"API请求失败，状态码: {response.status}")
                error_text = await response.text()
                self.logger.debug(f"错误响应: {error_text[:200]}")
            
            return ""
            
        except Exception as e:
            self.logger.error(f"通过API获取secretVal失败: {str(e)}")
            return ""
    
    async def _extract_from_network_responses(self) -> Optional[AuthInfo]:
        """从网络响应中提取认证信息"""
        try:
            token = None
            cookie = None
            
            # 检查所有响应的请求头
            for response in self.network_responses:
                try:
                    # 从请求头中提取token
                    request = response.request
                    if request and hasattr(request, 'headers'):
                        auth_header = request.headers.get('authorization', '')
                        if auth_header and auth_header.startswith('eyJ'):
                            token = auth_header
                            self.logger.debug("从请求头提取到Token")
                    
                    # 从响应的Set-Cookie中提取cookie信息
                    response_headers = await response.all_headers()
                    set_cookie = response_headers.get('set-cookie', '')
                    if set_cookie and 'token=' in set_cookie:
                        # 这里可以进一步解析cookie
                        self.logger.debug("从响应头发现Cookie信息")
                
                except Exception as e:
                    self.logger.debug(f"处理响应时出错: {str(e)}")
                    continue
            
            # 如果从网络响应中获取了token，尝试获取完整的cookie
            if token:
                cookie_str = await self._get_current_cookies()
                if cookie_str:
                    course_info = self.config_manager.get_course_info()
                    course_id = course_info.get('course_id', '')
                    
                    # 获取secretVal
                    secret_val = await self._get_secret_val(course_id)
                    
                    return AuthInfo(
                        token=token,
                        cookie=cookie_str,
                        secret_val=secret_val,
                        batch_id=course_info.get('batch_id', ''),
                        course_id=course_id
                    )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"从网络响应提取认证信息失败: {str(e)}")
            return None
    
    async def _extract_from_javascript(self) -> Optional[AuthInfo]:
        """从JavaScript执行中提取认证信息"""
        try:
            auth_script = """
            () => {
                // 尝试从localStorage或sessionStorage获取token
                const token = localStorage.getItem('token') || 
                            localStorage.getItem('authorization') ||
                            sessionStorage.getItem('token') ||
                            sessionStorage.getItem('authorization');
                
                // 获取cookies
                const cookies = document.cookie;
                
                // 尝试提取token从cookie
                let cookieToken = '';
                const tokenMatch = cookies.match(/token=([^;]+)/);
                if (tokenMatch) {
                    cookieToken = tokenMatch[1];
                }
                
                return { 
                    token: token || cookieToken, 
                    cookies: cookies 
                };
            }
            """
            
            result = await self.page.evaluate(auth_script)
            
            if result and result.get('token'):
                course_info = self.config_manager.get_course_info()
                course_id = course_info.get('course_id', '')
                
                # 获取secretVal
                secret_val = await self._get_secret_val(course_id)
                
                return AuthInfo(
                    token=result['token'],
                    cookie=result.get('cookies', ''),
                    secret_val=secret_val,
                    batch_id=course_info.get('batch_id', ''),
                    course_id=course_id
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"从JavaScript提取认证信息失败: {str(e)}")
            return None
    
    async def _extract_from_page_elements(self) -> Optional[AuthInfo]:
        """从页面元素中提取认证信息"""
        try:
            # 这个方法主要是为了完整性，实际上认证信息通常不在页面元素中
            # 如果有特殊的隐藏字段包含认证信息，可以在这里提取
            
            # 尝试获取当前cookies作为fallback
            cookie_str = await self._get_current_cookies()
            
            if cookie_str and 'token=' in cookie_str:
                # 从cookie中提取token
                token_match = re.search(r'token=([^;]+)', cookie_str)
                if token_match:
                    token = token_match.group(1)
                    
                    course_info = self.config_manager.get_course_info()
                    course_id = course_info.get('course_id', '')
                    
                    # 获取secretVal
                    secret_val = await self._get_secret_val(course_id)
                    
                    return AuthInfo(
                        token=token,
                        cookie=cookie_str,
                        secret_val=secret_val,
                        batch_id=course_info.get('batch_id', ''),
                        course_id=course_id
                    )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"从页面元素提取认证信息失败: {str(e)}")
            return None
    
    async def _get_current_cookies(self) -> str:
        """获取当前页面的所有cookies"""
        try:
            cookies = await self.context.cookies()
            cookie_pairs = []
            
            for cookie in cookies:
                cookie_pairs.append(f"{cookie['name']}={cookie['value']}")
            
            return '; '.join(cookie_pairs)
            
        except Exception as e:
            self.logger.debug(f"获取cookies失败: {str(e)}")
            return ""
    
    async def cleanup(self) -> None:
        """清理浏览器资源"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.logger.debug("浏览器资源清理完成")
            
        except Exception as e:
            self.logger.debug(f"清理浏览器资源时出错: {str(e)}")
    
    def get_auth_info(self) -> Optional[AuthInfo]:
        """获取当前的认证信息"""
        return self.auth_info
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.auth_info is not None


# 便利函数
async def authenticate_with_playwright(
    config_manager: SimplifiedConfigManager,
    username: Optional[str] = None,
    password: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> AuthInfo:
    """
    使用Playwright进行认证的便利函数
    
    Args:
        config_manager: 简化配置管理器
        username: 用户名（可选，如果不提供则从配置中读取）
        password: 密码（可选，如果不提供则从配置中读取）
        logger: 日志记录器（可选）
        
    Returns:
        AuthInfo对象
        
    Raises:
        PlaywrightAuthenticationError: 认证失败时抛出
    """
    # 如果没有提供用户名密码，从配置中读取
    if not username or not password:
        config_username, config_password = config_manager.get_user_credentials()
        username = username or config_username
        password = password or config_password
    
    authenticator = PlaywrightAuthenticator(config_manager, logger)
    return await authenticator.authenticate(username, password)
