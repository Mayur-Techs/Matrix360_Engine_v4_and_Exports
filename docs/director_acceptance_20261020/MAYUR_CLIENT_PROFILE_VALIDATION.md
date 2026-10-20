# Client profile validation

The existing Lakhotia, Shree Heights, and Vrindavan Greens rules remain configuration-driven V4 profiles. The V4 engine emits observed-evidence reason codes and does not infer consent, wealth, ownership, or purchase intent.

The generic profile API supports tenant-scoped creation, versioning, retirement, inclusion/exclusion definitions, and a deterministic selection plan. `tests/test_audience_contract.py` verifies a synthetic manufacturing profile is created and produces a different export from the same source dataset.

The fourth-client acceptance evidence is synthetic only: `Synthetic Manufacturing` in `tests/test_audience_contract.py`. It is not a real client and is not hard-coded into engine classification.

Pilot profile UI selection was extended to load versioned objectives for AI Direct. Custom profile selection plans remain schema-validated at job creation.
