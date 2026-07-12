"""Focused tests for unified Item CSV persistence."""

import csv
from datetime import date, datetime, timedelta

from abundroid.models import Item
from abundroid.stores.item_csv_store import CsvItemStore, load_sources


def item(uid: str = "guid:feed:one", **changes) -> Item:
    values = {
        "title": "Original title",
        "publisher": "Publisher",
        "kind": "article",
        "uid": uid,
        "source_item_id": "one",
        "canonical_url": "https://example.com/one",
        "source_url": "https://example.com/feed.xml",
        "published_at": datetime(2026, 7, 1, 9, 30),
        "author": "Author",
        "summary": "Source summary",
        "topics": ["Housing"],
        "source_hash": "hash-one",
    }
    values.update(changes)
    return Item(**values)


def read_rows(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_load_sources_parses_active_and_skips_unusable_rows(tmp_path):
    path = tmp_path / "sources.csv"
    path.write_text(
        "organization,name,url,format,default_kind,active,notes\n"
        "Org A,Newsroom,https://a.example/feed.xml,rss,article,YES,Main feed\n"
        "Org B,Updates,https://b.example/feed.xml,rss,update,0,Paused\n"
        ",Missing owner,https://bad.example/feed.xml,rss,article,true,\n"
        "Org C,Missing URL,,rss,article,true,\n",
        encoding="utf-8",
    )

    sources = load_sources(path)

    assert len(sources) == 2
    assert sources[0].organization == "Org A"
    assert sources[0].active is True
    assert sources[0].default_kind == "article"
    assert sources[1].active is False


def test_upsert_new_items_writes_complete_review_row(tmp_path):
    path = tmp_path / "items.csv"
    result = CsvItemStore(path).upsert([item()])

    assert result == {"new": 1, "seen": 0}
    row = read_rows(path)[0]
    assert row["uid"] == "guid:feed:one"
    assert row["source_item_id"] == "one"
    assert row["status"] == "Needs Review"
    assert row["topics"] == "Housing"
    assert row["first_seen"] == date.today().isoformat()
    assert row["last_seen"] == date.today().isoformat()


def test_seen_item_updates_hash_but_preserves_human_edits(tmp_path):
    path = tmp_path / "items.csv"
    store = CsvItemStore(path)
    store.upsert([item()])
    row = read_rows(path)[0]
    row.update(
        {
            "title": "Reviewed title",
            "summary": "Reviewed summary",
            "topics": "Reviewed Topic",
            "status": "Approved",
            "reviewer_notes": "Keep this wording",
        }
    )
    store._write_rows([row])

    result = store.upsert(
        [item(title="Changed at source", summary="Changed source summary", source_hash="hash-two")]
    )

    assert result == {"new": 0, "seen": 1}
    updated = read_rows(path)[0]
    assert updated["title"] == "Reviewed title"
    assert updated["summary"] == "Reviewed summary"
    assert updated["topics"] == "Reviewed Topic"
    assert updated["status"] == "Approved"
    assert updated["reviewer_notes"] == "Keep this wording"
    assert updated["source_hash"] == "hash-two"
    assert updated["changed"] == "yes"


def test_recent_items_filters_on_persisted_last_seen(tmp_path):
    path = tmp_path / "items.csv"
    store = CsvItemStore(path)
    store.upsert([item("old"), item("recent")])
    rows = read_rows(path)
    rows[0]["last_seen"] = (date.today() - timedelta(days=10)).isoformat()
    store._write_rows(rows)

    recent = store.recent_items(datetime.now() - timedelta(days=2))

    assert [stored.uid for stored in recent] == ["recent"]


def test_set_possible_duplicates_only_changes_duplicate_field(tmp_path):
    path = tmp_path / "items.csv"
    store = CsvItemStore(path)
    store.upsert([item()])
    before = read_rows(path)[0]

    assert store.set_possible_duplicates({"guid:feed:one": "guid:other:one", "missing": "x"}) == 1
    after = read_rows(path)[0]
    assert after["possible_duplicate_of"] == "guid:other:one"
    assert {key: value for key, value in after.items() if key != "possible_duplicate_of"} == {
        key: value for key, value in before.items() if key != "possible_duplicate_of"
    }


def test_upsert_does_not_replace_reviewed_duplicate_link(tmp_path):
    path = tmp_path / "items.csv"
    store = CsvItemStore(path)
    store.upsert([item(possible_duplicate_of="reviewed-match")])

    store.upsert([item(possible_duplicate_of="new-suggestion")])

    assert read_rows(path)[0]["possible_duplicate_of"] == "reviewed-match"
