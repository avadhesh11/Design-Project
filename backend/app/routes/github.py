from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, UTC, timedelta
from typing import Optional
from uuid import UUID
import os
import json
import logging

from ..database import get_db
from ..models import (
    User,
    WorkspaceMember,
    GitHubConnection,
    GitHubRepository,
    GitHubEvent,
    GitHubPullRequest,
    GitHubCommit,
    TaskGitHubLink,
    Task,
    TaskStatus,
    UserActivityState,
    InstallationLifecycleEvent
)
from ..schemas import (
    GitHubConnectionOut,
    GitHubRepositoryOut,
    GitHubRepositoryToggle,
    GitHubPullRequestOut,
    GitHubCommitOut,
    TaskGitHubLinkOut,
    SinceYouWereAwayOut
)
from ..dependencies import get_current_user
from ..services.github_app import (
    verify_webhook_signature,
    list_app_installations,
    list_installation_repositories,
    get_installation_access_token,
    fetch_repository_commits,
    fetch_repository_pull_requests
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..utils.development_cache import development_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["github"])



def check_workspace_membership(workspace_id: str, user_id: str, db: Session):
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return member


# --- GitHub App Installation & Connection ---

@router.get("/integrations/github/install-url")
def get_github_install_url():
    app_slug = os.getenv("GITHUB_APP_SLUG", "orbit-ai-workspace")
    return {
        "install_url": f"https://github.com/apps/{app_slug}/installations/new"
    }


@router.get("/integrations/github/status")
async def get_github_status(
    workspace_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    connection = None
    if workspace_id:
        connection = db.query(GitHubConnection).filter(
            GitHubConnection.workspace_id == workspace_id,
            GitHubConnection.status == "active"
        ).first()

    if not connection:
        connection = db.query(GitHubConnection).filter(
            GitHubConnection.user_id == current_user.id,
            GitHubConnection.status == "active"
        ).first()
        if connection and workspace_id:
            connection.workspace_id = workspace_id
            db.commit()
            db.refresh(connection)

    # Auto-heal: If no connection, check GitHub App installations
    if not connection:
        try:
            installations = await list_app_installations()
            if installations:
                first_inst = installations[0]
                real_inst_id = str(first_inst["id"])
                account_login = first_inst.get("account", {}).get("login")
                
                connection = GitHubConnection(
                    user_id=current_user.id,
                    workspace_id=workspace_id,
                    installation_id=real_inst_id,
                    github_login=account_login,
                    status="active"
                )
                db.add(connection)
                db.commit()
                db.refresh(connection)
        except Exception as e:
            logger.warning("Could not auto-sync installations in get_github_status: %s", e)


    if not connection:
        return {
            "connected": False,
            "status": "disconnected",
            "connection": None,
            "repositories_count": 0
        }

    repos_count = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == workspace_id if workspace_id else GitHubRepository.installation_id == connection.installation_id,
        GitHubRepository.is_active == True
    ).count()

    return {
        "connected": connection.status == "active",
        "status": connection.status,
        "connection": connection,
        "repositories_count": repos_count
    }


