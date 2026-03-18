"""
Relatórios Page — Bomtempo Intelligence
Feature 3: Módulo de Relatórios IA (implementation-core.md)

Two sub-modules:
  1. Dossier Estático — structured HTML report with real data → preview + PDF download
  2. Análise IA — streaming generative analysis in 4 approaches (Estratégica/Analítica/Descritiva/Operacional)
  + Custom chatbox for natural-language report requests
"""

import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState
from bomtempo.state.relatorios_state import RelatoriosState


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

def _page_header() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text(
                    "CENTRAL DE RELATÓRIOS",
                    font_family=S.FONT_TECH,
                    font_size="1.6rem",
                    font_weight="700",
                    letter_spacing="0.1em",
                    color="white",
                    line_height="1",
                ),
                rx.text(
                    "Geração automática e análise inteligente — dados reais, exportação PDF",
                    font_size="0.85rem",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_BODY,
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.icon("file-text", size=16, color=S.COPPER),
                rx.text(
                    RelatoriosState.reports_history.length().to_string() + " relatórios gerados",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_MONO,
                ),
                spacing="2",
                align="center",
                padding="8px 16px",
                border=f"1px solid {S.BORDER_SUBTLE}",
                border_radius="8px",
                bg=S.BG_INPUT,
            ),
            width="100%",
            align="center",
        ),
        # Contrato Selector — always visible at top
        rx.box(
            rx.hstack(
                rx.icon("building-2", size=16, color=S.COPPER),
                rx.text(
                    "CONTRATO",
                    font_size="11px",
                    font_weight="700",
                    letter_spacing="0.12em",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_TECH,
                ),
                spacing="2",
                align="center",
                margin_bottom="8px",
            ),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Selecionar contrato para gerar relatório...",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        GlobalState.contratos_list,
                        lambda c: rx.select.item(
                            c["contrato"],
                            value=c["contrato"],
                        ),
                    ),
                    bg=S.BG_ELEVATED,
                    border=f"1px solid {S.BORDER_SUBTLE}",
                ),
                value=RelatoriosState.selected_contrato,
                on_change=[
                    RelatoriosState.set_selected_contrato,
                    GlobalState.set_obras_selected_contract,
                ],
                width="100%",
            ),
            width="100%",
            **{**S.GLASS_CARD, "padding": "16px 20px"},
        ),
        width="100%",
        spacing="4",
    )


# ─────────────────────────────────────────────────────────────────────────────
# MODULE CARDS: Static + AI side by side
# ─────────────────────────────────────────────────────────────────────────────

