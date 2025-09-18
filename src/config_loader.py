import json
import os
from typing import Dict, Any


class ConfigLoader:
    """配置加载器 - 支持JSON配置文件和默认配置"""
    
    def __init__(self, config_file="config.json"):
        """
        初始化配置加载器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            "user": {
                "student_id": "",
                "password": "",
                "target_course_name": ""
            },
            "system": {
                "log_level": "INFO",
                "retry_interval": 1,
                "course_selection_mode": "once",  # "once" | "loop"
                "max_log_files": 10,
                "log_file_size": "10MB"
            }
        }
    
    def _load_config(self):
        """加载配置文件"""
        # 如果配置文件存在，尝试读取
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 验证配置项
                validated_config = self._validate_config(config)
                print(f"✅ 配置文件加载成功: {self.config_file}")
                return validated_config
                
            except json.JSONDecodeError as e:
                print(f"❌ 配置文件格式错误: {e}")
                print("📋 使用默认配置")
                return self._get_default_config()
            except Exception as e:
                print(f"❌ 配置文件读取失败: {e}")
                print("📋 使用默认配置")
                return self._get_default_config()
        else:
            print(f"⚠️ 配置文件不存在: {self.config_file}")
            print("📋 使用默认配置")
            return self._get_default_config()
    
    def _validate_config(self, config):
        """验证配置项并填充缺失的默认值"""
        default_config = self._get_default_config()
        
        # 确保必要的配置项存在
        if "user" not in config:
            config["user"] = default_config["user"]
        if "system" not in config:
            config["system"] = default_config["system"]
        
        # 填充缺失的用户配置
        for key, default_value in default_config["user"].items():
            if key not in config["user"]:
                config["user"][key] = default_value
        
        # 填充缺失的系统配置
        for key, default_value in default_config["system"].items():
            if key not in config["system"]:
                config["system"][key] = default_value
        
        return config
    
    def get_user_config(self):
        """获取用户配置"""
        return self.config.get("user", {})
    
    def get_system_config(self):
        """获取系统配置"""
        return self.config.get("system", {})
    
    def get_config(self, key=None):
        """获取配置项"""
        if key is None:
            return self.config
        return self.config.get(key)
    
    def save_config(self, config_file=None):
        """保存配置到文件"""
        target_file = config_file or self.config_file
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置已保存: {target_file}")
            return True
        except Exception as e:
            print(f"❌ 配置保存失败: {e}")
            return False
    
    def update_config(self, key, value):
        """更新配置项"""
        keys = key.split('.')
        current = self.config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def reload_config(self):
        """重新加载配置文件"""
        self.config = self._load_config()
        return self.config


# 提供全局配置实例
_default_config = None

def get_config(config_file="config.json"):
    """获取配置加载器实例"""
    global _default_config
    if _default_config is None:
        _default_config = ConfigLoader(config_file)
    return _default_config