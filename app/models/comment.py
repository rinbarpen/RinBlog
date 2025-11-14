from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_slug: str = Field(index=True, max_length=200)
    nickname: Optional[str] = Field(default=None, max_length=50)
    content: str = Field(min_length=1, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class CommentView:
    display_name: str
    content: str
    display_time: str

    @classmethod
    def from_model(cls, comment: Comment) -> "CommentView":
        nickname = comment.nickname.strip() if comment.nickname else ""
        display_name = nickname or "Anonymous"
        display_time = comment.created_at.strftime("%Y-%m-%d %H:%M")
        return cls(display_name=display_name, content=comment.content, display_time=display_time)


