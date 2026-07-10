"""Fuzzy cross-organization duplicate event detection."""

import re
from difflib import SequenceMatcher

from abundroid.models import Event


def _normalize_title(title: str) -> str:
    """
    Normalize a title for similarity comparison.

    - Lowercase the title
    - Strip leading/trailing whitespace
    - Remove all characters that are not alphanumeric or whitespace
    - Collapse runs of whitespace to a single space
    """
    # Lowercase and strip
    normalized = title.lower().strip()

    # Remove non-alphanumeric and non-whitespace characters
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

    # Collapse runs of whitespace to a single space
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized


def flag_possible_duplicates(events: list[Event], threshold: float = 0.85) -> int:
    """
    Flag possible duplicate events across organizations using fuzzy matching.

    Considers every unordered pair of events in the batch. A pair is a possible
    duplicate if and only if ALL of:

    1. Organizers differ (case-insensitive comparison after strip)
    2. UIDs differ
    3. Both events have start != None AND start.date() is equal
    4. Normalized-title similarity >= threshold, using difflib.SequenceMatcher

    Flagging: Sets a.possible_duplicate_of = b.uid and b.possible_duplicate_of = a.uid.
    If an event already has a non-empty possible_duplicate_of (from an earlier pair
    this run), that value is preserved — first match wins.

    Args:
        events: List of Event objects to compare.
        threshold: Similarity threshold (0.0-1.0) for title matching. Defaults to 0.85.

    Returns:
        The number of pairs where at least one side was newly flagged. A pair where
        both sides were already flagged from earlier matches still counts toward
        comparison but sets nothing — only pairs where at least one side is newly set
        count toward the return value.
    """
    if len(events) <= 1:
        return 0

    pairs_flagged = 0

    # Compare every unordered pair
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            event_a = events[i]
            event_b = events[j]

            # Check all four conditions
            # 1. Organizers differ (case-insensitive, after strip)
            org_a = event_a.organizer.strip().lower()
            org_b = event_b.organizer.strip().lower()
            if org_a == org_b:
                continue

            # 2. UIDs differ
            if event_a.uid == event_b.uid:
                continue

            # 3. Both have start != None AND start.date() is equal
            if event_a.start is None or event_b.start is None:
                continue
            if event_a.start.date() != event_b.start.date():
                continue

            # 4. Normalized-title similarity >= threshold
            norm_a = _normalize_title(event_a.title)
            norm_b = _normalize_title(event_b.title)
            similarity = SequenceMatcher(None, norm_a, norm_b).ratio()
            if similarity < threshold:
                continue

            # All conditions met: flag this pair if at least one side is new
            set_a = False
            set_b = False

            if not event_a.possible_duplicate_of:
                event_a.possible_duplicate_of = event_b.uid
                set_a = True

            if not event_b.possible_duplicate_of:
                event_b.possible_duplicate_of = event_a.uid
                set_b = True

            # Count this pair only if at least one side was newly set
            if set_a or set_b:
                pairs_flagged += 1

    return pairs_flagged
