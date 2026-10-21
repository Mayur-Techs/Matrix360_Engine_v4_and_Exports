"""Parquet accepted at upload must be processed by the same local worker engine."""
from __future__ import annotations

import pyarrow as pa
import pyarrow.parquet as pq

from matrix_engine.engine.core import run


def test_parquet_source_is_processed_without_losing_headers_or_rows(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "synthetic.parquet"
    pq.write_table(
        pa.table({
            "Company": ["Synthetic Steel", "Synthetic Retail"],
            "Industry": ["manufacturing", "retail"],
            "State": ["West Bengal", "West Bengal"],
            "District": ["Howrah", "Kolkata"],
        }),
        source,
    )

    report = run(source_dir, tmp_path / "workspace")

    assert report["active_rows"] == 2
    assert report["reconciled"] is True
    assert report["events"] == [{"source": "synthetic.parquet", "status": "DONE", "rows": 2}]
