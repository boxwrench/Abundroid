"""Command-line interface for Abundroid."""

import argparse
import os
import sys
from pathlib import Path

from abundroid.stores.csv_store import load_organizations as load_orgs_csv, CsvEventStore
from abundroid.stores.airtable_store import load_organizations as load_orgs_airtable, AirtableEventStore
from abundroid.classifier import topics_from_airtable, load_topics_csv
from abundroid.pipeline import run_pipeline
from abundroid.item_pipeline import run_item_pipeline
from abundroid.stores.item_csv_store import (
    CsvItemStore,
    load_sources as load_sources_csv,
)
from abundroid.stores.item_airtable_store import (
    AirtableItemStore,
    load_sources as load_sources_airtable,
)


def load_env(path=".env"):
    """
    Load environment variables from a .env file.

    Parses KEY=VALUE lines (skip blanks and # comments).
    Sets each via os.environ.setdefault.
    """
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip blank lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            os.environ.setdefault(key, value)


class DryRunStore:
    """Wrapper store that prints events instead of persisting."""

    def __init__(self):
        """Initialize."""
        pass

    def upsert(self, events):
        """Print events and return fake counts."""
        for event in events:
            # Print: title, start, url, uid
            start_str = event.start.isoformat() if event.start else "No date"
            print(f"  {event.title} ({start_str}) - {event.url} [{event.uid}]")
        return {"new": len(events), "seen": 0}


class DryRunItemStore:
    '''Print collected Items instead of persisting them.'''

    def recent_items(self, since=None):
        return []

    def upsert(self, items):
        for item in items:
            published = item.published_at.isoformat() if item.published_at else 'No date'
            print(
                f'  [{item.kind}] {item.title} ({published}) - '
                f'{item.canonical_url} [{item.uid}]'
            )
        return {'new': len(items), 'seen': 0}


def _load_airtable_topics(api, base_id):
    try:
        topics_table = api.table(
            base_id,
            os.environ.get('AIRTABLE_TOPICS_TABLE', 'Topics'),
        )
        return topics_from_airtable(topics_table)
    except Exception as exc:
        print(f'Warning: could not load Topics table ({exc}); tagging skipped')
        return []


def run_collect(args):
    '''Run the unified published-items pipeline.'''
    airtable_key = os.environ.get('AIRTABLE_API_KEY', '').strip()
    airtable_base = os.environ.get('AIRTABLE_BASE_ID', '').strip()

    if airtable_key and airtable_base:
        import pyairtable

        api = pyairtable.Api(airtable_key)
        orgs_table = api.table(
            airtable_base,
            os.environ.get('AIRTABLE_ORGS_TABLE', 'Organizations'),
        )
        sources_table = api.table(
            airtable_base,
            os.environ.get('AIRTABLE_SOURCES_TABLE', 'Sources'),
        )
        items_table = api.table(
            airtable_base,
            os.environ.get('AIRTABLE_ITEMS_TABLE', 'Items'),
        )
        sources = load_sources_airtable(sources_table, orgs_table)
        topics = _load_airtable_topics(api, airtable_base)
        store = DryRunItemStore() if args.dry_run else AirtableItemStore(items_table)
    else:
        sources = load_sources_csv(args.sources)
        topics = load_topics_csv(args.topics) if os.path.exists(args.topics) else []
        store = DryRunItemStore() if args.dry_run else CsvItemStore(args.out)

    result = run_item_pipeline(sources, store, topics=topics)
    for summary in result['sources']:
        name = summary['source']
        if summary['ok']:
            print('{}: ok, {} found'.format(name, summary['items_found']))
        else:
            print('{}: error ({})'.format(name, summary['error']))
    print(
        'Totals: {} found, {} new, {} seen'.format(
            result['items_found'], result['new'], result['seen']
        )
    )
    return 0


def main(argv=None):
    """
    Main CLI entry point.

    Returns 0 on success.
    """
    # Load .env file if present
    load_env()

    parser = argparse.ArgumentParser(prog="abundroid")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Run the event pipeline")
    run_parser.add_argument(
        "--orgs",
        default="data/organizations.csv",
        help="Path to organizations CSV (default: data/organizations.csv)"
    )
    run_parser.add_argument(
        "--out",
        default="output/events.csv",
        help="Path to output events CSV (default: output/events.csv)"
    )
    run_parser.add_argument(
        "--topics",
        default="data/topics.csv",
        help="Path to topics CSV for tagging (default: data/topics.csv; skipped if absent)"
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse but don't write, print events instead"
    )

    collect_parser = subparsers.add_parser(
        'collect', help='Collect articles, posts, updates, and other published items'
    )
    collect_parser.add_argument(
        '--sources',
        default='data/sources.csv',
        help='Path to sources CSV (default: data/sources.csv)',
    )
    collect_parser.add_argument(
        '--out',
        default='output/items.csv',
        help='Path to output Items CSV (default: output/items.csv)',
    )
    collect_parser.add_argument(
        '--topics',
        default='data/topics.csv',
        help='Path to topics CSV for tagging',
    )
    collect_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and parse Items without writing them',
    )

    args = parser.parse_args(argv)

    if args.command == 'collect':
        return run_collect(args)

    if args.command != "run":
        parser.print_help()
        return 0

    # Determine mode: Airtable or CSV
    airtable_key = os.environ.get("AIRTABLE_API_KEY", "").strip()
    airtable_base = os.environ.get("AIRTABLE_BASE_ID", "").strip()

    if airtable_key and airtable_base:
        # Airtable mode
        import pyairtable
        api = pyairtable.Api(airtable_key)
        orgs_table = api.table(
            airtable_base,
            os.environ.get("AIRTABLE_ORGS_TABLE", "Organizations")
        )
        events_table = api.table(
            airtable_base,
            os.environ.get("AIRTABLE_EVENTS_TABLE", "Events")
        )
        orgs = load_orgs_airtable(orgs_table)
        try:
            topics_table = api.table(
                airtable_base,
                os.environ.get("AIRTABLE_TOPICS_TABLE", "Topics")
            )
            topics = topics_from_airtable(topics_table)
        except Exception as e:
            print(f"Warning: could not load Topics table ({e}); tagging skipped")
            topics = []
        if args.dry_run:
            store = DryRunStore()
        else:
            store = AirtableEventStore(events_table)
    else:
        # CSV mode
        orgs = load_orgs_csv(args.orgs)
        if os.path.exists(args.topics):
            topics = load_topics_csv(args.topics)
        else:
            topics = []
        if args.dry_run:
            store = DryRunStore()
        else:
            store = CsvEventStore(args.out)

    # Run pipeline
    summaries = run_pipeline(orgs, store, topics=topics)

    # Print summaries
    total_new = 0
    total_seen = 0
    for summary in summaries:
        org = summary["org"]
        ok = summary["ok"]
        error = summary["error"]
        events_found = summary["events_found"]
        new = summary["new"]
        seen = summary["seen"]
        total_new += new
        total_seen += seen

        cancelled = summary.get("possibly_cancelled", 0)
        cancelled_note = f", {cancelled} possibly cancelled" if cancelled else ""
        if ok:
            print(f"{org}: ok, {events_found} found, {new} new, {seen} seen{cancelled_note}")
        else:
            print(f"{org}: error ({error}), {events_found} found, {new} new, {seen} seen{cancelled_note}")

    # Print totals
    print(f"Totals: {total_new} new, {total_seen} seen")

    return 0


if __name__ == "__main__":
    sys.exit(main())
