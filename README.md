# anp协议认证通信开发示例

[English Version](README_EN.md)

这是一个使用FastAPI和Agent_Connect库实现的DID WBA方法示例，同时支持客户端和服务器功能。

## 功能特点

### resp（服务端）功能
- anp协议认证：DID WBA首次认证，Bearer Token会话认证
- anp自然语言通信：/wba/anp-nlp接口进行通信

### req（客户端）功能
- 自动生成DID和密钥或加载已有身份
- 向resp发起首次认证和令牌申请
- 向resp的anp-nlp接口发起消息
server
## 安装方法

### 环境准备

1. 克隆项目
2. 创建环境配置文件
   ```
   cp .env.example .env
   ```
3. 编辑.env文件，设置必要的配置项

### 使用Poetry安装依赖

```bash
# 激活虚拟环境(如果已存在)
source .venv/bin/activate

# 安装依赖
poetry install
```

## 运行方法

本项目提供三种不同的运行方式：

### 1. 直接调用ANP接口

通过运行`anp_llmapp.py`，直接调用`anp_core`中的ANP接口：

```bash
python anp_llmapp.py
```

### 2. 通过stdio调用MCP接口

运行`mcp_stdio_client.py`，通过stdio调用`mcp_stdio_server.py`封装的ANP接口，可以调试完整MCP流程：

```bash
# 启动服务端
python -m anp_mcpwrapper.mcp_stdio_server

# 启动客户端
python -m anp_mcpwrapper.mcp_stdio_client
```

### 3. 通过SSE接口调用

将`mcp_stdio_server.py`启动为SSE服务，通过SSE接口调用：

```bash
python -m anp_mcpwrapper.mcp_stdio_server -t sse
```

**注意**：方法2和方法3均已在TRAE环境中配置测试成功。

## 项目结构

```
.
├── anp_core/            # 封装便于开发者调用的ANP接口
├── anp_mcpwrapper/      # 实现MCP接口的对接
├── api/                 # API路由模块
├── core/                # 应用框架
├── doc/                 # 文档说明和测试用key
├── examples/            # 未来增加面向开发者的更多示例
├── utils/               # 工具函数
├── logs/                # 日志文件
├── setup/               # 后续增加安装方案（当前暂时无用）
├── anp_llmapp.py        # 直接调用ANP接口的应用
└── anp_llmagent.py      # 计划开发为开箱即用的agent
```

## 项目说明

1. **anp_core**：封装便于开发者调用的ANP接口，当前DID认证为本地测试，下一版本将增加实用的DID服务

2. **anp_mcpwrapper**：实现了MCP接口的对接，目前在TRAE环境中测试成功，Claude环境测试不成功

3. **api/core**：应用框架，提供API路由和核心配置

4. **doc**：文档说明和测试用密钥

5. **examples**：未来将增加面向开发者的更多示例

6. **utils/logs**：工具函数和日志文件

7. **setup**：后续将增加安装方案，当前文件暂时无用

8. **anp_llmagent.py**：计划开发为开箱即用的agent，与`anp_llmapp.py`/MCP调用可以互通

## API端点

- `GET /agents/example/ad.json`: 获取代理描述信息
- `GET /ad.json`: 获取广告JSON数据，需要进行鉴权
- `POST /auth/did-wba`: DID WBA首次鉴权
- `GET /auth/verify`: 验证Bearer Token
- `GET /wba/test`: 测试DID WBA认证
- `POST /wba/anp-nlp`: ANP自然语言通信接口
- `GET /wba/user/{user_id}/did.json`: 获取用户DID文档
- `PUT /wba/user/{user_id}/did.json`: 保存用户DID文档

## 工作流程

### 服务器流程
1. 启动服务器，监听请求
2. 接收DID WBA认证请求，验证签名
3. 生成并返回访问令牌
4. 处理后续使用令牌的请求

### 客户端流程
1. 生成或加载DID文档和私钥
2. 向服务器发送带有DID WBA签名头的请求
3. 接收令牌并保存
4. 使用令牌发送后续请求

## 鉴权说明

示例实现了两种鉴权方式：

1. **首次DID WBA鉴权**：根据DID WBA规范进行签名验证
2. **Bearer Token鉴权**：通过JWT令牌进行后续请求鉴权

详细的鉴权流程请参考代码实现和[DID WBA规范](https://github.com/agent-network-protocol/AgentNetworkProtocol/blob/main/chinese/03-did%3Awba%E6%96%B9%E6%B3%95%E8%A7%84%E8%8C%83.md)
