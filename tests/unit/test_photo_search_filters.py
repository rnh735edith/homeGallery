import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.photo import Photo
from app.models.photo_metadata import PhotoMetadata
from app.models.user import User
from app.utils.security import hash_password
from app.api.photos import list_photos


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

        # Create photos
        photos = [
            Photo(id=1, filename="beach.jpg", original_path="/beach.jpg", exif_data={}),
            Photo(id=2, filename="dog.jpg", original_path="/dog.jpg", exif_data={}),
            Photo(id=3, filename="night.jpg", original_path="/night.jpg", exif_data={}),
        ]
        for p in photos:
            db.add(p)

        # Create metadata
        metadata_list = [
            PhotoMetadata(photo_id=1, objects=["beach", "ocean"], colors=["#0000FF"], scene_type="outdoor"),
            PhotoMetadata(photo_id=2, objects=["dog", "pet"], colors=["#8B4513"], scene_type="indoor"),
            PhotoMetadata(photo_id=3, objects=["stars"], colors=["#000000"], scene_type="night"),
        ]
        for m in metadata_list:
            db.add(m)

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


class TestTagSearch:
    def test_search_by_tag_returns_matching_photos(self, db_session, mock_user):
        """Tag search returns photos with matching metadata objects."""
        # Directly call the endpoint function
        result = list_photos(
            page=1,
            page_size=20,
            q=None,
            tag="beach",
            color=None,
            min_quality=None,
            favorite=None,
            sort_by="uploaded_at",
            sort_order="desc",
            db=db_session,
            current_user=mock_user,
        )
        assert len(result.photos) >= 1
        filenames = [p.filename for p in result.photos]
        assert "beach.jpg" in filenames

    def test_search_by_tag_no_results(self, db_session, mock_user):
        """Tag search returns empty when no matches."""
        result = list_photos(
            page=1,
            page_size=20,
            q=None,
            tag="nonexistent",
            color=None,
            min_quality=None,
            favorite=None,
            sort_by="uploaded_at",
            sort_order="desc",
            db=db_session,
            current_user=mock_user,
        )
        assert len(result.photos) == 0


class TestColorSearch:
    def test_search_by_color_returns_matching_photos(self, db_session, mock_user):
        """Color search returns photos with matching color palette."""
        result = list_photos(
            page=1,
            page_size=20,
            q=None,
            tag=None,
            color="#0000FF",
            min_quality=None,
            favorite=None,
            sort_by="uploaded_at",
            sort_order="desc",
            db=db_session,
            current_user=mock_user,
        )
        assert len(result.photos) >= 1
        filenames = [p.filename for p in result.photos]
        assert "beach.jpg" in filenames

    def test_search_by_color_no_results(self, db_session, mock_user):
        """Color search returns empty when no matches."""
        result = list_photos(
            page=1,
            page_size=20,
            q=None,
            tag=None,
            color="#FF0000",
            min_quality=None,
            favorite=None,
            sort_by="uploaded_at",
            sort_order="desc",
            db=db_session,
            current_user=mock_user,
        )
        assert len(result.photos) == 0
