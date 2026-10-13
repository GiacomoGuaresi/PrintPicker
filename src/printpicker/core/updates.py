"""Update check logic, without Qt: version comparison, GitHub release parsing, when to check.

The app asks GitHub for the latest *published* release
(``/repos/<owner>/<repo>/releases/latest``, which already skips drafts and pre-releases)
and offers it when its version is newer than the running one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

AUTO_CHECK_INTERVAL = timedelta(days=1)

_VERSION = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """``"v1.2.0"`` → ``(1, 2, 0)``; None for anything else, pre-releases included."""
    match = _VERSION.match(text.strip())
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch or 0)


def is_newer(latest: str, current: str) -> bool:
    new, old = parse_version(latest), parse_version(current)
    return new is not None and old is not None and new > old


@dataclass(frozen=True)
class ReleaseInfo:
    version: str  # without the leading "v"
    url: str  # release page on GitHub
    notes: str  # Markdown
    published_at: str = ""


class ReleaseFormatError(ValueError):
    pass


def parse_release(data: object) -> ReleaseInfo:
    """Read the JSON of GitHub's "latest release" endpoint."""
    if not isinstance(data, dict):
        raise ReleaseFormatError("not a release")
    tag, url = data.get("tag_name"), data.get("html_url")
    if not isinstance(tag, str) or not isinstance(url, str) or parse_version(tag) is None:
        raise ReleaseFormatError(f"unexpected release: {tag!r}")
    if data.get("draft") or data.get("prerelease"):
        raise ReleaseFormatError(f"not a final release: {tag}")
    notes = data.get("body")
    published = data.get("published_at")
    return ReleaseInfo(
        version=tag.strip().removeprefix("v"),
        url=url,
        notes=notes if isinstance(notes, str) else "",
        published_at=published if isinstance(published, str) else "",
    )


def should_auto_check(enabled: bool, last_check: datetime | None, now: datetime) -> bool:
    """At most one automatic check a day, and only if the user did not turn it off."""
    if not enabled:
        return False
    return last_check is None or now - last_check >= AUTO_CHECK_INTERVAL or last_check > now


def should_offer(release: ReleaseInfo, current: str, skipped: str, manual: bool) -> bool:
    """Offer a newer release, unless the user chose to skip that version (a manual check
    always offers it)."""
    if not is_newer(release.version, current):
        return False
    return manual or release.version != skipped
