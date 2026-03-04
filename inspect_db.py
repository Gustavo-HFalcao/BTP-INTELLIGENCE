import httpx
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv('SUPABASE_SERVICE_KEY')
URL = 'https://nychzaapchxdlsffotcq.supabase.co/rest/v1/'
HEADERS = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}

sys.stdout.reconfigure(encoding='utf-8')

tables = ['contratos', 'projetos', 'obras', 'financeiro', 'system_logs', 'alert_subscriptions', 'alert_history']

for t in tables:
    r = httpx.get(f"{URL}{t}?limit=2", headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        print(f"--- {t} ---")
        if data:
            print("Columns:", list(data[0].keys()))
            print("First row:", json.dumps(data[0], indent=2, ensure_ascii=False))
        else:
            print("Table is empty")
        print("\n")
    else:
        print(f"Failed to fetch {t}: {r.status_code} - {r.text}")
