import reflex as rx

from bomtempo.components.weather_widget import weather_widget
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def obras_header() -> rx.Component:
    """Header — matching Construction.tsx exactly:
    Left: title + subtitle
    Right: contract filter
    """
    return rx.hstack(
        rx.vstack(
            rx.text("FIELD OPERATIONS", **S.PAGE_TITLE_STYLE),
            rx.text("Acompanhamento de Obras em Tempo Real", **S.PAGE_SUBTITLE_STYLE),
            spacing="1",
        ),
        rx.spacer(),
        # Contract filter (matching React reference)
        rx.hstack(
            rx.icon(tag="filter", size=16, color=S.COPPER, margin_left="8px"),
            rx.el.select(
                rx.foreach(
                    GlobalState.obras_contract_options,
                    lambda c: rx.el.option(
                        c, value=c, style={"background": S.BG_ELEVATED, "color": S.COPPER}
                    ),
                ),
                value=GlobalState.obras_selected_contract,
                on_change=GlobalState.select_obra_and_load_weather,
                background="transparent",
                color="white",
                border="none",
                outline="none",
                font_size="14px",
                font_family=S.FONT_MONO,
                padding="8px",
                cursor="pointer",
            ),
            bg=S.PATINA_GLOW,
            padding_x="12px",
            padding_y="8px",
            border_radius="12px",
            border=f"1px solid {S.PATINA}",
            align="center",
        ),
        width="100%",
        align="center",
        class_name="animate-enter",
    )


# ── Detalhamento da Obra ────────────────────────────────────


def obra_detail_item(label: str, value: str, is_highlight: bool = False) -> rx.Component:
    return rx.vstack(
        rx.text(
            label,
            font_size="10px",
            color=S.TEXT_MUTED,
            text_transform="uppercase",
            font_weight="700",
            letter_spacing="0.05em",
        ),
        rx.text(
            value,
            color=S.COPPER if is_highlight else "white",
            font_family=S.FONT_TECH if is_highlight else S.FONT_MONO,
            font_size="1.25rem" if is_highlight else "1rem",
            font_weight="700",
        ),
        spacing="1",
        align="start",
    )


def obra_detail_block() -> rx.Component:
    """Construction detail info block — matching React reference exactly"""
    data = GlobalState.obra_selected_data

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="layout-template", size=20, color=S.COPPER, margin_right="8px"),
                rx.text(
                    "Detalhamento da Obra",
                    font_family=S.FONT_TECH,
                    font_size="1.25rem",
                    font_weight="700",
                    color=S.COPPER,
                ),
                align="center",
                margin_bottom="32px",
            ),
            rx.grid(
                obra_detail_item("CLIENTE", data.get("cliente", "—")),
                obra_detail_item("ORDEM DE SERVIÇO", data.get("os", "—")),
                obra_detail_item("POTÊNCIA", data.get("potencia_kwp", "—"), is_highlight=True),
                obra_detail_item("PRAZO", data.get("prazo_dias", "—")),
                columns=rx.breakpoints(initial="2", md="4"),
                spacing="6",
                width="100%",
            ),
            width="100%",
        ),
        width="100%",
        **S.GLASS_CARD,
    )


# ── Discipline Progress ─────────────────────────────────────


