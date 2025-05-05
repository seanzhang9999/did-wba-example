"""Chat API router for OpenRouter LLM chat relay."""
import os
import logging
import httpx
import asyncio
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from agent_connect.authentication import (
    verify_auth_header_signature,
    resolve_did_wba_document,
    extract_auth_header_parts,
    create_did_wba_document,
    DIDWbaAuthHeader
)

from core.config import Settings

# 导入新创建的适配器模块中的函数
from anp_core.agent.anp_llm_adapter import request_openrouter, anp_nlp_resp_messages, anp_nlp_resp_new_message_event, notify_chat_thread

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str


def get_and_validate_port(request: Request) -> str:
    """
    Get the domain from the request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Domain from request host header
    """
    # Get host from request
    host = request.headers.get('host', '')
    port = host.split(":")[1]
    return port

@router.post("/wba/anp-nlp", summary="ANP的NLP接口，Chat with OpenRouter LLM")
async def anp_nlp_service(
    request: Request,
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
        
    did = request.headers.get("DID")
    requestport = get_and_validate_port(request)
    
    # 调用封装的OpenRouter请求函数
    status_code, response_data = await request_openrouter(chat_req.message, did, requestport)
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response_data["answer"])
        
    return JSONResponse(content=response_data)


async def notify_chat_thread(message_data: Dict[str, Any], did: str):
    """
    通知聊天线程有新消息
    
    Args:
        message_data: 消息数据
    """
    global anp_nlp_resp_messages, anp_nlp_resp_new_message_event
    
    # 添加消息到全局列表
    anp_nlp_resp_messages.append(message_data)
    
    # 如果列表太长，保留最近的50条消息
    if len(anp_nlp_resp_messages) > 50:
        anp_nlp_resp_messages = anp_nlp_resp_messages[-50:]
    
    # 设置事件，通知聊天线程
    anp_nlp_resp_new_message_event.set()
    
    # 在控制台显示通知
    # logging.info(f"ANP-resp收到: {message_data['user_message']}")
    # logging.info(f"ANP-resp返回: {message_data['assistant_message']}")
    
    # 打印到控制台，确保在聊天线程中可见

    port= os.environ.get("PORT")
    print(f"\nANP-resp收自@{did}: {message_data['user_message']}")
    print(f"\nANP-resp从{port}返回: {message_data['assistant_message']}\n")
    
    # 注释掉重置事件的代码，让mcp_server.py中的监听器来清除事件
    # new_message_event.clear()