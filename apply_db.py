import sys
import psycopg2
import codecs

password = "f48hYLaviOTW9lnS"
host = "db.nychzaapchxdlsffotcq.supabase.co"
port = "5432"
dbname = "postgres"
user = "postgres"

conn_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

try:
    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(conn_string)
    conn.autocommit = True
    cur = conn.cursor()

    # Leitura com fallback de encoding para windows-1252
    try:
        with codecs.open('supabase_setup.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
    except UnicodeDecodeError:
        with codecs.open('supabase_setup.sql', 'r', encoding='windows-1252') as f:
            sql = f.read()

    print("Executing SQL script...")
    cur.execute(sql)
    
    print("Database setup complete!")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
