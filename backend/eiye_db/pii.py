"""Baseline PII detection and redaction (regex; NER comes post-wedge)."""

import re
from typing import Any

PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"),
}


def luhn_valid(number: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    """Replace detected PII with [REDACTED:<type>] tokens; return counts by type."""
    counts: dict[str, int] = {}

    for pii_type, pattern in PATTERNS.items():
        def _sub(m: re.Match) -> str:
            if pii_type == "credit_card" and not luhn_valid(m.group()):
                return m.group()
            counts[pii_type] = counts.get(pii_type, 0) + 1
            return f"[REDACTED:{pii_type}]"

        text = pattern.sub(_sub, text)
    return text, counts


def redact_structure(obj: Any) -> tuple[Any, dict[str, int]]:
    """Recursively redact PII in all strings of a JSON-like structure."""
    totals: dict[str, int] = {}

    def _merge(counts: dict[str, int]) -> None:
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v

    def _walk(value: Any) -> Any:
        if isinstance(value, str):
            redacted, counts = redact_text(value)
            _merge(counts)
            return redacted
        # Numeric PII, e.g. a card number stored as a bigint. bool is an int
        # subclass, so exclude it. Only convert to str when redaction fires;
        # ordinary numbers keep their type. Note: bare-digit SSN/phone without
        # separators are not matched by the regex baseline (NER is post-wedge).
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            redacted, counts = redact_text(str(value))
            if counts:
                _merge(counts)
                return redacted
            return value
        if isinstance(value, dict):
            # Redact keys as well as values — REST sources can return objects
            # keyed by PII (e.g. {"alice@example.com": {...}}).
            return {_walk(k): _walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_walk(v) for v in value]
        return value

    return _walk(obj), totals
