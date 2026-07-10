'''Near-duplicate detection for published items.'''

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher


def _normalized(text: str) -> str:
    text = re.sub('[^a-z0-9 ]', ' ', (text or '').lower())
    return ' '.join(text.split())


def _days_between(a: datetime | None, b: datetime | None) -> int | None:
    if a is None or b is None:
        return None
    return abs((a.date() - b.date()).days)


def flag_possible_item_duplicates(
    items,
    existing_items=(),
    *,
    title_threshold: float = 0.9,
    publication_window_days: int = 14,
) -> dict[str, str]:
    '''Flag likely duplicates, including items persisted by earlier runs.'''
    candidates = list(items)
    all_items = candidates + list(existing_items)
    candidate_ids = {id(item) for item in candidates}
    relationships: dict[str, str] = {}

    for index, left in enumerate(all_items):
        for right in all_items[index + 1:]:
            if id(left) not in candidate_ids and id(right) not in candidate_ids:
                continue
            if not left.uid or not right.uid or left.uid == right.uid:
                continue

            left_url = getattr(left, 'canonical_url', '')
            right_url = getattr(right, 'canonical_url', '')
            same_url = bool(left_url and right_url and left_url == right_url)
            left_title = _normalized(left.title)
            right_title = _normalized(right.title)
            if not same_url and (not left_title or not right_title):
                continue
            similarity = SequenceMatcher(
                None, left_title, right_title
            ).ratio()
            if not same_url and similarity < title_threshold:
                continue

            distance = _days_between(
                getattr(left, 'published_at', None),
                getattr(right, 'published_at', None),
            )
            if not same_url and distance is not None and distance > publication_window_days:
                continue

            if not left.possible_duplicate_of:
                left.possible_duplicate_of = right.uid
            if not right.possible_duplicate_of:
                right.possible_duplicate_of = left.uid
            relationships.setdefault(left.uid, right.uid)
            relationships.setdefault(right.uid, left.uid)

    return relationships
