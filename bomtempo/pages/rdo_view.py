"""
RDO Public View — Visualização pública e interativa do RDO (sem login).
Rota: /rdo-view/[token]

Renderiza os dados nativamente (não iframe) com:
- Fotos clicáveis em lightbox com zoom
- Layout responsivo mobile
- AI summary inline
- Botão baixar PDF
"""

import asyncio
from typing import Any, Dict, List

import reflex as rx

from bomtempo.core.logging_utils import get_logger
from bomtempo.core.rdo_service import RDOService

logger = get_logger(__name__)

_BG     = "#0B1A15"
_COPPER = "#C98B2A"
_PATINA = "#2A9D8F"
_TEXT   = "#E8F0EE"
_MUTED  = "#6B9090"
_BORDER = "rgba(255,255,255,0.10)"
_CARD   = "rgba(255,255,255,0.04)"
_SURFACE = "#0E1A17"


# ── State ────────────────────────────────────────────────────────────────────

class RDOViewState(rx.State):
    rdo_html: str = ""           # kept for print fallback
    rdo_id: str = ""
    rdo_contrato: str = ""
    rdo_data: str = ""
    rdo_status: str = ""
    rdo_projeto: str = ""
    rdo_cliente: str = ""
    rdo_clima: str = ""
    rdo_turno: str = ""
    rdo_mestre: str = ""
    rdo_observacoes: str = ""
    rdo_orientacao: str = ""
    rdo_checkin_endereco: str = ""
    rdo_checkin_timestamp: str = ""
    rdo_checkout_endereco: str = ""
    rdo_checkout_timestamp: str = ""
    pdf_url: str = ""
    ai_summary: str = ""
    is_loading: bool = True
    not_found: bool = False
    # Evidences for interactive gallery
    evidencias: List[Dict[str, str]] = []
    # Atividades
    atividades: List[Dict[str, str]] = []
    # Lightbox
    lightbox_url: str = ""

    def open_lightbox(self, url: str):
        self.lightbox_url = url

    def close_lightbox(self):
        self.lightbox_url = ""

    @rx.event(background=True)
    async def load_rdo(self):
        async with self:
            self.is_loading = True
            self.not_found = False
            token = str(self.router.page.params.get("token", ""))

        loop = asyncio.get_running_loop()
        data: Dict[str, Any] = await loop.run_in_executor(
            None,
            lambda: RDOService.get_by_token(token),
        )

        if not data:
            async with self:
                self.is_loading = False
                self.not_found = True
            return

        # Extract evidence list
        evidencias_raw = data.get("evidencias") or []
        ev_list = []
        for e in evidencias_raw:
            url = str(e.get("foto_url") or e.get("url") or "")
            legenda = str(e.get("legenda") or "")
            if url:
                ev_list.append({"url": url, "legenda": legenda})

        # Extract atividades
        atividades_raw = data.get("atividades") or []
        at_list = []
        for a in atividades_raw:
            at_list.append({
                "descricao": str(a.get("atividade") or a.get("descricao") or a.get("description") or ""),
                "status": str(a.get("status") or ""),
                "percentual": str(a.get("progresso_percentual") or a.get("percentual_conclusao") or a.get("pct") or ""),
            })

        # Build HTML for print
        html = await loop.run_in_executor(
            None,
            lambda: RDOService.build_html(data, is_preview=False),
        )

        async with self:
            self.rdo_html             = html
            self.rdo_id               = data.get("id_rdo", "")
            self.rdo_contrato         = data.get("contrato", "")
            self.rdo_data             = str(data.get("data", ""))
            self.rdo_status           = data.get("status", "")
            self.rdo_projeto          = str(data.get("projeto") or "")
            self.rdo_cliente          = str(data.get("cliente") or "")
            self.rdo_clima            = str(data.get("condicao_climatica") or data.get("clima") or "")
            self.rdo_turno            = str(data.get("turno") or "")
            self.rdo_mestre           = str(data.get("mestre_id") or "")
            self.rdo_observacoes      = str(data.get("observacoes") or "")
            self.rdo_orientacao       = str(data.get("orientacao") or "")
            self.rdo_checkin_endereco = str(data.get("checkin_endereco") or "")
            self.rdo_checkin_timestamp = str(data.get("checkin_timestamp") or "")
            self.rdo_checkout_endereco = str(data.get("checkout_endereco") or "")
            self.rdo_checkout_timestamp = str(data.get("checkout_timestamp") or "")
            self.pdf_url              = data.get("pdf_url", "")
            self.ai_summary           = data.get("ai_summary", "")
            self.evidencias           = ev_list
            self.atividades           = at_list
            self.is_loading           = False


