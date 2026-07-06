"""Tests for the deterministic random data generators."""

from __future__ import annotations

from random_mcp_server.generators import KINDS, RandomFactory


def test_same_seed_is_reproducible():
    a = RandomFactory(seed=42)
    b = RandomFactory(seed=42)
    assert a.build_pool("people", 5) == b.build_pool("people", 5)
    assert a.build_pool("coords", 5) == b.build_pool("coords", 5)


def test_different_seed_differs():
    a = RandomFactory(seed=1).build_pool("people", 5)
    b = RandomFactory(seed=2).build_pool("people", 5)
    assert a != b


def test_reseed_changes_stream():
    f = RandomFactory(seed=7)
    first = f.build_pool("words", 5)
    f.reseed(7)
    assert f.build_pool("words", 5) == first


def test_person_shape():
    person = RandomFactory(seed=3).person()
    assert set(person) == {
        "type", "prefix", "first", "last", "age", "birthday",
        "gender", "zip", "ssnFour", "phone", "email",
    }
    assert person["type"] == "people"
    assert person["gender"] in ("male", "female")
    assert len(person["ssnFour"]) == 4
    assert isinstance(person["age"], int)


def test_coord_ranges():
    for coord in RandomFactory(seed=5).build_pool("coords", 25):
        assert -90.0 <= coord["latitude"] <= 90.0
        assert -180.0 <= coord["longitude"] <= 180.0


def test_word_and_value_shapes():
    word = RandomFactory(seed=9).word()
    assert word["type"] == "words" and isinstance(word["value"], str) and word["value"]

    value = RandomFactory(seed=9).value()
    assert value["type"] == "values"
    assert isinstance(value["name"], str)
    assert isinstance(value["value"], float)


def test_empty_is_always_empty():
    assert RandomFactory(seed=1).build_pool("empty", 25) == []


def test_build_pool_count():
    for kind in KINDS:
        expected = 0 if kind == "empty" else 10
        assert len(RandomFactory(seed=1).build_pool(kind, 10)) == expected


def test_unknown_kind_raises():
    try:
        RandomFactory(seed=1).build_pool("nope", 5)
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown kind")
