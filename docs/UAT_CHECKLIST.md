# Local UAT checklist

1. Copy `.env.example` to `.env` and change the local password.
2. Start the API and worker in separate terminals, then sign in at `http://127.0.0.1:8000`.
3. Run `python scripts/seed_synthetic.py`, select the CSV in **Choose files**, upload and verify the sampled headers/hash.
4. Select the uploaded dataset, start the job and observe `queued` then `completed` in **Jobs & Activity**.
5. Select the completed job and verify four result rows, including one `OUTSIDE_WB` row and independent three-client `P2` labels for the matching synthetic records.
6. Download the three CSVs and combined XLSX. Verify that the JSON manifest checksum entries exist and that exports state they are not consent to contact.
7. Sign out; direct `/api/v1/datasets` access must return HTTP 401.
8. Do not proceed with real client data or cloud publishing until every item in `docs/SECURITY_THREAT_MODEL.md` release gate is closed.

