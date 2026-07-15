from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.schemas.referee import RefereeCreate, RefereeRead, RefereeUpdate
from shared.database import get_db
from shared.models import ReferenceRequest, User
from shared.repositories import referees as referee_repo

router = APIRouter(prefix="/api/referees", tags=["referees"])


def _to_read(db: Session, referee) -> RefereeRead:
    count = len(list(db.scalars(select(ReferenceRequest).where(ReferenceRequest.referee_id == referee.id))))
    data = RefereeRead.model_validate(referee)
    data.request_count = count
    return data


@router.get("", response_model=list[RefereeRead])
def list_referees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RefereeRead]:
    return [_to_read(db, r) for r in referee_repo.list_by_user(db, current_user.id)]


@router.post("", response_model=RefereeRead, status_code=status.HTTP_201_CREATED)
def create_referee(
    body: RefereeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RefereeRead:
    referee = referee_repo.create(db, current_user.id, **body.model_dump())
    return _to_read(db, referee)


@router.patch("/{referee_id}", response_model=RefereeRead)
def update_referee(
    referee_id: int,
    body: RefereeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RefereeRead:
    referee = referee_repo.update(db, referee_id, current_user.id, **body.model_dump(exclude_unset=True))
    if referee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referee not found")
    return _to_read(db, referee)


@router.delete("/{referee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_referee(
    referee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    referee = referee_repo.get(db, referee_id, current_user.id)
    if referee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referee not found")
    active = db.scalar(
        select(ReferenceRequest).where(
            ReferenceRequest.referee_id == referee_id,
            ReferenceRequest.status.in_(["draft", "sent", "overdue"]),
        )
    )
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this referee has an active reference request — resolve it before deleting",
        )
    referee_repo.delete(db, referee_id, current_user.id)
