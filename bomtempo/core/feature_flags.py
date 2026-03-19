"""
Feature Flags Service — controla quais sub-features estão ativas por contrato.

Cada contrato pode ter um conjunto diferente de features habilitadas.
O gestor controla isso em /admin/contract-features.
A tabela `contract_features` armazena: (contract_id, feature_key, is_enabled).

Features OFF por padrão (opt-in): tank_capacity_check
Features ON por padrão (opt-out): todas as demais
"""

from typing import Dict, List

from bomtempo.core.logging_utils import get_logger
from bomtempo.core.supabase_client import sb_select, sb_upsert

logger = get_logger(__name__)

_TABLE = "contract_features"

# ── Feature Keys ────────────────────────────────────────────────────────────

# Reembolso
FEATURE_GPS_VALIDATION      = "gps_validation"
FEATURE_DUPLICATE_DETECTION = "duplicate_detection"
FEATURE_AI_SCORE            = "ai_score"
FEATURE_DIGITAL_SIGNATURE   = "digital_signature"

# RDO
FEATURE_CONDITIONAL_FIELDS  = "conditional_fields"   # chuva / acidente
FEATURE_AUTO_WEATHER        = "auto_weather"          # clima no check-in

# Features que ficam OFF por padrão (admin precisa ativar explicitamente)
FEATURES_OFF_BY_DEFAULT: List[str] = []

# ── Metadata ────────────────────────────────────────────────────────────────

FEATURE_LABELS: Dict[str, str] = {
    FEATURE_GPS_VALIDATION:      "Validação GPS (Localização vs Check-in)",
    FEATURE_DUPLICATE_DETECTION: "Detecção de Duplicidade (Hash MD5)",
    FEATURE_AI_SCORE:            "Score de Confiabilidade IA (0–100)",
    FEATURE_DIGITAL_SIGNATURE:   "Assinatura Digital",
    FEATURE_CONDITIONAL_FIELDS:  "Campos Condicionais (Chuvas / Acidentes)",
    FEATURE_AUTO_WEATHER:        "Clima Automático no Check-in (RDO)",
}

FEATURE_MODULES: Dict[str, str] = {
    FEATURE_GPS_VALIDATION:      "reembolso",
    FEATURE_DUPLICATE_DETECTION: "reembolso",
    FEATURE_AI_SCORE:            "reembolso",
    FEATURE_DIGITAL_SIGNATURE:   "ambos",
    FEATURE_CONDITIONAL_FIELDS:  "rdo",
    FEATURE_AUTO_WEATHER:        "rdo",
}

# Ordem fixa para a UI
FEATURE_ORDER: List[str] = [
    # — Reembolso
    FEATURE_GPS_VALIDATION,
    FEATURE_DUPLICATE_DETECTION,
    FEATURE_AI_SCORE,
    FEATURE_DIGITAL_SIGNATURE,
    # — RDO
    FEATURE_CONDITIONAL_FIELDS,
    FEATURE_AUTO_WEATHER,
]

# Features ativas por padrão quando não há configuração no banco
_DEFAULT_ACTIVE = [fk for fk in FEATURE_ORDER if fk not in FEATURES_OFF_BY_DEFAULT]


# ── Service ─────────────────────────────────────────────────────────────────

class FeatureFlagsService:
    """Serviço de feature flags por contrato."""

    @staticmethod
    def get_features_for_contract(contract_id: str) -> List[str]:
        """Retorna lista de feature keys habilitadas para um contrato.
        Padrão opt-out: se não houver registros, retorna _DEFAULT_ACTIVE."""
        try:
            if not contract_id or contract_id.strip() in ("", "nan", "None"):
                return list(_DEFAULT_ACTIVE)
            rows = sb_select(_TABLE, filters={"contract_id": contract_id}) or []
            if not rows:
                return list(_DEFAULT_ACTIVE)
            return [
                str(r["feature_key"])
                for r in rows
                if r.get("feature_key") and bool(r.get("is_enabled", True))
            ]
        except Exception as e:
            logger.error(f"get_features_for_contract({contract_id}): {e}")
            return list(_DEFAULT_ACTIVE)  # erro → fail-open

    @staticmethod
    def get_all_features_raw() -> List[Dict]:
        """Retorna todos os registros da tabela contract_features."""
        try:
            return sb_select(_TABLE, order="contract_id.asc") or []
        except Exception as e:
            logger.error(f"get_all_features_raw: {e}")
            return []

    @staticmethod
    def set_feature(contract_id: str, feature_key: str, is_enabled: bool, updated_by: str = "") -> bool:
        """Habilita ou desabilita uma feature para um contrato (upsert)."""
        if not contract_id or not feature_key:
            return False
        try:
            sb_upsert(
                _TABLE,
                {
                    "contract_id": contract_id,
                    "feature_key": feature_key,
                    "is_enabled":  is_enabled,
                    "updated_by":  updated_by,
                },
                on_conflict="contract_id,feature_key",
            )
            logger.info(f"✅ Feature flag: {contract_id}/{feature_key} → {is_enabled}")
            return True
        except Exception as e:
            logger.error(f"set_feature({contract_id}/{feature_key}): {e}")
            return False

    @staticmethod
    def build_matrix(contract_ids: List[str]) -> Dict[str, Dict[str, bool]]:
        """
        Retorna dict: contract_id → {feature_key: is_enabled}
        para todos os contratos listados.
        """
        try:
            rows = sb_select(_TABLE) or []
            matrix: Dict[str, Dict[str, bool]] = {
                cid: {fk: False for fk in FEATURE_ORDER}
                for cid in contract_ids
            }
            for r in rows:
                cid = str(r.get("contract_id", ""))
                fk  = str(r.get("feature_key", ""))
                if cid in matrix and fk in matrix[cid]:
                    matrix[cid][fk] = bool(r.get("is_enabled", False))
            return matrix
        except Exception as e:
            logger.error(f"build_matrix: {e}")
            return {}

    @staticmethod
    def get_grid_rows(contract_ids: List[str]) -> List[Dict]:
        """
        Retorna lista de dicts para rx.foreach na UI de admin.
        Cada dict: {"contract_id": "BOM-001", "gps_validation": "true", ...}
        Valores são strings "true"/"false" para compatibilidade com Reflex.
        """
        matrix = FeatureFlagsService.build_matrix(contract_ids)
        rows = []
        for cid in contract_ids:
            row: Dict[str, str] = {"contract_id": cid}
            for fk in FEATURE_ORDER:
                row[fk] = "true" if matrix.get(cid, {}).get(fk, False) else "false"
            rows.append(row)
        return rows
