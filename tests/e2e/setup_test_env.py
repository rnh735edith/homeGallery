#!/usr/bin/env python
"""
Global setup for E2E tests.
Creates config.json and seeds test database.
"""

import os
import sys
import json
import bcrypt
import hashlib

# Add paths
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models.user import User
from app.models.photo import Photo
from app.models.album import Album, AlbumPhoto

DATA_DIR = os.path.join(repo_root, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
TEST_DB_PATH = os.path.join(DATA_DIR, "test_gallery.db")


def create_config():
    """Create config.json for tests."""
    config = {
        "version": "1.0.0",
        "setup_complete": True,
        "database": {
            "type": "sqlite",
            "url": f"sqlite:///{TEST_DB_PATH}"
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8080
        },
        "storage": {
            "photo_dir": os.path.join(DATA_DIR, "test_photos"),
            "thumbnail_dir": os.path.join(DATA_DIR, "test_thumbnails"),
            "face_encoding_dir": os.path.join(DATA_DIR, "test_face_encodings")
        },
        "security": {
            "jwt_secret": "test-secret-key-for-e2e-tests-only",
            "jwt_expire_minutes": 1440
        },
        "processing": {
            "auto_thumbnails": True,
            "face_detection": False,
            "face_processing_max_memory_mb": 512,
            "max_concurrent_tasks": 2
        }
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Created config at {CONFIG_PATH}")


def seed_database():
    """Create test database with test user and sample photos."""
    # Remove old test db if exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    engine = create_engine(f"sqlite:///{TEST_DB_PATH}")
    Base.metadata.create_all(engine)

    hashed_pw = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode()

    with Session(engine) as session:
        # Create test admin user
        admin = User(
            username="testadmin",
            password_hash=hashed_pw,
            is_admin=True
        )
        session.add(admin)
        session.commit()
        print(f"Created test user: testadmin")

        # Create sample photos
        photo_dir = os.path.join(DATA_DIR, "test_photos")
        os.makedirs(photo_dir, exist_ok=True)

        # Create dummy photo files
        for i in range(1, 6):
            photo_path = os.path.join(photo_dir, f"test_photo_{i}.jpg")
            # Create a minimal valid JPEG (1x1 red pixel)
            with open(photo_path, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7teletext7teletext(7teletext\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd2\x8a(\xff\xd9")

            photo = Photo(
                filename=f"test_photo_{i}.jpg",
                original_path=photo_path,
                user_id=admin.id,
                file_size=1024,
                mime_type="image/jpeg",
                width=1920,
                height=1080,
            )
            session.add(photo)

        session.commit()
        print(f"Created 5 test photos")

        # Create test albums
        album1 = Album(name="Vacation 2024", description="Summer vacation photos", user_id=admin.id)
        session.add(album1)
        session.flush()

        # Add photos to album
        all_photos = session.query(Photo).filter_by(user_id=admin.id).all()
        for idx, photo in enumerate(all_photos[:3]):
            album_photo = AlbumPhoto(album_id=album1.id, photo_id=photo.id, position=idx)
            session.add(album_photo)

        album2 = Album(name="Family", description="Family gatherings", user_id=admin.id)
        session.add(album2)
        session.flush()

        for idx, photo in enumerate(all_photos[3:]):
            album_photo = AlbumPhoto(album_id=album2.id, photo_id=photo.id, position=idx)
            session.add(album_photo)

        session.commit()
        print(f"Created 2 test albums with photos")


if __name__ == "__main__":
    create_config()
    seed_database()
    print("E2E test setup complete")
