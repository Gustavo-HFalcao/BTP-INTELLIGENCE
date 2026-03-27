"""
Hub de Operações — Unified Operations Hub
Merges former Obras (field ops) + Projetos (project portfolio) into one module.
Route: /hub

Replaces obras.py + projetos.py with a single, richer unified view:
  - Landing: Project Pulse Cards grid
  - Detail: 5-tab hub (Visão Geral, Dashboard, Cronograma, Auditoria, Timeline)
"""
import reflex as rx

from bomtempo.components.skeletons import page_loading_skeleton
from bomtempo.components.windy_map_widget import windy_map_widget
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState
from bomtempo.state.hub_state import HubState, AUDIT_CATEGORIES, ENTRY_TYPES

# ── Local glass card variants ──────────────────────────────────────────────────
_GLASS_COMPACT = {**S.GLASS_CARD, "padding": "16px 20px"}
_GLASS_PANEL   = {**S.GLASS_CARD, "padding": "20px 24px"}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — LANDING PAGE: PROJECT PULSE CARDS
# ══════════════════════════════════════════════════════════════════════════════


def hub_pulse_card(item: dict) -> rx.Component:
    """Enterprise project pulse card — matched to Deep Tectonic design system."""
    avanco = item["progress"].to(float).to(int)

    return rx.box(
        # ── Top row: contract code + status badge ─────────────────────────────
        rx.hstack(
            rx.text(
                item["contrato"],
                font_family=S.FONT_MONO,
                font_size="11px",
                font_weight="700",
                color=S.COPPER,
                letter_spacing="0.05em",
            ),
            rx.box(
                item["status"],
                padding="2px 8px",
                background=item["status_bg"],
                color=item["status_color"],
                font_size="10px",
                font_family=S.FONT_MONO,
                text_transform="uppercase",
                letter_spacing="-0.01em",
                border=f"1px solid {item['status_color']}",
                border_radius="2px",
            ),
            justify="between",
            align="start",
            margin_bottom="20px",
            width="100%",
        ),
        # ── Client / project name ─────────────────────────────────────────────
        rx.text(
            item["cliente"],
            font_family=S.FONT_TECH,
            font_size="1.4rem",
            font_weight="700",
            text_transform="uppercase",
            line_height="1.2",
            margin_bottom="4px",
            color="var(--text-main)",
        ),
        # ── Location row ──────────────────────────────────────────────────────
        rx.hstack(
            rx.icon(tag="map-pin", size=13, color=S.TEXT_MUTED),
            rx.text(
                item["localizacao"],
                font_size="12px",
                font_family=S.FONT_BODY,
                color=S.TEXT_MUTED,
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
            spacing="2",
            align="center",
            margin_bottom="20px",
            width="100%",
        ),
        rx.spacer(),
        # ── Progress + deadline ───────────────────────────────────────────────
        rx.box(
            # Label row
            rx.hstack(
                rx.text(
                    "PROGRESS PULSE",
                    font_family=S.FONT_MONO,
                    font_size="9px",
                    color=S.TEXT_MUTED,
                    text_transform="uppercase",
                    letter_spacing="0.1em",
                ),
                rx.spacer(),
                rx.text(
                    avanco.to_string() + "%",
                    font_family=S.FONT_MONO,
                    font_size="14px",
                    font_weight="700",
                    color=item["status_color"],
                ),
                width="100%",
                align="center",
                margin_bottom="6px",
            ),
            # Progress track
            rx.box(
                rx.box(
                    height="100%",
                    bg=item["status_color"],
                    width=avanco.to_string() + "%",
                    border_radius="2px",
                    transition="width 1.1s ease-out",
                ),
                height="3px",
                bg="rgba(44,55,52,1)",
                width="100%",
                margin_bottom="20px",
                border_radius="2px",
            ),
            # Deadline + risk row
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "DEADLINE",
                        font_family=S.FONT_MONO,
                        font_size="9px",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.08em",
                    ),
                    rx.text(
                        item["days_fmt"],
                        font_family=S.FONT_MONO,
                        font_size="12px",
                        font_weight="600",
                        color=rx.cond(
                            item["days_to_deadline"].to(int) < 0,
                            S.DANGER,
                            "var(--text-main)",
                        ),
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                # Risk badge pill
                rx.hstack(
                    rx.box(
                        width="6px",
                        height="6px",
                        border_radius="50%",
                        bg=item["risco_color"],
                        class_name=rx.cond(
                            item["days_to_deadline"].to(int) < 0,
                            "animate-pulse",
                            "",
                        ),
                    ),
                    rx.text(
                        item["risco_label"],
                        font_family=S.FONT_MONO,
                        font_size="9px",
                        text_transform="uppercase",
                        letter_spacing="0.05em",
                        font_weight="700",
                        color=item["risco_color"],
                    ),
                    padding="4px 8px",
                    bg="rgba(255,255,255,0.05)",
                    border="1px solid rgba(255,255,255,0.1)",
                    border_radius="4px",
                    align="center",
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
            width="100%",
        ),
        # ── Card container ────────────────────────────────────────────────────
        background="rgba(14,26,23,0.6)",
        backdrop_filter="blur(12px)",
        border="1px solid rgba(255,255,255,0.08)",
        border_radius=S.R_CARD,
        padding="20px",
        display="flex",
        flex_direction="column",
        height="100%",
        min_height="280px",
        cursor="pointer",
        on_click=GlobalState.select_project(item["contrato"]),
        transition="all 0.25s cubic-bezier(0.4,0,0.2,1)",
        _hover={
            "background": "rgba(14,26,23,0.95)",
            "border_color": "rgba(201,139,42,0.5)",
            "box_shadow": (
                "0 0 0 1px rgba(201,139,42,0.15),"
                "0 12px 40px rgba(0,0,0,0.5),"
                "0 0 50px rgba(201,139,42,0.07)"
            ),
            "transform": "translateY(-3px)",
        },
    )


def hub_landing_page() -> rx.Component:
    """Landing view — header + search + project pulse cards grid."""
    return rx.vstack(
        # ── Header row ─────────────────────────────────────────────────────────
        rx.flex(
            # Left: title block
            rx.vstack(
                rx.text(
                    "HUB DE OPERAÇÕES",
                    font_family=S.FONT_TECH,
                    font_size="clamp(1.5rem,4vw,2.5rem)",
                    font_weight="700",
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                    color="var(--text-main)",
                    line_height="1.1",
                ),
                rx.text(
                    "Gestão centralizada de frentes de obra, orçamentos e "
                    "cronogramas críticos em tempo real.",
                    font_family=S.FONT_BODY,
                    font_size="14px",
                    color=S.TEXT_MUTED,
                    margin_top="4px",
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            # Right: action buttons
            rx.hstack(
                # FILTRAR
                rx.button(
                    rx.hstack(
                        rx.icon(tag="filter", size=14),
                        rx.text(
                            "FILTRAR",
                            font_family=S.FONT_TECH,
                            font_size="13px",
                            font_weight="700",
                            letter_spacing="0.08em",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    bg="rgba(19,29,27,1)",
                    color="var(--text-main)",
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    padding="8px 16px",
                    border_radius=S.R_CONTROL,
                    _hover={"border_color": "rgba(201,139,42,0.4)", "bg": "rgba(30,52,48,1)"},
                    cursor="pointer",
                    transition="all 0.2s ease",
                ),
                # DUPLICAR
                rx.button(
                    rx.hstack(
                        rx.icon(tag="copy", size=14),
                        rx.text(
                            "DUPLICAR",
                            font_family=S.FONT_TECH,
                            font_size="13px",
                            font_weight="700",
                            letter_spacing="0.08em",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    bg="rgba(19,29,27,1)",
                    color="var(--text-main)",
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    padding="8px 16px",
                    border_radius=S.R_CONTROL,
                    _hover={"border_color": "rgba(201,139,42,0.4)", "bg": "rgba(30,52,48,1)"},
                    cursor="pointer",
                    transition="all 0.2s ease",
                ),
                # NOVO PROJETO
                rx.button(
                    rx.hstack(
                        rx.icon(tag="plus", size=14),
                        rx.text(
                            "NOVO PROJETO",
                            font_family=S.FONT_TECH,
                            font_size="13px",
                            font_weight="700",
                            letter_spacing="0.08em",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    background="linear-gradient(135deg, #C98B2A 0%, #835500 100%)",
                    color="#3d2500",
                    border="none",
                    padding="8px 20px",
                    border_radius=S.R_CONTROL,
                    box_shadow="0 0 18px rgba(201,139,42,0.28)",
                    _hover={"filter": "brightness(1.1)", "box_shadow": "0 0 24px rgba(201,139,42,0.4)"},
                    cursor="pointer",
                    transition="all 0.2s ease",
                ),
                spacing="3",
                align="center",
                flex_wrap="wrap",
            ),
            width="100%",
            direction=rx.breakpoints(initial="column", md="row"),
            justify="between",
            align=rx.breakpoints(initial="start", md="center"),
            gap="1.25rem",
            margin_bottom="28px",
        ),
        # ── Search bar ─────────────────────────────────────────────────────────
        rx.box(
            rx.icon(
                tag="search",
                size=15,
                color=S.TEXT_MUTED,
                position="absolute",
                left="14px",
                top="50%",
                transform="translateY(-50%)",
                z_index="2",
            ),
            rx.el.input(
                value=GlobalState.project_search,
                on_change=GlobalState.set_project_search,
                placeholder="PESQUISAR TELEMETRIA...",
                style={
                    "background": "rgba(14,26,23,0.8)",
                    "backdropFilter": "blur(12px)",
                    "border": f"1px solid {S.BORDER_SUBTLE}",
                    "borderRadius": S.R_CONTROL,
                    "color": "var(--text-main)",
                    "padding": "10px 14px 10px 42px",
                    "fontSize": "13px",
                    "fontFamily": S.FONT_MONO,
                    "letterSpacing": "0.05em",
                    "width": "100%",
                    "outline": "none",
                    "transition": "border-color 0.2s ease, box-shadow 0.2s ease",
                },
                _focus={
                    "border_color": S.COPPER,
                    "box_shadow": "0 0 0 1px rgba(201,139,42,0.2)",
                },
            ),
            position="relative",
            width=rx.breakpoints(initial="100%", md="380px"),
            margin_bottom="32px",
        ),
        # ── Cards grid ─────────────────────────────────────────────────────────
        rx.cond(
            GlobalState.project_pulse_cards,
            rx.grid(
                rx.foreach(GlobalState.project_pulse_cards, hub_pulse_card),
                columns=rx.breakpoints(initial="1", md="2", lg="3"),
                gap="20px",
                width="100%",
                class_name="animate-enter",
            ),
            rx.center(
                rx.vstack(
                    rx.icon(
                        tag="folder-kanban",
                        size=48,
                        color=S.BORDER_SUBTLE,
                    ),
                    rx.text(
                        "Nenhum projeto encontrado",
                        font_size="1rem",
                        color=S.TEXT_MUTED,
                        font_family=S.FONT_TECH,
                        font_weight="700",
                        text_transform="uppercase",
                    ),
                    rx.text(
                        "Ajuste os filtros ou verifique a conexão com o banco de dados.",
                        font_size="13px",
                        color=S.TEXT_MUTED,
                        font_family=S.FONT_BODY,
                    ),
                    spacing="3",
                    align="center",
                ),
                height="40vh",
                width="100%",
            ),
        ),
        width="100%",
        spacing="0",
        align="start",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SHARED NAV BAR — appears at top of detail view
# ══════════════════════════════════════════════════════════════════════════════


def _hub_navbar() -> rx.Component:
    """Sticky nav bar with back button + tab list for the detail hub."""

    def _tab(label: str, value: str, icon_tag: str) -> rx.Component:
        is_active = GlobalState.project_hub_tab == value
        return rx.box(
            rx.hstack(
                rx.icon(
                    tag=icon_tag,
                    size=13,
                    color=rx.cond(is_active, S.COPPER, S.TEXT_MUTED),
                ),
                rx.text(
                    label,
                    font_family=S.FONT_MONO,
                    font_size="13px",
                    font_weight=rx.cond(is_active, "700", "400"),
                    color=rx.cond(is_active, S.COPPER, "rgba(218,229,225,0.55)"),
                    transition="color 0.2s ease",
                    white_space="nowrap",
                ),
                spacing="2",
                align="center",
            ),
            padding_bottom="10px",
            padding_top="2px",
            padding_x="4px",
            border_bottom=rx.cond(
                is_active,
                f"2px solid {S.COPPER}",
                "2px solid transparent",
            ),
            cursor="pointer",
            on_click=GlobalState.set_project_hub_tab(value),
            _hover={"& > div > p": {"color": "rgba(218,229,225,0.9)"}},
            transition="border-color 0.2s ease",
        )

    return rx.box(
        rx.flex(
            # Back button + project code
            rx.hstack(
                rx.icon_button(
                    rx.icon(tag="chevron-left", size=18, color="var(--text-main)"),
                    variant="ghost",
                    on_click=GlobalState.deselect_project,
                    _hover={"bg": "rgba(255,255,255,0.06)"},
                    cursor="pointer",
                    border_radius="4px",
                    size="2",
                ),
                rx.vstack(
                    rx.text(
                        GlobalState.selected_project,
                        font_family=S.FONT_TECH,
                        font_size="1.2rem",
                        font_weight="700",
                        color="var(--text-main)",
                        letter_spacing="-0.01em",
                    ),
                    rx.text(
                        "HUB DE OPERAÇÕES",
                        font_family=S.FONT_MONO,
                        font_size="9px",
                        color=S.COPPER,
                        text_transform="uppercase",
                        letter_spacing="0.12em",
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
                align="center",
            ),
            # Tab strip
            rx.hstack(
                _tab("Visão Geral", "visao_geral", "layout-dashboard"),
                _tab("Dashboard", "dashboard", "bar-chart-3"),
                _tab("Cronograma", "cronograma", "calendar-range"),
                _tab("Auditoria", "auditoria", "scan-eye"),
                _tab("Timeline", "timeline", "git-branch"),
                spacing="6",
                align="end",
                display=rx.breakpoints(initial="none", lg="flex"),
                overflow_x="auto",
            ),
            width="100%",
            justify="between",
            align="end",
        ),
        padding="14px 28px",
        background="rgba(14,26,23,0.7)",
        backdrop_filter="blur(24px)",
        border="1px solid rgba(255,255,255,0.06)",
        border_radius="8px",
        box_shadow="0 16px 40px rgba(0,0,0,0.35), 0 0 8px rgba(42,157,143,0.04)",
        margin_bottom="24px",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — VISÃO GERAL
# ══════════════════════════════════════════════════════════════════════════════


def _vg_kpi_card(
    icon_tag: str,
    label: str,
    value,
    subtitle,
    value_color: str = "var(--text-main)",
    bar_pct=None,
) -> rx.Component:
    """Compact KPI tile for the visão geral strip."""
    return rx.box(
        rx.text(
            label,
            font_size="9px",
            font_family=S.FONT_MONO,
            color="rgba(218,229,225,0.5)",
            text_transform="uppercase",
            letter_spacing="0.1em",
            margin_bottom="6px",
        ),
        rx.hstack(
            rx.center(
                rx.icon(tag=icon_tag, size=14, color=value_color),
                width="28px",
                height="28px",
                bg="rgba(255,255,255,0.04)",
                border_radius="4px",
                flex_shrink="0",
            ),
            rx.text(
                value,
                font_family=S.FONT_TECH,
                font_size="2rem",
                font_weight="700",
                color=value_color,
                line_height="1",
            ),
            spacing="3",
            align="center",
            margin_bottom="4px",
        ),
        rx.cond(
            bar_pct != None,
            rx.box(
                rx.box(
                    height="100%",
                    bg=value_color,
                    width=bar_pct,
                    border_radius="2px",
                    transition="width 1.2s ease-out",
                ),
                height="3px",
                bg="rgba(255,255,255,0.06)",
                border_radius="2px",
                overflow="hidden",
                width="100%",
                margin_top="6px",
            ),
            rx.text(
                subtitle,
                font_size="10px",
                font_family=S.FONT_MONO,
                color=S.TEXT_MUTED,
            ),
        ),
        **_GLASS_COMPACT,
        flex="1",
        min_width="150px",
        flex_direction="column",
        display="flex",
    )


def _vg_weather_card() -> rx.Component:
    """Compact weather KPI tile — shows temp + condition + wind."""
    wd = GlobalState.weather_data
    return rx.box(
        rx.text(
            "TELEMETRIA AMBIENTAL",
            font_size="9px",
            font_family=S.FONT_MONO,
            color="rgba(218,229,225,0.5)",
            text_transform="uppercase",
            letter_spacing="0.1em",
            margin_bottom="6px",
        ),
        rx.cond(
            GlobalState.weather_loading,
            rx.hstack(
                rx.spinner(size="2", color=S.PATINA),
                rx.text("Carregando...", font_size="12px", color=S.TEXT_MUTED),
                spacing="3",
                align="center",
            ),
            rx.cond(
                GlobalState.weather_data != {},
                rx.hstack(
                    rx.center(
                        rx.icon(tag="thermometer", size=14, color=S.PATINA),
                        width="28px",
                        height="28px",
                        bg="rgba(42,157,143,0.1)",
                        border_radius="4px",
                        flex_shrink="0",
                    ),
                    rx.vstack(
                        rx.text(
                            wd["temp"].to_string() + "°C",
                            font_family=S.FONT_TECH,
                            font_size="2rem",
                            font_weight="700",
                            color=S.PATINA,
                            line_height="1",
                        ),
                        rx.hstack(
                            rx.text(
                                wd.get("condition", "—"),
                                font_size="10px",
                                color=S.TEXT_MUTED,
                                font_family=S.FONT_MONO,
                            ),
                            rx.text("·", font_size="10px", color=S.TEXT_MUTED),
                            rx.text(
                                wd.get("wind_speed", "—").to_string() + " km/h",
                                font_size="10px",
                                color=S.TEXT_MUTED,
                                font_family=S.FONT_MONO,
                            ),
                            spacing="1",
                            align="center",
                        ),
                        spacing="0",
                        align="start",
                    ),
                    spacing="3",
                    align="center",
                ),
                rx.text(
                    "Sem dados climáticos",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_MONO,
                    font_style="italic",
                ),
            ),
        ),
        **_GLASS_COMPACT,
        flex="1",
        min_width="160px",
        flex_direction="column",
        display="flex",
    )


def _vg_ai_feed() -> rx.Component:
    """AI Intelligence feed panel with LIVE badge."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.hstack(
                    rx.center(
                        rx.icon(tag="brain-circuit", size=14, color=S.COPPER),
                        width="28px",
                        height="28px",
                        bg=S.COPPER_GLOW,
                        border_radius="4px",
                        border=f"1px solid {S.BORDER_ACCENT}",
                        flex_shrink="0",
                    ),
                    rx.text(
                        "FEED DE INTELIGÊNCIA IA",
                        font_family=S.FONT_TECH,
                        font_size="1rem",
                        font_weight="700",
                        text_transform="uppercase",
                        color="var(--text-main)",
                        letter_spacing="0.04em",
                    ),
                    spacing="3",
                    align="center",
                ),
                rx.spacer(),
                # LIVE badge
                rx.hstack(
                    rx.box(
                        width="7px",
                        height="7px",
                        border_radius="50%",
                        bg="#22c55e",
                        class_name="animate-pulse",
                    ),
                    rx.text(
                        "LIVE",
                        font_size="9px",
                        font_weight="700",
                        color="#22c55e",
                        font_family=S.FONT_MONO,
                        letter_spacing="0.1em",
                    ),
                    padding="3px 8px",
                    border_radius="4px",
                    bg="rgba(34,197,94,0.1)",
                    border="1px solid rgba(34,197,94,0.25)",
                    spacing="1",
                    align="center",
                ),
                width="100%",
                align="center",
                margin_bottom="16px",
            ),
            # Feed content — AI insight from state or placeholder entries
            rx.cond(
                GlobalState.obra_insight_loading,
                rx.vstack(
                    rx.hstack(
                        rx.spinner(size="2", color=S.COPPER),
                        rx.text(
                            "Analisando dados do projeto...",
                            font_size="12px",
                            color=S.TEXT_MUTED,
                            font_style="italic",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    rx.vstack(
                        rx.box(
                            height="10px",
                            bg="rgba(201,139,42,0.09)",
                            border_radius="4px",
                            width="100%",
                        ),
                        rx.box(
                            height="10px",
                            bg="rgba(201,139,42,0.06)",
                            border_radius="4px",
                            width="80%",
                        ),
                        rx.box(
                            height="10px",
                            bg="rgba(201,139,42,0.04)",
                            border_radius="4px",
                            width="60%",
                        ),
                        spacing="2",
                        width="100%",
                        margin_top="10px",
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.cond(
                    GlobalState.obra_insight_text != "",
                    rx.box(
                        # Priority badge
                        rx.hstack(
                            rx.box(
                                "ANÁLISE IA",
                                padding="2px 8px",
                                border_radius="3px",
                                bg="rgba(201,139,42,0.12)",
                                border=f"1px solid {S.BORDER_ACCENT}",
                                font_size="9px",
                                font_family=S.FONT_MONO,
                                font_weight="700",
                                color=S.COPPER,
                                text_transform="uppercase",
                            ),
                            rx.spacer(),
                            rx.text(
                                "agora",
                                font_size="9px",
                                color=S.TEXT_MUTED,
                                font_family=S.FONT_MONO,
                            ),
                            width="100%",
                            align="center",
                            margin_bottom="8px",
                        ),
                        rx.text(
                            GlobalState.obra_insight_text,
                            font_size="0.8125rem",
                            color=S.TEXT_PRIMARY,
                            line_height="1.7",
                            font_family=S.FONT_BODY,
                        ),
                        padding="14px 16px",
                        bg="rgba(201,139,42,0.04)",
                        border_radius="6px",
                        border=f"1px solid {S.BORDER_ACCENT}",
                        border_left=f"3px solid {S.COPPER}",
                        width="100%",
                    ),
                    # Static placeholder feed items when no insight yet
                    rx.vstack(
                        _static_feed_item(
                            "ALTA",
                            S.DANGER,
                            "rgba(239,68,68,0.12)",
                            "Desvio de cronograma detectado",
                            "Atividade Estrutura Metálica com atraso acumulado de 4 dias.",
                            "Ver detalhes",
                        ),
                        _static_feed_item(
                            "OTIMIZAÇÃO",
                            S.PATINA,
                            "rgba(42,157,143,0.12)",
                            "Oportunidade de aceleração",
                            "Equipe civil disponível para realocar para frente elétrica.",
                            "Ver recomendação",
                        ),
                        _static_feed_item(
                            "RELATÓRIO",
                            S.COPPER,
                            S.COPPER_GLOW,
                            "Relatório semanal gerado",
                            "Semana 14 — todas as métricas dentro do SLA contratual.",
                            "Abrir relatório",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
            ),
            width="100%",
        ),
        **_GLASS_PANEL,
        height="100%",
    )


def _static_feed_item(
    badge_label: str,
    badge_color: str,
    badge_bg: str,
    title: str,
    description: str,
    action: str,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                badge_label,
                padding="2px 7px",
                border_radius="3px",
                bg=badge_bg,
                border=f"1px solid {badge_color}",
                font_size="9px",
                font_family=S.FONT_MONO,
                font_weight="700",
                color=badge_color,
                text_transform="uppercase",
            ),
            rx.spacer(),
            rx.text(
                "agora",
                font_size="9px",
                color=S.TEXT_MUTED,
                font_family=S.FONT_MONO,
            ),
            width="100%",
            align="center",
            margin_bottom="5px",
        ),
        rx.text(
            title,
            font_size="13px",
            font_weight="700",
            color="var(--text-main)",
            margin_bottom="3px",
        ),
        rx.text(
            description,
            font_size="11px",
            color=S.TEXT_MUTED,
            line_height="1.5",
            margin_bottom="6px",
        ),
        rx.text(
            action + " →",
            font_size="10px",
            color=S.COPPER,
            font_family=S.FONT_MONO,
            cursor="pointer",
            _hover={"opacity": "0.75"},
        ),
        padding="12px 14px",
        border_radius="4px",
        bg="rgba(255,255,255,0.02)",
        border=f"1px solid {S.BORDER_SUBTLE}",
        _hover={"border_color": "rgba(255,255,255,0.14)", "bg": "rgba(255,255,255,0.03)"},
        transition="all 0.15s ease",
        width="100%",
    )


def _vg_site_telemetry() -> rx.Component:
    """Left column — compact site info panel."""
    data = GlobalState.obra_enterprise_data
    fmt = GlobalState.obra_kpi_fmt
    progress_pct = data.get("progress", "0").to(float).to(int).to_string() + "%"

    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.icon(tag="radio-tower", size=15, color=S.PATINA, margin_right="6px"),
                rx.text(
                    "TELEMETRIA DO SITE",
                    font_family=S.FONT_TECH,
                    font_size="1rem",
                    font_weight="700",
                    text_transform="uppercase",
                    color="var(--text-main)",
                    letter_spacing="0.04em",
                ),
                align="center",
                margin_bottom="16px",
                width="100%",
            ),
            # Location row
            rx.hstack(
                rx.icon(tag="map-pin", size=13, color=S.TEXT_MUTED),
                rx.text(
                    data.get("localizacao", "—"),
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_MONO,
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                spacing="2",
                align="center",
                margin_bottom="16px",
                width="100%",
            ),
            # Progress physical
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "PROGRESSO FÍSICO",
                        font_size="9px",
                        font_family=S.FONT_MONO,
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.1em",
                    ),
                    rx.spacer(),
                    rx.text(
                        progress_pct,
                        font_size="12px",
                        font_weight="700",
                        color=S.PATINA,
                        font_family=S.FONT_MONO,
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="5px",
                ),
                rx.box(
                    rx.box(
                        height="100%",
                        bg=S.PATINA,
                        width=progress_pct,
                        transition="width 1.2s ease-out",
                        border_radius="2px",
                    ),
                    height="4px",
                    bg="rgba(255,255,255,0.05)",
                    border_radius="2px",
                    overflow="hidden",
                    width="100%",
                    margin_bottom="16px",
                ),
                spacing="0",
                width="100%",
            ),
            # Uptime metric
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "UPTIME / FREQUÊNCIA AUDIT",
                        font_size="9px",
                        font_family=S.FONT_MONO,
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.1em",
                    ),
                    rx.spacer(),
                    rx.text(
                        "99.2%",
                        font_size="12px",
                        font_weight="700",
                        color=S.COPPER,
                        font_family=S.FONT_MONO,
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="5px",
                ),
                rx.box(
                    rx.box(
                        height="100%",
                        bg=S.COPPER,
                        width="99.2%",
                        transition="width 1.2s ease-out",
                        border_radius="2px",
                    ),
                    height="4px",
                    bg="rgba(255,255,255,0.05)",
                    border_radius="2px",
                    overflow="hidden",
                    width="100%",
                ),
                spacing="0",
                width="100%",
            ),
            rx.spacer(),
            # Divider
            rx.box(height="1px", bg=S.BORDER_SUBTLE, width="100%", margin_y="12px"),
            # Contract + Client mini chips
            rx.vstack(
                rx.hstack(
                    rx.text(
                        "CONTRATO",
                        font_size="9px",
                        color=S.TEXT_MUTED,
                        font_family=S.FONT_MONO,
                        text_transform="uppercase",
                        letter_spacing="0.08em",
                        min_width="80px",
                    ),
                    rx.text(
                        data.get("contrato", GlobalState.selected_project),
                        font_size="12px",
                        color=S.COPPER,
                        font_family=S.FONT_MONO,
                        font_weight="700",
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                rx.hstack(
                    rx.text(
                        "CLIENTE",
                        font_size="9px",
                        color=S.TEXT_MUTED,
                        font_family=S.FONT_MONO,
                        text_transform="uppercase",
                        letter_spacing="0.08em",
                        min_width="80px",
                    ),
                    rx.text(
                        data.get("cliente", "—"),
                        font_size="12px",
                        color="var(--text-main)",
                        font_family=S.FONT_MONO,
                        overflow="hidden",
                        text_overflow="ellipsis",
                        white_space="nowrap",
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                rx.hstack(
                    rx.text(
                        "PRAZO",
                        font_size="9px",
                        color=S.TEXT_MUTED,
                        font_family=S.FONT_MONO,
                        text_transform="uppercase",
                        letter_spacing="0.08em",
                        min_width="80px",
                    ),
                    rx.text(
                        data.get("prazo_dias", "—").to_string() + " dias",
                        font_size="12px",
                        color="var(--text-main)",
                        font_family=S.FONT_MONO,
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            width="100%",
        ),
        **_GLASS_PANEL,
        height="100%",
    )


def _tab_visao_geral() -> rx.Component:
    fmt = GlobalState.obra_kpi_fmt
    data = GlobalState.obra_enterprise_data
    progress_val = data.get("progress", "0").to(float).to(int).to_string() + "%"

    return rx.vstack(
        # ── KPI Strip ─────────────────────────────────────────────────────────
        rx.flex(
            _vg_kpi_card(
                "trending-up",
                "PROGRESSO FÍSICO",
                progress_val,
                "",
                value_color=S.PATINA,
                bar_pct=progress_val,
            ),
            _vg_kpi_card(
                "shield-check",
                "SALDO DO PROJETO",
                data.get("nota_risco", "—"),
                "Nota de risco",
                value_color=S.COPPER,
            ),
            _vg_kpi_card(
                "brain-circuit",
                "DISRUPÇÕES IA",
                fmt.get("disrupcoes_ia", "—"),
                "Alertas ativos",
                value_color="#E89845",
            ),
            _vg_kpi_card(
                "percent",
                "DESVIO FINANCEIRO",
                fmt.get("budget_variacao_fmt", "—"),
                fmt.get("budget_exec_rate_fmt", ""),
                value_color=rx.cond(
                    fmt.get("budget_over", False),
                    S.DANGER,
                    S.PATINA,
                ),
            ),
            _vg_weather_card(),
            gap="12px",
            flex_wrap="wrap",
            width="100%",
            align_items="stretch",
        ),
        # ── Row 2: S-Curve + AI feed ──────────────────────────────────────────
        rx.grid(
            # LEFT: S-Curve chart card
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.hstack(
                            rx.icon(
                                tag="trending-up",
                                size=15,
                                color=S.PATINA,
                                margin_right="6px",
                            ),
                            rx.text(
                                "ANÁLISE DE CURVA S INTEGRADA",
                                font_family=S.FONT_TECH,
                                font_size="1rem",
                                font_weight="700",
                                text_transform="uppercase",
                                color="var(--text-main)",
                                letter_spacing="0.04em",
                            ),
                            align="center",
                        ),
                        rx.spacer(),
                        # Legend
                        rx.hstack(
                            rx.box(
                                width="20px",
                                height="2px",
                                bg="transparent",
                                border_top=f"2px dashed {S.TEXT_MUTED}",
                            ),
                            rx.text(
                                "Previsto",
                                font_size="9px",
                                color=S.TEXT_MUTED,
                                font_weight="700",
                            ),
                            rx.box(width="12px"),
                            rx.box(
                                width="20px",
                                height="3px",
                                bg=S.PATINA,
                                border_radius="2px",
                            ),
                            rx.text(
                                "Realizado",
                                font_size="9px",
                                color=S.TEXT_MUTED,
                                font_weight="700",
                            ),
                            align="center",
                            spacing="2",
                        ),
                        width="100%",
                        align="center",
                        margin_bottom="16px",
                    ),
                    # Chart
                    rx.cond(
                        GlobalState.project_scurve_chart,
                        rx.recharts.area_chart(
                            rx.recharts.area(
                                data_key="previsto",
                                stroke=S.TEXT_MUTED,
                                fill="rgba(136,153,153,0.04)",
                                stroke_dasharray="5 3",
                                dot=False,
                                stroke_width=2,
                            ),
                            rx.recharts.area(
                                data_key="realizado",
                                stroke=S.PATINA,
                                fill="rgba(42,157,143,0.12)",
                                dot={"fill": S.PATINA, "r": 3, "strokeWidth": 0},
                                active_dot={
                                    "fill": S.COPPER,
                                    "r": 5,
                                    "stroke": "rgba(201,139,42,0.4)",
                                    "strokeWidth": 3,
                                },
                                stroke_width=2,
                            ),
                            rx.recharts.x_axis(
                                data_key="data",
                                tick={
                                    "fontSize": 10,
                                    "fill": S.TEXT_MUTED,
                                    "fontFamily": "JetBrains Mono",
                                },
                            ),
                            rx.recharts.y_axis(
                                unit="%",
                                tick={
                                    "fontSize": 10,
                                    "fill": S.TEXT_MUTED,
                                    "fontFamily": "JetBrains Mono",
                                },
                                domain=[0, 100],
                                width=36,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 3",
                                stroke="rgba(255,255,255,0.04)",
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "background": "rgba(8,18,16,0.96)",
                                    "border": f"1px solid {S.BORDER_ACCENT}",
                                    "borderRadius": "8px",
                                    "fontSize": "12px",
                                    "boxShadow": "0 8px 32px rgba(0,0,0,0.6)",
                                    "backdropFilter": "blur(12px)",
                                    "padding": "12px 16px",
                                },
                                label_style={
                                    "color": S.TEXT_MUTED,
                                    "fontSize": "9px",
                                    "fontWeight": "700",
                                    "textTransform": "uppercase",
                                    "letterSpacing": ".1em",
                                },
                            ),
                            data=GlobalState.project_scurve_chart,
                            height=200,
                            width="100%",
                            class_name="chart-enter",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="line-chart", size=32, color=S.BORDER_SUBTLE),
                                rx.text(
                                    "Curva S — dados do contrato selecionado",
                                    font_size="13px",
                                    color=S.TEXT_MUTED,
                                    text_align="center",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            height="200px",
                        ),
                    ),
                    # AI footer strip
                    rx.cond(
                        GlobalState.obra_insight_text != "",
                        rx.hstack(
                            rx.center(
                                rx.icon(tag="brain-circuit", size=11, color=S.COPPER),
                                width="20px",
                                height="20px",
                                bg=S.COPPER_GLOW,
                                border_radius="50%",
                                flex_shrink="0",
                            ),
                            rx.text(
                                GlobalState.obra_insight_text,
                                font_size="11px",
                                color=S.TEXT_MUTED,
                                line_height="1.5",
                                overflow="hidden",
                                white_space="nowrap",
                                text_overflow="ellipsis",
                            ),
                            padding="8px 12px",
                            border_radius=S.R_CONTROL,
                            bg="rgba(201,139,42,0.03)",
                            border=f"1px solid {S.BORDER_ACCENT}",
                            width="100%",
                            align="center",
                            spacing="2",
                            margin_top="10px",
                        ),
                    ),
                    width="100%",
                ),
                **_GLASS_PANEL,
                grid_column=rx.breakpoints(initial="span 12", lg="span 8"),
                height="100%",
            ),
            # RIGHT: AI feed
            rx.box(
                _vg_ai_feed(),
                grid_column=rx.breakpoints(initial="span 12", lg="span 4"),
                height="100%",
            ),
            # Row 3: site telemetry + windy map
            rx.box(
                _vg_site_telemetry(),
                grid_column=rx.breakpoints(initial="span 12", lg="span 4"),
                height="100%",
            ),
            rx.box(
                windy_map_widget(),
                grid_column=rx.breakpoints(initial="span 12", lg="span 8"),
                height="100%",
                min_height="380px",
                border_radius="8px",
                overflow="hidden",
            ),
            columns="12",
            gap="24px",
            width="100%",
            align_items="stretch",
            class_name="animate-fade-in",
        ),
        width="100%",
        spacing="6",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════


def _dashboard_chart_card(
    title: str,
    subtitle: str,
    icon_tag: str,
    icon_color: str,
    children,
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.center(
                    rx.icon(tag=icon_tag, size=14, color=icon_color),
                    width="28px",
                    height="28px",
                    bg=f"rgba({','.join(str(int(icon_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))}, 0.12)"
                    if icon_color.startswith("#") else "rgba(255,255,255,0.06)",
                    border_radius="4px",
                    flex_shrink="0",
                ),
                rx.vstack(
                    rx.text(
                        title,
                        font_family=S.FONT_TECH,
                        font_size="0.875rem",
                        font_weight="700",
                        text_transform="uppercase",
                        color="var(--text-main)",
                        letter_spacing="0.04em",
                    ),
                    rx.text(
                        subtitle,
                        font_size="11px",
                        color=S.TEXT_MUTED,
                        font_family=S.FONT_MONO,
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
                align="center",
                margin_bottom="20px",
            ),
            children,
            width="100%",
        ),
        **_GLASS_PANEL,
        height="100%",
        min_height="300px",
    )


def _tab_dashboard() -> rx.Component:
    return rx.vstack(
        # Header
        rx.hstack(
            rx.vstack(
                rx.text(
                    "DASHBOARD DO PROJETO",
                    font_family=S.FONT_TECH,
                    font_size="1.25rem",
                    font_weight="700",
                    text_transform="uppercase",
                    color="var(--text-main)",
                    letter_spacing="0.04em",
                ),
                rx.text(
                    "Métricas consolidadas e gráficos analíticos do projeto selecionado.",
                    font_size="13px",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_BODY,
                ),
                spacing="1",
                align="start",
            ),
            width="100%",
            margin_bottom="4px",
        ),
        # 2x2 chart grid
        rx.grid(
            # 1 — Evolução do Progresso
            rx.box(
                _dashboard_chart_card(
                    "Evolução do Progresso",
                    "Avanço físico acumulado no tempo",
                    "trending-up",
                    S.PATINA,
                    rx.cond(
                        GlobalState.project_scurve_chart,
                        rx.recharts.line_chart(
                            rx.recharts.line(
                                data_key="realizado",
                                stroke=S.PATINA,
                                dot=False,
                                stroke_width=2,
                            ),
                            rx.recharts.line(
                                data_key="previsto",
                                stroke=S.TEXT_MUTED,
                                stroke_dasharray="4 3",
                                dot=False,
                                stroke_width=1.5,
                            ),
                            rx.recharts.x_axis(
                                data_key="data",
                                tick={"fontSize": 9, "fill": S.TEXT_MUTED, "fontFamily": "JetBrains Mono"},
                            ),
                            rx.recharts.y_axis(
                                unit="%",
                                tick={"fontSize": 9, "fill": S.TEXT_MUTED, "fontFamily": "JetBrains Mono"},
                                width=32,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 3",
                                stroke="rgba(255,255,255,0.04)",
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "background": "rgba(8,18,16,0.96)",
                                    "border": f"1px solid {S.BORDER_ACCENT}",
                                    "borderRadius": "6px",
                                    "fontSize": "11px",
                                },
                            ),
                            data=GlobalState.project_scurve_chart,
                            height=180,
                            width="100%",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="line-chart", size=32, color=S.BORDER_SUBTLE),
                                rx.text("Sem dados de progresso", font_size="12px", color=S.TEXT_MUTED),
                                spacing="2",
                                align="center",
                            ),
                            height="180px",
                        ),
                    ),
                ),
                grid_column=rx.breakpoints(initial="span 2", lg="span 1"),
            ),
            # 2 — Distribuição Financeira
            rx.box(
                _dashboard_chart_card(
                    "Distribuição Financeira",
                    "Orçamento planejado vs realizado",
                    "pie-chart",
                    S.COPPER,
                    rx.cond(
                        GlobalState.obra_budget_chart,
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="planejado",
                                fill=S.TEXT_MUTED,
                                fill_opacity=0.4,
                                radius=2,
                                name="Planejado",
                            ),
                            rx.recharts.bar(
                                data_key="realizado",
                                fill=S.COPPER,
                                fill_opacity=0.85,
                                radius=2,
                                name="Realizado",
                            ),
                            rx.recharts.x_axis(
                                data_key="label",
                                tick={"fontSize": 9, "fill": S.TEXT_MUTED, "fontFamily": "JetBrains Mono"},
                            ),
                            rx.recharts.y_axis(
                                tick={"fontSize": 9, "fill": S.TEXT_MUTED, "fontFamily": "JetBrains Mono"},
                                width=32,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 3",
                                stroke="rgba(255,255,255,0.04)",
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "background": "rgba(8,18,16,0.96)",
                                    "border": f"1px solid {S.BORDER_ACCENT}",
                                    "borderRadius": "6px",
                                    "fontSize": "11px",
                                },
                            ),
                            data=GlobalState.obra_budget_chart,
                            height=180,
                            width="100%",
                            bar_size=28,
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="pie-chart", size=32, color=S.BORDER_SUBTLE),
                                rx.text("Sem dados financeiros", font_size="12px", color=S.TEXT_MUTED),
                                spacing="2",
                                align="center",
                            ),
                            height="180px",
                        ),
                    ),
                ),
                grid_column=rx.breakpoints(initial="span 2", lg="span 1"),
            ),
            # 3 — Alocação de Equipe
            rx.box(
                _dashboard_chart_card(
                    "Alocação de Equipe",
                    "Efetivo presente vs planejado",
                    "users",
                    "#E89845",
                    rx.center(
                        rx.vstack(
                            rx.recharts.radial_bar_chart(
                                rx.recharts.radial_bar(
                                    data_key="value",
                                    fill=S.PATINA,
                                    background={"fill": "rgba(255,255,255,0.03)"},
                                    corner_radius=4,
                                    label=False,
                                ),
                                data=[
                                    {"name": "Equipe", "value": 78, "fill": S.PATINA},
                                    {"name": "Meta", "value": 100, "fill": S.BORDER_SUBTLE},
                                ],
                                inner_radius="40%",
                                outer_radius="90%",
                                height=180,
                                width=220,
                            ),
                            rx.text(
                                "78% efetivo em campo",
                                font_size="11px",
                                color=S.TEXT_MUTED,
                                font_family=S.FONT_MONO,
                            ),
                            spacing="1",
                            align="center",
                        ),
                        height="180px",
                    ),
                ),
                grid_column=rx.breakpoints(initial="span 2", lg="span 1"),
            ),
            # 4 — Cronograma vs Realizado
            rx.box(
                _dashboard_chart_card(
                    "Cronograma vs Realizado",
                    "Desvio de prazo por disciplina",
                    "calendar-clock",
                    "#3B82F6",
                    rx.cond(
                        GlobalState.disciplina_progress_chart,
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="planejado_pct",
                                fill=S.TEXT_MUTED,
                                fill_opacity=0.35,
                                name="Planejado",
                                radius=2,
                            ),
                            rx.recharts.bar(
                                data_key="realizado_pct",
                                fill=S.PATINA,
                                fill_opacity=0.8,
                                name="Realizado",
                                radius=2,
                            ),
                            rx.recharts.x_axis(
                                data_key="categoria",
                                tick={"fontSize": 8, "fill": S.TEXT_MUTED, "fontFamily": "JetBrains Mono"},
                                angle=-30,
                                text_anchor="end",
                                height=48,
                            ),
                            rx.recharts.y_axis(
                                unit="%",
                                tick={"fontSize": 9, "fill": S.TEXT_MUTED, "fontFamily": "JetBrains Mono"},
                                width=32,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 3",
                                stroke="rgba(255,255,255,0.04)",
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "background": "rgba(8,18,16,0.96)",
                                    "border": f"1px solid {S.BORDER_ACCENT}",
                                    "borderRadius": "6px",
                                    "fontSize": "11px",
                                },
                            ),
                            data=GlobalState.disciplina_progress_chart,
                            height=180,
                            width="100%",
                            bar_size=16,
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="calendar-clock", size=32, color=S.BORDER_SUBTLE),
                                rx.text("Sem dados de disciplinas", font_size="12px", color=S.TEXT_MUTED),
                                spacing="2",
                                align="center",
                            ),
                            height="180px",
                        ),
                    ),
                ),
                grid_column=rx.breakpoints(initial="span 2", lg="span 1"),
            ),
            columns=rx.breakpoints(initial="2", lg="4"),
            gap="20px",
            width="100%",
            class_name="animate-fade-in",
        ),
        width="100%",
        spacing="6",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CRONOGRAMA
# ══════════════════════════════════════════════════════════════════════════════


def _activity_row(item: dict) -> rx.Component:
    """Single row in the activity management table."""
    type_colors = {
        "Elétrica": ("#3B82F6", "rgba(59,130,246,0.12)"),
        "Civil": (S.COPPER, S.COPPER_GLOW),
        "Hidráulica": (S.PATINA, S.PATINA_GLOW),
        "Estrutural": ("#E89845", "rgba(232,152,69,0.12)"),
        "Outros": (S.TEXT_MUTED, "rgba(136,153,153,0.1)"),
    }
    # We use a fixed-color pill approach (can't do dict lookup dynamically in Reflex frontend)
    fase = item.get("fase", "Outros")
    pct = item["conclusao_pct"].to(float).to(int)

    return rx.hstack(
        # Type badge
        rx.box(
            fase,
            padding="2px 8px",
            border_radius="3px",
            bg="rgba(255,255,255,0.06)",
            border=f"1px solid {S.BORDER_SUBTLE}",
            font_size="9px",
            font_family=S.FONT_MONO,
            font_weight="700",
            color="var(--text-main)",
            text_transform="uppercase",
            white_space="nowrap",
            min_width="70px",
            text_align="center",
        ),
        # Activity name
        rx.text(
            item["atividade"],
            font_size="13px",
            font_weight="600",
            color="var(--text-main)",
            flex="1",
            min_width="0",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        ),
        # Phase
        rx.text(
            item.get("responsavel", item.get("fase", "—")),
            font_size="11px",
            color=S.TEXT_MUTED,
            font_family=S.FONT_MONO,
            display=rx.breakpoints(initial="none", md="block"),
            min_width="80px",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        ),
        # Mini progress bar + %
        rx.hstack(
            rx.box(
                rx.box(
                    height="100%",
                    bg=rx.cond(
                        item["critico"] == "Sim",
                        S.DANGER,
                        S.COPPER,
                    ),
                    width=pct.to_string() + "%",
                    border_radius="2px",
                    transition="width 1s ease-out",
                ),
                height="4px",
                bg="rgba(255,255,255,0.05)",
                border_radius="2px",
                overflow="hidden",
                width="60px",
                flex_shrink="0",
            ),
            rx.text(
                pct.to_string() + "%",
                font_size="10px",
                font_weight="700",
                color=rx.cond(item["critico"] == "Sim", S.DANGER, S.COPPER),
                font_family=S.FONT_MONO,
                min_width="32px",
                text_align="right",
            ),
            align="center",
            spacing="2",
        ),
        # Critical badge
        rx.cond(
            item["critico"] == "Sim",
            rx.hstack(
                rx.icon(tag="circle-alert", size=11, color=S.DANGER),
                rx.text(
                    "CRÍTICO",
                    font_size="9px",
                    color=S.DANGER,
                    font_family=S.FONT_MONO,
                    font_weight="700",
                    display=rx.breakpoints(initial="none", md="block"),
                ),
                spacing="1",
                align="center",
            ),
        ),
        padding="10px 14px",
        border_radius=S.R_CONTROL,
        border=f"1px solid {S.BORDER_SUBTLE}",
        bg="rgba(255,255,255,0.02)",
        _hover={"bg": "rgba(255,255,255,0.04)", "border_color": S.BORDER_ACCENT},
        transition="all 0.15s ease",
        width="100%",
        align="center",
        spacing="3",
        flex_wrap="wrap",
    )


def _gantt_real_row(item: dict) -> rx.Component:
    """
    Real Gantt row driven by GlobalState.gantt_rows data.
    Displays a horizontal progress bar sized by start/end dates relative to
    the project span. Falls back to a simple bar if dates are missing.
    Each row: label | date range | progress bar | % | responsavel
    """
    pct_val = item["pct"].to(int)
    is_critical = item["critico"] == "1"

    bar_color = rx.cond(is_critical, S.DANGER, item["color"])

    return rx.hstack(
        # Activity label
        rx.text(
            item["label"],
            font_size="11px",
            font_family=S.FONT_MONO,
            color="var(--text-main)",
            white_space="nowrap",
            overflow="hidden",
            text_overflow="ellipsis",
            width="180px",
            flex_shrink="0",
        ),
        # Phase badge
        rx.box(
            item["fase"],
            padding="1px 6px",
            border_radius="2px",
            bg="rgba(255,255,255,0.05)",
            border=f"1px solid {S.BORDER_SUBTLE}",
            font_size="9px",
            font_family=S.FONT_MONO,
            color=S.TEXT_MUTED,
            text_transform="uppercase",
            white_space="nowrap",
            width="80px",
            text_align="center",
            flex_shrink="0",
            overflow="hidden",
            text_overflow="ellipsis",
        ),
        # Date range
        rx.text(
            rx.cond(
                item["start_iso"] != "",
                item["start_iso"] + " → " + item["end_iso"],
                "—",
            ),
            font_size="10px",
            font_family=S.FONT_MONO,
            color=S.TEXT_MUTED,
            white_space="nowrap",
            width="140px",
            flex_shrink="0",
        ),
        # Progress bar + %
        rx.box(
            rx.box(
                height="100%",
                bg=bar_color,
                width=pct_val.to_string() + "%",
                border_radius="2px",
                transition="width 1s ease-out",
                position="relative",
            ),
            height="8px",
            bg="rgba(255,255,255,0.06)",
            border_radius="3px",
            overflow="hidden",
            flex="1",
            min_width="80px",
        ),
        rx.text(
            pct_val.to_string() + "%",
            font_size="10px",
            font_weight="700",
            font_family=S.FONT_MONO,
            color=rx.cond(is_critical, S.DANGER, S.COPPER),
            width="36px",
            text_align="right",
            flex_shrink="0",
        ),
        # Responsável
        rx.text(
            item["responsavel"],
            font_size="10px",
            font_family=S.FONT_MONO,
            color=S.TEXT_MUTED,
            white_space="nowrap",
            overflow="hidden",
            text_overflow="ellipsis",
            width="100px",
            flex_shrink="0",
            display=rx.breakpoints(initial="none", lg="block"),
        ),
        # Critical badge
        rx.cond(
            is_critical,
            rx.hstack(
                rx.icon(tag="circle-alert", size=11, color=S.DANGER),
                rx.text("CRÍTICO", font_size="9px", color=S.DANGER, font_family=S.FONT_MONO, font_weight="700"),
                spacing="1",
                align="center",
            ),
        ),
        padding="8px 12px",
        border_radius=S.R_CONTROL,
        border=f"1px solid {S.BORDER_SUBTLE}",
        bg="rgba(255,255,255,0.02)",
        _hover={"bg": "rgba(255,255,255,0.04)", "border_color": S.BORDER_ACCENT},
        transition="all 0.15s ease",
        width="100%",
        align="center",
        spacing="3",
        overflow="hidden",
    )


def _fase_filter_pill(fase: str) -> rx.Component:
    """Dynamic filter pill for a single fase_macro value."""
    is_active = GlobalState.projetos_fase_filter == fase
    return rx.box(
        rx.text(
            fase,
            font_size="11px",
            font_weight="700",
            color=rx.cond(is_active, S.BG_VOID, S.TEXT_MUTED),
        ),
        padding="4px 12px",
        border_radius="4px",
        cursor="pointer",
        bg=rx.cond(is_active, S.COPPER, "rgba(255,255,255,0.04)"),
        border=rx.cond(
            is_active,
            f"1px solid {S.COPPER}",
            f"1px solid {S.BORDER_SUBTLE}",
        ),
        on_click=GlobalState.set_projetos_fase_filter(fase),
        _hover={"bg": rx.cond(is_active, S.COPPER, "rgba(255,255,255,0.07)")},
        transition="all 0.18s ease",
        white_space="nowrap",
    )


def _cron_stat_badge(label: str, value, color: str) -> rx.Component:
    return rx.vstack(
        rx.text(value, font_family=S.FONT_TECH, font_size="1.4rem", font_weight="700", color=color),
        rx.text(label, font_size="9px", font_family=S.FONT_MONO, color=S.TEXT_MUTED, text_transform="uppercase", letter_spacing="0.08em"),
        spacing="0", align="center",
    )


def _cron_fase_pill(fase: str) -> rx.Component:
    is_active = HubState.cron_fase_filter == fase
    return rx.box(
        rx.text(fase, font_size="10px", font_weight="700", color=rx.cond(is_active, S.BG_VOID, S.TEXT_MUTED), white_space="nowrap"),
        padding="3px 10px", border_radius="4px", cursor="pointer",
        bg=rx.cond(is_active, S.COPPER, "rgba(255,255,255,0.04)"),
        border=rx.cond(is_active, f"1px solid {S.COPPER}", f"1px solid {S.BORDER_SUBTLE}"),
        on_click=HubState.set_cron_fase_filter(fase),
        _hover={"bg": rx.cond(is_active, S.COPPER, "rgba(255,255,255,0.07)")},
        transition="all 0.15s ease",
    )


def _cron_display_row(item: dict) -> rx.Component:
    """Unified row renderer for macro and micro activities (uses _display_mode field)."""
    is_critical = item["critico"] == "1"
    is_macro = item["_display_mode"] == "macro"
    is_micro = item["_display_mode"] == "micro"
    has_micros = item["_has_micros"] == "1"
    is_expanded = item["_is_expanded"] == "1"
    pct = item["_computed_pct"]
    is_pending = item["pendente_aprovacao"] == "1"

    # Indent micros
    indent = rx.cond(is_micro, rx.box(width="20px", flex_shrink="0"), rx.fragment())

    # Color stripe — thicker for macro, thinner for micro
    stripe_w = rx.cond(is_micro, "2px", "3px")
    stripe = rx.box(width=stripe_w, height="100%", bg=item["color"], border_radius="2px", flex_shrink="0", align_self="stretch", min_height="32px")

    # Expand toggle (only for macros with micros)
    expand_btn = rx.cond(
        is_macro & has_micros,
        rx.icon_button(
            rx.icon(tag=rx.cond(is_expanded, "chevron-down", "chevron-right"), size=11),
            size="1", variant="ghost", cursor="pointer",
            on_click=HubState.toggle_macro_expanded(item["id"]),
            color=S.TEXT_MUTED,
            _hover={"color": S.COPPER},
            flex_shrink="0",
        ),
        rx.box(width="20px", flex_shrink="0"),  # spacer to keep alignment
    )

    # Peso badge for micros
    peso_badge = rx.cond(
        is_micro,
        rx.box(
            rx.text(item["peso_pct"] + "%", font_size="8px", font_weight="700", color=item["color"], font_family=S.FONT_MONO),
            padding="1px 5px", border_radius="3px", bg="rgba(255,255,255,0.05)",
            border=f"1px solid rgba(255,255,255,0.1)", flex_shrink="0",
        ),
        rx.fragment(),
    )

    # Pending badge
    pending_badge = rx.cond(
        is_pending,
        rx.box(
            rx.text("PENDENTE", font_size="7px", font_weight="800", color="#E89845", font_family=S.FONT_TECH, letter_spacing="0.06em"),
            padding="1px 5px", border_radius="3px",
            border="1px solid rgba(232,152,69,0.5)", bg="rgba(232,152,69,0.08)", flex_shrink="0",
        ),
        rx.fragment(),
    )

    # Micro count badge for macros with children
    micro_count_badge = rx.cond(
        is_macro & has_micros,
        rx.box(
            rx.text(item["_micro_count"] + " sub", font_size="8px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
            padding="1px 5px", border_radius="3px", bg="rgba(255,255,255,0.04)",
            border=f"1px solid {S.BORDER_SUBTLE}", flex_shrink="0",
        ),
        rx.fragment(),
    )

    # Add micro button (only for macros)
    add_micro_btn = rx.cond(
        is_macro,
        rx.icon_button(
            rx.icon(tag="plus", size=10),
            size="1", variant="ghost", cursor="pointer",
            on_click=lambda: HubState.open_cron_new(item["id"]),
            title="Adicionar sub-atividade",
            color=S.TEXT_MUTED,
            _hover={"color": S.COPPER, "bg": "rgba(201,139,42,0.1)"},
            flex_shrink="0",
        ),
        rx.fragment(),
    )

    font_sz = rx.cond(is_micro, "12px", "13px")
    font_w = rx.cond(is_micro, "500", "600")

    return rx.hstack(
        indent,
        expand_btn,
        stripe,
        # Name + fase
        rx.vstack(
            rx.hstack(
                rx.cond(is_critical, rx.icon(tag="circle-alert", size=11, color=S.DANGER)),
                rx.text(item["atividade"], font_size=font_sz, font_weight=font_w, color="var(--text-main)", font_family=S.FONT_TECH, letter_spacing="0.01em"),
                peso_badge,
                pending_badge,
                micro_count_badge,
                spacing="1", align="center",
            ),
            rx.hstack(
                rx.text(item["fase_macro"], font_size="9px", color=item["color"], font_family=S.FONT_MONO, font_weight="700"),
                rx.text("·", font_size="9px", color=S.TEXT_MUTED),
                rx.text(item["fase"], font_size="9px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                spacing="1", align="center",
            ),
            spacing="0", flex="1", min_width="0",
        ),
        # Responsável
        rx.text(item["responsavel"], font_size="10px", font_family=S.FONT_MONO, color=S.TEXT_MUTED, white_space="nowrap", overflow="hidden", text_overflow="ellipsis", width="90px", flex_shrink="0", display=rx.breakpoints(initial="none", lg="block")),
        # Datas
        rx.vstack(
            rx.text(item["inicio_previsto"], font_size="9px", color=S.TEXT_MUTED, font_family=S.FONT_MONO, white_space="nowrap"),
            rx.text(item["termino_previsto"], font_size="9px", color=S.TEXT_MUTED, font_family=S.FONT_MONO, white_space="nowrap"),
            spacing="0", flex_shrink="0", display=rx.breakpoints(initial="none", md="block"),
        ),
        # Progress bar + pct
        rx.vstack(
            rx.box(
                rx.box(width=pct + "%", height="100%", bg=rx.cond(is_critical, S.DANGER, S.COPPER), border_radius="2px", transition="width 0.4s ease"),
                width="80px", height="4px", bg="rgba(255,255,255,0.08)", border_radius="2px", overflow="hidden",
            ),
            rx.text(pct + "%", font_size="10px", color=rx.cond(is_critical, S.DANGER, S.COPPER), font_family=S.FONT_MONO, font_weight="700", text_align="center"),
            spacing="1", align="center", flex_shrink="0",
        ),
        # Actions
        rx.hstack(
            add_micro_btn,
            rx.icon_button(rx.icon(tag="pencil", size=12), size="1", variant="ghost", on_click=HubState.open_cron_edit(item["id"]), cursor="pointer", _hover={"bg": "rgba(201,139,42,0.15)"}),
            rx.icon_button(rx.icon(tag="trash-2", size=12, color=S.DANGER), size="1", variant="ghost", on_click=HubState.request_cron_delete(item["id"]), cursor="pointer", _hover={"bg": "rgba(239,68,68,0.12)"}),
            spacing="1", flex_shrink="0",
        ),
        padding=rx.cond(is_micro, "7px 14px 7px 4px", "10px 14px"),
        border_radius=S.R_CONTROL,
        border=rx.cond(is_micro, f"1px solid rgba(255,255,255,0.04)", f"1px solid {S.BORDER_SUBTLE}"),
        bg=rx.cond(is_critical, "rgba(239,68,68,0.04)", rx.cond(is_micro, "rgba(255,255,255,0.015)", "rgba(255,255,255,0.02)")),
        _hover={"bg": rx.cond(is_critical, "rgba(239,68,68,0.07)", "rgba(255,255,255,0.04)"), "border_color": S.BORDER_ACCENT},
        transition="all 0.15s ease",
        width="100%", align="center", spacing="2", overflow="hidden",
        margin_left=rx.cond(is_micro, "12px", "0px"),
    )


def _cron_edit_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag=rx.cond(HubState.cron_edit_id == "", "circle-plus", "pencil"), size=16, color=S.COPPER),
                    rx.dialog.title(
                        rx.cond(HubState.cron_edit_id == "", "Nova Atividade", "Editar Atividade"),
                        font_family=S.FONT_TECH, font_size="1rem", font_weight="700", color="var(--text-main)",
                    ),
                    rx.spacer(),
                    rx.dialog.close(rx.icon_button(rx.icon(tag="x", size=14), size="1", variant="ghost", cursor="pointer")),
                    align="center", width="100%",
                ),
                rx.divider(border_color=S.BORDER_SUBTLE),
                # Row 1: Atividade + Responsável
                # Note: text inputs use default_value + on_blur (uncontrolled) to avoid
                # per-keystroke round-trips to the server that cause input lag.
                # Date/number inputs keep on_change (they don't have the lag problem).
                rx.flex(
                    rx.vstack(rx.text("Atividade *", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(default_value=HubState.cron_edit_atividade, on_blur=HubState.set_cron_edit_atividade, placeholder="Nome da atividade", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"14px","width":"100%","outline":"none"}), spacing="1", flex="1"),
                    rx.vstack(rx.text("Responsável", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(default_value=HubState.cron_edit_responsavel, on_blur=HubState.set_cron_edit_responsavel, placeholder="Ex: Engenheiro A", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"14px","width":"100%","outline":"none"}), spacing="1", flex="1"),
                    gap="12px", flex_wrap="wrap",
                ),
                # Row 2: Fase Macro + Fase
                rx.flex(
                    rx.vstack(rx.text("Fase Macro", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(default_value=HubState.cron_edit_fase_macro, on_blur=HubState.set_cron_edit_fase_macro, placeholder="Ex: Elétrica", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"14px","width":"100%","outline":"none"}), spacing="1", flex="1"),
                    rx.vstack(rx.text("Fase", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(default_value=HubState.cron_edit_fase, on_blur=HubState.set_cron_edit_fase, placeholder="Ex: SPDA", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"14px","width":"100%","outline":"none"}), spacing="1", flex="1"),
                    gap="12px", flex_wrap="wrap",
                ),
                # Row 3: Datas
                rx.flex(
                    rx.vstack(rx.text("Início Previsto", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(type="date", value=HubState.cron_edit_inicio, on_change=HubState.set_cron_edit_inicio, style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"13px","width":"100%","outline":"none","colorScheme":"dark"}), spacing="1", flex="1"),
                    rx.vstack(rx.text("Término Previsto", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(type="date", value=HubState.cron_edit_termino, on_change=HubState.set_cron_edit_termino, style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"13px","width":"100%","outline":"none","colorScheme":"dark"}), spacing="1", flex="1"),
                    gap="12px", flex_wrap="wrap",
                ),
                # Row 4a: Tipo (macro/micro) + Macro Pai
                rx.flex(
                    rx.vstack(
                        rx.text("Tipo", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                        rx.select.root(
                            rx.select.trigger(style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","fontSize":"13px","width":"140px","outline":"none"}),
                            rx.select.content(
                                rx.select.item("Macro (Principal)", value="macro"),
                                rx.select.item("Micro (Sub-atividade)", value="micro"),
                                style={"background": S.BG_ELEVATED, "border": f"1px solid {S.BORDER_SUBTLE}"},
                            ),
                            value=HubState.cron_edit_nivel,
                            on_change=HubState.set_cron_edit_nivel,
                        ),
                        spacing="1",
                    ),
                    rx.cond(
                        HubState.cron_edit_nivel == "micro",
                        rx.vstack(
                            rx.text("Macro Pai *", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                            rx.cond(
                                HubState.cron_parent_options.length() > 0,
                                rx.select.root(
                                    rx.select.trigger(placeholder="Selecionar macro...", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","fontSize":"13px","width":"200px","outline":"none"}),
                                    rx.select.content(
                                        rx.foreach(
                                            HubState.cron_parent_options,
                                            lambda opt: rx.select.item(opt["label"], value=opt["id"]),
                                        ),
                                        style={"background": S.BG_ELEVATED, "border": f"1px solid {S.BORDER_SUBTLE}"},
                                    ),
                                    value=HubState.cron_edit_parent_id,
                                    on_change=HubState.set_cron_edit_parent_id,
                                ),
                                rx.text("Crie uma atividade macro primeiro", font_size="11px", color=S.TEXT_MUTED, font_style="italic"),
                            ),
                            spacing="1", flex="1",
                        ),
                        rx.fragment(),
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.text("Peso %", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                            rx.spacer(),
                            rx.box(
                                rx.el.input(
                                    type="number",
                                    value=HubState.cron_edit_peso,
                                    on_change=HubState.set_cron_edit_peso,
                                    min="1", max="100",
                                    style={"background":"transparent","border":"none","color":S.COPPER,"padding":"0","fontSize":"13px","width":"42px","outline":"none","textAlign":"right","fontWeight":"700","fontFamily":S.FONT_MONO},
                                ),
                                rx.text("%", font_size="12px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                                display="flex", align_items="center", gap="2px",
                            ),
                            width="100%", align="center",
                        ),
                        rx.el.input(
                            type="range",
                            value=HubState.cron_edit_peso,
                            on_change=HubState.set_cron_edit_peso,
                            min="1", max="100", step="1",
                            style={
                                "width": "100%",
                                "height": "4px",
                                "accentColor": S.COPPER,
                                "cursor": "pointer",
                                "outline": "none",
                                "background": f"linear-gradient(to right, {S.COPPER} 0%, {S.COPPER} {HubState.cron_edit_peso}%, rgba(255,255,255,0.1) {HubState.cron_edit_peso}%, rgba(255,255,255,0.1) 100%)",
                            },
                        ),
                        spacing="1",
                        min_width="160px",
                        flex="1",
                    ),
                    gap="12px", flex_wrap="wrap", align="start",
                ),
                # Row 4b: Progresso + Crítico
                rx.hstack(
                    rx.vstack(rx.text("Conclusão %", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                              rx.el.input(type="number", value=HubState.cron_edit_pct, on_change=HubState.set_cron_edit_pct, min="0", max="100", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"13px","width":"120px","outline":"none"}), spacing="1"),
                    rx.hstack(
                        rx.checkbox(checked=HubState.cron_edit_critico, on_change=HubState.toggle_cron_edit_critico, color_scheme="red"),
                        rx.text("Atividade Crítica", font_size="12px", color=rx.cond(HubState.cron_edit_critico, S.DANGER, S.TEXT_MUTED)),
                        spacing="2", align="center", margin_top="18px",
                    ),
                    align="end", spacing="6",
                ),
                # Row 5: Dependência + Observações
                rx.vstack(
                    rx.text("Dependência", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                    rx.cond(
                        HubState.cron_activity_options.length() > 0,
                        rx.select.root(
                            rx.select.trigger(
                                placeholder="— Sem dependência —",
                                style={"background": "rgba(14,26,23,0.8)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "padding": "8px 10px", "fontSize": "13px", "width": "100%", "outline": "none"},
                            ),
                            rx.select.content(
                                rx.select.item("— Sem dependência —", value="__none__"),
                                rx.foreach(
                                    HubState.cron_activity_options,
                                    lambda name: rx.select.item(name, value=name),
                                ),
                                style={"background": S.BG_ELEVATED, "border": f"1px solid {S.BORDER_SUBTLE}"},
                            ),
                            value=rx.cond(HubState.cron_edit_dependencia == "", "__none__", HubState.cron_edit_dependencia),
                            on_change=HubState.set_cron_edit_dependencia,
                        ),
                        rx.text("Nenhuma atividade criada ainda", font_size="11px", color=S.TEXT_MUTED, font_style="italic"),
                    ),
                    spacing="1", width="100%",
                ),
                rx.vstack(rx.text("Observações", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                          rx.el.textarea(default_value=HubState.cron_edit_observacoes, on_blur=HubState.set_cron_edit_observacoes, placeholder="Notas técnicas, impedimentos, contexto...", rows="3", style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"13px","width":"100%","outline":"none","resize":"vertical","fontFamily":S.FONT_BODY}), spacing="1", width="100%"),
                # Error
                rx.cond(HubState.cron_error != "", rx.text(HubState.cron_error, font_size="12px", color=S.DANGER)),
                # Footer
                rx.hstack(
                    rx.dialog.close(rx.button("Cancelar", variant="ghost", size="2", color=S.TEXT_MUTED, cursor="pointer", on_click=HubState.close_cron_dialog)),
                    rx.button(
                        rx.cond(HubState.cron_saving, rx.spinner(size="2"), rx.hstack(rx.icon(tag="save", size=13), rx.text("Salvar"), spacing="1", align="center")),
                        on_click=HubState.save_cron_activity, size="2", disabled=HubState.cron_saving,
                        style={"background": S.COPPER, "color": S.BG_VOID, "fontFamily": S.FONT_TECH, "fontWeight": "700", "cursor": "pointer"},
                    ),
                    justify="end", spacing="2", width="100%", padding_top="8px",
                ),
                spacing="4", width="100%",
            ),
            bg=S.BG_ELEVATED, border=f"1px solid {S.BORDER_SUBTLE}", border_radius=S.R_CARD,
            max_width="600px", width="95vw",
        ),
        open=HubState.cron_show_dialog,
        on_open_change=HubState.set_cron_show_dialog,
    )


def _cron_delete_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="trash-2", size=16, color=S.DANGER),
                    rx.dialog.title("Excluir Atividade", font_family=S.FONT_TECH, font_weight="700", color="var(--text-main)"),
                    spacing="2", align="center",
                ),
                rx.text("Tem certeza que deseja excluir a atividade:", font_size="13px", color=S.TEXT_MUTED),
                rx.text(HubState.cron_delete_name, font_size="13px", font_weight="700", color=S.DANGER),
                rx.text("Esta ação não pode ser desfeita.", font_size="11px", color=S.TEXT_MUTED),
                rx.hstack(
                    rx.button("Cancelar", variant="ghost", size="2", cursor="pointer", on_click=HubState.cancel_cron_delete),
                    rx.button(rx.hstack(rx.icon(tag="trash-2", size=13), rx.text("Excluir"), spacing="1"), on_click=HubState.confirm_cron_delete, size="2", style={"background": S.DANGER, "color": "white", "cursor": "pointer"}),
                    justify="end", spacing="2", width="100%",
                ),
                spacing="3", width="100%",
            ),
            bg=S.BG_ELEVATED, border=f"1px solid rgba(239,68,68,0.3)", border_radius=S.R_CARD, max_width="420px", width="90vw",
        ),
        open=HubState.cron_show_delete,
    )


def _gantt_bar(item: dict) -> rx.Component:
    """Single Gantt row: label + date-positioned bar with progress fill + badges."""
    # Bar color: overdue → red, else activity color
    bar_color = rx.cond(item["gantt_overdue"] == "1", "#EF4444", item["color"])
    progress_fill = rx.cond(
        item["conclusao_pct"] == "0",
        rx.fragment(),
        rx.box(
            height="100%",
            width=item["conclusao_pct"] + "%",
            bg=bar_color,
            border_radius="3px 0 0 3px",
            opacity="0.85",
        ),
    )
    overdue_badge = rx.cond(
        item["gantt_overdue"] == "1",
        rx.box(
            rx.text("ATRASADA", font_size="7px", font_weight="800", color="#EF4444", font_family=S.FONT_TECH, letter_spacing="0.06em"),
            padding="1px 4px", border_radius="2px",
            border="1px solid rgba(239,68,68,0.5)", bg="rgba(239,68,68,0.08)",
            flex_shrink="0",
        ),
        rx.fragment(),
    )
    critical_badge = rx.cond(
        item["critico"] == "1",
        rx.box(
            rx.text("CRÍTICO", font_size="7px", font_weight="800", color="#E89845", font_family=S.FONT_TECH, letter_spacing="0.06em"),
            padding="1px 4px", border_radius="2px",
            border="1px solid rgba(232,152,69,0.5)", bg="rgba(232,152,69,0.08)",
            flex_shrink="0",
        ),
        rx.fragment(),
    )
    dep_text = rx.cond(
        item["dependencia"] != "",
        rx.hstack(
            rx.icon(tag="arrow-right", size=9, color=S.TEXT_MUTED),
            rx.text(item["dependencia"], font_size="8px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
            spacing="1", align="center",
        ),
        rx.fragment(),
    )
    return rx.box(
        rx.hstack(
            # Label column
            rx.vstack(
                rx.hstack(
                    rx.text(
                        item["atividade"],
                        font_size="11px", color="rgba(255,255,255,0.85)",
                        white_space="nowrap", overflow="hidden", text_overflow="ellipsis",
                        max_width="100%",
                    ),
                    rx.hstack(overdue_badge, critical_badge, spacing="1"),
                    spacing="2", align="center", width="100%",
                ),
                rx.hstack(
                    rx.text(item["fase_macro"], font_size="9px", color=item["color"], font_weight="600"),
                    rx.text("·", font_size="9px", color=S.TEXT_MUTED),
                    rx.text(item["responsavel"], font_size="9px", color=S.TEXT_MUTED),
                    dep_text,
                    spacing="1", align="center",
                ),
                spacing="0", align_items="flex-start", width="160px", flex_shrink="0",
            ),
            # Timeline track
            rx.box(
                # Outer track
                rx.box(
                    # Positioned bar container
                    rx.box(
                        # Background track
                        rx.box(
                            # Progress fill
                            progress_fill,
                            height="100%",
                            bg="rgba(255,255,255,0.06)",
                            border_radius="3px",
                            overflow="hidden",
                            position="relative",
                        ),
                        position="absolute",
                        left=item["gantt_left_pct"] + "%",
                        width=item["gantt_width_pct"] + "%",
                        height="22px",
                        top="0",
                        border=rx.cond(
                            item["gantt_overdue"] == "1",
                            "1px solid rgba(239,68,68,0.4)",
                            f"1px solid {item['color']}44",
                        ),
                        border_radius="3px",
                        min_width="8px",
                    ),
                    # Today marker
                    rx.box(
                        position="absolute",
                        left="0%",  # We can't compute today% in component; use CSS trick
                        width="1px",
                        height="100%",
                        bg="rgba(201,139,42,0.4)",
                        top="0",
                        display="none",  # hidden for now; would need server-side today_pct
                    ),
                    position="relative", height="22px", width="100%",
                ),
                flex="1", overflow="hidden",
            ),
            # End date
            rx.text(
                item["termino_previsto"],
                font_size="9px", color=S.TEXT_MUTED, font_family=S.FONT_MONO,
                white_space="nowrap", flex_shrink="0", width="65px", text_align="right",
            ),
            spacing="3", align="center", width="100%",
        ),
        padding="6px 0",
        border_bottom=f"1px solid {S.BORDER_SUBTLE}22",
        _last={"borderBottom": "none"},
    )


def _gantt_premium() -> rx.Component:
    """Premium scrollable Gantt chart with date-positioned bars, weather badges, IA button."""
    return rx.box(
        rx.vstack(
            # ── Header ─────────────────────────────────────────────────────────
            rx.hstack(
                rx.hstack(
                    rx.icon(tag="gantt-chart", size=14, color=S.COPPER),
                    rx.text("GANTT", font_family=S.FONT_TECH, font_size="11px", font_weight="700", color=S.COPPER, letter_spacing="0.10em"),
                    rx.box(width="1px", height="14px", bg=S.BORDER_SUBTLE),
                    rx.text(HubState.gantt_date_range["start"], font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                    rx.icon(tag="arrow-right", size=10, color=S.TEXT_MUTED),
                    rx.text(HubState.gantt_date_range["end"], font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                    spacing="2", align="center",
                ),
                rx.spacer(),
                # IA Climate Analysis button
                rx.cond(
                    HubState.cron_climate_loading,
                    rx.hstack(
                        rx.spinner(size="1"),
                        rx.text("Analisando...", font_size="11px", color=S.TEXT_MUTED),
                        spacing="2", align="center",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="cloud-rain", size=12),
                            rx.text("Analisar Impacto Climático", font_size="11px"),
                            spacing="1", align="center",
                        ),
                        on_click=HubState.analyze_climate_impact,
                        size="1", variant="soft",
                        style={
                            "background": "rgba(42,157,143,0.12)",
                            "border": "1px solid rgba(42,157,143,0.3)",
                            "color": S.PATINA,
                            "cursor": "pointer",
                            "fontFamily": S.FONT_TECH,
                            "fontWeight": "600",
                        },
                    ),
                ),
                width="100%", align="center",
            ),
            # ── Legend ─────────────────────────────────────────────────────────
            rx.hstack(
                rx.hstack(
                    rx.box(width="24px", height="8px", bg=S.COPPER, border_radius="2px", opacity="0.7"),
                    rx.text("Progresso", font_size="9px", color=S.TEXT_MUTED),
                    spacing="1", align="center",
                ),
                rx.hstack(
                    rx.box(width="24px", height="8px", bg="#EF4444", border_radius="2px", opacity="0.7"),
                    rx.text("Atrasada", font_size="9px", color=S.TEXT_MUTED),
                    spacing="1", align="center",
                ),
                rx.hstack(
                    rx.box(width="24px", height="8px", bg="rgba(255,255,255,0.06)", border="1px solid rgba(255,255,255,0.15)", border_radius="2px"),
                    rx.text("Planejado", font_size="9px", color=S.TEXT_MUTED),
                    spacing="1", align="center",
                ),
                spacing="4", flex_wrap="wrap",
            ),
            # ── Bars ───────────────────────────────────────────────────────────
            rx.box(
                rx.foreach(HubState.gantt_rows, _gantt_bar),
                width="100%",
            ),
            spacing="3", width="100%",
        ),
        padding="16px 20px", border_radius=S.R_CARD,
        border=f"1px solid {S.BORDER_SUBTLE}", bg="rgba(255,255,255,0.02)",
        width="100%",
    )


def _climate_analysis_panel() -> rx.Component:
    """Displays the IA climate impact analysis result."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="cloud-rain", size=14, color=S.PATINA),
                rx.text("ANÁLISE DE IMPACTO CLIMÁTICO", font_family=S.FONT_TECH, font_size="11px", font_weight="700", color=S.PATINA, letter_spacing="0.08em"),
                rx.spacer(),
                rx.icon(
                    tag="x", size=14, color=S.TEXT_MUTED, cursor="pointer",
                    on_click=HubState.clear_climate_analysis,
                    _hover={"color": "white"},
                ),
                width="100%", align="center",
            ),
            rx.box(
                rx.text(
                    HubState.cron_climate_analysis,
                    font_size="13px", color="rgba(255,255,255,0.85)",
                    line_height="1.65", white_space="pre-wrap",
                ),
                padding="12px 16px",
                border_radius=S.R_CONTROL,
                bg="rgba(42,157,143,0.06)",
                border=f"1px solid rgba(42,157,143,0.15)",
                width="100%",
            ),
            rx.hstack(
                rx.icon(tag="bot", size=10, color=S.TEXT_MUTED),
                rx.text("Gerado por Bomtempo Intelligence · baseado na previsão atual do tempo", font_size="9px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                spacing="1", align="center",
            ),
            spacing="3", width="100%",
        ),
        padding="16px 20px", border_radius=S.R_CARD,
        border=f"1px solid rgba(42,157,143,0.2)", bg="rgba(42,157,143,0.04)",
        width="100%",
    )


def _tab_cronograma() -> rx.Component:
    return rx.vstack(
        _cron_edit_dialog(),
        _cron_delete_dialog(),
        # ── Stats strip ──────────────────────────────────────────────────────────
        rx.hstack(
            _cron_stat_badge("Total", HubState.cron_stats["total"], S.COPPER),
            rx.box(width="1px", height="40px", bg=S.BORDER_SUBTLE),
            _cron_stat_badge("Concluídas", HubState.cron_stats["done"], S.PATINA),
            rx.box(width="1px", height="40px", bg=S.BORDER_SUBTLE),
            _cron_stat_badge("Críticas", HubState.cron_stats["critical"], S.DANGER),
            rx.box(width="1px", height="40px", bg=S.BORDER_SUBTLE),
            _cron_stat_badge("Progresso", HubState.cron_stats["pct"] + "%", "#A855F7"),
            rx.spacer(),
            rx.button(
                rx.hstack(rx.icon(tag="plus", size=13), rx.text("Nova Atividade"), spacing="1", align="center"),
                on_click=HubState.open_cron_new_root, size="2",
                style={"background": S.COPPER, "color": S.BG_VOID, "fontFamily": S.FONT_TECH, "fontWeight": "700", "cursor": "pointer"},
            ),
            padding="14px 20px", border_radius=S.R_CARD,
            bg="rgba(255,255,255,0.03)", border=f"1px solid {S.BORDER_SUBTLE}",
            width="100%", align="center",
        ),
        # ── Toolbar: search + filters ─────────────────────────────────────────
        rx.hstack(
            rx.hstack(
                rx.icon(tag="search", size=14, color=S.TEXT_MUTED),
                rx.el.input(
                    value=HubState.cron_search,
                    on_change=HubState.set_cron_search,
                    placeholder="Buscar atividade, responsável, fase...",
                    style={"background": "transparent", "border": "none", "color": "white", "fontSize": "13px", "outline": "none", "flex": "1", "minWidth": "180px"},
                ),
                padding="8px 12px", border_radius=S.R_CONTROL,
                border=f"1px solid {S.BORDER_SUBTLE}",
                bg="rgba(255,255,255,0.02)", flex="1", align="center",
            ),
            rx.hstack(
                rx.box(
                    rx.text("Todos", font_size="10px", font_weight="700", color=rx.cond(HubState.cron_fase_filter == "", S.BG_VOID, S.TEXT_MUTED), white_space="nowrap"),
                    padding="3px 10px", border_radius="4px", cursor="pointer",
                    bg=rx.cond(HubState.cron_fase_filter == "", S.COPPER, "rgba(255,255,255,0.04)"),
                    border=rx.cond(HubState.cron_fase_filter == "", f"1px solid {S.COPPER}", f"1px solid {S.BORDER_SUBTLE}"),
                    on_click=HubState.set_cron_fase_filter(""),
                    _hover={"bg": rx.cond(HubState.cron_fase_filter == "", S.COPPER, "rgba(255,255,255,0.07)")},
                    transition="all 0.15s ease",
                ),
                rx.foreach(HubState.cron_unique_fases, _cron_fase_pill),
                spacing="1", flex_wrap="wrap", align="center",
            ),
            rx.hstack(
                rx.checkbox(checked=HubState.cron_show_only_critical, on_change=lambda _: HubState.toggle_cron_critical(), color_scheme="red"),
                rx.text("Só críticas", font_size="11px", color=rx.cond(HubState.cron_show_only_critical, S.DANGER, S.TEXT_MUTED)),
                spacing="2", align="center",
            ),
            width="100%", align="center", flex_wrap="wrap", gap="10px",
        ),
        # ── Pending approval panel (gestor only) ─────────────────────────────
        rx.cond(
            HubState.cron_pending_rows.length() > 0,
            rx.box(
                rx.hstack(
                    rx.icon(tag="clock", size=14, color="#E89845"),
                    rx.text("ATIVIDADES PENDENTES DE APROVAÇÃO", font_size="11px", font_weight="700", color="#E89845", font_family=S.FONT_TECH, letter_spacing="0.06em"),
                    rx.text(HubState.cron_pending_rows.length(), font_size="10px", color="#E89845", font_family=S.FONT_MONO),
                    spacing="2", align="center",
                ),
                rx.vstack(
                    rx.foreach(
                        HubState.cron_pending_rows,
                        lambda row: rx.hstack(
                            rx.box(width="3px", height="100%", bg="#E89845", border_radius="2px", align_self="stretch", flex_shrink="0"),
                            rx.vstack(
                                rx.text(row["atividade"], font_size="12px", font_weight="600", color="white", font_family=S.FONT_TECH),
                                rx.text(row["responsavel"] + " · " + row["fase_macro"], font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                                spacing="0",
                            ),
                            rx.spacer(),
                            rx.hstack(
                                rx.button(
                                    rx.hstack(rx.icon(tag="check", size=11), rx.text("Aprovar"), spacing="1"),
                                    on_click=HubState.approve_pending_activity(row["id"]),
                                    size="1", style={"background": "#22c55e", "color": "white", "cursor": "pointer"},
                                    disabled=HubState.cron_approve_loading,
                                ),
                                rx.button(
                                    rx.hstack(rx.icon(tag="x", size=11), rx.text("Rejeitar"), spacing="1"),
                                    on_click=HubState.reject_pending_activity(row["id"]),
                                    size="1", variant="ghost", style={"color": S.DANGER, "cursor": "pointer", "border": f"1px solid {S.DANGER}"},
                                    disabled=HubState.cron_approve_loading,
                                ),
                                spacing="2",
                            ),
                            padding="8px 12px", border_radius=S.R_CONTROL,
                            bg="rgba(232,152,69,0.05)", border="1px solid rgba(232,152,69,0.2)",
                            width="100%", align="center", spacing="3",
                        ),
                    ),
                    spacing="2", width="100%", padding_top="8px",
                ),
                padding="14px 16px", border_radius=S.R_CARD,
                border="1px solid rgba(232,152,69,0.3)", bg="rgba(232,152,69,0.04)",
                width="100%",
            ),
        ),
        # ── Activity list ─────────────────────────────────────────────────────
        rx.cond(
            HubState.cron_loading,
            rx.center(rx.vstack(rx.spinner(size="3"), rx.text("Carregando atividades...", font_size="12px", color=S.TEXT_MUTED), spacing="2", align="center"), padding="40px"),
            rx.cond(
                HubState.cron_display_rows.length() == 0,
                rx.center(
                    rx.vstack(
                        rx.icon(tag="calendar-off", size=32, color=S.BORDER_SUBTLE),
                        rx.text("Nenhuma atividade encontrada", font_size="13px", color=S.TEXT_MUTED),
                        rx.text("Clique em 'Nova Atividade' para começar", font_size="11px", color=S.TEXT_MUTED, opacity="0.7"),
                        rx.button(
                            rx.hstack(rx.icon(tag="plus", size=13), rx.text("Criar Primeira Atividade"), spacing="1"),
                            on_click=HubState.open_cron_new_root, size="2", variant="soft",
                            style={"cursor": "pointer", "marginTop": "8px"},
                        ),
                        spacing="2", align="center",
                    ), padding="40px",
                ),
                rx.vstack(
                    rx.foreach(HubState.cron_display_rows, _cron_display_row),
                    spacing="1", width="100%",
                ),
            ),
        ),
        # ── Gantt Premium ─────────────────────────────────────────────────────
        rx.cond(
            HubState.cron_rows.length() > 0,
            _gantt_premium(),
        ),
        # ── IA Climate Analysis Panel ─────────────────────────────────────────
        rx.cond(
            HubState.cron_climate_analysis != "",
            _climate_analysis_panel(),
        ),
        spacing="4", width="100%", class_name="animate-fade-in",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AUDITORIA DE IMAGENS
# ══════════════════════════════════════════════════════════════════════════════


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'R, G, B' string for rgba()."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r}, {g}, {b}"
    return "255, 255, 255"


def _audit_thumb(img: dict) -> rx.Component:
    return rx.box(
        rx.box(
            rx.image(src=img["url"], width="100%", height="100%", object_fit="cover", border_radius="4px"),
            position="absolute", inset="0", overflow="hidden", border_radius="6px",
        ),
        rx.box(
            rx.vstack(
                rx.text(img["legenda"], font_size="10px", color="white", font_family=S.FONT_BODY, line_height="1.3", overflow="hidden", text_overflow="ellipsis", display="-webkit-box", style={"WebkitLineClamp": "2", "WebkitBoxOrient": "vertical"}),
                rx.hstack(
                    rx.icon(tag="calendar", size=9, color="rgba(255,255,255,0.6)"),
                    rx.text(img["data_captura"], font_size="9px", color="rgba(255,255,255,0.6)", font_family=S.FONT_MONO),
                    spacing="1", align="center",
                ),
                spacing="1",
            ),
            position="absolute", bottom="0", left="0", right="0",
            background="linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 100%)",
            padding="8px", border_radius="0 0 6px 6px",
        ),
        # Delete button (top-right)
        rx.box(
            rx.icon(tag="trash-2", size=11, color="white"),
            position="absolute", top="6px", right="6px",
            bg="rgba(239,68,68,0.7)", border_radius="4px", padding="3px",
            cursor="pointer", opacity="0",
            on_click=HubState.delete_audit_image(img["id"]),
            class_name="audit-thumb-delete",
        ),
        position="relative", width="140px", height="105px", flex_shrink="0",
        border_radius="6px", overflow="hidden", cursor="pointer",
        border=f"1px solid {S.BORDER_SUBTLE}",
        on_click=HubState.open_lightbox(img["id"]),
        _hover={"border_color": "rgba(255,255,255,0.25)", "& .audit-thumb-delete": {"opacity": "1"}},
        transition="all 0.2s ease",
    )


def _audit_lightbox() -> rx.Component:
    return rx.cond(
        HubState.audit_lightbox_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.box(
                            rx.icon(tag="x", size=18, color="white"),
                            on_click=HubState.close_lightbox,
                            cursor="pointer", padding="6px",
                            bg="rgba(255,255,255,0.1)", border_radius="6px",
                            _hover={"bg": "rgba(255,255,255,0.2)"},
                        ),
                        width="100%",
                    ),
                    rx.image(
                        src=HubState.audit_lightbox_url,
                        max_height="60vh", max_width="100%", object_fit="contain", border_radius="8px",
                    ),
                    rx.vstack(
                        rx.text(HubState.audit_lightbox_legenda, font_size="14px", color="white", font_family=S.FONT_BODY, text_align="center"),
                        rx.hstack(
                            rx.icon(tag="calendar", size=12, color="rgba(255,255,255,0.5)"),
                            rx.text(HubState.audit_lightbox_data, font_size="11px", color="rgba(255,255,255,0.5)", font_family=S.FONT_MONO),
                            rx.text("·", font_size="11px", color="rgba(255,255,255,0.3)"),
                            rx.icon(tag="user", size=12, color="rgba(255,255,255,0.5)"),
                            rx.text(HubState.audit_lightbox_autor, font_size="11px", color="rgba(255,255,255,0.5)", font_family=S.FONT_MONO),
                            spacing="2", align="center", justify="center",
                        ),
                        spacing="2", align="center",
                    ),
                    spacing="4", align="center", padding="20px", max_width="800px", width="90vw",
                ),
                bg="rgba(10,18,16,0.97)", border=f"1px solid {S.BORDER_SUBTLE}", border_radius=S.R_CARD,
            ),
            position="fixed", inset="0", bg="rgba(0,0,0,0.85)", display="flex",
            align_items="center", justify_content="center", z_index="9999",
            on_click=HubState.close_lightbox,
        ),
    )


def _audit_upload_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="upload", size=14, color=S.COPPER),
                    rx.dialog.title("Adicionar Imagem", font_family=S.FONT_TECH, font_weight="700", color="var(--text-main)"),
                    rx.spacer(),
                    rx.dialog.close(rx.icon_button(rx.icon(tag="x", size=12), size="1", variant="ghost", cursor="pointer")),
                    align="center", width="100%",
                ),
                rx.divider(border_color=S.BORDER_SUBTLE),
                rx.vstack(
                    rx.text("URL da Imagem *", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                    rx.el.input(
                        value=HubState.audit_upload_url, on_change=HubState.set_audit_upload_url,
                        placeholder="https://... ou URL do Supabase Storage",
                        style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"13px","width":"100%","outline":"none"},
                    ),
                    spacing="1", width="100%",
                ),
                rx.vstack(
                    rx.text("Legenda", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                    rx.el.input(
                        value=HubState.audit_upload_legenda, on_change=HubState.set_audit_upload_legenda,
                        placeholder="Descrição da imagem...",
                        style={"background":"rgba(14,26,23,0.8)","border":f"1px solid {S.BORDER_SUBTLE}","borderRadius":S.R_CONTROL,"color":"white","padding":"8px 10px","fontSize":"13px","width":"100%","outline":"none"},
                    ),
                    spacing="1", width="100%",
                ),
                rx.cond(HubState.audit_upload_error != "", rx.text(HubState.audit_upload_error, font_size="12px", color=S.DANGER)),
                rx.hstack(
                    rx.dialog.close(rx.button("Cancelar", variant="ghost", size="2", cursor="pointer", on_click=HubState.close_audit_upload)),
                    rx.button(
                        rx.cond(HubState.audit_uploading, rx.spinner(size="2"), rx.hstack(rx.icon(tag="upload", size=13), rx.text("Salvar"), spacing="1")),
                        on_click=HubState.save_audit_image, size="2", disabled=HubState.audit_uploading,
                        style={"background": S.COPPER, "color": S.BG_VOID, "fontFamily": S.FONT_TECH, "fontWeight": "700", "cursor": "pointer"},
                    ),
                    justify="end", spacing="2", width="100%",
                ),
                spacing="4", width="100%",
            ),
            bg=S.BG_ELEVATED, border=f"1px solid {S.BORDER_SUBTLE}", border_radius=S.R_CARD, max_width="480px", width="90vw",
        ),
        open=HubState.audit_show_upload,
    )


def _audit_bolsao_card(cat: dict) -> rx.Component:
    slug = cat["slug"]
    label = cat["label"]
    icon_tag = cat["icon"]
    color = cat["color"]
    count = HubState.audit_category_counts[slug]
    is_open = HubState.audit_open_category == slug
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.box(
                    rx.icon(tag=icon_tag, size=18, color=color),
                    width="36px", height="36px", border_radius="8px",
                    bg="rgba(255,255,255,0.06)",
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    display="flex", align_items="center", justify_content="center", flex_shrink="0",
                ),
                rx.vstack(
                    rx.text(label, font_family=S.FONT_TECH, font_size="13px", font_weight="700", color="var(--text-main)", letter_spacing="0.02em"),
                    rx.hstack(
                        rx.text(count, font_size="11px", font_weight="700", color=color),
                        rx.text("imagens", font_size="11px", color=S.TEXT_MUTED),
                        spacing="1", align="center",
                    ),
                    spacing="0", align="start",
                ),
                rx.spacer(),
                rx.icon(tag=rx.cond(is_open, "chevron-up", "chevron-down"), size=14, color=S.TEXT_MUTED),
                align="center", width="100%",
            ),
            # Image grid (visible when open)
            rx.cond(
                is_open,
                rx.vstack(
                    rx.divider(border_color=S.BORDER_SUBTLE),
                    rx.cond(
                        HubState.audit_open_images.length() == 0,
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="image-off", size=24, color=S.BORDER_SUBTLE),
                                rx.text("Nenhuma imagem neste bolsão", font_size="12px", color=S.TEXT_MUTED),
                                spacing="2", align="center",
                            ), padding="20px",
                        ),
                        rx.box(
                            rx.foreach(HubState.audit_open_images, _audit_thumb),
                            display="flex", flex_wrap="wrap", gap="10px",
                        ),
                    ),
                    rx.button(
                        rx.hstack(rx.icon(tag="plus", size=12), rx.text("Adicionar Imagem"), spacing="1"),
                        on_click=HubState.open_audit_upload(slug), size="1", variant="ghost",
                        style={"color": color, "cursor": "pointer", "border": f"1px solid {S.BORDER_SUBTLE}"},
                    ),
                    spacing="3", width="100%",
                ),
            ),
            spacing="3", width="100%",
        ),
        padding="16px 20px", border_radius=S.R_CARD,
        border=rx.cond(is_open, f"1px solid {S.BORDER_ACCENT}", f"1px solid {S.BORDER_SUBTLE}"),
        bg=rx.cond(is_open, "rgba(255,255,255,0.03)", "rgba(255,255,255,0.02)"),
        cursor="pointer", on_click=HubState.open_audit_category(slug),
        _hover={"border_color": S.BORDER_ACCENT, "bg": "rgba(255,255,255,0.03)"},
        transition="all 0.2s ease", width="100%",
    )


