"""Topic classifier using keyword and exclusion matching."""

import re
import csv
from pathlib import Path
from abundroid.models import Topic


def split_terms(s: str | None) -> list[str]:
    """
    Split a comma-separated string into terms.

    - Strip whitespace from each term
    - Drop empty terms
    - Preserve original case
    - None or empty input returns []
    """
    if not s:
        return []

    terms = s.split(",")
    result = []
    for term in terms:
        term = term.strip()
        if term:
            result.append(term)
    return result


def tag_items(items, topics: list[Topic]) -> None:
    '''Tag published items using their title and summary.'''
    for item in items:
        text = (item.title or '') + ' ' + (item.summary or '')

        for topic in topics:
            if not topic.active or not topic.keywords:
                continue

            if any(
                re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.IGNORECASE)
                for term in topic.exclusions
            ):
                continue

            if any(
                re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.IGNORECASE)
                for term in topic.keywords
            ) and topic.name not in item.topics:
                item.topics.append(topic.name)


def topics_from_airtable(table) -> list[Topic]:
    """
    Load topics from an Airtable-compatible table.

    Expected fields: Topic, Keywords, Aliases, Exclusions, Active
    - Keywords and Aliases are comma-separated strings (aliases appended after keywords)
    - Exclusions is comma-separated
    - Active is a checkbox (absent/False means False, present/True means True)
    - Skip records with missing/empty Topic field
    """
    topics = []

    for record in table.all():
        fields = record.get("fields", {})

        # Get topic name
        topic_name = (fields.get("Topic") or "").strip()
        if not topic_name:
            continue

        # Parse keywords and aliases
        keywords_str = fields.get("Keywords", "")
        aliases_str = fields.get("Aliases", "")
        keywords = split_terms(keywords_str)
        keywords.extend(split_terms(aliases_str))

        # Parse exclusions
        exclusions_str = fields.get("Exclusions", "")
        exclusions = split_terms(exclusions_str)

        # Parse active flag (absent means False)
        active = fields.get("Active", False)

        topic = Topic(
            name=topic_name,
            keywords=keywords,
            exclusions=exclusions,
            active=active
        )
        topics.append(topic)

    return topics


def load_topics_csv(path: str | Path) -> list[Topic]:
    """
    Load topics from a CSV file.

    Expected columns: topic, keywords, aliases, exclusions, active
    - keywords, aliases, exclusions are comma-separated
    - active parses "yes"/"true"/"1" (case-insensitive) as True
    - Skip rows with empty topic
    - File is UTF-8 encoded
    """
    topics = []
    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic_name = (row.get("topic") or "").strip()
            if not topic_name:
                continue

            # Parse keywords and aliases
            keywords_str = row.get("keywords", "")
            aliases_str = row.get("aliases", "")
            keywords = split_terms(keywords_str)
            keywords.extend(split_terms(aliases_str))

            # Parse exclusions
            exclusions_str = row.get("exclusions", "")
            exclusions = split_terms(exclusions_str)

            # Parse active flag
            active_str = (row.get("active", "") or "").strip().lower()
            active = active_str in ("yes", "true", "1")

            topic = Topic(
                name=topic_name,
                keywords=keywords,
                exclusions=exclusions,
                active=active
            )
            topics.append(topic)

    return topics
