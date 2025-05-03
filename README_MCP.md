# DID WBA MCP 服务器使用指南

本文档介绍如何使用 Model Context Protocol (MCP) 服务器来控制 DID WBA 客户端和服务器。

## 项目概述

本项目在原有 DID WBA 示例的基础上，添加了 MCP 服务器支持，将 `start_server` 和 `start_client` 功能封装为 MCP 工具，使其可以通过 MCP 协议进行调用。特别地，`start_server` 工具支持长连接，并会将连接事件通知给 MCP 工具调用者。

## 文件说明

- `mcp_stdio_server.py`: MCP 服务器实现，封装了 DID WBA 服务器和客户端功能
- `mcp_stdio_client.py`: MCP 客户端实现，用于通过stdio与MCP服务器通信
- `mcp_client_example.py`: MCP 客户端示例，演示如何使用 MCP 客户端调用工具
- `setup_mcp.py`: 安装和设置脚本，帮助安装依赖和设置环境
- `MCP_README.md`: 详细的 MCP 服务器使用文档

## 快速开始

### 安装依赖

请确保您使用的是 Python 3.10 或更高版本，然后运行：

```bash
python setup_mcp.py --install
```

### 运行 MCP 服务器

```bash
python setup_mcp.py --run
```

或者直接运行：

```bash
python mcp_server.py
```

### 运行客户端示例

```bash
python setup/setup_mcp.py --example
```

或者直接运行：

```bash
python mcp_stdio_client.py
```

### 安装到 Claude Desktop

```bash
python setup_mcp.py --install-claude
```

或者直接运行：

```bash
mcp install mcp_server.py
```

## MCP 工具说明

### 1. start_did_server

启动 DID WBA 服务器，支持长连接。

**参数：**
- `port`（可选）：服务器端口号

### 2. stop_did_server

停止 DID WBA 服务器。

### 3. start_did_client

启动 DID WBA 客户端。

**参数：**
- `port`（可选）：目标服务器端口号
- `unique_id`（可选）：客户端唯一标识符
- `message`（可选）：要发送的自定义消息

### 4. stop_did_client

停止 DID WBA 客户端。

### 5. get_connection_events

获取 DID WBA 服务器的连接事件，支持等待新事件。

**参数：**
- `wait_for_new`（可选）：是否等待新事件，默认为 false

## 注意事项

1. MCP 服务器不会影响原有的 DID WBA 功能，可以同时使用。
2. 连接事件通知功能通过 `get_connection_events` 工具提供，可以选择等待新事件或立即返回当前事件列表。
3. 更多详细信息请参考 `MCP_README.md` 文档。

## 示例：在 Claude Desktop 中使用

安装 MCP 服务器到 Claude Desktop 后，可以使用以下提示：

```
启动 DID WBA 服务器，然后启动客户端发送消息 "你好，这是一条测试消息"，最后获取连接事件。
```

## 示例：在自定义 LLM 应用中使用

```python
from mcp.client.client import Client as MCPClient

async with MCPClient.connect("stdio://mcp_server.py") as client:
    # 启动服务器
    result = await client.invoke_tool("start_did_server")
    print(f"服务器启动结果: {result}")
    
    # 启动客户端
    result = await client.invoke_tool(
        "start_did_client", 
        {"message": "你好，这是一条测试消息"}
    )
    print(f"客户端启动结果: {result}")
    
    # 等待并获取连接事件
    events = await client.invoke_tool(
        "get_connection_events", 
        {"wait_for_new": True}
    )
    print(f"连接事件: {events}")
```