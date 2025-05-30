"""DID WBA Example with both Client and Server capabilities.

This module serves as the main entry point for the DID WBA system,
providing access to both client and server functionalities.
"""
import argparse
import sys
import os

from loguru import logger

# 导入服务器和客户端功能
from anp_core.server.server import ANP_resp_start, ANP_resp_stop, server_running
from anp_core.client.client import ANP_connector_start, ANP_connector_stop, connector_running, client_chat_messages, client_new_message_event

# 从API模块导入服务器端消息处理
from api.anp_nlp_router import anp_nlp_resp_messages, anp_nlp_resp_new_message_event as server_new_message_event

# 设置日志
logger.add("logs/anp_llm.log", rotation="1000 MB", retention="7 days", encoding="utf-8")


def main():
    """主函数，处理命令行参数并启动相应功能"""
    parser = argparse.ArgumentParser(description="DID WBA示例 - 客户端和服务器功能")
    
    # 添加子命令解析器
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 服务器命令
    server_parser = subparsers.add_parser("server", help="启动DID WBA服务器")
    server_parser.add_argument("-p", "--port", type=int, help="服务器端口号")
    
    # 客户端命令
    client_parser = subparsers.add_parser("client", help="启动DID WBA客户端")
    client_parser.add_argument("-p", "--port", type=int, help="目标服务器端口号")
    client_parser.add_argument("-i", "--id", type=str, help="客户端唯一标识符")
    client_parser.add_argument("-m", "--message", type=str, help="要发送的消息")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 根据命令执行相应功能
    if args.command == "server":
        # 启动服务器
        print(f"正在启动DID WBA服务器...")
        if ANP_resp_start(port=args.port):
            print(f"服务器已启动，按Ctrl+C停止")
            try:
                # 保持主线程运行，直到用户按Ctrl+C
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在停止服务器...")
                ANP_resp_stop()
                print("服务器已停止")
        else:
            print("服务器启动失败")
            sys.exit(1)
    
    elif args.command == "client":
        # 启动客户端
        print(f"正在启动DID WBA客户端...")
        if ANP_connector_start(port=args.port, unique_id=args.id, message=args.message):
            print(f"客户端已启动，等待完成...")
            # 等待客户端完成
            import time
            for _ in range(30):  # 最多等待30秒
                if not connector_running:
                    break
                time.sleep(1)
            ANP_connector_stop()
            print("客户端已停止")
        else:
            print("客户端启动失败")
            sys.exit(1)
    
    else:
        # 显示帮助信息
        parser.print_help()


if __name__ == "__main__":
    main()