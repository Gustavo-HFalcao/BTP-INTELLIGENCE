-- ============================================================
-- MIGRATION: Multi-tenant SaaS Foundation (3-Client Model) - V2.1
-- Descrição: Cria a infraestrutura para Master, BOMTEMPO (com dados) e PLENO (vazio).
-- Inclui agora a tabela de logs (system_logs).
-- Instruções: Execute este script no SQL Editor do Supabase.
-- ============================================================

-- 1. Criar tabela de Clientes (Tenants)
CREATE TABLE IF NOT EXISTS clients (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name         text        NOT NULL,
  is_master    boolean     DEFAULT false,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

-- 2. Criar os 3 Clientes do Modelo
-- Master: Gestão Global
INSERT INTO clients (id, name, is_master)
VALUES ('00000000-0000-0000-0000-000000000000', 'BTP MASTER', true)
ON CONFLICT (id) DO NOTHING;

-- BOMTEMPO: Cliente com os dados atuais (Mockados)
INSERT INTO clients (id, name, is_master)
VALUES ('11111111-1111-1111-1111-111111111111', 'BOMTEMPO', false)
ON CONFLICT (id) DO NOTHING;

-- PLENO: Cliente novo/vazio para demonstração
INSERT INTO clients (id, name, is_master)
VALUES ('22222222-2222-2222-2222-222222222222', 'PLENO', false)
ON CONFLICT (id) DO NOTHING;

-- 3. Adicionar client_id em todas as tabelas e migrar dados para BOMTEMPO
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
        'chat_messages',
        'system_logs'   -- <--- ADICIONADO: Logs agora também são isolados
    ];
BEGIN 
    FOREACH t IN ARRAY target_tables LOOP
        -- Adiciona coluna client_id se não existir
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = t AND column_name = 'client_id') THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN client_id uuid REFERENCES clients(id)', t);
        END IF;
        
        -- MIGRAR DADOS EXISTENTES PARA O CLIENTE BOMTEMPO (ID 1111...)
        -- Motive: O usuário quer que o ambiente atual mockado seja o cliente 1 (Bomtempo).
        EXECUTE format('UPDATE %I SET client_id = ''11111111-1111-1111-1111-111111111111'' WHERE client_id IS NULL', t);
        
        -- Criar índice para performance de filtros por cliente
        EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (client_id)', 'idx_' || t || '_client_id', t);
    END LOOP;
END $$;

-- 4. Ajustes de Usuários: Vincular 'master' ao Tenant Master
UPDATE login 
SET client_id = '00000000-0000-0000-0000-000000000000' 
WHERE username = 'master';

-- 5. View Master Stats (Refinada para o dashboard mestre)
CREATE OR REPLACE VIEW master_stats AS
SELECT 
    c.id as client_id,
    c.name as client_name,
    c.is_master,
    (SELECT count(*) FROM login l WHERE l.client_id = c.id) as user_count,
    (SELECT count(*) FROM system_logs sl WHERE sl.client_id = c.id) as total_logs,
    (SELECT count(*) FROM chat_messages cm 
     JOIN chat_sessions cs ON cm.session_id = cs.id 
     WHERE cs.client_id = c.id) as ai_messages_count
FROM clients c;
