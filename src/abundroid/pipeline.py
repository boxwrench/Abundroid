"""Event aggregation pipeline."""

import httpx

from abundroid.models import Event, Organization
from abundroid.uid import compute_uid
from abundroid.adapters import ical, rss


ADAPTERS = {
    "ical": ical.parse,
    "rss": rss.parse,
}


def default_fetch(url: str) -> str:
    """
    Fetch content from a URL.

    Args:
        url: The URL to fetch.

    Returns:
        The response text.

    Raises:
        httpx.HTTPError: If the request fails.
    """
    response = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "Abundroid/0.1 (+https://github.com/boxwrench/Abundroid)"}
    )
    response.raise_for_status()
    return response.text


def run_pipeline(orgs, event_store, fetch=None, adapters=None):
    """
    Run the event aggregation pipeline.

    Args:
        orgs: List of Organization objects.
        event_store: Object with upsert(events) -> dict method.
        fetch: Function to fetch URLs (default: default_fetch).
        adapters: Dict of source_type -> parse function (default: ADAPTERS).

    Returns:
        List of summary dicts: {"org": name, "ok": bool, "error": str, "events_found": int, "new": int, "seen": int}
    """
    if fetch is None:
        fetch = default_fetch
    if adapters is None:
        adapters = ADAPTERS

    summaries = []

    for org in orgs:
        # Skip inactive orgs
        if not org.active:
            continue

        # Check if source type is known
        if org.source_type not in adapters:
            summaries.append({
                "org": org.name,
                "ok": False,
                "error": f"unknown source type: {org.source_type}",
                "events_found": 0,
                "new": 0,
                "seen": 0,
            })
            continue

        try:
            # Fetch content
            content = fetch(org.events_url)

            # Parse using adapter
            parser = adapters[org.source_type]
            events = parser(content, org)

            # Set uid on each event
            for event in events:
                event.uid = compute_uid(event)

            # Upsert events
            result = event_store.upsert(events)

            # Build summary
            summaries.append({
                "org": org.name,
                "ok": True,
                "error": "",
                "events_found": len(events),
                "new": result["new"],
                "seen": result["seen"],
            })
        except Exception as e:
            # Error isolation: capture error and continue
            summaries.append({
                "org": org.name,
                "ok": False,
                "error": str(e),
                "events_found": 0,
                "new": 0,
                "seen": 0,
            })

    return summaries
