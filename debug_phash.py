"""Debug script to test pHash computation."""
import sys
import os
sys.path.insert(0, r'D:\Service\homeGallery')
os.chdir(r'D:\Service\homeGallery')

from unittest.mock import MagicMock
from PIL import Image
import tempfile

from app.config import get_settings
from app.agents.services.organization_service import OrganizationService

settings = get_settings()
service = OrganizationService(settings)

# Create test images
tmp = tempfile.mkdtemp()
img = Image.new('RGB', (100, 100), color=(200, 200, 200))
path1 = os.path.join(tmp, 'original.png')
path2 = os.path.join(tmp, 'copy.png')
img.save(path1, 'PNG')
img.save(path2, 'PNG')

print(f"File exists path1: {os.path.exists(path1)}")
print(f"File exists path2: {os.path.exists(path2)}")

# Compute hashes
hash1 = service.compute_phash(path1)
hash2 = service.compute_phash(path2)
print(f'Hash1: {hash1}')
print(f'Hash2: {hash2}')
print(f'Distance: {service.hash_distance(hash1, hash2)}')
print(f'Same hash: {hash1 == hash2}')

# Cleanup
os.remove(path1)
os.remove(path2)
os.rmdir(tmp)
