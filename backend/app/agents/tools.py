from langchain.tools import tool
from app.rag.vector_store import search_similar
from app.database import SessionLocal
from app.models import Task, WorkspaceMember, Document, User, RoleEnum,Workspace
from app.utils.supabase_client import supabase
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import json
import html
import logging

logger = logging.getLogger(__name__)


@tool
def search_workspace(query: str, workspace_id: str) -> str:
    """Search workspace documents and knowledge.

Use this whenever the user asks about:
- project details
- requirements
- decisions
- meetings
- documentation
- deadlines"""
    chunks = search_similar(workspace_id=workspace_id, query=query, limit=5)
    if not chunks:
        return "No relevant information found in workspace."
    return "\n\n".join(chunk["content"] for chunk in chunks)

@tool
def get_tasks(workspace_id: str, status: str = None) -> str:
    """Retrieve workspace tasks.

Use this whenever the user asks:
- what tasks exist
- pending tasks
- completed tasks
- task status
- assigned work
"""
    db = SessionLocal()
    try:
        query = db.query(Task).filter(Task.workspace_id == workspace_id)
        if status:
            query = query.filter(Task.status == status)
        tasks = query.all()
        if not tasks:
            return "No tasks found."
        return json.dumps([{
            "id": str(t.id),
            "title": t.title,
            "status": t.status.value if hasattr(t.status, 'value') else t.status,
            "priority": t.priority.value if hasattr(t.priority, 'value') else t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "assigned_to": str(t.assigned_to) if t.assigned_to else None,
        } for t in tasks], indent=2)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def create_task(
    workspace_id: str,
    created_by: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: str = None,
    is_admin: bool = False
) -> str:
    """
    Create a new task. ONLY callable if is_admin=True.
    priority: low, medium, high
    due_date: ISO format string e.g. 2026-05-20
    """
    if not is_admin:
        return "Permission denied: Only workspace admins can create tasks."

    db = SessionLocal()
    try:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            workspace_id=workspace_id,
            created_by=created_by,
            status="todo",
            due_date=datetime.fromisoformat(due_date) if due_date else None
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return f"Task created: '{title}' | Priority: {priority} | Due: {due_date or 'not set'}"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def update_task(
    task_id: str,
    status: str = None,
    priority: str = None,
    title: str = None,
    is_admin: bool = False
) -> str:
    """
    Update a task's status, priority or title. ONLY callable if is_admin=True.
    status: todo, in_progress, done
    """
    if not is_admin:
        return "Permission denied: Only workspace admins can update tasks."

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return f"Task {task_id} not found."
        if status:
            task.status = status
        if priority:
            task.priority = priority
        if title:
            task.title = title
        task.updated_at = datetime.utcnow()
        db.commit()
        return f" Task '{task.title}' updated successfully."
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()



def _send_email(to: str, subject: str, body: str) -> bool:
    """Internal email sender using SMTP."""
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        if not smtp_user or not smtp_pass:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


