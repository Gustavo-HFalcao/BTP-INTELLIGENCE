"""
RDO Public View — Visualização pública do RDO (sem login).
Rota: /rdo-view/[token]

Acessível via link enviado por e-mail.
Mostra HTML renderizado + botões Imprimir / Baixar PDF.
"""

import asyncio
from typing import Any, Dict

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


# ── State ────────────────────────────────────────────────────────────────────

class RDOViewState(rx.State):
    rdo_html: str = ""
    rdo_id: str = ""
    rdo_contrato: str = ""
    rdo_data: str = ""
    rdo_status: str = ""
    pdf_url: str = ""
    ai_summary: str = ""
    is_loading: bool = True
    not_found: bool = False
    # Nota: 'token' é injetado automaticamente pelo roteador Reflex via dynamic route [token]
    # Não declarar aqui para não conflitar.

    @rx.event(background=True)
    async def load_rdo(self):
        """Chamado no on_load — self.token já está populado pelo roteador Reflex."""
        async with self:
            self.is_loading = True
            self.not_found = False
            # rx injeta o param da URL como atributo do State
            token = str(getattr(self, "token", ""))

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

        # Build HTML for iframe rendering
        html = await loop.run_in_executor(
            None,
            lambda: RDOService.build_html(data, is_preview=False),
        )

        async with self:
            self.rdo_html     = html
            self.rdo_id       = data.get("id_rdo", "")
            self.rdo_contrato = data.get("contrato", "")
            self.rdo_data     = str(data.get("data", ""))
            self.rdo_status   = data.get("status", "")
            self.pdf_url      = data.get("pdf_url", "")
            self.ai_summary   = data.get("ai_summary", "")
            self.is_loading   = False


# ── Components ───────────────────────────────────────────────────────────────

def _print_script() -> rx.Component:
    """Botão imprimir via JS."""
    return rx.button(
        rx.icon("printer", size=15),
        "Imprimir",
        on_click=rx.call_script("window.frames['rdo-frame'].contentWindow.print()"),
        size="2",
        style={
            "background": "rgba(255,255,255,0.06)",
            "border": f"1px solid {_BORDER}",
            "color": _TEXT,
            "border_radius": "6px",
            "cursor": "pointer",
        },
    )


def _ai_panel() -> rx.Component:
    return rx.cond(
        RDOViewState.ai_summary != "",
        rx.box(
            rx.hstack(
                rx.icon("bot", size=18, color=_PATINA),
                rx.text("Análise BTP Intelligence", size="3", weight="bold", color=_PATINA),
                spacing="2",
                align="center",
                margin_bottom="12px",
            ),
            rx.box(
                rx.markdown(RDOViewState.ai_summary),
                style={
                    "color": _TEXT,
                    "font_size": "14px",
                    "line_height": "1.7",
                },
            ),
            padding="20px 24px",
            background=_CARD,
            border=f"1px solid rgba(42,157,143,0.3)",
            border_left=f"3px solid {_PATINA}",
            border_radius="10px",
            margin_top="20px",
        ),
    )


# ── Page ─────────────────────────────────────────────────────────────────────

def rdo_view_page() -> rx.Component:
    return rx.box(
        # Top bar
        rx.hstack(
            rx.hstack(
                rx.box(
                    rx.text("BOMTEMPO", weight="bold", size="4", color="#fff"),
                    rx.text("ENGENHARIA", weight="bold", size="4", color=_COPPER),
                    display="flex",
                    gap="4px",
                    align_items="baseline",
                ),
                rx.text("·", color=_MUTED),
                rx.text("Relatório Diário de Obra", size="2", color=_MUTED),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.cond(
                    RDOViewState.pdf_url != "",
                    rx.link(
                        rx.button(
                            rx.icon("download", size=15),
                            "Baixar PDF",
                            size="2",
                            style={
                                "background": "linear-gradient(135deg,#C98B2A,#9B6820)",
                                "color": "#fff",
                                "border_radius": "6px",
                                "font_weight": "600",
                            },
                        ),
                        href=RDOViewState.pdf_url,
                        is_external=True,
                    ),
                ),
                _print_script(),
                rx.link(
                    rx.button(
                        rx.icon("layout-dashboard", size=14),
                        "Dashboard",
                        size="2",
                        variant="ghost",
                        color=_MUTED,
                    ),
                    href="/",
                ),
                spacing="2",
                align="center",
            ),
            padding="12px 28px",
            background=f"rgba(11,26,21,0.96)",
            border_bottom=f"1px solid {_BORDER}",
            style={"backdrop_filter": "blur(12px)"},
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
                    spacing="3",
                    align="center",
                ),
                min_height="60vh",
            ),
            rx.cond(
                RDOViewState.not_found,
                rx.center(
                    rx.vstack(
                        rx.icon("file-x", size=48, color=_MUTED),
                        rx.text("Relatório não encontrado", size="5", weight="bold", color=_TEXT),
                        rx.text(
                            "O link pode ter expirado ou o RDO não existe.",
                            size="2",
                            color=_MUTED,
                        ),
                        rx.link(
                            rx.button("Ir para o Dashboard", size="2",
                                      style={"background": "linear-gradient(135deg,#C98B2A,#9B6820)",
                                             "color": "#fff", "border_radius": "6px"}),
                            href="/",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    min_height="60vh",
                ),
                # Main: RDO HTML in iframe + AI panel
                rx.vstack(
                    # Meta bar
                    rx.hstack(
                        rx.hstack(
                            rx.badge(RDOViewState.rdo_contrato, color_scheme="amber", variant="soft", size="2"),
                            rx.badge(RDOViewState.rdo_data, color_scheme="gray", variant="surface", size="1"),
                            rx.cond(
                                RDOViewState.rdo_status == "finalizado",
                                rx.badge("Finalizado", color_scheme="teal", variant="soft", size="1"),
                                rx.badge("Rascunho", color_scheme="amber", variant="outline", size="1"),
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.spacer(),
                        rx.text(RDOViewState.rdo_id, size="1", color=_MUTED,
                                style={"font_family": "monospace"}),
                        align="center",
                        width="100%",
                        padding="12px 0",
                    ),
                    # HTML iframe (render the PDF-quality HTML)
                    rx.el.iframe(
                        src_doc=RDOViewState.rdo_html,
                        name="rdo-frame",
                        width="100%",
                        height="900px",
                        style={
                            "border": f"1px solid {_BORDER}",
                            "border_radius": "10px",
                            "background": "#fff",
                        },
                    ),
                    # AI Panel
                    _ai_panel(),
                    # Footer note
                    rx.center(
                        rx.text(
                            "Gerado por BTP Intelligence · Bomtempo Engenharia",
                            size="1",
                            color=_MUTED,
                        ),
                        padding_y="20px",
                    ),
                    spacing="0",
                    width="100%",
                    padding="24px 28px",
                    max_width="1100px",
                    margin="0 auto",
                ),
            ),
        ),
        min_height="100vh",
        background=_BG,
    )
