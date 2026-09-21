from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
from typing import Optional
from datetime import datetime
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
    ai_today_usage: int
    ai_daily_limit: int

class WorkspaceSettingsUpdate(BaseModel):
    settings_allow_dm: Optional[bool] = None
    settings_ai_daily_limit: Optional[int] = None
    settings_allow_file_uploads: Optional[bool] = None
    settings_restrict_invites: Optional[bool] = None

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
    assigned_to: Optional[UUID] = None
    assigned_to_ids: Optional[list[UUID]] = None
    due_date: Optional[datetime] = None

class TaskOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: str
    priority: str
    workspace_id: UUID
    created_by: UUID
    assigned_to: Optional[UUID] = None
    assignee_email: Optional[str] = None
    assigned_to_ids: list[UUID] = []
    assignee_emails: list[str] = []
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    pr_id: Optional[UUID]
    commit_id: Optional[UUID]
    match_score: float
    match_reason: Optional[str]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
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


