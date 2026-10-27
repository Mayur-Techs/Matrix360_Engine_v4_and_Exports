import os
import pytest

@pytest.fixture(autouse=True)
def set_test_auth_env(monkeypatch):
    monkeypatch.setenv("MATRIX_TEST_AUTH_MODE", "fixture")
