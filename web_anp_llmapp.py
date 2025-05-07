"""DID WBA Example with both Client and Server capabilities."""
import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import secrets
import signal
import sys
import threading
import time
from typing import Any, Dict

from loguru import logger
import uvicorn

unique_id = None

# 尝试导入httpx，如果不存在则在需要时提示安装
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("警告: 缺少httpx模块，某些功能将不可用。请使用 'pip install httpx' 安装该模块。")

from api.anp_nlp_router import (
    resp_handle_request_msgs,
    resp_handle_request_new_msg_event as server_new_message_event,
)
from core.app import create_app
from core.config import settings
from anp_core.server.server import ANP_resp_start, ANP_resp_stop, server_status
from anp_core.client.client import ANP_req_auth, ANP_req_chat
from utils.log_base import set_log_color_level
user_dir = os.path.dirname(os.path.abspath(__file__))
user_dir = os.path.join(user_dir, "logs")
# 设置日志
logger.add(f"{user_dir}/anp_llmapp_web.log", rotation="1000 MB", retention="7 days", encoding="utf-8")

# Create FastAPI application
app = create_app()


@app.get("/", tags=["status"])
async def root():
    """
    Root endpoint for server status check.
    
    Returns:
        dict: Server status information
    """
    return {
        "status": "running",
        "service": "DID WBA Example",
        "version": "0.1.0",
        "mode": "Client and Server",
        "documentation": "/docs"
    }


# 全局变量，用于存储服务器、客户端和聊天线程
server_thread = None
chat_thread = None
server_running = False
chat_running = False
server_instance = None  # 存储uvicorn.Server实例

# 全局变量，用于存储最新的聊天消息
client_chat_messages = []
# 事件，用于通知聊天线程有新消息
client_new_message_event = asyncio.Event()


def resp_start(port=None):
    """启动服务器线程
    
    Args:
        port: 可选的服务器端口号，如果提供则会覆盖默认端口
    """
    # 如果提供了端口号，则临时修改设置中的端口
    if port is not None:
        try:
            port_num = int(port)
            settings.PORT = port_num
            logger.info(f"Use a custom port: {port_num}")
        except ValueError:
            logger.error(f"Error prot : {port}，use default port: {settings.PORT}")
    
    # 调用did_core中的start_server函数
    return ANP_resp_start(port=port)


def resp_stop():
    """停止服务器线程"""
    # 调用did_core中的stop_server函数
    return ANP_resp_stop()


async def run_chat():
    """运行LLM聊天线程 - 直接调用OpenRouter API"""
    global chat_running

    try:
        # 检查是否安装了httpx模块
        if not HTTPX_AVAILABLE:
            print("[错误] 缺少httpx模块，无法启动聊天线程。请使用 'pip install httpx' 安装该模块。")
            chat_running = False
            return
            
        # 导入ANP-NLP路由器中的事件和消息
        from api.anp_nlp_router import resp_handle_request_new_msg_event, resp_handle_request_msgs, notify_chat_thread
        
        # 检查OpenRouter API密钥是否配置
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not openrouter_api_key:
            print("[错误] 未配置OpenRouter API密钥，请在环境变量中设置OPENROUTER_API_KEY")
            chat_running = False
            return
            
        # OpenRouter API配置
        openrouter_api_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        print("\n已启动LLM聊天线程。输入消息与AI对话，输入 /q 退出。")
        print("特殊命令: 输入 @[agent-name]:[msg] 。")
        logging.info("聊天线程启动 - 直接调用OpenRouter API")
        
        # 进入聊天模式
        async with httpx.AsyncClient(timeout=30) as client:
            chat_running = True
            while chat_running:
                user_msg = input("你: ").strip()
                
                if user_msg.lower() == "/q":
                    print("退出聊天线程。\n")
                    break
                