@router.post("/integrations/github/connect", response_model=GitHubConnectionOut)
def connect_github_installation(
    installation_id: str,
    workspace_id: Optional[str] = None,
    github_login: Optional[str] = None,
    github_user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if workspace_id:
        check_workspace_membership(workspace_id, str(current_user.id), db)

    conn = db.query(GitHubConnection).filter(
        GitHubConnection.installation_id == installation_id
    ).first()

    if not conn:
        conn = GitHubConnection(
            user_id=current_user.id,
            workspace_id=workspace_id,
            installation_id=installation_id,
            github_login=github_login,
            github_user_id=github_user_id,
            status="active"
        )
        db.add(conn)
    else:
        conn.user_id = current_user.id
        conn.status = "active"
        if workspace_id:
            conn.workspace_id = workspace_id
        if github_login:
            conn.github_login = github_login
        if github_user_id:
            conn.github_user_id = github_user_id

    db.commit()
    db.refresh(conn)
    return conn


@router.get("/integrations/github/repositories", response_model=list[GitHubRepositoryOut])
async def get_repositories(
    workspace_id: str,
    sync: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_membership(workspace_id, str(current_user.id), db)
    if sync:
        try:
            return await sync_repositories(workspace_id, db, current_user)
        except Exception as e:
            logger.warning("Sync error in get_repositories: %s", e)

    repos = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == workspace_id
    ).all()
    if not repos:
        try:
            return await sync_repositories(workspace_id, db, current_user)
        except Exception as e:
            logger.warning("Auto-sync fallback in get_repositories: %s", e)
    return repos



@router.post("/integrations/github/repositories/sync", response_model=list[GitHubRepositoryOut])
async def sync_repositories(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_membership(workspace_id, str(current_user.id), db)
    connection = db.query(GitHubConnection).filter(
        GitHubConnection.workspace_id == workspace_id,
        GitHubConnection.status == "active"
    ).first()

    if not connection:
        connection = db.query(GitHubConnection).filter(
            GitHubConnection.user_id == current_user.id,
            GitHubConnection.status == "active"
        ).first()
        if connection:
            connection.workspace_id = workspace_id
            db.commit()
            db.refresh(connection)

    if not connection:
        try:
            installations = await list_app_installations()
            if installations:
                first_inst = installations[0]
                real_inst_id = str(first_inst["id"])
                connection = GitHubConnection(
                    user_id=current_user.id,
                    workspace_id=workspace_id,
                    installation_id=real_inst_id,
                    github_login=first_inst.get("account", {}).get("login"),
                    status="active"
                )
                db.add(connection)
                db.commit()
                db.refresh(connection)
        except Exception as e:
            logger.warning("Installation auto-discovery error: %s", e)

    if not connection:
        raise HTTPException(status_code=400, detail="No active GitHub App connection for this workspace")


    remote_repos = []
    try:
        remote_repos = await list_installation_repositories(connection.installation_id)
    except Exception as api_err:
        logger.warning("Could not fetch repositories via GitHub API (%s), checking received webhook payloads...", api_err)
        # Fallback: scan GitHubEvent records for installation payloads
        events = db.query(GitHubEvent).filter(
            GitHubEvent.event_type.in_(["installation", "installation_repositories"])
        ).order_by(GitHubEvent.occurred_at.desc()).all()

        for ev in events:
            payload = ev.payload_json
            inst = payload.get("installation", {})
            if str(inst.get("id")) == str(connection.installation_id):
                repos_in_payload = payload.get("repositories", []) or payload.get("repositories_added", [])
                for rp in repos_in_payload:
                    full_name = rp.get("full_name", "")
                    owner_login = full_name.split("/")[0] if "/" in full_name else (payload.get("sender", {}).get("login", "") or "unknown")
                    remote_repos.append({
                        "id": rp.get("id"),
                        "owner": {"login": owner_login},
                        "name": rp.get("name"),
                        "full_name": full_name or f"{owner_login}/{rp.get('name')}",
                        "private": rp.get("private", False),
                        "default_branch": "main"
                    })
                if remote_repos:
                    break

    # If remote repos were discovered, prune any repos in DB that are no longer accessible
    if remote_repos:
        remote_repo_ids = {str(repo_data["id"]) for repo_data in remote_repos}
        stale_repos = db.query(GitHubRepository).filter(
            GitHubRepository.workspace_id == workspace_id,
            ~GitHubRepository.github_repo_id.in_(remote_repo_ids)
        ).all()
        for stale in stale_repos:
            db.query(GitHubCommit).filter(GitHubCommit.repository_id == stale.id).delete(synchronize_session=False)
            db.query(GitHubPullRequest).filter(GitHubPullRequest.repository_id == stale.id).delete(synchronize_session=False)
            db.delete(stale)
        db.commit()

    synced_repos = []
    for repo_data in remote_repos:
        repo_id_str = str(repo_data["id"])
        existing = db.query(GitHubRepository).filter(
            GitHubRepository.workspace_id == workspace_id,
            GitHubRepository.github_repo_id == repo_id_str
        ).first()

        if not existing:
            new_repo = GitHubRepository(
                workspace_id=workspace_id,
                github_repo_id=repo_id_str,
                owner_login=repo_data["owner"]["login"],
                name=repo_data["name"],
                full_name=repo_data["full_name"],
                is_private=repo_data.get("private", False),
                default_branch=repo_data.get("default_branch", "main"),
                installation_id=connection.installation_id,
                is_active=True
            )
            db.add(new_repo)
            synced_repos.append(new_repo)
        else:
            existing.owner_login = repo_data["owner"]["login"]
            existing.name = repo_data["name"]
            existing.full_name = repo_data["full_name"]
            existing.default_branch = repo_data.get("default_branch", "main")
            existing.installation_id = connection.installation_id
            synced_repos.append(existing)

    db.commit()
    for r in synced_repos:
        db.refresh(r)
        if r.is_active:
            await sync_repository_activity(r, db)

    return synced_repos



@router.post("/integrations/github/repositories/toggle", response_model=GitHubRepositoryOut)
async def toggle_repository_sync(
    body: GitHubRepositoryToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = db.query(GitHubRepository).filter(GitHubRepository.id == body.repository_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    check_workspace_membership(str(repo.workspace_id), str(current_user.id), db)
    repo.is_active = body.is_active
    db.commit()
    db.refresh(repo)

    if repo.is_active:
        await sync_repository_activity(repo, db)

    return repo


async def sync_repository_activity(repo: GitHubRepository, db: Session):

    """Fetch latest commits and pull requests directly from GitHub API for a repo."""
    if not repo.installation_id:
        return
    try:
        # 1. Fetch commits
        commits_data = await fetch_repository_commits(repo.installation_id, repo.owner_login, repo.name, per_page=30)
        for c in commits_data:
            sha = c.get("sha")
            if not sha:
                continue
            existing = db.query(GitHubCommit).filter(GitHubCommit.sha == sha).first()
            if not existing:
                commit_info = c.get("commit", {})
                author_info = c.get("author") or {}
                author_login = (
                    author_info.get("login")
                    or commit_info.get("author", {}).get("name")
                    or "developer"
                )
                author_id = str(author_info.get("id", ""))
                msg = commit_info.get("message", "")
                date_str = commit_info.get("author", {}).get("date")
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(UTC)

                new_commit = GitHubCommit(
                    sha=sha,
                    repository_id=repo.id,
                    author_github_id=author_id,
                    author_login=author_login,
                    message=msg,
                    branch=repo.default_branch or "main",
                    url=c.get("html_url"),
                    additions=0,
                    deletions=0,
                    committed_at=dt
                )
                db.add(new_commit)

        # 2. Fetch Pull Requests
        prs_data = await fetch_repository_pull_requests(repo.installation_id, repo.owner_login, repo.name, state="all", per_page=30)
        for p in prs_data:
            github_pr_id = str(p.get("id"))
            if not github_pr_id:
                continue
            existing_pr = db.query(GitHubPullRequest).filter(GitHubPullRequest.github_pr_id == github_pr_id).first()
            pr_state = "merged" if p.get("merged_at") else p.get("state", "open")
            merged_at = None
            if p.get("merged_at"):
                try:
                    merged_at = datetime.fromisoformat(p["merged_at"].replace("Z", "+00:00"))
                except Exception:
                    merged_at = None

            if not existing_pr:
                new_pr = GitHubPullRequest(
                    github_pr_id=github_pr_id,
                    pr_number=p.get("number"),
                    repository_id=repo.id,
                    author_github_id=str(p.get("user", {}).get("id", "")),
                    author_login=p.get("user", {}).get("login"),
                    title=p.get("title", ""),
                    body=p.get("body"),
                    state=pr_state,
                    head_branch=p.get("head", {}).get("ref"),
                    base_branch=p.get("base", {}).get("ref"),
                    merged_at=merged_at,
                    url=p.get("html_url", "")
                )
                db.add(new_pr)
                db.flush()
                match_pr_to_tasks(new_pr, repo.workspace_id, db)
            else:
                existing_pr.title = p.get("title", existing_pr.title)
                existing_pr.body = p.get("body", existing_pr.body)
                existing_pr.state = pr_state
                existing_pr.merged_at = merged_at
                match_pr_to_tasks(existing_pr, repo.workspace_id, db)

        db.commit()
    except Exception as e:
        logger.warning("Error syncing activity for repo %s: %s", repo.full_name, e)


@router.post("/integrations/github/sync-activity")
async def sync_github_activity(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_membership(workspace_id, str(current_user.id), db)
    repos = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == workspace_id,
        GitHubRepository.is_active == True
    ).all()

    for repo in repos:
        await sync_repository_activity(repo, db)

    return {"status": "ok", "synced_repositories": len(repos)}



# --- Webhook Gateway & Processor ---

def process_webhook_event(event_id: UUID, db: Session):
    event = db.query(GitHubEvent).filter(GitHubEvent.id == event_id).first()
    if not event:
        return

    payload = event.payload_json
    event_type = event.event_type

    try:
        # 1. Lifecycle Events
        if event_type.startswith("installation"):
            installation = payload.get("installation", {})
            inst_id = str(installation.get("id"))
            action = payload.get("action")

            lifecycle = InstallationLifecycleEvent(
                installation_id=inst_id,
                event_type=f"{event_type}.{action}",
                payload_json=payload,
                handled_at=datetime.now(UTC)
            )
            db.add(lifecycle)

            # Update connections
            if action == "suspend":
                db.query(GitHubConnection).filter(GitHubConnection.installation_id == inst_id).update({"status": "suspended"})
            elif action == "unsuspend":
                db.query(GitHubConnection).filter(GitHubConnection.installation_id == inst_id).update({"status": "active"})
            elif action == "deleted":
                db.query(GitHubConnection).filter(GitHubConnection.installation_id == inst_id).update({"status": "revoked"})
                db.query(GitHubRepository).filter(GitHubRepository.installation_id == inst_id).update({"is_active": False})

            db.commit()

        # 2. Pull Request Events
        elif event_type == "pull_request":
            pr_data = payload.get("pull_request", {})
            repo_data = payload.get("repository", {})
            repo_id_str = str(repo_data.get("id"))

            repo = db.query(GitHubRepository).filter(
                GitHubRepository.github_repo_id == repo_id_str,
                GitHubRepository.is_active == True
            ).first()

            if repo and pr_data:
                github_pr_id = str(pr_data.get("id"))
                existing_pr = db.query(GitHubPullRequest).filter(
                    GitHubPullRequest.github_pr_id == github_pr_id
                ).first()

                pr_state = "merged" if pr_data.get("merged") else pr_data.get("state", "open")
                merged_at = None
                if pr_data.get("merged_at"):
                    merged_at = datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00"))

                if not existing_pr:
                    new_pr = GitHubPullRequest(
                        github_pr_id=github_pr_id,
                        pr_number=pr_data.get("number"),
                        repository_id=repo.id,
                        author_github_id=str(pr_data.get("user", {}).get("id", "")),
                        author_login=pr_data.get("user", {}).get("login"),
                        title=pr_data.get("title", ""),
                        body=pr_data.get("body"),
                        state=pr_state,
                        head_branch=pr_data.get("head", {}).get("ref"),
                        base_branch=pr_data.get("base", {}).get("ref"),
                        merged_at=merged_at,
                        url=pr_data.get("html_url", "")
                    )
                    db.add(new_pr)
                    db.flush()
                    match_pr_to_tasks(new_pr, repo.workspace_id, db)
                else:
                    existing_pr.title = pr_data.get("title", existing_pr.title)
                    existing_pr.body = pr_data.get("body", existing_pr.body)
                    existing_pr.state = pr_state
                    existing_pr.merged_at = merged_at
                    match_pr_to_tasks(existing_pr, repo.workspace_id, db)

                db.commit()

        # 3. Push Events (Commits)
        elif event_type == "push":
            repo_data = payload.get("repository", {})
            repo_id_str = str(repo_data.get("id"))
            repo = db.query(GitHubRepository).filter(
                GitHubRepository.github_repo_id == repo_id_str,
                GitHubRepository.is_active == True
            ).first()

            if repo:
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
                for c in payload.get("commits", []):
                    sha = c.get("id")
                    if not sha:
                        continue
                    existing_commit = db.query(GitHubCommit).filter(GitHubCommit.sha == sha).first()
                    if not existing_commit:
                        timestamp_str = c.get("timestamp")
                        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else datetime.now(UTC)
                        new_commit = GitHubCommit(
                            sha=sha,
                            repository_id=repo.id,
                            author_github_id=str(c.get("author", {}).get("username", "")),
                            author_login=c.get("author", {}).get("name") or c.get("author", {}).get("username"),
                            message=c.get("message", ""),
                            branch=branch,
                            url=c.get("url"),
                            additions=len(c.get("added", [])),
                            deletions=len(c.get("removed", [])),
                            committed_at=dt
                        )
                        db.add(new_commit)

                db.commit()

        event.processing_status = "processed"
        event.processed_at = datetime.now(UTC)
        db.commit()

    except Exception as e:
        logger.error("Error processing webhook event %s: %s", event_id, e, exc_info=True)
        event.processing_status = "failed"
        db.commit()


def match_pr_to_tasks(pr: GitHubPullRequest, workspace_id: UUID, db: Session):
    """Correlate PR with workspace tasks using title, branch, and descriptions."""
    open_tasks = db.query(Task).filter(
        Task.workspace_id == workspace_id,
        Task.status.in_([TaskStatus.todo, TaskStatus.in_progress])
    ).all()

    pr_text = f"{pr.title} {pr.head_branch or ''} {pr.body or ''}".lower()

    for task in open_tasks:
        score = 0.0
        reason_parts = []
        task_title_words = set(task.title.lower().split())

        # Exact keywords overlap
        matched_words = [w for w in task_title_words if len(w) > 3 and w in pr_text]
        if matched_words:
            score += min(0.6, len(matched_words) * 0.2)
            reason_parts.append(f"Matched task keywords: {', '.join(matched_words)}")

        # Branch name signal
        if pr.head_branch and task.title.lower().replace(" ", "-") in pr.head_branch.lower():
            score += 0.4
            reason_parts.append("Branch name references task title")

        if score >= 0.4:
            # Check if link already exists
            existing_link = db.query(TaskGitHubLink).filter(
                TaskGitHubLink.task_id == task.id,
                TaskGitHubLink.pr_id == pr.id
            ).first()

            if not existing_link:
                link = TaskGitHubLink(
                    task_id=task.id,
                    pr_id=pr.id,
                    match_score=min(1.0, score),
                    match_reason="; ".join(reason_parts),
                    status="suggested"
                )
                db.add(link)


@router.post("/webhooks/github", status_code=202)
async def github_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_delivery: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    body_bytes = await request.body()

    if not verify_webhook_signature(body_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if not x_github_delivery or not x_github_event:
        raise HTTPException(status_code=400, detail="Missing delivery or event headers")

    # Idempotency check
    existing = db.query(GitHubEvent).filter(GitHubEvent.delivery_id == x_github_delivery).first()
    if existing:
        return {"status": "already_received", "delivery_id": x_github_delivery}

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload")

    repo_id = str(payload.get("repository", {}).get("id", "")) or None
    actor_id = str(payload.get("sender", {}).get("id", "")) or None

    event = GitHubEvent(
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        repository_id=repo_id,
        github_actor_id=actor_id,
        payload_json=payload,
        processing_status="pending"
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Process immediately in background
    background_tasks.add_task(process_webhook_event, event.id, db)

    return {"status": "accepted", "delivery_id": x_github_delivery}


# --- Timeline & Since You Were Away Intelligence ---

@router.get("/github/since-last-seen", response_model=SinceYouWereAwayOut)
async def get_since_you_were_away(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_membership(workspace_id, str(current_user.id), db)

    # Fetch user activity state
    act_state = db.query(UserActivityState).filter(
        UserActivityState.user_id == current_user.id
    ).first()

    now = datetime.now(UTC)
    if not act_state:
        since_time = now - timedelta(hours=24)
        act_state = UserActivityState(
            user_id=current_user.id,
            last_seen_at=now,
            previous_seen_at=since_time
        )
        db.add(act_state)
        db.commit()
    else:
        since_time = act_state.previous_seen_at or (now - timedelta(hours=24))

    # Get active repositories for this workspace
    active_repos = db.query(GitHubRepository).filter(
        GitHubRepository.workspace_id == workspace_id,
        GitHubRepository.is_active == True
    ).all()
    repo_ids = [r.id for r in active_repos]

    prs = db.query(GitHubPullRequest).filter(
        GitHubPullRequest.repository_id.in_(repo_ids),
        GitHubPullRequest.created_at >= since_time
    ).order_by(GitHubPullRequest.created_at.desc()).limit(15).all()

    commits = db.query(GitHubCommit).filter(
        GitHubCommit.repository_id.in_(repo_ids),
        GitHubCommit.committed_at >= since_time
    ).order_by(GitHubCommit.committed_at.desc()).limit(25).all()

    # If no PRs strictly since last seen, fallback to the latest PRs
    if not prs and repo_ids:
        prs = db.query(GitHubPullRequest).filter(
            GitHubPullRequest.repository_id.in_(repo_ids)
        ).order_by(GitHubPullRequest.created_at.desc()).limit(10).all()

    # If no commits strictly since last seen, fallback to the latest commits
    if not commits and repo_ids:
        commits = db.query(GitHubCommit).filter(
            GitHubCommit.repository_id.in_(repo_ids)
        ).order_by(GitHubCommit.committed_at.desc()).limit(25).all()

    summary = ""
    if prs or commits:
        # 1. Compute fingerprint of current developments (PRs + Commits)
        current_fingerprint = development_cache.compute_fingerprint(prs + commits)

        # 2. Check if cached summary exists for this exact set of developments
        cached_summary = development_cache.get_cached_response(workspace_id, current_fingerprint)
        if cached_summary:
            summary = cached_summary
        else:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    google_api_key=os.getenv("GEMINI_API_KEY"),
                    temperature=0.3
                )
                pr_bullets = "\n".join([f"- PR #{p.pr_number} '{p.title}' ({p.state}) by @{p.author_login}" for p in prs[:6]])
                commit_bullets = "\n".join([f"- Commit on '{c.branch}': {c.message.splitlines()[0]} by {c.author_login}" for c in commits[:8]])

                prompt = f"""You are Orbit Workspace Assistant. Synthesize a concise 1-2 sentence executive brief summarizing key recent repository developments.
Recent PRs:
{pr_bullets or 'None'}

Recent Commits:
{commit_bullets or 'None'}
"""
                res = await llm.ainvoke([SystemMessage(content="Be concise, professional and highlight key deliverables in 1-2 sentences."), HumanMessage(content=prompt)])
                raw_content = res.content
                if isinstance(raw_content, list):
                    summary = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content]).strip()
                else:
                    summary = str(raw_content or "").strip()

                if not summary:
                    summary = f"Recent repository activity: {len(prs)} pull request(s) and {len(commits)} commit(s) recorded across your monitored repositories."

                # Cache the fresh synthesis for this workspace
                development_cache.set_cached_response(workspace_id, current_fingerprint, summary)
            except Exception as e:
                logger.warning("Failed to generate AI summary for Since You Were Away: %s", e)
                summary = f"Recent repository activity: {len(prs)} pull request(s) and {len(commits)} commit(s) recorded across your monitored repositories."
    else:
        summary = "No repository activity recorded yet. Connect and sync your repositories to track commits and PRs."

    return {
        "workspace_id": workspace_id,
        "since": since_time,
        "until": now,
        "summary": summary,
        "pull_requests_count": len(prs),
        "commits_count": len(commits),
        "recent_pull_requests": prs,
        "recent_commits": commits
    }



# --- Task ↔ GitHub Suggestions Flow ---

@router.get("/tasks/{task_id}/github-links", response_model=list[TaskGitHubLinkOut])
def get_task_github_links(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_membership(str(task.workspace_id), str(current_user.id), db)
    links = db.query(TaskGitHubLink).filter(TaskGitHubLink.task_id == task_id).all()
    return links


@router.post("/tasks/{task_id}/suggestions/{suggestion_id}/accept")
def accept_task_suggestion(
    task_id: str,
    suggestion_id: str,
    mark_task_done: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_membership(str(task.workspace_id), str(current_user.id), db)
    link = db.query(TaskGitHubLink).filter(
        TaskGitHubLink.id == suggestion_id,
        TaskGitHubLink.task_id == task_id
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    link.status = "accepted"
    link.reviewed_at = datetime.now(UTC)

    if mark_task_done:
        task.status = TaskStatus.done
        task.updated_at = datetime.now(UTC)

    db.commit()
    return {"message": "Suggestion accepted", "task_status": task.status}


@router.post("/tasks/{task_id}/suggestions/{suggestion_id}/dismiss")
def dismiss_task_suggestion(
    task_id: str,
    suggestion_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_workspace_membership(str(task.workspace_id), str(current_user.id), db)
    link = db.query(TaskGitHubLink).filter(
        TaskGitHubLink.id == suggestion_id,
        TaskGitHubLink.task_id == task_id
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    link.status = "dismissed"
    link.reviewed_at = datetime.now(UTC)
    db.commit()
    return {"message": "Suggestion dismissed"}
