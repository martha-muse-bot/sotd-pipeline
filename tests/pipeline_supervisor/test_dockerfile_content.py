from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "webui" / "Dockerfile.pipeline"


def test_dockerfile_exists():
    assert DOCKERFILE.exists()


def test_dockerfile_installs_git_and_rsync():
    text = DOCKERFILE.read_text()
    assert "git" in text and "rsync" in text


def test_requirements_has_prometheus_client():
    assert "prometheus_client" in (ROOT / "requirements.txt").read_text()
