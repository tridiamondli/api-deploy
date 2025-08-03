import json
import time
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from loguru import logger
from config import Config

class APILogger:
    """基于loguru的API请求日志记录器"""
    
    def __init__(self):
        self.setup_logger()
    
    def setup_logger(self):
        """设置日志记录器"""
        if not Config.ENABLE_REQUEST_LOGGING:
            return
        
        # 移除默认的logger
        logger.remove()
        
        # 始终配置控制台输出
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True
        )
        
        # 配置文件输出
        if Config.LOG_TO_FILE:
            try:
                # 创建日志目录
                log_path = Path(Config.LOG_FILE_PATH)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                logger.add(
                    Config.LOG_FILE_PATH,
                    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                    level="INFO",
                    rotation=Config.LOG_ROTATION,      # 自动轮转
                    retention=Config.LOG_RETENTION,    # 保留时间
                    compression="zip",                 # 压缩格式
                    encoding="utf-8",
                    enqueue=True                       # 异步写入
                )
                
                logger.info(f"📁 日志文件已配置: {Config.LOG_FILE_PATH}")
                logger.info(f"🔄 轮转设置: {Config.LOG_ROTATION}, 保留: {Config.LOG_RETENTION}")
                
            except Exception as e:
                logger.error(f"⚠️  创建日志文件失败: {e}")
    
    def truncate_content(self, content: Any) -> str:
        """截断内容到指定长度"""
        content_str = json.dumps(content, ensure_ascii=False) if isinstance(content, (dict, list)) else str(content)
        
        if len(content_str) > Config.LOG_MAX_BODY_SIZE:
            return content_str[:Config.LOG_MAX_BODY_SIZE] + "...[truncated]"
        return content_str
    
    def get_client_ip(self, request) -> str:
        """获取客户端IP地址"""
        # 尝试从各种header中获取真实IP
        forwarded_for = getattr(request.headers, 'x-forwarded-for', None)
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = getattr(request.headers, 'x-real-ip', None)
        if real_ip:
            return real_ip
        
        # 回退到客户端IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"
    
    def log_request_start(self, endpoint: str, request, request_data: Dict) -> Dict:
        """记录请求开始"""
        if not Config.ENABLE_REQUEST_LOGGING:
            return {}
        
        request_id = f"{int(time.time() * 1000000)}"  # 微秒级时间戳
        client_ip = self.get_client_ip(request)
        method = request.method  # 从request对象获取实际的HTTP方法
        
        log_context = {
            "request_id": request_id,
            "endpoint": endpoint,
            "client_ip": client_ip,
            "method": method
        }
        
        # 构建日志数据
        log_data = {
            "request_id": request_id,
            "endpoint": endpoint,
            "client_ip": client_ip,
            "method": f"{method}",
            "user_agent": getattr(request.headers, 'user-agent', 'unknown')
        }
        
        # 记录请求体（如果启用）
        if Config.LOG_REQUEST_BODY:
            log_data["request_body"] = self.truncate_content(request_data)
        
        logger.bind(request_id=request_id).info(f"🚀 REQUEST_START | {json.dumps(log_data, ensure_ascii=False)}")
        
        return log_context
    
    def log_request_end(self, log_context: Dict, success: bool, response_data: Any = None, error: str = None, status_code: int = None):
        """记录请求结束"""
        if not Config.ENABLE_REQUEST_LOGGING or not log_context:
            return
        
        request_id = log_context.get("request_id")
        
        log_data = {
            "request_id": request_id,
            "endpoint": log_context.get("endpoint"),
            "success": success,
            "status_code": status_code,
        }
        
        if success and Config.LOG_RESPONSE_DATA and response_data is not None:
            log_data["response_data"] = self.truncate_content(response_data)
        
        if not success and error:
            log_data["error"] = error
        
        status_icon = "✅" if success else "❌"
        
        if success:
            logger.bind(request_id=request_id).info(f"{status_icon} REQUEST_END | {json.dumps(log_data, ensure_ascii=False)}")
        else:
            logger.bind(request_id=request_id).error(f"{status_icon} REQUEST_END | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_auth_failure(self, endpoint: str, client_ip: str, reason: str, request_data: Dict = None):
        """记录认证失败"""
        if not Config.ENABLE_REQUEST_LOGGING:
            return
        
        log_data = {
            "endpoint": endpoint,
            "client_ip": client_ip,
            "reason": reason,
            "event": "AUTH_FAILURE"
        }
        
        if request_data:
            log_data["request_data"] = self.truncate_content(request_data)
        
        logger.warning(f"🔐 AUTH_FAILURE | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_error(self, message: str, error_details: Dict = None, request_id: str = None):
        """记录错误日志"""
        if not Config.ENABLE_REQUEST_LOGGING:
            return
        
        log_data = {"message": message}
        
        if error_details:
            log_data.update(error_details)
        
        if request_id:
            logger.bind(request_id=request_id).error(f"💥 ERROR | {json.dumps(log_data, ensure_ascii=False)}")
        else:
            logger.error(f"💥 ERROR | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_system_event(self, event: str, details: Dict = None):
        """记录系统事件"""
        if not Config.ENABLE_REQUEST_LOGGING:
            return
        
        log_data = {"event": event}
        
        if details:
            log_data.update(details)
        
        logger.info(f"🔧 SYSTEM | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_module_event(self, event: str, module_name: str, details: Dict = None):
        """记录模块相关事件"""
        if not Config.ENABLE_REQUEST_LOGGING:
            return
        
        log_data = {
            "event": event,
            "module": module_name
        }
        
        if details:
            log_data.update(details)
        
        logger.info(f" MODULE | {json.dumps(log_data, ensure_ascii=False)}")
    
    def info(self, message: str):
        """记录信息日志"""
        logger.info(message)
    
    def error(self, message: str):
        """记录错误日志"""
        logger.error(message)
    
    def warning(self, message: str):
        """记录警告日志"""
        logger.warning(message)
    
    def debug(self, message: str):
        """记录调试日志"""
        logger.debug(message)

# 全局日志记录器实例
api_logger = APILogger()
