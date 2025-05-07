"""DID WBA Web API - 为Web界面提供API接口"""
import asyncio
import json
import logging
import os
import threading
import time
import re
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import AsyncAzureOpenAI
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 导入anp_llmapp_web中的功能
from web_anp_llmapp import (
    resp_start, resp_stop,
    start_chat, stop_chat,
    chat_to_ANP,
    server_thread, chat_thread,
    server_running, chat_running,
    client_chat_messages, client_new_message_event
)

# 创建FastAPI应用
app = FastAPI(title="DID WBA Web API", description="为DID WBA Web界面提供API接口")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static/chat"), name="static")

# 定义请求和响应模型
class MessageRequest(BaseModel):
    message: str
    isAgentCommand: bool = False
    isRecommendation: bool = False
    agentInfo: Optional[Dict[str, Any]] = None

class BookmarkRequest(BaseModel):
    name: str

class Bookmark(BaseModel):
    id: str
    name: str
    did: Optional[str] = None
    url: Optional[str] = None
    port: Optional[str] = None
    discovery: Optional[str] = None

# 存储智能体书签
bookmarks: List[Bookmark] = []

# 存储聊天历史
chat_history: List[Dict[str, Any]] = []

# 上次检查智能体消息的时间
last_agent_check_time = 0

# 在send_message函数中添加对isRecommendation的处理
@app.post("/api/chat/send")
async def send_message(request: MessageRequest):
    global chat_running, chat_history
    try:
        # 从anp_llmapp_web模块获取最新的聊天状态
        from web_anp_llmapp import chat_running as current_chat_running
        chat_running = current_chat_running
        
        if not chat_running:
            return {"success": False, "message": "请先启动聊天"}
        
        message = request.message
        
        # 添加用户消息到聊天历史
        chat_history.append({
            "type": "user",
            "message": message,
            "timestamp": time.time()
        })
        
        # 如果是智能体推荐请求
        if request.isRecommendation:
            try:
                # 直接调用大模型处理推荐请求
                response = await llm_handler(message, chat_history)
                
                # 添加助手回复到聊天历史
                chat_history.append({
                    "type": "assistant",
                    "message": response,
                    "timestamp": time.time()
                })
                
                # 保存聊天历史
                save_chat_history()
                
                return {"success": True, "response": response}
            except Exception as e:
                logging.error(f"智能体推荐处理出错: {e}")
                fallback_response = f"抱歉，无法完成推荐: {str(e)}"
                return {"success": False, "message": fallback_response}
        # 如果是智能体命令
        elif request.isAgentCommand:
            parts = message.strip().split(" ", 1)
            agentname = parts[0].strip().split("@", 1)
            agentname = agentname[1]
            
            # 默认消息
            custom_msg = "ANPbot的问候，请二十字内回复我"
            if len(parts) > 1 and parts[1].strip():
                custom_msg = parts[1].strip()
            
            # 优先使用前端传递的智能体信息
            if request.agentInfo:
                agent_info = request.agentInfo
                agentname = agent_info.get('name')
                did = agent_info.get('did')
                url = agent_info.get('url')
                port = agent_info.get('port')
                
                # 确保port是字符串类型
                if port is not None:
                    port = str(port)
                    
                print(f"使用前端传递的智能体信息 - 名称:{agentname} DID:{did} 地址:{url} 端口:{port}")
                
                # 设置环境变量
                if port:
                    os.environ['target-port'] = port
                if url:
                    os.environ['target-host'] = url
                    
                # 获取token，如果环境变量中不存在则使用None
                token = os.environ.get('did-token', None)
                
                # 发送到ANP服务器
                print(f"将向智能体发送消息: {custom_msg}")
                chat_running = False
                chat_to_ANP(custom_msg, token=token)
                
                # 添加系统消息到聊天历史
                chat_history.append({
                    "type": "system",
                    "message": "已发送到智能体，请等待回复（可能需要刷新页面查看）",
                    "timestamp": time.time()
                })
                
                # 保存聊天历史
                save_chat_history()
                
                return {"success": True, "response": "已发送到智能体，请等待回复（可能需要刷新页面查看）"}
            else:
                # 从本地文件读取智能体信息（兼容旧版本）
                bookmark_config_dir = os.path.dirname(os.path.abspath(__file__))
                bookmark_config_dir = os.path.join(bookmark_config_dir, "anp_core", "anp_bookmark")
                os.makedirs(bookmark_config_dir, exist_ok=True)
                bookmark_config_file = os.path.join(bookmark_config_dir, f"{agentname}.js")
                
                if os.path.exists(bookmark_config_file):
                    # 读取已有的配置文件
                    print(f"找到智能体书签文件: {bookmark_config_file}")
                    with open(bookmark_config_file, 'r', encoding='utf-8') as f:
                        config_data = json.loads(f.read())
                        agentname = config_data.get('name')
                        did = config_data.get('did')
                        url = config_data.get('url')
                        port = config_data.get('port')
                        # 确保port是字符串类型
                        if port is not None:
                            port = str(port)
                    print(f"使用{agentname}智能体DID: {did}地址：{url}端口：{port}通讯")
                    
                    # 设置环境变量
                    if port:
                        os.environ['target-port'] = port
                    if url:
                        os.environ['target-host'] = url
                        
                    # 获取token，如果环境变量中不存在则使用None
                    token = os.environ.get('did-token', None)
                    
                    # 发送到ANP服务器
                    print(f"将向智能体发送消息: {custom_msg}")
                    chat_running = False
                    chat_to_ANP(custom_msg, token=token)
                    
                    # 添加系统消息到聊天历史
                    chat_history.append({
                        "type": "system",
                        "message": "已发送到智能体，请等待回复（可能需要刷新页面查看）",
                        "timestamp": time.time()
                    })
                    
                    # 保存聊天历史
                    save_chat_history()
                    
                    return {"success": True, "response": "已发送到智能体，请等待回复（可能需要刷新页面查看）"}
                else:
                    # 书签文件不存在
                    error_msg = f"找不到智能体书签文件: {agentname}"
                    print(error_msg)
                    
                    # 添加错误消息到聊天历史
                    chat_history.append({
                        "type": "system",
                        "message": error_msg,
                        "timestamp": time.time()
                    })
                    
                    # 保存聊天历史
                    save_chat_history()
                    
                    return {"success": False, "message": error_msg}
        else:
            # 普通消息，使用大模型处理
            try:
                # 调用大模型处理函数
                response = await llm_handler(message, chat_history)
                
                # 添加助手回复到聊天历史
                chat_history.append({
                    "type": "assistant",
                    "message": "localAI" + response,
                    "timestamp": time.time()
                })
                
                # 保存聊天历史
                save_chat_history()
                
                return {"success": True, "response": response}
            except Exception as e:
                logging.error(f"大模型处理出错: {e}")
                # 如果大模型处理失败，返回简单回复
                fallback_response = f"抱歉，处理您的消息时出现了问题: {str(e)}"
                
                # 添加助手回复到聊天历史
                chat_history.append({
                    "type": "assistant",
                    "message": fallback_response,
                    "timestamp": time.time()
                })
                
                # 保存聊天历史
                save_chat_history()
                
                return {"success": True, "response": fallback_response}
    except Exception as e:
        logging.error(f"发送消息出错: {e}")
        return {"success": False, "message": str(e)}

