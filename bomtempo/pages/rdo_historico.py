"""
RDO v2 Histórico — Lista de RDOs com dados da tabela rdo_master.
Rota: /rdo2-historico
"""

import asyncio
from typing import Any, Dict, List

import reflex as rx

from bomtempo.state.global_state import GlobalState
from bomtempo.core.rdo_service import RDOService
from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

_BG      = "#0B1A15"
_CARD    = "rgba(255,255,255,0.04)"
_BORDER  = "rgba(255,255,255,0.10)"
_COPPER  = "#C98B2A"
_PATINA  = "#2A9D8F"
_TEXT    = "#E8F0EE"
_MUTED   = "#6B9090"
_BTN_PRI = "linear-gradient(135deg,#C98B2A,#9B6820)"


# ── State ────────────────────────────────────────────────────────────────────

class RDOHistoricoState(rx.State):
    rdos_list: List[Dict[str, str]] = []
    is_loading: bool = False
    filter_status: str = "todos"  # todos | rascunho | finalizado

    @rx.var
    def filtered_rdos(self) -> List[Dict[str, str]]:
        if self.filter_status == "todos":
            return self.rdos_list
        return [r for r in self.rdos_list if r.get("status", "") == self.filter_status]

    @rx.var
    def count_rascunho(self) -> int:
        return sum(1 for r in self.rdos_list if r.get("status") == "rascunho")

    @rx.var
    def count_finalizado(self) -> int:
        return sum(1 for r in self.rdos_list if r.get("status") == "finalizado")

    @rx.event(background=True)
    async def load_rdos(self):
        async with self:
            self.is_loading = True
            gs = await self.get_state(GlobalState)
            user = str(gs.current_user_name)
            role = str(gs.current_user_role)
            contrato = str(gs.current_user_contrato).strip()

        loop = asyncio.get_running_loop()

        # Filtrar por role
        if role in ("Administrador", "admin", "Gestão-Mobile"):
            rdos = await loop.run_in_executor(None, lambda: RDOService.get_rdos_list(limit=200))
        elif role == "Mestre de Obras":
            rdos = await loop.run_in_executor(
                None,
                lambda: RDOService.get_rdos_list(contrato=contrato, mestre_id=user, limit=100),
            )
        else:
            rdos = await loop.run_in_executor(
                None,
                lambda: RDOService.get_rdos_list(contrato=contrato, limit=100),
            )

        def _fmt_date(val: str) -> str:
            """Converte YYYY-MM-DD ou ISO datetime → DD/MM/YYYY."""
            v = str(val or "")[:10]
            if len(v) == 10 and v[4] == "-":
                try:
                    parts = v.split("-")
                    return f"{parts[2]}/{parts[1]}/{parts[0]}"
                except Exception:
                    pass
            return v

        def _fmt_datetime(val: str) -> str:
            """Converte ISO datetime → DD/MM/YYYY HH:MM."""
            v = str(val or "")
            if len(v) >= 16 and v[4] == "-":
                try:
                    date_part = v[:10].split("-")
                    time_part = v[11:16]
                    return f"{date_part[2]}/{date_part[1]}/{date_part[0]} {time_part}"
                except Exception:
                    pass
            return v[:16].replace("T", " ")

        # Normalizar para exibição
        normalized = []
        for r in (rdos or []):
            normalized.append({
                "id_rdo":     str(r.get("id_rdo", "")),
                "contrato":   str(r.get("contrato", "")),
                "data":       _fmt_date(r.get("data", "")),
                "status":     str(r.get("status", "rascunho")),
                "clima":      str(r.get("condicao_climatica", "")),
                "turno":      str(r.get("turno", "")),
                "mestre":     str(r.get("mestre_id", "")),
                "pdf_url":    str(r.get("pdf_url", "")),
                "view_token": str(r.get("view_token", "")),
                "checkin":    "✓" if r.get("checkin_lat") else "—",
                "created_at": _fmt_datetime(r.get("created_at", "")),
            })

        async with self:
            self.rdos_list = normalized
            self.is_loading = False

    def set_filter(self, status: str):
        self.filter_status = status

    def open_external_url(self, url: str):
        """Abre URL em nova aba via JS — bypassa o router SPA/PWA."""
        if url and url.startswith("http"):
            return rx.call_script(f"window.open({repr(url)}, '_blank', 'noopener,noreferrer')")


