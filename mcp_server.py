"""MCP Server for DID WBA Example.

This module implements a Model Context Protocol (MCP) server that exposes
the DID WBA client and server functionalities as MCP tools.
"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

# Import DID WBA server and client functions
from did_server import (
    start_server,
    stop_server,
    start_client,
    stop_client,
    server_running,
    client_running,
    client_chat_messages,
    client_new_message_event
)

# Create a named MCP server
mcp = FastMCP("DID WBA MCP Server")

# Store connection events for notification
connection_events = []
new_connection_event = asyncio.Event()

@dataclass
class AppContext:
    """Application context for MCP server."""
    server_status: Dict[str, Any] = None
    client_status: Dict[str, Any] = None
    connection_events: List[Dict[str, Any]] = None

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context."""
    # Initialize on startup
    app_context = AppContext(
        server_status={"running": False, "port": None},
        client_status={"running": False, "port": None},
        connection_events=[]
    )
    
    # Start connection event listener
    asyncio.create_task(connection_event_listener(app_context))
    
    try:
        yield app_context
    finally:
        # Cleanup on shutdown
        if app_context.server_status.get("running"):
            stop_server()
        if app_context.client_status.get("running"):
            stop_client()

# Pass lifespan to server
mcp = FastMCP("DID WBA MCP Server", lifespan=app_lifespan)

async def connection_event_listener(app_context: AppContext):
    """Listen for connection events from the DID WBA server."""
    global client_chat_messages, client_new_message_event, connection_events, new_connection_event
    
    while True:
        try:
            # Wait for new message event from client
            await client_new_message_event.wait()
            
            # If there are new messages, add them to connection events
            if client_chat_messages and client_new_message_event.is_set():
                # Get the latest message
                latest_message = client_chat_messages[-1]
                
                # Add to connection events
                connection_events.append(latest_message)
                if len(connection_events) > 50:
                    connection_events = connection_events[-50:]
                
                # Update app context
                app_context.connection_events = connection_events
                
                # Set event to notify subscribers
                new_connection_event.set()
                
                # Reset client event
                client_new_message_event.clear()
                
            # Small delay to prevent CPU hogging
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in connection event listener: {e}")
            await asyncio.sleep(1)  # Wait before retrying

@mcp.tool()
def start_did_server(ctx: Context, port: Optional[int] = None) -> Dict[str, Any]:
    """Start the DID WBA server.
    
    Args:
        port: Optional server port number (default: from settings)
        
    Returns:
        Dict with server status information
    """
    app_context = ctx.request_context.lifespan_context
    
    # Check if server is already running
    if server_running:
        return {"status": "already_running", "message": "服务器已经在运行中"}
    
    # Start the server
    start_server(port=port)
    
    # Update app context
    app_context.server_status = {"running": True, "port": port}
    
    return {
        "status": "success",
        "message": f"服务器已在端口 {port if port else '默认端口'} 启动",
        "is_running": True
    }

@mcp.tool()
def stop_did_server(ctx: Context) -> Dict[str, Any]:
    """Stop the DID WBA server.
    
    Returns:
        Dict with server status information
    """
    app_context = ctx.request_context.lifespan_context
    
    # Check if server is running
    if not server_running:
        return {"status": "not_running", "message": "服务器未运行"}
    
    # Stop the server
    stop_server()
    
    # Update app context
    app_context.server_status = {"running": False, "port": None}
    
    return {
        "status": "success",
        "message": "服务器已关闭",
        "is_running": False
    }

@mcp.tool()
def start_did_client(ctx: Context, port: Optional[int] = None, unique_id: Optional[str] = None, message: Optional[str] = None) -> Dict[str, Any]:
    """Start the DID WBA client.
    
    Args:
        port: Optional target server port number
        unique_id: Optional unique identifier for the client
        message: Optional custom message to send
        
    Returns:
        Dict with client status information
    """
    app_context = ctx.request_context.lifespan_context
    
    # Check if client is already running
    if client_running:
        return {"status": "already_running", "message": "客户端已经在运行中"}
    
    # Start the client
    start_client(port=port, unique_id_arg=unique_id, silent=False, from_chat=False, msg=message)
    
    # Update app context
    app_context.client_status = {"running": True, "port": port, "unique_id": unique_id}
    
    return {
        "status": "success",
        "message": f"客户端已启动，目标端口: {port if port else '默认端口'}",
        "is_running": True
    }

@mcp.tool()
def stop_did_client(ctx: Context) -> Dict[str, Any]:
    """Stop the DID WBA client.
    
    Returns:
        Dict with client status information
    """
    app_context = ctx.request_context.lifespan_context
    
    # Check if client is running
    if not client_running:
        return {"status": "not_running", "message": "客户端未运行"}
    
    # Stop the client
    stop_client()
    
    # Update app context
    app_context.client_status = {"running": False, "port": None, "unique_id": None}
    
    return {
        "status": "success",
        "message": "客户端已关闭",
        "is_running": False
    }

@mcp.tool()
async def get_connection_events(ctx: Context, wait_for_new: bool = False) -> Dict[str, Any]:
    """Get connection events from the DID WBA server.
    
    Args:
        wait_for_new: Whether to wait for new events
        
    Returns:
        Dict with connection events
    """
    global connection_events, new_connection_event
    
    if wait_for_new:
        # Wait for new connection event with timeout
        try:
            await asyncio.wait_for(new_connection_event.wait(), timeout=30)
            # Reset event for next notification
            new_connection_event.clear()
        except asyncio.TimeoutError:
            return {"status": "timeout", "message": "等待新连接事件超时", "events": connection_events}
    
    return {
        "status": "success",
        "message": "获取连接事件成功",
        "events": connection_events
    }

@mcp.resource("status://did-wba")
def get_status(ctx: Context) -> Dict[str, Any]:
    """Get the current status of the DID WBA server and client.
    
    Returns:
        Dict with status information
    """
    app_context = ctx.request_context.lifespan_context
    
    return {
        "server": {
            "running": server_running,
            "status": app_context.server_status
        },
        "client": {
            "running": client_running,
            "status": app_context.client_status
        },
        "connection_events_count": len(connection_events)
    }

def run_mcp_server():
    """Run the MCP server."""
    # Install the MCP server for development
    import sys
    from mcp.cli.dev import dev_command
    
    # Run the MCP server in development mode
    sys.argv = ["mcp", "dev", __file__]
    dev_command()

if __name__ == "__main__":
    run_mcp_server()