# 保存聊天历史到文件
def save_chat_history():
    try:
        history_file = Path(__file__).parent / "chat_history.json"
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存聊天历史出错: {e}")

# 加载聊天历史
def load_chat_history():
    global chat_history
    try:
        history_file = Path(__file__).parent / "chat_history.json"
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                chat_history = json.load(f)
    except Exception as e:
        logging.error(f"加载聊天历史出错: {e}")
        chat_history = []

# 根路径 - 返回静态HTML页面
@app.get("/")
async def read_root():
    return FileResponse("static/chat/index.html")

# 检查是否有新的智能体消息
def check_agent_messages():
    global chat_history, last_agent_check_time
    try:
        # 从web_anp_llmapp模块获取最新的客户端消息
        from web_anp_llmapp import client_chat_messages
        
        # 如果没有新消息，直接返回
        if not client_chat_messages:
            return
        
        # 获取当前时间
        current_time = time.time()
        
        # 只处理上次检查后的新消息
        for msg in client_chat_messages:
            # 检查消息时间戳是否晚于上次检查时间
            if 'timestamp' in msg and msg['timestamp'] > last_agent_check_time:
                # 检查这条消息是否已经在聊天历史中
                if not any(h.get('timestamp') == msg.get('timestamp') for h in chat_history):
                    # 添加到聊天历史
                    chat_history.append({
                        "type": "assistant",
                        "message": msg.get('content', ''),
                        "timestamp": msg.get('timestamp'),
                        "from_agent": True
                    })
                    logging.info(f"添加智能体消息到聊天历史: {msg.get('content', '')}")
        
        # 更新上次检查时间
        last_agent_check_time = current_time
        
        # 保存聊天历史
        save_chat_history()
    except Exception as e:
        logging.error(f"检查智能体消息出错: {e}")

