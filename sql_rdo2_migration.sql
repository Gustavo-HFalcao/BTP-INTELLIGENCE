-- ============================================================
-- RDO v2 Migration — Execute no Supabase SQL Editor
-- ============================================================

-- 1. TABELA MESTRE (substitui rdo_cabecalho + adiciona GPS/status/token)
CREATE TABLE IF NOT EXISTS rdo_master (
    id          UUID DEFAULT gen_random_uuid(),
    id_rdo      TEXT PRIMARY KEY,
    status      TEXT DEFAULT 'rascunho',       -- rascunho | finalizado | cancelado

    -- Cabeçalho
    contrato            TEXT,
    projeto             TEXT,
    cliente             TEXT,
    localizacao         TEXT,
    data                DATE,
    turno               TEXT DEFAULT 'Diurno',
    hora_inicio         TEXT DEFAULT '07:00',
    hora_termino        TEXT DEFAULT '17:00',
    condicao_climatica  TEXT DEFAULT 'Ensolarado',
    houve_interrupcao   BOOLEAN DEFAULT FALSE,
    motivo_interrupcao  TEXT,
    observacoes         TEXT,

    -- GPS Check-in
    checkin_timestamp   TIMESTAMPTZ,
    checkin_lat         FLOAT8,
    checkin_lng         FLOAT8,
    checkin_endereco    TEXT,

    -- GPS Check-out
    checkout_timestamp  TIMESTAMPTZ,
    checkout_lat        FLOAT8,
    checkout_lng        FLOAT8,
    checkout_endereco   TEXT,

    -- Assinatura digital (futura)
    assinatura_url      TEXT,
    assinatura_nome     TEXT,

    -- Output
    ai_summary          TEXT,
    pdf_path            TEXT,
    pdf_url             TEXT,
    view_token          TEXT UNIQUE DEFAULT gen_random_uuid()::TEXT,  -- link público

    -- Meta
    mestre_id           TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Index para lookup por token (visualização pública)
CREATE INDEX IF NOT EXISTS idx_rdo_master_token ON rdo_master (view_token);
-- Index para busca por mestre e status (retomar rascunho)
CREATE INDEX IF NOT EXISTS idx_rdo_master_mestre ON rdo_master (mestre_id, status);
-- Index para listagem por contrato
CREATE INDEX IF NOT EXISTS idx_rdo_master_contrato ON rdo_master (contrato, created_at DESC);


-- 2. MÃO DE OBRA (simplificado — sem colunas de custo)
CREATE TABLE IF NOT EXISTS rdo2_mao_obra (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_rdo      TEXT REFERENCES rdo_master(id_rdo) ON DELETE CASCADE,
    profissao   TEXT NOT NULL,
    quantidade  INTEGER DEFAULT 1,
    observacoes TEXT
);
CREATE INDEX IF NOT EXISTS idx_rdo2_mo_rdo ON rdo2_mao_obra (id_rdo);


-- 3. ATIVIDADES (simplificado — sem Sequencia obrigatória)
CREATE TABLE IF NOT EXISTS rdo2_atividades (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_rdo                TEXT REFERENCES rdo_master(id_rdo) ON DELETE CASCADE,
    atividade             TEXT NOT NULL,
    progresso_percentual  INTEGER DEFAULT 0,
    status                TEXT DEFAULT 'Em andamento'
);
CREATE INDEX IF NOT EXISTS idx_rdo2_atv_rdo ON rdo2_atividades (id_rdo);


-- 4. EQUIPAMENTOS (simplificado — sem custo, com status operacional)
CREATE TABLE IF NOT EXISTS rdo2_equipamentos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_rdo      TEXT REFERENCES rdo_master(id_rdo) ON DELETE CASCADE,
    equipamento TEXT NOT NULL,
    quantidade  INTEGER DEFAULT 1,
    status      TEXT DEFAULT 'Operando'    -- Operando | Parado | Em Manutenção
);
CREATE INDEX IF NOT EXISTS idx_rdo2_eq_rdo ON rdo2_equipamentos (id_rdo);


-- 5. MATERIAIS (simplificado — sem custo)
CREATE TABLE IF NOT EXISTS rdo2_materiais (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_rdo      TEXT REFERENCES rdo_master(id_rdo) ON DELETE CASCADE,
    material    TEXT NOT NULL,
    quantidade  FLOAT8,
    unidade     TEXT DEFAULT 'un'
);
CREATE INDEX IF NOT EXISTS idx_rdo2_mat_rdo ON rdo2_materiais (id_rdo);


-- 6. EVIDÊNCIAS FOTOGRÁFICAS (novo — foto proof-of-origin)
CREATE TABLE IF NOT EXISTS rdo2_evidencias (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_rdo          TEXT REFERENCES rdo_master(id_rdo) ON DELETE CASCADE,
    foto_url        TEXT NOT NULL,
    legenda         TEXT,
    gps_lat         FLOAT8,
    gps_lng         FLOAT8,
    gps_endereco    TEXT,
    timestamp_foto  TIMESTAMPTZ,
    analise_vision  TEXT,              -- resultado da Vision API (futuro)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rdo2_ev_rdo ON rdo2_evidencias (id_rdo);


-- ============================================================
-- BUCKET — criar manualmente no Supabase Dashboard > Storage:
--   Nome: rdo-evidencias   (público)
--   já existe: rdo-pdfs    (público) — manter
-- ============================================================
