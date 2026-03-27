"""
FinState — State for Financeiro por Projeto tab (Feature #21)
Manages CRUD for fin_custos, KPI cards, S-curve and categoria chart.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from bomtempo.core.fin_service import FinService
from bomtempo.core.supabase_client import sb_select

logger = logging.getLogger(__name__)

# Status options for custo
FIN_STATUS_OPTIONS = ["previsto", "em_andamento", "concluido", "cancelado"]
FIN_STATUS_LABELS = {
    "previsto":     "Previsto",
    "em_andamento": "Em Andamento",
    "concluido":    "Concluído",
    "cancelado":    "Cancelado",
}


class FinState(rx.State):
    """State for the Financeiro tab inside Hub de Operações."""

    # ── Loading ───────────────────────────────────────────────────────────────
    fin_loading: bool = False
    fin_saving: bool = False
    fin_error: str = ""

    # ── Data ─────────────────────────────────────────────────────────────────
    fin_contrato: str = ""          # current contract (set when tab activates)
    fin_custos: List[Dict[str, str]] = []
    fin_categorias: List[Dict[str, str]] = []

    # ── KPIs ─────────────────────────────────────────────────────────────────
    fin_kpis: Dict[str, str] = {
        "total_previsto":  "R$ 0,00",
        "total_executado": "R$ 0,00",
        "saldo":           "R$ 0,00",
        "pct_executado":   "0.0",
        "total_itens":     "0",
        "concluidos":      "0",
    }

    # ── Charts ───────────────────────────────────────────────────────────────
    fin_scurve: List[Dict[str, str]] = []
    fin_by_cat: List[Dict[str, str]] = []

    # ── Filter ───────────────────────────────────────────────────────────────
    fin_filter_status: str = ""
    fin_filter_categoria: str = ""
    fin_search: str = ""
    fin_search_input: str = ""

    # ── New/Edit dialog ───────────────────────────────────────────────────────
    fin_show_dialog: bool = False
    fin_edit_id: str = ""           # empty = new
    fin_edit_categoria_id: str = ""
    fin_edit_categoria_nome: str = ""
    fin_edit_descricao: str = ""
    fin_edit_valor_previsto: str = ""
    fin_edit_valor_executado: str = ""
    fin_edit_status: str = "previsto"
    fin_edit_data: str = ""
    fin_edit_atividade_id: str = ""
    fin_edit_observacoes: str = ""

    # ── Delete confirm ────────────────────────────────────────────────────────
    fin_show_delete: bool = False
    fin_delete_id: str = ""
    fin_delete_desc: str = ""

    # ── Activity options (from hub_atividades for this contract) ─────────────
    fin_atividade_options: List[Dict[str, str]] = []

    # ═════════════════════════════════════════════════════════════════════════
    # Computed vars
    # ═════════════════════════════════════════════════════════════════════════

    @rx.var
    def filtered_custos(self) -> List[Dict[str, str]]:
        rows = self.fin_custos
        if self.fin_filter_status:
            rows = [r for r in rows if r.get("status") == self.fin_filter_status]
        if self.fin_filter_categoria:
            rows = [r for r in rows if r.get("categoria_nome") == self.fin_filter_categoria]
        if self.fin_search:
            q = self.fin_search.lower()
            rows = [
                r for r in rows
                if q in r.get("descricao", "").lower()
                or q in r.get("categoria_nome", "").lower()
            ]
        return rows

    @rx.var
    def fin_categoria_options(self) -> List[str]:
        """Unique categoria names for filter dropdown."""
        seen = []
        for r in self.fin_custos:
            n = r.get("categoria_nome", "")
            if n and n not in seen:
                seen.append(n)
        return seen

    @rx.var
    def fin_dialog_title(self) -> str:
        return "Editar Custo" if self.fin_edit_id else "Novo Custo"

    # ═════════════════════════════════════════════════════════════════════════
    # Load
    # ═════════════════════════════════════════════════════════════════════════

    @rx.event(background=True)
    async def load_financeiro(self, contrato: str):
        async with self:
            self.fin_loading = True
            self.fin_custos = []
            self.fin_kpis = {}
            self.fin_scurve = []
            self.fin_by_cat = []
            self.fin_contrato = contrato
            self.fin_filter_status = ""
            self.fin_filter_categoria = ""
            self.fin_search = ""
            self.fin_search_input = ""

        try:
            # Load categorias (once, small table)
            cats = FinService.load_categorias()
            # Load custos for this contract
            custos = FinService.load_custos(contrato)
            # Load atividades for dropdown
            try:
                ativ_rows = sb_select(
                    "hub_atividades",
                    filters={"contrato": contrato},
                    order="fase_macro.asc,atividade.asc",
                    limit=300,
                )
                ativ_opts = [
                    {"id": str(r.get("id", "")), "label": str(r.get("atividade", ""))}
                    for r in (ativ_rows or [])
                ]
            except Exception:
                ativ_opts = []

            kpis = FinService.compute_kpis(custos)
            scurve = FinService.compute_scurve(custos)
            by_cat = FinService.compute_by_categoria(custos)

        except Exception as e:
            logger.error(f"load_financeiro error: {e}")
            cats, custos, ativ_opts, kpis, scurve, by_cat = [], [], [], {}, [], []

        async with self:
            self.fin_categorias = cats
            self.fin_custos = custos
            self.fin_atividade_options = ativ_opts
            self.fin_kpis = kpis
            self.fin_scurve = scurve
            self.fin_by_cat = by_cat
            self.fin_loading = False

    def _refresh_charts(self):
        """Recompute KPIs + charts from current fin_custos. Call after mutations."""
        self.fin_kpis = FinService.compute_kpis(self.fin_custos)
        self.fin_scurve = FinService.compute_scurve(self.fin_custos)
        self.fin_by_cat = FinService.compute_by_categoria(self.fin_custos)

    # ═════════════════════════════════════════════════════════════════════════
    # Dialog open/close
    # ═════════════════════════════════════════════════════════════════════════

    def open_fin_new(self):
        self.fin_edit_id = ""
        self.fin_edit_categoria_id = ""
        self.fin_edit_categoria_nome = ""
        self.fin_edit_descricao = ""
        self.fin_edit_valor_previsto = ""
        self.fin_edit_valor_executado = ""
        self.fin_edit_status = "previsto"
        self.fin_edit_data = ""
        self.fin_edit_atividade_id = ""
        self.fin_edit_observacoes = ""
        self.fin_error = ""
        self.fin_show_dialog = True

    def open_fin_edit(self, custo_id: str):
        row = next((r for r in self.fin_custos if r.get("id") == custo_id), None)
        if not row:
            return
        self.fin_edit_id = custo_id
        self.fin_edit_categoria_id = row.get("categoria_id", "")
        self.fin_edit_categoria_nome = row.get("categoria_nome", "")
        self.fin_edit_descricao = row.get("descricao", "")
        self.fin_edit_valor_previsto = row.get("valor_previsto", "")
        self.fin_edit_valor_executado = row.get("valor_executado", "")
        self.fin_edit_status = row.get("status", "previsto")
        self.fin_edit_data = row.get("data_custo", "")
        self.fin_edit_atividade_id = row.get("atividade_id", "")
        self.fin_edit_observacoes = row.get("observacoes", "")
        self.fin_error = ""
        self.fin_show_dialog = True

    def close_fin_dialog(self):
        self.fin_show_dialog = False

    def set_fin_show_dialog(self, v: bool):
        self.fin_show_dialog = v

    # ═════════════════════════════════════════════════════════════════════════
    # Field setters for dialog
    # ═════════════════════════════════════════════════════════════════════════

    def set_fin_edit_categoria(self, v: str):
        """v is categoria_id. Also look up nome."""
        self.fin_edit_categoria_id = v
        cat = next((c for c in self.fin_categorias if c.get("id") == v), None)
        self.fin_edit_categoria_nome = cat["nome"] if cat else v

    def set_fin_edit_descricao(self, v: str):
        self.fin_edit_descricao = v

    def set_fin_edit_valor_previsto(self, v: str):
        self.fin_edit_valor_previsto = v

    def set_fin_edit_valor_executado(self, v: str):
        self.fin_edit_valor_executado = v

    def set_fin_edit_status(self, v: str):
        self.fin_edit_status = v

    def set_fin_edit_data(self, v: str):
        self.fin_edit_data = v

    def set_fin_edit_atividade(self, v: str):
        self.fin_edit_atividade_id = v if v != "__none__" else ""

    def set_fin_edit_observacoes(self, v: str):
        self.fin_edit_observacoes = v

    # ═════════════════════════════════════════════════════════════════════════
    # Filter setters
    # ═════════════════════════════════════════════════════════════════════════

    def set_fin_filter_status(self, v: str):
        self.fin_filter_status = "" if v == "__none__" else v

    def set_fin_filter_categoria(self, v: str):
        self.fin_filter_categoria = "" if v == "__none__" else v

    def set_fin_search_input(self, v: str):
        self.fin_search_input = v

    def commit_fin_search(self, _v: str = ""):
        self.fin_search = self.fin_search_input

    def handle_fin_search_key(self, key: str):
        if key == "Enter":
            self.fin_search = self.fin_search_input

    # ═════════════════════════════════════════════════════════════════════════
    # Save
    # ═════════════════════════════════════════════════════════════════════════

    @rx.event(background=True)
    async def save_fin_custo(self):
        async with self:
            # Validate
            if not self.fin_edit_descricao.strip():
                self.fin_error = "Descrição é obrigatória."
                return
            prev_str = self.fin_edit_valor_previsto.strip() or "0"
            exec_str = self.fin_edit_valor_executado.strip() or "0"
            self.fin_saving = True
            self.fin_error = ""
            contrato = self.fin_contrato
            custo_id = self.fin_edit_id
            cat_id = self.fin_edit_categoria_id
            cat_nome = self.fin_edit_categoria_nome
            descricao = self.fin_edit_descricao.strip()
            status = self.fin_edit_status
            data = self.fin_edit_data
            atividade_id = self.fin_edit_atividade_id
            obs = self.fin_edit_observacoes

        from bomtempo.core.fin_service import _parse_float as _pf
        prev_val = _pf(prev_str)
        exec_val = _pf(exec_str)

        # Get username
        try:
            from bomtempo.state.global_state import GlobalState
            gs = await self.get_state(GlobalState)
            username = gs.username
        except Exception:
            username = ""

        ok, result = FinService.save_custo(
            contrato=contrato,
            categoria_id=cat_id,
            categoria_nome=cat_nome,
            descricao=descricao,
            valor_previsto=prev_val,
            valor_executado=exec_val,
            status=status,
            data_custo=data,
            atividade_id=atividade_id,
            observacoes=obs,
            created_by=username,
            custo_id=custo_id,
        )

        if not ok:
            async with self:
                self.fin_error = f"Erro ao salvar: {result[:120]}"
                self.fin_saving = False
            return

        # Reload custos list
        custos = FinService.load_custos(contrato)
        scurve = FinService.compute_scurve(custos)
        by_cat = FinService.compute_by_categoria(custos)
        kpis = FinService.compute_kpis(custos)

        async with self:
            self.fin_custos = custos
            self.fin_scurve = scurve
            self.fin_by_cat = by_cat
            self.fin_kpis = kpis
            self.fin_saving = False
            self.fin_show_dialog = False

    # ═════════════════════════════════════════════════════════════════════════
    # Delete
    # ═════════════════════════════════════════════════════════════════════════

    def request_fin_delete(self, custo_id: str):
        row = next((r for r in self.fin_custos if r.get("id") == custo_id), None)
        self.fin_delete_id = custo_id
        self.fin_delete_desc = row.get("descricao", custo_id[:8]) if row else custo_id[:8]
        self.fin_show_delete = True

    def cancel_fin_delete(self):
        self.fin_show_delete = False
        self.fin_delete_id = ""
        self.fin_delete_desc = ""

    @rx.event(background=True)
    async def confirm_fin_delete(self):
        async with self:
            custo_id = self.fin_delete_id
            contrato = self.fin_contrato
            self.fin_show_delete = False

        ok = FinService.delete_custo(custo_id)
        if not ok:
            async with self:
                self.fin_error = "Erro ao excluir custo."
            return

        custos = FinService.load_custos(contrato)
        scurve = FinService.compute_scurve(custos)
        by_cat = FinService.compute_by_categoria(custos)
        kpis = FinService.compute_kpis(custos)

        async with self:
            self.fin_custos = custos
            self.fin_scurve = scurve
            self.fin_by_cat = by_cat
            self.fin_kpis = kpis
            self.fin_delete_id = ""
            self.fin_delete_desc = ""
