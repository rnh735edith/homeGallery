import time
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.contact import ContactMessage
from app.schemas.contact import ContactMessageCreate, ContactMessageResponse
from app.utils.security import get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/contact", tags=["contact"], redirect_slashes=False)

_rate_limit_store: dict = {}
RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 15 * 60


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    key = ip
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    _rate_limit_store[key] = [
        t for t in _rate_limit_store[key] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_store[key]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many submissions. Try again later.")
    _rate_limit_store[key].append(now)


def _to_response(msg: ContactMessage) -> ContactMessageResponse:
    return ContactMessageResponse(
        id=msg.id,
        name=msg.name,
        email=msg.email,
        subject=msg.subject,
        message=msg.message,
        ip_address=msg.ip_address,
        user_agent=msg.user_agent,
        is_read=msg.is_read,
        created_at=msg.created_at,
    )


@router.post("", response_model=ContactMessageResponse, status_code=status.HTTP_201_CREATED)
def submit_contact_message(
    data: ContactMessageCreate,
    db: Session = Depends(get_db),
    ip_address: str = None,
    user_agent: str = None,
    request: Request = None,
):
    ip = ip_address or (request.client.host if request and request.client else None)
    _check_rate_limit(ip)
    ua = user_agent or (request.headers.get("user-agent") if request else None)

    msg = ContactMessage(
        name=data.name,
        email=data.email,
        subject=data.subject,
        message=data.message,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _to_response(msg)


@router.get("/messages", response_model=List[ContactMessageResponse])
def list_contact_messages(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    messages = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()
    return [_to_response(m) for m in messages]


@router.get("/messages/{message_id}", response_model=ContactMessageResponse)
def get_contact_message(
    message_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return _to_response(msg)


@router.put("/messages/{message_id}/read", response_model=ContactMessageResponse)
def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.is_read = True
    db.commit()
    db.refresh(msg)
    return _to_response(msg)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact_message(
    message_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
