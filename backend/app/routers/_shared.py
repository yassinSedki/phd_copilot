"""Small helpers shared across routers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shared.models import Application, User
from shared.repositories import applications as app_repo


def get_application_or_404(db: Session, current_user: User, application_id: int) -> Application:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    return app
