import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.contact import ContactMessage


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestContactMessageModel:
    def test_create_contact_message(self, db_session):
        msg = ContactMessage(
            name="John Doe",
            email="john@example.com",
            subject="Feature Request",
            message="Please add dark mode!",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        db_session.add(msg)
        db_session.commit()

        saved = db_session.query(ContactMessage).first()
        assert saved.name == "John Doe"
        assert saved.email == "john@example.com"
        assert saved.subject == "Feature Request"
        assert saved.message == "Please add dark mode!"
        assert saved.ip_address == "192.168.1.1"
        assert saved.user_agent == "Mozilla/5.0"
        assert saved.is_read is False

    def test_contact_message_defaults(self, db_session):
        msg = ContactMessage(
            name="Jane",
            email="jane@test.com",
            message="Hello",
        )
        db_session.add(msg)
        db_session.commit()

        saved = db_session.query(ContactMessage).first()
        assert saved.id is not None
        assert saved.subject is None
        assert saved.ip_address is None
        assert saved.user_agent is None
        assert saved.is_read is False
        assert saved.created_at is not None

    def test_mark_message_as_read(self, db_session):
        msg = ContactMessage(
            name="Test",
            email="test@test.com",
            message="Test message",
            is_read=False,
        )
        db_session.add(msg)
        db_session.commit()

        msg.is_read = True
        db_session.commit()

        saved = db_session.query(ContactMessage).first()
        assert saved.is_read is True

    def test_multiple_contact_messages(self, db_session):
        for i in range(3):
            msg = ContactMessage(
                name=f"User {i}",
                email=f"user{i}@test.com",
                message=f"Message {i}",
            )
            db_session.add(msg)
        db_session.commit()

        messages = db_session.query(ContactMessage).all()
        assert len(messages) == 3
        assert messages[0].name == "User 0"
        assert messages[2].email == "user2@test.com"

    def test_contact_message_long_message(self, db_session):
        long_text = "A" * 5000
        msg = ContactMessage(
            name="Long Msg User",
            email="long@test.com",
            message=long_text,
        )
        db_session.add(msg)
        db_session.commit()

        saved = db_session.query(ContactMessage).first()
        assert len(saved.message) == 5000
        assert saved.message == long_text
