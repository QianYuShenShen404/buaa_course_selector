#!/usr/bin/env python3
"""
混合重试管理器

为方案二提供适应性重试机制，支持登录重试和HTTP请求重试两种不同的重试策略。

功能特性：
- 登录操作重试（较慢但稳定）
- HTTP请求重试（快速响应）
- 指数退避算法
- 可配置重试参数
- 统一重试接口

作者: Assistant
版本: 1.0.0
创建时间: 2025-09-12
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

from simplified_config_manager import SimplifiedConfigManager


class OperationType(Enum):
    """操作类型枚举"""
    LOGIN = "login"
    HTTP_REQUEST = "http_request"
    GENERAL = "general"


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_interval: float = 1.0
    backoff_factor: float = 2.0
    max_interval: float = 60.0
    jitter: bool = True


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    result: Any = None
    attempts: int = 0
    total_time: float = 0.0
    last_error: Optional[Exception] = None


class HybridRetryError(Exception):
    """混合重试异常"""
    pass


class HybridRetryManager:
    """
    混合重试管理器
    
    为不同类型的操作提供适应性的重试策略。
    """
    
    def __init__(self, config_manager: Optional[SimplifiedConfigManager] = None, logger: Optional[logging.Logger] = None):
        """
        初始化混合重试管理器
        
        Args:
            config_manager: 简化配置管理器（可选）
            logger: 日志记录器（可选）
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # 预定义的重试配置
        self.retry_configs = {
            OperationType.LOGIN: RetryConfig(
                max_retries=3,
                base_interval=2.0,
                backoff_factor=2.0,
                max_interval=30.0,
                jitter=True
            ),
            OperationType.HTTP_REQUEST: RetryConfig(
                max_retries=5,
                base_interval=0.5,
                backoff_factor=1.5,
                max_interval=10.0,
                jitter=True
            ),
            OperationType.GENERAL: RetryConfig(
                max_retries=3,
                base_interval=1.0,
                backoff_factor=2.0,
                max_interval=30.0,
                jitter=True
            )
        }
        
    async def execute_with_retry_async(
        self,
        operation: Callable,
        operation_type: OperationType = OperationType.GENERAL,
        custom_config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        异步执行操作并重试
        
        Args:
            operation: 要执行的异步操作
            operation_type: 操作类型
            custom_config: 自定义重试配置
            *args: 传递给操作的位置参数
            **kwargs: 传递给操作的关键字参数
            
        Returns:
            RetryResult对象
        """
        config = custom_config or self.retry_configs[operation_type]
        start_time = time.time()
        attempts = 0
        last_error = None
        
        self.logger.info(f"开始执行{operation_type.value}操作，最大重试次数: {config.max_retries}")
        
        for attempt in range(config.max_retries + 1):
            attempts = attempt + 1
            
            try:
                if attempt > 0:
                    self.logger.info(f"第{attempt}次重试{operation_type.value}操作")
                
                # 执行操作
                result = await operation(*args, **kwargs)
                
                total_time = time.time() - start_time
                self.logger.info(f"{operation_type.value}操作成功，尝试次数: {attempts}, 总耗时: {total_time:.2f}s")
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_time=total_time
                )
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"{operation_type.value}操作第{attempts}次尝试失败: {str(e)}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < config.max_retries:
                    delay = self._calculate_delay(attempt, config)
                    self.logger.info(f"等待{delay:.2f}s后重试...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"{operation_type.value}操作失败，已达到最大重试次数")
        
        total_time = time.time() - start_time
        return RetryResult(
            success=False,
            result=None,
            attempts=attempts,
            total_time=total_time,
            last_error=last_error
        )
    
    def execute_with_retry_sync(
        self,
        operation: Callable,
        operation_type: OperationType = OperationType.GENERAL,
        custom_config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        同步执行操作并重试
        
        Args:
            operation: 要执行的同步操作
            operation_type: 操作类型
            custom_config: 自定义重试配置
            *args: 传递给操作的位置参数
            **kwargs: 传递给操作的关键字参数
            
        Returns:
            RetryResult对象
        """
        config = custom_config or self.retry_configs[operation_type]
        start_time = time.time()
        attempts = 0
        last_error = None
        
        self.logger.info(f"开始执行{operation_type.value}操作，最大重试次数: {config.max_retries}")
        
        for attempt in range(config.max_retries + 1):
            attempts = attempt + 1
            
            try:
                if attempt > 0:
                    self.logger.info(f"第{attempt}次重试{operation_type.value}操作")
                
                # 执行操作
                result = operation(*args, **kwargs)
                
                total_time = time.time() - start_time
                self.logger.info(f"{operation_type.value}操作成功，尝试次数: {attempts}, 总耗时: {total_time:.2f}s")
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_time=total_time
                )
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"{operation_type.value}操作第{attempts}次尝试失败: {str(e)}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < config.max_retries:
                    delay = self._calculate_delay(attempt, config)
                    self.logger.info(f"等待{delay:.2f}s后重试...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"{operation_type.value}操作失败，已达到最大重试次数")
        
        total_time = time.time() - start_time
        return RetryResult(
            success=False,
            result=None,
            attempts=attempts,
            total_time=total_time,
            last_error=last_error
        )
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """
        计算重试延迟时间
        
        Args:
            attempt: 当前尝试次数（从0开始）
            config: 重试配置
            
        Returns:
            延迟时间（秒）
        """
        # 指数退避算法
        delay = config.base_interval * (config.backoff_factor ** attempt)
        
        # 限制最大延迟
        delay = min(delay, config.max_interval)
        
        # 添加随机抖动以避免雷群效应
        if config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return max(delay, 0.1)  # 最小延迟0.1秒
    
    def should_retry(self, error: Exception, operation_type: OperationType) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 发生的异常
            operation_type: 操作类型
            
        Returns:
            是否应该重试
        """
        # 定义不应重试的异常类型
        non_retryable_errors = [
            # 认证相关错误
            "认证失败", "用户名或密码错误", "账户被锁定",
            # 权限相关错误
            "权限不足", "访问被拒绝",
            # 参数错误
            "参数错误", "配置错误", "课程ID无效"
        ]
        
        error_message = str(error).lower()
        
        # 检查是否为不可重试的错误
        for non_retryable in non_retryable_errors:
            if non_retryable.lower() in error_message:
                self.logger.info(f"检测到不可重试错误: {non_retryable}")
                return False
        
        # 针对不同操作类型的特殊判断
        if operation_type == OperationType.LOGIN:
            # 登录操作的特殊判断
            login_non_retryable = ["验证码错误", "用户不存在", "密码错误"]
            for error_type in login_non_retryable:
                if error_type in error_message:
                    return False
        
        elif operation_type == OperationType.HTTP_REQUEST:
            # HTTP请求的特殊判断
            import requests
            if isinstance(error, requests.exceptions.RequestException):
                # 某些HTTP状态码不应重试
                if hasattr(error, 'response') and error.response:
                    status_code = error.response.status_code
                    if status_code in [400, 401, 403, 404]:  # 客户端错误
                        return False
        
        return True
    
    def get_retry_config(self, operation_type: OperationType) -> RetryConfig:
        """获取指定操作类型的重试配置"""
        return self.retry_configs.get(operation_type, self.retry_configs[OperationType.GENERAL])
    
    def update_retry_config(self, operation_type: OperationType, config: RetryConfig) -> None:
        """更新指定操作类型的重试配置"""
        self.retry_configs[operation_type] = config
        self.logger.info(f"更新{operation_type.value}的重试配置")


# 便利函数
async def retry_login_operation(
    operation: Callable,
    retry_manager: Optional[HybridRetryManager] = None,
    *args,
    **kwargs
) -> RetryResult:
    """
    重试登录操作的便利函数
    
    Args:
        operation: 登录操作函数
        retry_manager: 重试管理器（可选）
        *args: 传递给操作的位置参数
        **kwargs: 传递给操作的关键字参数
        
    Returns:
        RetryResult对象
    """
    if not retry_manager:
        retry_manager = HybridRetryManager()
    
    return await retry_manager.execute_with_retry_async(
        operation, OperationType.LOGIN, None, *args, **kwargs
    )


def retry_http_operation(
    operation: Callable,
    retry_manager: Optional[HybridRetryManager] = None,
    *args,
    **kwargs
) -> RetryResult:
    """
    重试HTTP操作的便利函数
    
    Args:
        operation: HTTP操作函数
        retry_manager: 重试管理器（可选）
        *args: 传递给操作的位置参数
        **kwargs: 传递给操作的关键字参数
        
    Returns:
        RetryResult对象
    """
    if not retry_manager:
        retry_manager = HybridRetryManager()
    
    return retry_manager.execute_with_retry_sync(
        operation, OperationType.HTTP_REQUEST, None, *args, **kwargs
    )


def create_hybrid_retry_manager(
    config_manager: Optional[SimplifiedConfigManager] = None,
    logger: Optional[logging.Logger] = None
) -> HybridRetryManager:
    """
    创建混合重试管理器的便利函数
    
    Args:
        config_manager: 简化配置管理器（可选）
        logger: 日志记录器（可选）
        
    Returns:
        HybridRetryManager实例
    """
    return HybridRetryManager(config_manager, logger)
