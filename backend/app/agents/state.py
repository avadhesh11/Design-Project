from langgraph.graph import MessagesState

class WorkspaceState(MessagesState):
    workspace_id:str
    user_id:str
    user_email: str
    is_admin: bool