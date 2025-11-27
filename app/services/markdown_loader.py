from __future__ import annotations

import logging
import re
import html
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import frontmatter
from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

from app.models.post import BlogPost, GroupSummary


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = BASE_DIR / "content"

_markdown = MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough").enable("fence")
_markdown.use(tasklists_plugin)

_posts_index: Dict[str, BlogPost] = {}
_ordered_posts: List[BlogPost] = []
_groups_index: Dict[str, GroupSummary] = {}
_posts_by_group: Dict[str, List[BlogPost]] = {}
_daily_posts: List[BlogPost] = []
_columns_index: Dict[str, Dict[str, List[BlogPost]]] = {}  # column -> subcolumn -> posts


def refresh_cache() -> None:
    """Load all markdown posts into memory."""
    global _posts_index, _ordered_posts, _groups_index, _posts_by_group, _daily_posts, _columns_index

    if not CONTENT_DIR.exists():
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        _clear_memory()
        return

    posts: List[BlogPost] = []
    groups: Dict[str, GroupSummary] = {}
    columns: Dict[str, Dict[str, List[BlogPost]]] = {}

    # Recursively scan all .md files in content directory
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        try:
            post = _load_post(path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to load post %s: %s", path, exc)
            continue

        if post is None:
            continue

        # Extract column and subcolumn from path
        # Path structure: content/posts/专栏名/小专栏名/文章.md
        relative_path = path.relative_to(CONTENT_DIR)
        parts = list(relative_path.parts)

        # If inside "posts" directory, treat "posts" as root
        if parts and parts[0] == "posts":
            parts.pop(0)
        
        if len(parts) >= 3:  # 专栏/小专栏/文章.md
            # Exclude daily/2025/... from being a column named "daily" with subcolumn "2025"
            # But we can still assign it if we want, just filter in nav.
            # However, let's be cleaner.
            if parts[0] != "daily":
                post.column = parts[0]
                post.subcolumn = parts[1]
        elif len(parts) == 2:  # 专栏/文章.md
            if parts[0] != "daily":
                post.column = parts[0]
                post.subcolumn = None
        # else: 根目录下的文件，column 和 subcolumn 为 None

        posts.append(post)

        # Index by column/subcolumn
        if post.column:
            if post.column not in columns:
                columns[post.column] = {}
            if post.subcolumn:
                if post.subcolumn not in columns[post.column]:
                    columns[post.column][post.subcolumn] = []
                columns[post.column][post.subcolumn].append(post)
            else:
                # Posts directly under column
                if "_root" not in columns[post.column]:
                    columns[post.column]["_root"] = []
                columns[post.column]["_root"].append(post)

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

    # Sort by pinned (desc), then date (desc)
    posts.sort(key=lambda item: (item.pinned, item.date), reverse=True)
    _ordered_posts = posts
    _posts_index = {post.slug: post for post in posts}
    _daily_posts = [post for post in posts if post.is_daily]

    grouped: Dict[str, List[BlogPost]] = {}
    for post in posts:
        if post.group_slug:
            grouped.setdefault(post.group_slug, []).append(post)
    _posts_by_group = grouped

    _groups_index = groups
    _columns_index = columns


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


def list_columns() -> List[str]:
    """List all column names."""
    return sorted(_columns_index.keys())


def list_subcolumns(column: str) -> List[str]:
    """List all subcolumn names for a given column."""
    if column not in _columns_index:
        return []
    subcolumns = [sc for sc in _columns_index[column].keys() if sc != "_root"]
    return sorted(subcolumns)


def get_navigation_structure() -> Dict[str, List[str]]:
    """Return a dictionary of column -> list[subcolumns] for navigation."""
    structure = {}
    for col, subcols in _columns_index.items():
        # Filter out _root and sort subcolumns
        subs = sorted([s for s in subcols.keys() if s != "_root"])
        structure[col] = subs
    # Sort columns alphabetically
    return dict(sorted(structure.items()))


def list_posts_by_column(column: str, subcolumn: Optional[str] = None) -> List[BlogPost]:
    """List posts in a column, optionally filtered by subcolumn."""
    if column not in _columns_index:
        return []
    
    if subcolumn:
        if subcolumn in _columns_index[column]:
            return list(_columns_index[column][subcolumn])
        return []
    
    # Return all posts in the column (from all subcolumns)
    all_posts: List[BlogPost] = []
    for subcol_posts in _columns_index[column].values():
        all_posts.extend(subcol_posts)
    all_posts.sort(key=lambda p: p.date, reverse=True)
    return all_posts


def _clear_memory() -> None:
    global _posts_index, _ordered_posts, _groups_index, _posts_by_group, _daily_posts, _columns_index
    _posts_index = {}
    _ordered_posts = []
    _groups_index = {}
    _posts_by_group = {}
    _daily_posts = []
    _columns_index = {}


def _load_post(path: Path) -> Optional[BlogPost]:
    parsed = frontmatter.load(path)
    meta = parsed.metadata or {}
    content = parsed.content.strip()

    if not content:
        logger.warning("Skipping empty post: %s", path)
        return None
    
    # Skip draft posts
    if meta.get("draft") or meta.get("published") is False:
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

    content_for_render, preview_map = _process_preview_shortcodes(content)
    content_html = _markdown.render(content_for_render)
    
    # Inject previews back into HTML
    for placeholder, preview_html in preview_map.items():
        content_html = content_html.replace(placeholder, preview_html)

    summary = _extract_summary(meta, content)
    excerpt = _extract_excerpt_html(content_html)

    tags = _normalize_tags(meta.get("tags"))
    pinned = bool(meta.get("pinned")) or bool(meta.get("pin"))
    
    # Check if daily based on metadata OR path
    is_daily_meta = bool(meta.get("daily")) or (meta.get("type") == "daily")
    is_daily_path = "daily" in path.parts
    is_daily = is_daily_meta or is_daily_path
    
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
        pinned=pinned,
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


def _process_preview_shortcodes(content: str) -> tuple[str, dict[str, str]]:
    """
    Find @[Preview](url) and @content/path:1-10 patterns.
    Replace them with placeholders and return a map of placeholder -> HTML.
    """
    preview_map = {}
    
    # 1. URL Previews: @[Preview](url)
    # Regex to capture url
    url_pattern = re.compile(r'@\[Preview\]\((https?://[^\)]+)\)')
    
    def url_replacer(match):
        url = match.group(1)
        placeholder = f"<!--PREVIEW_URL_{len(preview_map)}-->"
        # Generate a simple card HTML
        card_html = (
            f'<div class="link-preview-card">'
            f'  <a href="{url}" target="_blank" rel="noopener noreferrer">'
            f'    <div class="link-preview-info">'
            f'      <span class="link-preview-title">{html.escape(url)}</span>'
            f'      <span class="link-preview-domain">{html.escape(url.split("/")[2])}</span>'
            f'    </div>'
            f'  </a>'
            f'</div>'
        )
        preview_map[placeholder] = card_html
        return placeholder

    content = url_pattern.sub(url_replacer, content)

    # 2. Local File Previews: @content/path/to/file.md:10-20
    # Regex to capture path and optional line range
    file_pattern = re.compile(r'@(content/[a-zA-Z0-9_./-]+)(?::(\d+)-(\d+))?')

    def file_replacer(match):
        rel_path_str = match.group(1)
        start_line = match.group(2)
        end_line = match.group(3)
        
        file_path = BASE_DIR / rel_path_str
        if not file_path.exists() or not file_path.is_file():
            return match.group(0)  # Leave as is if file not found

        try:
            file_content = file_path.read_text(encoding="utf-8")
            lines = file_content.splitlines()
            
            if start_line and end_line:
                start = max(0, int(start_line) - 1)
                end = min(len(lines), int(end_line))
                snippet = "\n".join(lines[start:end])
                source_info = f"{rel_path_str}:{start_line}-{end_line}"
            else:
                snippet = file_content
                source_info = rel_path_str

            # Detect language from extension
            ext = file_path.suffix.lstrip(".").lower() or "text"
            
            # Render as code block or markdown quote depending on type?
            # Let's use a styled block
            placeholder = f"<!--PREVIEW_FILE_{len(preview_map)}-->"
            
            # We'll render the snippet as a code block to preserve formatting,
            # but wrap it in a container that shows the source path.
            # If it's markdown, we might want to render it? 
            # User said "HTML form", let's render as code block for clarity as it's a preview.
            
            block_html = (
                f'<div class="file-preview-card">'
                f'  <div class="file-preview-header">{html.escape(source_info)}</div>'
                f'  <pre><code class="language-{ext}">{html.escape(snippet)}</code></pre>'
                f'</div>'
            )
            preview_map[placeholder] = block_html
            return placeholder
            
        except Exception as e:
            logger.warning(f"Failed to read file preview {rel_path_str}: {e}")
            return match.group(0)

    content = file_pattern.sub(file_replacer, content)
    
    return content, preview_map


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



