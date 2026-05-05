from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse
from app.utils.encryption import encrypt_value, decrypt_value, mask_key
from app.utils.security import get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/api-keys", tags=["api-keys"], redirect_slashes=False)


def _to_response(key: ApiKey) -> ApiKeyResponse:
    """Convert DB model to response schema with masked key."""
    try:
        decrypted = decrypt_value(key.key_encrypted)
        masked = mask_key(decrypted)
    except Exception:
        masked = "***" + str(key.id)

    return ApiKeyResponse(
        id=key.id,
        provider=key.provider,
        name=key.name,
        key_masked=masked,
        is_active=key.is_active,
        created_at=key.created_at,
        updated_at=key.updated_at,
    )


@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return [_to_response(k) for k in keys]


@router.get("/{key_id}", response_model=ApiKeyResponse)
def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return _to_response(key)


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    encrypted = encrypt_value(data.key)
    key = ApiKey(
        provider=data.provider.lower(),
        name=data.name,
        key_encrypted=encrypted,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return _to_response(key)


@router.put("/{key_id}", response_model=ApiKeyResponse)
def update_api_key(
    key_id: int,
    data: ApiKeyUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    if data.name is not None:
        key.name = data.name
    if data.key is not None:
        key.key_encrypted = encrypt_value(data.key)
    if data.is_active is not None:
        key.is_active = data.is_active

    db.commit()
    db.refresh(key)
    return _to_response(key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(key)
    db.commit()
