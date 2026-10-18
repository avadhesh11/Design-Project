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
  ai_provider?: string;
  ai_model?: string;
  ai_ollama_url?: string;
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
  task_type?: "feature" | "bug" | "chore" | "design" | "docs" | "other" | string;
  requires_commit?: boolean;
  no_commit_reason?: string | null;
  completion_notes?: string | null;
  workspace_id: string;
  created_by: string;
  assigned_to?: string | null;
  assignee_email?: string | null;
  assigned_to_ids?: string[];
  assignee_emails?: string[];
  due_date?: string;
  created_at: string;
  updated_at: string;
  github_links?: TaskGitHubLink[];
  primary_commit?: GitHubCommit | null;
  primary_pr?: GitHubPullRequest | null;
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
  status: "suggested" | "accepted" | "dismissed" | string;
  verification_status?: "verified_in_repo" | "manual_entry" | "unverified" | string;
  verification_source?: "github_api" | "local_db" | "manual" | string;
  verification_notes?: string;
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

export interface WhenYouWereAwayTask {
  id: string;
  title: string;
  description?: string;
  status: "todo" | "in_progress" | "done" | string;
  priority: "low" | "medium" | "high" | string;
  creator_email?: string;
  assigned_to_email?: string;
  assigned_to_ids?: string[];
  due_date?: string;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
  is_approaching: boolean;
  is_new: boolean;
  is_status_changed: boolean;
  is_assigned_to_me: boolean;
  link: string;
}

export interface WhenYouWereAwayGitHubPR {
  id: string;
  pr_number: number;
  title: string;
  state: "open" | "closed" | "merged" | string;
  author_login?: string;
  repository_name?: string;
  url: string;
  merged_at?: string;
  created_at: string;
  updated_at?: string;
  link: string;
}

export interface WhenYouWereAwayGitHubCommit {
  id: string;
  sha: string;
  message: string;
  author_login?: string;
  branch?: string;
  url?: string;
  additions: number;
  deletions: number;
  committed_at: string;
  repository_name?: string;
  link: string;
}

export interface WhenYouWereAwayTeamActivity {
  id: string;
  category: "document" | "chat" | "member" | "workflow" | "github" | "task";
  action: string;
  title: string;
  description?: string;
  actor_email?: string;
  target_link: string;
  created_at: string;
}

export interface WhenYouWereAwayStats {
  tasks_created_count: number;
  tasks_updated_count: number;
  tasks_assigned_to_user_count: number;
  tasks_overdue_count: number;
  tasks_approaching_count: number;
  github_commits_count: number;
  github_prs_count: number;
  team_docs_count: number;
  team_chats_count: number;
  team_members_count: number;
  total_events_count: number;
}

export interface WhenYouWereAwayResponse {
  workspace_id: string;
  time_window_type: string;
  since: string;
  until: string;
  since_label: string;
  away_duration_seconds: number;
  has_events: boolean;
  summary: string;
  stats: WhenYouWereAwayStats;
  tasks_created: WhenYouWereAwayTask[];
  tasks_updated: WhenYouWereAwayTask[];
  tasks_assigned_to_user: WhenYouWereAwayTask[];
  tasks_overdue: WhenYouWereAwayTask[];
  tasks_approaching: WhenYouWereAwayTask[];
  github_prs: WhenYouWereAwayGitHubPR[];
  github_commits: WhenYouWereAwayGitHubCommit[];
  team_activities: WhenYouWereAwayTeamActivity[];
  last_fetched_at?: string;
}