# 获取聊天历史
@app.get("/api/chat/history")
async def get_chat_history():
    # 先检查是否有新的智能体消息
    check_agent_messages()
    return {"success": True, "history": chat_history}

# 清除聊天历史
@app.post("/api/chat/clear-history")
async def clear_chat_history():
    global chat_history
    chat_history = []
    save_chat_history()
    return {"success": True}

# 服务器API
@app.get("/api/server/status")
async def get_server_status():
    # 直接从anp_core.server.server模块获取最新的服务器状态
    from anp_core.server.server import server_status
    # 更新全局变量以保持一致
    global server_running
    server_running = server_status.is_running()
    return {"running": server_running}

@app.post("/api/server/start")
async def start_server():
    global server_running
    try:
        if not server_running:
            result = resp_start()
            if result:
                # 直接从anp_core.server.server模块获取最新的服务器状态
                from anp_core.server.server import server_status
                server_running = server_status.is_running()
                return {"success": True}
            else:
                return {"success": False, "message": "服务器启动失败"}
        return {"success": True, "message": "服务器已经在运行"}
    except Exception as e:
        logging.error(f"启动服务器出错: {e}")
        return {"success": False, "message": str(e)}

@app.get("/api/status")
async def get_status():
    # 添加一个统一的状态API端点
    from anp_core.server.server import server_status
    # 更新全局变量以保持一致
    global server_running
    server_running = server_status.is_running()
    return {"server": server_running, "chat": chat_running}

@app.post("/api/server/stop")
async def stop_server():
    global server_running
    try:
        if server_running:
            # 如果聊天在运行，先停止聊天
            if chat_running:
                stop_chat()
            
            result = resp_stop()
            if result:
                return {"success": True}
            else:
                return {"success": False, "message": "服务器停止失败"}
        return {"success": True, "message": "服务器已经停止"}
    except Exception as e:
        logging.error(f"停止服务器出错: {e}")
        return {"success": False, "message": str(e)}

# 聊天API
@app.get("/api/chat/status")
async def get_chat_status():
    # 从anp_llmapp_web模块获取最新的聊天状态
    global chat_running
    from web_anp_llmapp import chat_running as current_chat_running
    chat_running = current_chat_running
    return {"running": chat_running}

@app.post("/api/chat/start")
async def start_chat_api():
    global chat_running, server_running
    try:
        # 先从server_status获取最新的服务器状态
        from anp_core.server.server import server_status
        server_running = server_status.is_running()
        
        # 添加日志以便调试
        logging.info(f"服务器状态检查: {server_running}")
        
        if not server_running:
            # 再次尝试获取服务器状态
            from anp_core.server.server import server_status
            server_running = server_status.is_running()
            logging.info(f"再次检查服务器状态: {server_running}")
            
            # 如果服务器确实没有运行，返回错误
            if not server_running:
                return {"success": False, "message": "请先启动服务器"}
        
        if not chat_running:
            # 启动聊天但不阻塞主线程
            threading.Thread(target=start_chat, daemon=True).start()
            # 等待聊天线程启动
            time.sleep(1)
            return {"success": True}
        return {"success": True, "message": "聊天已经在运行"}
    except Exception as e:
        logging.error(f"启动聊天出错: {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/chat/stop")
async def stop_chat_api():
    global chat_running
    try:
        if chat_running:
            stop_chat()
            return {"success": True}
        return {"success": True, "message": "聊天已经停止"}
    except Exception as e:
        logging.error(f"停止聊天出错: {e}")
        return {"success": False, "message": str(e)}

