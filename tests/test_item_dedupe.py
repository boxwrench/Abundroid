"""Tests for candidate-bounded near-duplicate detection."""

from abundroid.item_dedupe import _comparison_pairs, flag_possible_item_duplicates
from abundroid.models import Item


def item(uid: str, title: str = "Shared update") -> Item:
    return Item(title=title, publisher="Example", uid=uid)


def test_comparison_pairs_exclude_persisted_to_persisted_pairs():
    candidates = [item("candidate-1"), item("candidate-2")]
    persisted = [item("existing-1"), item("existing-2"), item("existing-3")]

    pairs = list(_comparison_pairs(candidates, persisted))

    assert len(pairs) == 7
    assert all(left in candidates for left, _ in pairs)
    assert not any(left in persisted and right in persisted for left, right in pairs)


def test_duplicate_detection_still_compares_candidates_and_persisted_items():
    first = item("candidate-1")
    second = item("candidate-2")
    existing = item("existing-1")

    relationships = flag_possible_item_duplicates([first, second], [existing])

    assert relationships["candidate-1"] == "candidate-2"
    assert relationships["candidate-2"] == "candidate-1"
    assert relationships["existing-1"] == "candidate-1"
