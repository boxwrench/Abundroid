"""Fuzzy cross-organization duplicate event detection tests."""

from datetime import datetime
import pytest

from abundroid.models import Event
from abundroid.dedupe import flag_possible_duplicates


class TestFlagPossibleDuplicates:
    """Test suite for fuzzy duplicate flagging across organizations."""

    def test_empty_list(self):
        """Empty event list returns 0."""
        assert flag_possible_duplicates([]) == 0

    def test_single_event(self):
        """Single event returns 0 (no pairs to compare)."""
        event = Event(
            title="Tech Summit 2026",
            organizer="TechCorp",
            uid="uid1",
            start=datetime(2026, 7, 15)
        )
        assert flag_possible_duplicates([event]) == 0

    def test_near_identical_titles_different_orgs_same_date_cross_flagged(self):
        """Near-identical titles from two different orgs on same date get cross-flagged both ways."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2], threshold=0.85)

        assert result == 1, "Should flag exactly 1 pair"
        assert e1.possible_duplicate_of == "uid2", "e1 should point to e2"
        assert e2.possible_duplicate_of == "uid1", "e2 should point to e1"

    def test_punctuation_case_differences_still_match(self):
        """Punctuation and case differences still match if similarity >= threshold."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026!",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="housing summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2], threshold=0.85)

        assert result == 1
        assert e1.possible_duplicate_of == "uid2"
        assert e2.possible_duplicate_of == "uid1"

    def test_identical_titles_different_dates_not_flagged(self):
        """Identical titles but different dates are not flagged."""
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=datetime(2026, 7, 15)
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=datetime(2026, 7, 16)  # Different date
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_same_organizer_not_flagged(self):
        """Same organizer not flagged even with identical title and date."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="SameOrg",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="SameOrg",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_same_organizer_case_insensitive(self):
        """Organizer comparison is case-insensitive."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="SameOrg",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="SAMEORG",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_same_organizer_with_whitespace(self):
        """Organizer comparison is case-insensitive and strips whitespace."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="  SameOrg  ",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="SAMEORG",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_same_uid_not_flagged(self):
        """Events with same UID are not flagged."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="same_uid",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="same_uid",
            start=date
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_missing_start_on_either_side_not_flagged(self):
        """Events with missing start date are not flagged."""
        date = datetime(2026, 7, 15)

        # e1 has start, e2 doesn't
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=None
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_both_missing_start_not_flagged(self):
        """Events both with missing start date are not flagged."""
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=None
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=None
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_clearly_different_titles_same_date_not_flagged(self):
        """Clearly different titles on same date are not flagged."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Computer Science Conference",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2])

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_three_way_case_a_matches_b_and_c(self):
        """Three-way: A matches B and C; A keeps first match, count reflects pairs that set something."""
        date = datetime(2026, 7, 15)

        # A, B, C all have identical title and different orgs on same date
        e_a = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid_a",
            start=date
        )
        e_b = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid_b",
            start=date
        )
        e_c = Event(
            title="Housing Summit 2026",
            organizer="OrgC",
            uid="uid_c",
            start=date
        )

        # When checking pairs in order: (A,B), (A,C), (B,C)
        # (A,B) matches: A.possible_duplicate_of = B, B.possible_duplicate_of = A (count = 1)
        # (A,C) matches but A already has possible_duplicate_of: don't overwrite, but still counts
        #       C doesn't have it yet: set C.possible_duplicate_of = A (count += 1)
        # (B,C) matches but both already have possible_duplicate_of: don't set anything (count += 0)

        result = flag_possible_duplicates([e_a, e_b, e_c])

        # A gets set to B (first match wins)
        # B gets set to A (first match wins)
        # C gets set to A (when checking (A,C), A already has value, C doesn't, so set C)
        # Then (B,C) pair: both already have values, so nothing new is set
        assert result == 2  # (A,B) pair sets 2 sides, (A,C) pair sets 1 side (C)
        assert e_a.possible_duplicate_of == "uid_b"
        assert e_b.possible_duplicate_of == "uid_a"
        assert e_c.possible_duplicate_of == "uid_a"

    def test_already_flagged_not_overwritten(self):
        """If an event already has possible_duplicate_of set, it is not overwritten."""
        date = datetime(2026, 7, 15)

        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date,
            possible_duplicate_of="uid_previous"
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2])

        # e1 already has a value, so it shouldn't be overwritten
        # e2 should still get the new value
        assert result == 1, "Should count 1 pair where at least one side was newly set"
        assert e1.possible_duplicate_of == "uid_previous", "e1 should keep its original value"
        assert e2.possible_duplicate_of == "uid1", "e2 should be newly set"

    def test_threshold_below_match(self):
        """Titles below threshold don't match."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Technology Conference 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2], threshold=0.9)

        assert result == 0
        assert e1.possible_duplicate_of == ""
        assert e2.possible_duplicate_of == ""

    def test_threshold_above_match(self):
        """Titles above threshold do match."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026 Extravaganza",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2], threshold=0.70)

        assert result == 1
        assert e1.possible_duplicate_of == "uid2"
        assert e2.possible_duplicate_of == "uid1"

    def test_return_value_is_int(self):
        """Return value is always an int."""
        assert isinstance(flag_possible_duplicates([]), int)

        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=datetime(2026, 7, 15)
        )
        assert isinstance(flag_possible_duplicates([e1]), int)

        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=datetime(2026, 7, 15)
        )
        assert isinstance(flag_possible_duplicates([e1, e2]), int)

    def test_title_normalization_removes_special_chars(self):
        """Title normalization removes non-alphanumeric/whitespace characters."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing-Summit_2026!!!",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="housing summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2], threshold=0.85)

        assert result == 1
        assert e1.possible_duplicate_of == "uid2"
        assert e2.possible_duplicate_of == "uid1"

    def test_whitespace_collapse_in_titles(self):
        """Multiple spaces in titles are collapsed to one."""
        date = datetime(2026, 7, 15)
        e1 = Event(
            title="Housing  Summit    2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="housing summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        result = flag_possible_duplicates([e1, e2], threshold=0.85)

        assert result == 1
        assert e1.possible_duplicate_of == "uid2"
        assert e2.possible_duplicate_of == "uid1"

    def test_four_events_complex(self):
        """Complex case with four events: two pairs match independently."""
        date = datetime(2026, 7, 15)

        # Pair 1: e1 and e2 match
        e1 = Event(
            title="Housing Summit 2026",
            organizer="OrgA",
            uid="uid1",
            start=date
        )
        e2 = Event(
            title="Housing Summit 2026",
            organizer="OrgB",
            uid="uid2",
            start=date
        )

        # Pair 2: e3 and e4 match
        e3 = Event(
            title="Tech Conference 2026",
            organizer="OrgC",
            uid="uid3",
            start=date
        )
        e4 = Event(
            title="Tech Conference 2026",
            organizer="OrgD",
            uid="uid4",
            start=date
        )

        result = flag_possible_duplicates([e1, e2, e3, e4])

        assert result == 2
        assert e1.possible_duplicate_of == "uid2"
        assert e2.possible_duplicate_of == "uid1"
        assert e3.possible_duplicate_of == "uid4"
        assert e4.possible_duplicate_of == "uid3"
