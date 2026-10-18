from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from uuid import UUID
import html
import logging
from ..database import get_db, engine, Base
from ..models import (
    User,
    Task,
    TaskAssignee,
    WorkspaceMember,
    Workspace,
    RoleEnum,
    TaskGitHubLink,
    GitHubCommit,
    GitHubPullRequest,
    GitHubRepository
)
from ..schemas import (
    TaskCreate,
    TaskUpdate,
    TaskOut,
    TaskLinkCommitIn,
    TaskCompleteIn,
    TaskGitHubLinkOut,
    GitHubCommitOut,
    GitHubPullRequestOut
)
from ..dependencies import get_current_user
from ..agents.tools import _send_email
from ..services.github_app import fetch_single_commit, fetch_repository_commits

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


def build_task_out(t: Task, assignee_emails: list[str], assigned_uids: list[UUID], db: Session) -> TaskOut:
    links = db.query(TaskGitHubLink).filter(TaskGitHubLink.task_id == t.id).all()
    primary_commit = None
    primary_pr = None
    links_out: list[TaskGitHubLinkOut] = []

    for l in links:
        commit_out = None
        pr_out = None
        if l.commit:
            commit_out = GitHubCommitOut.model_validate(l.commit)
            if not primary_commit and l.status in ("accepted", "linked", "suggested"):
                primary_commit = commit_out
        if l.pr:
            pr_out = GitHubPullRequestOut.model_validate(l.pr)
            if not primary_pr and l.status in ("accepted", "linked", "suggested"):
                primary_pr = pr_out

        links_out.append(
            TaskGitHubLinkOut(
                id=l.id,
                task_id=l.task_id,
                pr_id=l.pr_id,
                commit_id=l.commit_id,
                match_score=l.match_score,
                match_reason=l.match_reason,
                status=l.status,
                verification_status=l.verification_status or "linked",
                verification_source=l.verification_source or "local",
                verification_notes=l.verification_notes,
                created_at=l.created_at,
                reviewed_at=l.reviewed_at,
                commit=commit_out,
                pr=pr_out
            )
        )

    return TaskOut(
        id=t.id,
        title=t.title,
        description=t.description,
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        priority=t.priority.value if hasattr(t.priority, "value") else str(t.priority),
        task_type=t.task_type or "feature",
        requires_commit=bool(t.requires_commit),
        no_commit_reason=t.no_commit_reason,
        completion_notes=t.completion_notes,
        workspace_id=t.workspace_id,
        created_by=t.created_by,
        assigned_to=t.assigned_to,
        assignee_email=assignee_emails[0] if assignee_emails else None,
        assigned_to_ids=assigned_uids,
        assignee_emails=assignee_emails,
        due_date=t.due_date,
        created_at=t.created_at,
        updated_at=t.updated_at,
        github_links=links_out,
        primary_commit=primary_commit,
        primary_pr=primary_pr
    )


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
        valid_members = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == body.workspace_id,
            WorkspaceMember.user_id.in_(target_ids)
        ).all()
        valid_user_ids = {m.user_id for m in valid_members}
        
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
        priority=body.priority or "medium",
        task_type=body.task_type or "feature",
        requires_commit=bool(body.requires_commit),
        workspace_id=body.workspace_id,
        created_by=current_user.id,
        assigned_to=primary_assignee,
        due_date=body.due_date
    )
    db.add(task)
    db.flush()

    for uid in target_ids:
        db.add(TaskAssignee(task_id=task.id, user_id=uid))

    db.commit()
    db.refresh(task)

    assignee_emails = [u.email for u in assigned_users]

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
                    <p style="color:#9a9ab0;font-size:14px;line-height:1.5;margin:0 0 16px 0;">{desc_text}</p>
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

    return build_task_out(task, assignee_emails, target_ids, db)


