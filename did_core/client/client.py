"""DID WBA Client implementation.

This module provides the client functionality for the DID WBA system.
"""
import os
import logging
import asyncio
import secrets
import httpx
import time
import threading

from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from loguru import logger

from core.config import settings
from auth.did_auth import (
    generate_or_load_did, 
    send_authenticated_request,
    send_request_with_token,
    DIDWbaAuthHeader
)

# 全局变量，用于存储最新的聊天消息
client_chat_messages = []
# 事件，用于通知聊天线程有新消息
client_new_message_event = asyncio.Event()

# 客户端状态全局变量
client_running = False
client_thread = None

# 初始化日志
logger.add("logs/did_client.log", rotation="1000 MB", retention="7 days", encoding="utf-8")


async def client_notify_chat_thread(message_data):
    """通知聊天线程有新消息
    
    Args:
        message_data: 消息数据
    """
    global client_chat_messages, client_new_message_event
    
    # 添加消息到聊天消息列表
    client_chat_messages.append(message_data)
    if len(client_chat_messages) > 50:
        client_chat_messages = client_chat_messages[-50:]
    
    # 设置事件，通知等待的线程
    client_new_message_event.set()


async def client_example(unique_id: str = None, silent: bool = False, from_chat: bool = False, msg: str = None):
    """运行客户端示例，演示DID WBA认证
    
    Args:
        unique_id: 可选的唯一标识符
        silent: 是否抑制日志输出
        from_chat: 调用是否来自聊天线程
        msg: 要发送的消息
    """
    if msg is None:
        msg = "ANP客户端的问候，请回复我今天北京的天气"
    try:
        # 1. 生成或加载DID文档
        if not unique_id:
            unique_id = secrets.token_hex(8)
       
        logging.info(f"使用唯一ID: {unique_id}")

        did_document, keys, user_dir = await generate_or_load_did(unique_id)
        os.environ['did-id'] = did_document.get('id')
        did_document_path = Path(user_dir) / settings.DID_DOCUMENT_FILENAME
        private_key_path = Path(user_dir) / settings.PRIVATE_KEY_FILENAME
        
        logging.info(f"DID文档路径: {did_document_path}")
        logging.info(f"私钥路径: {private_key_path}")
        
        # 2. 目标服务器信息
        target_host = settings.TARGET_SERVER_HOST
        target_port = settings.TARGET_SERVER_PORT
        base_url = f"http://{target_host}:{target_port}"
        test_url = f"{base_url}/wba/test"
        
        # 3. 创建DIDWbaAuthHeader实例
        auth_client = DIDWbaAuthHeader(
            did_document_path=str(did_document_path),
            private_key_path=str(private_key_path)
        )
        
        # 4. 发送带DID WBA认证的请求
        logging.info(f"发送认证请求到 {test_url}")
        status, response, token = await send_authenticated_request(test_url, auth_client)
        
        if status != 200:
            logging.error(f"认证失败! 状态: {status}")
            logging.error(f"响应: {response}")
            return
            
        logging.info(f"认证成功! 响应: {response}")
        
        # 5. 如果收到令牌，使用它进行后续请求
        if token:
            logging.info("收到访问令牌，尝试用于下一个请求")
            status, response = await send_request_with_token(test_url, token)
            
            if status == 200:
                logging.info(f"令牌认证成功! 响应: {response}")
                # 发送消息到聊天接口
                anp_nlp_url = f"{base_url}/wba/anp-nlp"
                logging.info("发送消息到聊天接口")
                try:
                    chat_status, chat_response = await send_request_with_token(
                        anp_nlp_url, 
                        token, 
                        method="POST", 
                        json_data={"message": msg}
                    )
                    if chat_status == 200:
                        logging.info(f"消息发送成功! 回复: {chat_response}")
                        if from_chat:
                            # 如果是从聊天线程调用，发送通知而不是打印
                            await client_notify_chat_thread({
                                "type": "anp_nlp",
                                "user_message": msg,
                                "assistant_message": chat_response.get('answer', '[无回复]'),
                                "status": "success"
                            })
                        elif not silent:
                            print(f"\nanp消息\"{msg}\"成功发送，服务器回复: {chat_response.get('answer', '[无回复]')}")
                    else:
                        logging.error(f"消息发送失败! 状态: {chat_status}")
                        logging.error(f"响应: {chat_response}")
                        if from_chat:
                            await client_notify_chat_thread({
                                "type": "anp_nlp",
                                "status": "error",
                                "message": "消息发送失败"
                            })
                        elif not silent:
                            print("\n消息发送失败，客户端示例完成。")
                except Exception as ce:
                    logging.error(f"发送消息时出错: {ce}")
                    if from_chat:
                        await client_notify_chat_thread({
                            "type": "anp_nlp",
                            "status": "error",
                            "message": f"发送消息时出错: {ce}"
                        })
                    elif not silent:
                        print(f"\n发送消息时出错: {ce}")
                if not from_chat and not silent:
                    print("\n客户端示例完成。")
            else:
                logging.error(f"令牌认证失败! 状态: {status}")
                logging.error(f"响应: {response}")
                if from_chat:
                    await client_notify_chat_thread({
                        "type": "anp_nlp",
                        "status": "error",
                        "message": "令牌认证失败"
                    })
                elif not silent:
                    print("\n令牌认证失败，客户端示例完成。")

        else:
            logging.warning("未从服务器收到令牌")
            
    except Exception as e:
        logging.error(f"客户端示例中出错: {e}")


def run_client(unique_id=None, message=None):
    """在子线程中运行客户端"""
    global client_running
    try:
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行客户端示例
        client_running = True
        loop.run_until_complete(client_example(unique_id=unique_id, from_chat=True, msg=message))
        
        # 关闭事件循环
        loop.close()
    except Exception as e:
        logger.error(f"客户端运行出错: {e}")
    finally:
        client_running = False
        logger.info("客户端已停止")


def start_client(port=None, unique_id=None, message=None):
    """启动DID WBA客户端
    
    Args:
        port: 可选的目标服务器端口号
        unique_id: 可选的客户端唯一标识符
        message: 要发送的消息
        
    Returns:
        bool: 客户端是否成功启动
    """
    global client_running, client_thread, settings
    
    # 检查客户端是否已经在运行
    if client_running:
        logger.warning("客户端已经在运行中")
        return True
    
    # 如果指定了端口，更新设置
    if port:
        settings.TARGET_SERVER_PORT = port
    
    try:
        # 创建并启动客户端线程
        client_thread = threading.Thread(target=run_client, args=(unique_id, message))
        client_thread.daemon = True
        client_thread.start()
        
        # 等待客户端启动
        for _ in range(10):
            if client_running:
                logger.info(f"客户端已启动，目标端口: {settings.TARGET_SERVER_PORT}")
                return True
            time.sleep(0.5)
        
        logger.error("客户端启动超时")
        return False
    except Exception as e:
        logger.error(f"启动客户端时出错: {e}")
        return False


def stop_client():
    """停止DID WBA客户端
    
    Returns:
        bool: 客户端是否成功停止
    """
    global client_running, client_thread
    
    if not client_running:
        logger.warning("客户端未运行")
        return True
    
    try:
        # 等待客户端停止
        client_running = False
        if client_thread and client_thread.is_alive():
            client_thread.join(timeout=5)
        
        logger.info("客户端已停止")
        return True
    except Exception as e:
        logger.error(f"停止客户端时出错: {e}")
        return False