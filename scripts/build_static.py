from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).resolve().parent.parent

import sys

sys.path.insert(0, str(BASE_DIR))

import sys

sys.path.insert(0, str(BASE_DIR))

from app.services import markdown_loader, tag_collections
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DEFAULT_OUTPUT = BASE_DIR / "site"


@dataclass
class StaticRequest:
    url_builder: Callable[[str, Dict[str, str]], str]

    def url_for(self, name: str, **params: str) -> str:
        return self.url_builder(name, params)


def build_url_factory(base_url: str) -> Callable[[str, Dict[str, str]], str]:
    base = "/" if not base_url else f"/{base_url.strip('/')}/"

    def builder(name: str, params: Dict[str, str]) -> str:
        if name == "homepage":
            path = ""
        elif name == "daily_posts":
            path = "daily/"
        elif name == "post_detail":
            slug = params["slug"]
            path = f"posts/{slug}/"
        elif name == "group_posts":
            slug = params["group_slug"]
            path = f"groups/{slug}/"
        elif name == "collection_posts":
            slug = params["collection_slug"]
            path = f"collections/{slug}/"
        elif name == "static":
            static_path = params.get("path", "")
            if static_path.startswith("/"):
                static_path = static_path[1:]
            path = f"static/{static_path}"
        else:
            path = ""
        return f"{base}{path}"

    return builder


def prepare_environment(url_builder: Callable[[str, Dict[str, str]], str]) -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["url_for"] = lambda name, **params: url_builder(name, params)
    return env


def ensure_output_dir(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "posts").mkdir()
    (output / "groups").mkdir()
    (output / "daily").mkdir()
    shutil.copytree(STATIC_DIR, output / "static", dirs_exist_ok=True)
    (output / ".nojekyll").write_text("", encoding="utf-8")


def render_template(env: Environment, template_name: str, destination: Path, context: Dict) -> None:
    template = env.get_template(template_name)
    html = template.render(context)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")


def build_site(output_dir: Path, base_url: str) -> None:
    markdown_loader.refresh_cache()
    tag_collections.refresh()
    url_builder = build_url_factory(base_url)
    env = prepare_environment(url_builder)

    request = StaticRequest(url_builder)

    ensure_output_dir(output_dir)

    posts = markdown_loader.list_posts(include_daily=True)
    regular_posts = [post for post in posts if not post.is_daily]
    regular_with_badges = [(post, tag_collections.build_badges(post.tags)) for post in regular_posts]
    groups = markdown_loader.list_groups()
    latest_daily = markdown_loader.get_latest_daily()
    daily_posts = markdown_loader.list_daily_posts()
    daily_with_badges = [(post, tag_collections.build_badges(post.tags)) for post in daily_posts]

    render_template(
        env,
        "index.html",
        output_dir / "index.html",
        {
            "request": request,
            "posts": regular_posts,
            "posts_badges": regular_with_badges,
            "groups": groups,
            "latest_daily": latest_daily,
            "comments_enabled": False,
        },
    )

    render_template(
        env,
        "daily.html",
        output_dir / "daily" / "index.html",
        {
            "request": request,
            "posts": daily_posts,
            "posts_badges": daily_with_badges,
            "comments_enabled": False,
        },
    )

    for group in groups:
        group_posts = markdown_loader.list_posts_by_group(group.slug)
        render_template(
            env,
            "group.html",
            output_dir / "groups" / group.slug / "index.html",
            {
                "request": request,
                "group": group,
                "posts": group_posts,
                "posts_badges": [
                    (post, tag_collections.build_badges(post.tags))
                    for post in group_posts
                ],
                "comments_enabled": False,
            },
        )

    from app.services.tag_collections import _read_collections_file, TagCollection
    collections_data = _read_collections_file()
    (output_dir / "collections").mkdir(exist_ok=True)
    for entry in collections_data:
        slug = str(entry.get("slug") or "").strip() or str(entry.get("name") or "").lower().replace(" ", "-")
        name = str(entry.get("name") or "").strip()
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
        matching_tags = [str(t).strip() for t in tags if isinstance(t, str) and t.strip()]
        all_matching_posts = []
        seen_slugs = set()
        for tag in matching_tags:
            for post in markdown_loader.list_posts_by_tag(tag):
                if post.slug not in seen_slugs:
                    all_matching_posts.append(post)
                    seen_slugs.add(post.slug)
        all_matching_posts.sort(key=lambda p: p.date, reverse=True)
        render_template(
            env,
            "collection.html",
            output_dir / "collections" / slug / "index.html",
            {
                "request": request,
                "collection": collection,
                "posts": all_matching_posts,
                "posts_badges": [
                    (post, tag_collections.build_badges(post.tags))
                    for post in all_matching_posts
                ],
                "comments_enabled": False,
            },
        )

    for post in posts:
        render_template(
            env,
            "post_detail.html",
            output_dir / "posts" / post.slug / "index.html",
            {
                "request": request,
                "post": post,
                "comments": [],
                "form_error": None,
                "comments_enabled": False,
                "tag_badges": tag_collections.build_badges(post.tags),
            },
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build static HTML snapshot for GitHub Pages.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="输出目录（默认: ./site）")
    parser.add_argument("--base-url", type=str, default="", help="GitHub Pages 子路径，例如 repo 名称。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_site(args.output.resolve(), args.base_url)


if __name__ == "__main__":
    main()


