# 系统配置
class Config:
    # 服务器配置
    # 配置成你的服务器IP地址和端口
    HOST = "127.0.0.1"
    PORT = 8000
    
    # 认证配置
    # 普通业务API访问token
    VALID_TOKENS = [
        "token",
        "admin",
        # 在这里添加更多普通业务token
    ]
    
    # 管理员token（用于重载、配置等管理操作）
    ADMIN_TOKENS = [
        "admin",
        # 在这里添加更多管理员token
    ]
    
    # API模块目录
    API_MODULES_DIR = "apis"
    
    # 热重载配置
    HOT_RELOAD = True
    
    # 调试模式
    DEBUG = True
    

    
    # 日志配置
    ENABLE_REQUEST_LOGGING = True  # 是否启用请求日志
    LOG_TO_FILE = True             # 是否保存到文件
    LOG_REQUEST_BODY = True       # 是否记录请求体内容（可能包含敏感信息）
    LOG_RESPONSE_DATA = False      # 是否记录响应数据
    LOG_MAX_BODY_SIZE = 1000        # 请求体和响应体的最大记录长度（字符）
    
    # 日志文件配置
    LOG_FILE_PATH = "logs/api_{time:YYYY-MM-DD}.log"  # 日志文件路径
    LOG_ROTATION = "1 day"         # 日志轮转：1 day / 1 week / 100 MB
    LOG_RETENTION = "30 days"      # 保留时间：30 days / 1 week / 10（保留文件数）
