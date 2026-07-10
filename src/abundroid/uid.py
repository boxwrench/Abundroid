"""UID generation for events — normalization and deterministic identity."""

import hashlib
import re
from urllib.parse import urlparse, urlencode, parse_qs

from abundroid.models import Event


def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison.

    - Lowercase scheme and host (preserve path case)
    - Remove utm_*, fbclid, gclid query parameters
    - Sort remaining query parameters
    - Drop fragment
    - Strip trailing slash from path (unless path is exactly "/")
    - Drop default ports (80 for http, 443 for https)
    """
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.hostname.lower() if parsed.hostname else ""

    # Preserve port only if non-default
    if parsed.port:
        if not ((scheme == "http" and parsed.port == 80) or
                (scheme == "https" and parsed.port == 443)):
            netloc += f":{parsed.port}"

    # Process path: strip trailing slash if longer than "/"
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    # If path is empty, make it empty string (no "/" for root)
    if not path or path == "/":
        path = ""

    # Parse and filter query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {}
    for key, values in query_params.items():
        # Skip utm_* params, fbclid, and gclid
        if not key.startswith("utm_") and key not in ("fbclid", "gclid"):
            # Take first value (parse_qs returns lists)
            filtered_params[key] = values[0] if values else ""

    # Sort query parameters by key
    sorted_query = urlencode(sorted(filtered_params.items()))

    # Reconstruct URL without fragment
    result = f"{scheme}://{netloc}{path}"
    if sorted_query:
        result += f"?{sorted_query}"

    return result


def compute_uid(event: Event) -> str:
    """
    Compute a deterministic UID for an event.

    If event.url is non-empty: return "url:" + normalize_url(event.url)
    Otherwise: return "hash:" + first 16 hex chars of sha256 hash of
               "{organizer}|{title}|{date}" where organizer and title are
               lowercased with whitespace collapsed and stripped, and date is
               event.start.date().isoformat() if start is not None else "".
    """
    if event.url:
        return "url:" + normalize_url(event.url)

    # Normalize organizer and title
    organizer = re.sub(r"\s+", " ", event.organizer.lower().strip())
    title = re.sub(r"\s+", " ", event.title.lower().strip())

    # Get date string
    if event.start:
        date_str = event.start.date().isoformat()
    else:
        date_str = ""

    # Create hash input
    hash_input = f"{organizer}|{title}|{date_str}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()

    return "hash:" + hash_digest[:16]


def content_hash(event: Event) -> str:
    """
    Fingerprint the source-provided details of an event (16 hex chars).

    Unlike compute_uid (identity), this changes whenever any detail the source
    publishes changes — used to flag already-seen events for re-review.
    """
    parts = [
        event.title,
        event.start.isoformat() if event.start else "",
        event.end.isoformat() if event.end else "",
        event.location,
        event.url,
        event.description,
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
