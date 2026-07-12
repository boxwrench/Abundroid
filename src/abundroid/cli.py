"""Command-line interface for Abundroid."""

import argparse
import os
import sys
from pathlib import Path

from abundroid.stores.csv_store import load_organizations as load_orgs_csv, CsvEventStore
from abundroid.stores.airtable_store import load_organizations as load_orgs_airtable, AirtableEventStore
from abundroid.classifier import topics_from_airtable, load_topics_csv
from abundroid.pipeline import run_pipeline


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


def main(argv=None):
    """
    Main CLI entry point.

    Returns 0 if all organizations succeeded, 1 if any failed.
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

    args = parser.parse_args(argv)

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
    any_failed = False
    for summary in summaries:
        org = summary["org"]
        ok = summary["ok"]
        error = summary["error"]
        events_found = summary["events_found"]
        new = summary["new"]
        seen = summary["seen"]
        total_new += new
        total_seen += seen

        if not ok:
            any_failed = True

        cancelled = summary.get("possibly_cancelled", 0)
        cancelled_note = f", {cancelled} possibly cancelled" if cancelled else ""
        if ok:
            print(f"{org}: ok, {events_found} found, {new} new, {seen} seen{cancelled_note}")
        else:
            print(f"{org}: error ({error}), {events_found} found, {new} new, {seen} seen{cancelled_note}")

    # Print totals
    print(f"Totals: {total_new} new, {total_seen} seen")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
