from fastapi import HTTPException, Request
from typing import Optional

def get_current_config():
    """动态获取当前配置，确保配置热重载生效"""
    import config
    import importlib
    importlib.reload(config)
    return config.Config

async def verify_token(request: Request):
    """
    验证普通业务API请求中的token
    支持GET和POST请求
    GET请求: 通过query参数传递token
    POST请求: 通过request body传递token
    """
    try:
        token = None
        
        if request.method == "GET":
            # GET请求从query参数获取token
            token = request.query_params.get("token")
        else:
            # POST请求从body获取token
            body = await request.json()
            token = body.get("token")
        
        if not token:
            raise HTTPException(
                status_code=401, 
                detail={"error": "Token is required", "code": "MISSING_TOKEN"}
            )
        
        # 动态获取配置
        current_config = get_current_config()
        if token not in current_config.VALID_TOKENS:
            raise HTTPException(
                status_code=401, 
                detail={"error": "Invalid token", "code": "INVALID_TOKEN"}
            )
        
        return True
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=400, 
            detail={"error": "Invalid request format", "code": "INVALID_REQUEST"}
        )

async def verify_admin_token(request: Request, token: Optional[str] = None):
    """
    验证管理员token，支持GET和POST请求
    GET请求: 通过query参数传递token
    POST请求: 通过request body传递token
    """
    request_token = None
    
    if request.method == "GET":
        # GET请求从query参数获取token
        if token:
            request_token = token
    else:
        # POST请求从body获取token
        try:
            body = await request.json()
            request_token = body.get("token")
        except:
            pass
    
    if not request_token:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": "Admin token is required for this operation",
                "code": "MISSING_ADMIN_TOKEN"
            }
        )
    
    # 动态获取配置
    current_config = get_current_config()
    if request_token not in current_config.ADMIN_TOKENS:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": "Invalid admin token or insufficient permissions",
                "code": "INVALID_ADMIN_TOKEN"
            }
        )
    
    return True