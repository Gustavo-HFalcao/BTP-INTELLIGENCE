import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState

# ── Header ───────────────────────────────────────────────────


def projetos_header() -> rx.Component:
    """Header — React reference: title + search (only in list view, NO phase filter here)"""
    return rx.hstack(
        rx.vstack(
            rx.text("Gestão de Projetos", **S.PAGE_TITLE_STYLE),
            rx.text("Portfolio e Cronogramas Detalhados", **S.PAGE_SUBTITLE_STYLE),
            spacing="1",
        ),
        rx.spacer(),
        # Search input (only in list view) — NO phase filter here
        rx.cond(
            GlobalState.selected_contrato == "",
            rx.box(
                rx.icon(
                    tag="search",
                    size=16,
                    color=S.TEXT_MUTED,
                    position="absolute",
                    left="12px",
                    top="50%",
                    transform="translateY(-50%)",
                    z_index="2",
                ),
                rx.el.input(
                    value=GlobalState.projetos_search,
                    on_change=GlobalState.set_projetos_search,
                    placeholder="Buscar contrato...",
                    background="rgba(255, 255, 255, 0.03)",
                    border="1px solid rgba(255, 255, 255, 0.06)",
                    color="white",
                    padding_left="36px",
                    padding_right="16px",
                    padding_top="8px",
                    padding_bottom="8px",
                    border_radius="12px",
                    outline="none",
                    font_size="13px",
                    font_family=S.FONT_MONO,
                    width="260px",
                    _focus={"borderColor": S.COPPER},
                    transition="all 0.3s ease",
                ),
                position="relative",
            ),
        ),
        width="100%",
        align="center",
        class_name="animate-enter",
    )


# ── Project Card (List View) ────────────────────────────────


def project_card(item: dict) -> rx.Component:
    """Clickable glass card for each contract"""
    return rx.box(
        # Hover arrow
        rx.box(
            rx.icon(tag="arrow-right", size=20, color=S.COPPER),
            class_name="arrow-icon",
        ),
        # Card content
        rx.vstack(
            # Contract + Client
            rx.box(
                rx.text(
                    item["contrato"],
                    color=S.COPPER,
                    font_family=S.FONT_TECH,
                    font_weight="700",
                    font_size="1.125rem",
                ),
                rx.text(
                    item["cliente"],
                    color="white",
                    font_weight="700",
                    font_size="1.25rem",
                    margin_top="4px",
                ),
                margin_bottom="16px",
            ),
            # Details
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="map-pin", size=14, color=S.TEXT_MUTED),
                    rx.text(
                        item.get("localizacao", "—"),
                        font_size="14px",
                        color=S.TEXT_MUTED,
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.hstack(
                    rx.icon(tag="calendar", size=14, color=S.TEXT_MUTED),
                    rx.text(
                        item.get("data_inicio", "—"),
                        font_size="14px",
                        color=S.TEXT_MUTED,
                    ),
                    align="center",
                    spacing="2",
                ),
                spacing="3",
                margin_bottom="24px",
            ),
            # Progress section
            rx.box(
                rx.hstack(
                    rx.text(
                        "Progresso Global",
                        font_size="10px",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        font_weight="700",
                    ),
                    rx.spacer(),
                    rx.text(
                        item.get("progress", 0).to_string() + "%",
                        font_family=S.FONT_MONO,
                        font_weight="700",
                        color="white",
                        font_size="13px",
                    ),
                    width="100%",
                    margin_bottom="8px",
                ),
                rx.box(
                    rx.box(
                        width=item.get("progress", 0).to_string() + "%",
                        height="100%",
                        bg=S.PATINA,
                        border_radius="9999px",
                        transition="width 1s ease-out",
                    ),
                    height="4px",
                    bg="rgba(255, 255, 255, 0.06)",
                    border_radius="9999px",
                    overflow="hidden",
                    width="100%",
                ),
                width="100%",
                padding_top="16px",
                border_top="1px solid rgba(255, 255, 255, 0.06)",
            ),
            width="100%",
            spacing="0",
        ),
        class_name="project-card",
        on_click=GlobalState.select_contrato(item["contrato"]),
    )


