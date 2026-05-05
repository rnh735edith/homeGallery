import os
import time
import platform
import shutil
import psutil
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.config_loader import config_loader
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

APP_START_TIME = datetime.now(timezone.utc).isoformat()
request_count = 0
total_response_time = 0.0


@router.get("/dashboard")
def get_dashboard():
    try:
        config = config_loader.load() or {}
        storage_config = config.get("storage", {})
        photo_dir = storage_config.get("photo_dir", "./data/photos")
        thumbnail_dir = storage_config.get("thumbnail_dir", "./data/thumbnails")

        photo_count = 0
        photo_size = 0
        if os.path.isdir(photo_dir):
            for f in os.scandir(photo_dir):
                if f.is_file():
                    photo_count += 1
                    photo_size += f.stat().st_size

        thumbnail_count = 0
        thumbnail_size = 0
        if os.path.isdir(thumbnail_dir):
            for f in os.scandir(thumbnail_dir):
                if f.is_file():
                    thumbnail_count += 1
                    thumbnail_size += f.stat().st_size

        disk = shutil.disk_usage("/")
        db_path = config.get("database", {}).get("url", "sqlite:///./data/gallery.db")
        db_size = 0
        if db_path.startswith("sqlite:///"):
            db_file = db_path.replace("sqlite:///", "")
            if os.path.isfile(db_file):
                db_size = os.path.getsize(db_file)

        process = psutil.Process(os.getpid())
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        system_cpu = psutil.cpu_percent(interval=0.1)
        system_memory = psutil.virtual_memory()

        return {
            "system": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "uptime_seconds": time.time() - psutil.Process(os.getpid()).create_time(),
                "started_at": APP_START_TIME,
            },
            "performance": {
                "app_cpu_percent": round(cpu_percent, 1),
                "app_memory_mb": round(memory_info.rss / 1024 / 1024, 1),
                "app_memory_percent": round(memory_percent, 1),
                "app_threads": process.num_threads(),
                "system_cpu_percent": round(system_cpu, 1),
                "system_memory_total_gb": round(system_memory.total / 1024 / 1024 / 1024, 1),
                "system_memory_used_gb": round(system_memory.used / 1024 / 1024 / 1024, 1),
                "system_memory_percent": round(system_memory.percent, 1),
            },
            "storage": {
                "photos": {
                    "count": photo_count,
                    "size_mb": round(photo_size / 1024 / 1024, 1),
                    "path": os.path.abspath(photo_dir),
                },
                "thumbnails": {
                    "count": thumbnail_count,
                    "size_mb": round(thumbnail_size / 1024 / 1024, 1),
                    "path": os.path.abspath(thumbnail_dir),
                },
                "database": {
                    "size_mb": round(db_size / 1024 / 1024, 2),
                    "type": config.get("database", {}).get("type", "sqlite"),
                },
                "disk": {
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
                    "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
                    "free_gb": round(disk.free / 1024 / 1024 / 1024, 1),
                    "percent_used": round(disk.used / disk.total * 100, 1),
                },
            },
            "config": {
                "version": config.get("version", "1.0.0"),
                "server": config.get("server", {}),
                "processing": config.get("processing", {}),
            },
        }
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system")
def get_system_info():
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "node": platform.node(),
        "processor": platform.processor() or "unknown",
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "total_memory_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 1),
    }


@router.get("/logs")
def get_logs(limit: int = 100, level: str = None):
    log_file = os.path.join("data", "logs", "homegallery.log")
    if not os.path.isfile(log_file):
        return {"logs": []}

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        if level:
            lines = [l for l in lines if f" {level.upper()} " in l]

        lines = lines[-limit:]

        logs = []
        for line in lines:
            parts = line.strip().split(" - ", 4)
            if len(parts) >= 4:
                logs.append({
                    "timestamp": parts[0],
                    "logger": parts[1],
                    "level": parts[2],
                    "message": parts[4] if len(parts) > 4 else parts[3],
                })

        return {"logs": logs, "total": len(lines)}
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
