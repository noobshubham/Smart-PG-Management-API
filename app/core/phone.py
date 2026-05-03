"""Phone-number normalisation.

Stored format: digits only, no leading "+", no spaces, no separators.
Indian numbers usually arrive as "+919876543210" or "919876543210" — both
normalise to the same string.
"""
import re

_DIGITS = re.compile(r"\D+")


def normalise_phone(raw: str) -> str:
    if raw is None:
        return ""
    return _DIGITS.sub("", raw)
