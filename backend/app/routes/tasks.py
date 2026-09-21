from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
import html
import logging
from ..database import get_db, engine, Base
from ..models import User, Task, TaskAssignee, WorkspaceMember, Workspace, RoleEnum
from ..schemas import TaskCreate, TaskUpdate, TaskOut
from ..dependencies import get_current_user
from ..agents.tools import _send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])



def check_workspace_member(workspace_id: str, user_id: str, db: Session) -> tuple[Workspace, WorkspaceMember]:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    # If owner is not explicitly in WorkspaceMember table, grant access
    if str(ws.owner_id) == str(user_id):
        if not member:
            member = WorkspaceMember(workspace_id=ws.id, user_id=user_id, role=RoleEnum.admin)
            db.add(member)
            db.commit()
            db.refresh(member)
        return ws, member

    if not member:
        raise HTTPException(status_code=403, detail="Not a workspace member")
    return ws, member


def check_is_workspace_admin(workspace_id: str, user_id: str, db: Session) -> tuple[Workspace, WorkspaceMember]:
    ws, member = check_workspace_member(workspace_id, user_id, db)
    if str(ws.owner_id) == str(user_id):
        return ws, member

    role_str = member.role.value if hasattr(member.role, "value") else str(member.role).lower()
    if role_str != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only workspace admins can create or manage tasks"
        )
    return ws, member


@router.post("/", response_model=TaskOut, status_code=201)
def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ws, _ = check_is_workspace_admin(str(body.workspace_id), str(current_user.id), db)

    # Collect assigned user IDs (deduplicated)
    target_ids = []
    if body.assigned_to_ids:
        for uid in body.assigned_to_ids:
            if uid not in target_ids:
                target_ids.append(uid)
    elif body.assigned_to:
        target_ids.append(body.assigned_to)

    assigned_users = []
    if target_ids:
        # Validate that all assigned users belong to the workspace
        valid_members = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == body.workspace_id,
            WorkspaceMember.user_id.in_(target_ids)
        ).all()
        valid_user_ids = {m.user_id for m in valid_members}
        
        # Also allow workspace owner
        if ws.owner_id in target_ids:
            valid_user_ids.add(ws.owner_id)

        invalid = [uid for uid in target_ids if uid not in valid_user_ids]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail="One or more assigned users are not members of this workspace"
            )

        assigned_users = db.query(User).filter(User.id.in_(target_ids)).all()

    primary_assignee = target_ids[0] if target_ids else None

    task = Task(
        title=body.title,
        description=body.description,
        priority=body.priority,
        workspace_id=body.workspace_id,
        created_by=current_user.id,
        assigned_to=primary_assignee,
        due_date=body.due_date
    )
    db.add(task)
    db.flush()

    # Create task_assignees records
    for uid in target_ids:
        db.add(TaskAssignee(task_id=task.id, user_id=uid))

    db.commit()
    db.refresh(task)

    assignee_emails = [u.email for u in assigned_users]

    # Email notifications if requested
    if body.notify_assignee:
        try:
            due_str = task.due_date.strftime('%b %d, %Y') if task.due_date else 'No deadline'
            desc_text = html.escape(task.description) if task.description else "No description provided."
            priority_val = task.priority.value if hasattr(task.priority, "value") else str(task.priority)

            def build_email_html(recipient_name: str, target_desc: str):
                return f"""
                <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;background:#0d0d15;color:#e6e6f0;border-radius:12px;overflow:hidden;border:1px solid #1e1e2e;padding:24px;">
                    <div style="margin-bottom:20px;display:flex;align-items:center;">
                        <span style="font-size:20px;font-weight:bold;color:#7fffb2;letter-spacing:-0.5px;">⚡ Orbit AI</span>
                        <span style="font-size:12px;color:#7a7a9a;margin-left:12px;background:#181826;padding:3px 8px;border-radius:6px;border:1px solid #242438;">Task Alert</span>
                    </div>
                    <h2 style="margin:0 0 12px 0;font-size:18px;color:#ffffff;">New Task Alert: {html.escape(task.title)}</h2>
                    <p style="color:#9a9ab0;font-size:14px;line-height:1.5;margin:0 0 16px 0;">
                        {desc_text}
                    </p>
                    <table style="width:100%;border-collapse:collapse;margin:16px 0;background:#131320;border-radius:8px;border:1px solid #1e1e2e;">
                        <tr>
                            <td style="padding:10px 14px;color:#7a7a9a;font-size:12px;border-bottom:1px solid #1e1e2e;">Workspace</td>
                            <td style="padding:10px 14px;color:#ffffff;font-size:13px;font-weight:600;border-bottom:1px solid #1e1e2e;">{html.escape(ws.name)}</td>
                        </tr>
                        <tr>
                            <td style="padding:10px 14px;color:#7a7a9a;font-size:12px;border-bottom:1px solid #1e1e2e;">Priority</td>
                            <td style="padding:10px 14px;color:#ffd166;font-size:13px;font-weight:600;border-bottom:1px solid #1e1e2e;text-transform:uppercase;">{priority_val}</td>
                        </tr>
                        <tr>
                            <td style="padding:10px 14px;color:#7a7a9a;font-size:12px;border-bottom:1px solid #1e1e2e;">Due Date</td>
                            <td style="padding:10px 14px;color:#ffffff;font-size:13px;border-bottom:1px solid #1e1e2e;">{due_str}</td>
                        </tr>
                        <tr>
                            <td style="padding:10px 14px;color:#7a7a9a;font-size:12px;">Assigned To</td>
                            <td style="padding:10px 14px;color:#7fffb2;font-size:13px;">{target_desc}</td>
                        </tr>
                    </table>
                    <div style="margin-top:24px;text-align:center;">
                        <a href="https://orbit-gamma-drab.vercel.app/dashboard/tasks" style="background:#7fffb2;color:#000000;text-decoration:none;padding:10px 22px;border-radius:8px;font-size:13px;font-weight:bold;display:inline-block;">View Task Board</a>
                    </div>
                </div>
                """

            if assigned_users:
                assignee_summary = ", ".join([u.email for u in assigned_users])
                for u in assigned_users:
                    email_body = build_email_html(u.email.split("@")[0], assignee_summary)
                    _send_email(u.email, f"📋 New Task Assigned: {task.title} — {ws.name}", email_body)
            else:
                members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == body.workspace_id).all()
                member_user_ids = [m.user_id for m in members]
                if member_user_ids:
                    users = db.query(User).filter(User.id.in_(member_user_ids)).all()
                    for u in users:
                        email_body = build_email_html(u.email.split("@")[0], "All Workspace Members")
                        _send_email(u.email, f"📋 New Task Alert: {task.title} — {ws.name}", email_body)
        except Exception as e:
            logger.error(f"Failed to send task assignment email: {e}")

    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value if hasattr(task.status, 'value') else task.status,
        priority=task.priority.value if hasattr(task.priority, 'value') else task.priority,
        workspace_id=task.workspace_id,
        created_by=task.created_by,
        assigned_to=primary_assignee,
        assignee_email=assignee_emails[0] if assignee_emails else None,
        assigned_to_ids=target_ids,
        assignee_emails=assignee_emails,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.get("/", response_model=list[TaskOut])
