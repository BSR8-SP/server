from sqlalchemy.orm import Session
from app.models.comment import Comment
from fastapi import HTTPException

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

def interact_with_comment(db: Session, comment_id: int, interaction_type: str):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )
    
    if interaction_type not in ("positive", "negative"):
        raise HTTPException(
            status_code=400,
            detail="Invalid interaction type",
        )

    if interaction_type == "positive":
        comment.interactions_positive += 1
    elif interaction_type == "negative":
        comment.interactions_negative += 1
    else:
        return {"error": "Invalid interaction type"}

    db.commit()
    db.refresh(comment)

    return comment