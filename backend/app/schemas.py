from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
# --- Auth schemas (already exist) ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str

    class Config:
        from_attributes = True

# --- Workspace schemas ---

class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class WorkspaceMemberOut(BaseModel):
    user_id: UUID
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True

class WorkspaceMemberDetailOut(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True

class WorkspaceMemberRoleUpdate(BaseModel):
    role: Literal["admin", "member", "viewer"]

class WorkspaceSettingsOut(BaseModel):
    workspace_id: UUID
    name: str
    owner_id: UUID
    is_admin: bool
    settings_allow_dm: bool
    settings_ai_daily_limit: int
    settings_allow_file_uploads: bool
    settings_restrict_invites: bool
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.5-flash"
    ai_ollama_url: str = "http://localhost:11434"
    ai_today_usage: int
    ai_daily_limit: int

class WorkspaceSettingsUpdate(BaseModel):
    settings_allow_dm: Optional[bool] = None
    settings_ai_daily_limit: Optional[int] = None
    settings_allow_file_uploads: Optional[bool] = None
    settings_restrict_invites: Optional[bool] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_ollama_url: Optional[str] = None

class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    invite_code: str
    owner_id: UUID
    settings_allow_dm: bool = True
    settings_ai_daily_limit: int = 50
    settings_allow_file_uploads: bool = True
    settings_restrict_invites: bool = False
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.5-flash"
    ai_ollama_url: str = "http://localhost:11434"
    created_at: datetime
    members: list[WorkspaceMemberOut] = []

    class Config:
        from_attributes = True


# --- Document schemas ---

class DocumentCreate(BaseModel):
    title: str = "Untitled"
    content: Optional[str] = ""
    workspace_id: UUID

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class DocumentOut(BaseModel):
    id: UUID
    title: str
    content: Optional[str]
    workspace_id: UUID
    created_by:UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Message schemas ---

class MessageOut(BaseModel):
    id: UUID
    content: str
    workspace_id: UUID
    sender_id: UUID
    sender_email: str
    recipient_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    recipient_id: Optional[UUID] = None


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = "medium"
    task_type: Optional[str] = "feature"
    requires_commit: Optional[bool] = False
    workspace_id: UUID
    assigned_to: Optional[UUID] = None
    assigned_to_ids: Optional[list[UUID]] = []
    due_date: Optional[datetime] = None
    notify_assignee: Optional[bool] = False

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["todo", "in_progress", "done"]] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    task_type: Optional[str] = None
    requires_commit: Optional[bool] = None
    no_commit_reason: Optional[str] = None
    completion_notes: Optional[str] = None
    assigned_to: Optional[UUID] = None
    assigned_to_ids: Optional[list[UUID]] = None
    due_date: Optional[datetime] = None

class TaskOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    task_type: Optional[str] = "feature"
    requires_commit: Optional[bool] = False
    no_commit_reason: Optional[str] = None
    completion_notes: Optional[str] = None
    workspace_id: UUID
    created_by: UUID
    assigned_to: Optional[UUID] = None
    assignee_email: Optional[str] = None
    assigned_to_ids: list[UUID] = []
    assignee_emails: list[str] = []
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    github_links: list[TaskGitHubLinkOut] = []
    primary_commit: Optional[GitHubCommitOut] = None
    primary_pr: Optional[GitHubPullRequestOut] = None

    class Config:
        from_attributes = True


class TaskLinkCommitIn(BaseModel):
    commit_sha: Optional[str] = None
    commit_id: Optional[UUID] = None
    pr_id: Optional[UUID] = None
    verification_notes: Optional[str] = None


class TaskCompleteIn(BaseModel):
    commit_sha: Optional[str] = None
    commit_id: Optional[UUID] = None
    no_commit_reason: Optional[str] = None
    completion_notes: Optional[str] = None


class ChatMessage(BaseModel):
    role: str        # "user" or "model"
    content: str

class AIChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"

class AIChatSessionUpdate(BaseModel):
    title: str

