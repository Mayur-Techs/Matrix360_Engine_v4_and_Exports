"""Adapter boundary for the supplied Matrix Engine V4 rule implementation."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOT = ROOT / "matrix_engine"
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

from engine.core import run as standalone_run  # noqa: E402


class StandaloneEngineAdapter:
    mode = "matrix-engine-v4-rulebase-local"

    def run(self, input_dir: Path, workspace: Path, on_progress: Callable[[int, int, str], None] | None = None) -> dict[str, Any]:
        report = standalone_run(input_dir, workspace, on_progress=on_progress)
        report["engine_mode"] = self.mode
        return report

