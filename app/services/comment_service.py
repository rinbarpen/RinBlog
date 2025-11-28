from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Any

from sqlmodel import Session

from app.models.comment import CommentView
from app.repositories import comments as comment_repo


MAX_CONTENT_LENGTH = 1000
MAX_NICKNAME_LENGTH = 50
UPLOAD_DIR = Path("static/uploads/comments")


def list_comment_views(session: Session, slug: str) -> List[CommentView]:
    records = comment_repo.list_comments(session, slug)
    # Convert all to views first
    all_views = [CommentView.from_model(record) for record in records]
    
    # Build a map of id -> view
    view_map = {view.comment_id: view for view in all_views}
    
    # Separate roots and children
    roots = []
    for record, view in zip(records, all_views):
        if record.parent_id and record.parent_id in view_map:
            parent = view_map[record.parent_id]
            parent.children.append(view)
        else:
            roots.append(view)
            
    return roots


def save_upload_file(upload_file: Any) -> Optional[str]:
    """
    Save an UploadFile to the static uploads directory and return the relative URL.
    Using Any for upload_file to avoid importing FastAPI/Starlette types here if possible,
    but in practice it will be an UploadFile.
    """
    if not upload_file or not upload_file.filename:
        return None
    
    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    ext = Path(upload_file.filename).suffix
    if not ext:
        ext = ".jpg" # default fallback
        
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name
    
    # Save file
    # Note: If this is called from an async route, we might want to use async read/write,
    # but here we are doing synchronous file I/O.
    # For UploadFile, we can use .file.read() or .file object.
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()
        
    # Return URL path relative to static root (handled by StaticFiles mount)
    # static is mounted at /static
    return f"/static/uploads/comments/{unique_name}"


def create_comment(
    session: Session, 
    slug: str, 
    nickname: Optional[str], 
    content: str, 
    images: Optional[List[Any]] = None,
    parent_id: Optional[int] = None
) -> CommentView:
    safe_nickname = (nickname or "").strip()
    safe_content = (content or "").strip()

    if not safe_content:
        raise ValueError("Comment cannot be empty.")

    if len(safe_content) > MAX_CONTENT_LENGTH:
        raise ValueError("Comment is too long.")

    if safe_nickname and len(safe_nickname) > MAX_NICKNAME_LENGTH:
        raise ValueError("Nickname is too long.")

    image_urls = []
    if images:
        for image in images:
            if not image or not image.filename:
                continue
            # Validate image (basic check)
            if not image.content_type.startswith(("image/", "application/octet-stream")):
                raise ValueError("Invalid file type. Only images are allowed.")
            
            image_url = save_upload_file(image)
            if image_url:
                image_urls.append(image_url)

    record = comment_repo.create_comment(
        session,
        slug=slug,
        nickname=safe_nickname or None,
        content=safe_content,
        image_urls=image_urls if image_urls else None,
        parent_id=parent_id,
    )
    return CommentView.from_model(record)


