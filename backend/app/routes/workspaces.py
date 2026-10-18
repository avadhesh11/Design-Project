from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
import secrets
import logging
from datetime import datetime, timedelta, UTC

from ..database import get_db
from ..models import User, Workspace, WorkspaceMember, RoleEnum
from ..schemas import (
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceMemberDetailOut,
    WorkspaceMemberRoleUpdate,
    WorkspaceSettingsOut,
    WorkspaceSettingsUpdate,
    WorkspaceActivityItem,
    WorkspaceActivityResponse
)
from ..dependencies import get_current_user
from ..utils.supabase_client import supabase
from ..models import Document, Task, GitHubPullRequest, GitHubCommit, GitHubRepository

logger = logging.getLogger(__name__)

router=APIRouter(prefix="/workspaces",tags=["workspaces"])

def generate_invite_code() -> str:
    return secrets.token_urlsafe(8) 

@router.post("/", response_model=WorkspaceOut, status_code=201)
def create_workspace(
    body: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # print(current_user.__dict__)
    workspace = Workspace(
        name=body.name,
        description=body.description,
        invite_code=generate_invite_code(),
        invite_expires_at=datetime.now(UTC) + timedelta(days=7),
        owner_id=current_user.id
    )
    db.add(workspace)
    db.flush() #flush becoz to get workspace id before commiting final change to db otherwise it would be null after commiting

    # to make creator as admin
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=RoleEnum.admin
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace


# LIST my workspaces
@router.get("/", response_model=list[WorkspaceOut])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # memberships = db.query(WorkspaceMember).filter(
    #     WorkspaceMember.user_id == current_user.id
    # ).all()

    # workspace_ids = [m.workspace_id for m in memberships]
    # workspaces = db.query(Workspace).filter(
    #     Workspace.id.in_(workspace_ids)
    # ).all()

    workspaces=db.query(Workspace).join(WorkspaceMember,Workspace.id==WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id==current_user.id).all()
    
     
    return workspaces


# GET single workspace
@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="Not a member")

    return workspace


