#!/usr/bin/env python3
"""
混合选课器

方案二的核心协调器，整合Playwright认证和HTTP选课，提供完整的选课解决方案。

功能特性：
- 自动认证获取最新Token/Cookie
- 高效HTTP选课执行
- 智能重试机制
- 完整错误处理
- 状态管理和监控

作者: Assistant
版本: 1.0.0
创建时间: 2025-09-12
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from simplified_config_manager import SimplifiedConfigManager, SimplifiedConfigValidationError
from playwright_authenticator import PlaywrightAuthenticator, PlaywrightAuthenticationError, AuthInfo
from http_course_executor import HTTPCourseExecutor, HTTPCourseExecutionError, CourseSelectionResult
from hybrid_retry_manager import HybridRetryManager, OperationType, RetryResult


@dataclass
class HybridSelectionResult:
    """混合选课结果"""
    success: bool
    message: str
    course_id: str
    course_name: str
    timestamp: datetime
    
    # 认证信息
    auth_success: bool
    auth_attempts: int
    auth_time: float
    
    # 选课信息
    selection_attempts: int
    selection_time: float
    total_time: float
    
    # 详细信息
    auth_error: Optional[str] = None
    selection_error: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


class HybridCourseSelectorError(Exception):
    """混合选课器异常"""
    pass


class HybridCourseSelector:
    """
    混合选课器
    
    协调Playwright认证和HTTP选课的完整流程，为用户提供无缝的选课体验。
    """
    
    def __init__(self, config_path: str = "config_simple.json"):
        """
        初始化混合选课器
        
        Args:
            config_path: 简化配置文件路径
        """
        # 核心组件
        self.config_manager = SimplifiedConfigManager(config_path)
        self.logger = self._setup_logger()
        self.retry_manager = HybridRetryManager(self.config_manager, self.logger)
        
        # 子组件（延迟初始化）
        self.playwright_authenticator: Optional[PlaywrightAuthenticator] = None
        self.http_executor: Optional[HTTPCourseExecutor] = None
        
        # 状态信息
        self.current_auth_info: Optional[AuthInfo] = None
        self.is_initialized = False
        
        self.logger.info("混合选课器初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        try:
            # 加载配置以获取日志设置
            config = self.config_manager.load_config()
            logging_config = config['logging']
            
            # 创建logger
            logger = logging.getLogger('HybridCourseSelector')
            logger.setLevel(getattr(logging, logging_config['level'].upper()))
            
            # 避免重复添加handler
            if not logger.handlers:
                # 创建文件handler
                import os
                from pathlib import Path
                
                log_file = Path(logging_config['file_path'])
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                handler = logging.FileHandler(log_file, encoding='utf-8')
                formatter = logging.Formatter(logging_config['format'])
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                
                # 添加控制台handler
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
            
            return logger
            
        except Exception as e:
            # 如果日志设置失败，使用基本的logger
            logger = logging.getLogger('HybridCourseSelector')
            logger.setLevel(logging.INFO)
            return logger
    
    def initialize(self) -> None:
        """初始化所有子组件"""
        try:
            if self.is_initialized:
                return
            
            self.logger.info("开始初始化混合选课器子组件")
            
            # 加载配置
            config = self.config_manager.load_config()
            
            # 初始化子组件
            self.playwright_authenticator = PlaywrightAuthenticator(self.config_manager, self.logger)
            self.http_executor = HTTPCourseExecutor(self.config_manager, self.logger)
            
            self.is_initialized = True
            self.logger.info("混合选课器子组件初始化完成")
            
        except Exception as e:
            error_msg = f"混合选课器初始化失败: {str(e)}"
            self.logger.error(error_msg)
            raise HybridCourseSelectorError(error_msg)
    
    async def execute_course_selection(
        self,
        course_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> HybridSelectionResult:
        """
        执行完整的混合选课流程
        
        Args:
            course_id: 课程ID（可选，从配置读取）
            batch_id: 批次ID（可选，从配置读取）  
            username: 用户名（可选，从配置读取）
            password: 密码（可选，从配置读取）
            
        Returns:
            HybridSelectionResult对象
        """
        start_time = time.time()
        
        try:
            self.logger.info("开始执行混合选课流程")
            
            # 初始化组件
            self.initialize()
            
            # 获取配置信息
            course_info = self._get_course_info(course_id, batch_id)
            user_credentials = self._get_user_credentials(username, password)
            
            self.logger.info(f"目标课程: {course_info['course_name']} ({course_info['course_id'][:15]}...)")
            
            # 阶段1：认证获取
            auth_result = await self._perform_authentication(user_credentials)
            
            if not auth_result.success:
                return HybridSelectionResult(
                    success=False,
                    message=f"认证失败: {auth_result.last_error}",
                    course_id=course_info['course_id'],
                    course_name=course_info['course_name'],
                    timestamp=datetime.now(),
                    auth_success=False,
                    auth_attempts=auth_result.attempts,
                    auth_time=auth_result.total_time,
                    selection_attempts=0,
                    selection_time=0.0,
                    total_time=time.time() - start_time,
                    auth_error=str(auth_result.last_error) if auth_result.last_error else None
                )
            
            self.current_auth_info = auth_result.result
            
            # 阶段2：HTTP选课
            selection_result = self._perform_http_selection(course_info)
            
            total_time = time.time() - start_time
            
            # 从RetryResult中提取CourseSelectionResult
            if selection_result.success and selection_result.result:
                # 成功时，result包含CourseSelectionResult对象
                course_selection = selection_result.result
                return HybridSelectionResult(
                    success=course_selection.success,
                    message=course_selection.message,
                    course_id=course_info['course_id'],
                    course_name=course_info['course_name'],
                    timestamp=datetime.now(),
                    auth_success=True,
                    auth_attempts=auth_result.attempts,
                    auth_time=auth_result.total_time,
                    selection_attempts=selection_result.attempts,
                    selection_time=selection_result.total_time,
                    total_time=total_time,
                    response_data=course_selection.response_data,
                    selection_error=course_selection.error_details if not course_selection.success else None
                )
            else:
                # 失败时，使用RetryResult的错误信息
                error_msg = str(selection_result.last_error) if selection_result.last_error else "选课执行失败"
                return HybridSelectionResult(
                    success=False,
                    message=f"选课失败: {error_msg}",
                    course_id=course_info['course_id'],
                    course_name=course_info['course_name'],
                    timestamp=datetime.now(),
                    auth_success=True,
                    auth_attempts=auth_result.attempts,
                    auth_time=auth_result.total_time,
                    selection_attempts=selection_result.attempts,
                    selection_time=selection_result.total_time,
                    total_time=total_time,
                    response_data=None,
                    selection_error=error_msg
                )
            
        except Exception as e:
            error_msg = f"混合选课流程异常: {str(e)}"
            self.logger.error(error_msg)
            
            return HybridSelectionResult(
                success=False,
                message=error_msg,
                course_id=course_id or "unknown",
                course_name="unknown",
                timestamp=datetime.now(),
                auth_success=False,
                auth_attempts=0,
                auth_time=0.0,
                selection_attempts=0,
                selection_time=0.0,
                total_time=time.time() - start_time
            )
    
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
            raise HybridCourseSelectorError(f"课程信息获取失败: {str(e)}")
    
    def _get_user_credentials(self, username: Optional[str], password: Optional[str]) -> Tuple[str, str]:
        """获取用户凭据"""
        try:
            if username and password:
                return username, password
            
            config_user_credentials = self.config_manager.get_user_credentials()
            
            return (
                username or config_user_credentials.get('username', ''),
                password or config_user_credentials.get('password', '')
            )
            
        except Exception as e:
            self.logger.error(f"获取用户凭据失败: {str(e)}")
            raise HybridCourseSelectorError(f"用户凭据获取失败: {str(e)}")
    
    async def _perform_authentication(self, credentials: Tuple[str, str]) -> RetryResult:
        """执行认证操作"""
        username, password = credentials
        
        self.logger.info(f"开始认证流程，用户名: {username[:3]}***")
        
        async def auth_operation():
            return await self.playwright_authenticator.authenticate(username, password)
        
        return await self.retry_manager.execute_with_retry_async(
            auth_operation,
            OperationType.LOGIN
        )
    
    def _perform_http_selection(self, course_info: Dict[str, str]) -> RetryResult:
        """执行HTTP选课操作"""
        self.logger.info(f"开始HTTP选课，课程: {course_info['course_name']}")
        
        def selection_operation():
            return self.http_executor.select_course(
                self.current_auth_info,
                course_info['course_id'],
                course_info['batch_id']
            )
        
        return self.retry_manager.execute_with_retry_sync(
            selection_operation,
            OperationType.HTTP_REQUEST
        )
    
    def get_auth_info(self) -> Optional[AuthInfo]:
        """获取当前认证信息"""
        return self.current_auth_info
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.current_auth_info is not None
    
    def get_course_info(self) -> Dict[str, str]:
        """获取课程信息"""
        try:
            return self.config_manager.get_course_info()
        except Exception:
            return {}
    
    def test_connection(self) -> bool:
        """测试网络连接"""
        try:
            import requests
            response = requests.get("https://www.baidu.com", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self) -> None:
        """清理资源"""
        try:
            if self.http_executor:
                self.http_executor.close()
            
            # 清理认证信息
            self.current_auth_info = None
            
            self.logger.info("混合选课器资源清理完成")
            
        except Exception as e:
            self.logger.debug(f"清理资源时出错: {str(e)}")


# 便利函数
def create_hybrid_course_selector(config_path: str = "config_simple.json") -> HybridCourseSelector:
    """
    创建混合选课器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        HybridCourseSelector实例
    """
    return HybridCourseSelector(config_path)


async def select_course_hybrid(
    config_path: str = "config_simple.json",
    course_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> HybridSelectionResult:
    """
    混合选课的便利函数
    
    Args:
        config_path: 配置文件路径
        course_id: 课程ID（可选）
        batch_id: 批次ID（可选）
        username: 用户名（可选）
        password: 密码（可选）
        
    Returns:
        HybridSelectionResult对象
    """
    selector = create_hybrid_course_selector(config_path)
    try:
        return await selector.execute_course_selection(course_id, batch_id, username, password)
    finally:
        selector.close()