def fetch_tasks(
    workspace_id: str = Query(...),
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_member(workspace_id, str(current_user.id), db)

    tasks_query = db.query(Task).filter(
        Task.workspace_id == workspace_id
    )
    if status:
        tasks_query = tasks_query.filter(Task.status == status)

    tasks = tasks_query.order_by(Task.created_at.desc()).all()
    task_ids = [t.id for t in tasks]

    # Batch query task assignees
    task_assignee_records = db.query(TaskAssignee).filter(TaskAssignee.task_id.in_(task_ids)).all() if task_ids else []
    
    # Collect all user IDs involved (both from task_assignees and task.assigned_to)
    all_user_ids = set()
    for ta in task_assignee_records:
        all_user_ids.add(ta.user_id)
    for t in tasks:
        if t.assigned_to:
            all_user_ids.add(t.assigned_to)

    user_map = {}
    if all_user_ids:
        users = db.query(User).filter(User.id.in_(list(all_user_ids))).all()
        user_map = {u.id: u.email for u in users}

    # Group assignees by task_id
    task_assignees_map: dict[UUID, list[UUID]] = {}
    for ta in task_assignee_records:
        task_assignees_map.setdefault(ta.task_id, []).append(ta.user_id)

    result = []
    for t in tasks:
        assigned_uids = task_assignees_map.get(t.id, [])
        if not assigned_uids and t.assigned_to:
            assigned_uids = [t.assigned_to]

        emails = [user_map[uid] for uid in assigned_uids if uid in user_map]

        result.append(
            TaskOut(
                id=t.id,
                title=t.title,
                description=t.description,
                status=t.status.value if hasattr(t.status, 'value') else t.status,
                priority=t.priority.value if hasattr(t.priority, 'value') else t.priority,
                workspace_id=t.workspace_id,
                created_by=t.created_by,
                assigned_to=t.assigned_to,
                assignee_email=emails[0] if emails else None,
                assigned_to_ids=assigned_uids,
                assignee_emails=emails,
                due_date=t.due_date,
                created_at=t.created_at,
                updated_at=t.updated_at
            )
        )
    return result


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    body: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_member(str(task.workspace_id), str(current_user.id), db)

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.status is not None:
        task.status = body.status
    if body.priority is not None:
        task.priority = body.priority
    if body.due_date is not None:
        task.due_date = body.due_date

    # Multiple assignees update
    if body.assigned_to_ids is not None:
        # Clear existing assignees
        db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).delete()
        for uid in body.assigned_to_ids:
            db.add(TaskAssignee(task_id=task.id, user_id=uid))
        task.assigned_to = body.assigned_to_ids[0] if body.assigned_to_ids else None
    elif body.assigned_to is not None:
        task.assigned_to = body.assigned_to
        db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).delete()
        db.add(TaskAssignee(task_id=task.id, user_id=body.assigned_to))

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    # Fetch updated assignees
    task_assignees = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).all()
    assigned_uids = [ta.user_id for ta in task_assignees]
    if not assigned_uids and task.assigned_to:
        assigned_uids = [task.assigned_to]

    emails = []
    if assigned_uids:
        users = db.query(User).filter(User.id.in_(assigned_uids)).all()
        emails = [u.email for u in users]

    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value if hasattr(task.status, 'value') else task.status,
        priority=task.priority.value if hasattr(task.priority, 'value') else task.priority,
        workspace_id=task.workspace_id,
        created_by=task.created_by,
        assigned_to=task.assigned_to,
        assignee_email=emails[0] if emails else None,
        assigned_to_ids=assigned_uids,
        assignee_emails=emails,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    ws, member = check_workspace_member(str(task.workspace_id), str(current_user.id), db)

    is_admin = (str(ws.owner_id) == str(current_user.id)) or (
        member.role == RoleEnum.admin or
        (hasattr(member.role, "value") and member.role.value == "admin") or
        str(member.role).lower() == "admin"
    )

    if str(task.created_by) != str(current_user.id) and not is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to delete this task")

    db.delete(task)
    db.commit()

