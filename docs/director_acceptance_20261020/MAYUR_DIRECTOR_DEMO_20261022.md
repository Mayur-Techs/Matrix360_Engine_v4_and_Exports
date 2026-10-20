# Director demonstration script — 5 to 7 minutes

Use only `synthetic_acceptance/director_synthetic.csv` or a newly generated synthetic file.

1. Start the local API and separate worker using the commands in `MAYUR_BASELINE_VALIDATION.md`; open `http://127.0.0.1:8000`.
2. **AI-Assisted Pipeline (about 3 minutes):** Upload the synthetic CSV, inspect the actual schema catalog, select **AI-Assisted Pipeline**, enter `West Bengal manufacturing companies in Howrah`, select **Suggest safe filters**, show the explicit ALL group and numeric turnover condition, choose **Validate & preview**, then choose **Approve & start AI-assisted processing**. Show job logs, results, and the manifest/export.
3. **AI Direct (about 2 minutes):** Choose **AI Direct**, select Lakhotia Industrial, show the loaded versioned objective, add a plain-language instruction, generate a plan, show unsupported criteria if any, then explicitly approve it. State that the displayed provider is rule-based unless a separately approved provider is configured.
4. **Generic fourth profile (about 1 minute):** Use the profile API exercise represented by `tests/test_audience_contract.py` to show the synthetic `Synthetic Manufacturing` profile has a schema-bound plan and generates a distinct export. Do not represent it as a real business.
5. Show an unsupported field/numeric comparison error and explain that phone, PIN, GST and account-like identifiers are not numeric targets.

Screen capture: **NOT CREATED**. Exact local reproduction is documented above; no capture tool was used in this execution.