# ── Components ───────────────────────────────────────────────────────────────

def _info_row(label: str, value: rx.Component | str) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="1", color=_MUTED, width="110px", flex_shrink="0"),
        rx.text(value, size="2", color=_TEXT, weight="medium") if isinstance(value, str) else value,
        spacing="3",
        align="start",
        width="100%",
    )


def _badge_status() -> rx.Component:
    return rx.cond(
        RDOViewState.rdo_status == "finalizado",
        rx.badge("Finalizado", color_scheme="teal", variant="soft", size="1"),
        rx.badge("Rascunho", color_scheme="amber", variant="outline", size="1"),
    )


def _ev_card(ev: Dict[str, str]) -> rx.Component:
    return rx.box(
        rx.image(
            src=ev["url"],
            width="100%",
            height="200px",
            object_fit="cover",
            border_radius="8px 8px 0 0",
            cursor="zoom-in",
            on_click=RDOViewState.open_lightbox(ev["url"]),
            style={"transition": "opacity 0.15s", "_hover": {"opacity": "0.88"}},
        ),
        rx.cond(
            ev["legenda"] != "",
            rx.box(
                rx.text(ev["legenda"], size="1", color=_MUTED),
                padding="6px 10px",
                background="rgba(0,0,0,0.3)",
                border_radius="0 0 8px 8px",
            ),
        ),
        border_radius="8px",
        border=f"1px solid {_BORDER}",
        overflow="hidden",
        style={
            "_hover": {"border_color": "rgba(201,139,42,0.4)"},
            "transition": "border-color 0.15s",
        },
    )


def _at_row(at: Dict[str, str]) -> rx.Component:
    status_color = rx.cond(
        at["status"] == "Concluído",
        "#2A9D8F",
        rx.cond(at["status"] == "Em andamento", _COPPER, _MUTED),
    )
    return rx.hstack(
        rx.box(
            width="8px", height="8px",
            border_radius="50%",
            background=status_color,
            flex_shrink="0",
            margin_top="6px",
        ),
        rx.vstack(
            rx.text(at["descricao"], size="2", color=_TEXT),
            rx.hstack(
                rx.text(at["status"], size="1", color=status_color),
                rx.cond(
                    at["percentual"] != "",
                    rx.text(f"· {at['percentual']}%", size="1", color=_MUTED),
                ),
                spacing="1",
            ),
            spacing="1",
            align="start",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def _lightbox() -> rx.Component:
    return rx.cond(
        RDOViewState.lightbox_url != "",
        rx.box(
            rx.box(
                rx.image(
                    src=RDOViewState.lightbox_url,
                    max_width="95vw",
                    max_height="90vh",
                    object_fit="contain",
                    border_radius="8px",
                    box_shadow="0 24px 64px rgba(0,0,0,0.9)",
                ),
                rx.button(
                    rx.icon("x", size=18),
                    on_click=RDOViewState.close_lightbox,
                    position="absolute",
                    top="12px",
                    right="12px",
                    style={
                        "background": "rgba(0,0,0,0.7)",
                        "border": "1px solid rgba(255,255,255,0.2)",
                        "color": "#fff",
                        "border_radius": "50%",
                        "width": "36px",
                        "height": "36px",
                        "cursor": "pointer",
                        "display": "flex",
                        "align_items": "center",
                        "justify_content": "center",
                    },
                ),
                rx.link(
                    rx.button(
                        rx.icon("download", size=14),
                        "Baixar",
                        size="1",
                        style={
                            "background": "rgba(201,139,42,0.8)",
                            "color": "#fff",
                            "border_radius": "6px",
                        },
                    ),
                    href=RDOViewState.lightbox_url,
                    is_external=True,
                    position="absolute",
                    bottom="12px",
                    right="12px",
                ),
                position="relative",
                display="inline-block",
            ),
            position="fixed",
            top="0", left="0", right="0", bottom="0",
            background="rgba(0,0,0,0.92)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="99999",
            on_click=RDOViewState.close_lightbox,
            style={"backdropFilter": "blur(6px)", "cursor": "zoom-out"},
        ),
    )


def _section(title: str, icon: str, children: list) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon(icon, size=15, color=_COPPER),
            rx.text(title, size="2", weight="bold", color=_COPPER,
                    letter_spacing="0.05em", text_transform="uppercase"),
            spacing="2", align="center", margin_bottom="12px",
        ),
        *children,
        padding="18px 20px",
        background=_CARD,
        border=f"1px solid {_BORDER}",
        border_radius="10px",
        width="100%",
    )


