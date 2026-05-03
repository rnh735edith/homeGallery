import pytest
from datetime import datetime
from app.models.task_queue import Task


def test_create_task(test_db):
    task = Task(
        id="test-uuid-123",
        type="metadata",
        status="pending",
        photo_id=1,
        description="Extracting metadata from test.jpg"
    )
    test_db.add(task)
    test_db.commit()
    
    retrieved = test_db.query(Task).filter(Task.id == "test-uuid-123").first()
    assert retrieved is not None
    assert retrieved.type == "metadata"
    assert retrieved.status == "pending"
    assert retrieved.photo_id == 1
    assert retrieved.progress == 0.0
    assert retrieved.created_at is not None


def test_task_status_transitions(test_db):
    task = Task(id="test-uuid", type="analysis", status="pending")
    test_db.add(task)
    test_db.commit()
    
    task.status = "running"
    task.started_at = datetime.now()
    task.progress = 0.5
    test_db.commit()
    
    task.status = "completed"
    task.completed_at = datetime.now()
    task.progress = 1.0
    task.result = {"objects": ["dog", "beach"]}
    test_db.commit()
    
    retrieved = test_db.query(Task).filter(Task.id == "test-uuid").first()
    assert retrieved.status == "completed"
    assert retrieved.progress == 1.0
    assert retrieved.result["objects"] == ["dog", "beach"]


def test_task_failure(test_db):
    task = Task(id="test-fail", type="search", status="running")
    test_db.add(task)
    test_db.commit()
    
    task.status = "failed"
    task.error = "Model not found"
    task.completed_at = datetime.now()
    test_db.commit()
    
    retrieved = test_db.query(Task).filter(Task.id == "test-fail").first()
    assert retrieved.status == "failed"
    assert retrieved.error == "Model not found"


def test_query_tasks_by_status(test_db):
    for i in range(5):
        test_db.add(Task(id=f"task-{i}", type="metadata", status="pending" if i < 3 else "completed"))
    test_db.commit()
    
    pending = test_db.query(Task).filter(Task.status == "pending").all()
    assert len(pending) == 3
    
    completed = test_db.query(Task).filter(Task.status == "completed").all()
    assert len(completed) == 2
