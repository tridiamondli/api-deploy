# 动态API部署 🚀

此项目是一个基于 FastAPI 的动态API框架，支持热重载、模块化开发、认证授权和日志的API框架。
免去配置路由，处理请求等重复繁杂操作，让开发者专注于API实现函数上，你只需要给你的API实现函数加上@api_function装饰器即可

## ✨ 核心特性

- 🔄 **热重载支持** - API/配置文件修改后自动重新加载，无需重启服务器
- 🧩 **模块化架构** - 每个功能模块独立开发和部署
- 🌐 **多请求方法支持** - 支持 GET 和 POST 请求，异步支持，可灵活配置
- 🔐 **Token认证** - 内置安全的API认证机制
- 📝 **完整日志系统** - 请求追踪、错误记录、系统事件监控
- ⚡ **异步支持** - 支持同步和异步API函数
- 📊 **API注册中心** - 自动发现和注册API端点
- 🔧 **灵活配置** - 可配置的服务器参数和日志选项
- 🎯 **智能参数提取** - GET请求从查询参数提取，POST请求从JSON body提取
- 🔄 **自动类型转换** - GET请求参数自动类型转换

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

## 🎯 快速示例
实现参考apis下模板

### GET请求示例

```bash
# 简单的GET请求（使用默认参数）
curl "http://127.0.0.1:8000/template/sync_hello?token=your-token"

# 带参数的GET请求
curl "http://127.0.0.1:8000/template/sync_hello?token=your-token&name=Alice"
```
### POST请求示例

```bash
# POST请求调用,业务请求参数包裹在body中
curl -X POST http://127.0.0.1:8000/template/sync_hello \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your-token",
    "body": {
      "name": "Alice"
    }
  }'
```

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

@api_function(GET=True, POST=True)
def sync_hello(name: str = "World"):
    """
    示例函数：问候（同步版本）
    支持GET和POST两种请求方式
    
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

@api_function(GET=False, POST=True)
async def async_hello(name: str = "World", delay: float = 0.5):
    """
    示例异步函数：异步问候
    只支持POST请求方式
    
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

### HTTP请求方法配置

使用 `@api_function` 装饰器可以灵活配置API支持的HTTP方法：

```python
# 默认只支持POST请求（默认行为，向后兼容）
@api_function
def post_only_api():
    return {"method": "POST only"}

# 只支持GET请求
@api_function(GET=True, POST=False)
def get_only_api():
    return {"method": "GET only"}

# 同时支持GET和POST请求
@api_function(GET=True, POST=True)
def both_methods_api():
    return {"method": "GET and POST"}

# 简化写法：只启用GET（POST默认为True）
@api_function(GET=True)
def get_and_post_api():
    return {"method": "GET and POST"}
```

### API调用格式

根据API配置的支持方法，有以下几种调用方式：

#### GET请求调用

**请求URL：** `GET /{module_name}/{function_name}?param1=value1&param2=value2&token=your-token`

**示例：**
```bash
# 调用template模块的sync_hello函数
GET http://127.0.0.1:8000/template/sync_hello?token=your-token&name=Alice

# 带类型转换的参数
GET http://127.0.0.1:8000/user/get_user?token=your-token&user_id=123&active=true
```

**GET请求特点：**
- Token通过查询参数 `token` 传递
- 函数参数直接作为查询参数传递
- 自动进行类型转换（支持 str、int、float、bool）
- 适用于简单参数的查询类操作

#### POST请求调用

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

**示例：**
```bash
# 调用template模块的sync_hello函数
curl -X POST http://127.0.0.1:8000/template/sync_hello \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your-token",
    "body": {
      "name": "Alice"
    }
  }'

# 调用异步函数
curl -X POST http://127.0.0.1:8000/template/async_hello \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your-token", 
    "body": {
      "name": "Bob",
      "delay": 1.5
    }
  }'
```

