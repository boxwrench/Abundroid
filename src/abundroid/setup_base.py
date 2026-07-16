"""Builder that creates the Abundroid Airtable base from the declarative schema."""

from __future__ import annotations

import os

from abundroid import airtable_schema as schema


def env_text_with_base_id(existing_text: str, base_id: str) -> str:
    """Return env-file text with AIRTABLE_BASE_ID set to base_id (upsert)."""
    line = f"AIRTABLE_BASE_ID={base_id}"
    lines = existing_text.splitlines()
    replaced = False
    for i, raw in enumerate(lines):
        if raw.strip().startswith("AIRTABLE_BASE_ID="):
            lines[i] = line
            replaced = True
            break
    if not replaced:
        lines.append(line)
    return "\n".join(lines) + "\n"


def write_base_id_to_env(base_id: str, env_path: str = ".env", example_path: str = ".env.example") -> None:
    """Create .env from the example if missing, then upsert the base ID line."""
    if not os.path.exists(env_path) and os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as example:
            existing = example.read()
    elif os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as env_file:
            existing = env_file.read()
    else:
        existing = ""
    with open(env_path, "w", encoding="utf-8") as env_file:
        env_file.write(env_text_with_base_id(existing, base_id))


def _field_id(table, field_name):
    for field in table.schema().fields:
        if field.name == field_name:
            return field.id
    raise KeyError(f"field {field_name!r} not found on table {table.name!r}")


def build_base(api, workspace_id, *, seed: bool = True) -> str:
    """Create the Abundroid base, its link/lookup fields, and (optionally) seed rows."""
    base = api.create_base(workspace_id, schema.BASE_NAME, schema.SIMPLE_TABLES)
    tables = {t.name: t for t in base.tables()}

    for link in schema.LINK_FIELDS:
        linked_id = tables[link["linked_table"]].id
        # Airtable's create-field endpoint rejects prefersSingleRecordLink and
        # its field-update endpoint only changes name/description, so the
        # single-record-link preference cannot be set through the API. The field
        # is created link-capable-to-many; the seed and collector use one link.
        tables[link["table"]].create_field(
            link["name"],
            "multipleRecordLinks",
            options={"linkedTableId": linked_id},
        )

    for lookup in schema.LOOKUP_FIELDS:
        table = tables[lookup["table"]]
        link_field_id = _field_id(table, lookup["via_link_field"])
        linked_field_id = _field_id(tables[lookup["linked_table"]], lookup["linked_field"])
        table.create_field(
            lookup["name"],
            "multipleLookupValues",
            options={"recordLinkFieldId": link_field_id, "fieldIdInLinkedTable": linked_field_id},
        )

    if seed:
        org = tables["Organizations"].create(dict(schema.SEED_ORGANIZATION))
        source_fields = dict(schema.SEED_SOURCE)
        source_fields["Organization"] = [org["id"]]
        tables["Sources"].create(source_fields)

    return base.id