# 处理特殊命令 @anp-bot
                if user_msg.strip().startswith("@") and user_msg.strip().find(" ") :
                    parts = user_msg.strip().split(" ", 1)
                    agentname = parts[0].strip().split("@", 1)
                    agentname = agentname[1]
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
                        print(f"使用{agentname}智能体DID: {did}地址：{url}端口：{port}通讯")
                        os.environ['target-port'] = f"{port}"
                        os.environ['target-host'] = f"{url}"                        
                        custom_msg = "ANPbot的问候，请二十字内回复我"
                        if len(parts) > 1 and parts[1].strip():
                            custom_msg = parts[1].strip()
                        print(f"将向智能体{port}发送消息: {custom_msg}")
                        chat_running = False
                        # 获取token，如果环境变量中不存在则使用None
                        token = os.environ.get('did-token', None)
                        # 调用send_msg函数发送消息（非阻塞方式）
                        chat_to_ANP(custom_msg, token, unique_id)
                        
                        print("\n客户端执行中，你可以先聊。")
                        chat_running = True
                    else:
                        print(f"您要交流的智能体{agentname}不存在，请通过智能体搜索寻找合适的智能体")# 生成或加载智能体的DID
                    continue
                    
                try:
                    # 准备请求数据
                    payload = {
                        "model": "deepseek/deepseek-chat-v3-0324:free",  # 免费模型
                        "messages": [{"role": "user", "content": user_msg}],
                        "max_tokens": 512
                    }
                    
                    # 发送请求到OpenRouter API
                    resp = await client.post(
                        openrouter_api_url,
                        headers=headers,
                        json=payload
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data['choices'][0]['message']['content']
                        print(f"助手: {answer}")
                    else:
                        print(f"[错误] OpenRouter API返回: {resp.status_code} {resp.text}")
                except Exception as ce:
                    print(f"白嫖的OpenRouter生气了: {ce}")
                    if not chat_running:  # 如果线程被外部终止
                        break
                
    except Exception as e:
        logging.error(f"聊天线程出错: {e}")
    finally:
        chat_running = False


def start_chat():
    """启动LLM聊天线程 - 直接调用OpenRouter API，同时自动启动服务器"""
    global chat_thread, chat_running, server_thread, server_running
    
    # 检查聊天线程是否已在运行
    if chat_thread and chat_thread.is_alive():
        print("聊天线程已经在运行中")
        return
    
    # 检查服务器是否已在运行，如果没有则自动启动（静默模式）
    if not server_thread or not server_thread.is_alive():
        # 启动服务器线程（不打印日志信息）
        original_log_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)  # 只显示错误日志
        
        server_thread = threading.Thread(target=resp_start, daemon=True)
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
    
    # 启动聊天线程
    chat_thread = threading.Thread(target=lambda: asyncio.run(run_chat()), daemon=True)
    chat_thread.start()
    print("LLM聊天线程已启动")


def stop_chat():
    """停止LLM聊天线程，同时处理自动启动的服务器线程"""
    global chat_thread, chat_running, server_thread, server_running, server_instance
    if not chat_thread or not chat_thread.is_alive():
        print("聊天线程未运行")
        return
    
    print("正在关闭聊天线程...")
    chat_running = False
    chat_thread.join(timeout=5)
    if chat_thread.is_alive():
        print("聊天线程关闭超时，可能需要重启程序")
    else:
        print("聊天线程已关闭")
        chat_thread = None


def show_status():
    """显示当前服务器和聊天状态"""
    server_status = "运行中" if server_thread and server_thread.is_alive() else "已停止"
    chat_status = "运行中" if chat_thread and chat_thread.is_alive() else "已停止"
    
    print(f"监听状态: {server_status}")
    print(f"聊天状态: {chat_status}")


def show_help():
    """显示帮助信息"""
    print("可用命令:")
    print("  start resp [port] - 启动anp服务器，可选指定端口号")
    print("  stop resp - 停止anp服务器")
    print("  start llm - 启动LLM聊天线程")
    print("  stop llm - 停止LLM聊天线程")
    print("  status - 显示服务器和聊天状态")
    print("  help - 显示此帮助信息")
    print("  test - 测试anp")
    print("  exit - 退出程序")


