from __future__ import annotations

import re

_YES = re.compile(r"^(yes|y|confirm|proceed|go ahead|do it)\.?$", re.I)
_NO = re.compile(r"^(no|n|cancel|stop|don't|do not)\.?$", re.I)


def is_explicit_yes(text: str) -> bool:
    t = text.strip()
    if _YES.match(t):
        return True
    low = t.lower()
    return low.startswith("yes,") or low.startswith("yes ")


def is_explicit_no(text: str) -> bool:
    t = text.strip()
    if _NO.match(t):
        return True
    low = t.lower()
    return low.startswith("no,") or low.startswith("no ") or low.startswith("don't")
