from sqlalchemy.orm import Session
from app.models.comment import Comment

def add_comment(db: Session, body: str = "", bus_line_id: int = None):
    comment = Comment(
        body=body,
        bus_line_id=bus_line_id,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment

def fetch_comments(db: Session, bus_line_id: int | None = None, page: int = 1, limit: int = 10):
    query = db.query(Comment).order_by(Comment.id)

    if bus_line_id is not None:
        query = query.filter(Comment.bus_line_id == bus_line_id)

    offset = (page - 1) * limit
    comments = query.offset(offset).limit(limit).all()

    return comments 