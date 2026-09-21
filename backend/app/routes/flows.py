from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID
import os
import json
import logging

from ..database import get_db
from ..models import (
    User,
    WorkspaceMember,
    RoleEnum,
    Flow,
    FlowNode,
    FlowEdge,
    FlowComment,
    FlowVersion,
    Task,
    Document
)
from ..schemas import (
    FlowCreate,
    FlowUpdate,
    FlowOut,
    FlowDetailOut,
    FlowSyncPayload,
    FlowCommentIn,
    FlowCommentOut,
    FlowVersionCreate,
    FlowVersionOut,
    FlowAIExplainRequest
)
from ..dependencies import get_current_user
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["flows"])


def check_workspace_membership(workspace_id: UUID, user_id: UUID, db: Session):
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return member


def populate_template_nodes(flow: Flow, template: str, db: Session):
    """Seed flow with popular pre-configured templates."""
    if template == "github_pr_triage":
        nodes = [
            FlowNode(flow_id=flow.id, node_key="node-1", type="trigger", label="GitHub PR Opened", position_x=100, position_y=200, data_json={"icon": "GitPullRequest", "color": "#8B5CF6", "description": "Triggered when a developer creates a PR"}),
            FlowNode(flow_id=flow.id, node_key="node-2", type="action", label="Run CI Checks & Lint", position_x=380, position_y=200, data_json={"icon": "Cpu", "color": "#3B82F6", "description": "Run automated test suite"}),
            FlowNode(flow_id=flow.id, node_key="node-3", type="decision", label="All Checks Pass?", position_x=660, position_y=180, data_json={"icon": "HelpCircle", "color": "#F59E0B", "description": "Verify code quality gates"}),
            FlowNode(flow_id=flow.id, node_key="node-4", type="action", label="Assign Code Reviewer", position_x=960, position_y=100, data_json={"icon": "UserCheck", "color": "#10B981", "description": "Request review from team lead"}),
            FlowNode(flow_id=flow.id, node_key="node-5", type="action", label="Post Slack / In-App Alert", position_x=960, position_y=300, data_json={"icon": "Bell", "color": "#EF4444", "description": "Notify author of test failure"}),
            FlowNode(flow_id=flow.id, node_key="node-6", type="note", label="Release Policy", position_x=380, position_y=400, data_json={"icon": "StickyNote", "color": "#FCD34D", "description": "All PRs require minimum 1 approval and clean CI before merge."}),
        ]
        edges = [
            FlowEdge(flow_id=flow.id, edge_key="edge-1-2", source_node_key="node-1", target_node_key="node-2", label="Push event"),
            FlowEdge(flow_id=flow.id, edge_key="edge-2-3", source_node_key="node-2", target_node_key="node-3", label="CI result"),
            FlowEdge(flow_id=flow.id, edge_key="edge-3-4", source_node_key="node-3", target_node_key="node-4", label="Yes / Passed"),
            FlowEdge(flow_id=flow.id, edge_key="edge-3-5", source_node_key="node-3", target_node_key="node-5", label="No / Failed"),
        ]
        db.add_all(nodes)
        db.add_all(edges)

    elif template == "release_pipeline":
        nodes = [
            FlowNode(flow_id=flow.id, node_key="node-1", type="trigger", label="Release Tag Pushed", position_x=100, position_y=180, data_json={"icon": "Tag", "color": "#6366F1", "description": "v*.*.* release triggered"}),
            FlowNode(flow_id=flow.id, node_key="node-2", type="action", label="Build Docker Artifacts", position_x=380, position_y=180, data_json={"icon": "Box", "color": "#3B82F6", "description": "Compile & tag production images"}),
            FlowNode(flow_id=flow.id, node_key="node-3", type="delay", label="Staging Soak Test (2h)", position_x=660, position_y=180, data_json={"icon": "Clock", "color": "#EC4899", "description": "Allow smoke tests & QA verification"}),
            FlowNode(flow_id=flow.id, node_key="node-4", type="action", label="Production Deploy", position_x=940, position_y=180, data_json={"icon": "Rocket", "color": "#10B981", "description": "Zero-downtime rolling update"}),
            FlowNode(flow_id=flow.id, node_key="node-5", type="action", label="Generate Release Notes", position_x=1220, position_y=180, data_json={"icon": "FileText", "color": "#8B5CF6", "description": "Summarize commits and publish doc"}),
        ]
        edges = [
            FlowEdge(flow_id=flow.id, edge_key="e1-2", source_node_key="node-1", target_node_key="node-2", label="Trigger build"),
            FlowEdge(flow_id=flow.id, edge_key="e2-3", source_node_key="node-2", target_node_key="node-3", label="Deploy to staging"),
            FlowEdge(flow_id=flow.id, edge_key="e3-4", source_node_key="node-3", target_node_key="node-4", label="Approval"),
            FlowEdge(flow_id=flow.id, edge_key="e4-5", source_node_key="node-4", target_node_key="node-5", label="Complete"),
        ]
        db.add_all(nodes)
        db.add_all(edges)

    elif template == "incident_response":
        nodes = [
            FlowNode(flow_id=flow.id, node_key="node-1", type="trigger", label="PagerDuty / Sentry Alert", position_x=100, position_y=200, data_json={"icon": "AlertTriangle", "color": "#EF4444", "description": "P1/P2 error spike detected"}),
            FlowNode(flow_id=flow.id, node_key="node-2", type="action", label="Create Incident War Room", position_x=380, position_y=200, data_json={"icon": "Video", "color": "#3B82F6", "description": "Spin up Orbit Meet call & channel"}),
            FlowNode(flow_id=flow.id, node_key="node-3", type="action", label="Mitigate & Rollback", position_x=680, position_y=200, data_json={"icon": "RotateCcw", "color": "#F59E0B", "description": "Revert offending commit or scale pods"}),
            FlowNode(flow_id=flow.id, node_key="node-4", type="action", label="AI Post-Mortem Synthesis", position_x=980, position_y=200, data_json={"icon": "Sparkles", "color": "#8B5CF6", "description": "Extract timeline from logs and meeting transcript"}),
        ]
        edges = [
            FlowEdge(flow_id=flow.id, edge_key="e1-2", source_node_key="node-1", target_node_key="node-2", label="Page on-call"),
            FlowEdge(flow_id=flow.id, edge_key="e2-3", source_node_key="node-2", target_node_key="node-3", label="Triage"),
            FlowEdge(flow_id=flow.id, edge_key="e3-4", source_node_key="node-3", target_node_key="node-4", label="Resolved"),
        ]
        db.add_all(nodes)
        db.add_all(edges)


