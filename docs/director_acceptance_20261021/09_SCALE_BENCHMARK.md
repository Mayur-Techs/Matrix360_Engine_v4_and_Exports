# 09 — Synthetic scale benchmark

Status: PARTIAL, measured P1 evidence only.

Fresh command:

```powershell
.\.venv\Scripts\python.exe -m matrix_engine.engine.benchmark --rows 25000 --input output\director_acceptance_20261021\benchmark-25k\input --workspace output\director_acceptance_20261021\benchmark-25k\workspace
```

Measured result: 25,000 rows, 13.750 seconds, 1,818.2 rows/sec, reconciled true, zero rejected rows, zero failed files and zero automatic merges. Windows does not provide a meaningful `resource` RSS value through the existing helper (`null`), so no memory claim is made.

An attempted 100,000-row benchmark was interrupted by the execution environment and left preserved synthetic artifacts under `output/director_acceptance_20261021/benchmark/`; it is not a completed benchmark. Do not extrapolate the 25,000-row figure to 100k, 500k, 2.5m or larger workloads.
