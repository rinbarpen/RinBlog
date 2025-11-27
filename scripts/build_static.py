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

from app.services import markdown_loader, i18n, tag_collections
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DEFAULT_OUTPUT = BASE_DIR / "site"


@dataclass
class StaticRequest:
    url_builder: Callable[[str, Dict[str, str]], str]

    @property
    def url(self):
        # Mock url object
        class Url:
            path = "/"
        return Url()

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
        elif name == "column_posts":
            column = params["column"]
            path = f"columns/{column}/"
        elif name == "subcolumn_posts":
            column = params["column"]
            subcolumn = params["subcolumn"]
            path = f"columns/{column}/{subcolumn}/"
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
    groups = markdown_loader.list_groups()
    columns = markdown_loader.list_columns()
    
    for lang in i18n.SUPPORTED_LANGUAGES:
        regular_posts = [post for post in posts if not post.is_daily]
        regular_posts = markdown_loader.filter_by_language(regular_posts, lang)
        regular_with_badges = [(post, tag_collections.build_badges(post.tags)) for post in regular_posts]
        all_daily = markdown_loader.list_daily_posts()
        latest_daily = next((p for p in all_daily if p.lang == lang), None) or (all_daily[0] if all_daily else None)
        daily_posts = markdown_loader.filter_by_language(all_daily, lang)
        daily_with_badges = [(post, tag_collections.build_badges(post.tags)) for post in daily_posts]

        output_path = output_dir / "index.html" if lang == i18n.DEFAULT_LANGUAGE else output_dir / f"index-{lang}.html"
        render_template(
            env,
            "index.html",
            output_path,
            {
                "request": request,
                "posts": regular_posts,
                "posts_badges": regular_with_badges,
                "groups": groups,
                "latest_daily": latest_daily,
                "columns": columns,
                "comments_enabled": False,
                "current_lang": lang,
                "available_langs": i18n.SUPPORTED_LANGUAGES,
            },
        )

        daily_output = output_dir / "daily" / ("index.html" if lang == i18n.DEFAULT_LANGUAGE else f"index-{lang}.html")
        render_template(
            env,
            "daily.html",
            daily_output,
            {
                "request": request,
                "posts": daily_posts,
                "posts_badges": daily_with_badges,
                "comments_enabled": False,
                "current_lang": lang,
                "available_langs": i18n.SUPPORTED_LANGUAGES,
            },
        )

    for group in groups:
        all_group_posts = markdown_loader.list_posts_by_group(group.slug)
        for lang in i18n.SUPPORTED_LANGUAGES:
            group_posts = markdown_loader.filter_by_language(all_group_posts, lang)
            group_output = output_dir / "groups" / group.slug / ("index.html" if lang == i18n.DEFAULT_LANGUAGE else f"index-{lang}.html")
            render_template(
                env,
                "group.html",
                group_output,
                {
                    "request": request,
                    "group": group,
                    "posts": group_posts,
                    "posts_badges": [
                        (post, tag_collections.build_badges(post.tags))
                        for post in group_posts
                    ],
                    "comments_enabled": False,
                    "current_lang": lang,
                    "available_langs": i18n.SUPPORTED_LANGUAGES,
                },
            )

    # Generate column and subcolumn pages
    for column in columns:
        all_column_posts = markdown_loader.list_posts_by_column(column)
        subcolumns = markdown_loader.list_subcolumns(column)
        
        for lang in i18n.SUPPORTED_LANGUAGES:
            column_posts = markdown_loader.filter_by_language(all_column_posts, lang)
            column_output = output_dir / "columns" / column / ("index.html" if lang == i18n.DEFAULT_LANGUAGE else f"index-{lang}.html")
            render_template(
                env,
                "column.html",
                column_output,
                {
                    "request": request,
                    "column": column,
                    "subcolumns": subcolumns,
                    "posts": column_posts,
                    "posts_badges": [
                        (post, tag_collections.build_badges(post.tags))
                        for post in column_posts
                    ],
                    "comments_enabled": False,
                    "current_lang": lang,
                    "available_langs": i18n.SUPPORTED_LANGUAGES,
                },
            )
        
        # Generate subcolumn pages
        for subcolumn in subcolumns:
            all_subcolumn_posts = markdown_loader.list_posts_by_column(column, subcolumn)
            for lang in i18n.SUPPORTED_LANGUAGES:
                subcolumn_posts = markdown_loader.filter_by_language(all_subcolumn_posts, lang)
                subcolumn_output = output_dir / "columns" / column / subcolumn / ("index.html" if lang == i18n.DEFAULT_LANGUAGE else f"index-{lang}.html")
                render_template(
                    env,
                    "subcolumn.html",
                    subcolumn_output,
                    {
                        "request": request,
                        "column": column,
                        "subcolumn": subcolumn,
                        "posts": subcolumn_posts,
                        "posts_badges": [
                            (post, tag_collections.build_badges(post.tags))
                            for post in subcolumn_posts
                        ],
                        "comments_enabled": False,
                        "current_lang": lang,
                        "available_langs": i18n.SUPPORTED_LANGUAGES,
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
        for lang in i18n.SUPPORTED_LANGUAGES:
            filtered_posts = markdown_loader.filter_by_language(all_matching_posts, lang)
            collection_output = output_dir / "collections" / slug / ("index.html" if lang == i18n.DEFAULT_LANGUAGE else f"index-{lang}.html")
            render_template(
                env,
                "collection.html",
                collection_output,
                {
                    "request": request,
                    "collection": collection,
                    "posts": filtered_posts,
                    "posts_badges": [
                        (post, tag_collections.build_badges(post.tags))
                        for post in filtered_posts
                    ],
                    "comments_enabled": False,
                    "current_lang": lang,
                    "available_langs": i18n.SUPPORTED_LANGUAGES,
                },
            )

    for post in posts:
        post_output = output_dir / "posts" / post.slug / ("index.html" if post.lang == i18n.DEFAULT_LANGUAGE else f"index-{post.lang}.html")
        render_template(
            env,
            "post_detail.html",
            post_output,
            {
                "request": request,
                "post": post,
                "comments": [],
                "form_error": None,
                "comments_enabled": False,
                "tag_badges": tag_collections.build_badges(post.tags),
                "current_lang": post.lang,
                "available_langs": i18n.SUPPORTED_LANGUAGES,
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


