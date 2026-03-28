-- ============================================================
-- MIGRATION: Multi-tenant Foundation
-- Descrição: Cria a tabela de clientes e adiciona isolamento por client_id em todas as tabelas de dados.
-- Instruções: Execute este script no SQL Editor do Supabase.
-- ============================================================

-- ── 1. Criar tabela de Clientes (Tenants) ──────────────────────
CREATE TABLE IF NOT EXISTS clients (
  id           uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  name         text        NOT NULL,
  is_master    boolean     DEFAULT false,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

-- ── 2. Criar Cliente Mestre Inicial ───────────────────────────
-- O ID abaixo será usado como padrão para todos os dados existentes.
-- Você pode gerar um novo UUID se preferir, mas este servirá para o bootstrap.
INSERT INTO clients (id, name, is_master)
VALUES ('00000000-0000-0000-0000-000000000000', 'Bomtempo Master', true)
ON CONFLICT (id) DO NOTHING;

-- ── 3. Adicionar client_id em todas as tabelas ─────────────────
DO $$ 
DECLARE 
    t text;
    target_tables text[] := ARRAY[
        'login', 
        'roles', 
        'projects', 
        'contratos', 
        'hub_atividades', 
        'fin_custos', 
        'om',
        'rdo_master',
        'rdo2_mao_obra',
        'rdo2_equipamentos',
        'fuel_reimbursements',
        'contract_features',
        'user_notifications',
        'chat_sessions',
        'chat_messages'
    ];
BEGIN 
    FOREACH t IN ARRAY target_tables LOOP
        -- Adiciona coluna client_id
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS client_id uuid REFERENCES clients(id) DEFAULT ''00000000-0000-0000-0000-000000000000''', t);
        
        -- Garante que dados existentes apontem para o Master
        EXECUTE format('UPDATE %I SET client_id = ''00000000-0000-0000-0000-000000000000'' WHERE client_id IS NULL', t);
        
        -- Remove o default para forçar inserção explícita no futuro (opcional, mas recomendado para segurança)
        -- EXECUTE format('ALTER TABLE %I ALTER COLUMN client_id DROP DEFAULT', t);
        
        -- Cria índice para performance de filtro por cliente
        EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (client_id)', 'idx_' || t || '_client_id', t);
    END LOOP;
END $$;

-- ── 4. Ajustes Específicos ────────────────────────────────────

-- Garantir que logins futuros exijam client_id
-- ALTER TABLE login ALTER COLUMN client_id SET NOT NULL;

-- Habilitar RLS (Opcional - Atualmente o App usa Service Key, mas RLS é o objetivo final)
-- ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
-- ... policies ...
