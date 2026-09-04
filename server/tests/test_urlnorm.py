"""URL 规范化规则（v1.2）测试。"""

import pytest

from app.core.errors import AppError
from app.services.fetcher import normalize_url, url_hash


def test_missing_scheme_becomes_https() -> None:
    assert normalize_url("example.com") == "https://example.com/"


def test_http_and_https_equivalent() -> None:
    assert normalize_url("http://example.com/a") == normalize_url("https://example.com/a")


def test_host_lowercased_and_default_port_dropped() -> None:
    assert normalize_url("https://EXAMPLE.com:443/a") == "https://example.com/a"
    assert normalize_url("https://example.com:8443/a") == "https://example.com:8443/a"


def test_fragment_removed() -> None:
    assert normalize_url("https://example.com/a#section") == "https://example.com/a"


def test_trailing_slash_equivalent_but_root_kept() -> None:
    assert normalize_url("https://example.com/a/") == "https://example.com/a"
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_tracking_params_removed_and_query_sorted() -> None:
    url = normalize_url("https://example.com/p?utm_source=x&b=2&a=1&fbclid=zzz")
    assert url == "https://example.com/p?a=1&b=2"


def test_url_hash_stable_and_64() -> None:
    h1 = url_hash(normalize_url("http://example.com/"))
    h2 = url_hash(normalize_url("https://example.com"))
    assert h1 == h2
    assert len(h1) == 64


def test_empty_url_rejected() -> None:
    with pytest.raises(AppError):
        normalize_url("   ")
