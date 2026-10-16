# Matrix360 standalone automation v4

Run from this directory after installing requirements. Node.js and @oai/artifact-tool must be available for workbook exports (the ChatGPT runtime supplies them here).

    python -m engine.automate --input INPUT_FOLDER --workspace SEPARATE_WORKSPACE --output OUTPUT_FOLDER --ai --max-ai-calls 20

Produces Lakhotia.xlsx, Shree_Heights.xlsx, Vrindavan_Greens.xlsx and Matrix360_Combined_Leads.xlsx, with three project tabs, review and summary in the combined file. Only confirmed WB records matching observed sector or local-area research criteria enter project tabs. Outside-WB records remain in the warehouse for reconciliation. Unknown/conflicting locations go to Review. AI suggestions also require review; they cannot automatically establish residence, intent, budget or permission. This is research prioritization, not verified buyer qualification.

Phone numbers are normalized to full country-code digits and stored as Excel text. Scientific notation is expanded where the source retains the full value. Already rounded/truncated source digits cannot be recovered. CSV files must be imported as text into Excel.

AI uses the OpenAI Responses API, structured JSON output, exact-substring evidence validation, a local cache and a per-run request cap. Names, phones and emails are omitted from AI input. Company, sector and location evidence is sent to OpenAI with store=false. Failures are recorded in ai_status; rules still generate the deliverables. The key is stored locally in .env.local, excluded from the downloadable package. The key is not deployed or shared with other machines.

This command automates an individual run; it is not a hosted service. For unattended recurring runs, schedule this command on the machine hosting the data. Drive download still requires independent Drive authorization. ChatGPT cannot continuously run this application just because this chat exists. A scheduled ChatGPT task does not itself execute this local pipeline.

XLSX exports are capped at 250000 source rows per run and currently materialize export rows in memory. Larger jobs use streamed ingestion and warehouse/CSV outputs pending partitioned XLSX delivery. Geography coverage is conservative, not a complete gazetteer. Sector and local-area profiles, plus explicit direct-intent Q1/Q2 evidence, are in engine/targeting.py; P1 and broader client-specific evidence forms remain future development. Existing reference candidates are re-evaluated from source ledger rather than copied as newly qualified results.

Governance: process authorized data only. No messages, ad audiences or referral outreach are sent. Review contact collisions and permissions before activation. Retain source evidence and respect access/deletion policies.
