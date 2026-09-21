from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, UTC
import uuid
import json
import logging

from ..database import get_db
from ..models import User, Workspace, WorkspaceMember, RoleEnum, AIChat, AIChatSession
from ..schemas import (
    AIChatRequest,
    AIChatOut,
    AIChatSessionCreate,
    AIChatSessionUpdate,
    AIChatSessionOut
)
from ..dependencies import get_current_user
from ..agents.agent import run_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def get_member_role(workspace_id: str, user_id: str, db: Session):
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a workspace member")
    return member


def check_and_get_daily_quota(workspace_id: str, user_id: str, db: Session) -> tuple[int, int]:
    """Returns (used_today, daily_limit). Raises 429 if exceeded."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    limit = ws.settings_ai_daily_limit if ws.settings_ai_daily_limit is not None else 50
    if limit <= 0:  # 0 or negative = unlimited
        return 0, 0

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = db.query(AIChat).filter(
        AIChat.workspace_id == workspace_id,
        AIChat.user_id == user_id,
        AIChat.role == "user",
        AIChat.created_at >= today_start
    ).count()

    if used_today >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI message quota of {limit} prompts reached for this workspace today. Contact your workspace admin to increase limits."
        )

    return used_today, limit


# --- AI Chat Sessions ---

@router.get("/{workspace_id}/sessions", response_model=list[AIChatSessionOut])
def list_ai_sessions(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    sessions = db.query(AIChatSession).filter(
        AIChatSession.workspace_id == workspace_id,
        AIChatSession.user_id == current_user.id
    ).order_by(AIChatSession.updated_at.desc()).all()

    result = []
    for s in sessions:
        msg_count = db.query(AIChat).filter(AIChat.session_id == s.id).count()
        result.append(
            AIChatSessionOut(
                id=s.id,
                workspace_id=s.workspace_id,
                user_id=s.user_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                messages_count=msg_count
            )
        )
    return result


@router.post("/{workspace_id}/sessions", response_model=AIChatSessionOut, status_code=201)
def create_ai_session(
    workspace_id: str,
    body: AIChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    session = AIChatSession(
        workspace_id=workspace_id,
        user_id=current_user.id,
        title=body.title or "New Chat"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return AIChatSessionOut(
        id=session.id,
        workspace_id=session.workspace_id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages_count=0
    )


@router.get("/{workspace_id}/sessions/{session_id}/messages", response_model=list[AIChatOut])
def get_session_messages(
    workspace_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    messages = db.query(AIChat).filter(
        AIChat.workspace_id == workspace_id,
        AIChat.user_id == current_user.id,
        AIChat.session_id == session_id
    ).order_by(AIChat.created_at.asc()).all()
    return messages


@router.patch("/{workspace_id}/sessions/{session_id}", response_model=AIChatSessionOut)
def rename_ai_session(
    workspace_id: str,
    session_id: str,
    body: AIChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    session = db.query(AIChatSession).filter(
        AIChatSession.id == session_id,
        AIChatSession.workspace_id == workspace_id,
        AIChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = body.title.strip() or "Untitled Chat"
    session.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)

    msg_count = db.query(AIChat).filter(AIChat.session_id == session.id).count()
    return AIChatSessionOut(
        id=session.id,
        workspace_id=session.workspace_id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages_count=msg_count
    )


@router.delete("/{workspace_id}/sessions/{session_id}", status_code=200)
def delete_ai_session(
    workspace_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    session = db.query(AIChatSession).filter(
        AIChatSession.id == session_id,
        AIChatSession.workspace_id == workspace_id,
        AIChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"message": "AI chat session deleted successfully"}


# --- AI Chat Execution ---

@router.post("/chat")
async def chat(
    body: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    member = get_member_role(body.workspace_id, str(current_user.id), db)
    is_admin = member.role == RoleEnum.admin

    # Validate daily quota
    check_and_get_daily_quota(body.workspace_id, str(current_user.id), db)

    # Resolve or create session
    session = None
    if body.session_id:
        session = db.query(AIChatSession).filter(
            AIChatSession.id == body.session_id,
            AIChatSession.workspace_id == body.workspace_id,
            AIChatSession.user_id == current_user.id
        ).first()

    if not session:
        prompt_preview = body.message.strip()
        auto_title = (prompt_preview[:36] + "...") if len(prompt_preview) > 36 else prompt_preview
        session = AIChatSession(
            workspace_id=body.workspace_id,
            user_id=current_user.id,
            title=auto_title or "New Chat"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        # If session has default title "New Chat", auto-rename to first prompt
        if session.title in ["New Chat", "Untitled Chat", ""]:
            prompt_preview = body.message.strip()
            session.title = (prompt_preview[:36] + "...") if len(prompt_preview) > 36 else prompt_preview

    # Save user message to chat history
    user_chat = AIChat(
        workspace_id=body.workspace_id,
        user_id=current_user.id,
        session_id=session.id,
        role="user",
        message=body.message
    )
    db.add(user_chat)
    session.updated_at = datetime.now(UTC)
    db.commit()

    result = await run_agent(
        message=body.message,
        workspace_id=body.workspace_id,
        user_id=str(current_user.id),
        user_email=current_user.email,
        is_admin=is_admin,
        history=[{"role": m.role, "content": m.content} for m in body.history]
    )

    response_content = result.get("response", "")
    if isinstance(response_content, list):
        response_text = "".join(
            b.get("text", "") or b.get("content", "") if isinstance(b, dict) else str(b)
            for b in response_content
        )
    elif isinstance(response_content, dict):
        response_text = json.dumps(response_content)
    else:
        response_text = str(response_content)

    # Save model response to chat history
    model_chat = AIChat(
        workspace_id=body.workspace_id,
        user_id=current_user.id,
        session_id=session.id,
        role="model",
        message=response_text
    )
    db.add(model_chat)
    session.updated_at = datetime.now(UTC)
    db.commit()

    result["session_id"] = str(session.id)
    result["session_title"] = session.title
    return result


@router.get("/{workspace_id}/history", response_model=list[AIChatOut])
def get_ai_chat_history(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    history = db.query(AIChat).filter(
        AIChat.workspace_id == workspace_id,
        AIChat.user_id == current_user.id
    ).order_by(AIChat.created_at.asc()).all()
    return history


@router.delete("/{workspace_id}/history", status_code=200)
def clear_ai_chat_history(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_member_role(workspace_id, str(current_user.id), db)
    db.query(AIChat).filter(
        AIChat.workspace_id == workspace_id,
        AIChat.user_id == current_user.id
    ).delete()
    db.query(AIChatSession).filter(
        AIChatSession.workspace_id == workspace_id,
        AIChatSession.user_id == current_user.id
    ).delete()
    db.commit()
    return {"message": "All AI chat sessions cleared successfully"}