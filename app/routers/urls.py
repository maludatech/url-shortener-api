from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import URL
from app.schemas.url import ShortenRequest, ShortenResponse
from app.short_code import generate_short_code

router = APIRouter(tags=["urls"])

_MAX_GENERATION_ATTEMPTS = 5


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
def shorten(payload: ShortenRequest, db: Session = Depends(get_db)) -> ShortenResponse:
    long_url = str(payload.long_url)

    for _ in range(_MAX_GENERATION_ATTEMPTS):
        code = generate_short_code()
        url = URL(short_code=code, long_url=long_url)
        db.add(url)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue

        db.refresh(url)
        return ShortenResponse(
            id=url.id,
            short_code=url.short_code,
            short_url=f"{settings.base_url}/{url.short_code}",
            long_url=url.long_url,
            click_count=url.click_count,
            created_at=url.created_at,
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique short code, please try again",
    )
