from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

# =====================================================================
# 1. Authentication Schemas
# =====================================================================

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


# =====================================================================
# 2. Workspace & Member Schemas
# =====================================================================

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


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    invite_code: str
    owner_id: UUID
    created_at: datetime
    members: list[WorkspaceMemberOut] = []

    class Config:
        from_attributes = True


class WorkspaceActivityItem(BaseModel):
    id: str
    category: Literal["document", "task", "member"]
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


# =====================================================================
# 3. Document Management Schemas (RAG Knowledge Base)
# =====================================================================

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
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =====================================================================
# 4. Task Management Schemas (Kanban Board)
# =====================================================================

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


# =====================================================================
# 5. AI Workspace Chat Schemas (Gemini 2.5 Flash / Agentic)
# =====================================================================

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
