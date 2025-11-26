from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import frontmatter
from markdown_it import MarkdownIt

from app.models.post import BlogPost, GroupSummary


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = BASE_DIR / "content" / "posts"

_markdown = MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough").enable("fence")

_posts_index: Dict[str, BlogPost] = {}
_ordered_posts: List[BlogPost] = []
_groups_index: Dict[str, GroupSummary] = {}
_posts_by_group: Dict[str, List[BlogPost]] = {}
_daily_posts: List[BlogPost] = []


def refresh_cache() -> None:
    """Load all markdown posts into memory."""
    global _posts_index, _ordered_posts, _groups_index, _posts_by_group, _daily_posts

    if not CONTENT_DIR.exists():
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        _clear_memory()
        return

    posts: List[BlogPost] = []
    groups: Dict[str, GroupSummary] = {}

    for path in sorted(CONTENT_DIR.glob("*.md")):
        try:
            post = _load_post(path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to load post %s: %s", path, exc)
            continue

        if post is None:
            continue

        posts.append(post)

        if post.group_slug:
            summary = groups.get(post.group_slug)
            if summary is None:
                summary = GroupSummary(
                    slug=post.group_slug,
                    name=post.group_label or post.group_slug.replace("-", " ").title(),
                    description=post.group_description,
                    post_count=0,
                )
                groups[post.group_slug] = summary

            summary.post_count += 1
            if post.group_description and not summary.description:
                summary.description = post.group_description

    posts.sort(key=lambda item: item.date, reverse=True)
    _ordered_posts = posts
    _posts_index = {post.slug: post for post in posts}
    _daily_posts = [post for post in posts if post.is_daily]

    grouped: Dict[str, List[BlogPost]] = {}
    for post in posts:
        if post.group_slug:
            grouped.setdefault(post.group_slug, []).append(post)
    _posts_by_group = grouped

    _groups_index = groups


def list_posts(*, include_daily: bool = False) -> List[BlogPost]:
    """Return posts sorted by date."""
    if include_daily:
        return list(_ordered_posts)
    return [post for post in _ordered_posts if not post.is_daily]


def get_post(slug: str) -> Optional[BlogPost]:
    return _posts_index.get(slug)


def get_latest_daily() -> Optional[BlogPost]:
    return _daily_posts[0] if _daily_posts else None


def list_daily_posts() -> List[BlogPost]:
    return list(_daily_posts)


def list_groups() -> List[GroupSummary]:
    groups = list(_groups_index.values())
    groups.sort(key=lambda item: item.name.lower())
    return groups


def get_group_by_slug(group_slug: str) -> Optional[GroupSummary]:
    return _groups_index.get(group_slug)


def list_posts_by_group(group_slug: str) -> List[BlogPost]:
    return list(_posts_by_group.get(group_slug, []))


def list_posts_by_tag(tag: str) -> List[BlogPost]:
    """List posts that contain the given tag (case-insensitive)."""
    normalized = tag.lower().strip()
    if not normalized:
        return []
    matching: List[BlogPost] = []
    for post in _ordered_posts:
        if any(t.lower() == normalized for t in post.tags):
            matching.append(post)
    return matching


def filter_by_language(posts: List[BlogPost], lang: str) -> List[BlogPost]:
    """Filter posts by language code."""
    return [post for post in posts if post.lang == lang]


def _clear_memory() -> None:
    global _posts_index, _ordered_posts, _groups_index, _posts_by_group, _daily_posts
    _posts_index = {}
    _ordered_posts = []
    _groups_index = {}
    _posts_by_group = {}
    _daily_posts = []


def _load_post(path: Path) -> Optional[BlogPost]:
    parsed = frontmatter.load(path)
    meta = parsed.metadata or {}
    content = parsed.content.strip()

    if not content:
        logger.warning("Skipping empty post: %s", path)
        return None

    title = str(meta.get("title") or _title_from_path(path))
    slug = str(meta.get("slug") or _slugify(path.stem))

    raw_date = meta.get("date")
    timestamp = _parse_date(raw_date) or _file_modified_at(path)

    group_slug: Optional[str] = None
    group_label: Optional[str] = None
    group_description: Optional[str] = None

    group_meta = meta.get("group")
    if isinstance(group_meta, str):
        group_label = group_meta.strip()
        group_slug = _slugify(group_label)
    elif isinstance(group_meta, dict):
        group_label = str(group_meta.get("name") or group_meta.get("label") or "")
        group_slug = str(group_meta.get("slug") or _slugify(group_label) or "") or None
        group_description = group_meta.get("description")
        if group_label:
            group_label = group_label.strip()
        if group_slug:
            group_slug = group_slug.strip()
        if isinstance(group_description, str):
            group_description = group_description.strip()

    content_html = _markdown.render(content)
    summary = _extract_summary(meta, content)
    excerpt = _extract_excerpt_html(content_html)

    tags = _normalize_tags(meta.get("tags"))
    is_daily = bool(meta.get("daily")) or (meta.get("type") == "daily")
    
    from app.services.i18n import normalize_lang
    lang = normalize_lang(meta.get("lang") or meta.get("language"))

    return BlogPost(
        slug=slug,
        title=title,
        summary=summary,
        content_html=content_html,
        content_raw=content,
        excerpt=excerpt,
        date=timestamp,
        group_slug=group_slug,
        group_label=group_label,
        group_description=group_description,
        tags=tags,
        is_daily=is_daily,
        lang=lang,
    )


def _title_from_path(path: Path) -> str:
    return path.stem.replace("-", " ").title()


def _parse_date(value) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)

    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            logger.warning("Unrecognized date format '%s'", value)
            return None

    return None


def _file_modified_at(path: Path) -> datetime:
    stat = path.stat()
    return datetime.fromtimestamp(stat.st_mtime)


_slug_pattern = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = _slug_pattern.sub("-", normalized)
    normalized = normalized.strip("-")
    return normalized or "post"


def _extract_summary(meta: dict, content: str) -> str:
    summary = meta.get("summary") or meta.get("description")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    plain = re.sub(r"\s+", " ", content.strip())
    max_length = 160
    if len(plain) <= max_length:
        return plain
    return f"{plain[:max_length].rstrip()}..."


def _extract_excerpt_html(html: str) -> str:
    closing_index = html.find("</p>")
    if closing_index != -1:
        return html[: closing_index + len("</p>")]
    snippet = html[:280]
    if len(html) > 280:
        snippet = f"{snippet}..."
    return snippet


def _normalize_tags(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Iterable):
        tags: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                tags.append(item.strip())
        return tags
    return []


try:
    refresh_cache()
except Exception as exc:  # pylint: disable=broad-except
    logger.warning("Initial markdown load failed: %s", exc)



