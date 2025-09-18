import logging
import logging.handlers
import os
import glob
from datetime import datetime


class Logger:
    """日志管理类 - 支持文件和控制台双输出"""
    
    def __init__(self, name="buaa_course_selector", log_level="INFO", 
                 log_dir="./log", max_log_files=10, log_file_size="10MB"):
        """
        初始化日志配置
        
        Args:
            name: 日志器名称
            log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            log_dir: 日志目录
            max_log_files: 最大日志文件数量
            log_file_size: 单个日志文件大小
        """
        self.name = name
        self.log_level = log_level
        self.log_dir = log_dir
        self.max_log_files = max_log_files
        self.log_file_size = self._parse_file_size(log_file_size)
        
        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 初始化日志器
        self.logger = self._setup_logger()
    
    def _parse_file_size(self, size_str):
        """解析文件大小字符串"""
        size_str = size_str.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        else:
            return int(size_str)
    
    def _generate_unique_log_filename(self):
        """生成基于日期+序号的唯一日志文件名"""
        today = datetime.now().strftime('%Y%m%d')
        
        # 查找当天已存在的日志文件
        pattern = os.path.join(self.log_dir, f"{self.name}_{today}_*.log")
        existing_files = glob.glob(pattern)
        
        if not existing_files:
            # 当天第一个日志文件
            sequence = 1
        else:
            # 找到当天最大的序号
            sequences = []
            for file_path in existing_files:
                filename = os.path.basename(file_path)
                # 提取序号部分，格式为：name_YYYYMMDD_XXX.log
                parts = filename.replace('.log', '').split('_')
                if len(parts) >= 3:
                    try:
                        seq = int(parts[-1])
                        sequences.append(seq)
                    except ValueError:
                        continue
            
            if sequences:
                sequence = max(sequences) + 1
            else:
                sequence = 1
        
        # 生成新的文件名
        log_filename = f"{self.name}_{today}_{sequence:03d}.log"
        return os.path.join(self.log_dir, log_filename)
    
    def _setup_logger(self):
        """设置日志器配置"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # 避免重复添加handler
        if logger.handlers:
            logger.handlers.clear()
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器 - 使用唯一的日志文件名
        log_file = self._generate_unique_log_filename()
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=self.log_file_size,
            backupCount=self.max_log_files,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, message):
        """DEBUG级别日志"""
        self.logger.debug(message)
    
    def info(self, message):
        """INFO级别日志"""
        self.logger.info(message)
    
    def warning(self, message):
        """WARNING级别日志"""
        self.logger.warning(message)
    
    def error(self, message):
        """ERROR级别日志"""
        self.logger.error(message)
    
    def critical(self, message):
        """CRITICAL级别日志"""
        self.logger.critical(message)
    
    def exception(self, message):
        """异常信息日志"""
        self.logger.exception(message)


# 提供全局日志实例
_default_logger = None

def get_logger(name="buaa_course_selector", system_config = None):
    """获取日志器实例"""
    global _default_logger
    if _default_logger is None:
        if system_config:
            _default_logger = Logger(name, system_config.get("log_level", "INFO"), system_config.get("log_dir", "./log"), system_config.get("max_log_files", 10), system_config.get("log_file_size", "10MB"))
        else:
            _default_logger = Logger(name)
    return _default_logger