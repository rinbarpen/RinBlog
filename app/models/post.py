from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(slots=True)
class BlogPost:
    slug: str
    title: str
    summary: str
    content_html: str
    content_raw: str
    excerpt: str
    date: datetime
    group_slug: Optional[str] = None
    group_label: Optional[str] = None
    group_description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_daily: bool = False
    lang: str = "en"
    column: Optional[str] = None
    subcolumn: Optional[str] = None
    pinned: bool = False

    @property
    def display_date(self) -> str:
        return self.date.strftime("%b %d, %Y")


@dataclass(slots=True)
class GroupSummary:
    slug: str
    name: str
    description: Optional[str] = None
    post_count: int = 0


