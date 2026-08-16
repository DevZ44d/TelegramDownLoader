from __future__ import annotations

from config import settings
from instagram.utils import guess_extension, instagram_temp_dir, sanitize_component, unique_instagram_path
from utils.files import safe_remove


def test_sanitize_component_strips_path_traversal():
    assert ".." not in sanitize_component("../../etc/passwd")
    assert "/" not in sanitize_component("../../etc/passwd")


def test_sanitize_component_strips_windows_invalid_chars():
    result = sanitize_component('con:foo<bar>|baz?"*')
    for bad_char in '<>:"/\\|?*':
        assert bad_char not in result


def test_sanitize_component_falls_back_when_empty():
    assert sanitize_component("") == "instagram"
    assert sanitize_component(None) == "instagram"
    assert sanitize_component("...") == "instagram"


def test_guess_extension_prefers_mime_type():
    assert guess_extension("https://cdn.example/x", "image/png", "image") == ".png"


def test_guess_extension_falls_back_to_url_suffix():
    assert guess_extension("https://cdn.example/file.webp?x=1", None, "image") == ".webp"


def test_guess_extension_falls_back_to_media_type_default():
    assert guess_extension(None, None, "video") == ".mp4"
    assert guess_extension(None, None, "image") == ".jpg"


def test_unique_instagram_path_stays_inside_temp_dir():
    dest = unique_instagram_path(".jpg", author="someuser", shortcode="ABC123", index=1)
    temp_dir = instagram_temp_dir().resolve()
    assert temp_dir in dest.resolve().parents


def test_unique_instagram_path_sanitizes_malicious_author():
    dest = unique_instagram_path(".jpg", author="../../../etc/passwd", shortcode="ABC", index=1)
    temp_dir = instagram_temp_dir().resolve()
    assert temp_dir in dest.resolve().parents
    assert ".." not in dest.name


def test_unique_instagram_path_is_unique_across_calls():
    a = unique_instagram_path(".jpg", author="user", shortcode="ABC", index=1)
    b = unique_instagram_path(".jpg", author="user", shortcode="ABC", index=1)
    assert a != b


def test_safe_remove_deletes_existing_temp_file():
    dest = unique_instagram_path(".txt", author="user", shortcode="ABC", index=1)
    dest.write_text("temp content")
    assert dest.exists()
    safe_remove(dest)
    assert not dest.exists()


def test_safe_remove_ignores_missing_file():
    dest = instagram_temp_dir() / "does_not_exist.txt"
    safe_remove(dest)  # should not raise
