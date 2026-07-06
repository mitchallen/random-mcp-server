"""Random data generators.

These mirror the shapes produced by the original `random-server`'s chance.js
routers (``src/controllers/*.ts``). Generation is seeded once through
:class:`RandomFactory` so that a given seed always yields the same records —
the same "values are seeded when the server first starts up" behavior the REST
server documents.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Any

from faker import Faker

# Consonant/vowel building blocks for pronounceable nonsense words, matching
# the flavor of chance.word() (e.g. "cezuwdi") rather than real dictionary words.
_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_VOWELS = "aeiou"

# The record kinds this factory knows how to produce, in REST-route order.
KINDS: tuple[str, ...] = ("people", "words", "values", "coords", "empty")


def _nonsense_word(rng: random.Random, syllables: int | None = None) -> str:
    """Return a pronounceable nonsense word of alternating consonant/vowel pairs."""
    if syllables is None:
        syllables = rng.randint(2, 4)
    return "".join(rng.choice(_CONSONANTS) + rng.choice(_VOWELS) for _ in range(syllables))


class RandomFactory:
    """Deterministic factory for random JSON records.

    Construct with a fixed ``seed`` for reproducible output, or leave it ``None``
    to pick a random seed. Call :meth:`reseed` to regenerate the underlying
    stream (the MCP ``regenerate`` tool uses this).
    """

    def __init__(self, seed: int | None = None) -> None:
        self.reseed(seed)

    def reseed(self, seed: int | None = None) -> None:
        """Reset the random stream. A ``None`` seed selects a fresh random one."""
        self._seed = seed if seed is not None else random.randrange(2**32)
        self._rng = random.Random(self._seed)
        self._faker = Faker()
        self._faker.seed_instance(self._seed)

    @property
    def seed(self) -> int:
        """The seed currently driving this factory."""
        return self._seed

    # --- record builders (one per REST route family) ---------------------

    def word(self) -> dict[str, Any]:
        """A single ``words`` record: ``{type, value}``."""
        return {"type": "words", "value": _nonsense_word(self._rng)}

    def value(self) -> dict[str, Any]:
        """A single ``values`` record: ``{type, name, value}`` with a float value."""
        return {
            "type": "values",
            "name": _nonsense_word(self._rng),
            "value": round(self._rng.uniform(-1e12, 1e12), 4),
        }

    def coord(self) -> dict[str, Any]:
        """A single ``coords`` record: ``{type, latitude, longitude}``."""
        return {
            "type": "coords",
            "latitude": round(self._rng.uniform(-90.0, 90.0), 5),
            "longitude": round(self._rng.uniform(-180.0, 180.0), 5),
        }

    def person(self) -> dict[str, Any]:
        """A single ``people`` record matching the REST server's person shape."""
        gender = self._rng.choice(["male", "female"])
        if gender == "male":
            prefix = self._rng.choice(["Mr.", "Dr."])
            first = self._faker.first_name_male()
        else:
            prefix = self._rng.choice(["Mrs.", "Ms.", "Miss", "Dr."])
            first = self._faker.first_name_female()

        birthday = self._faker.date_of_birth(minimum_age=18, maximum_age=80)
        age = (date.today() - birthday).days // 365

        return {
            "type": "people",
            "prefix": prefix,
            "first": first,
            "last": self._faker.last_name(),
            "age": age,
            "birthday": f"{birthday.month}/{birthday.day}/{birthday.year}",
            "gender": gender,
            "zip": f"{self._rng.randint(0, 99999):05d}-{self._rng.randint(0, 9999):04d}",
            "ssnFour": f"{self._rng.randint(0, 9999):04d}",
            "phone": (
                f"({self._rng.randint(200, 999)}) "
                f"{self._rng.randint(200, 999)}-{self._rng.randint(0, 9999):04d}"
            ),
            "email": self._faker.email(),
        }

    # --- pool builder ----------------------------------------------------

    def build_pool(self, kind: str, count: int) -> list[dict[str, Any]]:
        """Generate ``count`` records of ``kind``. ``empty`` always yields ``[]``."""
        if kind == "empty":
            return []
        builder = {
            "people": self.person,
            "words": self.word,
            "values": self.value,
            "coords": self.coord,
        }.get(kind)
        if builder is None:
            raise ValueError(f"unknown kind '{kind}'; expected one of {', '.join(KINDS)}")
        return [builder() for _ in range(count)]
