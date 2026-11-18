from datetime import date
from unittest.mock import patch

import sotd.fetch.run as run_mod
from sotd.fetch.reddit import filter_valid_threads
from sotd.fetch.run import _calc_missing


# --------------------------------------------------------------------------- #
# helper fakes and patches                                                    #
# --------------------------------------------------------------------------- #
class FakeSubmission:
    def __init__(self, _id: str, title: str, created_utc: int = 0, permalink: str = "/p"):
        self.id = _id
        self.title = title
        self.created_utc = created_utc
        self.permalink = permalink
        self.num_comments = 0
        self.link_flair_text = None
        self.author = "tester"


class FakeComment:
    def __init__(self, _id: str, body: str = "body", created_utc: int = 0):
        self.id = _id
        self.body = body
        self.created_utc = created_utc
        self.author = "c_tester"
        self.is_root = True
        self.permalink = "/c"


class FakeSubreddit:
    def __init__(self, submissions):
        self._subs = submissions

    def search(self, *_args, **_kwargs):
        for s in self._subs:
            yield s


class FakeReddit:
    def __init__(self):
        good1 = FakeSubmission("good1", "SOTD Thread May 01, 2025")
        good2 = FakeSubmission("good2", "SOTD Thread May 02, 2025")
        bad = FakeSubmission("badxx", "Weekly Recap")
        self._sub = FakeSubreddit([good1, good2, bad])

    def subreddit(self, _name):
        return self._sub

    def submission(self, submission_id):
        return FakeSubmission(submission_id, f"Included {submission_id}")


# --------------------------------------------------------------------------- #
# tests                                                                        #
# --------------------------------------------------------------------------- #
@patch("sotd.fetch.reddit.get_reddit", return_value=FakeReddit())
def test_filter_valid_threads_and_missing(_patched) -> None:
    """filter_valid_threads should keep only valid titles and sort by date."""

    year, month = 2025, 5
    raw = list(
        _patched.return_value.subreddit("wetshaving").search("dummy", sort="new", syntax="lucene")
    )
    valid = filter_valid_threads(raw, year, month)

    # Only two good submissions (good1, good2)
    assert [sub.id for sub in valid] == ["good1", "good2"]


def test_missing_day_calc() -> None:
    """_calc_missing should detect calendar gaps."""

    class Dummy:
        def __init__(self, title: str):
            self.title = title

    year, month = 2025, 5
    threads = [Dummy("SOTD Thread May 1, 2025"), Dummy("SOTD Thread May 3, 2025")]
    missing = _calc_missing(year, month, threads)

    # Expect May 2 is missing.
    assert missing[0] == date(2025, 5, 2)


# ----------------------------------------------------------------------- #
# multi-month integration: ensure _process_month is called per month      #
# ----------------------------------------------------------------------- #
def test_main_multi_month(monkeypatch):
    """--year should process 12 months in ascending order."""

    called = []

    def fake_process(y, m, *_, **__):
        called.append((y, m))

    monkeypatch.setattr(
        "sotd.fetch.run._process_month",
        fake_process,
        raising=True,
    )  # type: ignore[attr-defined]
    monkeypatch.setattr("sotd.fetch.run.get_reddit", lambda: None, raising=True)

    # run main with a fake argv (year 2024)
    run_mod.main(["--year", "2024"])

    assert len(called) == 12
    assert called[0] == (2024, 1)
    assert called[-1] == (2024, 12)
