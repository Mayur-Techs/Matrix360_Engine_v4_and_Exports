"""Regression tests for source columns observed in the July company workbook."""
import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "matrix_engine" / "engine" / "core.py"

def load_mapping_functions():
    # Extract actual production mapping logic without requiring DuckDB/PyArrow
    # just to execute schema-mapping unit tests.
    tree = ast.parse(CORE.read_text(encoding="utf-8"))
    selected = [node for node in tree.body if
                (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ALIASES" for t in node.targets))
                or (isinstance(node, ast.FunctionDef) and node.name in {"text", "key", "mapping"})]
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    namespace = {"re": __import__("re")}
    exec(compile(module, str(CORE), "exec"), namespace)
    return namespace["mapping"]

def test_company_workbook_headers_map_without_losing_evidence():
    headers = ["Name of the Company", "Name", "Email", "Address1", "Address2",
               "Address3", "Address4", "Address5", "City", "State",
               "Industry Segment", "Sub Industry Segment"]
    mapped = load_mapping_functions()(headers)
    assert mapped["company"] == [0]
    assert mapped["name"] == [1]
    assert mapped["email"] == [2]
    assert mapped["address"] == [3, 4, 5, 6, 7]
    assert mapped["city"] == [8]
    assert mapped["state"] == [9]
    assert mapped["sector"] == [10, 11]

def test_old_aliases_are_preserved():
    mapped = load_mapping_functions()(["Company Name", "Address", "Phone", "Business Sector Hint"])
    assert mapped == {"company": [0], "phone": [2], "address": [1], "sector": [3]}
