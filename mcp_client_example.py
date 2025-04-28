"""MCP Client Example for DID WBA.

This script demonstrates how to use the MCP client to connect to the MCP server
and invoke the DID WBA tools.
"""
import asyncio
import json
from mcp.client.client import Client as MCPClient

async def main():
    """Run the MCP client example."""
    print("连接到 MCP 服务器...")
    
    # 连接到 MCP 服务器
    # 使用 stdio 传输连接到本地 MCP 服务器脚本
    async with MCPClient.connect("stdio://mcp_server.py") as client:
        print("已连接到 MCP 服务器")
        
        # 获取当前状态
        status = await client.get_resource("status://did-wba")
        print(f"当前状态:\n{json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # 启动服务器
        print("\n启动 DID WBA 服务器...")
        server_result = await client.invoke_tool("start_did_server")
        print(f"服务器启动结果: {server_result}")
        
        # 等待服务器启动
        await asyncio.sleep(2)
        
        # 启动客户端并发送消息
        print("\n启动 DID WBA 客户端...")
        client_result = await client.invoke_tool(
            "start_did_client", 
            {"message": "你好，这是通过 MCP 客户端发送的测试消息"}
        )
        print(f"客户端启动结果: {client_result}")
        
        # 等待并获取连接事件
        print("\n等待连接事件...")
        print("(最多等待 30 秒，如果没有新事件将超时)")
        events = await client.invoke_tool(
            "get_connection_events", 
            {"wait_for_new": True}
        )
        print(f"连接事件:\n{json.dumps(events, indent=2, ensure_ascii=False)}")
        
        # 停止客户端
        print("\n停止 DID WBA 客户端...")
        stop_client_result = await client.invoke_tool("stop_did_client")
        print(f"客户端停止结果: {stop_client_result}")
        
        # 停止服务器
        print("\n停止 DID WBA 服务器...")
        stop_server_result = await client.invoke_tool("stop_did_server")
        print(f"服务器停止结果: {stop_server_result}")
        
        # 再次获取状态
        status = await client.get_resource("status://did-wba")
        print(f"\n最终状态:\n{json.dumps(status, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(main())