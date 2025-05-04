"""
Authentication middleware module.
"""
import logging
from typing import List, Optional, Callable
from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse

from anp_core.auth.did_auth import handle_did_auth, get_and_validate_domain
from anp_core.auth.token_auth import handle_bearer_auth


# Define exempt paths that don't require authentication
EXEMPT_PATHS = [
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/wba/user/",  # Allow access to DID documents
    "/",           # Allow access to root endpoint
    "/agents/example/ad.json"  # Allow access to agent description
]  # "/wba/test" path removed from exempt list, now requires authentication


async def verify_auth_header(request: Request) -> dict:
    """
    Verify authentication header and return authenticated user data.
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: Authenticated user data
        
    Raises:
        HTTPException: When authentication fails
    """
    # Get authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Handle DID WBA authentication
    if not auth_header.startswith("Bearer "):
        domain = get_and_validate_domain(request)
        return await handle_did_auth(auth_header, domain)
    
    # Handle Bearer token authentication
    return await handle_bearer_auth(auth_header)


async def authenticate_request(request: Request) -> Optional[dict]:
    """
    Authenticate a request and return user data if successful.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Optional[dict]: Authenticated user data or None for exempt paths
        
    Raises:
        HTTPException: When authentication fails
    """
    # Log request path and headers for debugging
    logging.info(f"Authenticating request to path: {request.url.path}")
    logging.info(f"Request headers: {request.headers}")
    
    # Check if path is exempt from authentication
    for exempt_path in EXEMPT_PATHS:
        logging.info(f"Checking if {request.url.path} matches exempt path {exempt_path}")
        # 特殊处理根路径"/"，它只应该精确匹配
        if exempt_path == "/":
            if request.url.path == "/":
                logging.info(f"Path {request.url.path} is exempt from authentication (matched root path)")
                return None
        # 其他路径的匹配逻辑
        elif request.url.path == exempt_path or (exempt_path.endswith('/') and request.url.path.startswith(exempt_path)):
            logging.info(f"Path {request.url.path} is exempt from authentication (matched {exempt_path})")
            return None
    
    # 特别检查 /wba/test 路径，确保它不被视为免认证
    if request.url.path == "/wba/test":
        logging.info("Path /wba/test requires authentication (special check)")
    
    logging.info(f"Path {request.url.path} requires authentication")
    
    # Verify authentication
    return await verify_auth_header(request)


async def auth_middleware(request: Request, call_next: Callable) -> Response:
    """
    Authentication middleware for FastAPI.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware or endpoint handler
        
    Returns:
        Response: API response
    """
    try:
        # Add user data to request state if authenticated
        request.state.user = await authenticate_request(request)
        return await call_next(request)
    
    except HTTPException as exc:
        logging.error(f"Authentication error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    except Exception as e:
        logging.error(f"Unexpected error in auth middleware: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
