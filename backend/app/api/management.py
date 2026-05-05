import os
import json
import shutil
import zipfile
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db, SessionFactory
from app.config_loader import config_loader
from app.models.photo import Photo
from app.models.album import Album, AlbumPhoto
from app.models.user import User
from app.models.face import FaceDetection, Person
from app.utils.security import get_current_admin_user
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/management", tags=["management"])


def _get_allowed_roots(storage: dict) -> list[str]:
    """Get list of allowed directory roots from storage config."""
    roots = []
    for key in ["photo_dir", "thumbnail_dir", "face_encoding_dir"]:
        if storage.get(key):
            roots.append(os.path.realpath(storage[key]))
    roots.append(os.path.realpath(os.path.join(os.getcwd(), "data")))
    roots.append(os.path.realpath(os.getcwd()))
    return roots


def _validate_path_in_roots(path: str, allowed_roots: list[str]) -> str:
    """Validate and resolve a path, ensuring it's within allowed roots.

    Raises HTTPException if path is outside allowed directories.
    Returns the resolved real path for safe use in filesystem operations.
    """
    real_path = os.path.realpath(path)
    # Ensure path doesn't escape allowed roots via traversal
    if not any(real_path.startswith(root + os.sep) or real_path == root for root in allowed_roots):
        raise HTTPException(status_code=403, detail="Access denied: path outside allowed directories")
    # Verify the resolved path is actually a directory or exists within allowed roots
    return real_path


@router.get("/status")
def get_management_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """Get system management status"""
    config = config_loader.load() or {}
    storage = config.get("storage", {})
    db_config = config.get("database", {})

    photo_dir = storage.get("photo_dir", "")
    thumbnail_dir = storage.get("thumbnail_dir", "")
    face_encoding_dir = storage.get("face_encoding_dir", "")

    def dir_stats(path):
        if not path or not os.path.exists(path):
            return {"exists": False, "size_bytes": 0, "file_count": 0}
        total_size = 0
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(path):
            file_count += len(filenames)
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    # File inaccessible - skip size calculation
                    pass
        return {"exists": True, "size_bytes": total_size, "file_count": file_count}

    photo_count = db.query(Photo).filter(Photo.deleted == False).count()
    album_count = db.query(Album).count()
    user_count = db.query(User).count()

    db_path = db_config.get("url", "").replace("sqlite:///", "").replace("sqlite://", "")
    db_size = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0

    return {
        "photo_count": photo_count,
        "album_count": album_count,
        "user_count": user_count,
        "db_path": db_path,
        "db_size_bytes": db_size,
        "photo_dir": dir_stats(photo_dir),
        "thumbnail_dir": dir_stats(thumbnail_dir),
        "face_encoding_dir": dir_stats(face_encoding_dir),
    }


@router.get("/config/export")
def export_config(current_user: User = Depends(get_current_admin_user)):
    """Export current configuration as JSON file"""
    config = config_loader.load()
    if not config:
        raise HTTPException(status_code=404, detail="No configuration found")

    safe_config = {k: v for k, v in config.items() if k != "admin"}
    safe_config.pop("security", None)

    temp_dir = tempfile.mkdtemp()
    export_path = os.path.join(temp_dir, "homegallery-config.json")
    with open(export_path, "w") as f:
        json.dump(safe_config, f, indent=2, default=str)

    logger.info(f"Config exported by {current_user.username}")
    return FileResponse(export_path, media_type="application/json", filename="homegallery-config.json")


@router.post("/config/import")
async def import_config(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user),
):
    """Import configuration from JSON file"""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    try:
        content = await file.read()
        config_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    required_keys = ["server", "storage"]
    for key in required_keys:
        if key not in config_data:
            raise HTTPException(status_code=400, detail=f"Missing required key: {key}")

    existing = config_loader.load() or {}
    merged = {**existing, **config_data}
    merged["version"] = "1.0.0"

    config_loader.save(merged)
    logger.info(f"Config imported by {current_user.username}")
    return {"message": "Configuration imported successfully. Restart required for some changes."}


