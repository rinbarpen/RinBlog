from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Iterator

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "rinblog.db"
DATABASE_PATH = Path(os.getenv("RINBLOG_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def check_schema_compatibility() -> None:
    """Check if database schema is compatible, warn if migration needed."""
    if not DATABASE_PATH.exists():
        return
    
    inspector = inspect(engine)
    if "comment" not in inspector.get_table_names():
        return
    
    columns = {col["name"]: col for col in inspector.get_columns("comment")}
    
    # Check if old schema exists (has image_url but not image_urls)
    if "image_url" in columns and "image_urls" not in columns:
        warnings.warn(
            "Database schema is outdated. The 'image_url' column needs to be migrated to 'image_urls'. "
            "Please delete the database file to recreate it with the new schema, or run a migration script. "
            f"Database location: {DATABASE_PATH}",
            UserWarning
        )


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    check_schema_compatibility()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


