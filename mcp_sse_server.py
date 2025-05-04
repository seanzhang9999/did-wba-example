"""MCP Server for DID WBA Example.

This module implements a Model Context Protocol (MCP) server that exposes
the DID WBA client and server functionalities as MCP tools.
"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from loguru import logger
from mcp.server.fastmcp import FastMCP, Context

# Import DID WBA server and client functions
from did_server import (
    start_server,
    stop_server,
    start_client,
    stop_client,
    server_running,
    client_running,
    client_chat_messages,
    client_new_message_event
)

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
import uvicorn

# Import server-side message handling
from api.anp_nlp_router import anp_nlp_resp_messages, anp_nlp_resp_new_message_event as server_new_message_event

# Store connection events for notification
connection_events = []
new_connection_event = asyncio.Event()

logger.add("logs/mcp_stdio_server.log", rotation="1000 MB", retention="7 days", encoding="utf-8")


@dataclass
class AppContext:
    """Application context for MCP server."""
    server_status: Dict[str, Any] = None
    client_status: Dict[str, Any] = None
    connection_events: List[Dict[str, Any]] = None


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context."""
    # Initialize on startup
    app_context = AppContext(
        server_status={"running": False, "port": None},
        client_status={"running": False, "port": None},
        connection_events=[]
    )

    # Start connection event listener
    asyncio.create_task(connection_event_listener(app_context))

    try:
        yield app_context
    finally:
        # Cleanup on shutdown
        if app_context.server_status.get("running"):
            stop_server()
        if app_context.client_status.get("running"):
            stop_client()


# Pass lifespan to server
mcp = FastMCP("DID WBA MCP Server", lifespan=app_lifespan, port=8080)


