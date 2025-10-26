import logging
import functools
import requests
import asyncio
from mcp.server.fastmcp import FastMCP

# -------------------------------
# 1. 日志配置
# -------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mcp-server")

# -------------------------------
# 2. 初始化 MCP 服务
# -------------------------------
mcp = FastMCP(
    name="mcp-server",
    host="0.0.0.0",
    port=9009,
)

# -------------------------------
# 3. 通用日志装饰器
# -------------------------------
def log_tool(func):
    """打印输入参数、返回值、异常，并保留原函数签名"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.debug(f"调用工具: {func.__name__}")
            logger.debug(f"输入参数: args={args}, kwargs={kwargs}")
            result = func(*args, **kwargs)
            logger.debug(f"返回结果: {result}")
            return result
        except asyncio.CancelledError:
            logger.warning(f"工具 {func.__name__} 执行中断（客户端断开连接）")
            raise
        except Exception as e:
            logger.exception(f"工具 {func.__name__} 执行出错: {e}")
            return {"success": False, "error": str(e)}
    return wrapper


# -------------------------------
# 4. 工具定义
# -------------------------------
@mcp.tool(name="initialize")
@log_tool
def initialize() -> dict:
    return {"status": "ok", "message": "MCP server initialized"}


@mcp.tool(name="list_tools")
@log_tool
def list_tools() -> dict:
    tools_info = []
    for tool in mcp._tools.values():
        try:
            params = {k: str(v.annotation) for k, v in tool.signature.parameters.items()}
        except Exception:
            params = {}
        tools_info.append({
            "name": tool.name,
            "description": getattr(tool, "description", ""),
            "parameters": params,
        })
    return {"tools": tools_info}


@mcp.tool(name="http_request")
@log_tool
def http_request(
    method: str,
    url: str,
    headers: dict = None,
    params: dict = None,
    data: dict = None,
    timeout: float = 10.0
) -> dict:
    """
    发起 HTTP 请求
    method: GET/POST/PUT/DELETE
    url: 请求 URL
    headers: 请求头
    params: URL 参数
    data: POST/PUT 数据
    timeout: 超时时间
    """
    method = method.upper()
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data,
            timeout=timeout
        )
        return {
            "success": True,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text[:5000],  # 避免日志过长
        }
    except asyncio.CancelledError:
        logger.warning("HTTP 请求被客户端中断")
        raise
    except Exception as e:
        logger.exception(f"HTTP request failed: {e}")
        return {"success": False, "error": str(e)}


# -------------------------------
# 5. 启动 MCP 服务
# -------------------------------
if __name__ == "__main__":
    logger.info("Starting MCP server on http://0.0.0.0:9009/mcp")
    try:
        mcp.run(transport="streamable-http", mount_path="/mcp")
    except asyncio.CancelledError:
        logger.warning("MCP Server stopped due to client disconnect")
    except Exception as e:
        logger.exception(f"MCP server 启动失败: {e}")
