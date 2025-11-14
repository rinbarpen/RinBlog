from app.services import markdown_loader


def test_list_posts_excludes_daily():
    posts = markdown_loader.list_posts()
    assert posts, "Expected posts to be loaded"
    assert all(not post.is_daily for post in posts)
    slugs = {post.slug for post in posts}
    assert "daily-2025-11-13" not in slugs


def test_list_posts_includes_daily_when_requested():
    posts = markdown_loader.list_posts(include_daily=True)
    daily_slugs = {post.slug for post in posts if post.is_daily}
    assert "daily-2025-11-13" in daily_slugs


def test_groups_are_loaded_with_counts():
    groups = markdown_loader.list_groups()
    names = {group.name for group in groups}
    assert "Announcements" in names
    announcements = next(group for group in groups if group.name == "Announcements")
    assert announcements.post_count >= 1


