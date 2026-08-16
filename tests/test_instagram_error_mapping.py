from __future__ import annotations

import instaloader.exceptions as ilx
from gallery_dl import exception as gdl_exc

from instagram.exceptions import (
    InstagramAuthRequiredError,
    InstagramExtractionError,
    InstagramMediaNotFoundError,
    InstagramNetworkError,
    InstagramPrivateContentError,
    InstagramRateLimitedError,
    UnsupportedInstagramURLError,
)
from instagram.extractors.gallery_dl import _map_exception as gdl_map
from instagram.extractors.instaloader import _map_exception as ilx_map
from instagram.extractors.parth import _map_error as parth_map


class _FakeRateLimitError(Exception):
    pass


class _FakeNetworkError(Exception):
    pass


def test_parth_maps_generic_login_message_to_auth_required(monkeypatch):
    mapped = parth_map(Exception("Instagram is serving a login wall to unauthenticated requests"))
    assert isinstance(mapped, InstagramAuthRequiredError)


def test_parth_maps_private_message_to_private_content():
    mapped = parth_map(Exception("Content not found. It might be private or deleted."))
    assert isinstance(mapped, InstagramPrivateContentError)


def test_parth_maps_unknown_message_to_generic_extraction_error():
    mapped = parth_map(Exception("something completely unexpected"))
    assert isinstance(mapped, InstagramExtractionError)


def test_gallery_dl_maps_auth_required():
    assert isinstance(gdl_map(gdl_exc.AuthRequired("login")), InstagramAuthRequiredError)


def test_gallery_dl_maps_not_found():
    assert isinstance(gdl_map(gdl_exc.NotFoundError("gone")), InstagramMediaNotFoundError)


def test_gallery_dl_maps_no_extractor_to_unsupported():
    assert isinstance(gdl_map(gdl_exc.NoExtractorError("nope")), UnsupportedInstagramURLError)


def test_gallery_dl_maps_429_http_error_to_rate_limited():
    class FakeResponse:
        status_code = 429
        reason = "Too Many Requests"
        url = "https://instagram.com/x"

    err = gdl_exc.HttpError(response=FakeResponse())
    assert isinstance(gdl_map(err), InstagramRateLimitedError)


def test_gallery_dl_maps_other_http_error_to_network_error():
    class FakeResponse:
        status_code = 500
        reason = "Server Error"
        url = "https://instagram.com/x"

    err = gdl_exc.HttpError(response=FakeResponse())
    assert isinstance(gdl_map(err), InstagramNetworkError)


def test_instaloader_maps_login_required():
    assert isinstance(ilx_map(ilx.LoginRequiredException("login needed")), InstagramAuthRequiredError)


def test_instaloader_maps_private_profile():
    assert isinstance(ilx_map(ilx.PrivateProfileNotFollowedException("private")), InstagramPrivateContentError)


def test_instaloader_maps_not_found():
    assert isinstance(ilx_map(ilx.ProfileNotExistsException("nope")), InstagramMediaNotFoundError)


def test_instaloader_maps_too_many_requests():
    assert isinstance(ilx_map(ilx.TooManyRequestsException("slow down")), InstagramRateLimitedError)


def test_instaloader_maps_connection_exception():
    assert isinstance(ilx_map(ilx.ConnectionException("down")), InstagramNetworkError)


def test_instaloader_maps_unknown_exception_to_generic():
    assert isinstance(ilx_map(ValueError("weird")), InstagramExtractionError)