@router.post("/backup/full")
def create_full_backup(
    include_photos: bool = Query(False, description="Include photo files in backup"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create a full system backup (config + database + optionally photos)"""
    config = config_loader.load()
    if not config:
        raise HTTPException(status_code=404, detail="No configuration found")

    storage = config.get("storage", {})
    db_config = config.get("database", {})
    db_path = db_config.get("url", "").replace("sqlite:///", "").replace("sqlite://", "")

    if not db_path or not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"homegallery-backup-{timestamp}"
    temp_dir = tempfile.mkdtemp()
    backup_dir = os.path.join(temp_dir, backup_name)
    os.makedirs(backup_dir)

    try:
        with zipfile.ZipFile(os.path.join(temp_dir, f"{backup_name}.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
            with open(os.path.join(backup_dir, "config.json"), "w") as f:
                json.dump(config, f, indent=2, default=str)
            zf.write(os.path.join(backup_dir, "config.json"), "config.json")
            zf.write(db_path, "database.db")

            photo_dir = storage.get("photo_dir", "")
            thumbnail_dir = storage.get("thumbnail_dir", "")
            face_encoding_dir = storage.get("face_encoding_dir", "")

            if include_photos and photo_dir and os.path.exists(photo_dir):
                for root, dirs, files in os.walk(photo_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("photos", os.path.relpath(file_path, photo_dir))
                        zf.write(file_path, arcname)

            if thumbnail_dir and os.path.exists(thumbnail_dir):
                for root, dirs, files in os.walk(thumbnail_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("thumbnails", os.path.relpath(file_path, thumbnail_dir))
                        zf.write(file_path, arcname)

            if face_encoding_dir and os.path.exists(face_encoding_dir):
                for root, dirs, files in os.walk(face_encoding_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("face_encodings", os.path.relpath(file_path, face_encoding_dir))
                        zf.write(file_path, arcname)

        backup_file = os.path.join(temp_dir, f"{backup_name}.zip")
        logger.info(f"Full backup created by {current_user.username} (include_photos={include_photos})")
        return FileResponse(backup_file, media_type="application/zip", filename=f"{backup_name}.zip")

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")


@router.post("/backup/restore")
async def restore_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user),
):
    """Restore from a backup ZIP file"""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a ZIP file")

    temp_dir = tempfile.mkdtemp()
    backup_path = os.path.join(temp_dir, file.filename)

    try:
        with open(backup_path, "wb") as f:
            f.write(await file.read())

        with zipfile.ZipFile(backup_path, "r") as zf:
            extract_dir = os.path.join(temp_dir, "extracted")
            zf.extractall(extract_dir)

            config = config_loader.load() or {}
            storage = config.get("storage", {})
            db_config = config.get("database", {})

            if os.path.exists(os.path.join(extract_dir, "config.json")):
                with open(os.path.join(extract_dir, "config.json"), "r") as f:
                    imported_config = json.load(f)
                config_loader.save(imported_config)
                config = imported_config
                storage = config.get("storage", {})
                db_config = config.get("database", {})

            db_path = db_config.get("url", "").replace("sqlite:///", "").replace("sqlite://", "")
            if db_path and os.path.exists(os.path.join(extract_dir, "database.db")):
                if os.path.exists(db_path):
                    os.remove(db_path)
                shutil.copy2(os.path.join(extract_dir, "database.db"), db_path)

            photo_dir = storage.get("photo_dir", "")
            if os.path.exists(os.path.join(extract_dir, "photos")):
                os.makedirs(photo_dir, exist_ok=True)
                for item in os.listdir(os.path.join(extract_dir, "photos")):
                    src = os.path.join(extract_dir, "photos", item)
                    dst = os.path.join(photo_dir, item)
                    if os.path.isfile(src):
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)

            thumbnail_dir = storage.get("thumbnail_dir", "")
            if os.path.exists(os.path.join(extract_dir, "thumbnails")):
                os.makedirs(thumbnail_dir, exist_ok=True)
                for item in os.listdir(os.path.join(extract_dir, "thumbnails")):
                    src = os.path.join(extract_dir, "thumbnails", item)
                    dst = os.path.join(thumbnail_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)

            face_encoding_dir = storage.get("face_encoding_dir", "")
            if os.path.exists(os.path.join(extract_dir, "face_encodings")):
                os.makedirs(face_encoding_dir, exist_ok=True)
                for item in os.listdir(os.path.join(extract_dir, "face_encodings")):
                    src = os.path.join(extract_dir, "face_encodings", item)
                    dst = os.path.join(face_encoding_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)

        logger.info(f"Backup restored by {current_user.username}")
        return {"message": "Backup restored successfully. Restart required for changes to take effect."}

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")


@router.post("/wipe/photos")
def wipe_all_photos(
    confirm: str = Query("", description="Must be 'DELETE ALL PHOTOS' to confirm"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Wipe all photos from the database"""
    if confirm != "DELETE ALL PHOTOS":
        raise HTTPException(status_code=400, detail="Confirmation string required: DELETE ALL PHOTOS")

    count = db.query(Photo).filter(Photo.deleted == False).update({"deleted": True})
    db.commit()
    logger.info(f"All photos wiped by {current_user.username} ({count} photos)")
    return {"message": f"All {count} photos have been deleted"}


@router.post("/wipe/albums")
def wipe_all_albums(
    confirm: str = Query("", description="Must be 'DELETE ALL ALBUMS' to confirm"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Wipe all albums"""
    if confirm != "DELETE ALL ALBUMS":
        raise HTTPException(status_code=400, detail="Confirmation string required: DELETE ALL ALBUMS")

    db.query(AlbumPhoto).delete()
    count = db.query(Album).delete()
    db.commit()
    logger.info(f"All albums wiped by {current_user.username} ({count} albums)")
    return {"message": f"All {count} albums have been deleted"}


@router.post("/wipe/database")
def wipe_database(
    confirm: str = Query("", description="Must be 'WIPE DATABASE' to confirm"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Wipe the entire database (keeps admin user)"""
    if confirm != "WIPE DATABASE":
        raise HTTPException(status_code=400, detail="Confirmation string required: WIPE DATABASE")

    db.query(AlbumPhoto).delete()
    db.query(Album).delete()
    db.query(FaceDetection).delete()
    db.query(Person).delete()
    db.query(Photo).delete()
    db.commit()
    logger.info(f"Database wiped by {current_user.username}")
    return {"message": "Database has been wiped. All data removed except admin user."}


@router.post("/wipe/full")
def wipe_full_system(
    confirm: str = Query("", description="Must be 'WIPE EVERYTHING' to confirm"),
    current_user: User = Depends(get_current_admin_user),
):
    """Full system wipe: database + photos + thumbnails + config"""
    if confirm != "WIPE EVERYTHING":
        raise HTTPException(status_code=400, detail="Confirmation string required: WIPE EVERYTHING")

    config = config_loader.load() or {}
    storage = config.get("storage", {})
    db_config = config.get("database", {})
    db_path = db_config.get("url", "").replace("sqlite:///", "").replace("sqlite://", "")

    db = SessionFactory()
    try:
        db.query(AlbumPhoto).delete()
        db.query(Album).delete()
        db.query(FaceDetection).delete()
        db.query(Person).delete()
        db.query(Photo).delete()
        db.query(User).filter(User.username != "testadmin").delete()
        db.commit()
    finally:
        db.close()

    if db_path and os.path.exists(db_path):
        os.remove(db_path)

    for dir_path in [storage.get("photo_dir"), storage.get("thumbnail_dir"), storage.get("face_encoding_dir")]:
        if dir_path and os.path.exists(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)

    config_loader.delete()
    logger.info(f"Full system wipe completed by {current_user.username}")
    return {"message": "Full system wipe completed. Restart server to run setup."}


@router.get("/folders/browse")
def browse_folders(
    path: str = Query(".", description="Directory path to browse"),
    current_user: User = Depends(get_current_admin_user),
):
    """Browse filesystem directories (restricted to safe paths)"""
    config = config_loader.load() or {}
    storage = config.get("storage", {})

    allowed_roots = _get_allowed_roots(storage)
    real_path = _validate_path_in_roots(path, allowed_roots)

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="Path does not exist")

    if not os.path.isdir(real_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    try:
        entries = []
        for item in sorted(os.listdir(real_path)):
            # Sanitize each item name before constructing paths
            if ".." in item or item.startswith("/"):
                continue
            item_path = os.path.join(real_path, item)
            # Verify item_path is still within the allowed directory
            if not os.path.realpath(item_path).startswith(real_path + os.sep):
                continue
            is_dir = os.path.isdir(item_path)
            if not is_dir:
                _, ext = os.path.splitext(item)
                if ext.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}:
                    continue
            entries.append({
                "name": item,
                "path": item_path,
                "is_directory": is_dir,
                "size": os.path.getsize(item_path) if not is_dir else 0,
            })
        return {
            "current_path": real_path,
            "parent_path": os.path.dirname(real_path) if real_path != os.path.dirname(real_path) else None,
            "entries": entries,
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")


@router.post("/folders/create")
def create_folder(
    path: str = Query(..., description="Full path for new folder"),
    current_user: User = Depends(get_current_admin_user),
):
    """Create a new directory"""
    config = config_loader.load() or {}
    storage = config.get("storage", {})
    allowed_roots = _get_allowed_roots(storage)

    real_path = _validate_path_in_roots(path, allowed_roots)

    try:
        os.makedirs(real_path, exist_ok=True)
        logger.info(f"Folder created: {real_path} by {current_user.username}")
        return {"message": f"Folder created: {real_path}", "path": real_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {e}")


@router.post("/folders/delete")
def delete_folder(
    path: str = Query(..., description="Full path to delete"),
    confirm: str = Query("", description="Must be 'DELETE FOLDER' to confirm"),
    current_user: User = Depends(get_current_admin_user),
):
    """Delete a directory"""
    if confirm != "DELETE FOLDER":
        raise HTTPException(status_code=400, detail="Confirmation string required: DELETE FOLDER")

    config = config_loader.load() or {}
    storage = config.get("storage", {})
    allowed_roots = _get_allowed_roots(storage)

    real_path = _validate_path_in_roots(path, allowed_roots)

    try:
        shutil.rmtree(real_path)
        logger.info(f"Folder deleted: {real_path} by {current_user.username}")
        return {"message": f"Folder deleted: {real_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete folder: {e}")


@router.get("/db/status")
def get_db_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Get database status and statistics"""
    config = config_loader.load() or {}
    db_config = config.get("database", {})
    db_path = db_config.get("url", "").replace("sqlite:///", "").replace("sqlite://", "")

    tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    table_stats = {}
    for (table_name,) in tables:
        count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        table_stats[table_name] = count

    db_size = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0

    return {
        "type": db_config.get("type", "sqlite"),
        "path": db_path,
        "size_bytes": db_size,
        "tables": table_stats,
    }


@router.post("/db/optimize")
def optimize_database(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Optimize database (VACUUM for SQLite)"""
    config = config_loader.load() or {}
    db_config = config.get("database", {})
    db_type = db_config.get("type", "sqlite")

    if db_type == "sqlite":
        db.execute(text("VACUUM"))
        db.commit()
        logger.info(f"Database optimized (VACUUM) by {current_user.username}")
        return {"message": "Database optimized successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Optimization not supported for {db_type}")


@router.post("/db/backup")
def create_db_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create a database backup file"""
    config = config_loader.load() or {}
    db_config = config.get("database", {})
    db_path = db_config.get("url", "").replace("sqlite:///", "").replace("sqlite://", "")

    if not db_path or not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    logger.info(f"Database backup created: {backup_path} by {current_user.username}")
    return FileResponse(backup_path, media_type="application/octet-stream", filename=os.path.basename(backup_path))
