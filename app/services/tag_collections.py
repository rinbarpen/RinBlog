from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
COLLECTIONS_PATHS = [
    BASE_DIR / "content" / "tag_collections.yaml",
    BASE_DIR / "content" / "tag_collections.yml",
    BASE_DIR / "content" / "tag_collections.json",
]


@dataclass(slots=True)
class TagCollection:
    slug: str
    name: str
    description: Optional[str]
    color: Optional[str]


@dataclass(slots=True)
class TagBadge:
    tag: str
    label: str
    collection: Optional[TagCollection]


_tag_to_collection: Dict[str, TagCollection] = {}
_loaded = False


def _read_collections_file() -> List[dict]:
    for path in COLLECTIONS_PATHS:
        if path.exists():
            try:
                if path.suffix in {".yaml", ".yml"}:
                    with path.open("r", encoding="utf-8") as fp:
                        data = yaml.safe_load(fp) or {}
                else:
                    data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to load tag collections from %s: %s", path, exc)
                return []

            collections = data.get("collections", [])
            if not isinstance(collections, list):
                logger.warning("tag collections file %s is not in expected format", path)
                return []
            return collections
    return []


def _ensure_loaded() -> None:
    global _loaded, _tag_to_collection
    if _loaded:
        return
    mapping: Dict[str, TagCollection] = {}
    for entry in _read_collections_file():
        name = str(entry.get("name") or "").strip()
        slug = str(entry.get("slug") or "").strip() or name.lower().replace(" ", "-")
        if not name:
            continue
        color = entry.get("color")
        if isinstance(color, str):
            color = color.strip() or None
        description = entry.get("description")
        if isinstance(description, str):
            description = description.strip() or None
        collection = TagCollection(slug=slug, name=name, description=description, color=color)
        tags = entry.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        for raw_tag in tags:
            if not isinstance(raw_tag, str):
                continue
            tag = raw_tag.strip()
            if not tag:
                continue
            mapping[tag.lower()] = collection
    _tag_to_collection = mapping
    _loaded = True


def refresh() -> None:
    """Reload collection mapping (used on startup)."""
    global _loaded
    _loaded = False
    _ensure_loaded()


def build_badges(tags: List[str]) -> List[TagBadge]:
    _ensure_loaded()
    badges: List[TagBadge] = []
    for tag in tags:
        normalized = tag.lower()
        collection = _tag_to_collection.get(normalized)
        badges.append(
            TagBadge(
                tag=tag,
                label=collection.name if collection else tag,
                collection=collection,
            )
        )
    return badges


