"""
Chat API router for OpenRouter LLM chat relay.
"""
from nt import environ
import os
import logging
import httpx
import asyncio
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from core.config import Settings

# 全局变量，用于存储最新的聊天消息
chat_messages = []
# 事件，用于通知聊天线程有新消息
new_message_event = asyncio.Event()

router = APIRouter(tags=["chat"])

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # 用户需在环境变量中配置免费key

class ChatRequest(BaseModel):
    message: str

@router.post("/wba/anp-nlp", summary="ANP的NLP接口，Chat with OpenRouter LLM")
async def anp_nlp_service(
    chat_req: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Relay chat message to OpenRouter LLM and return the response.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not chat_req.message:
        raise HTTPException(status_code=400, detail="Empty message")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",  # 免费模型
        "messages": [{"role": "user", "content": chat_req.message}],
        "max_tokens": 512
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logging.error(f"OpenRouter error: {resp.text}")
                raise HTTPException(status_code=500, detail="OpenRouter query failed")
            data = resp.json()
            # 确保data是预期的格式，并安全地提取answer
            # if not isinstance(data, dict) or 'choices' not in data or not data['choices']:
            #    logging.error(f"Unexpected API response format: {data}")
            #    raise HTTPException(status_code=500, detail="Unexpected API response format")
            answer = data['choices'][0]['message']['content']
            
            # 添加消息到全局消息列表，并通知聊天线程
            message_data = {
                "type": "anp_nlp",
                "user_message": chat_req.message,
                "assistant_message": answer
            }
            await notify_chat_thread(message_data)
            
            return JSONResponse(content={"answer": answer})
    except Exception as e:
        message_data = {
                "type": "anp_nlp",
                "user_message": chat_req.message,
                "assistant_message": f"白嫖的OpenRouter生气了:{e}"
            }
        await notify_chat_thread(message_data)
        return JSONResponse(content={"answer":  f"白嫖的OpenRouter生气了:{e}"})
        # logging.error(f"Chat relay error: {e}")
        # raise HTTPException(status_code=500, detail="Chat relay failed")


async def notify_chat_thread(message_data: Dict[str, Any]):
    """
    通知聊天线程有新消息
    
    Args:
        message_data: 消息数据
    """
    global chat_messages, new_message_event
    
    # 添加消息到全局列表
    chat_messages.append(message_data)
    
    # 如果列表太长，保留最近的50条消息
    if len(chat_messages) > 50:
        chat_messages = chat_messages[-50:]
    
    # 设置事件，通知聊天线程
    new_message_event.set()
    
    # 在控制台显示通知
    logging.info(f"ANP-NLP请求: {message_data['user_message']}")
    logging.info(f"ANP-NLP响应: {message_data['assistant_message']}")
    
    # 打印到控制台，确保在聊天线程中可见
    import os
    port = os.environ.get("PORT", "9527")
    print(f"\n[ANP-NLP] 对方: {message_data['user_message']}")
    print(f"[ANP-NLP] 我方@{port}: {message_data['assistant_message']}\n")
    
    # 重置事件，为下一次通知做准备
    new_message_event.clear()