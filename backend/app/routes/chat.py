from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User, Workspace, WorkspaceMember
from ..schemas import MessageOut, MessageCreate
from ..dependencies import get_current_user
from ..utils.supabase_client import supabase  

router = APIRouter(prefix="/chat", tags=["chat"])


def is_workspace_member(workspace_id: str, user_id: str, db: Session):
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a workspace member")
    return member 


@router.post("/{workspace_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    workspace_id: str,
    body: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_workspace_member(workspace_id, str(current_user.id), db)
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    recipient_id_str = str(body.recipient_id) if body.recipient_id else None

    # If this is a direct message
    if recipient_id_str:
        if not ws.settings_allow_dm:
            raise HTTPException(status_code=403, detail="Direct messaging is disabled by workspace admin")

        # Verify recipient belongs to this workspace
        rec_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == recipient_id_str
        ).first()
        if not rec_member:
            raise HTTPException(status_code=400, detail="Recipient is not a member of this workspace")

    msg_payload = {
        "content": body.content,
        "workspace_id": workspace_id,
        "sender_id": str(current_user.id),
        "sender_email": current_user.email,
        "recipient_id": recipient_id_str
    }

    result = supabase.table("messages").insert(msg_payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to send message")

    return result.data[0]


@router.get("/{workspace_id}/messages")
def get_messages(
    workspace_id: str,
    recipient_id: Optional[str] = Query(None),
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_workspace_member(workspace_id, str(current_user.id), db)

    if recipient_id:
        # Direct Messages between current_user and recipient_id
        query = supabase.table("messages") \
            .select("*") \
            .eq("workspace_id", workspace_id) \
            .or_(
                f"and(sender_id.eq.{current_user.id},recipient_id.eq.{recipient_id}),"
                f"and(sender_id.eq.{recipient_id},recipient_id.eq.{current_user.id})"
            ) \
            .order("created_at", desc=False) \
            .limit(limit)
    else:
        # Public workspace room messages (recipient_id IS NULL)
        query = supabase.table("messages") \
            .select("*") \
            .eq("workspace_id", workspace_id) \
            .is_("recipient_id", "null") \
            .order("created_at", desc=False) \
            .limit(limit)

    result = query.execute()
    return result.data or []

@router.get("/{workspace_id}/inbox")
def get_chat_inbox(
    workspace_id: str,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_workspace_member(workspace_id, str(current_user.id), db)

    query = supabase.table("messages") \
        .select("*") \
        .eq("workspace_id", workspace_id) \
        .or_(
            f"recipient_id.eq.{current_user.id},"
            f"sender_id.eq.{current_user.id},"
            f"recipient_id.is.null"
        ) \
        .order("created_at", desc=False) \
        .limit(limit)

    result = query.execute()
    return result.data or []