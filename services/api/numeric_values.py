"""Conservative parsing for schema-approved numeric filter values.

This module deliberately does not coerce identifier-looking fields.  It
understands only a small, explicit set of display formats so preview, worker
exports, and result queries use the same deterministic interpretation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


IDENTIFIER_TOKENS = {
    "phone", "mobile", "telephone", "tel", "pin", "postal", "zip", "account", "gst", "pan",
    "id", "identifier", "registration", "reg", "vehicle", "aadhaar", "aadhar", "passport",
}
NUMERIC_TOKENS = {
    "price", "turnover", "revenue", "salary", "package", "area", "quantity", "amount", "year",
    "headcount", "employee", "employees", "staff", "units", "sqft", "square", "acre", "budget",
}
_CURRENCIES = (("inr", "INR"), ("rs.", "INR"), ("rs", "INR"), ("₹", "INR"), ("usd", "USD"), ("$", "USD"), ("eur", "EUR"), ("€", "EUR"))
_MULTIPLIERS = (("crores", Decimal("10000000")), ("crore", Decimal("10000000")), ("cr", Decimal("10000000")), ("lakhs", Decimal("100000")), ("lakh", Decimal("100000")), ("lacs", Decimal("100000")), ("lac", Decimal("100000")), ("million", Decimal("1000000")), ("mn", Decimal("1000000")), ("k", Decimal("1000")))


@dataclass(frozen=True)
class NumericValue:
    value: Decimal
    currency: str | None


def header_tokens(header: object) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(header).casefold()))


def is_identifier_header(header: object) -> bool:
    return bool(header_tokens(header) & IDENTIFIER_TOKENS)


def is_numeric_semantic_header(header: object) -> bool:
    tokens = header_tokens(header)
    return not bool(tokens & IDENTIFIER_TOKENS) and bool(tokens & NUMERIC_TOKENS)


def parse_numeric(value: object) -> NumericValue | None:
    """Parse a display value without guessing a currency or malformed unit."""
    text = str(value or "").strip().casefold()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    currency: str | None = None
    for marker, code in _CURRENCIES:
        if marker in text:
            if currency and currency != code:
                return None
            currency = code
            text = text.replace(marker, " ")
    multiplier = Decimal(1)
    for marker, factor in _MULTIPLIERS:
        if re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", text):
            multiplier = factor
            text = re.sub(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", " ", text)
            break
    compact = re.sub(r"\s+", "", text).replace(",", "")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", compact):
        return None
    try:
        parsed = Decimal(compact) * multiplier
    except InvalidOperation:
        return None
    return NumericValue(-parsed if negative else parsed, currency)


def comparable(left: NumericValue | None, right: NumericValue | None, expected_currency: str | None = None) -> bool:
    if left is None or right is None:
        return False
    if expected_currency:
        return left.currency in {None, expected_currency} and right.currency in {None, expected_currency}
    return left.currency == right.currency
