import time
import uuid
from enum import Enum
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/queue", tags=["queue"])


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    THUMBNAIL = "thumbnail"
    FACE_DETECTION = "face_detection"
    IMPORT_PHOTOS = "import_photos"
    BACKUP = "backup"
    CUSTOM = "custom"


class Task(BaseModel):
    id: str
    type: str
    status: str = TaskStatus.PENDING
    description: str = ""
    progress: float = 0.0
    total_items: int = 0
    processed_items: int = 0
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    result: Optional[dict] = None


task_store: dict[str, Task] = {}
task_queue: list[str] = []
active_tasks: set[str] = set()


def create_task(task_type: TaskType, description: str = "", total_items: int = 0) -> str:
    task_id = str(uuid.uuid4())[:8]
    task = Task(
        id=task_id,
        type=task_type.value,
        description=description,
        total_items=total_items,
        created_at=time.time(),
    )
    task_store[task_id] = task
    task_queue.append(task_id)
    logger.info(f"Task created: {task_id} ({task_type.value}) - {description}")
    return task_id


def start_task(task_id: str):
    if task_id not in task_store:
        raise ValueError(f"Task {task_id} not found")
    task = task_store[task_id]
    task.status = TaskStatus.RUNNING
    task.started_at = time.time()
    active_tasks.add(task_id)
    if task_id in task_queue:
        task_queue.remove(task_id)
    logger.info(f"Task started: {task_id}")


def update_task_progress(task_id: str, processed: int, error: str = None):
    if task_id not in task_store:
        return
    task = task_store[task_id]
    task.processed_items = processed
    if task.total_items > 0:
        task.progress = round((processed / task.total_items) * 100, 1)
    if error:
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        active_tasks.discard(task_id)
        logger.error(f"Task failed: {task_id} - {error}")
    else:
        logger.debug(f"Task progress: {task_id} - {task.processed_items}/{task.total_items}")


def complete_task(task_id: str, result: dict = None):
    if task_id not in task_store:
        return
    task = task_store[task_id]
    task.status = TaskStatus.COMPLETED
    task.progress = 100.0
    task.completed_at = time.time()
    task.result = result
    active_tasks.discard(task_id)
    logger.info(f"Task completed: {task_id}")


def cancel_task(task_id: str):
    if task_id not in task_store:
        return
    task = task_store[task_id]
    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        return
    task.status = TaskStatus.CANCELLED
    task.completed_at = time.time()
    active_tasks.discard(task_id)
    if task_id in task_queue:
        task_queue.remove(task_id)
    logger.info(f"Task cancelled: {task_id}")


@router.get("/")
def get_queue_status():
    tasks = []
    for task_id, task in task_store.items():
        tasks.append(task.model_dump())
    tasks.sort(key=lambda t: t["created_at"], reverse=True)

    return {
        "queue_length": len(task_queue),
        "active_count": len(active_tasks),
        "total_tasks": len(task_store),
        "tasks": tasks[:50],
    }


@router.get("/{task_id}")
def get_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_store[task_id].model_dump()


@router.post("/")
def create_queue_task(task_type: TaskType, description: str = "", total_items: int = 0):
    task_id = create_task(task_type, description, total_items)
    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"Task created: {task_type.value}",
    }


@router.post("/{task_id}/cancel")
def cancel_queue_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    cancel_task(task_id)
    return {"message": "Task cancelled"}


@router.post("/clear-completed")
def clear_completed():
    completed_ids = [
        tid for tid, task in task_store.items()
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
    ]
    for tid in completed_ids:
        del task_store[tid]
    return {"message": f"Cleared {len(completed_ids)} completed tasks"}