# ── Components ───────────────────────────────────────────────────────────────

def _status_badge(status: str) -> rx.Component:
    return rx.cond(
        status == "finalizado",
        rx.badge("Finalizado", color_scheme="teal", variant="soft", size="1"),
        rx.badge("Rascunho", color_scheme="amber", variant="soft", size="1"),
    )


def _rdo_card(rdo: Dict[str, Any]) -> rx.Component:
    has_pdf = (rdo["pdf_url"] != "") & rdo["pdf_url"].startswith("http")
    has_token = rdo["view_token"] != ""

    return rx.box(
        rx.hstack(
            # Left: id + meta
            rx.vstack(
                rx.hstack(
                    rx.text(rdo["id_rdo"], size="2", weight="bold", color=_COPPER,
                            style={"font_family": "monospace"}),
                    _status_badge(rdo["status"]),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.hstack(
                    rx.icon("calendar", size=12, color=_MUTED),
                    rx.text(rdo["data"], size="1", color=_MUTED),
                    rx.text("·", color=_MUTED),
                    rx.icon("user", size=12, color=_MUTED),
                    rx.text(rdo["mestre"], size="1", color=_MUTED),
                    rx.text("·", color=_MUTED),
                    rx.icon("cloud", size=12, color=_MUTED),
                    rx.text(rdo["clima"], size="1", color=_MUTED),
                    rx.text("·", color=_MUTED),
                    rx.text(f"GPS: {rdo['checkin']}", size="1", color=_MUTED),
                    spacing="1",
                    align="center",
                    flex_wrap="wrap",
                ),
                spacing="1",
                align="start",
                flex="1",
            ),
            rx.spacer(),
            # Actions
            rx.hstack(
                rx.cond(
                    has_pdf,
                    rx.button(
                        rx.icon("download", size=14),
                        "PDF",
                        on_click=RDOHistoricoState.open_external_url(rdo["pdf_url"]),
                        size="1",
                        style={
                            "background": "rgba(201,139,42,0.12)",
                            "border": "1px solid rgba(201,139,42,0.3)",
                            "color": _COPPER,
                            "border_radius": "5px",
                            "cursor": "pointer",
                        },
                    ),
                ),
                rx.cond(
                    has_token,
                    rx.button(
                        rx.icon("eye", size=14),
                        "Ver online",
                        on_click=rx.redirect(f"/rdo-view/{rdo['view_token']}"),
                        size="1",
                        style={
                            "background": "rgba(42,157,143,0.12)",
                            "border": "1px solid rgba(42,157,143,0.3)",
                            "color": _PATINA,
                            "border_radius": "5px",
                            "cursor": "pointer",
                        },
                    ),
                ),
                rx.cond(
                    rdo["status"] == "rascunho",
                    rx.button(
                        rx.icon("pencil", size=14),
                        "Continuar",
                        on_click=rx.redirect("/rdo-form"),
                        size="1",
                        style={
                            "background": "rgba(255,255,255,0.06)",
                            "border": f"1px solid {_BORDER}",
                            "color": _TEXT,
                            "border_radius": "5px",
                        },
                    ),
                ),
                spacing="1",
                align="center",
            ),
            align="center",
            width="100%",
            flex_wrap="wrap",
            gap="8px",
        ),
        padding="14px 16px",
        background=_CARD,
        border=f"1px solid {_BORDER}",
        border_radius="10px",
        style={
            "_hover": {"border_color": "rgba(201,139,42,0.3)", "background": "rgba(255,255,255,0.06)"},
            "transition": "all 0.15s ease",
        },
    )


# ── Page ─────────────────────────────────────────────────────────────────────

def rdo_historico_page() -> rx.Component:
    return rx.box(
        # Header
        rx.hstack(
            rx.vstack(
                rx.text("Histórico de RDOs", size="6", weight="bold", color=_TEXT),
                rx.text("Relatórios Diários de Obra — v2", size="2", color=_MUTED),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("plus", size=16),
                "Novo RDO",
                on_click=rx.redirect("/rdo-form"),
                size="2",
                style={"background": _BTN_PRI, "color": "#fff", "border_radius": "8px", "font_weight": "600", "min_height": "44px"},
            ),
            align="center",
            margin_bottom="24px",
        ),
        # Stats row
        rx.grid(
            _stat_card("Total", RDOHistoricoState.rdos_list.length().to_string(), "file-text", _COPPER),
            _stat_card("Finalizados", RDOHistoricoState.count_finalizado.to_string(), "check-circle", _PATINA),
            _stat_card("Rascunhos", RDOHistoricoState.count_rascunho.to_string(), "clock", "#E0A030"),
            columns={"initial": "1", "sm": "3"},
            gap="12px",
            margin_bottom="20px",
        ),
        # Filter tabs
        rx.hstack(
            _filter_tab("Todos", "todos", RDOHistoricoState.filter_status),
            _filter_tab("Finalizados", "finalizado", RDOHistoricoState.filter_status),
            _filter_tab("Rascunhos", "rascunho", RDOHistoricoState.filter_status),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                on_click=RDOHistoricoState.load_rdos,
                size="1",
                variant="ghost",
                color=_MUTED,
            ),
            spacing="2",
            align="center",
            margin_bottom="16px",
        ),
        # List
        rx.cond(
            RDOHistoricoState.is_loading,
            rx.center(
                rx.vstack(
                    rx.spinner(size="3"),
                    rx.text("Carregando RDOs…", size="2", color=_MUTED),
                    spacing="2",
                    align="center",
                ),
                padding="60px",
            ),
            rx.cond(
                RDOHistoricoState.filtered_rdos.length() == 0,
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=40, color=_MUTED),
                        rx.text("Nenhum RDO encontrado", size="3", color=_MUTED),
                        rx.button(
                            "Criar primeiro RDO",
                            on_click=rx.redirect("/rdo-form"),
                            size="2",
                            style={"background": _BTN_PRI, "color": "#fff", "border_radius": "6px"},
                        ),
                        spacing="3",
                        align="center",
                    ),
                    padding="60px",
                ),
                rx.vstack(
                    rx.foreach(RDOHistoricoState.filtered_rdos, _rdo_card),
                    spacing="2",
                    width="100%",
                ),
            ),
        ),
        padding=["16px", "28px"],
        max_width="960px",
        margin="0 auto",
        min_height="100vh",
        background=_BG,
    )


def _stat_card(label: str, value: rx.Var, icon: str, color: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(label, size="1", color=_MUTED, weight="medium"),
                rx.text(value, size="6", weight="bold", color=color),
                spacing="0",
            ),
            rx.spacer(),
            rx.icon(icon, size=24, color=color, opacity="0.5"),
            align="center",
        ),
        padding="16px 20px",
        background=_CARD,
        border=f"1px solid {_BORDER}",
        border_radius="10px",
    )


def _filter_tab(label: str, value: str, current: rx.Var) -> rx.Component:
    is_active = current == value
    return rx.button(
        label,
        on_click=RDOHistoricoState.set_filter(value),
        size="2",
        style={
            "background": rx.cond(is_active, "rgba(201,139,42,0.2)", "rgba(255,255,255,0.04)"),
            "border": rx.cond(is_active, f"1px solid rgba(201,139,42,0.5)", f"1px solid {_BORDER}"),
            "color": rx.cond(is_active, _COPPER, _MUTED),
            "border_radius": "6px",
            "cursor": "pointer",
            "font_weight": rx.cond(is_active, "600", "400"),
        },
    )
