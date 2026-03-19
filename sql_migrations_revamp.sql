-- ============================================================
-- MIGRATION: RDO & Reembolso Revamp — Feature Flags + New Columns
-- Execute no Supabase SQL Editor
-- ============================================================

-- ── 1. contract_features table ───────────────────────────────────────────────
-- Armazena quais sub-features estão ativas por contrato.
-- Cada linha = (contract_id, feature_key, is_enabled)

CREATE TABLE IF NOT EXISTS contract_features (
  id           uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  contract_id  text        NOT NULL,
  feature_key  text        NOT NULL,
  is_enabled   boolean     DEFAULT true,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),
  updated_by   text        DEFAULT '',
  CONSTRAINT uq_contract_feature UNIQUE (contract_id, feature_key)
);

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_contract_features_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contract_features_updated ON contract_features;
CREATE TRIGGER trg_contract_features_updated
  BEFORE UPDATE ON contract_features
  FOR EACH ROW EXECUTE FUNCTION update_contract_features_timestamp();

-- ── 2. fuel_reimbursements — novas colunas ───────────────────────────────────

-- GPS check-in no momento do preenchimento
ALTER TABLE fuel_reimbursements
  ADD COLUMN IF NOT EXISTS checkin_lat              float,
  ADD COLUMN IF NOT EXISTS checkin_lng              float,
  ADD COLUMN IF NOT EXISTS checkin_endereco         text,
  ADD COLUMN IF NOT EXISTS checkin_timestamp        timestamptz,
  ADD COLUMN IF NOT EXISTS checkin_distancia_posto  float;  -- metros entre GPS e cidade declarada (Haversine)

-- Assinatura digital (base64 JPEG)
ALTER TABLE fuel_reimbursements
  ADD COLUMN IF NOT EXISTS signature_b64    text;

-- Detecção de duplicidade (MD5 da imagem)
ALTER TABLE fuel_reimbursements
  ADD COLUMN IF NOT EXISTS image_hash       text;

-- Score de confiabilidade IA (0-100)
ALTER TABLE fuel_reimbursements
  ADD COLUMN IF NOT EXISTS ai_score         integer;

-- Centro de custo / Obra vinculada
ALTER TABLE fuel_reimbursements
  ADD COLUMN IF NOT EXISTS centro_custo     text,
  ADD COLUMN IF NOT EXISTS obra_id          text;

-- Alerta de capacidade de tanque
ALTER TABLE fuel_reimbursements
  ADD COLUMN IF NOT EXISTS capacidade_tanque      float,     -- litros configurados
  ADD COLUMN IF NOT EXISTS tank_overflow_alert    boolean DEFAULT false;

-- ── 3. rdo_master — novas colunas condicionais ───────────────────────────────

-- Campos condicionais de chuva
ALTER TABLE rdo_master
  ADD COLUMN IF NOT EXISTS houve_chuva          boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS quantidade_chuva     text;         -- "Leve", "Moderada", "Forte"

-- Campos condicionais de acidente
ALTER TABLE rdo_master
  ADD COLUMN IF NOT EXISTS houve_acidente       boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS descricao_acidente   text;

-- ── 4. Índices para performance ──────────────────────────────────────────────

-- Busca rápida de duplicidade por hash
CREATE INDEX IF NOT EXISTS idx_fr_image_hash
  ON fuel_reimbursements(image_hash)
  WHERE image_hash IS NOT NULL;

-- Busca por contrato em contract_features
CREATE INDEX IF NOT EXISTS idx_contract_features_contract_id
  ON contract_features(contract_id);

-- ── 5. Seed inicial: habilitar todas as features para contratos existentes ──
-- Descomente e ajuste conforme necessário.
-- As features ficam DESABILITADAS por padrão para contratos existentes.
-- O gestor ativa via UI em /admin/contract-features.

-- INSERT INTO contract_features (contract_id, feature_key, is_enabled)
-- SELECT DISTINCT contrato, unnest(ARRAY[
--   'gps_validation', 'duplicate_detection', 'ai_score',
--   'centro_custo', 'tank_capacity_check', 'digital_signature',
--   'conditional_fields', 'auto_weather'
-- ]), false
-- FROM contratos
-- ON CONFLICT (contract_id, feature_key) DO NOTHING;