async def connection_event_listener(app_context: AppContext):
    """Listen for connection events from both DID WBA client and server."""
    global client_chat_messages, client_new_message_event, connection_events, new_connection_event
    global anp_nlp_resp_messages, server_new_message_event

    # 创建两个任务，分别监听客户端和服务器端的消息
    while True:
        try:
            # 创建两个等待事件的任务
            client_task = asyncio.create_task(client_new_message_event.wait())
            server_task = asyncio.create_task(server_new_message_event.wait())

            # 等待任意一个任务完成
            done, pending = await asyncio.wait(
                [client_task, server_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 取消未完成的任务
            for task in pending:
                task.cancel()

            # 处理客户端消息
            if client_task in done and client_new_message_event.is_set():
                if client_chat_messages:
                    # 获取最新消息
                    latest_message = client_chat_messages[-1]
                    latest_message['source'] = 'client'  # 添加来源标记

                    # 添加到连接事件
                    connection_events.append(latest_message)
                    if len(connection_events) > 50:
                        connection_events = connection_events[-50:]

                    # 更新应用上下文
                    app_context.connection_events = connection_events

                    # 设置事件通知订阅者
                    new_connection_event.set()

                    # 重置客户端事件
                    client_new_message_event.clear()

            # 处理服务器端消息
            if server_task in done and server_new_message_event.is_set():
                if anp_nlp_resp_messages:
                    # 获取最新消息
                    latest_message = anp_nlp_resp_messages[-1]
                    latest_message['source'] = 'server'  # 添加来源标记

                    # 添加到连接事件
                    connection_events.append(latest_message)
                    if len(connection_events) > 50:
                        connection_events = connection_events[-50:]

                    # 更新应用上下文
                    app_context.connection_events = connection_events

                    # 设置事件通知订阅者
                    new_connection_event.set()

                    # 重置服务器端事件
                    server_new_message_event.clear()

            # 小延迟防止CPU过载
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in connection event listener: {e}")
            await asyncio.sleep(1)  # 出错后等待一段时间再重试


@mcp.tool()
async def start_did_server(ctx: Context, port: Optional[int] = None) -> Dict[str, Any]:
    """Start the DID WBA server.
    
    Args:
        port: Optional server port number (default: from settings)
        
    Returns:
        Dict with server status information
    """
    global server_running
    app_context = ctx.request_context.lifespan_context

    if server_running:
        return {"status": "already_running", "message": "服务器已经在运行中"}

    try:
        logger.info(f"Starting DID WBA server on port {port if port else 'default'}")
        if not start_server(port=port):  # 检查启动返回值
            raise RuntimeError("服务器启动失败")

        max_retries = 10  # 增加重试次数
        for _ in range(max_retries):
            if server_running:
                break
            await asyncio.sleep(1)  # 增加等待间隔
        else:
            raise RuntimeError("Server did not start in time. Wait server_running event to check status.")

        app_context.server_status = {"running": True, "port": port}
        return {
            "status": "success",
            "message": f"服务器已在端口 {port if port else '默认端口'} 启动",
            "is_running": True
        }
    except Exception as e:
        logger.error(f"Server start failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "is_running": False
        }


@mcp.tool()
async def stop_did_server(ctx: Context) -> Dict[str, Any]:
    """Stop the DID WBA server.
    
    Returns:
        Dict with server status information
    """
    app_context = ctx.request_context.lifespan_context

    # Check if server is running
    if not server_running:
        return {"status": "not_running", "message": "服务器未运行"}

    # Stop the server
    stop_server()

    # Update app context
    app_context.server_status = {"running": False, "port": None}

    return {
        "status": "success",
        "message": "服务器已关闭",
        "is_running": False
    }


@mcp.tool()
async def start_did_client(ctx: Context, port: Optional[int] = None, unique_id: Optional[str] = None,
                           message: Optional[str] = None) -> Dict[str, Any]:
    """Start the DID WBA client.
    
    Args:
        port: Optional target server port number
        unique_id: Optional unique identifier for the client
        message: Optional custom message to send
        
    Returns:
        Dict with client status information
    """
    global client_running

    app_context = ctx.request_context.lifespan_context

    # Check if client is already running
    if client_running:
        return {"status": "already_running", "message": "客户端已经在运行中"}

    # Start the client
    start_client(port=port, unique_id_arg=unique_id, silent=False, from_chat=False, msg=message)

    # Update app context
    app_context.client_status = {"running": True, "port": port, "unique_id": unique_id}

    return {
        "status": "success",
        "message": f"客户端已启动，目标端口: {port if port else '默认端口'}",
        "is_running": True
    }


@mcp.tool()
async def stop_did_client(ctx: Context) -> Dict[str, Any]:
    """Stop the DID WBA client.
    
    Returns:
        Dict with client status information
    """
    app_context = ctx.request_context.lifespan_context

    # Check if client is running
    if not client_running:
        return {"status": "not_running", "message": "客户端未运行"}

    # Stop the client
    stop_client()

    # Update app context
    app_context.client_status = {"running": False, "port": None, "unique_id": None}

    return {
        "status": "success",
        "message": "客户端已关闭",
        "is_running": False
    }


@mcp.tool()
async def get_connection_events(ctx: Context, wait_for_new: bool = False, timeout: int = 300) -> Dict[str, Any]:
    """Get connection events from the DID WBA server.
    
    Args:
        wait_for_new: Whether to wait for new events
        timeout: Timeout in seconds for waiting for new events

    Returns:
        Dict with connection events
    """
    global connection_events, new_connection_event

    try:
        if wait_for_new:
            # Wait for new connection event with timeout
            try:
                await asyncio.wait_for(new_connection_event.wait(), timeout=timeout)
                # Reset event for next notification
                new_connection_event.clear()
            except asyncio.TimeoutError:
                logging.warning("等待新连接事件超时")
                return {
                    "status": "timeout",
                    "message": "等待新连接事件超时",
                    "events": connection_events,
                    "error": None
                }

        return {
            "status": "success",
            "message": "获取连接事件成功",
            "events_number": len(connection_events),
            "events": connection_events,
            "error": None
        }
    except Exception as e:
        logging.error(f"获取连接事件时发生错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"获取连接事件失败: {str(e)}",
            "events_number": 0,
            "events": [],
            "error": str(e)
        }


@mcp.resource("status://did-wba")
async def get_status() -> Dict[str, Any]:
    """Get the current status of the DID WBA server and client.
    
    Returns:
        Dict with status information
    """
    global server_running, client_running, connection_events
    return {
        "server": {
            "running": server_running,
            "status": {"running": server_running}
        },
        "client": {
            "running": client_running,
            "status": {"running": client_running}
        },
        "connection_events_count": len(connection_events)
    }


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """创建支持SSE的Starlette应用"""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    # 获取底层MCP服务器
    mcp_server = mcp._mcp_server

    # 创建支持SSE的Starlette应用
    starlette_app = create_starlette_app(mcp_server, debug=True)

    port = 8080
    print(f"Starting MCP server with SSE transport on port {port}...")
    print(f"SSE endpoint available at: http://localhost:{port}/sse")

    # 使用uvicorn运行服务器
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
