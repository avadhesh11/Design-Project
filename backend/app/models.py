from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import uuid
import enum
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # relationships
    memberships = relationship("WorkspaceMember", back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    invite_code = Column(String, unique=True, nullable=False)
    invite_expires_at = Column(DateTime, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Workspace Admin Config & Controls
    settings_allow_dm = Column(Boolean, default=True, nullable=False)
    settings_ai_daily_limit = Column(Integer, default=50, nullable=False)  # 0 = unlimited
    settings_allow_file_uploads = Column(Boolean, default=True, nullable=False)
    settings_restrict_invites = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    members = relationship("WorkspaceMember", back_populates="workspace")
    documents = relationship("Document", back_populates="workspace")


class RoleEnum(str, enum.Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.member, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="memberships")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False, default="Untitled")
    content = Column(String, nullable=True, default="")  # stores raw text for now
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # relationships
    workspace = relationship("Workspace", back_populates="documents")
    author = relationship("User")

class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"

class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.todo, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.medium, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # relationships
    workspace = relationship("Workspace")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    assignees = relationship("TaskAssignee", back_populates="task", cascade="all, delete-orphan")


class TaskAssignee(Base):
    __tablename__ = "task_assignees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    task = relationship("Task", back_populates="assignees")
    user = relationship("User")



class AIChatSession(Base):
    __tablename__ = "ai_chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Chat", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    messages = relationship("AIChat", back_populates="session", cascade="all, delete-orphan")


class AIChat(Base):
    __tablename__ = "ai_chat_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"), nullable=True)
    role = Column(String, nullable=False)   
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    session = relationship("AIChatSession", back_populates="messages")


# --- GitHub Intelligence & Automation Models ---

class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True)
    github_user_id = Column(String, nullable=True)
    github_login = Column(String, nullable=True)
    installation_id = Column(String, nullable=False, index=True)
    status = Column(String, default="active", nullable=False)  # active, suspended, revoked, disconnected
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class GitHubRepository(Base):
    __tablename__ = "github_repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    github_repo_id = Column(String, nullable=False, index=True)
    owner_login = Column(String, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    default_branch = Column(String, default="main", nullable=False)
    installation_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class GitHubEvent(Base):
    __tablename__ = "github_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    repository_id = Column(String, nullable=True, index=True)
    github_actor_id = Column(String, nullable=True)
    occurred_at = Column(DateTime, default=lambda: datetime.now(UTC))
    payload_json = Column(JSON, nullable=False)
    processing_status = Column(String, default="pending", nullable=False)  # pending, processed, failed, ignored
    processed_at = Column(DateTime, nullable=True)


class GitHubPullRequest(Base):
    __tablename__ = "github_pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_pr_id = Column(String, nullable=False, index=True)
    pr_number = Column(Integer, nullable=False)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("github_repositories.id"), nullable=False)
    author_github_id = Column(String, nullable=True)
    author_login = Column(String, nullable=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=True)
    state = Column(String, nullable=False)  # open, closed, merged
    head_branch = Column(String, nullable=True)
    base_branch = Column(String, nullable=True)
    merged_at = Column(DateTime, nullable=True)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class GitHubCommit(Base):
    __tablename__ = "github_commits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sha = Column(String, nullable=False, index=True)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("github_repositories.id"), nullable=False)
    author_github_id = Column(String, nullable=True)
    author_login = Column(String, nullable=True)
    message = Column(String, nullable=False)
    branch = Column(String, nullable=True)
    url = Column(String, nullable=True)
    additions = Column(Integer, default=0, nullable=False)
    deletions = Column(Integer, default=0, nullable=False)
    committed_at = Column(DateTime, nullable=False)


class TaskGitHubLink(Base):
    __tablename__ = "task_github_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    pr_id = Column(UUID(as_uuid=True), ForeignKey("github_pull_requests.id"), nullable=True)
    commit_id = Column(UUID(as_uuid=True), ForeignKey("github_commits.id"), nullable=True)
    match_score = Column(Float, nullable=False)
    match_reason = Column(String, nullable=True)
    status = Column(String, default="suggested", nullable=False)  # suggested, accepted, dismissed
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    reviewed_at = Column(DateTime, nullable=True)  # For scoring weight feedback loop


class UserActivityState(Base):
    __tablename__ = "user_activity_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    last_seen_at = Column(DateTime, default=lambda: datetime.now(UTC))
    previous_seen_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_digest_at = Column(DateTime, nullable=True)
    timezone = Column(String, default="UTC", nullable=False)


class InstallationLifecycleEvent(Base):
    __tablename__ = "installation_lifecycle_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installation_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime, default=lambda: datetime.now(UTC))
    payload_json = Column(JSON, nullable=False)
    handled_at = Column(DateTime, nullable=True)


# --- Orbit Flow (Section 26: Workflow / Flowchart Canvas) Models ---

class Flow(Base):
    __tablename__ = "flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Untitled Workflow")
    description = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visibility = Column(String, default="workspace", nullable=False)  # workspace, private, link
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    workspace = relationship("Workspace")
    creator = relationship("User")
    nodes = relationship("FlowNode", back_populates="flow", cascade="all, delete-orphan")
    edges = relationship("FlowEdge", back_populates="flow", cascade="all, delete-orphan")
    comments = relationship("FlowComment", back_populates="flow", cascade="all, delete-orphan")
    versions = relationship("FlowVersion", back_populates="flow", cascade="all, delete-orphan")


class FlowNode(Base):
    __tablename__ = "flow_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String, nullable=False, index=True)  # ReactFlow node ID
    type = Column(String, default="default", nullable=False)  # trigger, action, decision, delay, note, custom
    label = Column(String, nullable=False, default="New Step")
    position_x = Column(Float, default=0.0, nullable=False)
    position_y = Column(Float, default=0.0, nullable=False)
    data_json = Column(JSON, default=dict, nullable=False)
    linked_object_type = Column(String, nullable=True)  # task, document, meeting, github_pr
    linked_object_id = Column(String, nullable=True)

    flow = relationship("Flow", back_populates="nodes")


class FlowEdge(Base):
    __tablename__ = "flow_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_key = Column(String, nullable=False, index=True)  # ReactFlow edge ID
    source_node_key = Column(String, nullable=False)
    target_node_key = Column(String, nullable=False)
    source_handle = Column(String, nullable=True)
    target_handle = Column(String, nullable=True)
    label = Column(String, nullable=True)
    data_json = Column(JSON, default=dict, nullable=False)

    flow = relationship("Flow", back_populates="edges")


class FlowComment(Base):
    __tablename__ = "flow_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String, nullable=True)  # Nullable if comment is on the general canvas
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    flow = relationship("Flow", back_populates="comments")
    user = relationship("User")


class FlowVersion(Base):
    __tablename__ = "flow_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    version_name = Column(String, nullable=False, default="Snapshot")
    snapshot_json = Column(JSON, nullable=False)  # Full node & edge graph
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    flow = relationship("Flow", back_populates="versions")
    creator = relationship("User")

    
