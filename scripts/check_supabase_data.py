import os
import json
from bomtempo.core.supabase_client import sb_select

def check_supabase_data():
    tables = ["contratos", "projeto", "obras", "financeiro", "om"]
    for t in tables:
        print(f"\n--- Table: {t} ---")
        rows = sb_select(t, limit=10)
        if rows:
            print(f"Found {len(rows)} sample rows.")
            unique_contracts = set(r.get("Contrato") or r.get("contrato") for r in rows)
            print(f"Contracts in sample: {unique_contracts}")
            print(json.dumps(rows[0], indent=2, ensure_ascii=False))
        else:
            print("EMPTY or ERROR")

if __name__ == "__main__":
    check_supabase_data()
