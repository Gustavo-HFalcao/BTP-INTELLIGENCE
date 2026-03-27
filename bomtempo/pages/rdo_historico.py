"""
RDO v2 Histórico — Lista de RDOs com dados da tabela rdo_master.
Rota: /rdo2-historico
"""

import asyncio
import json as _json
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

    # ── Email notification management ─────────────────────────
    emails_list: List[Dict[str, str]] = []
    emails_loading: bool = False
    new_email_input: str = ""
    emails_error: str = ""

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
            """Converte ISO UTC datetime → DD/MM/YYYY HH:MM (BRT, UTC-3)."""
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td
            _BRT = _tz(_td(hours=-3))
            v = str(val or "")
            if not v or len(v) < 16:
                return v
            try:
                dt = _dt.fromisoformat(v.replace("Z", "+00:00")[:32])
                brt = dt.astimezone(_BRT)
                return brt.strftime("%d/%m/%Y %H:%M")
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

    def set_new_email_input(self, v: str):
        self.new_email_input = v

    def handle_email_keydown(self, key: str):
        if key == "Enter":
            return RDOHistoricoState.add_email

    @rx.event(background=True)
    async def load_emails(self):
        async with self:
            self.emails_loading = True
            self.emails_error = ""
        from bomtempo.core.supabase_client import sb_select as _sel
        try:
            rows = _sel("email_sender", filters={"module": "rdo"}, order="created_at.asc", limit=50) or []
            normalized = [{"id": str(r.get("id", "")), "email": str(r.get("email", ""))} for r in rows]
        except Exception as e:
            normalized = []
            async with self:
                self.emails_error = f"Erro ao carregar e-mails: {str(e)[:80]}"
        async with self:
            self.emails_list = normalized
            self.emails_loading = False

    @rx.event(background=True)
    async def add_email(self):
        email = ""
        async with self:
            email = self.new_email_input.strip().lower()
        if not email or "@" not in email:
            async with self:
                self.emails_error = "E-mail inválido."
            return
        from bomtempo.core.supabase_client import sb_insert as _ins
        try:
            _ins("email_sender", {"module": "rdo", "email": email})
        except Exception as e:
            async with self:
                self.emails_error = f"Erro ao adicionar: {str(e)[:80]}"
            return
        async with self:
            self.new_email_input = ""
            self.emails_error = ""
        yield RDOHistoricoState.load_emails

    @rx.event(background=True)
    async def remove_email(self, email_id: str):
        from bomtempo.core.supabase_client import sb_delete as _del
        try:
            _del("email_sender", filters={"id": email_id})
        except Exception as e:
            async with self:
                self.emails_error = f"Erro ao remover: {str(e)[:80]}"
            return
        yield RDOHistoricoState.load_emails

    def open_external_url(self, url: str):
        """Abre URL em nova aba via JS — bypassa o router SPA/PWA."""
        if url and url.startswith("http"):
            safe = _json.dumps(url)
            return rx.call_script(f"window.open({safe}, '_blank', 'noopener,noreferrer')")

    @rx.event(background=True)
    async def delete_draft_rdo(self, id_rdo: str):
        """Exclui um RDO com status=rascunho. Recusa excluir finalizados."""
        if not id_rdo:
            return
        loop = asyncio.get_running_loop()
        # Safety check: only delete drafts
        rows = await loop.run_in_executor(
            None,
            lambda: RDOService.get_full_rdo(id_rdo),
        )
        if not rows:
            async with self:
                yield rx.toast("❌ RDO não encontrado.", position="top-center")
            return
        if rows.get("status") != "rascunho":
            async with self:
                yield rx.toast("❌ Apenas rascunhos podem ser excluídos.", position="top-center")
            return
        ok = await loop.run_in_executor(None, lambda: RDOService.delete_draft(id_rdo))
        async with self:
            if ok:
                self.rdos_list = [r for r in self.rdos_list if r.get("id_rdo") != id_rdo]
                yield rx.toast("🗑️ Rascunho excluído.", position="top-center")
            else:
                yield rx.toast("❌ Falha ao excluir rascunho.", position="top-center")


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
                    rx.link(
                        rx.button(
                            rx.icon("eye", size=14),
                            "Ver online",
                            size="1",
                            style={
                                "background": "rgba(42,157,143,0.12)",
                                "border": "1px solid rgba(42,157,143,0.3)",
                                "color": _PATINA,
                                "border_radius": "5px",
                                "cursor": "pointer",
                            },
                        ),
                        href=f"/rdo-view/{rdo['view_token']}",
                        is_external=True,
                    ),
                ),
                rx.cond(
                    rdo["status"] == "rascunho",
                    rx.hstack(
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
                        rx.button(
                            rx.icon("trash-2", size=14),
                            on_click=RDOHistoricoState.delete_draft_rdo(rdo["id_rdo"]),
                            size="1",
                            style={
                                "background": "rgba(239,68,68,0.08)",
                                "border": "1px solid rgba(239,68,68,0.25)",
                                "color": "#EF4444",
                                "border_radius": "5px",
                                "cursor": "pointer",
                            },
                            title="Excluir rascunho",
                        ),
                        spacing="1",
                        align="center",
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

def _email_row(item: Dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.icon("mail", size=13, color=_MUTED),
        rx.text(item["email"], size="2", color=_TEXT, flex="1"),
        rx.icon_button(
            rx.icon("trash-2", size=13),
            variant="ghost", size="1",
            on_click=RDOHistoricoState.remove_email(item["id"]),
            style={"color": "#EF4444", "cursor": "pointer"},
        ),
        spacing="2", align="center", width="100%",
        padding="8px 12px",
        border_radius="6px",
        background="rgba(255,255,255,0.03)",
        border=f"1px solid {_BORDER}",
    )


def _tab_emails() -> rx.Component:
    return rx.vstack(
        rx.text(
            "Defina quem recebe notificações por e-mail quando um RDO for finalizado.",
            size="2", color=_MUTED, margin_bottom="16px",
        ),
        # Add email row
        rx.hstack(
            rx.input(
                placeholder="novo@email.com",
                value=RDOHistoricoState.new_email_input,
                on_change=RDOHistoricoState.set_new_email_input,
                on_key_down=RDOHistoricoState.handle_email_keydown,
                style={
                    "background": "rgba(255,255,255,0.06)",
                    "border": f"1px solid {_BORDER}",
                    "border_radius": "6px",
                    "color": _TEXT,
                    "flex": "1",
                },
            ),
            rx.button(
                rx.icon("plus", size=14),
                "Adicionar",
                on_click=RDOHistoricoState.add_email,
                size="2",
                style={"background": _BTN_PRI, "color": "#fff", "border_radius": "6px", "cursor": "pointer"},
            ),
            spacing="2", width="100%",
        ),
        rx.cond(
            RDOHistoricoState.emails_error != "",
            rx.text(RDOHistoricoState.emails_error, size="1", color="#EF4444"),
        ),
        rx.separator(width="100%", margin_y="12px"),
        # List
        rx.cond(
            RDOHistoricoState.emails_loading,
            rx.center(rx.spinner(size="2"), padding="24px"),
            rx.cond(
                RDOHistoricoState.emails_list.length() == 0,
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=28, color=_MUTED),
                        rx.text("Nenhum e-mail cadastrado", size="2", color=_MUTED),
                        spacing="2", align="center",
                    ),
                    padding="32px",
                ),
                rx.vstack(
                    rx.foreach(RDOHistoricoState.emails_list, _email_row),
                    spacing="2", width="100%",
                ),
            ),
        ),
        spacing="3", width="100%",
    )


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
        # Main tabs: RDOs | E-mails
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger(
                    rx.hstack(rx.icon("file-text", size=14), rx.text("Meus RDOs"), spacing="2", align="center"),
                    value="rdos",
                    style={"cursor": "pointer"},
                ),
                rx.tabs.trigger(
                    rx.hstack(rx.icon("mail", size=14), rx.text("E-mails de Notificação"), spacing="2", align="center"),
                    value="emails",
                    on_click=RDOHistoricoState.load_emails,
                    style={"cursor": "pointer"},
                ),
                margin_bottom="16px",
            ),
            # Tab: RDOs
            rx.tabs.content(
                rx.vstack(
                    # Filter bar
                    rx.hstack(
                        _filter_tab("Todos", "todos", RDOHistoricoState.filter_status),
                        _filter_tab("Finalizados", "finalizado", RDOHistoricoState.filter_status),
                        _filter_tab("Rascunhos", "rascunho", RDOHistoricoState.filter_status),
                        rx.spacer(),
                        rx.button(
                            rx.icon("refresh-cw", size=14),
                            on_click=RDOHistoricoState.load_rdos,
                            size="1", variant="ghost", color=_MUTED,
                        ),
                        spacing="2", align="center",
                    ),
                    # List
                    rx.cond(
                        RDOHistoricoState.is_loading,
                        rx.center(
                            rx.vstack(
                                rx.spinner(size="3"),
                                rx.text("Carregando RDOs…", size="2", color=_MUTED),
                                spacing="2", align="center",
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
                                    spacing="3", align="center",
                                ),
                                padding="60px",
                            ),
                            rx.vstack(
                                rx.foreach(RDOHistoricoState.filtered_rdos, _rdo_card),
                                spacing="2", width="100%",
                            ),
                        ),
                    ),
                    spacing="3", width="100%",
                ),
                value="rdos",
            ),
            # Tab: E-mails
            rx.tabs.content(
                _tab_emails(),
                value="emails",
            ),
            default_value="rdos",
            width="100%",
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
