"""
RDO Dashboard State — KPIs, filtros e dados para Admin/Gestor
Carrega dados de TODAS as 5 tabelas RDO do Supabase:
  rdo_cabecalho, rdo_mao_obra, rdo_equipamentos, rdo_atividades, rdo_materiais
"""

from datetime import datetime, timedelta

import reflex as rx

from bomtempo.core.logging_utils import get_logger
from bomtempo.core.rdo_service import RDOService
from bomtempo.core.supabase_client import sb_select

logger = get_logger(__name__)


class RDODashboardState(rx.State):
    """Estado do Dashboard 360° de RDOs"""

    # Dados brutos (rdo_cabecalho)
    rdos: list[dict] = []

    # Filtros
    filtro_contrato: str = "Todos"
    filtro_periodo: str = "30"  # dias

    # KPIs calculados
    kpi_total: int = 0
    kpi_obras_ativas: int = 0
    kpi_ultima_data: str = "—"
    kpi_hoje: int = 0

    # KPIs extras (detalhes)
    kpi_profissionais: int = 0
    kpi_equipamentos: int = 0
    kpi_atividades: int = 0

    # Gráfico: RDOs por dia (últimos N dias)
    grafico_por_dia: list[dict] = []

    # Gráfico: Distribuição climática
    grafico_clima: list[dict] = []

    # Gráfico: Mão de obra por contrato
    grafico_mo_contrato: list[dict] = []

    # Gráfico: Equipamentos por tipo
    grafico_equipamentos: list[dict] = []

    # Gráfico: Atividades por status
    grafico_atividades_status: list[dict] = []

    # Gráfico: Top materiais (custo)
    grafico_materiais: list[dict] = []

    # Lista de contratos disponíveis para filtro
    contratos_disponiveis: list[str] = ["Todos"]

    # Loading
    is_loading: bool = False

    async def load_dashboard(self):
        """Carrega e calcula todos os dados do dashboard (5 tabelas)"""
        self.is_loading = True
        yield

        import asyncio

        await asyncio.sleep(1)  # Sincronismo visual forçado / UX

        try:
            # ── 1. rdo_cabecalho ──────────────────────────────────
            all_rdos = RDOService.get_all_rdos(limit=500)
            logger.info(f"📊 Dashboard: {len(all_rdos)} cabeçalhos")

            # Contratos disponíveis
            contratos = sorted(set(r.get("Contrato", "") for r in all_rdos if r.get("Contrato")))
            self.contratos_disponiveis = ["Todos"] + contratos

            # Filtrar por período
            dias = int(self.filtro_periodo) if self.filtro_periodo.isdigit() else 30
            cutoff = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
            filtro_ctr = self.filtro_contrato

            def _match(r: dict) -> bool:
                d = r.get("Data") or "0"
                ctr = r.get("Contrato", "")
                return d >= cutoff and (filtro_ctr == "Todos" or ctr == filtro_ctr)

            filtered = [r for r in all_rdos if _match(r)]
            self.rdos = filtered  # mostrar somente os filtrados na tabela

            # KPIs
            self.kpi_total = len(filtered)
            self.kpi_obras_ativas = len(
                set(r.get("Contrato", "") for r in filtered if r.get("Contrato"))
            )
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.kpi_hoje = len([r for r in filtered if r.get("Data", "") == today_str])
            if filtered:
                datas = sorted(r.get("Data", "") for r in filtered if r.get("Data"))
                self.kpi_ultima_data = datas[-1] if datas else "—"
            else:
                self.kpi_ultima_data = "—"

            # RDOs por dia
            day_counts: dict[str, int] = {}
            for r in filtered:
                d = (r.get("Data") or "")[:10]
                if d:
                    day_counts[d] = day_counts.get(d, 0) + 1
            self.grafico_por_dia = [{"data": k, "rdos": v} for k, v in sorted(day_counts.items())][
                -30:
            ]

            # Clima
            clima_counts: dict[str, int] = {}
            for r in filtered:
                clima = r.get("Condicao_Climatica") or "Não informado"
                if clima in ("None", "nan", ""):
                    clima = "Não informado"
                clima_counts[clima] = clima_counts.get(clima, 0) + 1
            self.grafico_clima = [{"name": k, "value": v} for k, v in clima_counts.items()]

            # ── 2. rdo_mao_obra ───────────────────────────────────
            try:
                mo_rows = sb_select("rdo_mao_obra", limit=2000) or []
                # Filtrar por período e contrato
                mo_filtered = [
                    r
                    for r in mo_rows
                    if (r.get("Data") or "0") >= cutoff
                    and (filtro_ctr == "Todos" or r.get("Contrato") == filtro_ctr)
                ]
                # KPI total profissionais
                self.kpi_profissionais = sum(int(r.get("Quantidade", 0) or 0) for r in mo_filtered)
                # Por contrato
                mo_map: dict[str, int] = {}
                for r in mo_filtered:
                    ctr = r.get("Contrato", "?")
                    qtd = int(r.get("Quantidade", 0) or 0)
                    mo_map[ctr] = mo_map.get(ctr, 0) + qtd
                self.grafico_mo_contrato = [
                    {"contrato": k, "profissionais": v}
                    for k, v in sorted(mo_map.items(), key=lambda x: -x[1])
                ][:10]
            except Exception as e:
                logger.warning(f"⚠️ rdo_mao_obra: {e}")

            # ── 3. rdo_equipamentos ───────────────────────────────
            try:
                eq_rows = sb_select("rdo_equipamentos", limit=2000) or []
                eq_filtered = [
                    r
                    for r in eq_rows
                    if (r.get("Data") or "0") >= cutoff
                    and (filtro_ctr == "Todos" or r.get("Contrato") == filtro_ctr)
                ]
                self.kpi_equipamentos = len(eq_filtered)
                # Por tipo de equipamento
                eq_map: dict[str, int] = {}
                for r in eq_filtered:
                    eq = r.get("Equipamento", "?")
                    eq_map[eq] = eq_map.get(eq, 0) + int(r.get("Quantidade", 0) or 0)
                self.grafico_equipamentos = [
                    {"equipamento": k, "quantidade": v}
                    for k, v in sorted(eq_map.items(), key=lambda x: -x[1])
                ][:10]
            except Exception as e:
                logger.warning(f"⚠️ rdo_equipamentos: {e}")

            # ── 4. rdo_atividades ─────────────────────────────────
            try:
                at_rows = sb_select("rdo_atividades", limit=2000) or []
                at_filtered = [
                    r
                    for r in at_rows
                    if (r.get("Data") or "0") >= cutoff
                    and (filtro_ctr == "Todos" or r.get("Contrato") == filtro_ctr)
                ]
                self.kpi_atividades = len(at_filtered)
                # Por status
                status_map: dict[str, int] = {}
                for r in at_filtered:
                    st = r.get("Status") or "Sem status"
                    status_map[st] = status_map.get(st, 0) + 1
                self.grafico_atividades_status = [
                    {"name": k, "value": v} for k, v in status_map.items()
                ]
            except Exception as e:
                logger.warning(f"⚠️ rdo_atividades: {e}")

            # ── 5. rdo_materiais ──────────────────────────────────
            try:
                mt_rows = sb_select("rdo_materiais", limit=2000) or []
                mt_filtered = [
                    r
                    for r in mt_rows
                    if (r.get("Data") or "0") >= cutoff
                    and (filtro_ctr == "Todos" or r.get("Contrato") == filtro_ctr)
                ]
                # Top materiais por quantidade
                mt_map: dict[str, int] = {}
                for r in mt_filtered:
                    mat = r.get("Material", "?")
                    qtd = int(r.get("Quantidade", 0) or 0)
                    mt_map[mat] = mt_map.get(mat, 0) + qtd
                self.grafico_materiais = [
                    {"material": k, "quantidade": v}
                    for k, v in sorted(mt_map.items(), key=lambda x: -x[1])
                ][:10]
            except Exception as e:
                logger.warning(f"⚠️ rdo_materiais: {e}")

            logger.info(
                f"📊 Dashboard completo: {self.kpi_total} RDOs, "
                f"{self.kpi_profissionais} profissionais, "
                f"{self.kpi_equipamentos} registros equip, "
                f"{self.kpi_atividades} atividades"
            )

        except Exception as e:
            logger.error(f"❌ Erro ao carregar dashboard RDO: {e}", exc_info=True)
        finally:
            self.is_loading = False

    def set_filtro_contrato(self, value: str):
        self.filtro_contrato = value
        return RDODashboardState.load_dashboard

    def set_filtro_periodo(self, value: str):
        self.filtro_periodo = value
        return RDODashboardState.load_dashboard