async def client_notify_chat_thread(message_data: Dict[str, Any]):
    """
    通知聊天线程有新消息
    
    Args:
        message_data: 消息数据
    """
    global client_chat_messages, client_new_message_event
    
    # 添加消息到全局列表
    client_chat_messages.append(message_data)
    
    # 如果列表太长，保留最近的50条消息
    if len(client_chat_messages) > 50:
        client_chat_messages = client_chat_messages[-50:]
    
    # 设置事件，通知聊天线程
    client_new_message_event.set()
    
    # 在控制台显示通知
    logging.info(f"ANP客户请求: {message_data['user_message']}")
    logging.info(f"ANP对方响应: {message_data['assistant_message']}")
    
    # 打印到控制台，确保在聊天线程中可见
    print(f"\nANP-req从本地发出: {message_data['user_message']}")
    print(f"\nANP-req从@{settings.TARGET_SERVER_PORT}收到:  {message_data['assistant_message']}\n")
    
    # 重置事件，为下一次通知做准备
    client_new_message_event.clear()


def chat_to_ANP(custom_msg, token=None, unique_id_arg=None):
    """发送消息到目标服务器（非阻塞方式）
    
    Args:
        custom_msg: 要发送的消息
        token: 认证令牌，如果为None则会启动客户端认证获取token
        unique_id_arg: 可选的唯一ID，用于客户端认证
    """
    # 使用线程模式运行，避免事件循环问题
    thread = threading.Thread(
        target=_chat_to_ANP_thread,
        args=(custom_msg, token, unique_id_arg),
        daemon=True
    )
    thread.start()
    return True

def _chat_to_ANP_thread(custom_msg, token=None, unique_id_arg=None):
    """在线程中运行异步函数的同步包装器"""
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # 运行异步函数
        loop.run_until_complete(_chat_to_ANP_impl(custom_msg, token, unique_id_arg))
    except Exception as e:
        logging.error(f"线程中运行_chat_to_ANP_impl时出错: {e}")
        print(f"发送消息时出错: {e}")
    finally:
        # 关闭事件循环
        loop.close()

async def _chat_to_ANP_impl(custom_msg, token=None, unique_id_arg=None):
    """发送消息的实际实现（内部函数）
    """
    try:

       
        target_host = settings.TARGET_SERVER_HOST
        target_port = settings.TARGET_SERVER_PORT
        if os.environ.get('target-port'):
            target_port = os.environ.get('target-port')
        if os.environ.get('target-host'):
            target_host = os.environ.get('target-host')
        base_url = f"http://{target_host}:{target_port}"
        
        if not token:
            print(f"无token，正在启动客户端认证获取token...\n并发送消息: {custom_msg}")
            await ANP_req_auth(unique_id=unique_id_arg, msg=custom_msg)
            token = os.environ.get('did-token', None)
            
        print(f"使用token...\n发送消息: {custom_msg}")
        # 调用did_core中的send_message_to_chat函数
        status, response = await ANP_req_chat(base_url=base_url, silent=True, from_chat=True, msg=custom_msg, token=token)
        
        # 通知聊天线程有新消息
        if status:
            await client_notify_chat_thread({
                "type": "anp_nlp",  # 确保类型与run_chat中的处理逻辑匹配
                "user_message": custom_msg,
                "assistant_message": response.get('answer', '[无回复]') if isinstance(response, dict) else str(response),
                "status": "success"
            })
        else:
            await client_notify_chat_thread({
                "type": "anp_nlp",
                "status": "error",
                "message": f"发送消息失败: {response}"
            })
    except Exception as e:
        logging.error(f"发送消息时出错: {e}")
        print(f"发送消息时出错: {e}")
        # 通知聊天线程出错
        try:
            await client_notify_chat_thread({
                "type": "anp_nlp",
                "status": "error",
                "message": f"发送消息时出错: {e}"
            })
        except Exception:
            pass

