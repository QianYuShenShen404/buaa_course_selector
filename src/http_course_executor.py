#!/usr/bin/env python3
"""
HTTP选课执行器

使用HTTP请求方式执行选课操作，专门为方案二设计。
复用现有的HTTP选课逻辑，但动态构建请求头。

功能特性：
- 动态构建HTTP请求
- 支持多种选课请求格式
- 响应解析和结果验证
- 错误处理和状态码分析

作者: Assistant
版本: 1.0.0
创建时间: 2025-09-12
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import requests

from simplified_config_manager import SimplifiedConfigManager
from playwright_authenticator import AuthInfo


@dataclass
class CourseSelectionResult:
    """选课结果数据类"""
    success: bool
    message: str
    course_id: str
    course_name: str
    timestamp: datetime
    attempt_count: int = 1
    response_data: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    http_status: Optional[int] = None


class HTTPCourseExecutionError(Exception):
    """HTTP选课执行异常"""
    pass


class HTTPCourseExecutor:
    """
    HTTP选课执行器
    
    使用HTTP请求执行高效的选课操作，需要有效的认证信息。
    """
    
    def __init__(self, config_manager: SimplifiedConfigManager, logger: Optional[logging.Logger] = None):
        """
        初始化HTTP选课执行器
        
        Args:
            config_manager: 简化配置管理器实例
            logger: 日志记录器（可选）
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 选课API配置
        self.course_selection_url = "https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/add"
        self.timeout = 10
        
    def select_course(
        self, 
        auth_info: AuthInfo, 
        course_id: Optional[str] = None,
        batch_id: Optional[str] = None
    ) -> CourseSelectionResult:
        """
        执行选课操作
        
        Args:
            auth_info: 认证信息（来自PlaywrightAuthenticator）
            course_id: 课程ID（可选，如果不提供则从配置中读取）
            batch_id: 批次ID（可选，如果不提供则从配置中读取）
            
        Returns:
            CourseSelectionResult对象
            
        Raises:
            HTTPCourseExecutionError: 选课执行失败时抛出
        """
        try:
            start_time = time.time()
            
            # 获取课程信息
            course_info = self._get_course_info(course_id, batch_id)
            
            self.logger.info(f"开始HTTP选课，课程ID: {course_info['course_id'][:10]}...")
            
            # 1. 构建HTTP请求
            request_data = self._build_request(auth_info, course_info)
            
            # 2. 发送选课请求
            response = self._execute_request(request_data)
            
            # 3. 解析响应结果
            result = self._parse_response(response, course_info)
            
            # 添加执行时间信息
            execution_time = time.time() - start_time
            result.timestamp = datetime.now()
            
            if result.success:
                self.logger.info(f"HTTP选课成功，耗时: {execution_time:.2f}s")
            else:
                self.logger.error(f"HTTP选课失败: {result.message}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"HTTP选课执行异常: {str(e)}")
            raise HTTPCourseExecutionError(f"选课执行失败: {str(e)}")
    
    def _get_course_info(self, course_id: Optional[str], batch_id: Optional[str]) -> Dict[str, str]:
        """获取课程信息"""
        try:
            config_course_info = self.config_manager.get_course_info()
            
            return {
                'course_id': course_id or config_course_info.get('course_id', ''),
                'batch_id': batch_id or config_course_info.get('batch_id', ''),
                'course_name': config_course_info.get('course_name', '未指定')
            }
            
        except Exception as e:
            self.logger.error(f"获取课程信息失败: {str(e)}")
            raise HTTPCourseExecutionError(f"课程信息获取失败: {str(e)}")
    
    def _build_request(self, auth_info: AuthInfo, course_info: Dict[str, str]) -> Dict[str, Any]:
        """
        构建HTTP请求数据
        
        Args:
            auth_info: 认证信息
            course_info: 课程信息
            
        Returns:
            请求数据字典
        """
        try:
            # 构建请求头
            headers = {
                'authority': 'byxk.buaa.edu.cn',
                'method': 'POST',
                'path': '/xsxk/elective/buaa/clazz/add',
                'scheme': 'https',
                'accept': 'application/json, text/plain, */*',
                'authorization': auth_info.token,
                'batchid': course_info['batch_id'],
                'content-type': 'application/x-www-form-urlencoded',
                'cookie': auth_info.cookie,
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'origin': 'https://byxk.buaa.edu.cn',
                'referer': 'https://byxk.buaa.edu.cn/xsxk/elective/buaa'
            }
            
            # 获取secretVal，优先级：认证信息 -> 已提取文件 -> API调用 -> 默认值
            secret_val = getattr(auth_info, 'secret_val', '')
            if secret_val and secret_val.strip():
                self.logger.info(f"使用认证信息中的secretVal: {secret_val[:50]}...")
            else:
                self.logger.info("认证信息中缺少secretVal，尝试从已提取文件获取...")
                secret_val = self.get_secret_val_from_extracted()
                
                if secret_val:
                    self.logger.info(f"成功从已提取文件获取secretVal: {secret_val[:50]}...")
                else:
                    self.logger.info("未找到已提取的secretVal，尝试API动态获取...")
                    secret_val = self.get_secret_val_from_api(auth_info)
                    
                    if secret_val:
                        self.logger.info(f"成功通过API动态获取secretVal: {secret_val[:50]}...")
                    else:
                        self.logger.warning("无法获取secretVal，使用空值（可能影响选课成功率）")
                        secret_val = self._generate_default_secret()
            
            # 构造表单数据
            form_data = {
                'clazzType': 'TJKC',  # 推荐课程类型
                'clazzId': course_info['course_id'],
                'secretVal': secret_val
            }
            
            self.logger.debug(f"构建请求完成，课程ID: {course_info['course_id']}")
            
            return {
                'url': self.course_selection_url,
                'headers': headers,
                'data': form_data,
                'timeout': self.timeout
            }
            
        except Exception as e:
            self.logger.error(f"构建HTTP请求失败: {str(e)}")
            raise HTTPCourseExecutionError(f"请求构建失败: {str(e)}")
    
    def _generate_default_secret(self) -> str:
        """
        生成默认的secretVal
        
        注意：实际环境中secretVal通常需要从服务器获取，
        这里提供一个基本的fallback机制。
        """
        self.logger.warning("使用默认secretVal，可能影响选课成功率")
        # 这里可以实现一个基本的secretVal生成逻辑
        # 或者返回空字符串让服务器处理
        return ""
    
    def get_secret_val_from_extracted(self) -> str:
        """
        从已提取的secrets文件中获取最新的secretVal
        这些secretVal是通过快速提取器成功获取的
        
        Returns:
            最新的secretVal值
        """
        try:
            import json
            import os
            from datetime import datetime
            
            secrets_file = "extracted_secrets.json"
            if not os.path.exists(secrets_file):
                self.logger.warning(f"未找到提取的secrets文件: {secrets_file}")
                return ""
            
            with open(secrets_file, 'r', encoding='utf-8') as f:
                secrets_data = json.load(f)
            
            if not secrets_data:
                self.logger.warning("extracted_secrets.json文件为空")
                return ""
            
            # 按时间戳排序，获取最新的secretVal
            sorted_secrets = sorted(secrets_data, key=lambda x: x.get('timestamp', ''), reverse=True)
            latest_secret = sorted_secrets[0]
            
            secret_val = latest_secret.get('value', '')
            timestamp = latest_secret.get('timestamp', '')
            
            if secret_val:
                self.logger.info(f"成功从提取文件获取最新secretVal（时间: {timestamp}）: {secret_val[:50]}...")
                return secret_val
            else:
                self.logger.warning("提取的secrets文件中secretVal为空")
                return ""
                
        except Exception as e:
            self.logger.error(f"从提取文件获取secretVal失败: {str(e)}")
            return ""
    
    def get_secret_val_from_api(self, auth_info: AuthInfo) -> str:
        """
        通过课程列表API获取secretVal（作为fallback机制）
        根据深度分析结果，secretVal包含在课程列表API的响应中
        
        Args:
            auth_info: 认证信息
            
        Returns:
            secretVal值
        """
        try:
            self.logger.info("尝试通过课程列表API获取secretVal（fallback）...")
            
            # 构造课程列表API请求
            list_url = "https://byxk.buaa.edu.cn/xsxk/elective/buaa/clazz/list"
            
            # 构造请求头
            headers = {
                'authority': 'byxk.buaa.edu.cn',
                'method': 'POST', 
                'path': '/xsxk/elective/buaa/clazz/list',
                'scheme': 'https',
                'accept': 'application/json, text/plain, */*',
                'authorization': auth_info.token,
                'content-type': 'application/x-www-form-urlencoded',
                'cookie': auth_info.cookie,
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'origin': 'https://byxk.buaa.edu.cn',
                'referer': 'https://byxk.buaa.edu.cn/xsxk/elective/buaa'
            }
            
            if auth_info.batch_id:
                headers['batchid'] = auth_info.batch_id
            
            # 构造表单数据
            form_data = {
                "campus": "01",
                "courseTypes": "TJKC",
                "pageNumber": "1",
                "pageSize": "10", 
                "orderBy": ""
            }
            
            # 发送POST请求
            response = self.session.post(
                list_url,
                headers=headers,
                data=form_data,
                timeout=15
            )
            
            if response.status_code == 200:
                response_text = response.text
                self.logger.debug(f"课程列表API响应长度: {len(response_text)} 字符")
                
                # 使用正则表达式从响应中提取secretVal
                import re
                secret_match = re.search(r'"secretVal"\s*:\s*"([^"]+)"', response_text)
                if secret_match:
                    secret_val = secret_match.group(1)
                    self.logger.info(f"成功从课程列表API获取secretVal: {secret_val[:50]}...")
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
                            self.logger.info(f"通过模式匹配从API获取secretVal: {secret_val[:50]}...")
                            return secret_val
                    
                    self.logger.warning("课程列表API响应中未找到secretVal字段")
                    self.logger.debug(f"API响应前500字符: {response_text[:500]}")
            else:
                self.logger.error(f"课程列表API请求失败，状态码: {response.status_code}")
                self.logger.debug(f"错误响应: {response.text[:200]}")
            
            return ""
            
        except Exception as e:
            self.logger.error(f"通过API获取secretVal失败: {str(e)}")
            return ""
    
    def _execute_request(self, request_data: Dict[str, Any]) -> requests.Response:
        """
        执行HTTP请求
        
        Args:
            request_data: 请求数据
            
        Returns:
            响应对象
            
        Raises:
            HTTPCourseExecutionError: 请求执行失败时抛出
        """
        try:
            self.logger.debug("发送HTTP选课请求")
            
            # 发送POST请求
            response = self.session.post(
                url=request_data['url'],
                headers=request_data['headers'],
                data=request_data['data'],
                timeout=request_data['timeout'],
                verify=True  # 验证SSL证书
            )
            
            self.logger.debug(f"HTTP响应状态码: {response.status_code}")
            
            # 检查HTTP状态码
            if response.status_code not in [200, 201]:
                self.logger.warning(f"HTTP状态码异常: {response.status_code}")
            
            return response
            
        except requests.exceptions.Timeout:
            error_msg = "HTTP请求超时"
            self.logger.error(error_msg)
            raise HTTPCourseExecutionError(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "HTTP连接失败"
            self.logger.error(error_msg)
            raise HTTPCourseExecutionError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP请求异常: {str(e)}"
            self.logger.error(error_msg)
            raise HTTPCourseExecutionError(error_msg)
        except Exception as e:
            error_msg = f"执行HTTP请求时发生未知异常: {str(e)}"
            self.logger.error(error_msg)
            raise HTTPCourseExecutionError(error_msg)
    
    def _parse_response(self, response: requests.Response, course_info: Dict[str, str]) -> CourseSelectionResult:
        """
        解析HTTP响应
        
        Args:
            response: HTTP响应对象
            course_info: 课程信息
            
        Returns:
            CourseSelectionResult对象
        """
        try:
            # 解析JSON响应
            response_data = None
            response_text = response.text.strip()
            
            if response_text:
                try:
                    response_data = response.json()
                    self.logger.debug("成功解析JSON响应")
                except json.JSONDecodeError:
                    self.logger.debug("响应不是有效的JSON格式")
                    response_data = {'raw_response': response_text}
            
            # 分析响应结果
            success = self._is_success_response(response, response_data)
            message = self._extract_response_message(response, response_data)
            
            return CourseSelectionResult(
                success=success,
                message=message,
                course_id=course_info['course_id'],
                course_name=course_info['course_name'],
                timestamp=datetime.now(),
                response_data=response_data,
                http_status=response.status_code,
                error_details=None if success else f"HTTP {response.status_code}: {response_text}"
            )
            
        except Exception as e:
            error_msg = f"解析HTTP响应失败: {str(e)}"
            self.logger.error(error_msg)
            
            return CourseSelectionResult(
                success=False,
                message=error_msg,
                course_id=course_info['course_id'],
                course_name=course_info['course_name'],
                timestamp=datetime.now(),
                response_data=None,
                http_status=response.status_code if response else None,
                error_details=error_msg
            )
    
    def _is_success_response(self, response: requests.Response, response_data: Optional[Dict]) -> bool:
        """
        判断响应是否表示成功
        
        Args:
            response: HTTP响应对象
            response_data: 解析后的响应数据
            
        Returns:
            是否成功
        """
        try:
            # 1. 检查HTTP状态码
            if response.status_code not in [200, 201]:
                return False
            
            # 2. 检查JSON响应中的成功标识
            if response_data and isinstance(response_data, dict):
                # 常见的成功标识字段
                success_fields = ['success', 'status', 'code', 'result']
                
                for field in success_fields:
                    if field in response_data:
                        value = response_data[field]
                        
                        # 检查不同的成功值格式
                        if isinstance(value, bool):
                            if not value:
                                return False
                        elif isinstance(value, str):
                            if value.lower() in ['false', 'error', 'fail', 'failed']:
                                return False
                        elif isinstance(value, int):
                            if value != 0 and value not in [200, 201]:  # 0通常表示成功，200/201也是成功
                                return False
                
                # 检查错误信息字段
                error_fields = ['error', 'message', 'msg', 'errorMessage']
                for field in error_fields:
                    if field in response_data:
                        error_value = response_data[field]
                        if error_value and str(error_value).strip():
                            # 检查是否包含明显的错误信息
                            error_keywords = ['错误', '失败', 'error', 'fail', '不能', '已满', '冲突']
                            if any(keyword in str(error_value).lower() for keyword in error_keywords):
                                return False
            
            # 3. 检查响应文本内容
            response_text = response.text.lower()
            success_keywords = ['成功', '选课成功', 'success', 'successful']
            fail_keywords = ['失败', '错误', '不能', '已满', 'error', 'failed', 'conflict']
            
            has_success = any(keyword in response_text for keyword in success_keywords)
            has_fail = any(keyword in response_text for keyword in fail_keywords)
            
            if has_fail:
                return False
            elif has_success:
                return True
            
            # 4. 默认情况：如果HTTP状态码是200且没有明显的错误信息，认为成功
            return response.status_code == 200
            
        except Exception as e:
            self.logger.debug(f"判断响应成功状态时出错: {str(e)}")
            return False
    
    def _extract_response_message(self, response: requests.Response, response_data: Optional[Dict]) -> str:
        """
        提取响应消息
        
        Args:
            response: HTTP响应对象
            response_data: 解析后的响应数据
            
        Returns:
            响应消息字符串
        """
        try:
            # 1. 从JSON响应中提取消息
            if response_data and isinstance(response_data, dict):
                message_fields = ['message', 'msg', 'error', 'errorMessage', 'description']
                
                for field in message_fields:
                    if field in response_data and response_data[field]:
                        return str(response_data[field]).strip()
            
            # 2. 使用响应文本
            if response.text and response.text.strip():
                text = response.text.strip()
                # 如果文本太长，截取前100个字符
                if len(text) > 100:
                    text = text[:100] + "..."
                return text
            
            # 3. 根据HTTP状态码生成默认消息
            status_messages = {
                200: "请求成功",
                201: "创建成功", 
                400: "请求参数错误",
                401: "认证失败",
                403: "权限不足",
                404: "资源不存在",
                429: "请求过于频繁",
                500: "服务器内部错误",
                502: "网关错误",
                503: "服务不可用"
            }
            
            return status_messages.get(response.status_code, f"HTTP {response.status_code}")
            
        except Exception as e:
            self.logger.debug(f"提取响应消息时出错: {str(e)}")
            return f"HTTP {response.status_code if response else 'Unknown'}"
    
    def close(self) -> None:
        """关闭HTTP会话"""
        try:
            if self.session:
                self.session.close()
                self.logger.debug("HTTP会话已关闭")
        except Exception as e:
            self.logger.debug(f"关闭HTTP会话时出错: {str(e)}")


# 便利函数
def select_course_with_http(
    config_manager: SimplifiedConfigManager,
    auth_info: AuthInfo,
    course_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> CourseSelectionResult:
    """
    使用HTTP方式选课的便利函数
    
    Args:
        config_manager: 简化配置管理器
        auth_info: 认证信息
        course_id: 课程ID（可选）
        batch_id: 批次ID（可选）
        logger: 日志记录器（可选）
        
    Returns:
        CourseSelectionResult对象
        
    Raises:
        HTTPCourseExecutionError: 选课执行失败时抛出
    """
    executor = HTTPCourseExecutor(config_manager, logger)
    try:
        return executor.select_course(auth_info, course_id, batch_id)
    finally:
        executor.close()
