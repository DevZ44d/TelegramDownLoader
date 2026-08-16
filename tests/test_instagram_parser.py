from __future__ import annotations

from instagram.parser import InstagramURLType, is_instagram_url, parse_instagram_url


def test_is_instagram_url_true_for_instagram_domains():
    assert is_instagram_url("https://www.instagram.com/reel/ABC123/")
    assert is_instagram_url("https://instagram.com/p/ABC123/")


def test_is_instagram_url_false_for_other_domains():
    assert not is_instagram_url("https://t.me/somechannel/10")
    assert not is_instagram_url("https://example.com/p/ABC123/")
    assert not is_instagram_url("not a url at all")


def test_parse_reel_url():
    parsed = parse_instagram_url("https://www.instagram.com/reel/CzXyzAbC1/")
    assert parsed.url_type == InstagramURLType.REEL
    assert parsed.shortcode == "CzXyzAbC1"
    assert parsed.is_media


def test_parse_reels_plural_url():
    parsed = parse_instagram_url("https://www.instagram.com/reels/CzXyzAbC1/")
    assert parsed.url_type == InstagramURLType.REEL


def test_parse_post_url():
    parsed = parse_instagram_url("https://www.instagram.com/p/CzXyzAbC1/")
    assert parsed.url_type == InstagramURLType.POST
    assert parsed.shortcode == "CzXyzAbC1"


def test_parse_tv_url():
    parsed = parse_instagram_url("https://www.instagram.com/tv/CzXyzAbC1/")
    assert parsed.url_type == InstagramURLType.TV


def test_parse_post_url_with_query_string():
    parsed = parse_instagram_url("https://www.instagram.com/p/CzXyzAbC1/?igsh=abc123")
    assert parsed.url_type == InstagramURLType.POST
    assert parsed.shortcode == "CzXyzAbC1"


def test_parse_profile_url():
    parsed = parse_instagram_url("https://www.instagram.com/some_user.name/")
    assert parsed.url_type == InstagramURLType.PROFILE
    assert parsed.username == "some_user.name"
    assert not parsed.is_media


def test_parse_reserved_segment_is_not_a_profile():
    parsed = parse_instagram_url("https://www.instagram.com/explore/")
    assert parsed.url_type == InstagramURLType.UNKNOWN


def test_parse_invalid_shortcode_characters():
    parsed = parse_instagram_url("https://www.instagram.com/p/../../etc/passwd/")
    assert parsed.url_type == InstagramURLType.UNKNOWN


def test_parse_non_instagram_url_is_unknown():
    parsed = parse_instagram_url("https://t.me/somechannel/10")
    assert parsed.url_type == InstagramURLType.UNKNOWN


def test_parse_stories_url_is_unknown():
    # Stories are intentionally unsupported by this module.
    parsed = parse_instagram_url("https://www.instagram.com/stories/someuser/12345/")
    assert parsed.url_type == InstagramURLType.UNKNOWN
