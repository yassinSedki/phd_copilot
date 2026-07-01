from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from shared.database import get_db
from shared.models import User

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = decode_access_token(creds.credentials)
    except PyJWTError:
        raise invalid
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise invalid
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise invalid
    user = db.get(User, user_id)
    if user is None:
        raise invalid
    return user
