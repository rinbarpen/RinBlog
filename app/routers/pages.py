from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from typing import List, Optional

from fastapi import Query

from app.database import get_session
from app.models.post import BlogPost
from app.services import markdown_loader, tag_collections
from app.services import comment_service, i18n
from app.services.tag_collections import TagCollection, _read_collections_file


router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_language(lang: Optional[str] = Query(None, alias="lang")) -> str:
    """Get current language from query parameter or default."""
    return i18n.normalize_lang(lang)


@router.get("/", response_class=HTMLResponse, name="homepage")
def homepage(request: Request, lang: str = Depends(get_language)) -> HTMLResponse:
    all_posts = markdown_loader.list_posts(include_daily=False)
    posts = markdown_loader.filter_by_language(all_posts, lang)
    groups = markdown_loader.list_groups()
    all_daily = markdown_loader.list_daily_posts()
    latest_daily = next((p for p in all_daily if p.lang == lang), None) or (all_daily[0] if all_daily else None)
    columns = markdown_loader.list_columns()

    posts_with_badges = [
        (post, tag_collections.build_badges(post.tags))
        for post in posts
    ]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "posts": posts,
            "posts_badges": posts_with_badges,
            "groups": groups,
            "latest_daily": latest_daily,
            "columns": columns,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


@router.get("/groups/{group_slug}", response_class=HTMLResponse, name="group_posts")
def group_posts(request: Request, group_slug: str, lang: str = Depends(get_language)) -> HTMLResponse:
    group = markdown_loader.get_group_by_slug(group_slug)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    all_posts = markdown_loader.list_posts_by_group(group_slug)
    posts = markdown_loader.filter_by_language(all_posts, lang)
    posts_badges = [
        (post, tag_collections.build_badges(post.tags))
        for post in posts
    ]
    return templates.TemplateResponse(
        "group.html",
        {
            "request": request,
            "group": group,
            "posts": posts,
            "posts_badges": posts_badges,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


@router.get("/posts/{slug}", response_class=HTMLResponse, name="post_detail")
def post_detail(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_language),
) -> HTMLResponse:
    post = markdown_loader.get_post(slug)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    comments = comment_service.list_comment_views(session, slug)
    tag_badges = tag_collections.build_badges(post.tags)
    return templates.TemplateResponse(
        "post_detail.html",
        {
            "request": request,
            "post": post,
            "comments": comments,
            "form_error": None,
            "comments_enabled": True,
            "tag_badges": tag_badges,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


@router.get("/daily", response_class=HTMLResponse, name="daily_posts")
def daily_posts(request: Request, lang: str = Depends(get_language)) -> HTMLResponse:
    all_posts = markdown_loader.list_daily_posts()
    posts = markdown_loader.filter_by_language(all_posts, lang)
    posts_with_badges = [
        (post, tag_collections.build_badges(post.tags))
        for post in posts
    ]
    return templates.TemplateResponse(
        "daily.html",
        {
            "request": request,
            "posts": posts,
            "posts_badges": posts_with_badges,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


@router.get("/collections/{collection_slug}", response_class=HTMLResponse, name="collection_posts")
def collection_posts(request: Request, collection_slug: str, lang: str = Depends(get_language)) -> HTMLResponse:
    collections_data = _read_collections_file()
    collection_info: Optional[TagCollection] = None
    matching_tags: List[str] = []
    
    for entry in collections_data:
        slug = str(entry.get("slug") or "").strip() or str(entry.get("name") or "").lower().replace(" ", "-")
        if slug == collection_slug:
            name = str(entry.get("name") or "").strip()
            if name:
                color = entry.get("color")
                if isinstance(color, str):
                    color = color.strip() or None
                description = entry.get("description")
                if isinstance(description, str):
                    description = description.strip() or None
                collection_info = TagCollection(slug=slug, name=name, description=description, color=color)
                tags = entry.get("tags") or []
                if isinstance(tags, str):
                    tags = [tags]
                matching_tags = [str(t).strip() for t in tags if isinstance(t, str) and t.strip()]
            break
    
    if collection_info is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    all_matching_posts: List[BlogPost] = []
    seen_slugs = set()
    for tag in matching_tags:
        for post in markdown_loader.list_posts_by_tag(tag):
            if post.slug not in seen_slugs:
                all_matching_posts.append(post)
                seen_slugs.add(post.slug)
    
    all_matching_posts.sort(key=lambda p: p.date, reverse=True)
    posts = markdown_loader.filter_by_language(all_matching_posts, lang)
    posts_with_badges = [
        (post, tag_collections.build_badges(post.tags))
        for post in posts
    ]
    
    return templates.TemplateResponse(
        "collection.html",
        {
            "request": request,
            "collection": collection_info,
            "posts": posts,
            "posts_badges": posts_with_badges,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


@router.get("/columns/{column}", response_class=HTMLResponse, name="column_posts")
def column_posts(request: Request, column: str, lang: str = Depends(get_language)) -> HTMLResponse:
    """List posts in a column."""
    all_posts = markdown_loader.list_posts_by_column(column)
    posts = markdown_loader.filter_by_language(all_posts, lang)
    subcolumns = markdown_loader.list_subcolumns(column)
    
    posts_with_badges = [
        (post, tag_collections.build_badges(post.tags))
        for post in posts
    ]
    
    return templates.TemplateResponse(
        "column.html",
        {
            "request": request,
            "column": column,
            "subcolumns": subcolumns,
            "posts": posts,
            "posts_badges": posts_with_badges,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


@router.get("/columns/{column}/{subcolumn}", response_class=HTMLResponse, name="subcolumn_posts")
def subcolumn_posts(request: Request, column: str, subcolumn: str, lang: str = Depends(get_language)) -> HTMLResponse:
    """List posts in a subcolumn."""
    all_posts = markdown_loader.list_posts_by_column(column, subcolumn)
    posts = markdown_loader.filter_by_language(all_posts, lang)
    
    posts_with_badges = [
        (post, tag_collections.build_badges(post.tags))
        for post in posts
    ]
    
    return templates.TemplateResponse(
        "subcolumn.html",
        {
            "request": request,
            "column": column,
            "subcolumn": subcolumn,
            "posts": posts,
            "posts_badges": posts_with_badges,
            "current_lang": lang,
            "available_langs": i18n.SUPPORTED_LANGUAGES,
        },
    )


