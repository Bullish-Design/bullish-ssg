"""Helpers for deriving GitHub Pages URLs from git remotes."""

from __future__ import annotations

import re

GITHUB_HTTP_RE = re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")
GITHUB_SSH_RE = re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")
GITHUB_SSH_SCHEME_RE = re.compile(r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")


def infer_pages_url(remote_url: str) -> str | None:
    """Infer GitHub Pages URL from a git remote URL.

    Supports HTTPS and SSH GitHub remote formats.
    """
    remote_url = remote_url.strip()
    for pattern in (GITHUB_HTTP_RE, GITHUB_SSH_RE, GITHUB_SSH_SCHEME_RE):
        match = pattern.match(remote_url)
        if not match:
            continue
        owner = match.group("owner")
        repo = match.group("repo")
        return f"https://{owner}.github.io/{repo}/"
    return None
