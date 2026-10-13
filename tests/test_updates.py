from datetime import datetime, timedelta

import pytest

from printpicker.core.updates import (
    ReleaseFormatError,
    ReleaseInfo,
    is_newer,
    parse_release,
    parse_version,
    should_auto_check,
    should_offer,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("v1.2.3", (1, 2, 3)),
        ("1.2.3", (1, 2, 3)),
        ("v1.0", (1, 0, 0)),
        (" v0.10.0 ", (0, 10, 0)),
        ("v1.0.0-rc1", None),
        ("latest", None),
        ("", None),
    ],
)
def test_parse_version(text, expected):
    assert parse_version(text) == expected


def test_is_newer_compares_numbers_not_text():
    assert is_newer("v0.10.0", "0.9.0")
    assert is_newer("1.0.0", "0.6.0")
    assert not is_newer("v0.6.0", "0.6.0")
    assert not is_newer("0.5.9", "0.6.0")
    assert not is_newer("garbage", "0.6.0")


RELEASE = {
    "tag_name": "v1.1.0",
    "html_url": "https://github.com/GiacomoGuaresi/PrintPicker/releases/tag/v1.1.0",
    "body": "## What's new\n- faster",
    "draft": False,
    "prerelease": False,
    "published_at": "2026-11-01T10:00:00Z",
}


def test_parse_release():
    release = parse_release(RELEASE)
    assert release.version == "1.1.0"
    assert release.url.endswith("/v1.1.0")
    assert "faster" in release.notes


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {"message": "Not Found"},
        {**RELEASE, "tag_name": "nightly"},
        {**RELEASE, "prerelease": True},
        {**RELEASE, "html_url": None},
    ],
)
def test_parse_release_rejects_unexpected_data(data):
    with pytest.raises(ReleaseFormatError):
        parse_release(data)


def test_missing_notes_are_empty():
    assert parse_release({**RELEASE, "body": None}).notes == ""


def test_auto_check_at_most_once_a_day():
    now = datetime(2026, 10, 13, 12, 0)
    assert should_auto_check(True, None, now)
    assert not should_auto_check(True, now - timedelta(hours=3), now)
    assert should_auto_check(True, now - timedelta(days=1, minutes=1), now)
    assert should_auto_check(True, now + timedelta(days=3), now)  # clock went back
    assert not should_auto_check(False, None, now)


def test_skipped_version_is_offered_only_on_manual_check():
    release = ReleaseInfo("1.1.0", "https://example.org", "")
    assert should_offer(release, "1.0.0", skipped="", manual=False)
    assert not should_offer(release, "1.0.0", skipped="1.1.0", manual=False)
    assert should_offer(release, "1.0.0", skipped="1.1.0", manual=True)
    assert not should_offer(release, "1.1.0", skipped="", manual=True)
