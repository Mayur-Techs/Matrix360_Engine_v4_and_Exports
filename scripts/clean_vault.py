import sqlite3
from pathlib import Path

db_path = Path("runtime/production_vault.db")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # Delete synthetic promoter records
    cur.execute("DELETE FROM production_leads WHERE verified_source_url IS NULL OR verified_source_url = '' OR lead_id LIKE '%specialty%'")
    print(f"Cleaned {cur.rowcount} unverified/synthetic leads from production_vault.db")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM production_leads")
    print("Remaining evidenced leads in vault:", cur.fetchone()[0])
    conn.close()