def _tab_auditoria() -> rx.Component:
    return rx.vstack(
        _audit_lightbox(),
        _audit_upload_dialog(),
        # Header
        rx.hstack(
            rx.hstack(
                rx.icon(tag="folder-open", size=16, color=S.COPPER),
                rx.text("GALERIA DE CAMPO", font_family=S.FONT_TECH, font_size="1rem", font_weight="700", color="var(--text-main)", letter_spacing="0.04em"),
                spacing="2", align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.icon(tag="images", size=13, color=S.TEXT_MUTED),
                rx.text(HubState.audit_images.length().to_string() + " imagens total", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                spacing="1", align="center",
            ),
            width="100%", align="center",
        ),
        rx.text("Fotos de campo integradas dos RDOs + uploads manuais, organizadas por categoria. Clique para expandir.", font_size="12px", color=S.TEXT_MUTED, font_family=S.FONT_BODY),
        rx.cond(
            HubState.audit_loading,
            rx.center(rx.vstack(rx.spinner(size="3"), rx.text("Carregando imagens...", font_size="12px", color=S.TEXT_MUTED), spacing="2", align="center"), padding="40px"),
            rx.vstack(
                rx.foreach(AUDIT_CATEGORIES, _audit_bolsao_card),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%", class_name="animate-fade-in",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — TIMELINE
# ══════════════════════════════════════════════════════════════════════════════


def _tl_type_badge(tipo: str) -> rx.Component:
    return rx.match(
        tipo,
        ("Reunião",     rx.badge("Reunião",     color_scheme="blue",   variant="soft", font_family=S.FONT_MONO, font_size="9px")),
        ("Marco",       rx.badge("Marco",       color_scheme="gold",   variant="soft", font_family=S.FONT_MONO, font_size="9px")),
        ("Falha",       rx.badge("Falha",       color_scheme="red",    variant="solid", font_family=S.FONT_MONO, font_size="9px")),
        ("Atualização", rx.badge("Atualização", color_scheme="green",  variant="soft", font_family=S.FONT_MONO, font_size="9px")),
        ("Alerta",      rx.badge("Alerta",      color_scheme="orange", variant="soft", font_family=S.FONT_MONO, font_size="9px")),
        ("Decisão",     rx.badge("Decisão",     color_scheme="purple", variant="soft", font_family=S.FONT_MONO, font_size="9px")),
        rx.badge(tipo,  color_scheme="gray",   variant="soft", font_family=S.FONT_MONO, font_size="9px"),
    )


def _tl_entry_row(entry: dict) -> rx.Component:
    return rx.hstack(
        # Timeline dot + line
        rx.vstack(
            rx.box(
                width="10px", height="10px", border_radius="50%",
                bg=rx.cond(entry["is_document"] == "1", S.PATINA, rx.cond(entry["is_cost"] == "1", S.COPPER, S.COPPER)),
                border=f"2px solid {S.BG_ELEVATED}", flex_shrink="0",
            ),
            rx.box(width="1px", flex="1", bg=S.BORDER_SUBTLE, margin_x="auto"),
            spacing="0", align="center", flex_shrink="0",
        ),
        # Content
        rx.box(
            rx.vstack(
                rx.hstack(
                    _tl_type_badge(entry["tipo"]),
                    # Document badge
                    rx.cond(
                        entry["is_document"] == "1",
                        rx.badge("DOC", color_scheme="teal", variant="solid", font_family=S.FONT_MONO, font_size="9px"),
                        rx.fragment(),
                    ),
                    # Cost badge
                    rx.cond(
                        entry["is_cost"] == "1",
                        rx.badge(
                            rx.hstack(rx.icon(tag="circle-dollar-sign", size=9), rx.text(entry["custo_categoria"]), spacing="1"),
                            color_scheme="amber", variant="soft", font_family=S.FONT_MONO, font_size="9px",
                        ),
                        rx.fragment(),
                    ),
                    rx.text(entry["titulo"], font_size="13px", font_weight="600", color="var(--text-main)", font_family=S.FONT_TECH, letter_spacing="0.01em"),
                    rx.spacer(),
                    rx.hstack(
                        rx.icon(tag="clock", size=11, color=S.TEXT_MUTED),
                        rx.text(entry["created_at"], font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                        spacing="1", align="center",
                    ),
                    rx.icon_button(rx.icon(tag="trash-2", size=11, color=S.DANGER), size="1", variant="ghost", on_click=HubState.delete_timeline_entry(entry["id"]), cursor="pointer", _hover={"bg": "rgba(239,68,68,0.1)"}),
                    spacing="2", align="center", width="100%", flex_wrap="wrap",
                ),
                rx.cond(
                    entry["descricao"] != "",
                    rx.text(entry["descricao"], font_size="12px", color=S.TEXT_MUTED, font_family=S.FONT_BODY, line_height="1.5"),
                ),
                # Cost value row
                rx.cond(
                    entry["is_cost"] == "1",
                    rx.hstack(
                        rx.icon(tag="banknote", size=11, color=S.COPPER),
                        rx.text("R$ " + entry["custo_valor"], font_size="12px", color=S.COPPER, font_family=S.FONT_MONO, font_weight="700"),
                        spacing="1", align="center",
                    ),
                    rx.fragment(),
                ),
                # Attachment
                rx.cond(
                    entry["anexo_url"] != "",
                    rx.el.a(
                        rx.hstack(
                            rx.icon(tag="paperclip", size=11, color=S.PATINA),
                            rx.text(entry["anexo_nome"], font_size="11px", color=S.PATINA, font_family=S.FONT_MONO,
                                    max_width="200px", overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
                            spacing="1", align="center",
                        ),
                        href=entry["anexo_url"], target="_blank",
                        style={"textDecoration": "none", "display": "inline-flex"},
                        _hover={"opacity": "0.8"},
                    ),
                    rx.fragment(),
                ),
                rx.hstack(
                    rx.icon(tag="user", size=10, color=S.TEXT_MUTED),
                    rx.text(entry["autor"], font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                    spacing="1", align="center",
                ),
                spacing="2", width="100%",
            ),
            padding="12px 16px", border_radius=S.R_CONTROL,
            border=rx.cond(
                entry["is_document"] == "1",
                f"1px solid rgba(42,157,143,0.3)",
                rx.cond(entry["is_cost"] == "1", f"1px solid rgba(201,139,42,0.3)", f"1px solid {S.BORDER_SUBTLE}"),
            ),
            bg="rgba(255,255,255,0.02)",
            _hover={"border_color": S.BORDER_ACCENT, "bg": "rgba(255,255,255,0.035)"},
            transition="all 0.15s ease", flex="1",
        ),
        spacing="3", align="start", width="100%",
    )


def _tl_filter_pill(tipo: str) -> rx.Component:
    is_active = HubState.tl_filter_tipo == tipo
    return rx.box(
        rx.text(tipo, font_size="10px", font_weight="700", color=rx.cond(is_active, S.BG_VOID, S.TEXT_MUTED), white_space="nowrap"),
        padding="3px 10px", border_radius="4px", cursor="pointer",
        bg=rx.cond(is_active, S.COPPER, "rgba(255,255,255,0.04)"),
        border=rx.cond(is_active, f"1px solid {S.COPPER}", f"1px solid {S.BORDER_SUBTLE}"),
        on_click=HubState.set_tl_filter_tipo(tipo),
        _hover={"bg": rx.cond(is_active, S.COPPER, "rgba(255,255,255,0.07)")},
        transition="all 0.15s ease",
    )


def _tab_timeline() -> rx.Component:
    return rx.flex(
        # ── LEFT: New entry form ──────────────────────────────────────────────
        rx.vstack(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon(tag="circle-plus", size=14, color=S.COPPER),
                        rx.text("NOVO REGISTRO", font_family=S.FONT_TECH, font_size="0.85rem", font_weight="700", color="var(--text-main)", letter_spacing="0.06em"),
                        spacing="2", align="center",
                    ),
                    # Type selector
                    rx.vstack(
                        rx.text("Tipo", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                        rx.select.root(
                            rx.select.trigger(placeholder="Tipo de registro...", style={"width": "100%", "background": "rgba(14,26,23,0.8)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "cursor": "pointer"}),
                            rx.select.content(
                                *[rx.select.item(t, value=t) for t in ENTRY_TYPES],
                                bg=S.BG_ELEVATED, border=f"1px solid {S.BORDER_SUBTLE}",
                            ),
                            value=HubState.tl_entry_type,
                            on_change=HubState.set_tl_entry_type,
                        ),
                        spacing="1", width="100%",
                    ),
                    # Título
                    rx.vstack(
                        rx.text("Título *", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                        rx.el.input(
                            default_value=HubState.tl_titulo, on_blur=HubState.set_tl_titulo,
                            placeholder="Título do registro...",
                            style={"background": "rgba(14,26,23,0.8)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "padding": "8px 10px", "fontSize": "14px", "width": "100%", "outline": "none"},
                        ),
                        spacing="1", width="100%",
                    ),
                    # Descrição
                    rx.vstack(
                        rx.hstack(
                            rx.text("Descrição", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                            rx.text("Use @username para mencionar", font_size="10px", color="rgba(201,139,42,0.6)", font_family=S.FONT_MONO),
                            justify="between", width="100%",
                        ),
                        rx.el.textarea(
                            default_value=HubState.tl_descricao, on_blur=HubState.set_tl_descricao,
                            placeholder="Detalhes, observações... Use @username para mencionar.",
                            rows="3",
                            style={"background": "rgba(14,26,23,0.8)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "padding": "8px 10px", "fontSize": "13px", "width": "100%", "outline": "none", "resize": "vertical", "fontFamily": S.FONT_BODY},
                        ),
                        # Chips de usuários disponíveis para @mention
                        rx.cond(
                            HubState.tl_mention_users.length() > 0,
                            rx.hstack(
                                rx.text("Mencionar:", font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO, flex_shrink="0"),
                                rx.flex(
                                    rx.foreach(
                                        HubState.tl_mention_users,
                                        lambda u: rx.box(
                                            rx.text("@" + u, font_size="10px", font_family=S.FONT_MONO, color=S.COPPER),
                                            padding="2px 8px",
                                            border_radius="12px",
                                            border=f"1px solid rgba(201,139,42,0.3)",
                                            bg="rgba(201,139,42,0.07)",
                                            cursor="pointer",
                                            _hover={"bg": "rgba(201,139,42,0.18)"},
                                        ),
                                    ),
                                    gap="4px",
                                    flex_wrap="wrap",
                                ),
                                spacing="2", align="start", width="100%",
                            ),
                        ),
                        spacing="1", width="100%",
                    ),
                    # ── Campos de custo (visíveis só se tipo == Custo) ────
                    rx.cond(
                        HubState.tl_entry_type == "Custo",
                        rx.hstack(
                            rx.vstack(
                                rx.text("Valor (R$)", font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                                rx.el.input(
                                    default_value=HubState.tl_custo_valor,
                                    on_blur=HubState.set_tl_custo_valor,
                                    placeholder="0,00",
                                    style={"background": "rgba(14,26,23,0.8)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "padding": "6px 8px", "fontSize": "13px", "width": "100%", "outline": "none"},
                                ),
                                spacing="1", flex="1",
                            ),
                            rx.vstack(
                                rx.text("Categoria", font_size="10px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                                rx.select.root(
                                    rx.select.trigger(style={"background": "rgba(14,26,23,0.8)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "fontSize": "12px", "cursor": "pointer", "width": "100%"}),
                                    rx.select.content(
                                        *[rx.select.item(c, value=c) for c in ["Operacional", "Comercial", "Marketing", "Logística", "Administrativo", "Outro"]],
                                        bg=S.BG_ELEVATED, border=f"1px solid {S.BORDER_SUBTLE}",
                                    ),
                                    value=HubState.tl_custo_categoria,
                                    on_change=HubState.set_tl_custo_categoria,
                                ),
                                spacing="1", flex="1",
                            ),
                            spacing="2", width="100%",
                        ),
                    ),
                    # ── Anexo ─────────────────────────────────────────────
                    rx.vstack(
                        rx.text("Anexo", font_size="11px", color=S.TEXT_MUTED, font_family=S.FONT_MONO),
                        rx.cond(
                            HubState.tl_anexo_nome != "",
                            rx.hstack(
                                rx.icon(tag="paperclip", size=12, color=S.PATINA),
                                rx.text(HubState.tl_anexo_nome, font_size="11px", color=S.PATINA, font_family=S.FONT_MONO, max_width="160px", overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
                                rx.icon_button(rx.icon(tag="x", size=10, color=S.DANGER), size="1", variant="ghost", on_click=HubState.set_tl_anexo_nome(""), cursor="pointer"),
                                spacing="1", align="center",
                            ),
                            rx.upload(
                                rx.hstack(
                                    rx.cond(
                                        HubState.tl_uploading_anexo,
                                        rx.spinner(size="1"),
                                        rx.icon(tag="upload", size=12, color=S.TEXT_MUTED),
                                    ),
                                    rx.text(rx.cond(HubState.tl_uploading_anexo, "Enviando...", "Clique ou arraste um arquivo"), font_size="11px", color=S.TEXT_MUTED),
                                    spacing="1", align="center",
                                ),
                                on_drop=HubState.upload_tl_anexo(rx.upload_files(upload_id="tl_file")),
                                id="tl_file",
                                border=f"1px dashed {S.BORDER_SUBTLE}",
                                border_radius="6px",
                                padding="8px 12px",
                                width="100%",
                                cursor="pointer",
                                _hover={"border_color": S.COPPER},
                                accept={"application/pdf": [".pdf"], "image/*": [".jpg", ".jpeg", ".png"], "application/vnd.openxmlformats-officedocument.*": [".xlsx", ".docx"]},
                            ),
                        ),
                        spacing="1", width="100%",
                    ),
                    rx.cond(HubState.tl_error != "", rx.text(HubState.tl_error, font_size="12px", color=S.DANGER)),
                    # Submit
                    rx.button(
                        rx.cond(
                            HubState.tl_submitting,
                            rx.spinner(size="2"),
                            rx.hstack(rx.icon(tag="send", size=13), rx.text("Registrar"), spacing="1", align="center"),
                        ),
                        on_click=HubState.submit_timeline_entry,
                        disabled=HubState.tl_submitting,
                        width="100%", size="2",
                        style={"background": S.COPPER, "color": S.BG_VOID, "fontFamily": S.FONT_TECH, "fontWeight": "700", "cursor": "pointer"},
                    ),
                    spacing="3", width="100%",
                ),
                **_GLASS_PANEL, width="100%",
            ),
            width=rx.breakpoints(initial="100%", lg="280px"),
            flex_shrink="0",
        ),
        # ── RIGHT: Timeline feed ──────────────────────────────────────────────
        rx.vstack(
            # Search bar
            rx.box(
                rx.icon(tag="search", size=13, color=S.TEXT_MUTED, position="absolute", left="10px", top="50%", transform="translateY(-50%)", pointer_events="none"),
                rx.el.input(
                    placeholder="Pesquisar registros...",
                    on_change=HubState.set_tl_search,
                    style={"background": "rgba(14,26,23,0.6)", "border": f"1px solid {S.BORDER_SUBTLE}", "borderRadius": S.R_CONTROL, "color": "white", "padding": "7px 10px 7px 30px", "fontSize": "13px", "width": "100%", "outline": "none"},
                ),
                position="relative", width="100%",
            ),
            # Filter pills
            rx.hstack(
                rx.box(
                    rx.text("Todos", font_size="10px", font_weight="700", color=rx.cond(HubState.tl_filter_tipo == "", S.BG_VOID, S.TEXT_MUTED), white_space="nowrap"),
                    padding="3px 10px", border_radius="4px", cursor="pointer",
                    bg=rx.cond(HubState.tl_filter_tipo == "", S.COPPER, "rgba(255,255,255,0.04)"),
                    border=rx.cond(HubState.tl_filter_tipo == "", f"1px solid {S.COPPER}", f"1px solid {S.BORDER_SUBTLE}"),
                    on_click=HubState.set_tl_filter_tipo(""),
                    _hover={"bg": rx.cond(HubState.tl_filter_tipo == "", S.COPPER, "rgba(255,255,255,0.07)")},
                    transition="all 0.15s ease",
                ),
                rx.foreach(rx.Var.create(ENTRY_TYPES), _tl_filter_pill),
                spacing="1", flex_wrap="wrap", align="center",
            ),
            # Feed
            rx.cond(
                HubState.timeline_loading,
                rx.center(rx.vstack(rx.spinner(size="3"), rx.text("Carregando registros...", font_size="12px", color=S.TEXT_MUTED), spacing="2", align="center"), padding="40px"),
                rx.cond(
                    HubState.filtered_timeline.length() == 0,
                    rx.center(
                        rx.vstack(
                            rx.icon(tag="scroll-text", size=32, color=S.BORDER_SUBTLE),
                            rx.text("Nenhum registro encontrado", font_size="13px", color=S.TEXT_MUTED),
                            rx.text("Use o formulário ao lado para criar o primeiro registro", font_size="11px", color=S.TEXT_MUTED, opacity="0.7"),
                            spacing="2", align="center",
                        ), padding="40px",
                    ),
                    rx.vstack(
                        rx.foreach(HubState.filtered_timeline, _tl_entry_row),
                        spacing="0", width="100%",
                    ),
                ),
            ),
            spacing="3", flex="1", width="100%",
        ),
        gap="20px",
        flex_wrap=rx.breakpoints(initial="wrap", lg="nowrap"),
        width="100%", align="start",
        class_name="animate-fade-in",
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PROJECT DETAIL: TAB ROUTER
# ══════════════════════════════════════════════════════════════════════════════


def _project_breadcrumb() -> rx.Component:
    """Minimal breadcrumb bar: back button + project code. Tabs are in the global top bar."""
    return rx.hstack(
        rx.button(
            rx.icon(tag="chevron-left", size=16),
            "Projetos",
            variant="ghost",
            on_click=GlobalState.deselect_project,
            cursor="pointer",
            color=S.TEXT_MUTED,
            font_family=S.FONT_MONO,
            font_size="12px",
            _hover={"color": "white", "bg": "rgba(255,255,255,0.06)"},
            padding_x="10px",
            padding_y="6px",
            border_radius="4px",
        ),
        rx.text("/", color=S.BORDER_SUBTLE, font_size="14px"),
        rx.text(
            GlobalState.selected_project,
            font_family=S.FONT_TECH,
            font_size="14px",
            font_weight="600",
            color="var(--text-main)",
        ),
        spacing="2",
        align="center",
        padding_y="8px",
        margin_bottom="12px",
        width="100%",
    )


def hub_project_detail() -> rx.Component:
    """Renders the correct sub-page tab based on GlobalState.project_hub_tab."""
    return rx.vstack(
        _project_breadcrumb(),
        rx.match(
            GlobalState.project_hub_tab,
            ("visao_geral", rx.box(_tab_visao_geral(), width="100%", class_name="animate-fade-in")),
            ("dashboard",   rx.box(_tab_dashboard(),   width="100%", class_name="animate-fade-in")),
            ("cronograma",  rx.box(_tab_cronograma(),  width="100%", class_name="animate-fade-in")),
            ("auditoria",   rx.box(_tab_auditoria(),   width="100%", class_name="animate-fade-in")),
            ("timeline",    rx.box(_tab_timeline(),    width="100%", class_name="animate-fade-in")),
            # Default
            rx.box(_tab_visao_geral(), width="100%"),
        ),
        width="100%",
        spacing="0",
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════


def hub_operacoes_page() -> rx.Component:
    """
    Hub de Operações — unified project operations page.
    Route: /hub
    """
    return rx.cond(
        GlobalState.is_loading,
        page_loading_skeleton(),
        rx.cond(
            GlobalState.selected_project != "",
            # Detail view — project selected
            rx.vstack(
                hub_project_detail(),
                width="100%",
                spacing="6",
                class_name="animate-enter",
                on_mount=lambda: GlobalState.set_current_path("/hub"),
            ),
            # Landing — pulse card grid
            rx.vstack(
                hub_landing_page(),
                width="100%",
                spacing="6",
                class_name="animate-enter",
                on_mount=lambda: GlobalState.set_current_path("/hub"),
            ),
        ),
    )
