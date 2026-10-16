from matrix_engine.engine.targeting import classify, geography_detail


def test_district_match_is_canonical_and_state_only_is_possible():
    assert geography_detail("", "Hooghly", "", "")[:2] == ("WB_CONFIRMED", "Hooghly")
    assert geography_detail("West Bengal", "", "", "")[:2] == ("WB_POSSIBLE", "")


def test_multi_signal_intent_is_qualified_but_proxy_is_not():
    qualified = classify({"state": "WB", "district": "Nadia", "city": "Kalyani", "address": "", "company": "", "sector": "", "interest": "interested in a plot", "budget": "50 lakh", "timeline": "3 months"})
    assert qualified["vrindavan_class"] == "Q1"
    proxy = classify({"state": "WB", "district": "Hooghly", "city": "Chandannagar", "address": "", "company": "", "sector": "", "interest": "", "budget": "", "timeline": ""})
    assert proxy["shree_class"] == "P2"
    assert proxy["shree_class"] not in {"Q1", "Q2"}


def test_outside_location_cannot_be_promoted_by_intent_words():
    row = classify({"state": "Maharashtra", "district": "", "city": "Pune", "address": "", "company": "steel manufacturer", "sector": "", "interest": "interested in factory space", "budget": "large", "timeline": "soon"})
    assert row["geo_status"] == "OUTSIDE_WB"
    assert {row["lakhotia_class"], row["shree_class"], row["vrindavan_class"]} == {"N"}