# JOIN via invite code
@router.post("/join/{invite_code}", response_model=WorkspaceOut)
def join_workspace(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(
        Workspace.invite_code == invite_code
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Check if invite code has expired
    if workspace.invite_expires_at:
        now_utc = datetime.now(UTC)
        expires_at = workspace.invite_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < now_utc:
            raise HTTPException(status_code=410, detail="Invite code has expired")

    # check already a member
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=RoleEnum.member
    )
    db.add(member)
    db.commit()
    db.refresh(workspace)
    return workspace


# REGENERATE invite code (owner only)
@router.post("/{workspace_id}/regenerate-invite", response_model=WorkspaceOut)
def regenerate_invite(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if str(workspace.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only owner can regenerate invite code")

    workspace.invite_code = generate_invite_code()
    workspace.invite_expires_at = datetime.now(UTC) + timedelta(days=7)
    db.commit()
    db.refresh(workspace)
    return workspace


def check_is_workspace_admin(workspace_id: str, user_id: str, db: Session) -> tuple[Workspace, WorkspaceMember]:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    # If user is workspace owner, they are always granted admin rights
    if str(ws.owner_id) == str(user_id):
        if not member:
            member = WorkspaceMember(workspace_id=ws.id, user_id=user_id, role=RoleEnum.admin)
            db.add(member)
            db.commit()
            db.refresh(member)
        elif member.role != RoleEnum.admin:
            member.role = RoleEnum.admin
            db.commit()
            db.refresh(member)
        return ws, member

    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    role_str = member.role.value if hasattr(member.role, "value") else str(member.role).lower()
    if role_str != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admins can modify workspace settings")

    return ws, member


def check_workspace_membership(workspace_id: str, user_id: str, db: Session) -> tuple[Workspace, WorkspaceMember | None]:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    if not member and str(ws.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return ws, member


# --- Member Management Endpoints ---

@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberDetailOut])
def list_workspace_members(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Verify current user is a member of this workspace or owner
    current_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    if not current_member and str(ws.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    # If owner is not registered in members yet, auto-add as admin
    if str(ws.owner_id) == str(current_user.id) and not current_member:
        current_member = WorkspaceMember(workspace_id=ws.id, user_id=current_user.id, role=RoleEnum.admin)
        db.add(current_member)
        db.commit()

    members = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id
    ).join(User, WorkspaceMember.user_id == User.id).all()

    result = []
    for m in members:
        # If member is workspace owner, ensure role displays as admin
        is_owner = str(ws.owner_id) == str(m.user_id)
        role_val = "admin" if is_owner else (m.role.value if hasattr(m.role, "value") else str(m.role))
        result.append(
            WorkspaceMemberDetailOut(
                id=m.id,
                user_id=m.user_id,
                email=m.user.email,
                role=role_val,
                joined_at=m.joined_at
            )
        )
    return result


@router.patch("/{workspace_id}/members/{member_id}/role", response_model=WorkspaceMemberDetailOut)
def update_member_role(
    workspace_id: str,
    member_id: str,
    body: WorkspaceMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws, _ = check_is_workspace_admin(workspace_id, str(current_user.id), db)

    target_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    target_member.role = RoleEnum(body.role)
    db.commit()
    db.refresh(target_member)

    return WorkspaceMemberDetailOut(
        id=target_member.id,
        user_id=target_member.user_id,
        email=target_member.user.email,
        role=target_member.role.value if hasattr(target_member.role, "value") else str(target_member.role),
        joined_at=target_member.joined_at
    )


@router.delete("/{workspace_id}/members/{member_id}", status_code=200)
def remove_workspace_member(
    workspace_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws, _ = check_is_workspace_admin(workspace_id, str(current_user.id), db)

    target_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id
    ).first()
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    if ws and str(ws.owner_id) == str(target_member.user_id):
        raise HTTPException(status_code=400, detail="Cannot remove the workspace owner")

    db.delete(target_member)
    db.commit()
    return {"message": "Member removed successfully"}


# --- Admin Settings Endpoints ---

@router.get("/{workspace_id}/settings", response_model=WorkspaceSettingsOut)
def get_workspace_settings(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    current_member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()

    if not current_member and str(ws.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    from ..models import AIChat
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = db.query(AIChat).filter(
        AIChat.workspace_id == workspace_id,
        AIChat.user_id == current_user.id,
        AIChat.role == "user",
        AIChat.created_at >= today_start
    ).count()

    is_admin = (str(ws.owner_id) == str(current_user.id)) or (
        current_member is not None and (
            current_member.role == RoleEnum.admin or
            (hasattr(current_member.role, "value") and current_member.role.value == "admin") or
            str(current_member.role).lower() == "admin"
        )
    )

    return WorkspaceSettingsOut(
        workspace_id=ws.id,
        name=ws.name,
        owner_id=ws.owner_id,
        is_admin=is_admin,
        settings_allow_dm=ws.settings_allow_dm,
        settings_ai_daily_limit=ws.settings_ai_daily_limit,
        settings_allow_file_uploads=ws.settings_allow_file_uploads,
        settings_restrict_invites=ws.settings_restrict_invites,
        ai_provider=getattr(ws, "ai_provider", "gemini") or "gemini",
        ai_model=getattr(ws, "ai_model", "gemini-2.5-flash") or "gemini-2.5-flash",
        ai_ollama_url=getattr(ws, "ai_ollama_url", "http://localhost:11434") or "http://localhost:11434",
        ai_today_usage=used_today,
        ai_daily_limit=ws.settings_ai_daily_limit
    )


@router.patch("/{workspace_id}/settings", response_model=WorkspaceSettingsOut)
def update_workspace_settings(
    workspace_id: str,
    body: WorkspaceSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws, current_member = check_is_workspace_admin(workspace_id, str(current_user.id), db)

    if body.settings_allow_dm is not None:
        ws.settings_allow_dm = body.settings_allow_dm
    if body.settings_ai_daily_limit is not None:
        ws.settings_ai_daily_limit = max(0, body.settings_ai_daily_limit)
    if body.settings_allow_file_uploads is not None:
        ws.settings_allow_file_uploads = body.settings_allow_file_uploads
    if body.settings_restrict_invites is not None:
        ws.settings_restrict_invites = body.settings_restrict_invites
    if body.ai_provider is not None:
        ws.ai_provider = body.ai_provider.strip().lower()
    if body.ai_model is not None:
        ws.ai_model = body.ai_model.strip()
    if body.ai_ollama_url is not None:
        ws.ai_ollama_url = body.ai_ollama_url.strip()

    db.commit()
    db.refresh(ws)

    from ..models import AIChat
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = db.query(AIChat).filter(
        AIChat.workspace_id == workspace_id,
        AIChat.user_id == current_user.id,
        AIChat.role == "user",
        AIChat.created_at >= today_start
    ).count()

    return WorkspaceSettingsOut(
        workspace_id=ws.id,
        name=ws.name,
        owner_id=ws.owner_id,
        is_admin=True,
        settings_allow_dm=ws.settings_allow_dm,
        settings_ai_daily_limit=ws.settings_ai_daily_limit,
        settings_allow_file_uploads=ws.settings_allow_file_uploads,
        settings_restrict_invites=ws.settings_restrict_invites,
        ai_provider=getattr(ws, "ai_provider", "gemini") or "gemini",
        ai_model=getattr(ws, "ai_model", "gemini-2.5-flash") or "gemini-2.5-flash",
        ai_ollama_url=getattr(ws, "ai_ollama_url", "http://localhost:11434") or "http://localhost:11434",
        ai_today_usage=used_today,
        ai_daily_limit=ws.settings_ai_daily_limit
    )


@router.post("/{workspace_id}/test-ollama")
def test_ollama_connection(
    workspace_id: str,
    ollama_url: str = "http://localhost:11434",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_membership(workspace_id, str(current_user.id), db)
    import requests
    try:
        url = (ollama_url or "http://localhost:11434").rstrip("/") + "/api/tags"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name") for m in data.get("models", [])]
            return {
                "status": "connected",
                "message": f"Successfully connected to Ollama! Found {len(models)} installed models.",
                "models": models
            }
        else:
            return {
                "status": "error",
                "message": f"Ollama responded with HTTP {resp.status_code}."
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Cannot reach Ollama at {ollama_url}. Is Ollama running on your machine? ({str(e)})"
        }


# DELETE workspace (admin only)
@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if str(workspace.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only owner can delete")

    db.delete(workspace)
    db.commit()


def to_utc_dt(dt):
    if dt is None:
        return datetime.min.replace(tzinfo=UTC)
    if isinstance(dt, str):
        try:
            return datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


import json
from ..utils.redis_client import get_redis_client

# --- Recent Developments / Workspace Activity Feed (No LLM, Fast Aggregation with Redis Cache) ---

@router.get("/{workspace_id}/activity", response_model=WorkspaceActivityResponse)
async def get_workspace_activity(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # verify membership
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    if not member and str(ws.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not a workspace member")

    # Check Redis cache first (15 second TTL)
    cache_key = f"orbit:ws_activity:{workspace_id}:{current_user.id}"
    redis_client = get_redis_client()
    if redis_client:
        try:
            cached_raw = redis_client.get(cache_key)
            if cached_raw:
                return json.loads(cached_raw)
        except Exception as e:
            logger.debug("Redis activity cache read error: %s", e)

    activities: list[WorkspaceActivityItem] = []
    user_ids: set[uuid.UUID] = set()

    try:
        # 1. Documents (created / updated)
        docs = db.query(Document).filter(Document.workspace_id == workspace_id).order_by(Document.updated_at.desc()).limit(15).all()
        for d in docs:
            if d.created_by:
                user_ids.add(d.created_by)

        # 2. Tasks (created / updated)
        tasks = db.query(Task).filter(Task.workspace_id == workspace_id).order_by(Task.updated_at.desc()).limit(15).all()
        for t in tasks:
            if t.created_by:
                user_ids.add(t.created_by)
            if t.assigned_to:
                user_ids.add(t.assigned_to)

        # 3. Workspace Members joined
        members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).order_by(WorkspaceMember.joined_at.desc()).limit(15).all()
        for m in members:
            user_ids.add(m.user_id)

        # 4. GitHub PRs and Commits
        repos = db.query(GitHubRepository).filter(GitHubRepository.workspace_id == workspace_id, GitHubRepository.is_active == True).all()
        repo_ids = [r.id for r in repos]
        prs = []
        commits = []
        if repo_ids:
            prs = db.query(GitHubPullRequest).filter(GitHubPullRequest.repository_id.in_(repo_ids)).order_by(GitHubPullRequest.created_at.desc()).limit(8).all()
            commits = db.query(GitHubCommit).filter(GitHubCommit.repository_id.in_(repo_ids)).order_by(GitHubCommit.committed_at.desc()).limit(12).all()


        # 5. Pre-fetch User Emails
        users = db.query(User).filter(User.id.in_(list(user_ids))).all() if user_ids else []
        user_map = {u.id: u.email for u in users}

        # Format document activities
        for d in docs:
            is_new = d.created_at and d.updated_at and abs((d.updated_at - d.created_at).total_seconds()) < 60
            actor = user_map.get(d.created_by, "Team member")
            activities.append(WorkspaceActivityItem(
                id=f"doc_{d.id}",
                category="document",
                action="Created document" if is_new else "Updated document",
                title=d.title or "Untitled Document",
                description=f"Document '{d.title}' was {'created' if is_new else 'updated'} by @{actor.split('@')[0]}",
                actor_email=actor,
                target_id=str(d.id),
                target_link=f"/dashboard/documents/{d.id}",
                created_at=to_utc_dt(d.updated_at or d.created_at)
            ))

        # Format task activities
        for t in tasks:
            creator_email = user_map.get(t.created_by, "Admin")
            status_label = t.status.value if hasattr(t.status, "value") else str(t.status)
            priority_label = t.priority.value if hasattr(t.priority, "value") else str(t.priority)
            is_new = t.created_at and t.updated_at and abs((t.updated_at - t.created_at).total_seconds()) < 60
            action_label = f"Created task" if is_new else f"Updated task"
            activities.append(WorkspaceActivityItem(
                id=f"task_{t.id}",
                category="task",
                action=action_label,
                title=t.title,
                description=f"Status: {status_label.upper()} • Priority: {priority_label.upper()}",
                actor_email=creator_email,
                target_id=str(t.id),
                target_link="/dashboard/tasks",
                status=status_label,
                priority=priority_label,
                created_at=to_utc_dt(t.updated_at or t.created_at)
            ))

        # 6. Format Chat Messages from Supabase (Strict Privacy: only public channel msgs or DMs involving current_user)
        try:
            chat_res = supabase.table("messages")\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .or_(f"recipient_id.is.null,recipient_id.eq.{current_user.id},sender_id.eq.{current_user.id}")\
                .order("created_at", desc=True)\
                .limit(15)\
                .execute()
            if chat_res.data:
                for msg in chat_res.data:
                    rec_id = msg.get("recipient_id")
                    is_dm = rec_id is not None
                    sender_email = msg.get("sender_email", "Team member")
                    sender_name = sender_email.split("@")[0]

                    if is_dm:
                        if str(msg.get("sender_id")) == str(current_user.id):
                            action_title = "Direct Message (Sent)"
                            title = "Private message sent"
                        else:
                            action_title = "Direct Message (Received)"
                            title = f"DM from @{sender_name}"
                    else:
                        action_title = "Workspace Chat"
                        title = f"Chat from @{sender_name}"

                    activities.append(WorkspaceActivityItem(
                        id=f"msg_{msg['id']}",
                        category="chat",
                        action=action_title,
                        title=title,
                        description=msg.get("content", "")[:90] + ("..." if len(msg.get("content", "")) > 90 else ""),
                        actor_email=sender_email,
                        target_id=str(msg["id"]),
                        target_link="/dashboard/chat",
                        created_at=to_utc_dt(msg.get("created_at"))
                    ))
        except Exception as e:
            logger.warning(f"Failed to query chat activity: {e}")


        # Format member join activities
        for m in members:
            member_email = user_map.get(m.user_id, "New Member")
            role_str = m.role.value if hasattr(m.role, "value") else str(m.role)
            activities.append(WorkspaceActivityItem(
                id=f"member_{m.id}",
                category="member",
                action="Joined workspace",
                title=f"@{member_email.split('@')[0]} joined",
                description=f"Role: {role_str.upper()}",
                actor_email=member_email,
                target_id=str(m.id),
                target_link="/dashboard/settings",
                status=role_str,
                created_at=to_utc_dt(m.joined_at)
            ))

        # Format GitHub activities
        for pr in prs:
            activities.append(WorkspaceActivityItem(
                id=f"pr_{pr.id}",
                category="github",
                action=f"PR #{pr.pr_number} {pr.state}",
                title=pr.title,
                description=f"Pull Request #{pr.pr_number} by @{pr.author_login or 'dev'}",
                actor_email=pr.author_login,
                target_id=str(pr.id),
                target_link="/dashboard/integrations",
                status=pr.state,
                created_at=to_utc_dt(pr.created_at)
            ))

        for cm in commits:
            activities.append(WorkspaceActivityItem(
                id=f"commit_{cm.id}",
                category="github",
                action="Pushed commit",
                title=cm.message.split("\n")[0][:60],
                description=f"Commit [{cm.sha[:7]}] by @{cm.author_login or 'dev'} (+{cm.additions}/-{cm.deletions})",
                actor_email=cm.author_login,
                target_id=str(cm.id),
                target_link="/dashboard/integrations",
                created_at=to_utc_dt(cm.committed_at)
            ))

        # Sort all activities by timestamp descending with normalized UTC datetimes
        activities.sort(key=lambda a: to_utc_dt(a.created_at), reverse=True)
    except Exception as e:
        logger.error(f"Error compiling workspace activity: {e}", exc_info=True)

    resp_obj = WorkspaceActivityResponse(
        workspace_id=ws.id,
        activities=activities[:30]
    )

    if redis_client:
        try:
            redis_client.setex(cache_key, 15, resp_obj.model_dump_json() if hasattr(resp_obj, "model_dump_json") else resp_obj.json())
        except Exception as e:
            logger.debug("Failed to set Redis activity cache: %s", e)

    return resp_obj


