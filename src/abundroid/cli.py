"""Command-line interface for Abundroid."""

import argparse
import os
import sys
import textwrap
from pathlib import Path

from abundroid import setup_base
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

    DESCRIPTION_LIMIT = 360

    def recent_items(self, since=None):
        return []

    def upsert(self, items):
        for item in items:
            if item.published_at:
                published = (
                    f"{item.published_at.strftime('%b')} "
                    f"{item.published_at.day}, {item.published_at.year}"
                )
            else:
                published = "No date"

            description = " ".join((item.summary or "").split())
            if not description:
                description = "No description supplied by source."
            elif len(description) > self.DESCRIPTION_LIMIT:
                cutoff = description.rfind(" ", 0, self.DESCRIPTION_LIMIT - 3)
                if cutoff < 1:
                    cutoff = self.DESCRIPTION_LIMIT - 3
                description = f"{description[:cutoff].rstrip()}..."

            publisher = item.publisher or "Unknown publisher"
            link = item.canonical_url or "No original link supplied by source."
            kind = (item.kind or "other").upper()
            print(f"[{kind}] {item.title}")
            print(f"  {publisher} | {published}")
            if item.author:
                print(f"  By {item.author}")
            if item.topics:
                print(f"  Topics: {', '.join(item.topics)}")
            for line in textwrap.wrap(description, width=76):
                print(f"  {line}")
            print(f"  Link: {link}")
            print()
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


def _make_setup_api(token):
    import pyairtable

    return pyairtable.Api(token)


def run_setup(args):
    """Create the Abundroid Airtable base from the declarative schema."""
    token = os.environ.get("AIRTABLE_SETUP_TOKEN", "").strip()
    workspace = os.environ.get("AIRTABLE_WORKSPACE_ID", "").strip()
    if not token or not workspace:
        print(
            "Error: set AIRTABLE_SETUP_TOKEN (a one-time token with "
            "schema.bases:write) and AIRTABLE_WORKSPACE_ID (from the Airtable "
            "URL, the wsp... segment). Do not put these in .env.",
            file=sys.stderr,
        )
        return 1

    api = _make_setup_api(token)
    try:
        base_id = setup_base.build_base(api, workspace, seed=not args.no_seed)
    except Exception as exc:
        print(
            f"Error creating base: {exc}\n"
            "If a partial 'Abundroid' base was created, delete it in Airtable "
            "before running setup again.",
            file=sys.stderr,
        )
        return 1

    print(f"Created base {base_id}.")
    setup_base.write_base_id_to_env(base_id)
    print("Wrote AIRTABLE_BASE_ID to .env.")
    print("Next steps (not automatable via the Airtable API):")
    print("  1. Build the 9 saved views (airtable-schema.md section 9).")
    print("  2. Build the 3 Interface pages (airtable-schema.md sections 10-11).")
    print("  3. Create the minimal runtime token: data.records:read + "
          "data.records:write, scoped to this base (section 12).")
    print("  4. Revoke the AIRTABLE_SETUP_TOKEN now that setup is complete.")
    return 0


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

    setup_parser = subparsers.add_parser(
        "setup", help="Create the Abundroid Airtable base, fields, and seed rows"
    )
    setup_parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip creating the Hypertext example Organization and Source",
    )

    args = parser.parse_args(argv)
    if args.command == "collect":
        return run_collect(args)
    if args.command == "setup":
        return run_setup(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
