"""
Chat API router for OpenRouter LLM chat relay.
"""
import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["chat"])

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # 用户需在环境变量中配置免费key

class ChatRequest(BaseModel):
    message: str

@router.post("/wba/chat", summary="Chat with OpenRouter LLM")
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
            answer = data['choices'][0]['message']['content']
            return JSONResponse(content={"answer": answer})
    except Exception as e:
        logging.error(f"Chat relay error: {e}")
        raise HTTPException(status_code=500, detail="Chat relay failed")