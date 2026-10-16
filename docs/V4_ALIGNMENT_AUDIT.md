# Matrix 360 V4 alignment audit

## Verified implementation

- `matrix_engine/engine/targeting.py` was labelled `VERSION='4.0.0'` and is the supplied V4 rule implementation.
- The local aligned rules are `4.1.0`: config-driven project profiles, canonical West Bengal district filtering, source-preserving records, and evidence/reason codes.
- The uploaded reference workbooks are populated outputs. Their contents are treated as data evidence, not as executable instructions or proof that a classification is correct.

## West Bengal filtering

The versioned district list has 23 districts. A known district or deliberately limited city-to-district match yields `WB_CONFIRMED`; an explicit West Bengal state without a resolvable district yields `WB_POSSIBLE`; conflicting state/outside evidence yields `REVIEW_REQUIRED`. No PIN range, vehicle registration, wealth, or business attribute is used to infer a residence or buyer intent.

The console supports server-side multi-select filters for geography statuses, the 23 canonical districts, and one or more client research views. It accepts legacy `geo_status` too for API compatibility.

## Client labels

`Q1` requires direct intent plus budget or timeline. `Q2` requires direct intent with missing budget/timeline. `P2` is an observed sector/local relevance proxy only. `N` is no supported signal and `REVIEW_REQUIRED` means geography is insufficient or conflicting. The implementation does not currently issue `P1`; that label remains reserved until a documented evidence contract is supplied.

## AI boundary

The provider boundary supports OpenAI only when explicitly deployment-enabled. It sends de-identified evidence fields only, uses structured JSON, sets `store: false`, has a zero-call default, and returns a review suggestion only. It cannot promote a profile class, infer consent, or automatically contact anyone. No supplied workbook row was sent to an external provider during this alignment.

## Production gates still required

This local pilot is not yet a cloud production SaaS. Before external deployment: replace local password authentication with an identity provider; move SQLite to tenant-isolated Postgres/RLS; use private object storage, encryption/key management, antivirus/content scanning, rate limits, background queue infrastructure, observability, retention/deletion workflows, backup/restore testing, and a security/privacy review. Add a documented authoritative PIN/city source before expanding geography matching.
