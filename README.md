# 动态API部署 🚀

此项目是一个基于 FastAPI 的动态API框架，支持热重载、模块化开发、认证授权和日志的API框架。
免去配置路由，处理请求等重复繁杂操作，让开发者专注于API实现函数上，你只需要给你的API实现函数加上@api_function装饰器即可

## ✨ 核心特性

- 🔄 **热重载支持** - 文件修改后自动重新加载，无需重启服务器
- 🧩 **模块化架构** - 每个功能模块独立开发和部署
- 🔐 **Token认证** - 内置安全的API认证机制
- 📝 **完整日志系统** - 请求追踪、错误记录、系统事件监控
- ⚡ **异步支持** - 支持同步和异步API函数
- 🛡️ **错误处理** - 统一的错误响应格式和异常处理
- 📊 **API注册中心** - 自动发现和注册API端点
- 🔧 **灵活配置** - 可配置的服务器参数和日志选项

## 🏗️ 项目结构

```
api-deploy/
├── main.py              # 主应用入口
├── config.py            # 配置文件
├── auth.py              # 认证模块
├── decorators.py        # API装饰器
├── module_loader.py     # 模块动态加载器
├── registry.py          # API注册中心
├── logger.py            # 日志系统
├── log_manager.py       # 日志管理器
├── requirements.txt     # 依赖包列表
├── apis/                # API模块目录
│   ├── __init__.py
│   └── template.py      # API模块模板
└── logs/                # 日志文件目录
```

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装 Python 3.8+：

```bash
python --version
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

编辑 `config.py` 文件，设置您的服务器配置：

```python
class Config:
    HOST = "127.0.0.1"
    PORT = 8000
    
    # 普通业务API访问token
    VALID_TOKENS = ["your-business-token"]
    
    # 管理员token（用于重载、配置等管理操作）
    ADMIN_TOKENS = ["your-admin-token"]
    
    HOT_RELOAD = True
    DEBUG = True
```

**⚠️ 重要说明：**
- `VALID_TOKENS`：用于普通业务API调用
- `ADMIN_TOKENS`：用于系统管理操作（如热重载、配置重载等）

### 4. 启动服务器

```bash
python main.py
```

服务器启动后，访问 http://127.0.0.1:8000 查看API状态。
注意：部署到服务器，配合守护进程使用更佳！

## 📖 API开发指南

### 创建新的API模块

1. 在 `apis/` 目录下创建新的Python文件
2. 使用 `@api_function` 装饰器标记您的函数
3. 保存文件，系统会自动热重载
4. 被标记的API函数返回结果会自动包装到响应JSON中

**示例：**

```python
# apis/template.py

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
```

### API调用格式

所有业务API端点都遵循统一的调用格式，POST请求参数包裹在body中：

**请求URL：** `POST /{module_name}/{function_name}`

**请求体格式：**
```json
{
    "token": "your-secret-token",
    "body": {
        "param1": "value1",
        "param2": "value2"
    }
}
```

**响应格式：**
```json
{
    "success": true,
    "data": {
        // 函数返回的数据
    },
    "endpoint": "/module_name/function_name"
}
```

**错误响应格式：**
```json
{
    "success": false,
    "error": "错误描述",
    "code": "ERROR_CODE",
    "endpoint": "/module_name/function_name"
}
```


## 🔧 配置选项

### 服务器配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `HOST` | str | "127.0.0.1" | 服务器监听地址 |
| `PORT` | int | 8000 | 服务器端口 |
| `HOT_RELOAD` | bool | True | 是否启用热重载 |
| `DEBUG` | bool | True | 调试模式 |

### 认证配置

| 配置项 | 类型 | 用途 | 说明 |
|--------|------|------|------|
| `VALID_TOKENS` | list | 业务API | 普通业务API访问令牌列表 |
| `ADMIN_TOKENS` | list | 管理操作 | 管理员令牌列表，用于热重载、配置重载等操作 |

**权限说明：**
- **普通业务token**：只能调用 `/{module_name}/{function_name}` 格式的业务API
- **管理员token**：可以调用 `/api/reload`、`/api/reload-config` 等管理API

### 日志配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ENABLE_REQUEST_LOGGING` | bool | True | 启用请求日志 |
| `LOG_TO_FILE` | bool | True | 保存日志到文件 |
| `LOG_REQUEST_BODY` | bool | True | 记录请求体内容 |
| `LOG_RESPONSE_DATA` | bool | False | 记录响应数据 |
| `LOG_MAX_BODY_SIZE` | int | 1000 | 最大记录长度 |
| `LOG_FILE_PATH` | str | "logs/api_{time:YYYY-MM-DD}.log" | 日志文件路径 |
| `LOG_ROTATION` | str | "1 day" | 日志轮转周期 |
| `LOG_RETENTION` | str | "30 days" | 日志保留时间 |

## 🛠️ 高级功能

### 手动重载API

**⚠️ 注意：重载功能需要提供有效的管理员token进行身份验证**

**GET方式（通过URL参数）：**
```bash
# 重新加载所有模块
curl -X GET "http://127.0.0.1:8000/api/reload?token=your-admin-token"

# 重新加载配置文件
curl -X GET "http://127.0.0.1:8000/api/reload-config?token=your-admin-token"
```

**POST方式（通过请求体）：**
```bash
# 重新加载所有模块
curl -X POST http://127.0.0.1:8000/api/reload \
  -H "Content-Type: application/json" \
  -d '{"token": "your-admin-token"}'

# 重新加载配置文件
curl -X POST http://127.0.0.1:8000/api/reload-config \
  -H "Content-Type: application/json" \
  -d '{"token": "your-admin-token"}'
```

**重载API错误响应格式：**
```json
// 缺少管理员token
{
    "success": false,
    "error": "Admin token is required for this operation",
    "code": "MISSING_ADMIN_TOKEN",
    "endpoint": "/api/reload"
}

// 无效的管理员token
{
    "success": false,
    "error": "Invalid admin token or insufficient permissions",
    "code": "INVALID_ADMIN_TOKEN"
}
```

### 查看可用端点

```bash
# 查看服务状态和所有可用端点
http://127.0.0.1:8000/
```

### 参数验证

`注意: 系统会自动验证函数参数：`

- **类型检查**：根据函数签名验证参数类型
- **必需参数**：检查是否提供了所有必需参数
- **参数匹配**：只接受函数签名中定义的参数

### 异步支持

框架同时支持同步和异步函数：

```python
@api_function
def sync_function(param: str):
    """同步函数"""
    return {"result": param}

@api_function
async def async_function(param: str):
    """异步函数"""
    await asyncio.sleep(1)
    return {"result": param}
```

## 📊 监控和日志

### 日志类型

- **请求日志**：记录所有API请求和响应
- **错误日志**：记录系统错误和异常
- **系统事件**：记录服务器启动、关闭等事件
- **认证日志**：记录认证事件

### 日志文件位置

日志文件保存在 `logs/` 目录下，按日期自动分割：
- `logs/api_2025-08-02.log`


## 🚧 故障排除

### 常见问题

**Q: 模块没有自动重载？**
A: 检查 `config.py` 中的 `HOT_RELOAD` 是否设置为 `True`

**Q: API函数没有被注册？**
A: 确保函数使用了 `@api_function` 装饰器

**Q: 认证失败？**
A: 检查请求中的 `token` 是否在 `VALID_TOKENS`或`ADMIN_TOKENS` 列表中

**Q: 重载API访问被拒绝？**
A: 重载功能需要提供有效的token。GET请求通过URL参数传递，POST请求通过请求体传递