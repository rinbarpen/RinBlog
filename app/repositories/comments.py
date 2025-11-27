from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from app.models.comment import Comment


def list_comments(session: Session, slug: str) -> List[Comment]:
    statement = select(Comment).where(Comment.post_slug == slug).order_by(Comment.created_at.asc())
    return list(session.exec(statement))


def create_comment(
    session: Session, *, slug: str, nickname: Optional[str], content: str, image_urls: Optional[List[str]] = None
) -> Comment:
    comment = Comment(post_slug=slug, nickname=nickname, content=content, image_urls=image_urls)
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


