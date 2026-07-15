from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.hashing import hash_password, verify_password
from app.auth.jwt import create_access_token
from shared.database import get_db
from shared.models import User
from shared.repositories import users as users_repo
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if users_repo.get_user_by_email(db, body.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    user = users_repo.create_user(db, body.email, hash_password(body.password))
    return TokenResponse(access_token=create_access_token(str(user.id)), is_onboarded=False)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = users_repo.get_user_by_email(db, body.email)
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    profile = users_repo.get_profile(db, user.id)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        is_onboarded=bool(profile and profile.is_onboarded),
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    profile = users_repo.get_profile(db, current_user.id)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_onboarded=bool(profile and profile.is_onboarded),
    )
