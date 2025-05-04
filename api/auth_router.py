"""
Authentication API router.
"""
import logging
from typing import Dict, Optional
from fastapi import APIRouter, Request, Header, HTTPException, Depends

from anp_core.auth.did_auth import get_and_validate_domain, handle_did_auth
from anp_core.auth.token_auth import handle_bearer_auth

router = APIRouter(tags=["authentication"])


@router.post("/auth/did-wba", summary="Authenticate using DID WBA")
async def did_wba_auth(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Dict:
    """
    Authenticate using DID WBA method.
    
    Args:
        request: FastAPI request object
        authorization: DID WBA authorization header
        
    Returns:
        Dict: Authentication result with token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Get and validate domain
    domain = get_and_validate_domain(request)
    
    # Process DID WBA authentication
    return await handle_did_auth(authorization, domain)


@router.get("/auth/verify", summary="Verify bearer token")
async def verify_token(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Dict:
    """
    Verify JWT bearer token.
    
    Args:
        request: FastAPI request object
        authorization: Bearer token header
        
    Returns:
        Dict: Token verification result
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format, must use Bearer scheme")
    
    # Verify bearer token
    user_data = await handle_bearer_auth(authorization)
    
    return {
        "verified": True,
        "did": user_data["did"],
        "message": "Token verified successfully"
    }


@router.get("/wba/test", summary="Test endpoint for DID WBA authentication")
async def test_endpoint(request: Request) -> Dict:
    """
    Test endpoint for DID WBA authentication.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict: Test result
    """
    user = getattr(request.state, "user", None)
    
    if not user:
        return {
            "status": "warning",
            "message": "No authentication provided, but access allowed"
        }
    
    response = {
        "status": "success",
        "message": "Successfully authenticated",
        "did": user.get("did"),
        "authenticated": True
    }
    
    # 只有当access_token存在且不为空时才添加Authorization字段
    if user.get("access_token"):
        response["Authorization"] = "bearer " + user.get("access_token")
    
    return response
