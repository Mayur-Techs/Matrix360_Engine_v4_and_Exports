"""Adapter boundary for the upgraded Matrix Engine V5 implementation."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOT = ROOT / "matrix_engine"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

from engine.core import run as standalone_run  # noqa: E402


class StandaloneEngineAdapter:
    mode = "matrix-engine-v5-agentic-dual-drive"

    def run(self, input_dir: Path, workspace: Path, on_progress: Callable[[int, int, str], None] | None = None) -> dict[str, Any]:
        report = standalone_run(input_dir, workspace, on_progress=on_progress)
        report["engine_mode"] = self.mode
        return report
