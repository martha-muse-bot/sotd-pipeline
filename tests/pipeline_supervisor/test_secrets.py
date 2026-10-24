from pathlib import Path

from sotd.pipeline_supervisor.secrets import materialize_praw_ini

ENV = {
    "REDDIT_CLIENT_ID": "cid",
    "REDDIT_CLIENT_SECRET": "csecret",
    "REDDIT_USERNAME": "u",
    "REDDIT_PASSWORD": "p",
}


def test_materializes_when_env_complete(tmp_path: Path):
    out = materialize_praw_ini(ENV, tmp_path)
    assert out == tmp_path / "praw.ini"
    text = out.read_text()
    assert "[app]" in text
    assert "client_id=cid" in text
    assert "client_secret=csecret" in text
    assert "username=u" in text
    assert "password=p" in text


def test_returns_none_when_env_incomplete(tmp_path: Path):
    env = dict(ENV)
    del env["REDDIT_PASSWORD"]
    assert materialize_praw_ini(env, tmp_path) is None
    assert not (tmp_path / "praw.ini").exists()


def test_prefers_existing_file(tmp_path: Path):
    existing = tmp_path / "praw.ini"
    existing.write_text("[app]\nclient_id=mounted\n")
    assert materialize_praw_ini(ENV, tmp_path) == existing
    assert "mounted" in existing.read_text()
