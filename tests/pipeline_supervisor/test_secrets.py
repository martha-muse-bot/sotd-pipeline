from pathlib import Path

from sotd.pipeline_supervisor.secrets import materialize_praw_ini

ENV = {
    "REDDIT_CLIENT_ID": "cid",
    "REDDIT_CLIENT_SECRET": "csecret",
}


def test_materializes_default_section_without_username_password(tmp_path: Path):
    out = materialize_praw_ini(ENV, tmp_path)
    assert out == tmp_path / "praw.ini"
    text = out.read_text()
    assert "[DEFAULT]" in text
    assert "[app]" not in text
    assert "client_id=cid" in text
    assert "client_secret=csecret" in text
    # user_agent is hard-required by praw; constant fallback when env unset
    assert "user_agent=sotd-pipeline-supervisor" in text
    # fetch is read-only: username/password are optional extras, absent when unset
    assert "username=" not in text
    assert "password=" not in text


def test_user_agent_env_overrides_constant(tmp_path: Path):
    env = dict(ENV, REDDIT_USER_AGENT="my-agent/1.0")
    out = materialize_praw_ini(env, tmp_path)
    assert "user_agent=my-agent/1.0" in out.read_text()


def test_username_password_written_when_env_set(tmp_path: Path):
    env = dict(ENV, REDDIT_USERNAME="u", REDDIT_PASSWORD="p")
    out = materialize_praw_ini(env, tmp_path)
    text = out.read_text()
    assert "username=u" in text
    assert "password=p" in text


def test_returns_none_when_env_incomplete(tmp_path: Path):
    env = dict(ENV)
    del env["REDDIT_CLIENT_SECRET"]
    assert materialize_praw_ini(env, tmp_path) is None
    assert not (tmp_path / "praw.ini").exists()


def test_braces_in_secrets_survive(tmp_path: Path):
    env = dict(ENV, REDDIT_CLIENT_SECRET="p{a}ss")
    out = materialize_praw_ini(env, tmp_path)
    assert "client_secret=p{a}ss" in out.read_text()


def test_prefers_existing_file(tmp_path: Path):
    existing = tmp_path / "praw.ini"
    existing.write_text("[DEFAULT]\nclient_id=mounted\n")
    assert materialize_praw_ini(ENV, tmp_path) == existing
    assert "mounted" in existing.read_text()
