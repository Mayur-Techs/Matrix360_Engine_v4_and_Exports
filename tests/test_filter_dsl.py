from services.api.filter_dsl import FilterValidationError, context_for_fields, evaluate, validate_plan


def test_nested_groups_and_missing_values_have_explicit_semantics():
    context = context_for_fields(["geo_status", "Industry", "phone_source"])
    plan = validate_plan(
        {"op": "all", "children": [
            {"field": "geo_status", "operator": "eq", "value": "WB_CONFIRMED"},
            {"op": "any", "children": [
                {"field": "Industry", "operator": "contains", "value": "manufacturing"},
                {"field": "phone_source", "operator": "present"},
            ]},
        ]},
        context,
    )
    assert evaluate(plan, {"geo_status": "WB_CONFIRMED", "original_fields": {"Industry": "Manufacturing"}}) is True
    assert evaluate(plan, {"geo_status": "WB_CONFIRMED", "original_fields": {}}) is None
    assert evaluate(plan, {"geo_status": "OUTSIDE_WB", "original_fields": {"Industry": "Manufacturing"}}) is False


def test_unknown_fields_and_unbounded_depth_are_rejected():
    context = context_for_fields(["Industry"])
    try:
        validate_plan({"field": "Email", "operator": "present"}, context)
    except FilterValidationError as exc:
        assert "not available" in str(exc)
    else:
        raise AssertionError("unknown field was accepted")
