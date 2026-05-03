import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.photo_metadata import PhotoMetadata
from app.models.photo import Photo
from app.models.user import User
from app.utils.security import hash_password
from app.api.metadata import get_photo_metadata

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def db_session():
    # Create tables in test database
    Base.metadata.create_all(bind=test_engine)
    
    # Seed test data
    db = TestSessionFactory()
    try:
        # Create user
        user = User(
            id=1,
            username="testadmin",
            password_hash=hash_password("TestPass123!"),
            is_admin=True,
        )
        db.add(user)

        # Create photo
        photo = Photo(
            id=1,
            filename="test.jpg",
            original_path="/fake/test.jpg",
            width=100,
            height=100,
            exif_data={},
        )
        db.add(photo)

        # Create metadata
        metadata = PhotoMetadata(
            photo_id=1,
            objects=["dog", "beach"],
            colors=["#FF5733", "#33FF57"],
            scene_type="outdoor",
            sharpness=0.75,
            brightness=0.65,
        )
        db.add(metadata)
        db.commit()
    finally:
        db.close()
    
    # Create and yield a session for the tests
    session = TestSessionFactory()
    yield session
    session.close()
    
    # Cleanup
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def mock_user():
    return User(id=1, username="testadmin", is_admin=True)


class TestGetPhotoMetadata:
    def test_get_metadata_success(self, db_session, mock_user):
        # Directly call the endpoint function
        result = get_photo_metadata(photo_id=1, db=db_session, current_user=mock_user)
        
        assert result.objects == ["dog", "beach"]
        assert result.scene_type == "outdoor"
        assert result.colors == ["#FF5733", "#33FF57"]
        assert result.photo_id == 1

    def test_get_metadata_not_found(self, db_session, mock_user):
        # Directly call the endpoint function - should raise HTTPException
        from fastapi import HTTPException
        try:
            get_photo_metadata(photo_id=999, db=db_session, current_user=mock_user)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
