"""Builder that creates the Abundroid Airtable base from the declarative schema."""

from __future__ import annotations

import os


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
