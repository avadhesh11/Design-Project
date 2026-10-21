import uuid
import pytest
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, User, Workspace, WorkspaceMember, RoleEnum, Task, TaskStatus, TaskPriority
from app.agents.tools import update_task, create_task, get_tasks


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for regression tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create Users
        admin_a = User(id=uuid.uuid4(), email="admin_a@orbit.test")
        member_a = User(id=uuid.uuid4(), email="member_a@orbit.test")
        admin_b = User(id=uuid.uuid4(), email="admin_b@orbit.test")
        unrelated_user = User(id=uuid.uuid4(), email="unrelated@orbit.test")

        session.add_all([admin_a, member_a, admin_b, unrelated_user])
        session.flush()

        # Create Workspaces
        ws_a = Workspace(
            id=uuid.uuid4(),
            name="Workspace A",
            invite_code="INV-A",
            owner_id=admin_a.id
        )
        ws_b = Workspace(
            id=uuid.uuid4(),
            name="Workspace B",
            invite_code="INV-B",
            owner_id=admin_b.id
        )
        session.add_all([ws_a, ws_b])
        session.flush()

        # Add Workspace Memberships
        member_record_admin_a = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=ws_a.id,
            user_id=admin_a.id,
            role=RoleEnum.admin
        )
        member_record_member_a = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=ws_a.id,
            user_id=member_a.id,
            role=RoleEnum.member
        )
        member_record_admin_b = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=ws_b.id,
            user_id=admin_b.id,
            role=RoleEnum.admin
        )
        session.add_all([member_record_admin_a, member_record_member_a, member_record_admin_b])
        session.flush()

        # Create Tasks
        task_a = Task(
            id=uuid.uuid4(),
            title="Task A in Workspace A",
            description="Initial description",
            status=TaskStatus.todo,
            priority=TaskPriority.medium,
            workspace_id=ws_a.id,
            created_by=admin_a.id
        )
        task_b = Task(
            id=uuid.uuid4(),
            title="Task B in Workspace B",
            description="Initial description B",
            status=TaskStatus.todo,
            priority=TaskPriority.high,
            workspace_id=ws_b.id,
            created_by=admin_b.id
        )
        session.add_all([task_a, task_b])
        session.commit()

        yield {
            "session": session,
            "admin_a": admin_a,
            "member_a": member_a,
            "admin_b": admin_b,
            "unrelated_user": unrelated_user,
            "ws_a": ws_a,
            "ws_b": ws_b,
            "task_a": task_a,
            "task_b": task_b,
        }
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_authorized_admin_updates_task_in_own_workspace(db_session):
    """1. An authorized administrator updating a task in their own workspace."""
    session = db_session["session"]
    admin_a = db_session["admin_a"]
    ws_a = db_session["ws_a"]
    task_a = db_session["task_a"]

    res = update_task.func(
        task_id=str(task_a.id),
        workspace_id=str(ws_a.id),
        user_id=str(admin_a.id),
        status="in_progress",
        priority="high",
        title="Updated Task A Title",
        is_admin=True,
        db=session
    )

    assert "updated successfully" in res
    assert "Updated Task A Title" in res

    # Verify directly in DB
    refreshed_task = session.query(Task).filter(Task.id == task_a.id).first()
    assert refreshed_task.title == "Updated Task A Title"
    assert refreshed_task.status == "in_progress" or refreshed_task.status == TaskStatus.in_progress
    assert refreshed_task.priority == "high" or refreshed_task.priority == TaskPriority.high