def rdo_view_page() -> rx.Component:
    return rx.box(
        _lightbox(),
        # Top bar
        rx.hstack(
            rx.hstack(
                rx.text("BOMTEMPO", weight="bold", size="4", color="#fff"),
                rx.text("·", color=_MUTED),
                rx.text("RDO Online", size="2", color=_MUTED),
                spacing="2", align="center",
            ),
            rx.spacer(),
            rx.cond(
                RDOViewState.pdf_url != "",
                rx.link(
                    rx.button(
                        rx.icon("download", size=14),
                        "Baixar PDF",
                        size="2",
                        style={
                            "background": f"linear-gradient(135deg,{_COPPER},#9B6820)",
                            "color": "#fff",
                            "border_radius": "6px",
                            "font_weight": "600",
                        },
                    ),
                    href=RDOViewState.pdf_url,
                    is_external=True,
                ),
            ),
            padding="12px 20px",
            background="rgba(11,26,21,0.96)",
            border_bottom=f"1px solid {_BORDER}",
            style={"backdropFilter": "blur(12px)"},
            position="sticky",
            top="0",
            z_index="50",
            width="100%",
        ),
        # Content
        rx.cond(
            RDOViewState.is_loading,
            rx.center(
                rx.vstack(
                    rx.spinner(size="3", color=_COPPER),
                    rx.text("Carregando relatório…", size="3", color=_MUTED),
                    spacing="3", align="center",
                ),
                min_height="60vh",
            ),
            rx.cond(
                RDOViewState.not_found,
                rx.center(
                    rx.vstack(
                        rx.icon("file-x", size=48, color=_MUTED),
                        rx.text("Relatório não encontrado", size="5", weight="bold", color=_TEXT),
                        rx.text("O link pode ter expirado ou o RDO não existe.", size="2", color=_MUTED),
                        rx.link(
                            rx.button("Ir para o Dashboard", size="2",
                                      style={"background": f"linear-gradient(135deg,{_COPPER},#9B6820)",
                                             "color": "#fff", "border_radius": "6px"}),
                            href="/",
                        ),
                        spacing="3", align="center",
                    ),
                    min_height="60vh",
                ),
                # Main interactive content
                rx.vstack(
                    # Header card
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.vstack(
                                    rx.text(RDOViewState.rdo_contrato, size="5", weight="bold", color=_COPPER),
                                    rx.text(RDOViewState.rdo_projeto, size="2", color=_MUTED),
                                    spacing="0", align="start",
                                ),
                                rx.spacer(),
                                rx.vstack(
                                    _badge_status(),
                                    rx.text(RDOViewState.rdo_data, size="2", color=_TEXT),
                                    spacing="1", align="end",
                                ),
                                align="start", width="100%",
                            ),
                            rx.divider(color_scheme="gray", opacity="0.2"),
                            rx.hstack(
                                _info_row("Cliente", RDOViewState.rdo_cliente),
                                _info_row("Mestre", RDOViewState.rdo_mestre),
                                flex_wrap="wrap",
                                gap="8px",
                                width="100%",
                            ),
                            rx.hstack(
                                _info_row("Clima", RDOViewState.rdo_clima),
                                _info_row("Turno", RDOViewState.rdo_turno),
                                flex_wrap="wrap",
                                gap="8px",
                                width="100%",
                            ),
                            spacing="3",
                        ),
                        padding="20px",
                        background=_CARD,
                        border=f"2px solid rgba(201,139,42,0.3)",
                        border_radius="12px",
                        width="100%",
                    ),

                    # GPS Check-in / Check-out
                    rx.cond(
                        RDOViewState.rdo_checkin_endereco != "",
                        _section("GPS", "map-pin", [
                            rx.hstack(
                                rx.vstack(
                                    rx.text("Check-in", size="1", color=_MUTED, weight="bold"),
                                    rx.text(RDOViewState.rdo_checkin_endereco, size="2", color=_TEXT),
                                    rx.text(RDOViewState.rdo_checkin_timestamp, size="1", color=_MUTED),
                                    spacing="1", align="start",
                                ),
                                rx.cond(
                                    RDOViewState.rdo_checkout_endereco != "",
                                    rx.vstack(
                                        rx.text("Check-out", size="1", color=_MUTED, weight="bold"),
                                        rx.text(RDOViewState.rdo_checkout_endereco, size="2", color=_TEXT),
                                        rx.text(RDOViewState.rdo_checkout_timestamp, size="1", color=_MUTED),
                                        spacing="1", align="start",
                                    ),
                                ),
                                spacing="6", flex_wrap="wrap", width="100%",
                            ),
                        ]),
                    ),

                    # Atividades
                    rx.cond(
                        RDOViewState.atividades.length() > 0,
                        _section("Atividades", "clipboard-list", [
                            rx.vstack(
                                rx.foreach(RDOViewState.atividades, _at_row),
                                spacing="3", width="100%",
                            ),
                        ]),
                    ),

                    # Observações
                    rx.cond(
                        RDOViewState.rdo_observacoes != "",
                        _section("Observações", "message-square", [
                            rx.text(RDOViewState.rdo_observacoes, size="2", color=_TEXT,
                                    line_height="1.7", white_space="pre-wrap"),
                        ]),
                    ),

                    # Orientações
                    rx.cond(
                        RDOViewState.rdo_orientacao != "",
                        _section("Orientações", "lightbulb", [
                            rx.text(RDOViewState.rdo_orientacao, size="2", color=_TEXT,
                                    line_height="1.7", white_space="pre-wrap"),
                        ]),
                    ),

                    # Evidências — gallery with click-to-zoom
                    rx.cond(
                        RDOViewState.evidencias.length() > 0,
                        rx.box(
                            rx.hstack(
                                rx.icon("camera", size=15, color=_COPPER),
                                rx.text("Evidências Fotográficas", size="2", weight="bold", color=_COPPER,
                                        letter_spacing="0.05em", text_transform="uppercase"),
                                rx.text("(toque para ampliar)", size="1", color=_MUTED),
                                spacing="2", align="center", margin_bottom="12px",
                            ),
                            rx.grid(
                                rx.foreach(RDOViewState.evidencias, _ev_card),
                                columns=rx.breakpoints(initial="2", md="3"),
                                gap="10px",
                                width="100%",
                            ),
                            padding="18px 20px",
                            background=_CARD,
                            border=f"1px solid {_BORDER}",
                            border_radius="10px",
                            width="100%",
                        ),
                    ),

                    # AI Analysis
                    rx.cond(
                        RDOViewState.ai_summary != "",
                        rx.box(
                            rx.hstack(
                                rx.icon("bot", size=16, color=_PATINA),
                                rx.text("Análise BTP Intelligence", size="2", weight="bold", color=_PATINA),
                                spacing="2", align="center", margin_bottom="12px",
                            ),
                            rx.box(
                                rx.markdown(RDOViewState.ai_summary),
                                style={"color": _TEXT, "font_size": "14px", "line_height": "1.7"},
                            ),
                            padding="18px 20px",
                            background="rgba(42,157,143,0.06)",
                            border=f"1px solid rgba(42,157,143,0.25)",
                            border_left=f"3px solid {_PATINA}",
                            border_radius="10px",
                            width="100%",
                        ),
                    ),

                    # Footer
                    rx.center(
                        rx.text("Gerado por BTP Intelligence · Bomtempo Engenharia",
                                size="1", color=_MUTED),
                        padding_y="24px",
                    ),
                    spacing="4",
                    width="100%",
                    padding=["16px", "24px 28px"],
                    max_width="900px",
                    margin="0 auto",
                ),
            ),
        ),
        min_height="100vh",
        background=_BG,
    )
