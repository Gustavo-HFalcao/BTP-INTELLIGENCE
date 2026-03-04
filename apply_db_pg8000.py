import pg8000
import sys

def apply_schema():
    host = "aws-0-sa-east-1.pooler.supabase.com"
    database = "postgres"
    user = "postgres.nychzaapchxdlsffotcq"
    password = "f48hYLaviOTW9lnS"
    port = 6543

    # A string contendo o DDL e DML necessários.
    sql = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'contratos_contrato_key') THEN
        ALTER TABLE contratos ADD CONSTRAINT contratos_contrato_key UNIQUE ("Contrato");
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_projetos_contrato') THEN
        ALTER TABLE projetos ADD CONSTRAINT fk_projetos_contrato FOREIGN KEY ("Contrato") REFERENCES contratos("Contrato") ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_obras_contrato') THEN
        ALTER TABLE obras ADD CONSTRAINT fk_obras_contrato FOREIGN KEY ("Contrato") REFERENCES contratos("Contrato") ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_financeiro_contrato') THEN
        ALTER TABLE financeiro ADD CONSTRAINT fk_financeiro_contrato FOREIGN KEY ("Contrato") REFERENCES contratos("Contrato") ON DELETE CASCADE;
    END IF;
END $$;

DO $$ 
BEGIN
    BEGIN ALTER TABLE obras ADD COLUMN budget_planejado numeric DEFAULT 0; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN budget_realizado numeric DEFAULT 0; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN equipe_presente_hoje integer DEFAULT 0; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN efetivo_planejado integer DEFAULT 0; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN chuva_acumulada_mm numeric DEFAULT 0; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN risco_geral_score integer DEFAULT 0; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN ultima_vistoria_data timestamp with time zone; EXCEPTION WHEN duplicate_column THEN END;
    BEGIN ALTER TABLE obras ADD COLUMN foto_destaque_url text; EXCEPTION WHEN duplicate_column THEN END;
END $$;

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_email text NOT NULL,
    alert_type text NOT NULL,
    is_active boolean DEFAULT true,
    channels text[] DEFAULT '{"in-app"}'::text[],
    created_at timestamp with time zone DEFAULT now(),
    UNIQUE(user_email, alert_type)
);

CREATE TABLE IF NOT EXISTS alert_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    project_code text REFERENCES contratos("Contrato") ON DELETE CASCADE,
    alert_type text NOT NULL,
    message text NOT NULL,
    is_read boolean DEFAULT false,
    timestamp timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamp with time zone DEFAULT now(),
    user_email text NOT NULL,
    action_category text NOT NULL,
    entity_id text,
    metadata jsonb DEFAULT '{}'::jsonb,
    client_info text
);

CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_email ON system_logs(user_email);
CREATE INDEX IF NOT EXISTS idx_alert_history_unread ON alert_history(is_read) WHERE is_read = false;

ALTER TABLE alert_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

UPDATE obras SET budget_planejado = 4100000, budget_realizado = 4650000, equipe_presente_hoje = 12, efetivo_planejado = 25, chuva_acumulada_mm = 65, risco_geral_score = 92 WHERE "Contrato" = 'CT-2024-001';
UPDATE obras SET budget_planejado = 2500000, budget_realizado = 2100000, equipe_presente_hoje = 45, efetivo_planejado = 50, chuva_acumulada_mm = 5, risco_geral_score = 15 WHERE "Contrato" = 'CT-2025-002';
UPDATE obras SET budget_planejado = 1200000, budget_realizado = 1250000, equipe_presente_hoje = 18, efetivo_planejado = 20, chuva_acumulada_mm = 20, risco_geral_score = 45 WHERE "Contrato" = 'CT-2025-003';
"""

    print("Connecting via pg8000...")
    try:
        conn = pg8000.connect(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port
        )
        print("Connected.")
        
        # pg8000 recommended execution
        conn.run(sql)
        print("Schema successfully applied!")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error executing schema script via pg8000: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_schema()
