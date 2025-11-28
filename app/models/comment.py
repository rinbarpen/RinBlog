from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_slug: str = Field(index=True, max_length=200)
    nickname: Optional[str] = Field(default=None, max_length=50)
    content: str = Field(min_length=1, max_length=1000)
    image_urls: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    parent_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class CommentView:
    comment_id: int
    display_name: str
    content: str
    display_time: str
    image_urls: List[str]
    children: List["CommentView"]

    @classmethod
    def from_model(cls, comment: Comment) -> "CommentView":
        nickname = comment.nickname.strip() if comment.nickname else ""
        display_name = nickname or "Anonymous"
        display_time = comment.created_at.strftime("%Y-%m-%d %H:%M")
        
        # Parse image_urls from JSON string or list
        image_urls = []
        if comment.image_urls:
            if isinstance(comment.image_urls, str):
                try:
                    image_urls = json.loads(comment.image_urls)
                except (json.JSONDecodeError, TypeError):
                    # Fallback: treat as single URL (backward compatibility)
                    if comment.image_urls:
                        image_urls = [comment.image_urls]
            elif isinstance(comment.image_urls, list):
                image_urls = comment.image_urls
        
        return cls(
            comment_id=comment.id or 0,
            display_name=display_name,
            content=comment.content,
            display_time=display_time,
            image_urls=image_urls or [],
            children=[],
        )


