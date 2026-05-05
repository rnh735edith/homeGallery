from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings, Settings
from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user as _get_current_user

database_dependency = Depends(get_db)
current_user_dependency = Depends(_get_current_user)
config_dependency = Depends(get_settings)