class AIChatSessionOut(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages_count: Optional[int] = 0

    class Config:
        from_attributes = True

class AIChatRequest(BaseModel):
    message: str
    workspace_id: str
    session_id: Optional[str] = None
    history: list[ChatMessage] = []

class AIChatOut(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    session_id: Optional[UUID] = None
    role: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- GitHub Integration Schemas ---

class GitHubConnectionOut(BaseModel):
    id: UUID
    user_id: UUID
    workspace_id: Optional[UUID] = None
    github_user_id: Optional[str] = None
    github_login: Optional[str] = None
    installation_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GitHubRepositoryOut(BaseModel):
    id: UUID
    workspace_id: UUID
    github_repo_id: str
    owner_login: str
    name: str
    full_name: str
    is_private: bool
    default_branch: str
    installation_id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GitHubRepositoryToggle(BaseModel):
    repository_id: UUID
    is_active: bool


class GitHubPullRequestOut(BaseModel):
    id: UUID
    github_pr_id: str
    pr_number: int
    repository_id: UUID
    author_github_id: Optional[str]
    author_login: Optional[str]
    title: str
    body: Optional[str]
    state: str
    head_branch: Optional[str]
    base_branch: Optional[str]
    merged_at: Optional[datetime]
    url: str
    created_at: datetime

    class Config:
        from_attributes = True


class GitHubCommitOut(BaseModel):
    id: UUID
    sha: str
    repository_id: UUID
    author_github_id: Optional[str]
    author_login: Optional[str]
    message: str
    branch: Optional[str]
    url: Optional[str]
    additions: int
    deletions: int
    committed_at: datetime

    class Config:
        from_attributes = True


class TaskGitHubLinkOut(BaseModel):
    id: UUID
    task_id: UUID
    pr_id: Optional[UUID] = None
    commit_id: Optional[UUID] = None
    match_score: float = 1.0
    match_reason: Optional[str] = None
    status: str
    verification_status: Optional[str] = "linked"
    verification_source: Optional[str] = "local"
    verification_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    pr: Optional[GitHubPullRequestOut] = None
    commit: Optional[GitHubCommitOut] = None

    class Config:
        from_attributes = True


class SinceYouWereAwayOut(BaseModel):
    workspace_id: UUID
    since: datetime
    until: datetime
    summary: str
    pull_requests_count: int
    commits_count: int
    recent_pull_requests: list[GitHubPullRequestOut] = []
    recent_commits: list[GitHubCommitOut] = []


class WorkspaceActivityItem(BaseModel):
    id: str
    category: Literal["document", "task", "chat", "member", "github"]
    action: str
    title: str
    description: Optional[str] = None
    actor_email: Optional[str] = None
    target_id: Optional[str] = None
    target_link: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    created_at: datetime


class WorkspaceActivityResponse(BaseModel):
    workspace_id: UUID
    activities: list[WorkspaceActivityItem] = []


class WhenYouWereAwayTask(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    creator_email: Optional[str] = None
    assigned_to_email: Optional[str] = None
    assigned_to_ids: list[str] = []
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False
    is_approaching: bool = False
    is_new: bool = False
    is_status_changed: bool = False
    is_assigned_to_me: bool = False
    link: str = "/dashboard/tasks"


class WhenYouWereAwayGitHubPR(BaseModel):
    id: str
    pr_number: int
    title: str
    state: str
    author_login: Optional[str] = None
    repository_name: Optional[str] = None
    url: str
    merged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    link: str


class WhenYouWereAwayGitHubCommit(BaseModel):
    id: str
    sha: str
    message: str
    author_login: Optional[str] = None
    branch: Optional[str] = None
    url: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    committed_at: datetime
    repository_name: Optional[str] = None
    link: str


class WhenYouWereAwayTeamActivity(BaseModel):
    id: str
    category: Literal["document", "chat", "member", "workflow", "github", "task"]
    action: str
    title: str
    description: Optional[str] = None
    actor_email: Optional[str] = None
    target_link: str
    created_at: datetime


class WhenYouWereAwayStats(BaseModel):
    tasks_created_count: int = 0
    tasks_updated_count: int = 0
    tasks_assigned_to_user_count: int = 0
    tasks_overdue_count: int = 0
    tasks_approaching_count: int = 0
    github_commits_count: int = 0
    github_prs_count: int = 0
    team_docs_count: int = 0
    team_chats_count: int = 0
    team_members_count: int = 0
    total_events_count: int = 0


class WhenYouWereAwayResponse(BaseModel):
    workspace_id: UUID
    time_window_type: str
    since: datetime
    until: datetime
    since_label: str
    away_duration_seconds: int
    has_events: bool
    summary: str
    stats: WhenYouWereAwayStats
    tasks_created: list[WhenYouWereAwayTask] = []
    tasks_updated: list[WhenYouWereAwayTask] = []
    tasks_assigned_to_user: list[WhenYouWereAwayTask] = []
    tasks_overdue: list[WhenYouWereAwayTask] = []
    tasks_approaching: list[WhenYouWereAwayTask] = []
    github_prs: list[WhenYouWereAwayGitHubPR] = []
    github_commits: list[WhenYouWereAwayGitHubCommit] = []
    team_activities: list[WhenYouWereAwayTeamActivity] = []
    last_fetched_at: Optional[datetime] = None


# --- Orbit Flow (Section 26: Workflow / Flowchart Canvas) Schemas ---

class FlowNodeIn(BaseModel):
    node_key: str
    type: str = "default"
    label: str
    position_x: float
    position_y: float
    data_json: dict = {}
    linked_object_type: Optional[str] = None
    linked_object_id: Optional[str] = None


class FlowNodeOut(BaseModel):
    id: UUID
    flow_id: UUID
    node_key: str
    type: str
    label: str
    position_x: float
    position_y: float
    data_json: dict = {}
    linked_object_type: Optional[str] = None
    linked_object_id: Optional[str] = None

    class Config:
        from_attributes = True


class FlowEdgeIn(BaseModel):
    edge_key: str
    source_node_key: str
    target_node_key: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    label: Optional[str] = None
    data_json: dict = {}


class FlowEdgeOut(BaseModel):
    id: UUID
    flow_id: UUID
    edge_key: str
    source_node_key: str
    target_node_key: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None
    label: Optional[str] = None
    data_json: dict = {}

    class Config:
        from_attributes = True


class FlowCreate(BaseModel):
    workspace_id: UUID
    title: str = "Untitled Workflow"
    description: Optional[str] = None
    visibility: str = "workspace"
    template: Optional[str] = None  # e.g., "github_pr_triage", "release_pipeline", "blank"


class FlowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None


class FlowCommentIn(BaseModel):
    node_key: Optional[str] = None
    text: str


class FlowCommentOut(BaseModel):
    id: UUID
    flow_id: UUID
    node_key: Optional[str] = None
    user_id: UUID
    user_email: Optional[str] = None
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class FlowVersionOut(BaseModel):
    id: UUID
    flow_id: UUID
    version_name: str
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class FlowOut(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: Optional[str] = None
    created_by: UUID
    visibility: str
    created_at: datetime
    updated_at: datetime
    nodes_count: Optional[int] = 0
    edges_count: Optional[int] = 0

    class Config:
        from_attributes = True


class FlowDetailOut(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: Optional[str] = None
    created_by: UUID
    visibility: str
    created_at: datetime
    updated_at: datetime
    nodes: list[FlowNodeOut] = []
    edges: list[FlowEdgeOut] = []
    comments: list[FlowCommentOut] = []
    versions: list[FlowVersionOut] = []

    class Config:
        from_attributes = True


class FlowSyncPayload(BaseModel):
    nodes: list[FlowNodeIn]
    edges: list[FlowEdgeIn]


class FlowVersionCreate(BaseModel):
    version_name: str = "Snapshot"


class FlowAIExplainRequest(BaseModel):
    question: Optional[str] = None


