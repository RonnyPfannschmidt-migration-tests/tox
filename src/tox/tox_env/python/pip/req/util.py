"""Borrowed from the pip code base"""
import sys
from typing import Optional
from urllib.parse import urlsplit
from urllib.request import url2pathname

VCS = ["ftp", "ssh", "git", "hg", "bzr", "sftp", "svn"]
VALID_SCHEMAS = ["http", "https", "file"] + VCS


def is_url(name: str) -> bool:
    return get_url_scheme(name) in VALID_SCHEMAS


def get_url_scheme(url: str) -> Optional[str]:
    if ":" not in url:
        return None
    return url.split(":", 1)[0].lower()


def url_to_path(url: str) -> str:
    _, netloc, path, _, _ = urlsplit(url)
    if not netloc or netloc == "localhost":  # According to RFC 8089, same as empty authority.
        netloc = ""
    elif sys.platform == "win32":  # pragma: win32 cover
        netloc = "\\\\" + netloc  # If we have a UNC path, prepend UNC share notation.
    else:
        raise ValueError(f"non-local file URIs are not supported on this platform: {url!r}")
    path = url2pathname(netloc + path)
    return path
