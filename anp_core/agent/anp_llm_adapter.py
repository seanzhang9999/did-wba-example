"""OpenRouter LLM API适配器

提供与OpenRouter API交互的功能，用于发送消息和接收响应。
"""
import os
import logging
import httpx
import asyncio
from typing import Dict, Any, Tuple, Optional

# 全局变量，用于存储最新的聊天消息
anp_nlp_resp_messages = []
# 事件，用于通知聊天线程有新消息
anp_nlp_resp_new_message_event = asyncio.Event()

# OpenRouter API配置
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # 用户需在环境变量中配置免费key

async def request_openrouter(message: str, did: str, requestport: str = None) -> Tuple[int, Dict[str, Any]]:
    """
    向OpenRouter发送请求并处理响应
    
    Args:
        message: 用户消息
        did: 用户DID
        requestport: 请求端口
        
    Returns:
        tuple: (状态码, 响应内容)
    """
    if not OPENROUTER_API_KEY:
        error_msg = "OpenRouter API key not configured"
        message_data = {
            "type": "anp_nlp",
            "user_message": message,
            "assistant_message": error_msg
        }
        await notify_chat_thread(message_data, did)
        return 500, {"answer": error_msg}
    
    agentname = os.environ.get('AGENT_NAME')
    if agentname == "weatherbj":
        prompt = "你是负责北京天气查询的机器人，你首先要回复用户你的身份，然后根据用户的查询，返回当前的天气情况。"
    elif agentname == "weatherall":
        prompt = "你是负责北京之外天气查询的机器人，你首先要告诉用户你的身份，然后根据用户的查询，返回当前的天气情况。如果用户询问北京的天气，你告诉用户应该去找weatherbj智能体"
    else:
        prompt = "你是一个智能助手，请根据用户的提问进行专业、简洁的回复。"



    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",  # 免费模型
        "messages": [
            {"role": "system", "content":prompt},
            {"role": "user", "content": message}
            ],
        "max_tokens": 512
    }


    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logging.error(f"OpenRouter error: {resp.text}")
                error_msg = f"OpenRouter query failed: {resp.status_code}"
                message_data = {
                    "type": "anp_nlp",
                    "user_message": message,
                    "assistant_message": error_msg
                }
                await notify_chat_thread(message_data, did)
                return resp.status_code, {"answer": error_msg}
                
            data = resp.json()
            agentname = os.environ.get('AGENT_NAME')  
            if agentname is None:
                answer = data['choices'][0]['message']['content']
            else:
                answer = agentname + ":" + data['choices'][0]['message']['content']


            # 添加消息到全局消息列表，并通知聊天线程
            message_data = {
                "type": "anp_nlp",
                "user_message": message,
                "assistant_message": answer
            }
            await notify_chat_thread(message_data, did)
            

            return 200, {"answer": answer}
    except Exception as e:
        error_msg = f"白嫖的OpenRouter生气了:{e}"
        message_data = {
            "type": "anp_nlp",
            "user_message": message,
            "assistant_message": error_msg
        }
        await notify_chat_thread(message_data, did)
        return 500, {"answer": error_msg}

async def notify_chat_thread(message_data: Dict[str, Any], did: str):
    """
    通知聊天线程有新消息
    
    Args:
        message_data: 消息数据
        did: 用户DID
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
    port = os.environ.get("PORT")
    print(f"\nANP-resp收自@{did}: {message_data['user_message']}")
    print(f"\nANP-resp从{port}返回: {message_data['assistant_message']}\n")
    
    # 注释掉重置事件的代码，让mcp_server.py中的监听器来清除事件
    # new_message_event.clear()