@router.get("/", response_model=list[FlowOut])
def get_flows(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    member = check_workspace_membership(workspace_id, current_user.id, db)
    flows = db.query(Flow).filter(Flow.workspace_id == workspace_id).order_by(Flow.updated_at.desc()).all()
    
    result = []
    for f in flows:
        # If private, only creator and admins can see it
        if f.visibility == "private" and f.created_by != current_user.id and member.role.value != "admin":
            continue

        out = FlowOut.from_orm(f)
        out.nodes_count = len(f.nodes)
        out.edges_count = len(f.edges)
        result.append(out)
    return result


@router.post("/", response_model=FlowDetailOut)
def create_flow(
    flow_in: FlowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_workspace_membership(flow_in.workspace_id, current_user.id, db)
    
    new_flow = Flow(
        workspace_id=flow_in.workspace_id,
        title=flow_in.title or "Untitled Workflow",
        description=flow_in.description,
        visibility=flow_in.visibility or "workspace",
        created_by=current_user.id
    )
    db.add(new_flow)
    db.flush()

    if flow_in.template and flow_in.template != "blank":
        populate_template_nodes(new_flow, flow_in.template, db)
    else:
        # Create a default starting trigger node
        start_node = FlowNode(
            flow_id=new_flow.id,
            node_key="node-1",
            type="trigger",
            label="Start Trigger",
            position_x=150,
            position_y=150,
            data_json={"icon": "Play", "color": "#10B981", "description": "Entry point for this workflow"}
        )
        db.add(start_node)

    db.commit()
    db.refresh(new_flow)
    return new_flow


@router.get("/{flow_id}", response_model=FlowDetailOut)
def get_flow_detail(
    flow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    member = check_workspace_membership(flow.workspace_id, current_user.id, db)

    # If private, only creator and admins can access
    if flow.visibility == "private" and flow.created_by != current_user.id and member.role.value != "admin":
        raise HTTPException(status_code=403, detail="This workflow is private to its creator.")

    return flow


@router.put("/{flow_id}", response_model=FlowOut)
def update_flow(
    flow_id: UUID,
    flow_update: FlowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    check_workspace_membership(flow.workspace_id, current_user.id, db)

    if flow_update.title is not None:
        flow.title = flow_update.title
    if flow_update.description is not None:
        flow.description = flow_update.description
    if flow_update.visibility is not None:
        flow.visibility = flow_update.visibility

    flow.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(flow)
    return flow


@router.delete("/{flow_id}")
def delete_flow(
    flow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    member = check_workspace_membership(flow.workspace_id, current_user.id, db)
    is_admin = member.role == RoleEnum.admin or member.role == "admin" or str(getattr(member.role, "value", member.role)) == "admin"
    is_creator = str(flow.created_by) == str(current_user.id)

    if not (is_admin or is_creator):
        raise HTTPException(status_code=403, detail="You are not authorized to delete this flow")

    db.delete(flow)
    db.commit()
    return {"message": "Flow deleted successfully"}


@router.post("/{flow_id}/sync")
def sync_flow_elements(
    flow_id: UUID,
    payload: FlowSyncPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    check_workspace_membership(flow.workspace_id, current_user.id, db)

    # Replace existing nodes and edges cleanly
    db.query(FlowNode).filter(FlowNode.flow_id == flow_id).delete(synchronize_session=False)
    db.query(FlowEdge).filter(FlowEdge.flow_id == flow_id).delete(synchronize_session=False)

    for n in payload.nodes:
        db.add(FlowNode(
            flow_id=flow.id,
            node_key=n.node_key,
            type=n.type,
            label=n.label,
            position_x=n.position_x,
            position_y=n.position_y,
            data_json=n.data_json or {},
            linked_object_type=n.linked_object_type,
            linked_object_id=n.linked_object_id
        ))

    for e in payload.edges:
        db.add(FlowEdge(
            flow_id=flow.id,
            edge_key=e.edge_key,
            source_node_key=e.source_node_key,
            target_node_key=e.target_node_key,
            source_handle=e.source_handle,
            target_handle=e.target_handle,
            label=e.label,
            data_json=e.data_json or {}
        ))

    flow.updated_at = datetime.now(UTC)
    db.commit()
    return {"status": "ok", "nodes_count": len(payload.nodes), "edges_count": len(payload.edges)}


@router.post("/{flow_id}/comments", response_model=FlowCommentOut)
def add_flow_comment(
    flow_id: UUID,
    comment_in: FlowCommentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    check_workspace_membership(flow.workspace_id, current_user.id, db)

    comment = FlowComment(
        flow_id=flow_id,
        node_key=comment_in.node_key,
        user_id=current_user.id,
        text=comment_in.text
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    out = FlowCommentOut.from_orm(comment)
    out.user_email = current_user.email
    return out


@router.post("/{flow_id}/versions", response_model=FlowVersionOut)
def create_flow_version(
    flow_id: UUID,
    version_in: FlowVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    check_workspace_membership(flow.workspace_id, current_user.id, db)

    # Snapshot current graph
    snapshot = {
        "title": flow.title,
        "description": flow.description,
        "nodes": [
            {
                "node_key": n.node_key,
                "type": n.type,
                "label": n.label,
                "position_x": n.position_x,
                "position_y": n.position_y,
                "data_json": n.data_json,
                "linked_object_type": n.linked_object_type,
                "linked_object_id": n.linked_object_id
            }
            for n in flow.nodes
        ],
        "edges": [
            {
                "edge_key": e.edge_key,
                "source_node_key": e.source_node_key,
                "target_node_key": e.target_node_key,
                "source_handle": e.source_handle,
                "target_handle": e.target_handle,
                "label": e.label,
                "data_json": e.data_json
            }
            for e in flow.edges
        ]
    }

    version = FlowVersion(
        flow_id=flow_id,
        version_name=version_in.version_name or f"Snapshot {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
        snapshot_json=snapshot,
        created_by=current_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.post("/{flow_id}/versions/{version_id}/restore", response_model=FlowDetailOut)
def restore_flow_version(
    flow_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    check_workspace_membership(flow.workspace_id, current_user.id, db)

    version = db.query(FlowVersion).filter(FlowVersion.id == version_id, FlowVersion.flow_id == flow_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version snapshot not found")

    snapshot = version.snapshot_json
    # Restore nodes and edges
    db.query(FlowNode).filter(FlowNode.flow_id == flow_id).delete(synchronize_session=False)
    db.query(FlowEdge).filter(FlowEdge.flow_id == flow_id).delete(synchronize_session=False)

    for n in snapshot.get("nodes", []):
        db.add(FlowNode(
            flow_id=flow.id,
            node_key=n["node_key"],
            type=n.get("type", "default"),
            label=n.get("label", "Step"),
            position_x=n.get("position_x", 0),
            position_y=n.get("position_y", 0),
            data_json=n.get("data_json", {}),
            linked_object_type=n.get("linked_object_type"),
            linked_object_id=n.get("linked_object_id")
        ))

    for e in snapshot.get("edges", []):
        db.add(FlowEdge(
            flow_id=flow.id,
            edge_key=e["edge_key"],
            source_node_key=e["source_node_key"],
            target_node_key=e["target_node_key"],
            source_handle=e.get("source_handle"),
            target_handle=e.get("target_handle"),
            label=e.get("label"),
            data_json=e.get("data_json", {})
        ))

    flow.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(flow)
    return flow


@router.post("/{flow_id}/ai-explain")
async def ai_explain_flow(
    flow_id: UUID,
    req: FlowAIExplainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    check_workspace_membership(flow.workspace_id, current_user.id, db)

    # Format nodes and connections for LLM
    nodes_summary = []
    for n in flow.nodes:
        linked = f"(Linked to {n.linked_object_type} #{n.linked_object_id})" if n.linked_object_type else ""
        desc = n.data_json.get("description", "") if n.data_json else ""
        nodes_summary.append(f"- [{n.type.upper()}] '{n.label}': {desc} {linked}")

    edges_summary = []
    node_map = {n.node_key: n.label for n in flow.nodes}
    for e in flow.edges:
        src = node_map.get(e.source_node_key, e.source_node_key)
        tgt = node_map.get(e.target_node_key, e.target_node_key)
        lbl = f" (via '{e.label}')" if e.label else ""
        edges_summary.append(f"- {src} ➔ {tgt}{lbl}")

    prompt = f"""You are the Orbit Workspace AI Assistant analyzing a workflow/process diagram titled '{flow.title}'.

Workflow Overview:
{flow.description or 'No description provided'}

Nodes / Steps in Flow:
{chr(10).join(nodes_summary) if nodes_summary else 'No nodes defined'}

Step Connections / Pathways:
{chr(10).join(edges_summary) if edges_summary else 'No connections defined'}

User Specific Question:
{req.question or 'Explain this workflow end-to-end, its critical path, decision points, and suggest optimization recommendations.'}
"""

    try:
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3
        )
        res = await llm.ainvoke([
            SystemMessage(content="You are an expert system architect and workflow analyst. Provide crisp, structured markdown explanations highlighting triggers, decisions, actions, and potential bottlenecks."),
            HumanMessage(content=prompt)
        ])
        return {"explanation": res.content}
    except Exception as e:
        logger.error("AI explain flow error: %s", e)
        return {
            "explanation": f"### Workflow Summary for {flow.title}\n\nThis flow contains **{len(flow.nodes)} steps** and **{len(flow.edges)} connections**.\n\n*Key steps include:*\n" + "\n".join([f"- {n.label} ({n.type})" for n in flow.nodes[:5]])
        }
