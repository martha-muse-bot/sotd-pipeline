"""Regression tests for the pattern cache's by-id fast path.

CPython may reuse a freed dict's memory address for a newly allocated dict.
The cache's fast path used to key on ``id(catalog_data)`` without keeping the
object alive, so a stale entry from a freed catalog could be served for a new
catalog at the same address — silently wrong patterns (and, in
test_handle_matcher.py::test_enhanced_regex_error_reporting, a swallowed
ValueError).

The fix: the by-id cache holds a strong reference to the catalog dict and
verifies identity on lookup. Holding the ref means the address can never be
reused while the entry exists, and the ``is`` check rejects any foreign entry.
"""

import pytest

from sotd.match.brush.strategies.utils.pattern_cache import (
    _pattern_cache_by_id,
    clear_pattern_cache,
    get_compiled_patterns,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Isolate the module-level cache for each test."""
    clear_pattern_cache()
    yield
    clear_pattern_cache()


def _compile(data):
    """Fake compilation: one marker dict per top-level key."""
    return [{"key": k} for k in data]


def test_entry_holds_strong_reference_to_catalog():
    """The by-id entry pins the catalog dict, so its address can never be reused."""
    catalog = {"alpha": {"Model": {"patterns": [r"alpha"]}}}
    get_compiled_patterns(catalog, "handle", _compile)
    entry = _pattern_cache_by_id[(id(catalog), "handle")]
    assert entry[0] is catalog, "by-id cache must hold the catalog dict itself"


def test_foreign_id_entry_is_not_served():
    """A by-id entry whose stored object is not the caller's dict must be ignored.

    Simulates the stale-hit state: an entry keyed by this dict's id() holding
    another object's patterns. The identity check must reject it and fall
    through to the content-hash path.
    """
    catalog = {"beta": {"Model": {"patterns": [r"beta"]}}}
    decoy = {"alpha": {"Model": {"patterns": [r"alpha"]}}}
    _pattern_cache_by_id[(id(catalog), "handle")] = (decoy, [{"key": "decoy"}])

    result = get_compiled_patterns(catalog, "handle", _compile)
    assert result == [
        {"key": "beta"}
    ], "foreign by-id entry was served instead of compiling the caller's catalog"


def test_live_objects_never_collide():
    """Two simultaneously-live dicts can never share an id, so both cache correctly."""
    cat1 = {"brand1": {"Model": {"patterns": [r"one"]}}}
    cat2 = {"brand2": {"Model": {"patterns": [r"two"]}}}
    r1 = get_compiled_patterns(cat1, "handle", _compile)
    r2 = get_compiled_patterns(cat2, "handle", _compile)
    assert r1 != r2
    # Both still hit their own entries
    assert get_compiled_patterns(cat1, "handle", _compile) is r1
    assert get_compiled_patterns(cat2, "handle", _compile) is r2
