from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session

from app.models.comment import CommentView
from app.repositories import comments as comment_repo


MAX_CONTENT_LENGTH = 1000
MAX_NICKNAME_LENGTH = 50


def list_comment_views(session: Session, slug: str) -> List[CommentView]:
    records = comment_repo.list_comments(session, slug)
    return [CommentView.from_model(record) for record in records]


def create_comment(session: Session, slug: str, nickname: Optional[str], content: str) -> CommentView:
    safe_nickname = (nickname or "").strip()
    safe_content = (content or "").strip()

    if not safe_content:
        raise ValueError("Comment cannot be empty.")

    if len(safe_content) > MAX_CONTENT_LENGTH:
        raise ValueError("Comment is too long.")

    if safe_nickname and len(safe_nickname) > MAX_NICKNAME_LENGTH:
        raise ValueError("Nickname is too long.")

    record = comment_repo.create_comment(
        session,
        slug=slug,
        nickname=safe_nickname or None,
        content=safe_content,
    )
    return CommentView.from_model(record)


