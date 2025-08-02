import os
import sys
import importlib
import inspect
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from registry import api_registry
from config import Config
from loguru import logger

# 延迟导入logger避免循环导入
def get_api_logger():
    try:
        from logger import api_logger
        return api_logger
    except ImportError:
        return None

class APIModuleHandler(FileSystemEventHandler):
    """文件系统事件处理器，用于热重载"""
    
    def __init__(self, module_loader):
        self.module_loader = module_loader
        self.loop = None  # 主事件循环引用
    
    def set_event_loop(self, loop):
        """设置主事件循环引用"""
        self.loop = loop
    
    def _schedule_async_task(self, coro):
        """安全地调度异步任务"""
        if self.loop and not self.loop.is_closed():
            try:
                # 使用 call_soon_threadsafe 从其他线程调度任务
                future = asyncio.run_coroutine_threadsafe(coro, self.loop)
                # 不等待结果，让任务在后台执行
            except Exception as e:
                logger.error(f"调度异步任务失败: {e}")
        else:
            logger.warning("事件循环不可用，回退到同步处理")
            # 回退到同步处理
            if hasattr(coro, 'cr_frame'):
                # 这是一个协程，需要特殊处理
                logger.warning("无法执行异步任务，跳过")
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.py'):
            module_path = Path(event.src_path)
            
            # 检查是否是config.py文件
            if module_path.name == "config.py":
                logger.info(f"⚙️  检测到配置文件修改: config.py")
                api_logger = get_api_logger()
                if api_logger:
                    api_logger.log_system_event("CONFIG_MODIFIED", {"file_path": event.src_path})
                self._schedule_async_task(self.module_loader.reload_config_async())
                return
            
            # 检查是否是API模块文件
            if module_path.parent.name == Config.API_MODULES_DIR:
                module_name = module_path.stem
                logger.info(f"🔄 检测到文件修改: {module_name}.py")
                api_logger = get_api_logger()
                if api_logger:
                    api_logger.log_module_event("FILE_MODIFIED", module_name, {"file_path": event.src_path})
                self._schedule_async_task(self.module_loader.schedule_reload(module_name))
    
    def on_deleted(self, event):
        """文件删除事件"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.py'):
            module_path = Path(event.src_path)
            if module_path.parent.name == Config.API_MODULES_DIR:
                module_name = module_path.stem
                logger.info(f"🗑️  检测到文件删除: {module_name}.py")
                api_logger = get_api_logger()
                if api_logger:
                    api_logger.log_module_event("FILE_DELETED", module_name, {"file_path": event.src_path})
                self._schedule_async_task(self.module_loader.unload_module_async(module_name))
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.py'):
            module_path = Path(event.src_path)
            if module_path.parent.name == Config.API_MODULES_DIR:
                module_name = module_path.stem
                logger.info(f"📁 检测到新文件创建: {module_name}.py")
                api_logger = get_api_logger()
                if api_logger:
                    api_logger.log_module_event("FILE_CREATED", module_name, {"file_path": event.src_path})
                asyncio.create_task(self.module_loader.load_module_async(module_name))

class ModuleLoader:
    """异步模块加载器，负责动态加载和重载API模块"""
    
    def __init__(self):
        self.loaded_modules = {}
        self.observer = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.reload_queue = asyncio.Queue()
        self.processing_modules: Set[str] = set()
        self.last_reload_time = {}
        self.min_reload_interval = 1.0  # 最小重载间隔（秒）
        self._queue_processor_started = False
        
        # 确保apis目录存在
        os.makedirs(Config.API_MODULES_DIR, exist_ok=True)
        
        # 将apis目录添加到Python路径
        apis_path = os.path.abspath(Config.API_MODULES_DIR)
        if apis_path not in sys.path:
            sys.path.insert(0, apis_path)
    
    async def _start_queue_processor(self):
        """启动队列处理器"""
        if not self._queue_processor_started:
            self._queue_processor_started = True
            asyncio.create_task(self._process_reload_queue())
            get_api_logger().info("🚀 异步队列处理器已启动")
    
    async def _process_reload_queue(self):
        """处理重载队列"""
        while True:
            try:
                module_name = await self.reload_queue.get()
                
                # 检查是否需要防抖
                current_time = time.time()
                last_time = self.last_reload_time.get(module_name, 0)
                
                if current_time - last_time < self.min_reload_interval:
                    # 等待一段时间再处理
                    await asyncio.sleep(self.min_reload_interval)
                
                if module_name not in self.processing_modules:
                    self.processing_modules.add(module_name)
                    
                    try:
                        # 在线程池中执行重载
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            self.executor,
                            self._reload_module_sync,
                            module_name
                        )
                        self.last_reload_time[module_name] = time.time()
                        
                    except Exception as e:
                        logger.error(f"异步重载模块失败 {module_name}: {e}")
                    finally:
                        self.processing_modules.discard(module_name)
                
                self.reload_queue.task_done()
                
            except Exception as e:
                logger.error(f"处理重载队列时出错: {e}")
                await asyncio.sleep(1)
    
    def load_all_modules(self):
        """加载所有API模块（同步方法，用于启动时）"""
        apis_dir = Path(Config.API_MODULES_DIR)
        
        if not apis_dir.exists():
            logger.warning(f"⚠️  API目录不存在: {apis_dir}")
            return
        
        for py_file in apis_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            module_name = py_file.stem
            self._load_module_sync(module_name)
    
    def _load_module_sync(self, module_name: str):
        """同步加载指定模块（内部方法）"""
        try:
            module_path = f"{Config.API_MODULES_DIR}.{module_name}"
            
            if module_path in sys.modules:
                # 如果模块已存在，重新加载
                module = importlib.reload(sys.modules[module_path])
            else:
                # 导入新模块
                module = importlib.import_module(module_path)
            
            self.loaded_modules[module_name] = module
            logger.success(f"✅ 加载模块成功: {module_name}")
            
        except Exception as e:
            logger.error(f"❌ 加载模块失败 {module_name}: {str(e)}")
    
    async def load_module_async(self, module_name: str):
        """异步加载指定模块"""
        await self._start_queue_processor()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._load_module_sync,
            module_name
        )
    
    def _unload_module_sync(self, module_name: str):
        """同步卸载指定模块（内部方法）"""
        try:
            # 清除注册的函数
            api_registry.clear_module_functions(module_name)
            
            # 从已加载模块列表中移除
            if module_name in self.loaded_modules:
                del self.loaded_modules[module_name]
            
            # 从Python模块缓存中移除
            module_path = f"{Config.API_MODULES_DIR}.{module_name}"
            if module_path in sys.modules:
                del sys.modules[module_path]
            
            logger.success(f"🗑️  模块卸载成功: {module_name}")
            
        except Exception as e:
            logger.error(f"❌ 模块卸载失败 {module_name}: {str(e)}")
    
    async def unload_module_async(self, module_name: str):
        """异步卸载指定模块"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._unload_module_sync,
            module_name
        )
    
    def _reload_module_sync(self, module_name: str):
        """同步重新加载指定模块（内部方法）"""
        try:
            # 清除旧的注册函数
            api_registry.clear_module_functions(module_name)
            
            # 重新加载模块
            self._load_module_sync(module_name)
            
            logger.success(f"🔄 模块热重载成功: {module_name}")
            
        except Exception as e:
            logger.error(f"❌ 模块热重载失败 {module_name}: {str(e)}")
    
    async def schedule_reload(self, module_name: str):
        """调度模块重载"""
        await self._start_queue_processor()
        
        if module_name not in self.processing_modules:
            await self.reload_queue.put(module_name)
            logger.debug(f"已调度模块重载: {module_name}")
    
    async def reload_config_async(self):
        """异步重新加载配置文件"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._reload_config_sync
        )
    
    def _reload_config_sync(self):
        """同步重新加载配置文件（内部方法）"""
        try:
            # 重新加载config模块
            import config
            importlib.reload(config)
            
            get_api_logger().info(f"⚙️  配置文件热重载成功")
            
            # 记录配置变更
            api_logger = get_api_logger()
            if api_logger:
                api_logger.log_system_event("CONFIG_RELOADED", {
                    "host": config.Config.HOST,
                    "port": config.Config.PORT,
                    "hot_reload": config.Config.HOT_RELOAD,
                    "enable_logging": config.Config.ENABLE_REQUEST_LOGGING
                })
                
                # 如果日志配置发生变化，重新设置logger
                api_logger.setup_logger()
                
                get_api_logger().info(f"⚙️  新配置已生效 - 主机: {config.Config.HOST}:{config.Config.PORT}")
            
        except Exception as e:
            get_api_logger().error(f"❌ 配置文件热重载失败: {str(e)}")
    
    def start_watching(self):
        """开始监控文件变化"""
        if not Config.HOT_RELOAD:
            return
        
        self.observer = Observer()
        handler = APIModuleHandler(self)
        
        # 设置事件循环引用，以便从watchdog线程调度异步任务
        try:
            current_loop = asyncio.get_running_loop()
            handler.set_event_loop(current_loop)
        except RuntimeError:
            logger.warning("没有找到运行中的事件循环，异步重载可能无法工作")
        
        # 监控API模块目录
        self.observer.schedule(handler, Config.API_MODULES_DIR, recursive=False)
        
        # 监控当前目录中的config.py文件
        self.observer.schedule(handler, ".", recursive=False)
        
        self.observer.start()
        get_api_logger().info(f"👀 开始监控目录: {Config.API_MODULES_DIR}")
        get_api_logger().info(f"👀 开始监控配置文件: config.py")
        get_api_logger().info(f"🚀 异步模块加载器已启用")
    
    def stop_watching(self):
        """停止监控文件变化"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            get_api_logger().info("🛑 停止文件监控")
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        get_api_logger().info("🛑 异步模块加载器已关闭")
    
    def get_function(self, module_name: str, function_name: str):
        """获取指定的API函数"""
        return api_registry.get_function(module_name, function_name)
    
    def list_all_functions(self) -> Dict[str, Any]:
        """列出所有已注册的API函数"""
        return api_registry.get_all_functions()
