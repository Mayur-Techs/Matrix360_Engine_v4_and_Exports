"""Validated, data-driven filter trees used by the audience API.

The module deliberately evaluates a constrained data structure rather than
accepting model-produced SQL, Python, or DuckDB expressions.  A missing value
is represented internally as ``None``; only a final ``True`` selects a row.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .numeric_values import comparable, parse_numeric


MAX_DEPTH = 5
MAX_LEAVES = 50
MAX_VALUE_LENGTH = 160
GROUP_OPERATORS = {"all", "any", "not"}
VALUE_OPERATORS = {"eq", "neq", "contains", "excludes", "present", "empty", "gt", "gte", "lt", "lte", "between"}
NUMERIC_OPERATORS = {"gt", "gte", "lt", "lte", "between"}


class FilterValidationError(ValueError):
    """A client-safe filter validation error."""


@dataclass(frozen=True)
class FilterContext:
    fields: frozenset[str]
    aliases: dict[str, str]
    numeric_fields: frozenset[str]
    numeric_currencies: dict[str, frozenset[str]]


def context_for_fields(fields: Iterable[str], aliases: dict[str, str] | None = None, numeric_fields: Iterable[str] | None = None, numeric_currencies: dict[str, Iterable[str]] | None = None) -> FilterContext:
    normalized = {str(field).strip() for field in fields if str(field).strip()}
    allowed_numeric = frozenset(str(field) for field in (numeric_fields or ()) if str(field) in normalized)
    currencies = {
        str(field): frozenset(str(currency).upper() for currency in values if str(currency).strip())
        for field, values in (numeric_currencies or {}).items()
        if str(field) in allowed_numeric
    }
    return FilterContext(frozenset(normalized), {str(k): str(v) for k, v in (aliases or {}).items() if str(v) in normalized}, allowed_numeric, currencies)


def _error(message: str) -> FilterValidationError:
    return FilterValidationError(message)


def validate_plan(plan: Any, context: FilterContext, depth: int = 0, leaves: list[int] | None = None) -> dict[str, Any]:
    """Normalize a declarative filter plan and reject ambiguous constructs."""
    leaves = leaves if leaves is not None else [0]
    if depth > MAX_DEPTH:
        raise _error(f"Filter nesting may not exceed {MAX_DEPTH} groups")
    if not isinstance(plan, dict):
        raise _error("Filter plan nodes must be objects")
    op = str(plan.get("op", "")).lower()
    if op in GROUP_OPERATORS:
        children = plan.get("children")
        if not isinstance(children, list) or not children:
            raise _error(f"'{op}' requires at least one child")
        if op == "not" and len(children) != 1:
            raise _error("'not' requires exactly one child")
        if len(children) > 20:
            raise _error("A group may contain at most 20 children")
        return {"op": op, "children": [validate_plan(child, context, depth + 1, leaves) for child in children]}
    field = str(plan.get("field", "")).strip()
    field = context.aliases.get(field.casefold(), field)
    if field not in context.fields:
        raise _error("Filter field is not available in this dataset")
    operator = str(plan.get("operator", "")).lower()
    if operator not in VALUE_OPERATORS:
        raise _error("Unsupported filter operator")
    leaves[0] += 1
    if leaves[0] > MAX_LEAVES:
        raise _error(f"Use at most {MAX_LEAVES} filter conditions")
    value = plan.get("value")
    if operator in NUMERIC_OPERATORS and field not in context.numeric_fields:
        raise _error("Numeric comparisons are allowed only for validated numeric fields")
    if operator not in {"present", "empty"}:
        if operator == "between":
            if not isinstance(value, list) or len(value) != 2:
                raise _error("'between' needs exactly two inclusive numeric bounds")
            value = [str(item).strip() for item in value]
            if any(not item or len(item) > MAX_VALUE_LENGTH for item in value):
                raise _error("Filter values must be non-empty and short")
        else:
            if isinstance(value, (dict, list)) or value is None:
                raise _error("This filter needs one scalar value")
            value = str(value).strip()
            if not value or len(value) > MAX_VALUE_LENGTH:
                raise _error("Filter values must be non-empty and short")
        if operator in NUMERIC_OPERATORS:
            numeric_values = [parse_numeric(item) for item in (value if isinstance(value, list) else [value])]
            if any(item is None for item in numeric_values):
                raise _error("Numeric comparisons need a supported numeric value")
            assert all(item is not None for item in numeric_values)
            numeric_values = [item for item in numeric_values if item is not None]
            currencies = {item.currency for item in numeric_values if item.currency}
            if len(currencies) > 1:
                raise _error("Numeric bounds must use one currency")
            expected = next(iter(currencies), None)
            observed = context.numeric_currencies.get(field, frozenset())
            if expected and observed and expected not in observed:
                raise _error("Numeric comparison currency is not compatible with this field")
            if not expected and len(observed) == 1:
                expected = next(iter(observed))
            if operator == "between" and numeric_values[0].value > numeric_values[1].value:
                raise _error("'between' lower bound must not exceed upper bound")
            return {
                "field": field,
                "operator": operator,
                "value": value,
                "numeric_values": [str(item.value) for item in numeric_values],
                "numeric_currency": expected,
            }
    else:
        value = None
    return {"field": field, "operator": operator, "value": value}


def _value(row: dict[str, Any], field: str) -> str | None:
    if field in row:
        candidate = row.get(field)
    else:
        original = row.get("original_fields", {})
        if isinstance(original, str):
            try:
                original = json.loads(original)
            except json.JSONDecodeError:
                original = {}
        candidate = original.get(field) if isinstance(original, dict) else None
        if candidate is None:
            source = original if isinstance(original, dict) else row
            candidate = next((value for key, value in source.items() if str(key).casefold() == field.casefold()), None)
    if candidate is None:
        return None
    result = str(candidate).strip()
    return result or None


def evaluate(plan: dict[str, Any], row: dict[str, Any]) -> bool | None:
    """Evaluate with SQL-like three-valued missing behaviour.

    ``all`` returns false on any false, ``any`` returns true on any true, and
    a missing comparison propagates as unknown.  Callers include only true.
    """
    op = plan.get("op")
    if op in GROUP_OPERATORS:
        values = [evaluate(child, row) for child in plan["children"]]
        if op == "all":
            return False if False in values else (True if values and all(value is True for value in values) else None)
        if op == "any":
            return True if True in values else (False if values and all(value is False for value in values) else None)
        return None if values[0] is None else not values[0]
    candidate = _value(row, str(plan["field"]))
    operator, wanted = str(plan["operator"]), plan.get("value")
    if operator == "present":
        return candidate is not None
    if operator == "empty":
        return candidate is None
    if candidate is None:
        return None
    if operator in NUMERIC_OPERATORS:
        left = parse_numeric(candidate)
        numbers = plan.get("numeric_values")
        if not isinstance(numbers, list):
            numbers = wanted if isinstance(wanted, list) else [wanted]
        rights = [parse_numeric(value) for value in numbers]
        expected_currency = str(plan.get("numeric_currency") or "").upper() or None
        if left is None or any(right is None or not comparable(left, right, expected_currency) for right in rights):
            return None
        values = [right.value for right in rights if right is not None]
        if operator == "between":
            return values[0] <= left.value <= values[1]
        return {"gt": left.value > values[0], "gte": left.value >= values[0], "lt": left.value < values[0], "lte": left.value <= values[0]}[operator]
    left, right = candidate.casefold(), str(wanted).casefold()
    if operator == "eq":
        return left == right
    if operator == "neq":
        return left != right
    if operator == "contains":
        return right in left
    return right not in left


def numeric_matches(value: object, operator: str, low: object, high: object = "", currency: object = "") -> bool:
    """DuckDB UDF bridge; false is the safe SQL-WHERE representation of unknown."""
    left, first = parse_numeric(value), parse_numeric(low)
    expected = str(currency or "").upper() or None
    if left is None or first is None or not comparable(left, first, expected):
        return False
    if operator == "between":
        second = parse_numeric(high)
        return bool(second and comparable(left, second, expected) and first.value <= left.value <= second.value)
    return {"gt": left.value > first.value, "gte": left.value >= first.value, "lt": left.value < first.value, "lte": left.value <= first.value}.get(operator, False)
