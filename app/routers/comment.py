from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import comment as comment_service

router = APIRouter(
    prefix="/comments",
    tags=["comment"],
)

@router.post("/add")
def create_comment(
    db: Session = Depends(get_db),
    body: str = "",
    bus_line_id: int = None
):
    return comment_service.add_comment(db, body, bus_line_id)

@router.get("/tempo-add")
def create_comment(
    db: Session = Depends(get_db),
    body: str = "",
    bus_line_id: int = None
):
    return comment_service.add_comment(db, body, bus_line_id)

@router.get("/fetch")
def fetch_comments(
    db: Session = Depends(get_db),
    bus_line_id: int | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    return comment_service.fetch_comments(
        db, bus_line_id, page, limit
    )