@router.get("/", response_model=list[TaskOut])
def fetch_tasks(
    workspace_id: str = Query(...),
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_member(workspace_id, str(current_user.id), db)

    tasks_query = db.query(Task).filter(Task.workspace_id == workspace_id)
    if status:
        tasks_query = tasks_query.filter(Task.status == status)

    tasks = tasks_query.order_by(Task.created_at.desc()).all()
    task_ids = [t.id for t in tasks]

    task_assignee_records = db.query(TaskAssignee).filter(TaskAssignee.task_id.in_(task_ids)).all() if task_ids else []
    
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

    task_assignees_map: dict[UUID, list[UUID]] = {}
    for ta in task_assignee_records:
        task_assignees_map.setdefault(ta.task_id, []).append(ta.user_id)

    result = []
    for t in tasks:
        assigned_uids = task_assignees_map.get(t.id, [])
        if not assigned_uids and t.assigned_to:
            assigned_uids = [t.assigned_to]

        emails = [user_map[uid] for uid in assigned_uids if uid in user_map]
        result.append(build_task_out(t, emails, assigned_uids, db))

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

    # Optional enforcement check when transitioning to 'done'
    if body.status == "done" and task.requires_commit:
        has_linked_commit = db.query(TaskGitHubLink).filter(
            TaskGitHubLink.task_id == task.id,
            TaskGitHubLink.commit_id != None,
            TaskGitHubLink.status.in_(["accepted", "linked", "suggested"])
        ).count() > 0
        has_reason = bool(body.no_commit_reason or task.no_commit_reason)
        if not has_linked_commit and not has_reason:
            raise HTTPException(
                status_code=400,
                detail="This task requires commit evidence before completion. Please link a commit or provide an explanation."
            )

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
    if body.task_type is not None:
        task.task_type = body.task_type
    if body.requires_commit is not None:
        task.requires_commit = body.requires_commit
    if body.no_commit_reason is not None:
        task.no_commit_reason = body.no_commit_reason
    if body.completion_notes is not None:
        task.completion_notes = body.completion_notes

    if body.assigned_to_ids is not None:
        db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).delete()
        for uid in body.assigned_to_ids:
            db.add(TaskAssignee(task_id=task.id, user_id=uid))
        task.assigned_to = body.assigned_to_ids[0] if body.assigned_to_ids else None
    elif body.assigned_to is not None:
        task.assigned_to = body.assigned_to
        db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).delete()
        db.add(TaskAssignee(task_id=task.id, user_id=body.assigned_to))

    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)

    task_assignees = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).all()
    assigned_uids = [ta.user_id for ta in task_assignees]
    if not assigned_uids and task.assigned_to:
        assigned_uids = [task.assigned_to]

    emails = []
    if assigned_uids:
        users = db.query(User).filter(User.id.in_(assigned_uids)).all()
        emails = [u.email for u in users]

    return build_task_out(task, emails, assigned_uids, db)


# --- Commit-to-Task Linking & Verification Endpoints ---

