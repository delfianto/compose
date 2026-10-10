#!/usr/bin/env python3
"""Resolve latest-stable through GitHub's release API; preserve explicit refs."""

import json
import re
import sys
import urllib.request


def resolve_ref(repository: str, requested: str) -> str:
    if requested != "latest-stable":
        return requested
    match = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?", repository)
    if match is None:
        raise ValueError("latest-stable requires an HTTPS GitHub repository URL")
    owner, repo = match.groups()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "comfyui-runtime"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        release = json.load(response)
    tag = release.get("tag_name")
    if release.get("draft") or release.get("prerelease") or not isinstance(tag, str) or not tag:
        raise ValueError("GitHub did not return a stable release tag")
    return tag


if __name__ == "__main__":
    try:
        print(resolve_ref(sys.argv[1], sys.argv[2]))
    except Exception as error:
        print(f"Could not resolve ComfyUI ref: {error}", file=sys.stderr)
        sys.exit(1)
