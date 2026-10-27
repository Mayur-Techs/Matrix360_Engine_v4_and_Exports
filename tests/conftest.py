import os
import pytest
from services.api import store

@pytest.fixture(autouse=True)
def set_test_auth_env(monkeypatch):
    monkeypatch.setenv("MATRIX_TEST_AUTH_MODE", "fixture")
    store.init()

