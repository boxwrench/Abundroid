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


def test_write_preserves_existing_env_token(tmp_path):
    """Test that real tokens in existing .env are preserved unchanged when updating base ID."""
    # Create .env.example to prove it's NOT used when .env exists
    example = tmp_path / ".env.example"
    example.write_text("AIRTABLE_API_KEY=pat_example_token\nAIRTABLE_BASE_ID=app_your_base_id\n", encoding="utf-8")

    # Create pre-existing .env with real secret and stale base id
    env = tmp_path / ".env"
    env.write_text("AIRTABLE_API_KEY=pat_real_secret_value\nAIRTABLE_BASE_ID=appOLD000\n", encoding="utf-8")

    # Update the base id
    setup_base.write_base_id_to_env("appNEW777", env_path=str(env), example_path=str(example))

    # Verify the result
    result_text = env.read_text(encoding="utf-8")

    # Real token must be preserved unchanged (byte-for-byte)
    assert "AIRTABLE_API_KEY=pat_real_secret_value" in result_text
    # New base id must be present
    assert "AIRTABLE_BASE_ID=appNEW777" in result_text
    # Old base id must be gone
    assert "appOLD000" not in result_text
    # Example API key must NOT appear (proves .env.example wasn't used)
    assert "pat_example_token" not in result_text
    # Exactly one AIRTABLE_BASE_ID line
    assert result_text.count("AIRTABLE_BASE_ID=") == 1
