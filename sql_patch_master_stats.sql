-- ============================================================
-- Patch: master_stats view — adiciona status, ai_budget, session_count
-- Executar no SQL Editor do Supabase
-- ============================================================

CREATE OR REPLACE VIEW master_stats AS
SELECT
    c.id          AS client_id,
    c.name        AS client_name,
    c.is_master,
    c.status,
    c.ai_budget,
    (SELECT count(*) FROM login l WHERE l.client_id = c.id)                         AS user_count,
    (SELECT count(*) FROM system_logs sl WHERE sl.client_id = c.id)                 AS total_logs,
    (SELECT count(*) FROM chat_sessions cs WHERE cs.client_id = c.id)               AS session_count,
    (SELECT count(*) FROM chat_messages cm
     JOIN chat_sessions cs ON cm.session_id = cs.id
     WHERE cs.client_id = c.id)                                                     AS ai_messages_count
FROM clients c;

-- ============================================================
-- Patch P2: Seed roles padrão para tenant BOMTEMPO (caso não existam com client_id)
-- Só executar se: SELECT COUNT(*) FROM roles WHERE client_id = '11111111-1111-1111-1111-111111111111' = 0
-- ============================================================

INSERT INTO roles (name, modules, icon, client_id)
SELECT 'Administrador',
       ARRAY['visao_geral','obras','financeiro','om','analytics','relatorios','chat_ia','alertas','logs_auditoria','gerenciar_usuarios','editar_dados'],
       'shield-check',
       '11111111-1111-1111-1111-111111111111'
WHERE NOT EXISTS (
    SELECT 1 FROM roles WHERE client_id = '11111111-1111-1111-1111-111111111111' AND name = 'Administrador'
);

INSERT INTO roles (name, modules, icon, client_id)
SELECT 'Gestor',
       ARRAY['visao_geral','obras','financeiro','om','analytics','relatorios','chat_ia'],
       'briefcase',
       '11111111-1111-1111-1111-111111111111'
WHERE NOT EXISTS (
    SELECT 1 FROM roles WHERE client_id = '11111111-1111-1111-1111-111111111111' AND name = 'Gestor'
);

INSERT INTO roles (name, modules, icon, client_id)
SELECT 'Engenheiro',
       ARRAY['visao_geral','obras','financeiro','om','analytics','relatorios','chat_ia'],
       'hard-hat',
       '11111111-1111-1111-1111-111111111111'
WHERE NOT EXISTS (
    SELECT 1 FROM roles WHERE client_id = '11111111-1111-1111-1111-111111111111' AND name = 'Engenheiro'
);

-- ============================================================
-- Patch P7: NOT NULL após confirmar todos os rows têm client_id
-- Só executar após confirmar que não há NULLs:
--   SELECT COUNT(*) FROM login WHERE client_id IS NULL;
--   SELECT COUNT(*) FROM contratos WHERE client_id IS NULL;
--   SELECT COUNT(*) FROM hub_atividades WHERE client_id IS NULL;
--   SELECT COUNT(*) FROM fin_custos WHERE client_id IS NULL;
-- ============================================================

-- ALTER TABLE login ALTER COLUMN client_id SET NOT NULL;
-- ALTER TABLE contratos ALTER COLUMN client_id SET NOT NULL;
-- ALTER TABLE hub_atividades ALTER COLUMN client_id SET NOT NULL;
-- ALTER TABLE fin_custos ALTER COLUMN client_id SET NOT NULL;
