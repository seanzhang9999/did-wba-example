"""MCP Client Example for DID WBA.

This script demonstrates how to use the MCP client to connect to the MCP server
and invoke the DID WBA tools.
"""
import asyncio
import json
import os
import sys
import logging
import traceback
import tempfile
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# 设置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建一个支持fileno的stderr捕获器
class StderrCapture:
    def __init__(self):
        # 创建临时文件来存储stderr输出
        self.temp_file = tempfile.TemporaryFile(mode='w+', encoding='utf-8')
    
    def write(self, data):
        # 写入临时文件
        self.temp_file.write(data)
        # 同时输出到控制台
        sys.__stderr__.write(data)
        sys.__stderr__.flush()
    
    def flush(self):
        self.temp_file.flush()
        sys.__stderr__.flush()
    
    def fileno(self):
        # 返回临时文件的文件描述符
        return self.temp_file.fileno()
    
    def get_content(self):
        # 保存当前位置
        current_pos = self.temp_file.tell()
        # 回到文件开始
        self.temp_file.seek(0)
        # 读取所有内容
        content = self.temp_file.read()
        # 恢复位置
        self.temp_file.seek(current_pos)
        return content
    
    def close(self):
        # 关闭临时文件
        self.temp_file.close()

async def main():
    """Run the MCP client example."""
    print("连接到 MCP 服务器...")
    logger.debug("开始连接MCP服务器")
    
    # 创建stderr捕获器
    stderr_capture = StderrCapture()
    
       
        # 设置超时
        timeout = 30  # 30秒超时
        
        # 使用stdio连接到MCP服务器
        server_params = StdioServerParameters(
            command="uv", 
            args=["run", "--with", "mcp", "mcp", "run", "mcp_server.py"],
            # 添加环境变量，确保输出不被缓冲并设置PATH
            env={
                "PYTHONUNBUFFERED": "1",
            #    "PATH": "/Users/seanzhang/.npm/_npx/5a9d879542beca3a/node_modules/.bin:/Users/seanzhang/seanwork/did-wba-example/node_modules/.bin:/Users/seanzhang/seanwork/node_modules/.bin:/Users/seanzhang/node_modules/.bin:/Users/node_modules/.bin:/node_modules/.bin:/usr/local/lib/node_modules/npm/node_modules/@npmcli/run-script/lib/node-gyp-bin:/Users/seanzhang/seanwork/did-wba-example/.venv/bin:/Users/seanzhang/.trae/extensions/ms-python.python-2025.4.0-universal/python_files/deactivate/zsh:/Users/seanzhang/seanwork/did-wba-example/.venv/bin:/Users/seanzhang/.codeium/windsurf/bin:/Users/seanzhang/.bun/bin:/opt/anaconda3/bin:/usr/local/sbin:/usr/local/bin:/Library/Java/JavaVirtualMachines/jdk1.8.0_202.jdk/Contents/Home/bin:/Users/seanzhang/.trae/extensions/ms-python.python-2025.4.0-universal/python_files/deactivate/zsh:/Users/seanzhang/seanwork/did-wba-example/.venv/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/Library/Apple/usr/bin:/Applications/VMware Fusion.app/Contents/Public:/usr/local/bin/pandoc:/Applications/Trae.app/Contents/Resources/app/bin:/Users/seanzhang/.trae/extensions/ms-python.python-2025.4.0-universal/python_files/deactivate/zsh:/Users/seanzhang/seanwork/did-wba-example/.venv/bin:/Users/seanzhang/.codeium/windsurf/bin:/Users/seanzhang/.bun/bin:/opt/anaconda3/bin:/usr/local/sbin:/Users/seanzhang/miniconda3/bin:/Users/seanzhang/miniconda3/condabin:/Library/Java/JavaVirtualMachines/jdk1.8.0_202.jdk/Contents/Home/bin:/Users/seanzhang/.local/bin:/Users/seanzhang/.local/bin:/Users/seanzhang/.local/bin"
            }
        )
        logger.debug(f"连接到MCP服务器(stdio): {server_params}")
        
        # 使用自定义的stderr捕获器
        async with stdio_client(server_params, errlog=stderr_capture) as (read_stream, write_stream):
            # 创建客户端会话
            async with ClientSession(read_stream, write_stream) as client:
                print("已连接到 MCP 服务器")
                logger.debug("成功创建ClientSession")
            
                # 获取当前状态 - 添加超时处理
                try:
                    await client.initialize()
                    logger.debug("初始化")
                    # 测试获取可用工具列表
                    # tools = await client.list_tools()
                    # print("可用工具列表:", tools)
                    
                    # 然后读取资源状态
                    # logger.debug("读取资源")
                    # status_task = asyncio.create_task(client.read_resource("status://did-wba"))
                    # status = await asyncio.wait_for(status_task, timeout=timeout)
                    # print(f"当前状态:\n{json.dumps(status, indent=2, ensure_ascii=False)}")
                except asyncio.TimeoutError:
                    logger.error(f"读取资源状态超时 (超过{timeout}秒)")
                    print(f"错误: 读取资源状态超时，服务器可能未正确启动")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                except Exception as e:
                    logger.error(f"读取资源状态时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
            
                # 启动服务器
                print("\n启动 DID WBA 服务器...")
                try:
                    server_result = await asyncio.wait_for(
                        client.call_tool("start_did_server"), 
                        timeout=timeout
                    )
                    print(f"服务器启动结果: {server_result}")
                except asyncio.TimeoutError:
                    logger.error(f"启动服务器超时 (超过{timeout}秒)")
                    print(f"错误: 启动服务器超时")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                except Exception as e:
                    logger.error(f"启动服务器时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
            
                # 等待服务器启动
                await asyncio.sleep(2)
            
                # 启动客户端并发送消息
                print("\n启动 DID WBA 客户端...")
                try:
                    client_result = await asyncio.wait_for(
                        client.call_tool(
                            "start_did_client", 
                            {"message": "你好，这是通过 MCP 客户端发送的测试消息"}
                        ),
                        timeout=timeout
                    )
                    print(f"客户端启动结果: {client_result}")
                except asyncio.TimeoutError:
                    logger.error(f"启动客户端超时 (超过{timeout}秒)")
                    print(f"错误: 启动客户端超时")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                except Exception as e:
                    logger.error(f"启动客户端时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                """
                # 等待并获取连接事件
                print("\n等待连接事件...")
                print("(最多等待 30 秒，如果没有新事件将超时)")
                try:
                    events = await asyncio.wait_for(
                        client.call_tool(
                            "get_connection_events", 
                            {"wait_for_new": True}
                        ),
                        timeout=timeout
                    )
                    print(f"连接事件:\n{json.dumps(events, indent=2, ensure_ascii=False)}")
                except asyncio.TimeoutError:
                    logger.error(f"获取连接事件超时 (超过{timeout}秒)")
                    print(f"错误: 获取连接事件超时")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                except Exception as e:
                    logger.error(f"获取连接事件时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                """
            
                # 停止客户端
                print("\n停止 DID WBA 客户端...")
                try:
                    stop_client_result = await asyncio.wait_for(
                        client.call_tool("stop_did_client"),
                        timeout=timeout
                    )
                    print(f"客户端停止结果: {stop_client_result}")
                except asyncio.TimeoutError:
                    logger.error(f"停止客户端超时 (超过{timeout}秒)")
                    print(f"错误: 停止客户端超时")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                except Exception as e:
                    logger.error(f"停止客户端时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
            
                # 停止服务器
                print("\n停止 DID WBA 服务器...")
                try:
                    stop_server_result = await asyncio.wait_for(
                        client.call_tool("stop_did_server"),
                        timeout=timeout
                    )
                    print(f"服务器停止结果: {stop_server_result}")
                except asyncio.TimeoutError:
                    logger.error(f"停止服务器超时 (超过{timeout}秒)")
                    print(f"错误: 停止服务器超时")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return
                except Exception as e:
                    logger.error(f"停止服务器时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                    return

                """
                # 再次获取状态
                try:
                    status = await asyncio.wait_for(
                        client.read_resource("status://did-wba"),
                        timeout=timeout
                    )
                    print(f"\n最终状态:\n{json.dumps(status, indent=2, ensure_ascii=False)}")
                except asyncio.TimeoutError:
                    logger.error(f"获取最终状态超时 (超过{timeout}秒)")
                    print(f"错误: 获取最终状态超时")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                except Exception as e:
                    logger.error(f"获取最终状态时出错: {e}")
                    print(f"错误: {e}")
                    # 输出捕获的stderr内容
                    stderr_content = stderr_capture.get_content()
                    if stderr_content:
                        logger.error(f"服务器stderr输出:\n{stderr_content}")
                        print(f"\n服务器错误输出:\n{stderr_content}")
                """
    
    except Exception as e:
        logger.error(f"执行过程中出错: {e}", exc_info=True)
        print(f"错误: {e}")
        print(f"错误详情: {traceback.format_exc()}")
        # 输出捕获的stderr内容
        stderr_content = stderr_capture.get_content()
        if stderr_content:
            logger.error(f"服务器stderr输出:\n{stderr_content}")
            print(f"\n服务器错误输出:\n{stderr_content}")
    
    finally:
        # 确保关闭临时文件
        if 'stderr_capture' in locals():
            stderr_capture.close()

if __name__ == "__main__":
    asyncio.run(main())