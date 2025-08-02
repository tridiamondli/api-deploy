"""
API函数注册中心
统一管理API函数的注册和获取，避免循环导入
"""
from typing import Dict, Callable, Any, Optional
import threading

class APIRegistry:
    """API函数注册中心 - 使用单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.registered_functions: Dict[str, Dict[str, Callable]] = {}
            self.logger = None  # 延迟设置
            self._initialized = True
    
    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger
    
    def register_function(self, module_name: str, function_name: str, func: Callable):
        """注册API函数"""
        if module_name not in self.registered_functions:
            self.registered_functions[module_name] = {}
        
        self.registered_functions[module_name][function_name] = func
        
        if self.logger:
            self.logger.log_module_event("FUNCTION_REGISTERED", module_name, {
                "function_name": function_name,
                "endpoint": f"/{module_name}/{function_name}"
            })
    
    def get_function(self, module_name: str, function_name: str) -> Optional[Callable]:
        """获取指定的API函数"""
        return self.registered_functions.get(module_name, {}).get(function_name)
    
    def get_all_functions(self) -> Dict[str, Dict[str, Callable]]:
        """获取所有已注册的函数"""
        return self.registered_functions.copy()
    
    def clear_module_functions(self, module_name: str):
        """清除指定模块的函数（用于热重载）"""
        if module_name in self.registered_functions:
            function_count = len(self.registered_functions[module_name])
            function_names = list(self.registered_functions[module_name].keys())
            del self.registered_functions[module_name]
            
            if self.logger:
                self.logger.log_module_event("FUNCTIONS_CLEARED", module_name, {
                    "function_count": function_count,
                    "function_names": function_names
                })
        else:
            if self.logger:
                self.logger.log_module_event("CLEAR_FAILED", module_name, {
                    "reason": "module_not_found"
                })
    
    def clear_all_functions(self):
        """清除所有函数"""
        self.registered_functions.clear()
        
        if self.logger:
            self.logger.log_system_event("ALL_FUNCTIONS_CLEARED")

# 全局注册中心实例
api_registry = APIRegistry()
