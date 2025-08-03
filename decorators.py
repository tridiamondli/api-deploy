import functools
import asyncio
from typing import Any, Callable, Union
from registry import api_registry

def api_function(func: Union[Callable, None] = None, *, GET: bool = False, POST: bool = True) -> Callable:
    """
    API函数装饰器
    使用此装饰器标记的函数将自动注册为API端点
    支持同步和异步函数
    
    参数:
        GET (bool): 是否支持GET请求，默认为False
        POST (bool): 是否支持POST请求，默认为True
    
    使用示例:
        @api_function  # 默认只支持POST
        @api_function(GET=True)  # 同时支持GET和POST
        @api_function(GET=True, POST=False)  # 只支持GET
    """
    def decorator(func: Callable) -> Callable:
        # 验证至少支持一种方法
        if not GET and not POST:
            raise ValueError("至少需要支持GET或POST中的一种方法")
        
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
        
        # 注册函数到注册中心，包含支持的HTTP方法信息
        api_registry.register_function(module_name, func.__name__, wrapper, 
                                     supported_methods={'GET': GET, 'POST': POST})
        
        return wrapper
    
    # 支持带参数和不带参数的调用
    if func is None:
        # 带参数调用: @api_function(GET=True)
        return decorator
    else:
        # 不带参数调用: @api_function
        return decorator(func)

def get_registered_functions():
    """获取所有已注册的函数"""
    return api_registry.get_all_functions()

def clear_module_functions(module_name: str):
    """清除指定模块的函数（用于热重载）"""
    api_registry.clear_module_functions(module_name)
