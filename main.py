from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import asyncio
import inspect
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from config import Config
from auth import verify_token, verify_admin_token
from module_loader import ModuleLoader
from registry import api_registry
from logger import api_logger

# 全局模块加载器
module_loader = ModuleLoader()

# 参数提取和类型转换辅助函数
def convert_query_param_type(value: str, param_type: type) -> Any:
    """将查询参数字符串转换为指定类型"""
    if param_type == str:
        return value
    elif param_type == int:
        return int(value)
    elif param_type == float:
        return float(value)
    elif param_type == bool:
        # 支持多种布尔值表示
        return value.lower() in ('true', '1', 'yes', 'on')
    else:
        # 其他类型尝试直接转换
        return param_type(value)

def extract_function_params_from_get(request: Request, sig: inspect.Signature) -> Dict[str, Any]:
    """从GET请求的查询参数中提取函数参数"""
    function_params = {}
    
    for param_name, param in sig.parameters.items():
        if param_name in request.query_params:
            value = request.query_params[param_name]
            
            # 获取参数类型注解
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                param_type = str  # 默认为字符串类型
            
            try:
                # 类型转换
                function_params[param_name] = convert_query_param_type(value, param_type)
            except (ValueError, TypeError) as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": f"Invalid parameter type for '{param_name}': expected {param_type.__name__}, got '{value}'",
                        "code": "INVALID_PARAMETER_TYPE",
                        "parameter": param_name,
                        "expected_type": param_type.__name__,
                        "received_value": value
                    }
                )
    
    return function_params

def extract_function_params_from_post(body: Dict[str, Any]) -> Dict[str, Any]:
    """从POST请求的body中提取函数参数"""
    return body.get("body", {})

def validate_function_params(function_params: Dict[str, Any], sig: inspect.Signature, endpoint: str) -> Dict[str, Any]:
    """验证函数参数并返回过滤后的参数"""
    filtered_params = {}
    
    # 获取函数的所有参数名
    valid_param_names = set(sig.parameters.keys())
    
    # 检查请求中是否有无效的参数名
    invalid_params = set(function_params.keys()) - valid_param_names
    if invalid_params:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid parameter(s): {', '.join(sorted(invalid_params))}",
                "code": "INVALID_PARAMETER",
                "valid_parameters": sorted(list(valid_param_names)),
                "received_parameters": sorted(list(function_params.keys())),
                "endpoint": endpoint
            }
        )
    
    # 匹配有效参数
    for param_name, param in sig.parameters.items():
        if param_name in function_params:
            filtered_params[param_name] = function_params[param_name]
        elif param.default == inspect.Parameter.empty:
            # 必需参数但未提供
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Missing required parameter: {param_name}",
                    "code": "MISSING_PARAMETER",
                    "required_parameters": [name for name, p in sig.parameters.items() if p.default == inspect.Parameter.empty],
                    "optional_parameters": [name for name, p in sig.parameters.items() if p.default != inspect.Parameter.empty],
                    "endpoint": endpoint
                }
            )
    
    return filtered_params

# 自定义异常处理器
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一的HTTP异常处理器"""
    detail = exc.detail
    
    # 如果detail已经是统一格式，直接返回
    if isinstance(detail, dict) and "success" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=detail
        )
    
    # 如果不是统一格式，转换为统一格式
    if isinstance(detail, dict):
        response_content = {
            "success": False,
            "error": detail.get("error", "Unknown error"),
            "code": detail.get("code", "UNKNOWN_ERROR")
        }
        if "endpoint" in detail:
            response_content["endpoint"] = detail["endpoint"]
    else:
        response_content = {
            "success": False,
            "error": str(detail),
            "code": "HTTP_ERROR"
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误的异常处理器"""
    # 检查是否是重载API的token缺失错误
    if request.url.path in ["/api/reload", "/api/reload-config"]:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Admin token is required for this operation",
                "code": "MISSING_ADMIN_TOKEN",
                "endpoint": request.url.path
            }
        )
    
    # 其他验证错误保持原有格式
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation error",
            "code": "VALIDATION_ERROR",
            "details": exc.errors()
        }
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    api_logger.info("🚀 启动API服务器...")
    
    # 加载所有API模块
    module_loader.load_all_modules()
    
    # 开始文件监控
    module_loader.start_watching()
    
    # 启动异步队列处理器
    await module_loader._start_queue_processor()
    
    # 设置注册中心的日志记录器
    api_registry.set_logger(api_logger)
    
    # 获取已注册的函数
    registered_funcs = api_registry.get_all_functions()
    
    # 记录系统启动事件
    api_logger.log_system_event("SERVER_STARTED", {
        "host": Config.HOST,
        "port": Config.PORT,
        "hot_reload": Config.HOT_RELOAD,
        "endpoints_count": sum(len(funcs) for funcs in registered_funcs.values()),
        "async_loading": True
    })
    
    api_logger.info(f"🌐 服务器启动完成: http://{Config.HOST}:{Config.PORT}")
    api_logger.info("📚 可用的API端点:")
    
    # 获取包含方法信息的函数列表
    registered_funcs_with_methods = api_registry.get_all_functions_with_methods()
    for module_name, functions in registered_funcs_with_methods.items():
        for func_name, func_info in functions.items():
            methods = func_info.get("methods", {"POST": True})
            supported_methods = [method for method, enabled in methods.items() if enabled]
            methods_str = "/".join(supported_methods)
            api_logger.info(f"   {methods_str} /{module_name}/{func_name}")
    
    yield
    
    # 关闭时执行
    api_logger.info("🛑 正在关闭API服务器...")
    api_logger.log_system_event("SERVER_SHUTDOWN")
    module_loader.stop_watching()

