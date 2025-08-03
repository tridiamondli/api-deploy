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
            # 存储函数信息：{module_name: {function_name: {"func": callable, "methods": {"GET": bool, "POST": bool}}}}
            self.registered_functions: Dict[str, Dict[str, Dict[str, Any]]] = {}
            self.logger = None  # 延迟设置
            self._initialized = True
    
    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger
    
    def register_function(self, module_name: str, function_name: str, func: Callable, supported_methods: Dict[str, bool] = None):
        """注册API函数"""
        if module_name not in self.registered_functions:
            self.registered_functions[module_name] = {}
        
        # 默认只支持POST（向后兼容）
        if supported_methods is None:
            supported_methods = {'GET': False, 'POST': True}
        
        self.registered_functions[module_name][function_name] = {
            "func": func,
            "methods": supported_methods
        }
        
        if self.logger:
            methods_list = [method for method, enabled in supported_methods.items() if enabled]
            self.logger.log_module_event("FUNCTION_REGISTERED", module_name, {
                "function_name": function_name,
                "endpoint": f"/{module_name}/{function_name}",
                "supported_methods": methods_list
            })
    
    def get_function(self, module_name: str, function_name: str) -> Optional[Callable]:
        """获取指定的API函数"""
        func_info = self.registered_functions.get(module_name, {}).get(function_name)
        return func_info["func"] if func_info else None
    
    def get_function_methods(self, module_name: str, function_name: str) -> Optional[Dict[str, bool]]:
        """获取指定函数支持的HTTP方法"""
        func_info = self.registered_functions.get(module_name, {}).get(function_name)
        return func_info["methods"] if func_info else None
    
    def supports_method(self, module_name: str, function_name: str, method: str) -> bool:
        """检查函数是否支持指定的HTTP方法"""
        methods = self.get_function_methods(module_name, function_name)
        return methods.get(method.upper(), False) if methods else False
    
    def get_all_functions(self) -> Dict[str, Dict[str, Callable]]:
        """获取所有已注册的函数（向后兼容）"""
        result = {}
        for module_name, functions in self.registered_functions.items():
            result[module_name] = {}
            for func_name, func_info in functions.items():
                result[module_name][func_name] = func_info["func"]
        return result
    
    def get_all_functions_with_methods(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """获取所有已注册的函数及其支持的方法"""
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
