# 01 — CI Root Cause and Green Tests Verification

**Date:** 27 October 2026  
**Investigating Engineer:** Mayur (`Mayur-Techs`)  
**CI Reference Run:** GitHub Actions Run `40470556342` (Commit: `ec16bca0eb54ebce86307875b899770c5a420bca`)  
**Linux CI Result at Baseline:** 137 passed, 5 failed, 2 skipped, 34 warnings, 31 subtests passed  

---

## 1. Root Cause Diagnosis of the 5 Linux CI Failures

The five failures observed in Ubuntu Linux CI were:
1. `tests/test_crm_mock_consumer_contract.py::test_handoff_prepare_and_schema_validation`
2. `tests/test_crm_mock_consumer_contract.py::test_mock_consumer_tamper_detection`
3. `tests/test_lead_discovery_pipeline.py::test_api_discovery_send_to_engine_bridge`
4. `tests/test_p0_red_regression_suite.py::test_handoff_16_returns_ready_for_handoff_not_synced_leads`
5. `tests/test_tenant_security_p0.py::test_authenticated_crm_handoff_contract`

### Failure Mechanism:
- All five tests failed with:
  ```
  sqlite3.OperationalError: no such table: audit_events
  sqlite3.OperationalError: no such table: datasets
  ```
- **Lifecycle Discrepancy:** On the local development environment, `runtime/metadata.sqlite` was pre-initialized by previous interactive app launches where FastAPI's lifespan `store.init()` had executed.
- On clean GitHub Actions runners (`runs-on: ubuntu-latest`), the workspace starts with an empty filesystem. When tests accessed `services/api/store.py` (`store.audit()` or `store.connect()`) directly or via Starlette `TestClient` without entering the FastAPI lifespan context, SQLite created an empty file on first connect without invoking table DDL.

---

## 2. Targeted Remediation

In `tests/conftest.py`, updated the autouse fixture to ensure deterministic table initialization for all test sessions:

```python
import os
import pytest
from services.api import store

@pytest.fixture(autouse=True)
def set_test_auth_env(monkeypatch):
    monkeypatch.setenv("MATRIX_TEST_AUTH_MODE", "fixture")
    store.init()
```

---

## 3. Local Verification & Reproducibility Proof

- Tested locally by completely deleting/renaming `runtime/metadata.sqlite`.
- Ran the 5 previously failing tests in a virgin SQLite environment:
  - `tests/test_crm_mock_consumer_contract.py`: 3 passed in 0.81s
  - `tests/test_p0_red_regression_suite.py`: 9 passed in 1.12s
  - `tests/test_tenant_security_p0.py`: 9 passed in 1.48s
  - `tests/test_lead_discovery_pipeline.py::test_api_discovery_send_to_engine_bridge`: 1 passed in 0.54s
- **Full Test Suite Status:** **142 passed, 2 skipped, 33 warnings in 36.76s** (0 failures repository-wide).
