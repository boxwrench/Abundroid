import abundroid.cli as cli


def test_setup_missing_env_returns_1(monkeypatch, capsys):
    monkeypatch.delenv("AIRTABLE_SETUP_TOKEN", raising=False)
    monkeypatch.delenv("AIRTABLE_WORKSPACE_ID", raising=False)
    rc = cli.main(["setup"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "AIRTABLE_SETUP_TOKEN" in err


def test_setup_happy_path(monkeypatch, capsys):
    monkeypatch.setenv("AIRTABLE_SETUP_TOKEN", "pat_setup")
    monkeypatch.setenv("AIRTABLE_WORKSPACE_ID", "wsp123")
    calls = {}

    class FakeApi:
        def __init__(self, token):
            calls["token"] = token

    monkeypatch.setattr(cli, "_make_setup_api", lambda token: FakeApi(token))

    def fake_build(api, ws, seed=True):
        calls["build"] = (ws, seed)
        return "appNEW1"

    def fake_write(base_id, **kw):
        calls["wrote"] = base_id

    monkeypatch.setattr(cli.setup_base, "build_base", fake_build)
    monkeypatch.setattr(cli.setup_base, "write_base_id_to_env", fake_write)
    rc = cli.main(["setup"])
    assert rc == 0
    assert calls["build"] == ("wsp123", True)
    assert calls["wrote"] == "appNEW1"
    out = capsys.readouterr().out
    assert "appNEW1" in out
    assert "revoke" in out.lower()  # reminds user to revoke the setup token


def test_setup_no_seed_flag(monkeypatch):
    monkeypatch.setenv("AIRTABLE_SETUP_TOKEN", "pat_setup")
    monkeypatch.setenv("AIRTABLE_WORKSPACE_ID", "wsp123")
    seen = {}
    monkeypatch.setattr(cli, "_make_setup_api", lambda token: object())

    def fake_build(api, ws, seed=True):
        seen["seed"] = seed
        return "appNEW2"

    monkeypatch.setattr(cli.setup_base, "build_base", fake_build)
    monkeypatch.setattr(cli.setup_base, "write_base_id_to_env", lambda base_id, **kw: None)
    cli.main(["setup", "--no-seed"])
    assert seen["seed"] is False
