#!/usr/bin/env python3
"""
快速secretVal提取器

基于之前的分析，这个工具专注于从最可能的位置快速提取secretVal：
1. 模拟完整的选课页面交互流程
2. 监控选课按钮点击前后的网络请求 
3. 分析页面JavaScript中的动态生成逻辑
4. 提取实际选课时使用的secretVal

作者: Assistant  
版本: 1.0.0
创建时间: 2025-09-15
"""

import sys
import os
import json
import asyncio
import re
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from playwright.async_api import async_playwright
    from simplified_config_manager import SimplifiedConfigManager
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    sys.exit(1)


class QuickSecretExtractor:
    """快速secretVal提取器"""
    
    def __init__(self, config_path: str = "../config_simple.json"):
        self.config_path = config_path
        self.config_manager = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        self.found_secrets = []
        self.network_data = []
        
    async def initialize(self):
        """初始化"""
        try:
            print("🚀 初始化快速secretVal提取器...")
            
            # 加载配置
            self.config_manager = SimplifiedConfigManager(self.config_path)
            self.config_manager.load_config()
            
            # 启动Playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                slow_mo=1000
            )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            
            self.page = await self.context.new_page()
            
            # 监控网络请求
            self.setup_network_monitoring()
            
            print("✅ 初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            return False
    
    def setup_network_monitoring(self):
        """设置网络监控"""
        async def on_response(response):
            try:
                if response.status == 200 and 'json' in response.headers.get('content-type', '').lower():
                    text = await response.text()
                    self.network_data.append({
                        'url': response.url,
                        'text': text,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 立即搜索secretVal
                    if 'secretVal' in text:
                        secrets = re.findall(r'"secretVal"[:\s]*"([^"]+)"', text)
                        for secret in secrets:
                            if len(secret) > 10:
                                self.found_secrets.append({
                                    'value': secret,
                                    'source': f'API: {response.url}',
                                    'timestamp': datetime.now().isoformat()
                                })
                                print(f"🎯 在API响应中发现secretVal: {secret}")
                                
            except Exception as e:
                print(f"处理响应时出错: {e}")
        
        self.page.on('response', on_response)
    
    async def perform_login(self):
        """执行登录"""
        try:
            print("🔐 开始SSO登录...")
            
            creds = self.config_manager.get_user_credentials()
            
            # 访问SSO登录页面
            await self.page.goto("https://sso.buaa.edu.cn/login?service=https%3A%2F%2Fbyxk.buaa.edu.cn%2Fxsxk%2Flogin%3F_targetUrl%3Dbase64aHR0cHM6Ly9ieXhrLmJ1YWEuZWR1LmNuL3hzeGsvZWxlY3RpdmUvYnVhYQ%3D%3D")
            
            await asyncio.sleep(3)
            
            # 在iframe中填写表单
            iframe_element = self.page.locator("#loginIframe")
            content_frame = iframe_element.content_frame
            
            if content_frame:
                # 填写用户名密码
                await content_frame.get_by_role("textbox", name="请输入学工号").fill(creds['username'])
                await content_frame.get_by_role("textbox", name="请输入密码").fill(creds['password'])
                
                # 点击登录
                await content_frame.get_by_role("button", name="登录").click()

                await self.page.locator('//html//body//div[1]//div[4]//div//div[3]//span//button[1]').click()

                await self.page.get_by_role("button", name="选课").click()

                await self.page.locator("#popContainer").get_by_role("img").click()
                # 处理确认页面
                # try:
                #     confirm_button = self.page.get_by_role("button", name="确定")
                #     await confirm_button.click()
                #     await asyncio.sleep(3)
                # except:
                #     print("⚠️ 登录确认页面未找到")
                
                print("✅ SSO登录完成")
                return True
            else:
                print("❌ 无法找到登录iframe")
                return False
                
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            return False
    async def trigger_course_list_api(self):
        """触发课程列表API以获取secretVal"""
        try:
            print("📋 触发课程列表API...")
            
            # 尝试点击查询或搜索按钮来触发API
            search_selectors = [
                'button:has-text("查询")',
                'button:has-text("搜索")',
                'input[type="submit"]',
                '.search-btn',
                '.btn-search',
                '[onclick*="search"]'
            ]
            
            for selector in search_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if elements:
                        print(f"🖱️ 点击: {selector}")
                        await elements[0].click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # 如果没有找到按钮，尝试手动触发API
            print("🔄 手动触发课程列表API...")
            
            # 获取当前cookies和headers
            cookies = await self.context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            
            # 手动调用API
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
                print(f"📄 API响应长度: {len(text)} 字符")
                
                # 搜索secretVal
                secrets = re.findall(r'"secretVal"[:\s]*"([^"]+)"', text)
                for secret in secrets:
                    if len(secret) > 10:
                        self.found_secrets.append({
                            'value': secret,
                            'source': 'Manual API Call',
                            'timestamp': datetime.now().isoformat()
                        })
                        print(f"🎯 手动API调用发现secretVal: {secret}")
                
                # 保存响应
                with open("manual_api_response.json", "w", encoding="utf-8") as f:
                    f.write(text)
                print("💾 API响应已保存到 manual_api_response.json")
                
                return True
            else:
                print(f"❌ API调用失败，状态码: {response.status}")
                return False
                
        except Exception as e:
            print(f"❌ 触发API失败: {e}")
            return False
    
    async def simulate_course_selection_click(self):
        """模拟点击选课按钮"""
        try:
            print("🖱️ 模拟选课按钮点击...")
            
            course_info = self.config_manager.get_course_info()
            target_course_id = course_info['course_id']
            
            # 等待页面加载完成
            await asyncio.sleep(3)
            
            # 寻找选课相关的按钮
            selection_selectors = [
                'button:has-text("选课")',
                'button:has-text("报名")',
                'button:has-text("选择")',
                '.btn-select',
                '.select-btn',
                f'[data-course-id="{target_course_id}"]',
                '[onclick*="select"]',
                '[onclick*="add"]'
            ]
            
            for selector in selection_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if elements:
                        print(f"🎯 找到选课按钮: {selector}")
                        
                        # 在点击前后监控网络请求
                        print("📡 监控选课网络请求...")
                        
                        # 点击选课按钮
                        await elements[0].click()
                        await asyncio.sleep(3)
                        
                        print("✅ 选课按钮点击完成")
                        break
                        
                except Exception as e:
                    print(f"点击 {selector} 时出错: {e}")
                    continue
            
            return True
            
        except Exception as e:
            print(f"❌ 模拟选课点击失败: {e}")
            return False
    
    async def extract_page_secrets(self):
        """从页面中提取secretVal"""
        try:
            print("🔍 从页面提取secretVal...")
            
            # JavaScript搜索脚本
            search_script = """
            () => {
                const results = [];
                
                // 1. 搜索全局变量
                for (const key in window) {
                    try {
                        const value = window[key];
                        if (typeof value === 'string' && value.length > 30 && value.length < 200) {
                            if (key.toLowerCase().includes('secret') || 
                                key.toLowerCase().includes('token') || 
                                key.toLowerCase().includes('val')) {
                                results.push({source: `window.${key}`, value: value});
                            }
                        }
                    } catch (e) {}
                }
                
                // 2. 搜索隐藏输入框
                document.querySelectorAll('input[type="hidden"]').forEach(input => {
                    if (input.value && input.value.length > 20) {
                        results.push({source: `hidden input: ${input.name || input.id}`, value: input.value});
                    }
                });
                
                // 3. 搜索脚本内容
                document.querySelectorAll('script').forEach(script => {
                    if (script.textContent) {
                        const content = script.textContent;
                        
                        // 常见的secretVal模式
                        const patterns = [
                            /secretVal["\s]*[:=]["\s]*([A-Za-z0-9+/=]{20,})/gi,
                            /"secretVal"["\s]*:["\s]*"([^"]{20,})"/gi,
                            /SECRET_VAL["\s]*[:=]["\s]*([A-Za-z0-9+/=]{20,})/gi
                        ];
                        
                        patterns.forEach(pattern => {
                            let match;
                            while ((match = pattern.exec(content)) !== null) {
                                results.push({source: 'script', value: match[1]});
                            }
                        });
                    }
                });
                
                return results;
            }
            """
            
            search_results = await self.page.evaluate(search_script)
            
            if search_results:
                print(f"🎯 页面搜索发现 {len(search_results)} 个结果:")
                for result in search_results:
                    value = result['value']
                    if len(value) > 10:
                        self.found_secrets.append({
                            'value': value,
                            'source': f"页面: {result['source']}",
                            'timestamp': datetime.now().isoformat()
                        })
                        print(f"  - {result['source']}: {value}")
            
            return True
            
        except Exception as e:
            print(f"❌ 页面提取失败: {e}")
            return False
    
    def generate_summary(self):
        """生成提取结果摘要"""
        print("\n" + "="*80)
        print("📊 secretVal提取结果摘要")
        print("="*80)
        
        if self.found_secrets:
            print(f"🎉 发现 {len(self.found_secrets)} 个潜在的secretVal:")
            
            # 去重并按来源分组
            unique_secrets = {}
            for secret in self.found_secrets:
                value = secret['value']
                if value not in unique_secrets:
                    unique_secrets[value] = secret
            
            for i, (value, info) in enumerate(unique_secrets.items(), 1):
                print(f"\n{i}. 值: {value}")
                print(f"   来源: {info['source']}")
                print(f"   时间: {info['timestamp']}")
                print(f"   长度: {len(value)} 字符")
                
                # 验证值的有效性
                if re.match(r'^[A-Za-z0-9+/=]{20,}$', value):
                    print("   ✅ 格式看起来有效")
                else:
                    print("   ⚠️ 格式可能异常")
            
            # 保存到文件
            with open("extracted_secrets.json", "w", encoding="utf-8") as f:
                json.dump(list(unique_secrets.values()), f, ensure_ascii=False, indent=2)
            print(f"\n💾 结果已保存到 extracted_secrets.json")
            
            # 推荐最可能的secretVal
            if unique_secrets:
                recommended = max(unique_secrets.values(), 
                    key=lambda x: len(x['value']) if 'API' in x['source'] else len(x['value']) // 2)
                print(f"\n🎯 推荐使用: {recommended['value']}")
                print(f"   理由: 来自 {recommended['source']}")
                
        else:
            print("❌ 未发现任何secretVal")
            print("\n💡 可能的原因:")
            print("   1. secretVal是动态生成的，需要在选课时实时获取")
            print("   2. secretVal藏在加密或混淆的代码中")
            print("   3. 需要特定的用户操作才能触发生成")
        
        print("\n📄 网络请求记录:")
        print(f"   总请求数: {len(self.network_data)}")
        for data in self.network_data[-5:]:  # 显示最近5个
            print(f"   - {data['url']}")
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass


async def main():
    """主函数"""
    print("⚡ 快速secretVal提取器")
    print("="*80)
    
    extractor = QuickSecretExtractor()
    
    try:
        # 初始化
        if not await extractor.initialize():
            return
        
        # 执行登录
        if not await extractor.perform_login():
            print("❌ 登录失败，无法继续")
            return

        # 从页面提取
        await extractor.extract_page_secrets()
        
        # 触发API调用
        await extractor.trigger_course_list_api()
        
        # 模拟选课点击
        await extractor.simulate_course_selection_click()
        
        # 再次提取（选课后可能会有新的secretVal）
        await extractor.extract_page_secrets()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断提取")
    except Exception as e:
        print(f"❌ 提取过程异常: {e}")
    finally:
        # 生成摘要
        extractor.generate_summary()
        
        # 清理资源
        await extractor.cleanup()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
