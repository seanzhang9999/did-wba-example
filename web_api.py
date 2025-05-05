"""DID WBA Web API - 为Web界面提供API接口"""
import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 导入anp_llmapp_web中的功能
from anp_llmapp_web import (
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
app.mount("/static", StaticFiles(directory="static"), name="static")

# 定义请求和响应模型
class MessageRequest(BaseModel):
    message: str
    isAgentCommand: bool = False

class BookmarkRequest(BaseModel):
    name: str

class Bookmark(BaseModel):
    id: str
    name: str
    did: Optional[str] = None
    url: Optional[str] = None
    port: Optional[str] = None

# 存储智能体书签
bookmarks: List[Bookmark] = []

# 存储聊天历史
chat_history: List[Dict[str, Any]] = []

# 上次检查智能体消息的时间
last_agent_check_time = 0

# 加载已有的智能体书签
def load_bookmarks():
    global bookmarks
    bookmark_dir = Path(__file__).parent / "anp_core" / "anp_bookmark"
    bookmark_dir.mkdir(exist_ok=True, parents=True)
    
    for file in bookmark_dir.glob("*.js"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                bookmark = Bookmark(
                    id=file.stem,
                    name=data.get("name", file.stem),
                    did=data.get("did"),
                    url=data.get("url"),
                    port=data.get("port")
                )
                bookmarks.append(bookmark)
        except Exception as e:
            logging.error(f"加载书签文件 {file} 出错: {e}")

# 启动时加载书签
@app.on_event("startup")
def startup_event():
    load_bookmarks()
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

# 检查智能体消息并添加到聊天历史
def check_agent_messages():
    global last_agent_check_time, chat_history
    
    # 检查是否有新的智能体消息
    if client_chat_messages:
        current_time = time.time()
        new_messages = []
        
        # 找出新消息
        for msg in client_chat_messages:
            # 只处理成功的消息
            if msg.get("status") == "success" and msg.get("type") == "anp_nlp":
                # 添加到聊天历史
                chat_history.append({
                    "type": "assistant",
                    "message": msg.get("assistant_message", "[无回复]"),
                    "timestamp": current_time,
                    "from_agent": True
                })
                new_messages.append(msg)
        
        # 如果有新消息，保存聊天历史
        if new_messages:
            # 从client_chat_messages中移除已处理的消息
            for msg in new_messages:
                if msg in client_chat_messages:
                    client_chat_messages.remove(msg)
            
            # 保存聊天历史
            save_chat_history()
            
            # 更新最后检查时间
            last_agent_check_time = current_time

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
    return FileResponse("static/index.html")

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
    from anp_llmapp_web import chat_running as current_chat_running
    chat_running = current_chat_running
    return {"running": chat_running}

@app.post("/api/chat/start")
async def start_chat_api():
    global chat_running, server_running
    try:
        # 先从server_status获取最新的服务器状态
        from anp_core.server.server import server_status
        server_running = server_status.is_running()
        
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

@app.post("/api/chat/send")
async def send_message(request: MessageRequest):
    global chat_running, chat_history
    try:
        # 从anp_llmapp_web模块获取最新的聊天状态
        from anp_llmapp_web import chat_running as current_chat_running
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
        
        # 如果是智能体命令
        if request.isAgentCommand:
            # 发送到ANP服务器
            chat_to_ANP(message)
            
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
            # 普通消息，直接发送到聊天线程
            # 这里简单返回一个回复，实际应用中可能需要更复杂的处理
            response = f"收到消息: {message}"
            
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
        logging.error(f"发送消息出错: {e}")
        return {"success": False, "message": str(e)}

# 书签API
@app.get("/api/bookmarks")
async def get_bookmarks():
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

# 启动服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)