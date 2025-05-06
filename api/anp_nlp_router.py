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
from anp_core.agent.anp_llm_adapter import resp_handle_request, resp_handle_request_msgs, resp_handle_request_new_msg_event, notify_chat_thread

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
    status_code, response_data = await resp_handle_request(chat_req.message, did, requestport)
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response_data["answer"])
        
    return JSONResponse(content=response_data)