def discipline_progress_bar(item: dict) -> rx.Component:
    """Progress bar by discipline — matching React reference grouped layout"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(
                    item["categoria"],
                    font_size="16px",
                    font_weight="700",
                    color="white",
                    white_space="nowrap",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.text("P:", font_family=S.FONT_MONO, font_size="13px", color=S.TEXT_MUTED),
                    rx.text(
                        item["previsto_pct"].to(int).to_string() + "%",
                        font_family=S.FONT_MONO,
                        font_size="13px",
                        color=S.TEXT_MUTED,
                    ),
                    rx.box(width="8px"),
                    rx.text("R:", font_family=S.FONT_MONO, font_size="13px", color=S.TEXT_MUTED),
                    rx.text(
                        item["realizado_pct"].to(int).to_string() + "%",
                        font_family=S.FONT_MONO,
                        font_size="13px",
                        font_weight="700",
                        color=rx.cond(
                            item["realizado_pct"].to(float) >= item["previsto_pct"].to(float),
                            S.PATINA,
                            S.DANGER,
                        ),
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                margin_bottom="8px",
            ),
            # Progress Bar Container
            rx.box(
                # Realizado Bar
                rx.box(
                    width=item["realizado_pct"].to(int).to_string() + "%",
                    height="100%",
                    border_radius="9999px",
                    bg=rx.cond(
                        item["realizado_pct"].to(float) >= item["previsto_pct"].to(float),
                        S.PATINA,
                        S.DANGER,
                    ),
                    position="absolute",
                    top="0",
                    left="0",
                    z_index="2",
                    transition="width 1s ease-out",
                ),
                # Previsto Marker (Ghost bar)
                rx.box(
                    width=item["previsto_pct"].to(int).to_string() + "%",
                    height="100%",
                    bg="rgba(255, 255, 255, 0.08)",
                    border_right="2px solid rgba(255, 255, 255, 0.3)",
                    position="absolute",
                    top="0",
                    left="0",
                    z_index="1",
                ),
                height="12px",
                bg="rgba(0, 0, 0, 0.3)",
                border_radius="9999px",
                overflow="hidden",
                position="relative",
                width="100%",
            ),
            # Status Text
            rx.cond(
                item["realizado_pct"].to(float) >= item["previsto_pct"].to(float),
                rx.text(
                    "Avançado",
                    font_size="10px",
                    color=S.TEXT_MUTED,
                    font_style="italic",
                    margin_top="6px",
                ),
                rx.text(
                    "Atraso detectado",
                    font_size="10px",
                    color=S.DANGER,
                    font_style="italic",
                    margin_top="6px",
                ),
            ),
            spacing="0",
            width="100%",
        ),
        padding_y="12px",
        border_bottom=f"1px solid {S.BORDER_SUBTLE}",
        width="100%",
    )


def discipline_progress_section() -> rx.Component:
    """Discipline progress panel — matches React reference"""
    return rx.box(
        rx.vstack(
            rx.text(
                "Progresso por Disciplina",
                font_family=S.FONT_TECH,
                font_size="1.25rem",
                font_weight="700",
                color="white",
                margin_bottom="24px",
            ),
            rx.vstack(
                rx.foreach(
                    GlobalState.disciplina_progress_chart,
                    discipline_progress_bar,
                ),
                spacing="4",
                width="100%",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        min_height="400px",
        width="100%",
    )


# ── Gauge Component ──────────────────────────────────────────


def gauge_component() -> rx.Component:
    """SVG Gauge for global physical progress — dynamic value."""
    # stroke-dasharray/offset use circumference = 2*pi*90 ≈ 565
    return rx.box(
        rx.vstack(
            rx.text(
                "AVANÇO FÍSICO GLOBAL",
                font_size="0.75rem",
                color=S.TEXT_MUTED,
                text_transform="uppercase",
                letter_spacing="0.15em",
                font_weight="700",
                margin_bottom="24px",
                text_align="center",
            ),
            # Gauge — dynamic center text
            rx.center(
                rx.box(
                    # Background track
                    rx.el.svg(
                        rx.el.circle(
                            cx="110",
                            cy="110",
                            r="90",
                            stroke="rgba(255,255,255,0.04)",
                            stroke_width="20",
                            fill="transparent",
                        ),
                        rx.el.circle(
                            cx="110",
                            cy="110",
                            r="90",
                            stroke="#C98B2A",
                            stroke_width="20",
                            fill="transparent",
                            stroke_dasharray="565",
                            stroke_dashoffset=(
                                565 - (565 * GlobalState.avanco_fisico_geral / 100)
                            ).to_string(),
                            stroke_linecap="round",
                            style={"transition": "stroke-dashoffset 1.5s ease-out"},
                        ),
                        height="220",
                        width="220",
                        style={"transform": "rotate(-90deg)"},
                    ),
                    # Center text
                    rx.box(
                        rx.text(
                            GlobalState.avanco_fisico_geral_fmt,
                            font_size="3rem",
                            font_family=S.FONT_TECH,
                            font_weight="700",
                            color="white",
                        ),
                        rx.text(
                            "Conclusão",
                            font_size="10px",
                            color=S.TEXT_MUTED,
                            text_transform="uppercase",
                            letter_spacing="0.15em",
                        ),
                        position="absolute",
                        top="50%",
                        left="50%",
                        transform="translate(-50%, -50%)",
                        text_align="center",
                    ),
                    position="relative",
                    width="220px",
                    height="220px",
                ),
                height="220px",
                width="100%",
            ),
            rx.text(
                "Indicador consolidado ponderado pelo peso financeiro de cada etapa.",
                font_size="0.8rem",
                color=S.TEXT_MUTED,
                text_align="center",
                max_width="240px",
                margin_top="16px",
                line_height="1.4",
            ),
            align="center",
            justify="center",
            width="100%",
            spacing="0",
        ),
        **S.GLASS_CARD,
        width="100%",
        display="flex",
        align_items="center",
        justify_content="center",
        min_height="320px",
    )


# ── Critical Alerts ──────────────────────────────────────────


def critical_alerts() -> rx.Component:
    """Status Crítico panel"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.center(
                    rx.icon(tag="zap", size=20, color=S.PATINA),
                    padding="10px",
                    bg=f"{S.PATINA_GLOW}",
                    border_radius="8px",
                    border=f"1px solid {S.PATINA}40",
                ),
                rx.vstack(
                    rx.text("Status Crítico", font_weight="700", font_size="14px", color="white"),
                    rx.text(
                        "ALERTAS DA PLATAFORMA",
                        font_size="10px",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                    ),
                    spacing="0",
                ),
                align="center",
                spacing="3",
                margin_bottom="16px",
            ),
            rx.vstack(
                rx.box(
                    rx.html("<strong>Atraso:</strong> Módulo Solar (Impacto: 2 dias)"),
                    padding="16px",
                    bg=S.DANGER_BG,
                    border="1px solid rgba(239, 68, 68, 0.2)",
                    border_radius="12px",
                    font_size="12px",
                    color=S.DANGER,
                ),
                rx.box(
                    rx.html("<strong>Atenção:</strong> Logística Inversor"),
                    padding="16px",
                    bg=S.COPPER_GLOW,
                    border=f"1px solid {S.BORDER_ACCENT}",
                    border_radius="12px",
                    font_size="12px",
                    color=S.COPPER,
                ),
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        width="100%",
    )


# ── Main Page Layout ─────────────────────────────────────────


def obras_page() -> rx.Component:
    """Page layout:
    Left (2/3): Detail + Progress
    Right (1/3): Gauge + Alerts
    """
    return rx.vstack(
        obras_header(),
        rx.cond(
            GlobalState.is_loading,
            rx.center(rx.spinner(size="3"), width="100%", height="50vh"),
            rx.grid(
                # Left column
                rx.vstack(
                    obra_detail_block(),
                    discipline_progress_section(),
                    spacing="6",
                    width="100%",
                ),
                # Right column
                rx.vstack(
                    weather_widget(),
                    gauge_component(),
                    critical_alerts(),
                    spacing="6",
                    width="100%",
                ),
                grid_template_columns=rx.breakpoints(initial="1fr", lg="2fr 1fr"),
                spacing="6",
                width="100%",
                align_items="start",
            ),
        ),
        width="100%",
        spacing="8",
        class_name="animate-enter",
        on_mount=[lambda: GlobalState.set_current_path("/obras"), GlobalState.load_weather_data],
    )
