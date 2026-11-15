"""Read the numbers out of one table cell.

Cells are free text: "0.21", "~ 21.5", "20 cm/s", "21; 26.5; 40",
"1.5 - 5", "RAMPED", "n/a". This module turns each into values plus how they
were written, and never guesses when the text is not a number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MISSING = {"", "-", "n/a", "na", "none"}
VARIED = {"ramp", "ramped"}  # the quantity was changed during the test

_NUM = r"-?(?:\d+\.?\d*|\.\d+)"
_SINGLE = re.compile(rf"^({_NUM})$")
_RANGE = re.compile(rf"^({_NUM})\s*(?:-|to)\s*({_NUM})$")
_LIST_SEPARATOR = re.compile(r";|\bor\b|\band\b|&")


@dataclass(frozen=True)
class Reading:
    status: str  # ok | missing | varied | not_a_number
    values: tuple[tuple[float, float | None], ...] = ()  # (value, upper end of a range)
    form: str = ""  # single | range | listed
    approximate: bool = False


def read_numbers(text: str, units: tuple[str, ...] = ()) -> Reading:
    """`units` are unit words allowed inside the cell, e.g. ("cm/s",) or ("%",)."""
    s = text.strip().replace("–", "-").replace("—", "-")
    if s.lower() in MISSING:
        return Reading("missing")
    if s.lower() in VARIED:
        return Reading("varied")

    approximate = "~" in s
    s = s.replace("~", " ")
    for unit in units:
        s = s.replace(unit, " ")

    parts = [part.strip() for part in _LIST_SEPARATOR.split(s) if part.strip()]
    if len(parts) > 1:
        if all(_SINGLE.match(part) for part in parts):
            return Reading("ok", tuple((float(part), None) for part in parts), "listed", approximate)
        return Reading("not_a_number")

    s = s.strip()
    if match := _SINGLE.match(s):
        return Reading("ok", ((float(match[1]), None),), "single", approximate)
    if match := _RANGE.match(s):
        low, high = sorted((float(match[1]), float(match[2])))
        return Reading("ok", ((low, high),), "range", approximate)
    return Reading("not_a_number")


def read_o2_percent_in_text(text: str, units: tuple[str, ...] = ()) -> Reading:
    """Oxygen percentages from a phrase like "~30% and ~21% O2 with He"."""
    if text.strip().lower() in MISSING:
        return Reading("missing")
    before_o2 = text.split("O2")[0]
    found = re.findall(rf"({_NUM})\s*%", before_o2)
    if "O2" not in text or not found:
        return Reading("not_a_number")
    form = "listed" if len(found) > 1 else "single"
    return Reading("ok", tuple((float(value), None) for value in found), form, "~" in before_o2)
