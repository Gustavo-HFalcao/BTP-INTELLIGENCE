"""
FinService — Serviço de custos por projeto (Feature #21)
Tabelas: fin_categorias, fin_custos
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from bomtempo.core.supabase_client import sb_select, sb_insert, sb_update, sb_delete

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _norm(v: Any, fallback: str = "") -> str:
    if v is None or str(v) in ("None", "NaT", "nan", ""):
        return fallback
    return str(v)


def _parse_float(v: Any) -> float:
    """Parse float from various formats including BR currency strings."""
    if v is None:
        return 0.0
    s = str(v).strip()
    if not s or s in ("None", "nan", ""):
        return 0.0
    # BR format: 1.000,50
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    # strip non-numeric except . and -
    import re
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _fmt_brl(v: float) -> str:
    """Format float as BR currency string for display."""
    return f"R$ {v:_.2f}".replace("_", ".").replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────────────────────
# FinService
# ─────────────────────────────────────────────────────────────────────────────

class FinService:

    # ── Categorias ────────────────────────────────────────────────────────────

    @staticmethod
    def load_categorias() -> List[Dict[str, str]]:
        """Load all fin_categorias ordered by nome."""
        try:
            rows = sb_select("fin_categorias", order="nome.asc", limit=100)
            return [
                {
                    "id":    _norm(r.get("id")),
                    "nome":  _norm(r.get("nome"), "—"),
                    "cor":   _norm(r.get("cor"), "#889999"),
                    "icone": _norm(r.get("icone"), "tag"),
                }
                for r in (rows or [])
            ]
        except Exception as e:
            logger.error(f"load_categorias error: {e}")
            return []

    # ── Custos ────────────────────────────────────────────────────────────────

    @staticmethod
    def load_custos(contrato: str) -> List[Dict[str, str]]:
        """Load all fin_custos for a contract, normalized as string dicts."""
        try:
            rows = sb_select(
                "fin_custos",
                filters={"contrato": contrato},
                order="data_custo.asc,created_at.asc",
                limit=1000,
            )
            result = []
            for r in (rows or []):
                prev = _parse_float(r.get("valor_previsto", 0))
                exec_ = _parse_float(r.get("valor_executado", 0))
                result.append({
                    "id":                _norm(r.get("id")),
                    "contrato":          _norm(r.get("contrato")),
                    "categoria_id":      _norm(r.get("categoria_id")),
                    "categoria_nome":    _norm(r.get("categoria_nome"), "—"),
                    "descricao":         _norm(r.get("descricao"), "—"),
                    "valor_previsto":    str(prev),
                    "valor_executado":   str(exec_),
                    "valor_previsto_fmt": _fmt_brl(prev),
                    "valor_executado_fmt": _fmt_brl(exec_),
                    "status":            _norm(r.get("status"), "previsto"),
                    "data_custo":        _norm(r.get("data_custo"), "")[:10],
                    "atividade_id":      _norm(r.get("atividade_id")),
                    "observacoes":       _norm(r.get("observacoes")),
                    "created_by":        _norm(r.get("created_by")),
                })
            return result
        except Exception as e:
            logger.error(f"load_custos error: {e}")
            return []

    @staticmethod
    def save_custo(
        contrato: str,
        categoria_id: str,
        categoria_nome: str,
        descricao: str,
        valor_previsto: float,
        valor_executado: float,
        status: str,
        data_custo: str,
        atividade_id: str,
        observacoes: str,
        created_by: str,
        custo_id: str = "",
    ) -> Tuple[bool, str]:
        """
        Insert or update a custo record.
        Returns (success, id_or_error).
        """
        payload: Dict[str, Any] = {
            "contrato":        contrato,
            "categoria_id":    categoria_id or None,
            "categoria_nome":  categoria_nome,
            "descricao":       descricao,
            "valor_previsto":  round(valor_previsto, 2),
            "valor_executado": round(valor_executado, 2),
            "status":          status or "previsto",
            "data_custo":      data_custo or None,
            "atividade_id":    atividade_id or None,
            "observacoes":     observacoes,
            "created_by":      created_by,
        }
        try:
            if custo_id:
                sb_update("fin_custos", {"id": custo_id}, payload)
                return True, custo_id
            else:
                rows = sb_insert("fin_custos", payload)
                new_id = _norm((rows or [{}])[0].get("id")) if rows else ""
                return True, new_id
        except Exception as e:
            logger.error(f"save_custo error: {e}")
            return False, str(e)

    @staticmethod
    def delete_custo(custo_id: str) -> bool:
        try:
            sb_delete("fin_custos", {"id": custo_id})
            return True
        except Exception as e:
            logger.error(f"delete_custo error: {e}")
            return False

    # ── KPIs ──────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_kpis(custos: List[Dict[str, str]]) -> Dict[str, str]:
        """Compute KPI summary from normalized custo rows."""
        total_prev = sum(_parse_float(r.get("valor_previsto", 0)) for r in custos)
        total_exec = sum(_parse_float(r.get("valor_executado", 0)) for r in custos)
        saldo = total_prev - total_exec
        pct = round(total_exec / total_prev * 100, 1) if total_prev > 0 else 0.0
        concluidos = sum(1 for r in custos if r.get("status") == "concluido")
        return {
            "total_previsto":   _fmt_brl(total_prev),
            "total_executado":  _fmt_brl(total_exec),
            "saldo":            _fmt_brl(saldo),
            "pct_executado":    f"{pct:.1f}",
            "total_itens":      str(len(custos)),
            "concluidos":       str(concluidos),
        }

    # ── S-Curve ───────────────────────────────────────────────────────────────

    @staticmethod
    def compute_scurve(custos: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Build cumulative S-curve data from custo rows.
        Returns list of {data, previsto_acum, executado_acum} sorted by date.
        """
        from collections import defaultdict
        prev_by_date: Dict[str, float] = defaultdict(float)
        exec_by_date: Dict[str, float] = defaultdict(float)

        for r in custos:
            d = r.get("data_custo", "") or ""
            if not d or len(d) < 10:
                continue
            d = d[:10]
            prev_by_date[d] += _parse_float(r.get("valor_previsto", 0))
            exec_by_date[d] += _parse_float(r.get("valor_executado", 0))

        all_dates = sorted(set(list(prev_by_date.keys()) + list(exec_by_date.keys())))
        if not all_dates:
            return []

        result = []
        acum_prev = 0.0
        acum_exec = 0.0
        for d in all_dates:
            acum_prev += prev_by_date.get(d, 0.0)
            acum_exec += exec_by_date.get(d, 0.0)
            # Format date as DD/MM for display
            try:
                parts = d.split("-")
                label = f"{parts[2]}/{parts[1]}"
            except Exception:
                label = d
            result.append({
                "data":             label,
                "previsto_acum":    str(round(acum_prev, 2)),
                "executado_acum":   str(round(acum_exec, 2)),
            })
        return result

    # ── Por categoria (bar chart) ─────────────────────────────────────────────

    @staticmethod
    def compute_by_categoria(custos: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Aggregate previsto/executado by categoria for bar chart."""
        from collections import defaultdict
        prev_cat: Dict[str, float] = defaultdict(float)
        exec_cat: Dict[str, float] = defaultdict(float)

        for r in custos:
            cat = r.get("categoria_nome", "Outros") or "Outros"
            prev_cat[cat] += _parse_float(r.get("valor_previsto", 0))
            exec_cat[cat] += _parse_float(r.get("valor_executado", 0))

        all_cats = sorted(set(list(prev_cat.keys()) + list(exec_cat.keys())))
        return [
            {
                "categoria":  cat,
                "previsto":   str(round(prev_cat.get(cat, 0), 2)),
                "executado":  str(round(exec_cat.get(cat, 0), 2)),
            }
            for cat in all_cats
        ]