# 创建FastAPI应用
app = FastAPI(
    title="动态API服务器",
    description="支持热重载的模块化API服务器",
    version="1.0.0",
    lifespan=lifespan
)

# 注册异常处理器
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

@app.get("/")
async def root():
    """根端点，显示服务状态"""
    registered_funcs_with_methods = api_registry.get_all_functions_with_methods()
    
    endpoints = []
    for module_name, functions in registered_funcs_with_methods.items():
        for func_name, func_info in functions.items():
            methods = func_info.get("methods", {"POST": True})
            supported_methods = [method for method, enabled in methods.items() if enabled]
            for method in supported_methods:
                endpoints.append(f"{method} /{module_name}/{func_name}")
    
    return {
        "message": "动态API服务器正在运行",
        "version": "1.0.0",
        "endpoints": endpoints,
        "hot_reload": Config.HOT_RELOAD
    }

# 管理API路由（必须在动态路由之前定义）
@app.get("/api/reload")
async def reload_all_modules_get(request: Request, token: Optional[str] = Query(None, description="认证token")):
    """手动重新加载所有模块（GET方式）"""
    return await _reload_all_modules(request, token)

@app.post("/api/reload") 
async def reload_all_modules_post(request: Request):
    """手动重新加载所有模块（POST方式）"""
    return await _reload_all_modules(request)

@app.get("/api/reload-config")
async def reload_config_get(request: Request, token: Optional[str] = Query(None, description="认证token")):
    """手动重新加载配置文件（GET方式）"""
    return await _reload_config(request, token)

@app.post("/api/reload-config")
async def reload_config_post(request: Request):
    """手动重新加载配置文件（POST方式）"""
    return await _reload_config(request)

async def _reload_all_modules(request: Request, token: Optional[str] = None):
    """重新加载所有模块的内部实现"""
    try:
        # 验证token
        await verify_admin_token(request, token)
        
        # 清除所有注册的函数
        api_registry.clear_all_functions()
        
        # 重新加载所有模块
        module_loader.load_all_modules()
        
        return {
            "success": True,
            "message": "所有模块已重新加载",
            "modules": list(api_registry.get_all_functions().keys())
        }
    except HTTPException as e:
        # token验证失败，直接重新抛出
        raise e
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "code": "RELOAD_ERROR"
            }
        )

async def _reload_config(request: Request, token: Optional[str] = None):
    """重新加载配置文件的内部实现"""
    try:
        # 验证token
        await verify_admin_token(request, token)
        
        # 重新加载配置
        await module_loader.reload_config_async()
        
        # 重新导入配置以获取最新值
        import config
        
        return {
            "success": True,
            "message": "配置文件已重新加载",
            "config": {
                "host": config.Config.HOST,
                "port": config.Config.PORT,
                "hot_reload": config.Config.HOT_RELOAD,
                "enable_request_logging": config.Config.ENABLE_REQUEST_LOGGING,
                "log_to_file": config.Config.LOG_TO_FILE
            }
        }
    except HTTPException as e:
        # token验证失败，直接重新抛出
        raise e
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "code": "CONFIG_RELOAD_ERROR"
            }
        )