# 书签API
@app.get("/api/bookmarks")
async def get_bookmarks(url: Optional[str] = None):
    # 如果提供了URL，从URL加载书签
    if url:
        # 确保load_bookmarks函数已定义
        from web_api import load_bookmarks
        result = load_bookmarks(url)
        return result
    # 否则返回本地书签
    return {"success": True, "bookmarks": bookmarks}

@app.post("/api/bookmarks/add")
async def add_bookmark(request: BookmarkRequest):
    try:
        name = request.name
        
        # 检查是否已存在同名书签
        if any(b.name == name for b in bookmarks):
            return {"success": False, "message": "已存在同名书签"}
        
        # 创建新书签
        bookmark_id = name.lower().replace(" ", "_")
        new_bookmark = Bookmark(id=bookmark_id, name=name)
        bookmarks.append(new_bookmark)
        
        # 保存到文件
        bookmark_dir = Path(__file__).parent / "anp_core" / "anp_bookmark"
        bookmark_dir.mkdir(exist_ok=True, parents=True)
        
        bookmark_file = bookmark_dir / f"{bookmark_id}.js"
        with open(bookmark_file, "w", encoding="utf-8") as f:
            json.dump({
                "name": name,
                "did": "",
                "url": "",
                "port": ""
            }, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "bookmark": new_bookmark}
    except Exception as e:
        logging.error(f"添加书签出错: {e}")
        return {"success": False, "message": str(e)}

@app.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str):
    try:
        # 查找书签
        bookmark = next((b for b in bookmarks if b.id == bookmark_id), None)
        if not bookmark:
            return {"success": False, "message": "书签不存在"}
        
        # 从列表中删除
        bookmarks.remove(bookmark)
        
        # 删除文件
        bookmark_file = Path(__file__).parent / "anp_core" / "anp_bookmark" / f"{bookmark_id}.js"
        if bookmark_file.exists():
            bookmark_file.unlink()
        
        return {"success": True}
    except Exception as e:
        logging.error(f"删除书签出错: {e}")
        return {"success": False, "message": str(e)}

# 导入所需的库
import os
import httpx
import asyncio

# 添加大模型处理函数
async def llm_handler(message: str, chat_history: List[Dict[str, Any]]):
    """
    大模型处理函数，基于聊天历史和当前消息生成回复
    """
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    
    if not OPENROUTER_API_KEY:
        error_msg = "OpenRouter API key未配置，请在环境变量中设置OPENROUTER_API_KEY"
        return error_msg
    
    # 构建消息历史
    messages = [
        {"role": "system", "content": "你是一个智能助手，请根据用户的提问进行专业、简洁的回复。"}
    ]
    
    # 添加聊天历史
    for item in chat_history:
        if item["type"] == "user":
            messages.append({"role": "user", "content": item["message"]})
        elif item["type"] == "assistant" and not item.get("from_agent", False):
            messages.append({"role": "assistant", "content": item["message"]})
    
    # 确保最后一条消息是当前用户消息
    if not messages[-1]["role"] == "user" or not messages[-1]["content"] == message:
        messages.append({"role": "user", "content": message})
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": messages,
        "max_tokens": 512
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                error_msg = f"API请求失败: {resp.status_code} - {resp.text}"
                return error_msg
            
            response_data = resp.json()
            assistant_message = response_data["choices"][0]["message"]["content"]
            return assistant_message
    except Exception as e:
        error_msg = f"处理请求时出错: {str(e)}"
        return error_msg