def anp_test():
    """测试函数，用于顺序测试服务器启动、消息发送和服务器停止
    
    按顺序执行以下操作并打印日志：
    1. resp_start - 启动服务器
    2. 发送消息 - 发送测试消息
    3. resp_stop - 停止服务器
    """
    import time
    import logging
    import os
    
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # 1. 启动服务器
        logger.info("===== 步骤1: 启动服务器 =====")
        server_result = resp_start()
        logger.info(f"服务器启动结果: {server_result}")
        logger.info("等待服务器完全启动...")
        time.sleep(3)  # 等待服务器完全启动
        
        # 2. 发送消息
        logger.info("\n===== 步骤2: 发送消息 =====")
        try:
            # 检查是否安装了httpx模块
            import httpx
            test_message = "这是一条测试消息，请回复"  
            logger.info(f"发送消息: {test_message}")
            # 获取token，如果环境变量中不存在则使用None
            token = os.environ.get('did-token', None)
            chat_result = chat_to_ANP(test_message, token)
            logger.info(f"消息发送结果: {chat_result}")
            logger.info("等待消息处理...")
            time.sleep(5)  # 等待消息处理
        except ImportError:
            logger.error("缺少httpx模块，无法发送消息。请使用 'pip install httpx' 安装该模块。")
            print("缺少httpx模块，无法发送消息。请使用 'pip install httpx' 安装该模块。")
        
        # 3. 停止服务器
        logger.info("\n===== 步骤3: 停止服务器 =====")
        stop_result = resp_stop()
        logger.info(f"服务器停止结果: {stop_result}")
        
        logger.info("\n===== 测试完成 =====")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")


if __name__ == "__main__":
    """主函数，处理命令行输入"""
    set_log_color_level(logging.INFO)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="DID WBA Example with Server capabilities")
    parser.add_argument("--server", action="store_true", help="Run server at startup", default=False)
    parser.add_argument("--port", type=int, help=f"Server port (default: {settings.PORT})", default=settings.PORT)
    
    args = parser.parse_args()
    
    if args.port != settings.PORT:
        settings.PORT = args.port

    import os
    os.environ["PORT"] = f"{settings.PORT}"
    
    # 根据命令行参数启动服务
    if args.server:
        resp_start()
    
    print("DID WBA 示例程序已启动")
    print("输入'help'查看可用命令，输入'exit'退出程序")
    
    # 主循环，处理用户输入
    while True:
        try:
            # 如果聊天线程正在运行，则等待其退出，不处理命令
            if chat_running:
                # 等待聊天线程退出
                while chat_running:
                    time.sleep(0.5)
                if not chat_running:
                    print("聊天线程已退出，恢复命令行控制。")
            command = input("> ").strip().lower()
            
            if command == "exit":
                print("正在关闭服务...")
                stop_chat()
                resp_stop()
                break
            elif command == "test":
                anp_test()
            elif command == "help":
                show_help()
            elif command == "status":
                show_status()
            elif command.startswith("start resp"):
                # 检查是否指定了端口号
                parts = command.split()
                if len(parts) > 2:
                    resp_start(parts[2])
                else:
                    resp_start()
            elif command.startswith("stop resp"):
                resp_stop()
            elif command == "start llm":
                start_chat()
                # 阻塞主进程直到 chat_thread 结束，避免输入竞争
                if chat_thread:
                    chat_thread.join()
                print("聊天线程已退出，恢复命令行控制。")
                continue  # 跳过本轮命令输入
            elif command == "stop llm":
                stop_chat()
            else:
                print(f"未知命令: {command}")
                print("输入'help'查看可用命令")
                
        except KeyboardInterrupt:
            print("\n检测到退出信号，正在关闭...")
            resp_stop()
            break
        except Exception as e:
            print(f"错误: {e}")
    
    print("程序已退出")
    sys.exit(0)