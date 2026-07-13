"""HTTP retrieval shared by publication source adapters."""

import httpx


def default_fetch(url: str) -> str:
    """Fetch a public source URL and return its response text."""
    response = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        headers={
            "User-Agent": "Abundroid/0.1 (+https://github.com/boxwrench/Abundroid)"
        },
    )
    response.raise_for_status()
    return response.text
