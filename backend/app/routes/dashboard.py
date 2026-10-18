from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime, UTC, timedelta
from typing import Optional
from uuid import UUID
import os
import json
import logging

from ..database import get_db
from ..models import (
    User,
    Workspace,
    WorkspaceMember,
    Task,
    TaskAssignee,
    Document,
    Flow,
    GitHubRepository,
    GitHubPullRequest,
    GitHubCommit,
    UserActivityState,
    TaskStatus,
)
from ..schemas import (
    WhenYouWereAwayResponse,
    WhenYouWereAwayStats,
    WhenYouWereAwayTask,
    WhenYouWereAwayGitHubPR,
    WhenYouWereAwayGitHubCommit,
    WhenYouWereAwayTeamActivity,
)
from ..dependencies import get_current_user
from ..utils.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def to_utc_dt(dt) -> datetime:
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


def check_workspace_membership(workspace_id: str, user_id: str, db: Session) -> tuple[Workspace, WorkspaceMember]:
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()

    if not member and str(ws.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not a workspace member")

    return ws, member


@router.post("/heartbeat")
def record_heartbeat(
    workspace_id: Optional[str] = None,
    reset_seen: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records or advances the user's active session timestamp.
    When reset_seen is True (e.g. user clicks 'Mark as caught up'),
    both last_seen_at and previous_seen_at are reset to now.
    """
    now = datetime.now(UTC)
    act_state = db.query(UserActivityState).filter(
        UserActivityState.user_id == current_user.id
    ).first()

    if not act_state:
        act_state = UserActivityState(
            user_id=current_user.id,
            last_seen_at=now,
            previous_seen_at=now,
            last_digest_at=now
        )
        db.add(act_state)
    else:
        act_state.previous_seen_at = now
        act_state.last_seen_at = now
        act_state.last_digest_at = now

    db.commit()
    db.refresh(act_state)

    return {
        "status": "recorded",
        "user_id": str(current_user.id),
        "last_seen_at": act_state.last_seen_at,
        "previous_seen_at": act_state.previous_seen_at
    }


@router.get("/when-you-were-away", response_model=WhenYouWereAwayResponse)
async def get_when_you_were_away(
    workspace_id: str = Query(...),
    time_window: str = Query("since_last_visit"),  # since_last_visit, 24h, 3d, 7d, 30d
    custom_since: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ws, _ = check_workspace_membership(workspace_id, str(current_user.id), db)
    now = datetime.now(UTC)

    # 1. Determine activity state and time window
    act_state = db.query(UserActivityState).filter(
        UserActivityState.user_id == current_user.id
    ).first()

    if not act_state:
        # Default initialization: 24h away prior to current visit
        prev_time = now - timedelta(hours=24)
        act_state = UserActivityState(
            user_id=current_user.id,
            last_seen_at=now,
            previous_seen_at=prev_time,
            last_digest_at=now
        )
        db.add(act_state)
        db.commit()
        db.refresh(act_state)

    # Calculate since_time based on selected time window
    if custom_since:
        since_time = to_utc_dt(custom_since)
        time_window_type = "custom"
        since_label = f"Since {since_time.strftime('%b %d, %Y %I:%M %p UTC')}"
    elif time_window == "24h":
        since_time = now - timedelta(hours=24)
        time_window_type = "24h"
        since_label = "Past 24 hours"
    elif time_window == "3d":
        since_time = now - timedelta(days=3)
        time_window_type = "3d"
        since_label = "Past 3 days"
    elif time_window == "7d":
        since_time = now - timedelta(days=7)
        time_window_type = "7d"
        since_label = "Past 7 days"
    elif time_window == "30d":
        since_time = now - timedelta(days=30)
        time_window_type = "30d"
        since_label = "Past 30 days"
    else:
        # Default: since_last_visit
        time_window_type = "since_last_visit"
        recorded_prev = act_state.previous_seen_at or act_state.last_seen_at
        if recorded_prev:
            since_time = to_utc_dt(recorded_prev)
        else:
            since_time = now - timedelta(hours=24)

        diff_seconds = max(0, int((now - since_time).total_seconds()))
        if diff_seconds < 60:
            since_label = f"Since your last visit just now ({since_time.strftime('%I:%M %p')})"
        elif diff_seconds < 3600:
            mins_ago = max(1, diff_seconds // 60)
            since_label = f"Since your last visit {mins_ago}m ago ({since_time.strftime('%I:%M %p')})"
        elif diff_seconds < 86400:
            hours_ago = max(1, diff_seconds // 3600)
            since_label = f"Since your last visit {hours_ago}h ago ({since_time.strftime('%I:%M %p')})"
        else:
            days_ago = max(1, diff_seconds // 86400)
            since_label = f"Since your last visit {days_ago}d ago ({since_time.strftime('%b %d, %I:%M %p')})"

    away_duration_seconds = max(0, int((now - since_time).total_seconds()))

    # Update last fetched time in the database so that subsequent visits/fetches measure from now
    act_state.previous_seen_at = now
    act_state.last_seen_at = now
    act_state.last_digest_at = now
    db.commit()

    # Convert to naive UTC for database comparisons where necessary
    since_naive = since_time.replace(tzinfo=None)
    now_naive = now.replace(tzinfo=None)

    # 2. Gather Users in Workspace for name mapping
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
    user_ids = {m.user_id for m in memberships}
    user_ids.add(ws.owner_id)
    user_ids.add(current_user.id)

    # 3. Tasks Data Gathering
    all_tasks = db.query(Task).filter(Task.workspace_id == workspace_id).all()
    for t in all_tasks:
        if t.created_by:
            user_ids.add(t.created_by)
        if t.assigned_to:
            user_ids.add(t.assigned_to)

    users_db = db.query(User).filter(User.id.in_(list(user_ids))).all() if user_ids else []
    user_email_map = {u.id: u.email for u in users_db}

    # Fetch multi-assignees
    task_ids = [t.id for t in all_tasks]
    assignee_records = db.query(TaskAssignee).filter(TaskAssignee.task_id.in_(task_ids)).all() if task_ids else []
    task_assignees_map: dict[str, list[str]] = {}
    for ta in assignee_records:
        tid = str(ta.task_id)
        task_assignees_map.setdefault(tid, []).append(str(ta.user_id))

    tasks_created_list: list[WhenYouWereAwayTask] = []
    tasks_updated_list: list[WhenYouWereAwayTask] = []
    tasks_assigned_to_user_list: list[WhenYouWereAwayTask] = []
    tasks_overdue_list: list[WhenYouWereAwayTask] = []
    tasks_approaching_list: list[WhenYouWereAwayTask] = []

    current_uid_str = str(current_user.id)

    for t in all_tasks:
        t_created = to_utc_dt(t.created_at)
        t_updated = to_utc_dt(t.updated_at or t.created_at)
        t_due = to_utc_dt(t.due_date) if t.due_date else None
        status_val = t.status.value if hasattr(t.status, "value") else str(t.status)
        priority_val = t.priority.value if hasattr(t.priority, "value") else str(t.priority)

        creator_email = user_email_map.get(t.created_by, "Team Member")
        primary_assigned_email = user_email_map.get(t.assigned_to) if t.assigned_to else None
        assigned_uids = task_assignees_map.get(str(t.id), [])
        if not assigned_uids and t.assigned_to:
            assigned_uids = [str(t.assigned_to)]

        is_assigned_to_me = current_uid_str in assigned_uids or str(t.assigned_to) == current_uid_str

        # Overdue check: due_date < now and status != done
        is_overdue = False
        is_approaching = False
        if t_due and status_val != "done":
            if t_due < now:
                is_overdue = True
            elif t_due <= now + timedelta(days=3):
                is_approaching = True

        # Created in window check
        is_new = t_created >= since_time

        # Status or content updated in window (not just initial creation)
        is_updated = (t_updated >= since_time) and not (is_new and abs((t_updated - t_created).total_seconds()) < 60)

        task_item = WhenYouWereAwayTask(
            id=str(t.id),
            title=t.title,
            description=t.description,
            status=status_val,
            priority=priority_val,
            creator_email=creator_email,
            assigned_to_email=primary_assigned_email,
            assigned_to_ids=assigned_uids,
            due_date=t_due,
            created_at=t_created,
            updated_at=t_updated,
            is_overdue=is_overdue,
            is_approaching=is_approaching,
            is_new=is_new,
            is_status_changed=is_updated,
            is_assigned_to_me=is_assigned_to_me,
            link="/dashboard/tasks"
        )

        if is_new:
            tasks_created_list.append(task_item)
        elif is_updated:
            tasks_updated_list.append(task_item)

        if is_assigned_to_me and (is_new or is_updated):
            tasks_assigned_to_user_list.append(task_item)

        if is_overdue:
            tasks_overdue_list.append(task_item)
        elif is_approaching:
            tasks_approaching_list.append(task_item)

    # Sort tasks
    tasks_created_list.sort(key=lambda x: x.created_at, reverse=True)
    tasks_updated_list.sort(key=lambda x: x.updated_at, reverse=True)
    tasks_overdue_list.sort(key=lambda x: x.due_date or x.created_at)
    tasks_approaching_list.sort(key=lambda x: x.due_date or x.created_at)

    # 4. GitHub PRs and Commits
    active_repos = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == workspace_id,
        GitHubRepository.is_active == True
    ).all()
    repo_ids = [r.id for r in active_repos]
    repo_name_map = {r.id: (r.full_name or r.name) for r in active_repos}

    github_prs_list: list[WhenYouWereAwayGitHubPR] = []
    github_commits_list: list[WhenYouWereAwayGitHubCommit] = []

    if repo_ids:
        # PRs created, updated, or merged since window start
        prs_query = db.query(GitHubPullRequest).filter(
            GitHubPullRequest.repository_id.in_(repo_ids),
            or_(
                GitHubPullRequest.created_at >= since_naive,
                GitHubPullRequest.updated_at >= since_naive,
                and_(GitHubPullRequest.merged_at != None, GitHubPullRequest.merged_at >= since_naive)
            )
        ).order_by(GitHubPullRequest.created_at.desc()).limit(20).all()

        for pr in prs_query:
            repo_name = repo_name_map.get(pr.repository_id, "Repository")
            pr_link = pr.url if pr.url else "/dashboard/integrations"
            github_prs_list.append(WhenYouWereAwayGitHubPR(
                id=str(pr.id),
                pr_number=pr.pr_number,
                title=pr.title,
                state=pr.state,
                author_login=pr.author_login,
                repository_name=repo_name,
                url=pr_link,
                merged_at=to_utc_dt(pr.merged_at) if pr.merged_at else None,
                created_at=to_utc_dt(pr.created_at),
                updated_at=to_utc_dt(pr.updated_at) if pr.updated_at else None,
                link=pr_link
            ))

        # Commits committed in window
        commits_query = db.query(GitHubCommit).filter(
            GitHubCommit.repository_id.in_(repo_ids),
            GitHubCommit.committed_at >= since_naive
        ).order_by(GitHubCommit.committed_at.desc()).limit(25).all()

        for cm in commits_query:
            repo_name = repo_name_map.get(cm.repository_id, "Repository")
            cm_link = cm.url if cm.url else "/dashboard/integrations"
            github_commits_list.append(WhenYouWereAwayGitHubCommit(
                id=str(cm.id),
                sha=cm.sha,
                message=cm.message.split("\n")[0][:100],
                author_login=cm.author_login,
                branch=cm.branch,
                url=cm_link,
                additions=cm.additions or 0,
                deletions=cm.deletions or 0,
                committed_at=to_utc_dt(cm.committed_at),
                repository_name=repo_name,
                link=cm_link
            ))

    # 5. Team Activity (Documents, Chat Conversations, Member joins, Flows)
    team_activities_list: list[WhenYouWereAwayTeamActivity] = []

    # Documents created or updated in window
    recent_docs = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        or_(Document.created_at >= since_naive, Document.updated_at >= since_naive)
    ).order_by(Document.updated_at.desc()).limit(15).all()

    for doc in recent_docs:
        doc_created = to_utc_dt(doc.created_at)
        doc_updated = to_utc_dt(doc.updated_at or doc.created_at)
        is_new_doc = abs((doc_updated - doc_created).total_seconds()) < 60
        author_email = user_email_map.get(doc.created_by, "Team member")
        author_name = author_email.split("@")[0] if author_email else "member"

        team_activities_list.append(WhenYouWereAwayTeamActivity(
            id=f"doc_{doc.id}",
            category="document",
            action="Created document" if is_new_doc else "Updated document",
            title=doc.title or "Untitled Document",
            description=f"{'Created' if is_new_doc else 'Updated'} by @{author_name}",
            actor_email=author_email,
            target_link=f"/dashboard/documents/{doc.id}",
            created_at=doc_updated
        ))

    # Realtime Chat (Strict permission: public messages or direct messages involving current user)
    try:
        chat_res = supabase.table("messages") \
            .select("*") \
            .eq("workspace_id", workspace_id) \
            .gte("created_at", since_time.isoformat()) \
            .or_(f"recipient_id.is.null,recipient_id.eq.{current_user.id},sender_id.eq.{current_user.id}") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()

        if chat_res.data:
            for msg in chat_res.data:
                rec_id = msg.get("recipient_id")
                is_dm = rec_id is not None
                sender_email = msg.get("sender_email", "Team member")
                sender_name = sender_email.split("@")[0] if sender_email else "member"

                if is_dm:
                    if str(msg.get("sender_id")) == str(current_user.id):
                        action_title = "Direct Message Sent"
                        title = "Sent direct message"
                    else:
                        action_title = "Direct Message Received"
                        title = f"Message from @{sender_name}"
                else:
                    action_title = "Workspace Chat"
                    title = f"Chat message from @{sender_name}"

                content_preview = msg.get("content", "")
                if len(content_preview) > 80:
                    content_preview = content_preview[:80] + "..."

                team_activities_list.append(WhenYouWereAwayTeamActivity(
                    id=f"msg_{msg.get('id')}",
                    category="chat",
                    action=action_title,
                    title=title,
                    description=content_preview,
                    actor_email=sender_email,
                    target_link="/dashboard/chat",
                    created_at=to_utc_dt(msg.get("created_at"))
                ))
    except Exception as e:
        logger.warning(f"When You Were Away: Failed to query chat messages from Supabase: {e}")

    # Members who joined in window
    recent_members = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.joined_at >= since_naive
    ).all()

    for m in recent_members:
        m_email = user_email_map.get(m.user_id, "New Member")
        m_role = m.role.value if hasattr(m.role, "value") else str(m.role)
        team_activities_list.append(WhenYouWereAwayTeamActivity(
            id=f"member_{m.id}",
            category="member",
            action="Joined workspace",
            title=f"@{m_email.split('@')[0]} joined",
            description=f"Assigned {m_role.upper()} role",
            actor_email=m_email,
            target_link="/dashboard/settings",
            created_at=to_utc_dt(m.joined_at)
        ))

    # Workflows / Flows created or updated in window
    recent_flows = db.query(Flow).filter(
        Flow.workspace_id == workspace_id,
        or_(Flow.created_at >= since_naive, Flow.updated_at >= since_naive)
    ).all()

    for fl in recent_flows:
        fl_time = to_utc_dt(fl.updated_at or fl.created_at)
        team_activities_list.append(WhenYouWereAwayTeamActivity(
            id=f"flow_{fl.id}",
            category="workflow",
            action="Workflow updated",
            title=fl.title,
            description=fl.description or "Flow diagram modified",
            actor_email=user_email_map.get(fl.created_by, "Team member"),
            target_link="/dashboard/flows",
            created_at=fl_time
        ))

    team_activities_list.sort(key=lambda x: x.created_at, reverse=True)

    # 6. Calculate Stats
    doc_count = sum(1 for a in team_activities_list if a.category == "document")
    chat_count = sum(1 for a in team_activities_list if a.category == "chat")
    member_count = sum(1 for a in team_activities_list if a.category == "member")

    total_events_count = (
        len(tasks_created_list)
        + len(tasks_updated_list)
        + len(tasks_overdue_list)
        + len(tasks_approaching_list)
        + len(github_prs_list)
        + len(github_commits_list)
        + len(team_activities_list)
    )

    stats = WhenYouWereAwayStats(
        tasks_created_count=len(tasks_created_list),
        tasks_updated_count=len(tasks_updated_list),
        tasks_assigned_to_user_count=len(tasks_assigned_to_user_list),
        tasks_overdue_count=len(tasks_overdue_list),
        tasks_approaching_count=len(tasks_approaching_list),
        github_commits_count=len(github_commits_list),
        github_prs_count=len(github_prs_list),
        team_docs_count=doc_count,
        team_chats_count=chat_count,
        team_members_count=member_count,
        total_events_count=total_events_count
    )

    has_events = total_events_count > 0

    # 7. Executive Summary (Use ONLY actual recorded events; NO fabricated data!)
    if not has_events:
        summary = f"No new changes or team activity were recorded in this workspace {since_label.lower()}. Everything is up to date."
    else:
        # Build factual summary using workspace preferred LLM (Gemini or Local Ollama/Llama)
        summary = None
        try:
            from ..utils.llm_factory import get_chat_llm
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = get_chat_llm(workspace=ws, temperature=0.2)

                # Format actual factual bullets strictly from verified lists
                task_bullets = []
                for t in tasks_created_list[:5]:
                    task_bullets.append(f"- Created task '{t.title}' [{t.priority.upper()}] by @{t.creator_email.split('@')[0] if t.creator_email else 'member'}")
                for t in tasks_updated_list[:5]:
                    task_bullets.append(f"- Updated task '{t.title}' (Status: {t.status.upper()})")

                deadline_bullets = []
                for t in tasks_overdue_list[:4]:
                    deadline_bullets.append(f"- OVERDUE: Task '{t.title}' was due on {t.due_date.strftime('%b %d') if t.due_date else 'unknown'}")
                for t in tasks_approaching_list[:4]:
                    deadline_bullets.append(f"- Approaching Deadline: Task '{t.title}' due {t.due_date.strftime('%b %d') if t.due_date else 'soon'}")

                pr_bullets = []
                for p in github_prs_list[:5]:
                    pr_bullets.append(f"- PR #{p.pr_number} '{p.title}' ({p.state.upper()}) on {p.repository_name}")

                commit_bullets = []
                for c in github_commits_list[:6]:
                    commit_bullets.append(f"- Commit on '{c.branch}': {c.message} by @{c.author_login or 'dev'}")

                team_bullets = []
                for a in team_activities_list[:5]:
                    team_bullets.append(f"- {a.action}: '{a.title}' ({a.description or ''})")

                prompt = f"""You are the Orbit Executive Assistant. Summarize ONLY the following factual recorded events that occurred in this workspace during the window: {since_label}.
CRITICAL CONSTRAINT: You must ONLY refer to items explicitly provided below. Do not fabricate, assume, or invent updates. If a category is empty, ignore it.
Highlight key tasks, urgent deadlines, pull requests/commits, and team interactions in 2-3 crisp, professional executive sentences.

Tasks:
{chr(10).join(task_bullets) if task_bullets else 'No new task changes.'}

Deadlines:
{chr(10).join(deadline_bullets) if deadline_bullets else 'No overdue or approaching deadlines.'}

GitHub Pull Requests:
{chr(10).join(pr_bullets) if pr_bullets else 'No repository pull requests.'}

GitHub Commits:
{chr(10).join(commit_bullets) if commit_bullets else 'No commits pushed.'}

Team Activity:
{chr(10).join(team_bullets) if team_bullets else 'No document or chat updates.'}
"""
                res = await llm.ainvoke([
                    SystemMessage(content="You are an accurate workspace intelligence reporter. Keep it factual, concise, and under 3 sentences."),
                    HumanMessage(content=prompt)
                ])

                raw = res.content
                if isinstance(raw, list):
                    summary = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in raw]).strip()
                else:
                    summary = str(raw or "").strip()
            except Exception as e:
                logger.warning(f"When You Were Away: LLM synthesis error: {e}")

        # Deterministic factual fallback if LLM is unavailable or fails
        if not summary:
            parts = []
            if tasks_created_list:
                parts.append(f"{len(tasks_created_list)} task(s) created")
            if tasks_updated_list:
                parts.append(f"{len(tasks_updated_list)} task status update(s)")
            if tasks_overdue_list:
                parts.append(f"{len(tasks_overdue_list)} overdue task(s)")
            if tasks_approaching_list:
                parts.append(f"{len(tasks_approaching_list)} approaching deadline(s)")
            if github_prs_list:
                parts.append(f"{len(github_prs_list)} pull request(s) active")
            if github_commits_list:
                parts.append(f"{len(github_commits_list)} commit(s) pushed")
            if team_activities_list:
                parts.append(f"{len(team_activities_list)} team activity item(s)")

            summary = f"Developments {since_label.lower()}: " + ", ".join(parts) + "."

    return WhenYouWereAwayResponse(
        workspace_id=ws.id,
        time_window_type=time_window_type,
        since=since_time,
        until=now,
        since_label=since_label,
        away_duration_seconds=away_duration_seconds,
        has_events=has_events,
        summary=summary,
        stats=stats,
        tasks_created=tasks_created_list,
        tasks_updated=tasks_updated_list,
        tasks_assigned_to_user=tasks_assigned_to_user_list,
        tasks_overdue=tasks_overdue_list,
        tasks_approaching=tasks_approaching_list,
        github_prs=github_prs_list,
        github_commits=github_commits_list,
        team_activities=team_activities_list,
        last_fetched_at=now
    )
