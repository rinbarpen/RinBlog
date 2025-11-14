import pytest
from sqlmodel import Session, SQLModel, create_engine
from app.services import comment_service


def build_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_create_comment_persists_and_returns_view():
    with build_session() as session:
        view = comment_service.create_comment(session, slug="example-post", nickname="Alice", content="Hello there!")
        assert view.display_name == "Alice"
        stored = comment_service.list_comment_views(session, "example-post")
        assert len(stored) == 1
        assert stored[0].content == "Hello there!"


def test_create_comment_enforces_non_empty_content():
    with build_session() as session:
        with pytest.raises(ValueError):
            comment_service.create_comment(session, slug="example-post", nickname="", content="   ")