**POST请求特点：**
- Token在JSON body中的 `token` 字段传递
- 函数参数在JSON body中的 `body` 字段传递
- 支持复杂数据类型（对象、数组等）
- 适用于复杂参数的数据操作

#### 统一响应格式

无论GET还是POST请求，响应格式都是统一的：

**成功响应：**
```json
{
    "success": true,
    "data": {
        // 函数返回的数据
        "message": "Hello, Alice!",
        "timestamp": 1722700800000,
        "type": "synchronous"
    },
    "endpoint": "/template/sync_hello"
}
```

**错误响应：**
```json
{
    "success": false,
    "error": "错误描述",
    "code": "ERROR_CODE",
    "endpoint": "/template/sync_hello"
}
```

#### 方法不支持错误

如果调用了API不支持的HTTP方法，会返回405错误：

```json
{
    "success": false,
    "error": "Method GET not allowed for endpoint /template/async_hello",
    "code": "METHOD_NOT_ALLOWED",
    "endpoint": "/template/async_hello",
    "allowed_methods": ["POST"]
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

### 参数验证和类型转换

系统会自动验证函数参数并进行智能类型转换：

#### GET请求参数类型转换

GET请求的查询参数都是字符串，系统会根据函数签名自动转换类型：

```python
@api_function(GET=True)
def user_search(user_id: int, active: bool = True, score: float = 0.0):
    """
    GET请求示例：
    /user/user_search?user_id=123&active=true&score=95.5
    
    参数会自动转换为：
    user_id: int = 123
    active: bool = True  
    score: float = 95.5
    """
    return {
        "user_id": user_id,
        "active": active, 
        "score": score,
        "types": {
            "user_id": type(user_id).__name__,
            "active": type(active).__name__,
            "score": type(score).__name__
        }
    }
```

**支持的类型转换：**
- `str`：保持字符串不变
- `int`：转换为整数
- `float`：转换为浮点数  
- `bool`：支持 `true`/`false`、`1`/`0`、`yes`/`no`、`on`/`off`

**类型转换错误处理：**
```json
{
    "success": false,
    "error": "Invalid parameter type for 'user_id': expected int, got 'abc'",
    "code": "INVALID_PARAMETER_TYPE",
    "parameter": "user_id",
    "expected_type": "int",
    "received_value": "abc"
}
```

#### 参数验证规则

- **类型检查**：根据函数签名验证参数类型
- **必需参数**：检查是否提供了所有必需参数
- **参数匹配**：只接受函数签名中定义的参数
- **无效参数**：拒绝函数签名中未定义的参数

**参数验证错误示例：**

```json
// 缺少必需参数
{
    "success": false,
    "error": "Missing required parameter: user_id",
    "code": "MISSING_PARAMETER",
    "required_parameters": ["user_id"],
    "optional_parameters": ["active", "score"]
}

// 无效参数
{
    "success": false, 
    "error": "Invalid parameter(s): unknown_param",
    "code": "INVALID_PARAMETER",
    "valid_parameters": ["user_id", "active", "score"],
    "received_parameters": ["user_id", "unknown_param"]
}
```

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

**Q: GET请求返回"Invalid request format"错误？**
A: 确保在GET请求的URL中包含了 `token` 参数，例如：`?token=your-token&param=value`

**Q: GET请求返回"Method GET not allowed"错误？**
A: 检查API函数的装饰器是否启用了GET支持：`@api_function(GET=True)`

**Q: GET请求参数类型转换失败？**
A: 检查查询参数值是否符合函数签名中定义的类型。例如，整数参数不能传递字母字符串

**Q: POST请求在支持GET的API上失败？**
A: 确保POST请求仍然按照原格式在JSON body中传递token和参数：`{"token": "...", "body": {...}}`

**Q: 重载API访问被拒绝？**
A: 重载功能需要提供有效的token。GET请求通过URL参数传递，POST请求通过请求体传递