@router.get("/workspace/{workspace_id}/repository-commits-and-prs")
async def get_workspace_repository_commits(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns commits and pull requests from active repositories connected to this workspace
    for easy selection and linking to tasks.
    """
    check_workspace_member(workspace_id, str(current_user.id), db)

    repos = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == workspace_id,
        GitHubRepository.is_active == True
    ).all()
    repo_ids = [r.id for r in repos]
    repo_map = {r.id: r.full_name or r.name for r in repos}

    # Fetch recorded commits from DB
    commits = db.query(GitHubCommit).filter(
        GitHubCommit.repository_id.in_(repo_ids)
    ).order_by(GitHubCommit.committed_at.desc()).limit(40).all() if repo_ids else []

    # Fetch recorded PRs from DB
    prs = db.query(GitHubPullRequest).filter(
        GitHubPullRequest.repository_id.in_(repo_ids)
    ).order_by(GitHubPullRequest.created_at.desc()).limit(20).all() if repo_ids else []

    commits_out = []
    for c in commits:
        c_dict = GitHubCommitOut.model_validate(c).model_dump()
        c_dict["repository_name"] = repo_map.get(c.repository_id, "Repository")
        commits_out.append(c_dict)

    prs_out = []
    for p in prs:
        p_dict = GitHubPullRequestOut.model_validate(p).model_dump()
        p_dict["repository_name"] = repo_map.get(p.repository_id, "Repository")
        prs_out.append(p_dict)

    return {
        "repositories": [{"id": str(r.id), "name": r.name, "full_name": r.full_name, "default_branch": r.default_branch} for r in repos],
        "commits": commits_out,
        "pull_requests": prs_out
    }


@router.post("/{task_id}/link-commit", response_model=TaskOut)
async def link_commit_to_task(
    task_id: str,
    body: TaskLinkCommitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Links a commit to a task. Validates commit SHA against connected GitHub repository
    when available, or checks local repository records. Records verification status.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_member(str(task.workspace_id), str(current_user.id), db)

    repos = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == task.workspace_id,
        GitHubRepository.is_active == True
    ).all()
    repo_ids = [r.id for r in repos]

    commit = None
    verification_status = "linked"
    verification_source = "local"
    verification_notes = body.verification_notes

    # 1. By commit_id
    if body.commit_id:
        commit = db.query(GitHubCommit).filter(GitHubCommit.id == body.commit_id).first()
        if not commit:
            raise HTTPException(status_code=404, detail="Selected commit not found in repository records")
        verification_status = "verified_in_repo"
        verification_source = "local_db"
        verification_notes = f"Commit [{commit.sha[:7]}] verified against local repository records."

    # 2. By commit_sha input
    elif body.commit_sha:
        sha_clean = body.commit_sha.strip().lower()
        if len(sha_clean) < 6 or not all(c in "0123456789abcdef" for c in sha_clean):
            raise HTTPException(status_code=400, detail="Invalid commit SHA format. Expected a 7-40 character hexadecimal hash.")

        # Check in local DB first
        commit = db.query(GitHubCommit).filter(
            GitHubCommit.sha.ilike(f"{sha_clean}%"),
            GitHubCommit.repository_id.in_(repo_ids) if repo_ids else True
        ).first()

        if commit:
            verification_status = "verified_in_repo"
            verification_source = "local_db"
            verification_notes = f"Commit [{commit.sha[:7]}] found and verified in connected repository."
        else:
            # Attempt live validation against connected GitHub repository API
            verified_on_github = False
            for repo in repos:
                if repo.installation_id:
                    try:
                        commit_data = await fetch_single_commit(
                            repo.installation_id,
                            repo.owner_login,
                            repo.name,
                            sha_clean
                        )
                        if commit_data and "sha" in commit_data:
                            full_sha = commit_data.get("sha", sha_clean)
                            commit_info = commit_data.get("commit", {})
                            author_info = commit_data.get("author") or {}
                            committer_info = commit_info.get("committer") or {}
                            date_str = committer_info.get("date")
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(UTC)

                            commit = GitHubCommit(
                                sha=full_sha,
                                repository_id=repo.id,
                                author_github_id=str(author_info.get("id")) if author_info.get("id") else None,
                                author_login=author_info.get("login") or committer_info.get("name") or "dev",
                                message=commit_info.get("message", "Commit linked to task"),
                                branch=repo.default_branch,
                                url=commit_data.get("html_url") or f"https://github.com/{repo.full_name}/commit/{full_sha}",
                                additions=commit_data.get("stats", {}).get("additions", 0),
                                deletions=commit_data.get("stats", {}).get("deletions", 0),
                                committed_at=dt
                            )
                            db.add(commit)
                            db.flush()
                            verified_on_github = True
                            verification_status = "verified_in_repo"
                            verification_source = "github_api"
                            verification_notes = f"Commit [{full_sha[:7]}] verified directly on GitHub repo '{repo.full_name}' via GitHub API."
                            break
                    except Exception as err:
                        logger.warning(f"Failed to check GitHub API for commit {sha_clean}: {err}")

            if not verified_on_github:
                # If repositories exist but commit wasn't found remotely, or API unavailable
                target_repo_id = repos[0].id if repos else None
                if target_repo_id:
                    commit = GitHubCommit(
                        sha=sha_clean,
                        repository_id=target_repo_id,
                        author_login=current_user.email.split("@")[0],
                        message=f"Manual commit evidence [{sha_clean[:7]}]",
                        branch="main",
                        url=f"https://github.com/{repos[0].full_name}/commit/{sha_clean}",
                        additions=0,
                        deletions=0,
                        committed_at=datetime.now(UTC)
                    )
                    db.add(commit)
                    db.flush()
                    verification_status = "manual_entry"
                    verification_source = "manual"
                    verification_notes = f"Commit SHA [{sha_clean[:7]}] recorded manually. Remote branch existence could not be confirmed via GitHub API."
                else:
                    raise HTTPException(status_code=400, detail="No connected GitHub repository in this workspace to link commit with.")
    else:
        raise HTTPException(status_code=400, detail="Must provide either commit_sha or commit_id to link")

    # Create or update link record
    existing_link = db.query(TaskGitHubLink).filter(
        TaskGitHubLink.task_id == task.id,
        TaskGitHubLink.commit_id == commit.id
    ).first()

    if not existing_link:
        new_link = TaskGitHubLink(
            task_id=task.id,
            commit_id=commit.id,
            pr_id=body.pr_id,
            match_score=1.0,
            match_reason="User linked commit as delivery evidence",
            status="accepted",
            verification_status=verification_status,
            verification_source=verification_source,
            verification_notes=verification_notes,
            reviewed_at=datetime.now(UTC)
        )
        db.add(new_link)
    else:
        existing_link.status = "accepted"
        existing_link.verification_status = verification_status
        existing_link.verification_source = verification_source
        existing_link.verification_notes = verification_notes
        existing_link.reviewed_at = datetime.now(UTC)

    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)

    task_assignees = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).all()
    assigned_uids = [ta.user_id for ta in task_assignees]
    if not assigned_uids and task.assigned_to:
        assigned_uids = [task.assigned_to]

    emails = []
    if assigned_uids:
        users = db.query(User).filter(User.id.in_(assigned_uids)).all()
        emails = [u.email for u in users]

    return build_task_out(task, emails, assigned_uids, db)


@router.delete("/{task_id}/links/{link_id}", status_code=200)
def unlink_commit_or_pr(
    task_id: str,
    link_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_member(str(task.workspace_id), str(current_user.id), db)

    link = db.query(TaskGitHubLink).filter(
        TaskGitHubLink.id == link_id,
        TaskGitHubLink.task_id == task_id
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    task.updated_at = datetime.now(UTC)
    db.commit()

    return {"message": "Link removed successfully"}


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task_with_evidence(
    task_id: str,
    body: TaskCompleteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transitions task to 'Done' with commit evidence or recorded explanation of why no commit applies.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_member(str(task.workspace_id), str(current_user.id), db)

    # 1. Link commit if provided
    if body.commit_sha or body.commit_id:
        link_in = TaskLinkCommitIn(
            commit_sha=body.commit_sha,
            commit_id=body.commit_id,
            verification_notes=body.completion_notes
        )
        await link_commit_to_task(task_id, link_in, db, current_user)

    # 2. Record explanation if provided
    if body.no_commit_reason:
        task.no_commit_reason = body.no_commit_reason

    if body.completion_notes:
        task.completion_notes = body.completion_notes

    # 3. Check commit enforcement
    has_commit = db.query(TaskGitHubLink).filter(
        TaskGitHubLink.task_id == task.id,
        TaskGitHubLink.commit_id != None,
        TaskGitHubLink.status.in_(["accepted", "linked"])
    ).count() > 0

    has_reason = bool(body.no_commit_reason or task.no_commit_reason)

    if task.requires_commit and not has_commit and not has_reason:
        raise HTTPException(
            status_code=400,
            detail="Commit evidence is enforced for this task type. Please link a commit or provide an explanation."
        )

    task.status = "done"
    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)

    task_assignees = db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).all()
    assigned_uids = [ta.user_id for ta in task_assignees]
    if not assigned_uids and task.assigned_to:
        assigned_uids = [task.assigned_to]

    emails = []
    if assigned_uids:
        users = db.query(User).filter(User.id.in_(assigned_uids)).all()
        emails = [u.email for u in users]

    return build_task_out(task, emails, assigned_uids, db)


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
