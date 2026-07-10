"""Event aggregation pipeline."""

import httpx

from abundroid.models import Event, Organization
from abundroid.uid import compute_uid
from abundroid.classifier import tag_events
from abundroid.dedupe import flag_possible_duplicates
from abundroid.adapters import ical, rss, jsonld


ADAPTERS = {
    "ical": ical.parse,
    "rss": rss.parse,
    "jsonld": jsonld.parse,
}

# Sources that publish their complete upcoming calendar. Only for these does
# "event vanished from the source" mean anything — RSS feeds naturally drop
# old posts, so their absences must never be read as cancellations.
FULL_CALENDAR_TYPES = {"ical", "jsonld"}


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


def run_pipeline(orgs, event_store, fetch=None, adapters=None, topics=None):
    """
    Run the event aggregation pipeline.

    Two phases: first fetch and parse every active organization (errors
    isolated per org), then — once the whole batch is known — tag topics,
    flag cross-organization duplicates, and upsert per org. The batch-wide
    middle step is why upserts can't happen during fetching: duplicates only
    become visible when events from different orgs sit side by side.

    Args:
        orgs: List of Organization objects.
        event_store: Object with upsert(events) -> dict method; may optionally
            provide flag_missing(organizer, present_uids) -> int.
        fetch: Function to fetch URLs (default: default_fetch).
        adapters: Dict of source_type -> parse function (default: ADAPTERS).
        topics: List of Topic objects for tagging (default: no tagging).

    Returns:
        List of summary dicts: {"org": name, "ok": bool, "error": str,
        "events_found": int, "new": int, "seen": int, "possibly_cancelled": int}
    """
    if fetch is None:
        fetch = default_fetch
    if adapters is None:
        adapters = ADAPTERS

    summaries = []
    parsed = []  # (org, events, summary) for orgs that fetched cleanly

    # Phase 1: fetch and parse every active org, isolating failures
    for org in orgs:
        if not org.active:
            continue

        summary = {
            "org": org.name,
            "ok": False,
            "error": "",
            "events_found": 0,
            "new": 0,
            "seen": 0,
            "possibly_cancelled": 0,
        }
        summaries.append(summary)

        if org.source_type not in adapters:
            summary["error"] = f"unknown source type: {org.source_type}"
            continue

        try:
            content = fetch(org.events_url)
            events = adapters[org.source_type](content, org)
            for event in events:
                event.uid = compute_uid(event)
        except Exception as e:
            summary["error"] = str(e)
            continue

        summary["events_found"] = len(events)
        parsed.append((org, events, summary))

    # Phase 2: batch-wide enrichment across all successfully parsed orgs
    all_events = [event for _, events, _ in parsed for event in events]
    if topics:
        tag_events(all_events, topics)
    flag_possible_duplicates(all_events)

    # Phase 3: persist per org, still isolating failures
    for org, events, summary in parsed:
        try:
            result = event_store.upsert(events)
            summary["new"] = result["new"]
            summary["seen"] = result["seen"]

            flag_missing = getattr(event_store, "flag_missing", None)
            if flag_missing and org.source_type in FULL_CALENDAR_TYPES:
                present_uids = {event.uid for event in events}
                summary["possibly_cancelled"] = flag_missing(org.name, present_uids)

            summary["ok"] = True
        except Exception as e:
            summary["error"] = str(e)

    return summaries
