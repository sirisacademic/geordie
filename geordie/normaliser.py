"""Normalise geographic entities: demonyms, adjectives, country codes -> country names."""

from __future__ import annotations

import re

from .resources.demonyms_and_adjectives import base_transformed_dict, pattern

# Compiled once at import time — avoids recompiling thousands of
# alternations on every normalise_entity() call.
_PATTERN = re.compile(pattern, re.IGNORECASE)


def normalise_entity(entity: str) -> str:
    """
    Replace demonyms, adjectives, and country codes with canonical country names.

    Examples
    --------
    >>> normalise_entity("French")
    'France'
    >>> normalise_entity("brasileño")
    'Brazil'
    >>> normalise_entity("Barcelona")
    'Barcelona'
    """
    return _PATTERN.sub(
        lambda m: base_transformed_dict.get(m.group(0), m.group(0)),
        entity,
    )