# 动态API路由（必须在具体路由之后定义）
@app.post("/{module_name}/{function_name}")
async def dynamic_api_endpoint(module_name: str, function_name: str, request: Request):
    """动态API POST端点处理器"""
    endpoint = f"/{module_name}/{function_name}"
    log_context = {}
    
    try:
        # 首先检查函数是否存在
        func = module_loader.get_function(module_name, function_name)
        
        if not func:
            # 检查模块是否存在
            registered_funcs = api_registry.get_all_functions()
            if module_name not in registered_funcs:
                available_modules = list(registered_funcs.keys())
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": f"API module not found: {module_name}",
                        "code": "MODULE_NOT_FOUND",
                        "available_modules": available_modules,
                        "endpoint": endpoint
                    }
                )
            else:
                available_functions = list(registered_funcs[module_name].keys())
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": f"API function not found: {function_name} in module {module_name}",
                        "code": "FUNCTION_NOT_FOUND",
                        "available_functions": available_functions,
                        "endpoint": endpoint
                    }
                )
        
        # 然后检查函数是否支持POST方法
        if not api_registry.supports_method(module_name, function_name, "POST"):
            raise HTTPException(
                status_code=405,
                detail={
                    "error": f"Method POST not allowed for endpoint {endpoint}",
                    "code": "METHOD_NOT_ALLOWED",
                    "endpoint": endpoint,
                    "allowed_methods": [method for method, enabled in 
                                      (api_registry.get_function_methods(module_name, function_name) or {}).items() 
                                      if enabled]
                }
            )
        
        # 获取请求体
        body = await request.json()
        
        # 记录请求开始
        log_context = api_logger.log_request_start(endpoint, request, body)
        
        # 验证token
        try:
            await verify_token(request)
        except HTTPException as e:
            # 记录认证失败
            api_logger.log_auth_failure(
                endpoint, 
                api_logger.get_client_ip(request), 
                "Token验证失败",
                body
            )
            # 为token验证错误添加endpoint信息
            detail = e.detail
            if isinstance(detail, dict):
                detail["endpoint"] = endpoint
            # 记录请求结束（失败）
            api_logger.log_request_end(log_context, False, error=str(detail), status_code=e.status_code)
            # 标记已经记录过日志
            log_context["logged"] = True
            # 直接返回错误响应，不要重新抛出异常
            return JSONResponse(
                status_code=e.status_code,
                content=detail
            )
        
        # 检查函数签名，从POST body中提取函数参数
        sig = inspect.signature(func)
        function_params = extract_function_params_from_post(body)
        
        # 验证参数
        filtered_params = validate_function_params(function_params, sig, endpoint)
        
        # 调用函数
        if asyncio.iscoroutinefunction(func):
            result = await func(**filtered_params)
        else:
            result = func(**filtered_params)
        
        # 包装结果为JSON格式
        response_data = {
            "success": True,
            "data": result,
            "endpoint": endpoint
        }
        
        # 记录请求结束（成功）
        api_logger.log_request_end(log_context, True, response_data, status_code=200)
        
        return response_data
        
    except HTTPException as e:
        # 检查是否已经记录过日志
        if not log_context.get("logged", False):
            # 为HTTPException添加endpoint信息
            detail = e.detail
            if isinstance(detail, dict):
                detail["endpoint"] = endpoint
            else:
                detail = {
                    "success": False,
                    "error": str(detail),
                    "code": "HTTP_ERROR",
                    "endpoint": endpoint
                }
            # 记录请求结束（HTTP异常）
            api_logger.log_request_end(log_context, False, error=str(detail), status_code=e.status_code)
            # 返回统一格式的错误响应
            return JSONResponse(
                status_code=e.status_code,
                content=detail
            )
        else:
            # 已经记录过日志，直接重新抛出
            raise
    except Exception as e:
        # 记录错误
        error_msg = str(e)
        api_logger.log_error(
            f"Internal error in {endpoint}",
            {"error": error_msg, "endpoint": endpoint},
            log_context.get("request_id")
        )
        
        # 记录请求结束（内部错误）
        api_logger.log_request_end(log_context, False, error=error_msg, status_code=500)
        
        # 处理其他异常
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "code": "INTERNAL_ERROR",
                "endpoint": endpoint
            }
        )

