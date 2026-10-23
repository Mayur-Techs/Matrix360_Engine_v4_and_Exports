# Quarantined Legacy Assets

## `v5.html`
- **Quarantine Date**: October 2026
- **Reason**: The audit revealed that `v5.html` contained embedded static rows and client-side heuristics that synthetically manufactured business turnover tiers, personal ITR income ranges, luxury vehicles (e.g. BMW X7, Land Rover Defender), and HNI classifications without verified web evidence.
- **Production Status**: `v5.html` is completely removed from the production web bundle (`apps/web/`) and is not served or linked by the application.
- **Production Truth**: All live discovery in Matrix 360 is executed strictly against public web endpoints via `apps/web/index.html` and the genuine evidence crawler engine, with per-field provenance and zero fabricated data.
