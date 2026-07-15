# tests/test_setup_base.py
from abundroid import setup_base


def test_env_text_appends_when_absent():
    out = setup_base.env_text_with_base_id("AIRTABLE_API_KEY=pat_x\n", "appABC123")
    assert "AIRTABLE_API_KEY=pat_x" in out
    assert "AIRTABLE_BASE_ID=appABC123" in out


def test_env_text_replaces_placeholder():
    existing = "AIRTABLE_API_KEY=pat_x\nAIRTABLE_BASE_ID=app_your_base_id\n"
    out = setup_base.env_text_with_base_id(existing, "appREAL999")
    assert "AIRTABLE_BASE_ID=appREAL999" in out
    assert "app_your_base_id" not in out
    assert out.count("AIRTABLE_BASE_ID=") == 1


def test_env_text_never_duplicates_on_repeat():
    once = setup_base.env_text_with_base_id("", "appONE")
    twice = setup_base.env_text_with_base_id(once, "appTWO")
    assert twice.count("AIRTABLE_BASE_ID=") == 1
    assert "AIRTABLE_BASE_ID=appTWO" in twice


def test_write_creates_env_from_example(tmp_path):
    example = tmp_path / ".env.example"
    example.write_text("AIRTABLE_API_KEY=pat_your_token\nAIRTABLE_BASE_ID=app_your_base_id\n", encoding="utf-8")
    env = tmp_path / ".env"
    setup_base.write_base_id_to_env("appXYZ", env_path=str(env), example_path=str(example))
    text = env.read_text(encoding="utf-8")
    assert "AIRTABLE_BASE_ID=appXYZ" in text
    assert "AIRTABLE_API_KEY=pat_your_token" in text
