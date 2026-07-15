# tests/test_setup_live.py
import os
import pytest

from abundroid import setup_base


LIVE = os.environ.get("ABUNDROID_LIVE_SETUP") == "1"


@pytest.mark.skipif(not LIVE, reason="set ABUNDROID_LIVE_SETUP=1 to run a real Airtable build")
def test_live_build_creates_base():
    import pyairtable

    token = os.environ["AIRTABLE_SETUP_TOKEN"]
    workspace = os.environ["AIRTABLE_WORKSPACE_ID"]
    api = pyairtable.Api(token)
    base_id = setup_base.build_base(api, workspace, seed=True)
    assert base_id.startswith("app")
    print(f"\nLive base created: {base_id} — delete it in Airtable when done.")
