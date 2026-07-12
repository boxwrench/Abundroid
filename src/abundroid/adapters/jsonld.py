"""JSON-LD adapter for parsing schema.org structured data."""

import json
from html.parser import HTMLParser
from urllib.parse import urljoin

from dateutil import parser as date_parser

from abundroid.models import Event, Organization


class JSONLDExtractor(HTMLParser):
    """Extract JSON-LD script blocks from HTML."""

    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self.jsonld_blocks = []
        self.current_script_content = None
        self.in_jsonld_script = False

    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        if tag == "script":
            # Check if type attribute is "application/ld+json" (case-insensitive)
            for attr_name, attr_value in attrs:
                if attr_name.lower() == "type" and attr_value and attr_value.lower() == "application/ld+json":
                    self.in_jsonld_script = True
                    self.current_script_content = ""
                    break

    def handle_data(self, data):
        """Handle script content."""
        if self.in_jsonld_script:
            self.current_script_content += data

    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag == "script" and self.in_jsonld_script:
            self.in_jsonld_script = False
            if self.current_script_content:
                self.jsonld_blocks.append(self.current_script_content)
            self.current_script_content = None


def _is_event_type(type_value):
    """
    Check if a type value represents an event.

    Type can be a string ending in 'Event' or a list containing such a string.
    """
    if isinstance(type_value, str):
        return type_value.endswith("Event")
    if isinstance(type_value, list):
        return any(isinstance(t, str) and t.endswith("Event") for t in type_value)
    return False


def _parse_date(date_str):
    """
    Parse a date string using dateutil.

    First tries isoparse, then parse. Returns None if both fail.
    Preserves timezone information exactly as given.
    """
    if not date_str:
        return None

    try:
        return date_parser.isoparse(date_str)
    except (ValueError, TypeError):
        pass

    try:
        return date_parser.parse(date_str)
    except (ValueError, TypeError):
        return None


def _resolve_location(location_data):
    """
    Resolve location from various possible formats.

    - string → use stripped
    - dict with "@type" == "VirtualLocation" → "Virtual"
    - dict otherwise → its "name" if non-empty string; else derive from "address"
    - list → resolve the first element that yields a non-empty string
    - missing/anything else → ""
    """
    if not location_data:
        return ""

    if isinstance(location_data, str):
        return location_data.strip()

    if isinstance(location_data, dict):
        # Check for VirtualLocation
        if location_data.get("@type") == "VirtualLocation":
            return "Virtual"

        # Try to use "name" field
        name = location_data.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

        # Try to derive from "address"
        address = location_data.get("address")
        if isinstance(address, str) and address.strip():
            return address.strip()
        if isinstance(address, dict):
            # Join present values of streetAddress, addressLocality, addressRegion
            parts = []
            for key in ["streetAddress", "addressLocality", "addressRegion"]:
                val = address.get(key)
                if val and isinstance(val, str) and val.strip():
                    parts.append(val.strip())
            if parts:
                return ", ".join(parts)

        return ""

    if isinstance(location_data, list):
        # Resolve the first element that yields a non-empty string
        for item in location_data:
            resolved = _resolve_location(item)
            if resolved:
                return resolved
        return ""

    return ""


def _collect_event_nodes(data):
    """
    Collect all candidate nodes from parsed JSON-LD data.

    Data may be a single dict, a list of dicts, a dict with "@graph", or an
    ItemList whose "itemListElement" entries hold events either directly or
    wrapped in ListItem "item" objects (the shape Eventbrite and Luma listing
    pages use). Containers may nest, e.g. an ItemList inside a @graph.
    """
    nodes = []

    if isinstance(data, dict):
        if "@graph" in data:
            graph = data["@graph"]
            if isinstance(graph, list):
                for entry in graph:
                    nodes.extend(_collect_event_nodes(entry))
        elif "itemListElement" in data:
            elements = data["itemListElement"]
            if isinstance(elements, list):
                for element in elements:
                    if isinstance(element, dict):
                        item = element.get("item")
                        if isinstance(item, dict):
                            nodes.append(item)
                        else:
                            nodes.append(element)
        else:
            nodes.append(data)
    elif isinstance(data, list):
        for entry in data:
            nodes.extend(_collect_event_nodes(entry))

    return nodes


def parse(text: str, org: Organization) -> list[Event]:
    """
    Parse JSON-LD structured data from an HTML page and extract events.

    Extracts schema.org Event objects from <script type="application/ld+json"> tags.
    Handles various data structures: single objects, arrays, and @graph containers.
    Skips malformed JSON blocks, non-event objects, and events without a name.

    Args:
        text: Full HTML page content as a string.
        org: Organization metadata to associate with extracted events.

    Returns:
        List of Event objects extracted from JSON-LD blocks in the page.
    """
    # Extract JSON-LD script blocks from HTML
    extractor = JSONLDExtractor()
    extractor.feed(text)
    jsonld_blocks = extractor.jsonld_blocks

    events = []

    # Process each JSON-LD block
    for block in jsonld_blocks:
        # Try to parse the JSON
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            # Silently skip malformed JSON blocks
            continue

        # Collect all candidate event nodes
        nodes = _collect_event_nodes(data)

        # Process each node
        for node in nodes:
            if not isinstance(node, dict):
                continue

            # Check if this is an event
            if not _is_event_type(node.get("@type")):
                continue

            # Extract and validate title
            title = node.get("name")
            if not isinstance(title, str) or not title.strip():
                # Skip nodes without a proper name
                continue
            title = title.strip()

            # Extract dates
            start = _parse_date(node.get("startDate"))
            end = _parse_date(node.get("endDate"))

            # Extract and resolve URL
            url = node.get("url", "")
            if not isinstance(url, str):
                url = ""
            elif url:
                # Resolve relative URLs against org.events_url
                url = urljoin(org.events_url, url)

            description = node.get("description", "")
            if isinstance(description, str):
                description = description.strip()
            else:
                description = ""

            # Resolve location
            location = _resolve_location(node.get("location"))

            # Build event
            event = Event(
                title=title,
                organizer=org.name,
                url=url,
                start=start,
                end=end,
                location=location,
                description=description,
                source_url=org.events_url,
                uid=""
            )
            events.append(event)

    return events
