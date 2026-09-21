export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  invite_code: string;
  owner_id: string;
  settings_allow_dm?: boolean;
  settings_ai_daily_limit?: number;
  settings_allow_file_uploads?: boolean;
  settings_restrict_invites?: boolean;
  created_at: string;
  members: WorkspaceMember[];
}

export interface WorkspaceMember {
  user_id: string;
  role: "admin" | "member" | "viewer";
  joined_at: string;
}

export interface WorkspaceMemberDetail {
  id: string;
  user_id: string;
  email: string;
  role: "admin" | "member" | "viewer";
  joined_at: string;
}

export interface WorkspaceSettings {
  workspace_id: string;
  name: string;
  owner_id: string;
  is_admin: boolean;
  settings_allow_dm: boolean;
  settings_ai_daily_limit: number;
  settings_allow_file_uploads: boolean;
  settings_restrict_invites: boolean;
  ai_today_usage: number;
  ai_daily_limit: number;
}

export interface Document {
  id: string;
  title: string;
  content?: string;
  workspace_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  content: string;
  workspace_id: string;
  sender_id: string;
  sender_email: string;
  recipient_id?: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: "todo" | "in_progress" | "done";
  priority: "low" | "medium" | "high";
  workspace_id: string;
  created_by: string;
  assigned_to?: string | null;
  assignee_email?: string | null;
  assigned_to_ids?: string[];
  assignee_emails?: string[];
  due_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: "user" | "model";
  content: string;
}

export interface AIResponse {
  response: string;
  role: string;
  sources_used: number;
  session_id?: string;
  session_title?: string;
}

export interface AIChatSession {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages_count?: number;
}

export interface AIChatMessage {
  id: string;
  workspace_id: string;
  user_id: string;
  session_id?: string | null;
  role: "user" | "model";
  message: string;
  created_at: string;
}

export interface GitHubConnection {
  id: string;
  user_id: string;
  workspace_id?: string;
  github_user_id?: string;
  github_login?: string;
  installation_id: string;
  status: "active" | "suspended" | "revoked" | "disconnected";
  created_at: string;
  updated_at: string;
}

export interface GitHubRepository {
  id: string;
  workspace_id: string;
  github_repo_id: string;
  owner_login: string;
  name: string;
  full_name: string;
  is_private: boolean;
  default_branch: string;
  installation_id: string;
  is_active: boolean;
  created_at: string;
}

export interface GitHubPullRequest {
  id: string;
  github_pr_id: string;
  pr_number: number;
  repository_id: string;
  author_github_id?: string;
  author_login?: string;
  title: string;
  body?: string;
  state: "open" | "closed" | "merged";
  head_branch?: string;
  base_branch?: string;
  merged_at?: string;
  url: string;
  created_at: string;
}

export interface GitHubCommit {
  id: string;
  sha: string;
  repository_id: string;
  author_github_id?: string;
  author_login?: string;
  message: string;
  branch?: string;
  url?: string;
  additions: number;
  deletions: number;
  committed_at: string;
}

export interface TaskGitHubLink {
  id: string;
  task_id: string;
  pr_id?: string;
  commit_id?: string;
  match_score: number;
  match_reason?: string;
  status: "suggested" | "accepted" | "dismissed";
  created_at: string;
  reviewed_at?: string;
  pr?: GitHubPullRequest;
  commit?: GitHubCommit;
}

export interface SinceYouWereAway {
  workspace_id: string;
  since: string;
  until: string;
  summary: string;
  pull_requests_count: number;
  commits_count: number;
  recent_pull_requests: GitHubPullRequest[];
  recent_commits: GitHubCommit[];
}

export interface WorkspaceActivityItem {
  id: string;
  category: "document" | "task" | "chat" | "member" | "github";
  action: string;
  title: string;
  description?: string;
  actor_email?: string;
  target_id?: string;
  target_link?: string;
  status?: string;
  priority?: string;
  created_at: string;
}

export interface WorkspaceActivityResponse {
  workspace_id: string;
  activities: WorkspaceActivityItem[];
}



