# -*- coding: utf-8 -*-
# MCP Client for DID WBA Example

import asyncio
import json
import os
from typing import List

from fastapi import status
from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextResourceContents, TextContent

logger.add("logs/mcp_client.log", rotation="1000 MB", retention="7 days", encoding="utf-8")


def get_status_data(status_contents: List[TextContent]):
    """解析状态数据
    
    Args:
        status_contents: 状态内容列表
        
    Returns:
        dict: 解析后的状态数据
    """
    assert len(status_contents) != 0, "状态返回数据为空"
    status_content = status_contents[0]
    status_data = {}
    try:
        status_data = json.loads(status_content.text)
    except json.JSONDecodeError:
        logger.warning("错误：服务器状态数据格式错误")

    return status_data


def get_text_content_data(text_contents: List[TextContent]):
    """解析文本内容数据
    
    Args:
        text_contents: 文本内容列表
        
    Returns:
        dict: 解析后的文本数据
    """
    assert len(text_contents) == 1, "MCPserver返回数据为空"
    text_content = text_contents[0]
    content_data = {}
    try:
        content_data = json.loads(text_content.text)
    except json.JSONDecodeError:
        logger.warning("错误：MCPserver返回的文本数据格式错误")
        ValueError("MCPserver返回的文本数据格式错误")
    return content_data


async def connect_to_mcp_server(server_path=None):
    """连接到MCP服务器
    
    Args:
        server_path: MCP服务器脚本路径，如果为None则使用默认路径
        
    Returns:
        tuple: (session, streams) 会话和流对象
    """
    # 获取服务器脚本路径
    if server_path is None:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(current_dir, "server", "mcp_stdio_server.py")
    logger.info(f"{server_path}")
    # 创建服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=[server_path]
    )

    logger.info("正在通过stdio建立与MCP服务器的连接...")
    # 使用异步上下文管理器语法
    async with stdio_client(server_params) as streams:
        session = await ClientSession(*streams).initialize()
        return session, streams


async def start_did_server(session, port=None):
    """启动DID WBA服务器
    
    Args:
        session: MCP客户端会话
        port: 可选的服务器端口号
        
    Returns:
        dict: 服务器启动结果
    """
    logger.info("启动DID WBA服务器...")
    params = {}
    if port is not None:
        params["port"] = port
        
    result = await session.call_tool("start_did_server", params)
    result_data = get_text_content_data(result.content)
    logger.info(f"服务器启动结果: {result_data}")
    
    return result_data


async def start_did_client(session, message=None, port=None, unique_id=None):
    """启动DID WBA客户端并发送消息
    
    Args:
        session: MCP客户端会话
        message: 要发送的消息
        port: 可选的目标服务器端口号
        unique_id: 可选的客户端唯一标识符
        
    Returns:
        dict: 客户端启动结果
    """
    logger.info("启动DID WBA客户端...")
    params = {}
    if message is not None:
        params["message"] = message
    if port is not None:
        params["port"] = port
    if unique_id is not None:
        params["unique_id"] = unique_id
        
    result = await session.call_tool("start_did_client", params)
    result_data = get_text_content_data(result.content)
    logger.info(f"客户端启动结果: {result_data}")
    
    return result_data


async def get_connection_events(session, wait_for_new=False, timeout=10):
    """获取连接事件
    
    Args:
        session: MCP客户端会话
        wait_for_new: 是否等待新事件
        timeout: 等待超时时间（秒）
        
    Returns:
        dict: 连接事件列表
    """
    logger.info("获取连接事件...")
    params = {}
    if wait_for_new:
        params["wait_for_new"] = True
    if timeout != 10:  # 只有当超时不是默认值时才添加
        params["timeout"] = timeout
        
    result = await session.call_tool("get_connection_events", params)
    result_data = get_text_content_data(result.content)
    
    return result_data


async def main():
    """主函数，演示MCP客户端的使用"""
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_path = os.path.join(current_dir, "server/mcp_stdio_server.py")
        
        # 连接到MCP服务器
        async with stdio_client(StdioServerParameters(
            command="python",
            args=[server_path]
        )) as streams:
            # 创建会话
            session = await ClientSession(*streams).initialize()
            
            try:
                # 列出可用工具
                logger.info("获取服务器可用工具列表...")
                response = await session.list_tools()
                logger.info(f"可用工具: {[tool.name for tool in response.tools]}")

                # 启动DID WBA服务器
                await start_did_server(session)
                await asyncio.sleep(2)

                # 启动DID WBA客户端并发送测试消息
                await start_did_client(session, message="你好，这是通过MCP客户端发送的测试消息")
                await asyncio.sleep(1)

                # 获取连接事件
                logger.info("等待并获取连接事件...")
                for i in range(5):  # 尝试获取5次事件
                    events_data = await get_connection_events(session, wait_for_new=(i > 0), timeout=10)
                    events = events_data.get("events", [])
                    
                    if events:
                        logger.info(f"收到 {len(events)} 个连接事件:")
                        for event in events:
                            logger.info(f"事件类型: {event.get('type')}")
                            if event.get('type') == 'anp_nlp':
                                logger.info(f"用户消息: {event.get('user_message')}")
                                logger.info(f"助手回复: {event.get('assistant_message')}")
                        break
                    else:
                        logger.info(f"未收到事件，等待中... ({i+1}/5)")
                        await asyncio.sleep(3)  # 增加等待时间
                
                # 停止服务器和客户端
                logger.info("停止DID WBA客户端...")
                await session.call_tool("stop_did_client")
                
                logger.info("停止DID WBA服务器...")
                await session.call_tool("stop_did_server")
            finally:
                # 关闭会话
                await session.close()
    except Exception as e:
        logger.error(f"MCP客户端运行出错: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())