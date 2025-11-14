from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.database import get_session
from app.services import markdown_loader
from app.services import comment_service


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse, name="homepage")
def homepage(request: Request) -> HTMLResponse:
    posts = markdown_loader.list_posts(include_daily=False)
    groups = markdown_loader.list_groups()
    latest_daily = markdown_loader.get_latest_daily()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "posts": posts,
            "groups": groups,
            "latest_daily": latest_daily,
        },
    )


@router.get("/groups/{group_slug}", response_class=HTMLResponse, name="group_posts")
def group_posts(request: Request, group_slug: str) -> HTMLResponse:
    group = markdown_loader.get_group_by_slug(group_slug)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    posts = markdown_loader.list_posts_by_group(group_slug)
    return templates.TemplateResponse(
        "group.html",
        {
            "request": request,
            "group": group,
            "posts": posts,
        },
    )


@router.get("/posts/{slug}", response_class=HTMLResponse, name="post_detail")
def post_detail(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    post = markdown_loader.get_post(slug)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    comments = comment_service.list_comment_views(session, slug)
    return templates.TemplateResponse(
        "post_detail.html",
        {
            "request": request,
            "post": post,
            "comments": comments,
            "form_error": None,
            "comments_enabled": True,
        },
    )


@router.get("/daily", response_class=HTMLResponse, name="daily_posts")
def daily_posts(request: Request) -> HTMLResponse:
    posts = markdown_loader.list_daily_posts()
    return templates.TemplateResponse(
        "daily.html",
        {
            "request": request,
            "posts": posts,
        },
    )


