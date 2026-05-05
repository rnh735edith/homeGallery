import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.contact import ContactMessage
from app.models.user import User
from app.api.contact import (
    submit_contact_message,
    list_contact_messages,
    get_contact_message,
    mark_message_read,
    delete_contact_message,
)
from app.schemas.contact import ContactMessageCreate
from fastapi import HTTPException
from app.api.contact import _check_rate_limit, _rate_limit_store


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_admin():
    class MockUser:
        id = 1
        username = "admin"
        is_admin = True
    return MockUser()


@pytest.fixture(autouse=True)
def reset_rate_limit():
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


class TestContactApiPublic:
    def test_submit_contact_message(self, db_session):
        data = ContactMessageCreate(
            name="John Doe",
            email="john@example.com",
            subject="Question",
            message="How does this work?",
        )
        result = submit_contact_message(data, db_session, "192.168.1.1")

        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        assert result.subject == "Question"
        assert result.message == "How does this work?"
        assert result.ip_address == "192.168.1.1"
        assert result.is_read is False
        assert result.id is not None

    def test_submit_message_without_subject(self, db_session):
        data = ContactMessageCreate(
            name="Jane",
            email="jane@test.com",
            message="No subject",
        )
        result = submit_contact_message(data, db_session, "10.0.0.1")

        assert result.subject is None
        assert result.message == "No subject"

    def test_submit_message_captures_user_agent(self, db_session):
        data = ContactMessageCreate(
            name="User",
            email="user@test.com",
            message="With UA",
        )
        result = submit_contact_message(data, db_session, "1.2.3.4", "Mozilla/5.0")

        assert result.user_agent == "Mozilla/5.0"

    def test_rate_limit_blocks_excess_submissions(self, db_session):
        data = ContactMessageCreate(
            name="Spammer",
            email="spam@test.com",
            message="Spam",
        )
        ip = "10.10.10.10"

        for _ in range(3):
            submit_contact_message(data, db_session, ip)

        with pytest.raises(HTTPException) as exc:
            submit_contact_message(data, db_session, ip)
        assert exc.value.status_code == 429

    def test_rate_limit_per_ip_independent(self, db_session):
        data = ContactMessageCreate(
            name="User",
            email="user@test.com",
            message="Hello",
        )
        for ip in ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]:
            submit_contact_message(data, db_session, ip)

        assert len(db_session.query(ContactMessage).all()) == 4


class TestContactApiAdmin:
    def test_list_messages_empty(self, db_session, mock_admin):
        result = list_contact_messages(mock_admin, db_session)
        assert result == []

    def test_list_messages_with_data(self, db_session, mock_admin):
        for i in range(3):
            msg = ContactMessage(
                name=f"User {i}",
                email=f"user{i}@test.com",
                message=f"Message {i}",
            )
            db_session.add(msg)
        db_session.commit()

        result = list_contact_messages(mock_admin, db_session)
        assert len(result) == 3
        assert result[0].name == "User 0"

    def test_get_message(self, db_session, mock_admin):
        msg = ContactMessage(
            name="Alice",
            email="alice@test.com",
            message="Hello admin",
        )
        db_session.add(msg)
        db_session.commit()

        result = get_contact_message(msg.id, mock_admin, db_session)
        assert result.name == "Alice"
        assert result.message == "Hello admin"

    def test_get_message_not_found(self, db_session, mock_admin):
        with pytest.raises(HTTPException) as exc:
            get_contact_message(999, mock_admin, db_session)
        assert exc.value.status_code == 404

    def test_mark_message_read(self, db_session, mock_admin):
        msg = ContactMessage(
            name="Bob",
            email="bob@test.com",
            message="Please read this",
            is_read=False,
        )
        db_session.add(msg)
        db_session.commit()

        result = mark_message_read(msg.id, mock_admin, db_session)
        assert result.is_read is True

    def test_mark_message_read_not_found(self, db_session, mock_admin):
        with pytest.raises(HTTPException) as exc:
            mark_message_read(999, mock_admin, db_session)
        assert exc.value.status_code == 404

    def test_delete_message(self, db_session, mock_admin):
        msg = ContactMessage(
            name="Delete",
            email="del@test.com",
            message="Delete me",
        )
        db_session.add(msg)
        db_session.commit()
        msg_id = msg.id

        delete_contact_message(msg_id, mock_admin, db_session)

        remaining = db_session.query(ContactMessage).filter(ContactMessage.id == msg_id).first()
        assert remaining is None

    def test_delete_message_not_found(self, db_session, mock_admin):
        with pytest.raises(HTTPException) as exc:
            delete_contact_message(999, mock_admin, db_session)
        assert exc.value.status_code == 404