def _static_module_card() -> rx.Component:
    return rx.vstack(
        # Header
        rx.hstack(
            rx.center(
                rx.icon("file-text", size=20, color=S.COPPER),
                bg=S.COPPER_GLOW,
                border_radius="10px",
                padding="10px",
                border=f"1px solid {S.BORDER_ACCENT}",
            ),
            rx.vstack(
                rx.text(
                    "DOSSIER ESTÁTICO",
                    font_family=S.FONT_TECH,
                    font_size="1rem",
                    font_weight="700",
                    letter_spacing="0.08em",
                    color="white",
                ),
                rx.text(
                    "Layout estruturado com dados reais da obra",
                    font_size="11px",
                    color=S.TEXT_MUTED,
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
            width="100%",
            margin_bottom="4px",
        ),
        rx.divider(color_scheme="gray", opacity="0.2"),
        # Description
        rx.text(
            "Gera um relatório executivo completo com KPIs financeiros, progresso por disciplina, "
            "equipe de campo e cronograma — formatado profissionalmente para impressão ou PDF.",
            font_size="12px",
            color=S.TEXT_MUTED,
            line_height="1.6",
        ),
        # Features list
        rx.vstack(
            _feature_bullet("Capa com identidade visual corporativa"),
            _feature_bullet("5 seções: Resumo, Disciplinas, Orçamento, Equipe, Cronograma"),
            _feature_bullet("Exportável como PDF de alta qualidade"),
            _feature_bullet("Salvo no histórico para re-download"),
            spacing="1",
            width="100%",
            margin_y="8px",
        ),
        rx.spacer(),
        # Generate button
        rx.button(
            rx.cond(
                RelatoriosState.is_generating_static,
                rx.hstack(
                    rx.spinner(size="1", color="white"),
                    rx.text("Gerando dossier...", font_size="13px"),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.icon("file-down", size=16),
                    rx.text("Gerar Dossier", font_size="13px"),
                    spacing="2",
                    align="center",
                ),
            ),
            on_click=RelatoriosState.generate_static_report,
            disabled=RelatoriosState.is_generating_static,
            width="100%",
            bg=S.COPPER,
            color="white",
            border_radius="10px",
            padding_y="12px",
            font_family=S.FONT_TECH,
            font_weight="700",
            letter_spacing="0.05em",
            _hover={"opacity": "0.85", "transform": "translateY(-1px)"},
            transition="all 0.15s ease",
        ),
        spacing="3",
        align="start",
        width="100%",
        **{**S.GLASS_CARD, "padding": "20px", "border_top": f"2px solid {S.COPPER}"},
        flex="1 1 280px",
        min_width="280px",
    )


def _ai_module_card() -> rx.Component:
    abordagem_options = [
        ("estrategica", "Estratégica", "Para diretoria e investidores"),
        ("analitica", "Analítica", "Análise financeira detalhada"),
        ("descritiva", "Descritiva", "Auditoria técnica formal"),
        ("operacional", "Operacional", "Foco em campo e disciplinas"),
    ]
    return rx.vstack(
        # Header
        rx.hstack(
            rx.center(
                rx.icon("sparkles", size=20, color=S.PATINA),
                bg=S.PATINA_GLOW,
                border_radius="10px",
                padding="10px",
                border=f"1px solid rgba(42, 157, 143, 0.3)",
            ),
            rx.vstack(
                rx.text(
                    "ANÁLISE IA GENERATIVA",
                    font_family=S.FONT_TECH,
                    font_size="1rem",
                    font_weight="700",
                    letter_spacing="0.08em",
                    color="white",
                ),
                rx.text(
                    "Insights profundos com 4 abordagens especializadas",
                    font_size="11px",
                    color=S.TEXT_MUTED,
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
            width="100%",
            margin_bottom="4px",
        ),
        rx.divider(color_scheme="gray", opacity="0.2"),
        # Abordagem selector
        rx.vstack(
            rx.text(
                "ABORDAGEM",
                font_size="10px",
                font_weight="700",
                letter_spacing="0.12em",
                color=S.TEXT_MUTED,
                font_family=S.FONT_TECH,
            ),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Selecionar abordagem...",
                    width="100%",
                ),
                rx.select.content(
                    *[
                        rx.select.item(
                            rx.hstack(
                                rx.text(label, font_weight="600", font_size="13px"),
                                rx.text(" — " + desc, font_size="11px", color=S.TEXT_MUTED),
                                spacing="0",
                            ),
                            value=val,
                        )
                        for val, label, desc in abordagem_options
                    ],
                    bg=S.BG_ELEVATED,
                    border=f"1px solid {S.BORDER_SUBTLE}",
                ),
                value=RelatoriosState.selected_abordagem,
                on_change=RelatoriosState.set_selected_abordagem,
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        # Approach description
        rx.box(
            rx.cond(
                RelatoriosState.selected_abordagem == "estrategica",
                rx.text(
                    "Tom assertivo orientado a decisão. Riscos estratégicos, oportunidades e recomendações de ação imediata para diretoria.",
                    font_size="11px", color=S.TEXT_MUTED, line_height="1.5",
                ),
                rx.cond(
                    RelatoriosState.selected_abordagem == "analitica",
                    rx.text(
                        "Análise quantitativa detalhada. Variações orçamentárias, eficiência de execução, desvios e projeções com números precisos.",
                        font_size="11px", color=S.TEXT_MUTED, line_height="1.5",
                    ),
                    rx.cond(
                        RelatoriosState.selected_abordagem == "descritiva",
                        rx.text(
                            "Relatório formal de auditoria. Todos os dados citados explicitamente com conformidade e pendências identificadas.",
                            font_size="11px", color=S.TEXT_MUTED, line_height="1.5",
                        ),
                        rx.text(
                            "Foco em campo e coordenação técnica. Disciplinas atrasadas, efetivo, ações práticas e próximos passos no canteiro.",
                            font_size="11px", color=S.TEXT_MUTED, line_height="1.5",
                        ),
                    ),
                ),
            ),
            padding="10px 12px",
            bg=S.PATINA_GLOW,
            border_radius="8px",
            border=f"1px solid rgba(42, 157, 143, 0.2)",
        ),
        rx.spacer(),
        # Generate button
        rx.button(
            rx.cond(
                RelatoriosState.is_generating_ai,
                rx.hstack(
                    rx.spinner(size="1", color="white"),
                    rx.text("Gerando análise...", font_size="13px"),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.icon("sparkles", size=16),
                    rx.text("Gerar com IA", font_size="13px"),
                    spacing="2",
                    align="center",
                ),
            ),
            on_click=RelatoriosState.generate_ai_report,
            disabled=RelatoriosState.is_generating_ai,
            width="100%",
            bg=S.PATINA,
            color="white",
            border_radius="10px",
            padding_y="12px",
            font_family=S.FONT_TECH,
            font_weight="700",
            letter_spacing="0.05em",
            _hover={"opacity": "0.85", "transform": "translateY(-1px)"},
            transition="all 0.15s ease",
        ),
        spacing="3",
        align="start",
        width="100%",
        **{**S.GLASS_CARD, "padding": "20px", "border_top": f"2px solid {S.PATINA}"},
        flex="1 1 280px",
        min_width="280px",
    )


def _feature_bullet(text: str) -> rx.Component:
    return rx.hstack(
        rx.icon("check", size=12, color=S.PATINA),
        rx.text(text, font_size="11px", color=S.TEXT_MUTED),
        spacing="2",
        align="center",
    )


# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW / RESULT PANEL
# ─────────────────────────────────────────────────────────────────────────────

def _preview_panel() -> rx.Component:
    """Shows static HTML preview OR AI markdown result, depending on what's available."""
    return rx.cond(
        (RelatoriosState.report_html_preview != "") | (RelatoriosState.ai_report_text != ""),
        rx.vstack(
            # Section header
            rx.hstack(
                rx.icon("eye", size=16, color=S.COPPER),
                rx.text(
                    "PRÉVIA / RESULTADO",
                    font_family=S.FONT_TECH,
                    font_size="0.85rem",
                    font_weight="700",
                    letter_spacing="0.12em",
                    color=S.TEXT_MUTED,
                ),
                rx.spacer(),
                # Action buttons — only shown when content exists
                rx.cond(
                    RelatoriosState.report_pdf_url != "",
                    rx.button(
                        rx.hstack(
                            rx.icon("download", size=14),
                            rx.text("Download PDF", font_size="12px"),
                            spacing="2",
                            align="center",
                        ),
                        on_click=RelatoriosState.open_pdf_url(RelatoriosState.report_pdf_url),
                        size="2",
                        bg=S.COPPER,
                        color="white",
                        border_radius="8px",
                        cursor="pointer",
                        _hover={"opacity": "0.85"},
                    ),
                ),
                rx.cond(
                    RelatoriosState.ai_report_text != "",
                    rx.button(
                        rx.hstack(
                            rx.icon("copy", size=14),
                            rx.text("Copiar", font_size="12px"),
                            spacing="2",
                            align="center",
                        ),
                        size="2",
                        variant="ghost",
                        color=S.PATINA,
                        border=f"1px solid rgba(42, 157, 143, 0.4)",
                        border_radius="8px",
                        on_click=RelatoriosState.copy_ai_text,
                        _hover={"bg": S.PATINA_GLOW},
                    ),
                ),
                rx.cond(
                    RelatoriosState.report_html_preview != "",
                    rx.button(
                        rx.icon("x", size=14),
                        size="2",
                        variant="ghost",
                        color=S.TEXT_MUTED,
                        border_radius="8px",
                        on_click=RelatoriosState.clear_static_preview,
                        _hover={"color": "white"},
                    ),
                ),
                rx.cond(
                    RelatoriosState.ai_report_text != "",
                    rx.button(
                        rx.icon("x", size=14),
                        size="2",
                        variant="ghost",
                        color=S.TEXT_MUTED,
                        border_radius="8px",
                        on_click=RelatoriosState.clear_ai_text,
                        _hover={"color": "white"},
                    ),
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            # Content area
            rx.cond(
                RelatoriosState.report_html_preview != "",
                # Static HTML preview — scroll horizontal on mobile (A4 layout)
                rx.box(
                    rx.box(
                        rx.html(RelatoriosState.report_html_preview),
                        min_width="800px",
                    ),
                    width="100%",
                    max_height="600px",
                    overflow_x="auto",
                    overflow_y="auto",
                    border_radius="12px",
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    bg="white",
                ),
                # AI Markdown: parchment card with proper report formatting
                rx.box(
                    rx.markdown(
                        RelatoriosState.ai_report_text,
                        component_map={
                            # Document title — full-width copper header with bottom rule
                            "h1": lambda text: rx.box(
                                rx.text(
                                    text,
                                    font_size="1.45rem", font_weight="900",
                                    color="#C98B2A", font_family="Rajdhani, sans-serif",
                                    letter_spacing="0.06em", line_height="1.2",
                                ),
                                padding_bottom="10px",
                                border_bottom="2px solid rgba(201,139,42,0.45)",
                                margin_bottom="18px",
                                width="100%",
                            ),
                            # Section header — copper left-bar accent block
                            "h2": lambda text: rx.box(
                                rx.text(
                                    text,
                                    font_size="0.95rem", font_weight="700",
                                    color="#1A1A2E", font_family="Rajdhani, sans-serif",
                                    letter_spacing="0.1em", text_transform="uppercase",
                                ),
                                padding="7px 14px",
                                bg="rgba(201,139,42,0.07)",
                                border_left="3px solid #C98B2A",
                                border_radius="0 6px 6px 0",
                                margin_top="22px",
                                margin_bottom="10px",
                                width="100%",
                            ),
                            # Sub-section header — teal
                            "h3": lambda text: rx.box(
                                rx.text(
                                    text,
                                    font_size="0.9rem", font_weight="700",
                                    color="#2A9D8F",
                                ),
                                margin_top="14px",
                                margin_bottom="6px",
                                width="100%",
                            ),
                            # Body text
                            "p": lambda text: rx.text(
                                text,
                                font_size="0.875rem", color="#374151",
                                line_height="1.75", margin_bottom="10px",
                            ),
                            # Bottom Line callout (blockquote > ...) — gold accent box
                            "blockquote": lambda text: rx.box(
                                rx.hstack(
                                    rx.box(
                                        width="3px", min_height="100%",
                                        bg="#C98B2A", border_radius="2px", flex_shrink="0",
                                    ),
                                    rx.text(
                                        text,
                                        font_size="0.9rem", font_weight="600",
                                        color="#1A1A2E", line_height="1.6",
                                        font_style="italic",
                                    ),
                                    spacing="3",
                                    align="stretch",
                                    width="100%",
                                ),
                                padding="10px 16px",
                                bg="rgba(201,139,42,0.08)",
                                border_radius="0 8px 8px 0",
                                margin_y="14px",
                                width="100%",
                            ),
                            # Inline code
                            "code": lambda text: rx.el.code(
                                text,
                                style={
                                    "fontFamily": "JetBrains Mono, monospace",
                                    "fontSize": "0.8rem",
                                    "color": "#2A9D8F",
                                    "background": "rgba(42,157,143,0.08)",
                                    "padding": "1px 6px",
                                    "borderRadius": "4px",
                                },
                            ),
                        },
                    ),
                    width="100%",
                    max_height="620px",
                    overflow_y="auto",
                    padding="28px 36px",
                    bg="linear-gradient(135deg, #FFFEF5 0%, #FFF8E7 50%, #FFFEF5 100%)",
                    border_radius="12px",
                    border="1px solid rgba(201,139,42,0.25)",
                    box_shadow="inset 0 0 40px rgba(201,139,42,0.04), 0 4px 20px rgba(0,0,0,0.15)",
                ),
            ),
            spacing="4",
            width="100%",
            **{**S.GLASS_CARD, "padding": "20px"},
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ERROR BANNER
# ─────────────────────────────────────────────────────────────────────────────

def _error_banner() -> rx.Component:
    return rx.cond(
        RelatoriosState.error_msg != "",
        rx.hstack(
            rx.icon("triangle-alert", size=16, color=S.DANGER),
            rx.text(
                RelatoriosState.error_msg,
                font_size="13px",
                color=S.DANGER,
            ),
            rx.spacer(),
            rx.button(
                rx.icon("x", size=14),
                variant="ghost",
                color=S.TEXT_MUTED,
                size="1",
                on_click=RelatoriosState.clear_ai_text,
            ),
            spacing="3",
            align="center",
            width="100%",
            padding="12px 16px",
            bg=S.DANGER_BG,
            border=f"1px solid rgba(239, 68, 68, 0.3)",
            border_radius="10px",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _history_row(row: dict) -> rx.Component:
    tipo_label = rx.cond(
        row["tipo"] == "ia",
        "IA",
        rx.cond(row["tipo"] == "custom", "Custom", "Estático"),
    )
    return rx.table.row(
        rx.table.cell(
            rx.text(
                row["created_at"],
                font_size="11px",
                color=S.TEXT_MUTED,
                font_family=S.FONT_MONO,
            ),
        ),
        rx.table.cell(
            rx.text(row["contrato"], font_size="12px", color="white", font_weight="500"),
        ),
        rx.table.cell(
            rx.text(row["cliente"], font_size="12px", color=S.TEXT_MUTED),
        ),
        rx.table.cell(
            rx.badge(
                tipo_label,
                color_scheme=rx.cond(
                    row["tipo"] == "ia", "teal",
                    rx.cond(row["tipo"] == "custom", "amber", "orange"),
                ),
                variant="soft",
                size="1",
            ),
        ),
        rx.table.cell(
            rx.text(row["abordagem"], font_size="11px", color=S.TEXT_MUTED),
        ),
        rx.table.cell(
            rx.text(row["created_by"], font_size="11px", color=S.TEXT_MUTED),
        ),
        rx.table.cell(
            rx.cond(
                row["pdf_url"] != "",
                rx.button(
                    rx.icon("download", size=12),
                    on_click=RelatoriosState.open_pdf_url(row["pdf_url"]),
                    size="1",
                    variant="ghost",
                    color=S.COPPER,
                    border=f"1px solid {S.BORDER_ACCENT}",
                    border_radius="6px",
                    cursor="pointer",
                    _hover={"bg": S.COPPER_GLOW},
                ),
                rx.text("—", font_size="11px", color=S.TEXT_MUTED),
            ),
        ),
    )


def _history_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("history", size=16, color=S.COPPER),
            rx.text(
                "HISTÓRICO DE RELATÓRIOS",
                font_family=S.FONT_TECH,
                font_size="0.85rem",
                font_weight="700",
                letter_spacing="0.12em",
                color=S.TEXT_MUTED,
            ),
            rx.spacer(),
            rx.cond(
                RelatoriosState.is_loading_history,
                rx.spinner(size="1", color=S.COPPER),
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.cond(
            RelatoriosState.reports_history.length() == 0,
            rx.center(
                rx.vstack(
                    rx.icon("file-x", size=32, color=S.TEXT_MUTED),
                    rx.text(
                        "Nenhum relatório gerado ainda",
                        font_size="13px",
                        color=S.TEXT_MUTED,
                    ),
                    spacing="2",
                    align="center",
                ),
                padding_y="32px",
                width="100%",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            "DATA",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                        rx.table.column_header_cell(
                            "CONTRATO",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                        rx.table.column_header_cell(
                            "CLIENTE",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                        rx.table.column_header_cell(
                            "TIPO",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                        rx.table.column_header_cell(
                            "ABORDAGEM",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                        rx.table.column_header_cell(
                            "GERADO POR",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                        rx.table.column_header_cell(
                            "PDF",
                            style={"fontSize": "10px", "color": S.TEXT_MUTED,
                                   "letterSpacing": "0.1em", "fontFamily": S.FONT_TECH,
                                   "background": S.BG_SURFACE},
                        ),
                    ),
                ),
                rx.table.body(
                    rx.foreach(RelatoriosState.reports_history, _history_row),
                ),
                width="100%",
                variant="ghost",
                size="1",
                style={"background": "transparent"},
            ),
        ),
        spacing="4",
        width="100%",
        **{**S.GLASS_CARD, "padding": "20px"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CHATBOX (Wow Factor)
# ─────────────────────────────────────────────────────────────────────────────

def _custom_chatbox() -> rx.Component:
    return rx.vstack(
        # Header with gradient accent
        rx.hstack(
            rx.hstack(
                rx.icon("wand-sparkles", size=18, color=S.COPPER),
                rx.text(
                    "RELATÓRIO CUSTOMIZADO",
                    font_family=S.FONT_TECH,
                    font_size="0.95rem",
                    font_weight="700",
                    letter_spacing="0.1em",
                    color="white",
                ),
                spacing="3",
                align="center",
            ),
            rx.spacer(),
            rx.badge(
                "IA GENERATIVA",
                color_scheme="amber",
                variant="soft",
                size="1",
                font_family=S.FONT_TECH,
                letter_spacing="0.05em",
            ),
            width="100%",
            align="center",
        ),
        rx.text(
            "Descreva em linguagem natural o relatório que precisa. "
            "A IA usará os dados reais do contrato selecionado para gerar um relatório personalizado.",
            font_size="12px",
            color=S.TEXT_MUTED,
            line_height="1.6",
        ),
        # Input area
        rx.hstack(
            rx.text_area(
                value=RelatoriosState.custom_prompt,
                on_change=RelatoriosState.set_custom_prompt,
                placeholder='Ex: "Relatório focado nos riscos financeiros para apresentar ao banco financiador, com ênfase nas variações orçamentárias e projeções de término..."',
                width="100%",
                min_height="80px",
                bg=S.BG_INPUT,
                border=f"1px solid {S.BORDER_SUBTLE}",
                color="white",
                font_size="13px",
                font_family=S.FONT_BODY,
                border_radius="10px",
                _focus={
                    "border_color": S.COPPER,
                    "outline": "none",
                    "box_shadow": f"0 0 0 2px {S.COPPER_GLOW}",
                },
                _placeholder={"color": S.TEXT_MUTED},
                resize="vertical",
            ),
            rx.button(
                rx.cond(
                    RelatoriosState.is_generating_custom,
                    rx.vstack(
                        rx.spinner(size="2", color="white"),
                        rx.text("IA", font_size="9px", color="white"),
                        spacing="1",
                        align="center",
                    ),
                    rx.vstack(
                        rx.icon("send", size=16, color="white"),
                        rx.text("Enviar", font_size="9px", color="white"),
                        spacing="1",
                        align="center",
                    ),
                ),
                on_click=RelatoriosState.generate_custom_report,
                disabled=RelatoriosState.is_generating_custom,
                bg=S.COPPER,
                border_radius="10px",
                width="64px",
                height="80px",
                flex_shrink="0",
                _hover={"opacity": "0.85"},
                transition="all 0.15s ease",
            ),
            spacing="3",
            width="100%",
            align="end",
        ),
        # Loading state
        rx.cond(
            RelatoriosState.is_generating_custom,
            rx.hstack(
                rx.spinner(size="1", color=S.COPPER),
                rx.text(
                    "IA processando seu pedido e gerando relatório personalizado...",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_style="italic",
                ),
                spacing="2",
                align="center",
            ),
        ),
        spacing="4",
        width="100%",
        padding="20px",
        bg=f"linear-gradient(135deg, {S.BG_ELEVATED} 0%, rgba(201, 139, 42, 0.05) 100%)",
        border=f"1px solid {S.BORDER_ACCENT}",
        border_radius="16px",
        box_shadow=f"0 0 30px rgba(201, 139, 42, 0.08)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# STREAMING INDICATOR (shown during any AI generation)
# ─────────────────────────────────────────────────────────────────────────────

def _streaming_banner() -> rx.Component:
    return rx.cond(
        RelatoriosState.is_streaming,
        rx.hstack(
            rx.spinner(size="1", color=S.PATINA),
            rx.text(
                "IA gerando relatório em tempo real",
                font_size="12px",
                color=S.PATINA,
                font_style="italic",
            ),
            rx.spacer(),
            rx.box(
                width="6px",
                height="6px",
                border_radius="50%",
                bg=S.PATINA,
                class_name="pulse-dot",
            ),
            spacing="2",
            align="center",
            width="100%",
            padding="10px 16px",
            bg=S.PATINA_GLOW,
            border=f"1px solid rgba(42, 157, 143, 0.3)",
            border_radius="10px",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def relatorios_page() -> rx.Component:
    return rx.vstack(
        _page_header(),

        # Module cards row
        rx.hstack(
            _static_module_card(),
            _ai_module_card(),
            spacing="4",
            width="100%",
            align_items="stretch",
            flex_wrap="wrap",
        ),

        # Error banner (if any)
        _error_banner(),

        # Streaming indicator
        _streaming_banner(),

        # Preview / Result panel (only shown when content is available)
        _preview_panel(),

        # Custom chatbox (Wow Factor)
        _custom_chatbox(),

        # History
        _history_section(),

        spacing="4",
        width="100%",
        padding_bottom="40px",
        class_name="animate-enter",
    )
