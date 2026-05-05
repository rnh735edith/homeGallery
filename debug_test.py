import sys
import os
sys.path.insert(0, r'D:\Service\homeGallery')
os.chdir(r'D:\Service\homeGallery')
from unittest.mock import MagicMock
from app.models.photo import Photo
from app.agents.services.organization_service import OrganizationService
from app.config import get_settings

settings = get_settings()
service = OrganizationService(settings)

# Create test images
from PIL import Image
import tempfile
import os

with tempfile.TemporaryDirectory() as tmp:
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    path1 = os.path.join(tmp, "original.jpg")
    path2 = os.path.join(tmp, "copy.jpg")
    img.save(path1, "JPEG")
    img.save(path2, "JPEG")

    # Compute hashes
    hash1 = service.compute_phash(path1)
    hash2 = service.compute_phash(path2)
    print(f"Hash1: {hash1}")
    print(f"Hash2: {hash2}")
    print(f"Distance: {service.hash_distance(hash1, hash2)}")
    print(f"Same hash: {hash1 == hash2}")
