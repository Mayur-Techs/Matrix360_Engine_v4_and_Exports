# 03 — Browser acceptance

Status: PASS for the exercised synthetic flows; PARTIAL for unexercised live-provider and cancellation scenarios.

The evidence uses the actual FastAPI API, SQLite metadata, filesystem storage and separate worker on `127.0.0.1`. It does not mock browser fetches or the worker.

## Mode A — AI-Assisted Pipeline

- Incorrect synthetic credentials returned `Invalid credentials`; valid synthetic credentials opened the workspace.
- Uploaded checked-in synthetic `director_synthetic.csv` (100 rows), inspected its actual schema, and generated a clearly labelled `Local deterministic fallback` plan because external model use was disabled.
- Edited the visual AND plan to require State contains West Bengal, District equals Howrah, Industry contains manufacturing, and Annual Turnover >= `1 lakh`.
- Numeric control exposed typed numeric operators only after selecting the verified Annual Turnover field. The preview returned **21 matching rows of 100**.
- The separate `Approve & start` action queued exactly one job. A separate local worker completed it and the UI auto-opened 21 results.
- Real browser downloads succeeded for `Lakhotia.csv`, `Matrix360_Combined.xlsx` and `job_manifest.v1.json`.

## Mode B — AI Direct

- Selected `Lakhotia Industrial · v1`; its saved default objective appeared in the browser.
- Submitted a three-line synthetic instruction. The UI displayed `Review required · deterministic-schema-planner · local-schema-only`, not a false live-model claim.
- Approval was distinct from suggestion. The completed job returned **23** rows because its approved plan deliberately omitted the Mode A turnover condition.

## Persisted state and responsive checks

- After a safe local API restart, the browser retained its authenticated synthetic session and showed 1 dataset and 2 completed jobs. Reselecting a completed job exposed its persisted exports again.
- At 390px, 768px and 1440px, final `scrollWidth == clientWidth`. A real 768px 56px overflow was found in the filter editors and fixed by stacking their controls at the existing tablet breakpoint.

Screenshots and the Mode B Playwright trace are in `output/director_acceptance_20261021/browser/` (ignored local synthetic evidence). The deliberate empty numeric validation produced one expected local HTTP 422 console entry; no external requests were observed.
