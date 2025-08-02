"""
API模块模板
复制此文件并重命名，然后编写您的API函数
支持同步和异步函数
"""

import asyncio
import time
from decorators import api_function
# 在这里导入您需要的其他库

@api_function
def sync_hello(name: str = "World"):
    """
    示例函数：问候（同步版本）
    
    参数:
        name (str): 要问候的名字，默认为"World"
    
    返回:
        dict: 包含问候信息的字典
    """
    return {
        "message": f"Hello, {name}!",
        "timestamp": int(time.time()*1000),  # 返回时间戳，单位为毫秒
        "type": "synchronous"
    }

@api_function
async def async_hello(name: str = "World", delay: float = 0.5):
    """
    示例异步函数：异步问候
    
    参数:
        name (str): 要问候的名字，默认为"World"
        delay (float): 异步延迟时间（秒），默认为0.5秒
    
    返回:
        dict: 包含问候信息的字典
    """
    start_time = time.time()
    
    # 模拟异步操作（如数据库查询、API调用等）
    await asyncio.sleep(delay)
    
    end_time = time.time()
    
    return {
        "message": f"Hello, {name}! (异步处理完成)",
        "timestamp": int(time.time()*1000),
        "type": "asynchronous"
    }