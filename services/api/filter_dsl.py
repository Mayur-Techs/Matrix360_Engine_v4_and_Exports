"""Validated, data-driven filter trees used by the audience API.

The module deliberately evaluates a constrained data structure rather than
accepting model-produced SQL, Python, or DuckDB expressions.  A missing value
is represented internally as ``None``; only a final ``True`` selects a row.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable


MAX_DEPTH = 5
MAX_LEAVES = 50
MAX_VALUE_LENGTH = 160
GROUP_OPERATORS = {"all", "any", "not"}
VALUE_OPERATORS = {"eq", "neq", "contains", "excludes", "present", "empty", "gt", "gte", "lt", "lte"}


class FilterValidationError(ValueError):
    """A client-safe filter validation error."""


@dataclass(frozen=True)
class FilterContext:
    fields: frozenset[str]
    aliases: dict[str, str]


def context_for_fields(fields: Iterable[str], aliases: dict[str, str] | None = None) -> FilterContext:
    normalized = {str(field).strip() for field in fields if str(field).strip()}
    return FilterContext(frozenset(normalized), {str(k): str(v) for k, v in (aliases or {}).items() if str(v) in normalized})


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
    if operator not in {"present", "empty"}:
        if isinstance(value, (dict, list)) or value is None:
            raise _error("This filter needs one scalar value")
        value = str(value).strip()
        if not value or len(value) > MAX_VALUE_LENGTH:
            raise _error("Filter values must be non-empty and short")
        if operator in {"gt", "gte", "lt", "lte"}:
            try:
                float(value)
            except ValueError as exc:
                raise _error("Numeric comparisons need a numeric value") from exc
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
    if operator in {"gt", "gte", "lt", "lte"}:
        try:
            left, right = float(candidate.replace(",", "")), float(wanted)
        except ValueError:
            return None
        return {"gt": left > right, "gte": left >= right, "lt": left < right, "lte": left <= right}[operator]
    left, right = candidate.casefold(), str(wanted).casefold()
    if operator == "eq":
        return left == right
    if operator == "neq":
        return left != right
    if operator == "contains":
        return right in left
    return right not in left
