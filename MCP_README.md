# DID WBA MCP 服务器

这个文档介绍了如何使用 Model Context Protocol (MCP) 服务器来控制 DID WBA 客户端和服务器。

## 什么是 MCP？

Model Context Protocol (MCP) 允许应用程序以标准化的方式为大语言模型 (LLM) 提供上下文，将提供上下文的关注点与实际的 LLM 交互分开。MCP 服务器可以：

- 通过资源（Resources）暴露数据（类似于 GET 端点，用于将信息加载到 LLM 的上下文中）
- 通过工具（Tools）提供功能（类似于 POST 端点，用于执行代码或产生副作用）
- 通过提示（Prompts）定义交互模式（用于 LLM 交互的可重用模板）

## 安装依赖

首先，确保已安装 MCP Python SDK：

```bash
pip install "mcp[cli]"
```

## 使用 MCP 服务器

### 启动 MCP 服务器

```bash
python mcp_server.py
```

或者使用 MCP CLI：

```bash
mcp dev mcp_server.py
```

### 可用工具

MCP 服务器提供以下工具：

#### 1. start_did_server

启动 DID WBA 服务器。

**参数：**
- `port`（可选）：服务器端口号

**返回：**
- 服务器状态信息

#### 2. stop_did_server

停止 DID WBA 服务器。

**返回：**
- 服务器状态信息

#### 3. start_did_client

启动 DID WBA 客户端。

**参数：**
- `port`（可选）：目标服务器端口号
- `unique_id`（可选）：客户端唯一标识符
- `message`（可选）：要发送的自定义消息

**返回：**
- 客户端状态信息

#### 4. stop_did_client

停止 DID WBA 客户端。

**返回：**
- 客户端状态信息

#### 5. get_connection_events

获取 DID WBA 服务器的连接事件。

**参数：**
- `wait_for_new`（可选）：是否等待新事件，默认为 false

**返回：**
- 连接事件列表

### 可用资源

#### 1. status://did-wba

获取 DID WBA 服务器和客户端的当前状态。

**返回：**
- 服务器和客户端的状态信息
- 连接事件计数

## 使用示例

### 在 Claude Desktop 中使用

1. 安装 MCP 服务器到 Claude Desktop：

```bash
mcp install mcp_server.py
```

2. 在 Claude Desktop 中，你可以使用以下提示：

```
启动 DID WBA 服务器，然后启动客户端发送消息 "你好，这是一条测试消息"，最后获取连接事件。
```

### 在自定义 LLM 应用中使用

你可以使用 MCP 客户端 API 连接到 MCP 服务器：

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

## 注意事项

1. 服务器工具 `start_did_server` 会启动一个长连接服务，它将保持运行直到调用 `stop_did_server`。
2. 连接事件通知功能通过 `get_connection_events` 工具提供，可以选择等待新事件或立即返回当前事件列表。
3. 所有工具都保持了原有 `start_client` 和 `start_server` 的功能，不会破坏现有功能。