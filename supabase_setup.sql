-- BOMTEMPO DASHBOARD - SCRIPT DE SETUP E AMARRAÇÃO DO BANCO (ENTERPRISE)
-- Instruções: Copie este código e cole no SQL Editor do seu painel Supabase e clique em RUN.

-------------------------------------------------------------------------------
-- 1. AMARRAÇÃO DAS TABELAS EXISTENTES (Primary Keys e Foreign Keys)
-------------------------------------------------------------------------------

-- 1.1 Garantir que na tabela mestre 'contratos', a coluna 'Contrato' seja UNIQUE (necessário para ser alvo de FK)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'contratos_contrato_key') THEN
        ALTER TABLE contratos ADD CONSTRAINT contratos_contrato_key UNIQUE ("Contrato");
    END IF;
END $$;

-- 1.2 Amarrar 'projetos' ao contrato mestre
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_projetos_contrato') THEN
        ALTER TABLE projetos ADD CONSTRAINT fk_projetos_contrato FOREIGN KEY ("Contrato") REFERENCES contratos("Contrato") ON DELETE CASCADE;
    END IF;
END $$;

-- 1.3 Amarrar 'obras' ao contrato mestre
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_obras_contrato') THEN
        ALTER TABLE obras ADD CONSTRAINT fk_obras_contrato FOREIGN KEY ("Contrato") REFERENCES contratos("Contrato") ON DELETE CASCADE;
    END IF;
END $$;

-- 1.4 Amarrar 'financeiro' ao contrato mestre
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_financeiro_contrato') THEN
        ALTER TABLE financeiro ADD CONSTRAINT fk_financeiro_contrato FOREIGN KEY ("Contrato") REFERENCES contratos("Contrato") ON DELETE CASCADE;
    END IF;
END $$;


-------------------------------------------------------------------------------
-- 2. ENRIQUECIMENTO DA TABELA 'obras' COM NOVOS INDICADORES "ENTERPRISE"
-------------------------------------------------------------------------------
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


-------------------------------------------------------------------------------
-- 3. CRIAÇÃO DAS TABELAS DE FEATURES COMPLEMENTARES (Alertas e Logs)
-------------------------------------------------------------------------------

-- 3.1 Tabela de Assinatura de Alertas (Painel de controle do gestor)
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_email text NOT NULL,
    alert_type text NOT NULL, -- Ex: 'ESTOURO_BUDGET', 'ATRASO_CRITICO'
    is_active boolean DEFAULT true,
    channels text[] DEFAULT '{"in-app"}'::text[],
    created_at timestamp with time zone DEFAULT now(),
    UNIQUE(user_email, alert_type)
);

-- 3.2 Tabela de Histórico de Alertas (Gerados pelo Cron Job/Sweep)
CREATE TABLE IF NOT EXISTS alert_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    project_code text REFERENCES contratos("Contrato") ON DELETE CASCADE, -- Amarrado ao contrato
    alert_type text NOT NULL,
    message text NOT NULL,
    is_read boolean DEFAULT false,
    timestamp timestamp with time zone DEFAULT now()
);

-- 3.3 Tabela de Logs e Auditoria (Rastreabilidade das ações na plataforma)
CREATE TABLE IF NOT EXISTS system_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamp with time zone DEFAULT now(),
    user_email text NOT NULL,
    action_category text NOT NULL, -- Ex: 'LOGIN', 'DATA_EDIT', 'REPORT_RENDER'
    entity_id text,
    metadata jsonb DEFAULT '{}'::jsonb, -- Aqui guardamos valor antigo/novo
    client_info text
);

-- 3.4 Criação de Índices para performance nas tabelas de listagem intensa
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_email ON system_logs(user_email);
CREATE INDEX IF NOT EXISTS idx_alert_history_unread ON alert_history(is_read) WHERE is_read = false;

-------------------------------------------------------------------------------
-- 4. SEGURANÇA (Row Level Security - RLS)
-------------------------------------------------------------------------------
-- Habilitar RLS preventivamente nas novas tabelas
ALTER TABLE alert_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Exemplo generoso de policy (Descomente caso não consiga ler via API depois):
-- CREATE POLICY allow_all ON system_logs FOR ALL USING (true);
-- CREATE POLICY allow_all ON alert_subscriptions FOR ALL USING (true);
-- CREATE POLICY allow_all ON alert_history FOR ALL USING (true);


-------------------------------------------------------------------------------
-- 5. POPULANDO DADOS MOCKADOS AOS CONTRATOS REAIS (Pra validação Visual)
-------------------------------------------------------------------------------
-- Habilitar REPLICA IDENTITY FULL temporariamente/permanentemente 
-- (necessário no Supabase pois essa tabela 'obras' está no realtime/publications sem Primary Key explícita)
ALTER TABLE obras REPLICA IDENTITY FULL;

-- Utilizando os seus contratos reais (CT-2024-001, CT-2025-002, CT-2025-003)

UPDATE obras 
SET budget_planejado = 4100000, 
    budget_realizado = 4650000,   -- Estourado
    equipe_presente_hoje = 12,    -- Abaixo do planejado
    efetivo_planejado = 25, 
    chuva_acumulada_mm = 65,      -- Alta umidade
    risco_geral_score = 92        -- Critico
WHERE "Contrato" = 'CT-2024-001';

UPDATE obras 
SET budget_planejado = 2500000, 
    budget_realizado = 2100000,   -- Saudável
    equipe_presente_hoje = 45, 
    efetivo_planejado = 50, 
    chuva_acumulada_mm = 5,       -- Seco
    risco_geral_score = 15        -- Baixo Risco
WHERE "Contrato" = 'CT-2025-002';

UPDATE obras 
SET budget_planejado = 1200000, 
    budget_realizado = 1250000,   -- Levemente Estourado
    equipe_presente_hoje = 18, 
    efetivo_planejado = 20, 
    chuva_acumulada_mm = 20, 
    risco_geral_score = 45        -- Risco Médio
WHERE "Contrato" = 'CT-2025-003';
