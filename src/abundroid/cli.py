"""Command-line interface for Abundroid."""

import argparse
import os
import sys
from pathlib import Path

from abundroid.classifier import load_topics_csv, topics_from_airtable
from abundroid.item_pipeline import run_item_pipeline
from abundroid.stores.item_airtable_store import (
    AirtableItemStore,
    load_sources as load_sources_airtable,
)
from abundroid.stores.item_csv_store import (
    CsvItemStore,
    load_sources as load_sources_csv,
)


def load_env(path=".env"):
    """Load simple KEY=VALUE entries without overriding the process environment."""
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _airtable_credentials():
    """Return a complete Airtable credential pair or the CSV-mode pair."""
    key = os.environ.get("AIRTABLE_API_KEY", "").strip()
    base_id = os.environ.get("AIRTABLE_BASE_ID", "").strip()
    if bool(key) != bool(base_id):
        raise ValueError(
            "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must both be set, or neither"
        )
    return key, base_id


class DryRunItemStore:
    """Print collected Items instead of persisting them."""

    def recent_items(self, since=None):
        return []

    def upsert(self, items):
        for item in items:
            published = item.published_at.isoformat() if item.published_at else "No date"
            print(
                f"  [{item.kind}] {item.title} ({published}) - "
                f"{item.canonical_url} [{item.uid}]"
            )
        return {"new": len(items), "seen": 0}


def _load_airtable_topics(api, base_id):
    table = api.table(base_id, os.environ.get("AIRTABLE_TOPICS_TABLE", "Topics"))
    return topics_from_airtable(table)


def run_collect(args):
    """Run the published-items pipeline."""
    try:
        airtable_key, airtable_base = _airtable_credentials()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        if airtable_key:
            import pyairtable

            api = pyairtable.Api(airtable_key)
            organizations = api.table(
                airtable_base,
                os.environ.get("AIRTABLE_ORGS_TABLE", "Organizations"),
            )
            source_table = api.table(
                airtable_base,
                os.environ.get("AIRTABLE_SOURCES_TABLE", "Sources"),
            )
            item_table = api.table(
                airtable_base,
                os.environ.get("AIRTABLE_ITEMS_TABLE", "Items"),
            )
            sources = load_sources_airtable(source_table, organizations)
            topics = _load_airtable_topics(api, airtable_base)
            item_store = (
                DryRunItemStore() if args.dry_run else AirtableItemStore(item_table)
            )
        else:
            sources = load_sources_csv(args.sources)
            topics = load_topics_csv(args.topics) if os.path.exists(args.topics) else []
            item_store = DryRunItemStore() if args.dry_run else CsvItemStore(args.out)
    except Exception as exc:
        print(f"Error loading collection configuration: {exc}", file=sys.stderr)
        return 1

    source_run_store = None
    if not args.dry_run:
        if airtable_key:
            from abundroid.stores.source_run_airtable_store import AirtableSourceRunStore

            table = api.table(
                airtable_base,
                os.environ.get("AIRTABLE_SOURCE_RUNS_TABLE", "Source Runs"),
            )
            source_run_store = AirtableSourceRunStore(table)
        else:
            from abundroid.stores.source_run_csv_store import SourceRunCsvStore

            source_run_store = SourceRunCsvStore(Path(args.out).parent / "source_runs.csv")

    try:
        result = run_item_pipeline(sources, item_store, topics=topics)
    except Exception as exc:
        print(f"Error running collection: {exc}", file=sys.stderr)
        return 1

    any_failed = False
    for summary in result["sources"]:
        if summary["ok"]:
            print(f"{summary['source']}: ok, {summary['items_found']} found")
        else:
            print(f"{summary['source']}: error ({summary['error']})")
            any_failed = True
    print(
        "Totals: {} found, {} new, {} seen".format(
            result["items_found"], result["new"], result["seen"]
        )
    )

    if source_run_store is not None:
        try:
            source_run_store.save_runs(result["source_runs"])
        except Exception as exc:
            print(f"Error saving source runs: {exc}", file=sys.stderr)
            return 1

    return 1 if any_failed else 0


def main(argv=None):
    """Parse arguments and run the requested command."""
    load_env()

    parser = argparse.ArgumentParser(prog="abundroid")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand")
    collect = subparsers.add_parser(
        "collect", help="Collect articles, posts, updates, and other published items"
    )
    collect.add_argument(
        "--sources",
        default="data/sources.csv",
        help="Path to sources CSV (default: data/sources.csv)",
    )
    collect.add_argument(
        "--out",
        default="output/items.csv",
        help="Path to output Items CSV (default: output/items.csv)",
    )
    collect.add_argument(
        "--topics",
        default="data/topics.csv",
        help="Path to topics CSV for tagging",
    )
    collect.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse Items without writing them",
    )

    args = parser.parse_args(argv)
    if args.command == "collect":
        return run_collect(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