@app.get("/{module_name}/{function_name}")
async def dynamic_api_get_endpoint(module_name: str, function_name: str, request: Request):
    """动态API GET端点处理器"""
    endpoint = f"/{module_name}/{function_name}"
    log_context = {}
    
    try:
        # 首先检查函数是否存在
        func = module_loader.get_function(module_name, function_name)
        
        if not func:
            # 检查模块是否存在
            registered_funcs = api_registry.get_all_functions()
            if module_name not in registered_funcs:
                available_modules = list(registered_funcs.keys())
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": f"API module not found: {module_name}",
                        "code": "MODULE_NOT_FOUND",
                        "available_modules": available_modules,
                        "endpoint": endpoint
                    }
                )
            else:
                available_functions = list(registered_funcs[module_name].keys())
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": f"API function not found: {function_name} in module {module_name}",
                        "code": "FUNCTION_NOT_FOUND",
                        "available_functions": available_functions,
                        "endpoint": endpoint
                    }
                )
        
        # 然后检查函数是否支持GET方法
        if not api_registry.supports_method(module_name, function_name, "GET"):
            raise HTTPException(
                status_code=405,
                detail={
                    "error": f"Method GET not allowed for endpoint {endpoint}",
                    "code": "METHOD_NOT_ALLOWED",
                    "endpoint": endpoint,
                    "allowed_methods": [method for method, enabled in 
                                      (api_registry.get_function_methods(module_name, function_name) or {}).items() 
                                      if enabled]
                }
            )
        
        # 将查询参数转换为body格式用于日志记录
        query_params = dict(request.query_params)
        log_body = {"query_params": query_params}
        
        # 记录请求开始
        log_context = api_logger.log_request_start(endpoint, request, log_body)
        
        # 验证token
        try:
            await verify_token(request)
        except HTTPException as e:
            # 记录认证失败
            api_logger.log_auth_failure(
                endpoint, 
                api_logger.get_client_ip(request), 
                "Token验证失败",
                log_body
            )
            # 为token验证错误添加endpoint信息
            detail = e.detail
            if isinstance(detail, dict):
                detail["endpoint"] = endpoint
            # 记录请求结束（失败）
            api_logger.log_request_end(log_context, False, error=str(detail), status_code=e.status_code)
            # 标记已经记录过日志
            log_context["logged"] = True
            # 直接返回错误响应，不要重新抛出异常
            return JSONResponse(
                status_code=e.status_code,
                content=detail
            )
        
        # 检查函数签名，从GET参数中提取函数参数
        sig = inspect.signature(func)
        function_params = extract_function_params_from_get(request, sig)
        
        # 验证参数
        filtered_params = validate_function_params(function_params, sig, endpoint)
        
        # 调用函数
        if asyncio.iscoroutinefunction(func):
            result = await func(**filtered_params)
        else:
            result = func(**filtered_params)
        
        # 包装结果为JSON格式
        response_data = {
            "success": True,
            "data": result,
            "endpoint": endpoint
        }
        
        # 记录请求结束（成功）
        api_logger.log_request_end(log_context, True, response_data, status_code=200)
        
        return response_data
        
    except HTTPException as e:
        # 检查是否已经记录过日志
        if not log_context.get("logged", False):
            # 为HTTPException添加endpoint信息
            detail = e.detail
            if isinstance(detail, dict):
                detail["endpoint"] = endpoint
            else:
                detail = {
                    "success": False,
                    "error": str(detail),
                    "code": "HTTP_ERROR",
                    "endpoint": endpoint
                }
            # 记录请求结束（HTTP异常）
            api_logger.log_request_end(log_context, False, error=str(detail), status_code=e.status_code)
            # 返回统一格式的错误响应
            return JSONResponse(
                status_code=e.status_code,
                content=detail
            )
        else:
            # 已经记录过日志，直接重新抛出
            raise
    except Exception as e:
        # 记录错误
        error_msg = str(e)
        api_logger.log_error(
            f"Internal error in {endpoint}",
            {"error": error_msg, "endpoint": endpoint},
            log_context.get("request_id")
        )
        
        # 记录请求结束（内部错误）
        api_logger.log_request_end(log_context, False, error=error_msg, status_code=500)
        
        # 处理其他异常
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "code": "INTERNAL_ERROR",
                "endpoint": endpoint
            }
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False,  # 我们使用自己的热重载机制
        log_level="info" if Config.DEBUG else "warning"
    )