def test_admin_attempting_to_update_another_workspace_task(db_session):
    """2. An administrator attempting to update another workspace's task."""
    session = db_session["session"]
    admin_a = db_session["admin_a"]
    ws_a = db_session["ws_a"]
    ws_b = db_session["ws_b"]
    task_b = db_session["task_b"]

    # Scenario 2a: Admin A uses their own authorized workspace ID with Task B's ID
    res1 = update_task.func(
        task_id=str(task_b.id),
        workspace_id=str(ws_a.id),
        user_id=str(admin_a.id),
        status="done",
        is_admin=True,
        db=session
    )
    assert res1 == "Task not found in the authorized workspace."

    # Scenario 2b: Admin A specifies Workspace B ID to reach Task B
    res2 = update_task.func(
        task_id=str(task_b.id),
        workspace_id=str(ws_b.id),
        user_id=str(admin_a.id),
        status="done",
        is_admin=True,
        db=session
    )
    assert "Permission denied" in res2

    # Verify task B was not modified
    task_b_db = session.query(Task).filter(Task.id == task_b.id).first()
    assert task_b_db.status == TaskStatus.todo


def test_non_admin_attempting_administrative_update(db_session):
    """3. A non-admin attempting an administrative update (even if is_admin=True is claimed)."""
    session = db_session["session"]
    member_a = db_session["member_a"]
    ws_a = db_session["ws_a"]
    task_a = db_session["task_a"]

    # Member claims is_admin=True in the tool call
    res = update_task.func(
        task_id=str(task_a.id),
        workspace_id=str(ws_a.id),
        user_id=str(member_a.id),
        status="done",
        is_admin=True,  # Untrusted caller claiming admin status
        db=session
    )

    assert "Permission denied: Only workspace admins can update tasks." in res

    # Verify task A was not modified
    task_a_db = session.query(Task).filter(Task.id == task_a.id).first()
    assert task_a_db.status == TaskStatus.todo


def test_nonexistent_task_id(db_session):
    """4. A nonexistent task ID."""
    session = db_session["session"]
    admin_a = db_session["admin_a"]
    ws_a = db_session["ws_a"]
    fake_task_id = str(uuid.uuid4())

    res = update_task.func(
        task_id=fake_task_id,
        workspace_id=str(ws_a.id),
        user_id=str(admin_a.id),
        status="done",
        is_admin=True,
        db=session
    )

    assert res == "Task not found in the authorized workspace."


def test_invalid_membership_or_authorization(db_session):
    """5. A user whose workspace membership or authorization is invalid."""
    session = db_session["session"]
    unrelated_user = db_session["unrelated_user"]
    ws_a = db_session["ws_a"]
    task_a = db_session["task_a"]

    # Unrelated user attempting update on workspace A
    res = update_task.func(
        task_id=str(task_a.id),
        workspace_id=str(ws_a.id),
        user_id=str(unrelated_user.id),
        status="done",
        is_admin=True,
        db=session
    )
    assert "Permission denied: User is not a member of this workspace." in res

    # Missing or empty user ID
    res_no_user = update_task.func(
        task_id=str(task_a.id),
        workspace_id=str(ws_a.id),
        user_id=None,
        status="done",
        is_admin=True,
        db=session
    )
    assert "Permission denied: User authorization could not be verified." in res_no_user

    # Missing or empty workspace ID
    res_no_ws = update_task.func(
        task_id=str(task_a.id),
        workspace_id="",
        user_id=str(unrelated_user.id),
        status="done",
        is_admin=True,
        db=session
    )
    assert "Permission denied: Workspace authorization could not be verified." in res_no_ws


def test_create_task_workspace_authorization(db_session):
    """Verify create_task enforces workspace admin authorization via DB checks."""
    session = db_session["session"]
    admin_a = db_session["admin_a"]
    member_a = db_session["member_a"]
    ws_a = db_session["ws_a"]

    # Admin A creates task in Workspace A -> Success
    res_admin = create_task.func(
        workspace_id=str(ws_a.id),
        created_by=str(admin_a.id),
        title="Admin Created Task",
        priority="high",
        is_admin=True,
        db=session
    )
    assert "Task created: 'Admin Created Task'" in res_admin

    # Member A attempts to create task claiming is_admin=True -> Denied
    res_member = create_task.func(
        workspace_id=str(ws_a.id),
        created_by=str(member_a.id),
        title="Unauthorized Task",
        is_admin=True,
        db=session
    )
    assert "Permission denied" in res_member
