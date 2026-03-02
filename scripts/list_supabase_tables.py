import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://nychzaapchxdlsffotcq.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

def get_tables():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    # Supabase doesn't have a direct "list tables" REST endpoint easily accessible without RLS issues sometimes
    # but we can try to hit the schema endpoint or just probe common names.
    # Actually, we can check the OpenApi spec that Supabase provides!
    resp = httpx.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
    if resp.status_code == 200:
        spec = resp.json()
        print("--- Tables in Schema ---")
        for table in spec.get('definitions', {}).keys():
            print(f"- {table}")
    else:
        print(f"Error fetching schema: {resp.status_code}")

if __name__ == "__main__":
    get_tables()