# 启动服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# 加载已有的智能体书签
def load_bookmarks(url=None):
    global bookmarks
    bookmarks = []
    
    # 如果提供了URL，从URL获取书签数据
    if url:
        try:
            import requests
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for agent in data:
                    # 确保port是字符串类型
                    port = agent.get("port")
                    if port is not None:
                        port = str(port)
                    
                    bookmark = Bookmark(
                        id=agent.get("name", "").lower().replace(" ", "_"),
                        name=agent.get("name", ""),
                        did=agent.get("did"),
                        url=agent.get("url"),
                        port=port,
                        discovery=agent.get("discovery")
                    )
                    bookmarks.append(bookmark)
                return {"success": True, "bookmarks": bookmarks}
            else:
                logging.error(f"从URL加载书签失败: {response.status_code}")
                return {"success": False, "message": f"从URL加载书签失败: {response.status_code}"}
        except Exception as e:
            logging.error(f"从URL加载书签失败: {e}")
            return {"success": False, "message": str(e)}
    
    # 否则从本地文件加载
    bookmark_dir = Path(__file__).parent / "anp_core" / "anp_bookmark"
    bookmark_dir.mkdir(exist_ok=True, parents=True)
    
    for file in bookmark_dir.glob("*.js"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 确保port是字符串类型
                port = data.get("port")
                if port is not None:
                    port = str(port)
                
                bookmark = Bookmark(
                    id=file.stem,
                    name=data.get("name", file.stem),
                    did=data.get("did"),
                    url=data.get("url"),
                    port=port,
                    discovery=data.get("discovery")
                )
                bookmarks.append(bookmark)
        except Exception as e:
            logging.error(f"加载书签文件 {file} 出错: {e}")
    
    return {"success": True, "bookmarks": bookmarks}

# 启动时加载书签
@app.on_event("startup")
def startup_event():
    # load_bookmarks()
    # 加载聊天历史（如果有）
    load_chat_history()
    # 启动智能体消息检查线程
    threading.Thread(target=check_agent_messages_thread, daemon=True).start()

# 检查智能体消息的线程函数
def check_agent_messages_thread():
    while True:
        try:
            check_agent_messages()
        except Exception as e:
            logging.error(f"检查智能体消息出错: {e}")
        time.sleep(2)  # 每2秒检查一次

# 检查是否有新的智能体消息
def check_agent_messages():
    global chat_history, last_agent_check_time
    try:
        # 从web_anp_llmapp模块获取最新的客户端消息
        from web_anp_llmapp import client_chat_messages
        
        # 如果没有新消息，直接返回
        if not client_chat_messages:
            return
        
        # 获取当前时间
        current_time = time.time()
        
        # 只处理上次检查后的新消息
        for msg in client_chat_messages:
            # 检查消息时间戳是否晚于上次检查时间
            if 'timestamp' in msg and msg['timestamp'] > last_agent_check_time:
                # 检查这条消息是否已经在聊天历史中
                if not any(h.get('timestamp') == msg.get('timestamp') for h in chat_history):
                    # 添加到聊天历史
                    chat_history.append({
                        "type": "assistant",
                        "message": msg.get('content', ''),
                        "timestamp": msg.get('timestamp'),
                        "from_agent": True
                    })
                    logging.info(f"添加智能体消息到聊天历史: {msg.get('content', '')}")
        
        # 更新上次检查时间
        last_agent_check_time = current_time
        
        # 保存聊天历史
        save_chat_history()
    except Exception as e:
        logging.error(f"检查智能体消息出错: {e}")

# 定义发现智能体请求模型
class DiscoverAgentRequest(BaseModel):
    bookmark_id: str
    url: str
    port: str

# 添加发现智能体API
@app.post("/api/discoveragent")
async def discoveragent(request: DiscoverAgentRequest):
    try:
        # 添加调试日志
        logging.info("开始处理发现智能体请求")
        
        # 获取请求数据
        bookmark_id = request.bookmark_id
        url = request.url
        port = request.port
        
        # 处理请求逻辑
        logging.info(f"处理智能体发现请求: bookmark_id={bookmark_id}, url={url}, port={port}")
        
        # 查找书签
        bookmark = next((b for b in bookmarks if b.id == bookmark_id), None)
        if not bookmark:
            return {"success": False, "message": "找不到指定的书签"}
        
        # 更新书签信息
        bookmark.url = url
        bookmark.port = port
        bookmark.discovery = "completed"
        
        # 保存到文件
        bookmark_dir = Path(__file__).parent / "anp_core" / "anp_bookmark"
        bookmark_file = bookmark_dir / f"{bookmark_id}.js"
        
        with open(bookmark_file, "w", encoding="utf-8") as f:
            json.dump({
                "name": bookmark.name,
                "did": bookmark.did or "",
                "url": url,
                "port": port
            }, f, ensure_ascii=False, indent=2)
        
        return {"success": True}
    except Exception as e:
        logging.error(f"处理发现智能体请求出错: {e}")
        return {"success": False, "message": str(e)}
    finally:
        logging.info("处理发现智能体请求完成")

# 启动服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
