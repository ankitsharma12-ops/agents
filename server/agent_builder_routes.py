"""Prototype agent builder API routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Depends, Query, Request
from pydantic import BaseModel, Field

import admin_auth
from prototype import agent_builder as builder

router = APIRouter(prefix="/api/agent-builder", tags=["agent-builder"])


def _get_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    token = (authorization or "").replace("Bearer ", "").strip()
    return admin_auth.verify_token(token) if token else None


def _require_user(authorization: Optional[str] = Header(None)) -> dict:
    user = _get_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


class CreateAgentRequest(BaseModel):
    name: str = "Untitled Agent"
    slug: Optional[str] = None
    description: str = ""
    system_prompt: str = ""
    llm_model: str = "vertex_ai.gemini-2.5-pro"
    llm_provider: str = "pwc_genai"
    category_id: str = "general"
    tools_config: List[Dict[str, Any]] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class TestAgentRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@router.post("/agents")
async def create_agent(req: CreateAgentRequest, user: dict = Depends(_require_user)):
    agent = builder.create_agent(req.model_dump(exclude_none=True), owner_id=user["id"])
    return {"success": True, "agent": agent}


@router.get("/agents")
async def list_agents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(_require_user),
):
    result = builder.list_agents(owner_id=user.get("user_id"))
    agents = result["agents"][offset : offset + limit]
    return {"success": True, "agents": agents, "total": result["total"], "limit": limit, "offset": offset}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, user: dict = Depends(_require_user)):
    agent = builder.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "agent": agent}


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, req: CreateAgentRequest, user: dict = Depends(_require_user)):
    agent = builder.update_agent(agent_id, req.model_dump(exclude_none=True))
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "agent": agent}


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, user: dict = Depends(_require_user)):
    if not builder.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True}


@router.post("/agents/{agent_id}/clone")
async def clone_agent(agent_id: str, user: dict = Depends(_require_user)):
    agent = builder.clone_agent(agent_id, user["id"])
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "agent": agent}


@router.get("/tools")
async def list_tools(user: dict = Depends(_require_user)):
    return {"success": True, "tools": builder.list_tools()}


@router.get("/agents/{agent_id}/versions")
async def list_versions(agent_id: str, user: dict = Depends(_require_user)):
    return {"success": True, "versions": builder.list_versions(agent_id)}


@router.post("/agents/{agent_id}/versions")
async def create_version(agent_id: str, user: dict = Depends(_require_user)):
    versions = builder.list_versions(agent_id)
    return {"success": True, "version": versions[0] if versions else {}}


@router.get("/agents/{agent_id}/versions/{version}/diff")
async def version_diff(agent_id: str, version: str, user: dict = Depends(_require_user)):
    return {"success": True, "version": version, "diff": []}


@router.post("/agents/{agent_id}/rollback")
async def rollback(agent_id: str, user: dict = Depends(_require_user)):
    agent = builder.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "agent": agent}


@router.post("/agents/{agent_id}/test")
async def test_agent(agent_id: str, req: TestAgentRequest, user: dict = Depends(_require_user)):
    return await builder.test_agent_stream(agent_id, req.query, req.session_id)


@router.delete("/agents/{agent_id}/test/session")
async def clear_test_session(agent_id: str, session_id: str = Query(...), user: dict = Depends(_require_user)):
    return {"success": True}


@router.post("/agents/{agent_id}/deploy")
async def deploy_agent(agent_id: str, user: dict = Depends(_require_user)):
    agent = builder.update_agent(agent_id, {"status": "deployed"})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "agent": agent}


@router.post("/agents/{agent_id}/publish")
async def publish_agent(agent_id: str, user: dict = Depends(_require_user)):
    agent = builder.update_agent(agent_id, {"status": "published", "published_at": builder._now_iso()})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "auto_approved": True, "agent": agent}


@router.get("/submissions")
async def list_submissions(user: dict = Depends(_require_user)):
    return {"success": True, "submissions": []}


@router.post("/submissions/{submission_id}/review")
async def review_submission(submission_id: str, user: dict = Depends(_require_user)):
    return {"success": True, "submission": {"id": submission_id, "status": "approved"}}


@router.get("/agents/{agent_id}/stats")
async def agent_stats(agent_id: str, days: int = Query(30), user: dict = Depends(_require_user)):
    return {"success": True, "stats": builder.agent_stats(agent_id, days)}


@router.get("/published")
async def list_published_agents(limit: int = Query(100, ge=1, le=500)):
    return {"success": True, "agents": builder.get_published()[:limit]}


@router.get("/oauth/google/config")
async def google_oauth_config():
    return {"enabled": False}


@router.post("/oauth/google/exchange")
async def google_oauth_exchange():
    raise HTTPException(status_code=501, detail="OAuth not available in prototype")


@router.post("/oauth/google/disconnect")
async def google_oauth_disconnect(user: dict = Depends(_require_user)):
    return {"success": True}


@router.post("/invoke/{agent_slug}")
async def invoke_agent(agent_slug: str, request: Request):
    body = await request.json()
    query = body.get("query", "")
    return await builder.test_agent_stream(agent_slug, query, body.get("session_id"))
