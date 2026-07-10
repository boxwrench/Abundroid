"""Tests for the topic classifier module."""

import pytest
from pathlib import Path
from abundroid.models import Event, Topic
from abundroid.classifier import split_terms, tag_events, topics_from_airtable, load_topics_csv


class TestSplitTerms:
    """Test the split_terms function."""

    def test_empty_string(self):
        """Empty string returns empty list."""
        assert split_terms("") == []

    def test_none_ish_input(self):
        """None-ish inputs return empty list."""
        assert split_terms(None) == []

    def test_single_term(self):
        """Single term without comma."""
        assert split_terms("art walk") == ["art walk"]

    def test_comma_separated(self):
        """Comma-separated terms are split."""
        assert split_terms("art, music, dance") == ["art", "music", "dance"]

    def test_strip_whitespace(self):
        """Whitespace around terms is stripped."""
        assert split_terms("  art  ,  music  ,  dance  ") == ["art", "music", "dance"]

    def test_drop_empties(self):
        """Empty terms (after stripping) are dropped."""
        assert split_terms("art, , music, ,") == ["art", "music"]

    def test_preserve_case(self):
        """Original case is preserved."""
        assert split_terms("ART, Music, DaNcE") == ["ART", "Music", "DaNcE"]


class TestTagEvents:
    """Test the tag_events function."""

    def test_keyword_match_in_title(self):
        """Keyword match in title adds topic."""
        event = Event(title="Art Walk Downtown", organizer="Downtown Arts")
        topics = [Topic(name="Arts", keywords=["art walk"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]

    def test_keyword_match_in_description(self):
        """Keyword match in description adds topic."""
        event = Event(
            title="Community Event",
            organizer="Organizer",
            description="Join us for an art walk"
        )
        topics = [Topic(name="Arts", keywords=["art walk"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]

    def test_case_insensitive_match(self):
        """Keyword matching is case-insensitive."""
        event = Event(title="ART WALK", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art walk"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]

    def test_word_boundary_no_match_startup(self):
        """'art' should not match 'startup' (word boundary enforcement)."""
        event = Event(title="Startup Showcase", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art"])]
        tag_events([event], topics)
        assert event.topics == []

    def test_word_boundary_match_art_walk(self):
        """'art' matches 'Art Walk' as separate word."""
        event = Event(title="Art Walk", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]

    def test_multi_word_keyword(self):
        """Multi-word keyword is matched as phrase."""
        event = Event(title="Zoning Reform 101", organizer="Org")
        topics = [Topic(name="Policy", keywords=["zoning reform"])]
        tag_events([event], topics)
        assert event.topics == ["Policy"]

    def test_exclusion_vetoes_topic(self):
        """Exclusion term prevents topic from matching."""
        event = Event(title="Art Walk in Downtown", organizer="Org", description="Jazz and art")
        topics = [Topic(name="Arts", keywords=["art"], exclusions=["jazz"])]
        tag_events([event], topics)
        assert event.topics == []

    def test_exclusion_does_not_prevent_if_no_exclusion_match(self):
        """Exclusion only prevents if it matches the text."""
        event = Event(title="Art Walk Downtown", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art"], exclusions=["jazz"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]

    def test_inactive_topic_never_matches(self):
        """Inactive topic is never matched."""
        event = Event(title="Art Walk", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art"], active=False)]
        tag_events([event], topics)
        assert event.topics == []

    def test_topic_with_no_keywords_never_matches(self):
        """Topic with empty keywords never matches."""
        event = Event(title="Art Walk", organizer="Org")
        topics = [Topic(name="Arts", keywords=[])]
        tag_events([event], topics)
        assert event.topics == []

    def test_multiple_topics_preserve_order(self):
        """Multiple topics on one event preserve given order."""
        event = Event(title="Art Music Festival", organizer="Org")
        topics = [
            Topic(name="Arts", keywords=["art"]),
            Topic(name="Music", keywords=["music"]),
            Topic(name="Festival", keywords=["festival"])
        ]
        tag_events([event], topics)
        assert event.topics == ["Arts", "Music", "Festival"]

    def test_event_no_matches(self):
        """Event with no matches has empty topics list."""
        event = Event(title="Generic Event", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art"]), Topic(name="Music", keywords=["music"])]
        tag_events([event], topics)
        assert event.topics == []

    def test_no_duplicate_topics(self):
        """Topic is assigned once, never duplicated."""
        event = Event(title="Art Art Art", organizer="Org")
        topics = [Topic(name="Arts", keywords=["art"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]
        assert len(event.topics) == 1

    def test_title_and_description_combined(self):
        """Keywords matched against title + description."""
        event = Event(title="Event", organizer="Org", description="art walk happening")
        topics = [Topic(name="Arts", keywords=["art"])]
        tag_events([event], topics)
        assert event.topics == ["Arts"]

    def test_multiple_events(self):
        """Multiple events are tagged independently."""
        event1 = Event(title="Art Walk", organizer="Org1")
        event2 = Event(title="Music Festival", organizer="Org2")
        topics = [
            Topic(name="Arts", keywords=["art"]),
            Topic(name="Music", keywords=["music"])
        ]
        tag_events([event1, event2], topics)
        assert event1.topics == ["Arts"]
        assert event2.topics == ["Music"]


class TestTopicsFromAirtable:
    """Test the topics_from_airtable function."""

    class FakeTable:
        """Fake Airtable table for testing."""
        def __init__(self, records):
            self.records = records

        def all(self):
            return self.records

    def test_basic_load(self):
        """Load basic topics from Airtable."""
        table = self.FakeTable([
            {
                "id": "rec1",
                "fields": {
                    "Topic": "Arts",
                    "Keywords": "art, painting",
                    "Aliases": "",
                    "Exclusions": "",
                    "Active": True
                }
            }
        ])
        topics = topics_from_airtable(table)
        assert len(topics) == 1
        assert topics[0].name == "Arts"
        assert topics[0].keywords == ["art", "painting"]
        assert topics[0].active is True

    def test_skip_missing_topic_name(self):
        """Skip records with missing Topic field."""
        table = self.FakeTable([
            {"id": "rec1", "fields": {"Keywords": "art", "Active": True}},
            {"id": "rec2", "fields": {"Topic": "Arts", "Keywords": "art", "Active": True}}
        ])
        topics = topics_from_airtable(table)
        assert len(topics) == 1
        assert topics[0].name == "Arts"

    def test_skip_empty_topic_name(self):
        """Skip records with empty Topic field."""
        table = self.FakeTable([
            {"id": "rec1", "fields": {"Topic": "", "Keywords": "art"}},
            {"id": "rec2", "fields": {"Topic": "Arts", "Keywords": "art"}}
        ])
        topics = topics_from_airtable(table)
        assert len(topics) == 1
        assert topics[0].name == "Arts"

    def test_aliases_as_additional_keywords(self):
        """Aliases are appended to keywords."""
        table = self.FakeTable([
            {
                "id": "rec1",
                "fields": {
                    "Topic": "Arts",
                    "Keywords": "art, painting",
                    "Aliases": "visual, creativity",
                    "Exclusions": "",
                    "Active": True
                }
            }
        ])
        topics = topics_from_airtable(table)
        assert topics[0].keywords == ["art", "painting", "visual", "creativity"]

    def test_exclusions(self):
        """Exclusions field is parsed."""
        table = self.FakeTable([
            {
                "id": "rec1",
                "fields": {
                    "Topic": "Arts",
                    "Keywords": "art",
                    "Aliases": "",
                    "Exclusions": "commercial, corporate",
                    "Active": True
                }
            }
        ])
        topics = topics_from_airtable(table)
        assert topics[0].exclusions == ["commercial", "corporate"]

    def test_active_checkbox_true(self):
        """Active checkbox present = True."""
        table = self.FakeTable([
            {
                "id": "rec1",
                "fields": {
                    "Topic": "Arts",
                    "Keywords": "art",
                    "Aliases": "",
                    "Exclusions": "",
                    "Active": True
                }
            }
        ])
        topics = topics_from_airtable(table)
        assert topics[0].active is True

    def test_active_checkbox_absent_defaults_to_false(self):
        """Active checkbox absent (Airtable omits unchecked) = False."""
        table = self.FakeTable([
            {
                "id": "rec1",
                "fields": {
                    "Topic": "Arts",
                    "Keywords": "art",
                    "Aliases": "",
                    "Exclusions": ""
                }
            }
        ])
        topics = topics_from_airtable(table)
        assert topics[0].active is False

    def test_loader_returns_inactive_topics(self):
        """Loader returns inactive topics with active=False (tag_events skips them)."""
        table = self.FakeTable([
            {
                "id": "rec1",
                "fields": {
                    "Topic": "Arts",
                    "Keywords": "art",
                    "Active": False
                }
            }
        ])
        topics = topics_from_airtable(table)
        assert len(topics) == 1
        assert topics[0].active is False


class TestLoadTopicsCsv:
    """Test the load_topics_csv function."""

    def test_load_from_csv(self, tmp_path):
        """Load topics from CSV file."""
        csv_file = tmp_path / "topics.csv"
        csv_file.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Arts,\"art, painting\",,commercial,yes\n",
            encoding="utf-8"
        )
        topics = load_topics_csv(str(csv_file))
        assert len(topics) == 1
        assert topics[0].name == "Arts"
        assert topics[0].keywords == ["art", "painting"]
        assert topics[0].active is True

    def test_csv_skip_empty_topic(self, tmp_path):
        """Skip rows with empty topic in CSV."""
        csv_file = tmp_path / "topics.csv"
        csv_file.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            ",art,,\n"
            "Arts,painting,,\n",
            encoding="utf-8"
        )
        topics = load_topics_csv(str(csv_file))
        assert len(topics) == 1
        assert topics[0].name == "Arts"

    def test_csv_aliases_appended(self, tmp_path):
        """CSV aliases are appended to keywords."""
        csv_file = tmp_path / "topics.csv"
        csv_file.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Arts,\"art, painting\",\"visual, creativity\",,yes\n",
            encoding="utf-8"
        )
        topics = load_topics_csv(str(csv_file))
        assert topics[0].keywords == ["art", "painting", "visual", "creativity"]

    def test_csv_active_parsing(self, tmp_path):
        """CSV active field parses yes/true/1 case-insensitive as True."""
        csv_file = tmp_path / "topics.csv"
        csv_file.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Arts1,art,,,yes\n"
            "Arts2,art,,,true\n"
            "Arts3,art,,,1\n"
            "Arts4,art,,,YES\n"
            "Arts5,art,,,no\n",
            encoding="utf-8"
        )
        topics = load_topics_csv(str(csv_file))
        assert topics[0].active is True  # yes
        assert topics[1].active is True  # true
        assert topics[2].active is True  # 1
        assert topics[3].active is True  # YES
        assert topics[4].active is False  # no

    def test_csv_exclusions(self, tmp_path):
        """CSV exclusions field is parsed."""
        csv_file = tmp_path / "topics.csv"
        csv_file.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Arts,art,,\"commercial, corporate\",yes\n",
            encoding="utf-8"
        )
        topics = load_topics_csv(str(csv_file))
        assert topics[0].exclusions == ["commercial", "corporate"]

    def test_csv_utf8_encoding(self, tmp_path):
        """CSV is read with UTF-8 encoding."""
        csv_file = tmp_path / "topics.csv"
        csv_file.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Café,\"café, arts\",,\n",
            encoding="utf-8"
        )
        topics = load_topics_csv(str(csv_file))
        assert topics[0].name == "Café"
        assert "café" in topics[0].keywords