@tool
def send_task_reminder_email(
    workspace_id: str,
    is_admin: bool = False
) -> str:
    """
    Send reminder emails to all members about their pending tasks.
    ONLY callable if is_admin=True.
    """
    if not is_admin:
        return "Permission denied: Only workspace admins can send emails."

    db = SessionLocal()
    try:
       
        members = db.query(WorkspaceMember).filter(
           WorkspaceMember.workspace_id == workspace_id
        ).all()
        # print(members)
        sent_count = 0
        for member in members:
            user = db.query(User).filter(User.id == member.user_id).first()
            if not user:
                continue

            tasks = db.query(Task).filter(
                Task.workspace_id == workspace_id,
                Task.status != "done"
            ).all()

            if not tasks:
                continue

            task_rows = "".join([
                f"""<tr>
                    <td style="padding:8px;border:1px solid #ddd">{html.escape(t.title)}</td>
                    <td style="padding:8px;border:1px solid #ddd">{html.escape(str(t.status))}</td>
                    <td style="padding:8px;border:1px solid #ddd">{html.escape(str(t.priority))}</td>
                    <td style="padding:8px;border:1px solid #ddd">{t.due_date.strftime('%b %d') if t.due_date else 'No deadline'}</td>
                </tr>"""
                for t in tasks
            ])

            body = f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
                <h2 style="color:#7fffb2">Orbit — Task Reminder</h2>
                <p>Hi {user.email.split('@')[0]},</p>
                <p>You have <strong>{len(tasks)} pending task(s)</strong> in your workspace:</p>
                <table style="border-collapse:collapse;width:100%">
                    <tr style="background:#f5f5f5">
                        <th style="padding:8px;border:1px solid #ddd;text-align:left">Task</th>
                        <th style="padding:8px;border:1px solid #ddd;text-align:left">Status</th>
                        <th style="padding:8px;border:1px solid #ddd;text-align:left">Priority</th>
                        <th style="padding:8px;border:1px solid #ddd;text-align:left">Due</th>
                    </tr>
                    {task_rows}
                </table>
                <p style="margin-top:20px">Log in to <a href="https://orbit-gamma-drab.vercel.app">Orbit AI</a> to update your tasks.</p>
            </div>
            """

            if _send_email(user.email, "📋 Your Pending Tasks — Orbit AI", body):
                sent_count += 1

        return f"Sent reminder emails to {sent_count} workspace members."
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def send_deadline_alert_email(
    workspace_id: str,
    is_admin: bool = False
) -> str:
    """
    Send deadline alert emails for tasks due in the next 2 days.
    ONLY callable if is_admin=True.
    """
    if not is_admin:
        return "Permission denied: Only workspace admins can send emails."

    db = SessionLocal()
    try:
        two_days = datetime.utcnow() + timedelta(days=2)
        overdue_tasks = db.query(Task).filter(
            Task.workspace_id == workspace_id,
            Task.due_date <= two_days,
            Task.status != "done"
        ).all()

        if not overdue_tasks:
            return "No tasks with upcoming deadlines found."

        # Group by assignee
        by_user = {}
        for task in overdue_tasks:
            key = str(task.assigned_to) if task.assigned_to else "unassigned"
            if key not in by_user:
                by_user[key] = []
            by_user[key].append(task)

        sent_count = 0
        for user_id, tasks in by_user.items():
            if user_id == "unassigned":
                continue
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                continue

            overdue = [t for t in tasks if t.due_date and t.due_date < datetime.utcnow()]
            upcoming = [t for t in tasks if t.due_date and t.due_date >= datetime.utcnow()]

            body = f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
                <h2 style="color:#ff6b6b">⚠️ Orbit AI — Deadline Alert</h2>
                <p>Hi {html.escape(user.email.split('@')[0])},</p>
                {"<h3 style='color:red'>🔴 Overdue Tasks</h3><ul>" + "".join(f"<li><strong>{html.escape(t.title)}</strong> — was due {t.due_date.strftime('%b %d')}</li>" for t in overdue) + "</ul>" if overdue else ""}
                {"<h3 style='color:orange'>🟡 Due Soon (next 2 days)</h3><ul>" + "".join(f"<li><strong>{html.escape(t.title)}</strong> — due {t.due_date.strftime('%b %d')}</li>" for t in upcoming) + "</ul>" if upcoming else ""}
                <p>Log in to <a href="https://orbit-gamma-drab.vercel.app">Orbit AI</a> to update your tasks.</p>
            </div>
            """

            if _send_email(user.email, "⚠️ Task Deadline Alert — Orbit AI", body):
                sent_count += 1

        return f"Sent deadline alerts to {sent_count} members."
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def send_important_info_email(
    workspace_id: str,
    content:str,
    is_admin: bool = False
    
) -> str:
    """
    Send important information or meeting details to all workspace members.
    ONLY callable if is_admin=True.
    Provide the exact content/message to be sent in the content argument.
    """
    if not is_admin:
        return "Permission denied: Only workspace admins can send emails."
    
    db = SessionLocal()
    try:
      
        members = db.query(WorkspaceMember).filter(
           WorkspaceMember.workspace_id == workspace_id
        ).all()
        Wsp=db.query(Workspace).filter(
            Workspace.id==workspace_id
        ).first()
        if not Wsp:
            return "Workspace not found."
   
        sent_count = 0
        for member in members:
            user = db.query(User).filter(User.id == member.user_id).first()
            if not user:
                continue

            body = f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
                <h2 style="color:#7fffb2">Orbit AI — Important Update</h2>
                <p>Hi {html.escape(user.email.split('@')[0])},</p>
                <p>You have an important message from workspace <strong>{html.escape(Wsp.name)}</strong>:</p>
                <div style="background:#f9f9f9;border-left:4px solid #7fffb2;padding:16px;margin:16px 0;border-radius:4px">
                    <p style="margin:0;font-size:16px;color:#333">{html.escape(content)}</p>
                </div>
                <p style="color:#888;font-size:12px">
                    Log in to <a href="https://orbit-gamma-drab.vercel.app">Orbit AI</a> for more details.
                </p>
            </div>
            """

            if _send_email(user.email, f"📢 Important Update — {Wsp.name}", body):
                sent_count += 1

        return f"Sent emails to {sent_count} workspace members."
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def get_recent_chat(workspace_id: str, limit: int = 20) -> str:
    """Get recent chat messages from the workspace."""
    result = supabase.table("messages")\
        .select("*")\
        .eq("workspace_id", workspace_id)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()

    if not result.data:
        return "No recent messages."

    messages = list(reversed(result.data))
    return "\n".join([
        f"{m['sender_email']}: {m['content']}"
        for m in messages
    ])

