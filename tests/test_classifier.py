"""Tests for Item topic tagging and topic configuration loading."""

from abundroid.classifier import (
    load_topics_csv,
    split_terms,
    tag_items,
    topics_from_airtable,
)
from abundroid.models import Item, Topic


def test_split_terms_strips_whitespace_and_drops_empty_values():
    assert split_terms(" art, ,Zoning Reform, ") == ["art", "Zoning Reform"]
    assert split_terms(None) == []


def test_tag_items_matches_title_and_summary_on_word_boundaries():
    items = [
        Item(title="Zoning reform update", publisher="One"),
        Item(title="Startup funding", publisher="Two", summary="More housing"),
    ]
    topics = [
        Topic(name="Housing", keywords=["zoning", "housing"]),
        Topic(name="Arts", keywords=["art"]),
    ]

    tag_items(items, topics)

    assert items[0].topics == ["Housing"]
    assert items[1].topics == ["Housing"]


def test_tag_items_honors_exclusions_activity_and_existing_topics():
    item = Item(
        title="Commercial solar project",
        publisher="Publisher",
        topics=["Existing"],
    )
    topics = [
        Topic(name="Energy", keywords=["solar"], exclusions=["commercial"]),
        Topic(name="Inactive", keywords=["solar"], active=False),
        Topic(name="Existing", keywords=["solar"]),
    ]

    tag_items([item], topics)

    assert item.topics == ["Existing"]


class FakeTable:
    def __init__(self, records):
        self.records = records

    def all(self):
        return self.records


def test_topics_from_airtable_parses_rules_and_skips_unnamed_records():
    table = FakeTable([
        {"id": "skip", "fields": {"Keywords": "ignored"}},
        {
            "id": "topic",
            "fields": {
                "Topic": "Housing",
                "Keywords": "housing, zoning",
                "Aliases": "homes",
                "Exclusions": "housing market",
                "Active": True,
            },
        },
    ])

    topics = topics_from_airtable(table)

    assert len(topics) == 1
    assert topics[0].name == "Housing"
    assert topics[0].keywords == ["housing", "zoning", "homes"]
    assert topics[0].exclusions == ["housing market"]
    assert topics[0].active is True


def test_topics_from_airtable_defaults_missing_active_to_false():
    [topic] = topics_from_airtable(
        FakeTable([{"fields": {"Topic": "Housing", "Keywords": "homes"}}])
    )

    assert topic.active is False


def test_load_topics_csv_parses_aliases_exclusions_and_activity(tmp_path):
    path = tmp_path / "topics.csv"
    path.write_text(
        "topic,keywords,aliases,exclusions,active\n"
        'Housing,"housing,zoning",homes,"housing market",yes\n'
        ",ignored,,,yes\n",
        encoding="utf-8",
    )

    [topic] = load_topics_csv(path)

    assert topic.name == "Housing"
    assert topic.keywords == ["housing", "zoning", "homes"]
    assert topic.exclusions == ["housing market"]
    assert topic.active is True
