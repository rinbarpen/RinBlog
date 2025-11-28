from __future__ import annotations

from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from typing import List, Optional

from app.database import get_session
from app.services import comment_service, markdown_loader


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/posts/{slug}/comments", name="create_comment", response_model=None)
def create_comment(
    request: Request,
    slug: str,
    nickname: str = Form(default=""),
    content: str = Form(...),
    parent_id: Optional[str] = Form(default=None),
    images: Optional[List[UploadFile]] = File(default=None),
    session: Session = Depends(get_session),
):
    post = markdown_loader.get_post(slug)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # Convert empty string or None to None, then to int if valid
    parent_id_int = None
    if parent_id and parent_id.strip():
        try:
            parent_id_int = int(parent_id.strip())
        except (ValueError, TypeError):
            parent_id_int = None

    try:
        comment_service.create_comment(
            session, 
            slug=slug, 
            nickname=nickname, 
            content=content,
            images=images,
            parent_id=parent_id_int
        )
    except ValueError as exc:
        comments = comment_service.list_comment_views(session, slug)
        return templates.TemplateResponse(
            "post_detail.html",
            {
                "request": request,
                "post": post,
                "comments": comments,
                "form_error": str(exc),
                "comments_enabled": True,
            },
            status_code=400,
        )

    redirect_url = str(request.url_for("post_detail", slug=slug)) + "#comments"
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