# ── Detail View: Project Info Panel ─────────────────────────


def project_info_panel() -> rx.Component:
    """Left panel showing selected contract details"""
    data = GlobalState.selected_contrato_data

    return rx.box(
        rx.vstack(
            rx.text(
                data["cliente"],
                font_family=S.FONT_TECH,
                font_size="1.5rem",
                font_weight="700",
                color="white",
                margin_bottom="24px",
            ),
            # Info rows
            rx.vstack(
                # Contrato
                rx.hstack(
                    rx.text(
                        "Contrato",
                        font_size="10px",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.15em",
                    ),
                    rx.spacer(),
                    rx.text(
                        data["contrato"],
                        color=S.COPPER,
                        font_family=S.FONT_MONO,
                        font_weight="700",
                        font_size="14px",
                    ),
                    width="100%",
                    padding="16px",
                    bg="rgba(255, 255, 255, 0.02)",
                    border_radius="12px",
                    border="1px solid rgba(255, 255, 255, 0.03)",
                    align="center",
                ),
                # Status
                rx.hstack(
                    rx.text(
                        "Status",
                        font_size="10px",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.15em",
                    ),
                    rx.spacer(),
                    rx.box(
                        rx.text(
                            data.get("status", "—"),
                            font_size="10px",
                            font_weight="700",
                            text_transform="uppercase",
                        ),
                        padding="4px 8px",
                        border_radius="4px",
                        bg=rx.cond(
                            data.get("status", "") == "Em Execução",
                            "rgba(42, 157, 143, 0.2)",
                            "rgba(239, 68, 68, 0.2)",
                        ),
                        color=rx.cond(
                            data.get("status", "") == "Em Execução",
                            S.PATINA,
                            S.DANGER,
                        ),
                    ),
                    width="100%",
                    padding="16px",
                    bg="rgba(255, 255, 255, 0.02)",
                    border_radius="12px",
                    border="1px solid rgba(255, 255, 255, 0.03)",
                    align="center",
                ),
                # Dates grid
                rx.grid(
                    rx.vstack(
                        rx.text(
                            "Início",
                            font_size="10px",
                            color=S.TEXT_MUTED,
                            text_transform="uppercase",
                        ),
                        rx.text(
                            data.get("projeto_inicio", "—"),
                            color="white",
                            font_family=S.FONT_MONO,
                            font_size="14px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text(
                            "Estimativa",
                            font_size="10px",
                            color=S.TEXT_MUTED,
                            text_transform="uppercase",
                        ),
                        rx.text(
                            data.get("termino_estimado", "—"),
                            color="white",
                            font_family=S.FONT_MONO,
                            font_size="14px",
                        ),
                        spacing="1",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                spacing="6",
                width="100%",
            ),
            width="100%",
            spacing="0",
        ),
        **S.GLASS_CARD,
    )


# ── Detail View: Activity Timeline ──────────────────────────


def activity_bar(item: dict) -> rx.Component:
    """Activity progress bar matching React reference timeline"""
    is_critical = item["critico"] == "Sim"

    return rx.box(
        rx.hstack(
            rx.text(
                item["atividade"],
                font_size="13px",
                font_weight="700",
                color="white",
            ),
            rx.spacer(),
            rx.text(
                item["fase"],
                font_size="12px",
                color=S.TEXT_MUTED,
            ),
            width="100%",
            margin_bottom="4px",
        ),
        # Progress bar
        rx.box(
            rx.box(
                width=item["conclusao_pct"].to_string() + "%",
                height="100%",
                border_radius="9999px",
                background=rx.cond(
                    is_critical,
                    f"linear-gradient(90deg, {S.DANGER}, #B91C1C)",
                    f"linear-gradient(90deg, {S.COPPER}, {S.COPPER_LIGHT})",
                ),
                transition="width 1s ease-out",
            ),
            rx.text(
                item["conclusao_pct"].to_string() + "%",
                position="absolute",
                right="8px",
                top="50%",
                transform="translateY(-50%)",
                font_size="9px",
                font_weight="700",
                color="white",
                mix_blend_mode="difference",
            ),
            height="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border_radius="9999px",
            overflow="hidden",
            position="relative",
            width="100%",
        ),
        # Critical indicator
        rx.cond(
            is_critical,
            rx.hstack(
                rx.icon(tag="circle-alert", size=10, color=S.DANGER),
                rx.text(
                    "CAMINHO CRÍTICO",
                    font_size="9px",
                    color=S.DANGER,
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                ),
                spacing="1",
                margin_top="4px",
            ),
        ),
        width="100%",
        margin_bottom="16px",
    )


def activity_timeline() -> rx.Component:
    """Activity timeline panel — phase filter goes HERE (inside detail view)"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="calendar", size=20, color=S.COPPER, margin_right="12px"),
                rx.text(
                    "Cronograma de Atividades",
                    font_family=S.FONT_TECH,
                    font_size="1.25rem",
                    font_weight="700",
                    color="white",
                ),
                rx.spacer(),
                # Phase filter buttons — INSIDE the detail view timeline
                rx.hstack(
                    rx.foreach(
                        GlobalState.fases_disponiveis,
                        lambda fase: rx.box(
                            rx.text(
                                fase,
                                font_size="10px",
                                font_weight="700",
                                color=rx.cond(
                                    GlobalState.projetos_fase_filter == fase,
                                    S.BG_VOID,
                                    S.TEXT_MUTED,
                                ),
                            ),
                            padding="4px 10px",
                            border_radius="6px",
                            cursor="pointer",
                            bg=rx.cond(
                                GlobalState.projetos_fase_filter == fase,
                                S.COPPER,
                                "transparent",
                            ),
                            on_click=GlobalState.set_projetos_fase_filter(fase),
                            _hover={
                                "bg": rx.cond(
                                    GlobalState.projetos_fase_filter == fase,
                                    S.COPPER,
                                    "rgba(255, 255, 255, 0.05)",
                                )
                            },
                            transition="all 0.2s ease",
                        ),
                    ),
                    bg="rgba(255, 255, 255, 0.03)",
                    padding="3px",
                    border_radius="10px",
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    spacing="1",
                    flex_wrap="wrap",
                ),
                align="center",
                margin_bottom="24px",
                width="100%",
            ),
            rx.foreach(
                GlobalState.filtered_projetos,
                activity_bar,
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
    )


# ── Detail View ──────────────────────────────────────────────


def detail_view() -> rx.Component:
    return rx.vstack(
        # Back button
        rx.box(
            rx.button(
                rx.icon(tag="arrow-left", size=20),
                rx.text(
                    "Voltar para Lista",
                    font_size="14px",
                    font_weight="700",
                ),
                color=S.COPPER,
                variant="ghost",
                cursor="pointer",
                on_click=GlobalState.deselect_contrato,
                _hover={"opacity": "0.8"},
                padding="0",
            ),
            margin_bottom="24px",
        ),
        # Two-column: Info panel + Timeline
        rx.grid(
            rx.box(
                project_info_panel(),
                grid_column="span 1",
            ),
            rx.box(
                activity_timeline(),
                grid_column=rx.breakpoints(initial="span 1", lg="span 2"),
            ),
            columns=rx.breakpoints(initial="1", lg="3"),
            spacing="8",
            width="100%",
        ),
        width="100%",
        spacing="0",
        class_name="animate-enter",
    )


# ── List View (Card Grid) ───────────────────────────────────


def list_view() -> rx.Component:
    return rx.box(
        rx.grid(
            rx.foreach(
                GlobalState.filtered_contratos,
                project_card,
            ),
            columns=rx.breakpoints(initial="1", md="2", lg="3"),
            spacing="6",
            width="100%",
        ),
        width="100%",
    )


# ── Main Page ────────────────────────────────────────────────


def projetos_page() -> rx.Component:
    return rx.vstack(
        projetos_header(),
        rx.cond(
            GlobalState.is_loading,
            rx.center(rx.spinner(size="3"), width="100%", height="50vh"),
            rx.cond(
                GlobalState.selected_contrato != "",
                detail_view(),
                list_view(),
            ),
        ),
        width="100%",
        spacing="6",
        class_name="animate-enter",
    )
