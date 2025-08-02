import functools
import asyncio
from typing import Any, Callable
from registry import api_registry

def api_function(func: Callable) -> Callable:
    """
    API函数装饰器
    使用此装饰器标记的函数将自动注册为API端点
    支持同步和异步函数
    """
    if asyncio.iscoroutinefunction(func):
        # 异步函数的包装器
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        wrapper = async_wrapper
    else:
        # 同步函数的包装器
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper = sync_wrapper
    
    # 获取函数所在的模块名
    module_name = func.__module__.split('.')[-1]
    if module_name.startswith('apis.'):
        module_name = module_name[5:]  # 移除 'apis.' 前缀
    elif 'apis.' in module_name:
        module_name = module_name.split('apis.')[-1]
    
    # 注册函数到注册中心
    api_registry.register_function(module_name, func.__name__, wrapper)
    
    return wrapper

def get_registered_functions():
    """获取所有已注册的函数"""
    return api_registry.get_all_functions()

def clear_module_functions(module_name: str):
    """清除指定模块的函数（用于热重载）"""
    api_registry.clear_module_functions(module_name)
