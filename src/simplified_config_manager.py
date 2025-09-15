#!/usr/bin/env python3
"""
简化配置管理器

专门为双版本选课脚本设计的简化配置管理器，只需要用户配置基础信息：
- 用户凭据（用户名和密码）
- 课程信息（课程ID、批次ID、课程名称）
- 浏览器配置（headless模式、超时等）
- 日志配置

作者: Assistant
版本: 1.0.0
创建时间: 2025-09-12
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class SimplifiedConfigValidationError(Exception):
    """简化配置验证异常"""
    pass


class SimplifiedConfigManager:
    """
    简化配置管理器
    
    为方案二和方案三提供简化的配置管理，移除复杂的认证信息配置需求。
    """
    
    # 必需的配置字段定义
    REQUIRED_FIELDS = {
        'user_credentials': ['username', 'password'],
        'course_info': ['course_id', 'batch_id'],
        'browser_config': ['headless', 'timeout'],
        'logging': ['level', 'file_path']
    }
    
    def __init__(self, config_path: str = "config_simple.json"):
        """
        初始化简化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config_data: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(__name__)
        
    def load_config(self) -> Dict[str, Any]:
        """
        加载简化配置文件
        
        Returns:
            配置数据字典
            
        Raises:
            SimplifiedConfigValidationError: 配置文件无效时抛出
            FileNotFoundError: 配置文件不存在时抛出
        """
        try:
            # 检查配置文件是否存在
            if not self.config_path.exists():
                raise FileNotFoundError(
                    f"简化配置文件不存在: {self.config_path.absolute()}\n"
                    f"请先创建配置文件。可参考 config_simple.json 模板。"
                )
            
            # 加载JSON配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # 验证配置结构
            self._validate_config()
            
            # 应用默认值
            self._apply_defaults()
            
            self.logger.info(f"简化配置文件加载成功: {self.config_path}")
            return self.config_data
            
        except json.JSONDecodeError as e:
            raise SimplifiedConfigValidationError(f"配置文件JSON格式错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"加载简化配置文件失败: {str(e)}")
            raise
    
    def _validate_config(self) -> None:
        """
        验证简化配置文件结构和必需字段
        
        Raises:
            SimplifiedConfigValidationError: 配置验证失败时抛出
        """
        if not isinstance(self.config_data, dict):
            raise SimplifiedConfigValidationError("配置文件根节点必须是JSON对象")
        
        # 检查顶级分区
        for section_name, required_fields in self.REQUIRED_FIELDS.items():
            if section_name not in self.config_data:
                raise SimplifiedConfigValidationError(f"缺少必需的配置分区: {section_name}")
            
            section = self.config_data[section_name]
            if not isinstance(section, dict):
                raise SimplifiedConfigValidationError(f"配置分区 {section_name} 必须是对象")
            
            # 检查必需字段
            for field in required_fields:
                if field not in section:
                    raise SimplifiedConfigValidationError(
                        f"配置分区 {section_name} 缺少必需字段: {field}"
                    )
        
        # 特殊验证逻辑
        self._validate_user_credentials()
        self._validate_course_info()
        self._validate_browser_config()
        self._validate_logging_config()
    
    def _validate_user_credentials(self) -> None:
        """验证用户凭据"""
        credentials = self.config_data['user_credentials']
        
        # 验证用户名和密码不为空
        username = credentials.get('username', '').strip()
        password = credentials.get('password', '').strip()
        
        if not username:
            raise SimplifiedConfigValidationError("用户名不能为空")
        if not password:
            raise SimplifiedConfigValidationError("密码不能为空")
        
        # 检查是否仍有占位符
        if username.startswith('PLACEHOLDER_') or password.startswith('PLACEHOLDER_'):
            raise SimplifiedConfigValidationError(
                "用户名或密码包含占位符，请替换为实际的用户名和密码"
            )
    
    def _validate_course_info(self) -> None:
        """验证课程信息"""
        course_info = self.config_data['course_info']
        
        # 验证课程ID和批次ID不为空
        course_id = course_info.get('course_id', '').strip()
        batch_id = course_info.get('batch_id', '').strip()
        
        if not course_id:
            raise SimplifiedConfigValidationError("课程ID不能为空")
        if not batch_id:
            raise SimplifiedConfigValidationError("批次ID不能为空")
        
        # 检查是否仍有占位符
        if (course_id.startswith('PLACEHOLDER_') or 
            batch_id.startswith('PLACEHOLDER_')):
            raise SimplifiedConfigValidationError(
                "课程ID或批次ID包含占位符，请替换为实际值"
            )
    
    def _validate_browser_config(self) -> None:
        """验证浏览器配置"""
        browser_config = self.config_data['browser_config']
        
        # 验证headless字段类型
        headless = browser_config.get('headless')
        if not isinstance(headless, bool):
            raise SimplifiedConfigValidationError("browser_config.headless 必须是布尔值 (true/false)")
        
        # 验证timeout字段
        timeout = browser_config.get('timeout')
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise SimplifiedConfigValidationError("browser_config.timeout 必须是大于0的数字")
    
    def _validate_logging_config(self) -> None:
        """验证日志配置"""
        logging_config = self.config_data['logging']
        
        # 验证日志级别
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        level = logging_config.get('level', '').upper()
        if level not in valid_levels:
            raise SimplifiedConfigValidationError(
                f"无效的日志级别: {level}。支持的级别: {', '.join(valid_levels)}"
            )
        
        # 确保日志目录存在
        log_path = Path(logging_config.get('file_path', ''))
        log_dir = log_path.parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"创建日志目录: {log_dir}")
            except Exception as e:
                raise SimplifiedConfigValidationError(f"无法创建日志目录 {log_dir}: {str(e)}")
    
    def _apply_defaults(self) -> None:
        """应用默认配置值"""
        # 为browser_config添加默认值
        browser_config = self.config_data['browser_config']
        browser_config.setdefault('slow_mo', 1000)
        browser_config.setdefault('viewport_width', 1280)
        browser_config.setdefault('viewport_height', 720)
        
        # 为course_info添加默认值
        course_info = self.config_data['course_info']
        course_info.setdefault('course_name', '未指定')
        
        # 为logging添加默认值
        logging_config = self.config_data['logging']
        logging_config.setdefault('max_size_mb', 100)
        logging_config.setdefault('backup_count', 5)
        logging_config.setdefault('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def get_user_credentials(self) -> Dict[str, str]:
        """
        获取用户凭据
        
        Returns:
            包含用户凭据的字典
            
        Raises:
            RuntimeError: 配置未加载时抛出
        """
        if self.config_data is None:
            raise RuntimeError("配置未加载，请先调用 load_config()")
        
        return self.config_data['user_credentials'].copy()
    
    def get_course_info(self) -> Dict[str, str]:
        """
        获取课程信息
        
        Returns:
            包含课程信息的字典
            
        Raises:
            RuntimeError: 配置未加载时抛出
        """
        if self.config_data is None:
            raise RuntimeError("配置未加载，请先调用 load_config()")
        
        return self.config_data['course_info'].copy()
    
    def get_browser_config(self) -> Dict[str, Any]:
        """
        获取浏览器配置
        
        Returns:
            包含浏览器配置的字典
            
        Raises:
            RuntimeError: 配置未加载时抛出
        """
        if self.config_data is None:
            raise RuntimeError("配置未加载，请先调用 load_config()")
        
        return self.config_data['browser_config'].copy()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        获取日志配置
        
        Returns:
            包含日志配置的字典
            
        Raises:
            RuntimeError: 配置未加载时抛出
        """
        if self.config_data is None:
            raise RuntimeError("配置未加载，请先调用 load_config()")
        
        return self.config_data['logging'].copy()
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取完整配置数据
        
        Returns:
            配置数据字典的副本
            
        Raises:
            RuntimeError: 配置未加载时抛出
        """
        if self.config_data is None:
            # 尝试自动加载配置
            try:
                return self.load_config()
            except Exception:
                raise RuntimeError("配置未加载，请先调用 load_config()")
        
        return self.config_data.copy()


# 便利函数
def create_simplified_config_manager(config_path: str = "config_simple.json") -> SimplifiedConfigManager:
    """
    创建简化配置管理器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        SimplifiedConfigManager实例
    """
    return SimplifiedConfigManager(config_path)


def load_simple_config(config_path: str = "config_simple.json") -> Dict[str, Any]:
    """
    加载简化配置文件的便利函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置数据字典
    """
    manager = SimplifiedConfigManager(config_path)
    return manager.load_config()
