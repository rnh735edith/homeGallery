import pytest
from app.models.photo_metadata import PhotoMetadata
from app.database import SessionFactory, engine, Base


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_photo_metadata():
    db = SessionFactory()
    metadata = PhotoMetadata(
        photo_id=1,
        objects=["dog", "beach", "sunset"],
        colors=["#FF5733", "#33FF57", "#3357FF"],
        quality_score=0.85,
        sharpness=0.72,
        brightness=0.65,
        composition_score=0.78,
        scene_type="outdoor",
        is_duplicate=False,
    )
    db.add(metadata)
    db.commit()

    retrieved = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 1).first()
    assert retrieved is not None
    assert retrieved.photo_id == 1
    assert retrieved.objects == ["dog", "beach", "sunset"]
    assert retrieved.colors == ["#FF5733", "#33FF57", "#3357FF"]
    assert retrieved.quality_score == 0.85
    assert retrieved.sharpness == 0.72
    assert retrieved.brightness == 0.65
    assert retrieved.composition_score == 0.78
    assert retrieved.scene_type == "outdoor"
    assert retrieved.is_duplicate == False
    db.close()


def test_photo_metadata_defaults():
    db = SessionFactory()
    metadata = PhotoMetadata(photo_id=2)
    db.add(metadata)
    db.commit()

    retrieved = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 2).first()
    assert retrieved.objects == []
    assert retrieved.colors == []
    assert retrieved.quality_score is None
    assert retrieved.sharpness is None
    assert retrieved.brightness is None
    assert retrieved.composition_score is None
    assert retrieved.scene_type is None
    assert retrieved.is_duplicate == False
    assert retrieved.duplicate_of is None
    assert retrieved.enhanced_path is None
    assert retrieved.embedding_path is None
    assert retrieved.processed_at is not None
    db.close()


def test_photo_metadata_duplicate_link():
    db = SessionFactory()
    original = PhotoMetadata(photo_id=10)
    duplicate = PhotoMetadata(photo_id=11, is_duplicate=True, duplicate_of=10)
    db.add_all([original, duplicate])
    db.commit()

    dup = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 11).first()
    assert dup.is_duplicate == True
    assert dup.duplicate_of == 10
    db.close()


def test_photo_metadata_json_serialization():
    db = SessionFactory()
    metadata = PhotoMetadata(
        photo_id=3,
        objects=["person", "car"],
        colors=["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF"],
    )
    db.add(metadata)
    db.commit()

    retrieved = db.query(PhotoMetadata).filter(PhotoMetadata.photo_id == 3).first()
    assert isinstance(retrieved.objects, list)
    assert len(retrieved.objects) == 2
    assert isinstance(retrieved.colors, list)
    assert len(retrieved.colors) == 5
    db.close()
