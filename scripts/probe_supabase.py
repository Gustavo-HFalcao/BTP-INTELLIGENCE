import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://nychzaapchxdlsffotcq.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
REST_BASE = f"{SUPABASE_URL}/rest/v1"

def check_table(table_name):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = httpx.get(f"{REST_BASE}/{table_name}?limit=1", headers=headers)
        if resp.status_code == 200:
            print(f"Table '{table_name}': FOUND ({len(resp.json())} rows sample)")
            if resp.json():
                print(f"  Columns: {list(resp.json()[0].keys())}")
        else:
            print(f"Table '{table_name}': NOT FOUND or Error ({resp.status_code})")
    except Exception as e:
        print(f"Table '{table_name}': Exception {e}")

tables_to_check = ["contratos", "projeto", "obras", "financeiro", "om", "login", "rdo_cabecalho"]

if __name__ == "__main__":
    for t in tables_to_check:
        check_table(t)
