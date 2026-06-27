"""Tests for URL normalization."""

from __future__ import annotations

from skillreg.services.url_utils import normalize_git_url


def test_ssh_url_to_https():
    assert normalize_git_url("git@github.com:fcraft/skillreg.git") == "https://github.com/fcraft/skillreg"


def test_https_url_strips_dot_git():
    assert normalize_git_url("https://github.com/fcraft/skillreg.git") == "https://github.com/fcraft/skillreg"


def test_https_url_no_dot_git():
    assert normalize_git_url("https://github.com/fcraft/skillreg") == "https://github.com/fcraft/skillreg"


def test_none_url_returns_none():
    assert normalize_git_url(None) is None


def test_empty_url_returns_none():
    assert normalize_git_url("") is None


def test_unrecognized_url_returns_none():
    assert normalize_git_url("not-a-url") is None
