import reflex as rx

from bomtempo.components.charts import (
    composed_chart_om,
    kpi_card,
)
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def om_header() -> rx.Component:
    """Header matching React OM.tsx — title + filter + time buttons"""
    return rx.hstack(
        rx.vstack(
            rx.text("O&M - Gestão de Ativos", **S.PAGE_TITLE_STYLE),
            rx.text("Performance Energética e Resultados", **S.PAGE_SUBTITLE_STYLE),
            spacing="1",
        ),
        rx.spacer(),
        # Project filter
        rx.hstack(
            rx.icon(tag="filter", size=16, color=S.COPPER),
            rx.el.select(
                rx.foreach(
                    GlobalState.project_filter_options,
                    lambda opt: rx.el.option(
                        opt, value=opt, style={"background": S.BG_ELEVATED, "color": S.COPPER}
                    ),
                ),
                value=GlobalState.om_project_filter,
                on_change=GlobalState.set_om_project_filter,
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
            padding_y="6px",
            border_radius="12px",
            border=f"1px solid {S.PATINA}",
            align="center",
        ),
        # Time filter (Mês / Trimestre / Ano)
        rx.hstack(
            rx.foreach(
                ["Mês", "Trimestre", "Ano"],
                lambda t: rx.box(
                    rx.text(
                        t,
                        font_size="12px",
                        font_weight="700",
                        color=rx.cond(
                            GlobalState.om_time_filter == t,
                            S.BG_VOID,
                            S.TEXT_MUTED,
                        ),
                    ),
                    padding="8px 16px",
                    border_radius="8px",
                    cursor="pointer",
                    bg=rx.cond(
                        GlobalState.om_time_filter == t,
                        S.COPPER,
                        "transparent",
                    ),
                    on_click=lambda: GlobalState.set_om_time_filter(t),
                    _hover={"color": "white"},
                    transition="all 0.2s ease",
                ),
            ),
            bg="rgba(255, 255, 255, 0.03)",
            padding="4px",
            border_radius="12px",
            border="1px solid rgba(255, 255, 255, 0.06)",
            spacing="1",
        ),
        width="100%",
        align="center",
        class_name="animate-enter",
        flex_wrap="wrap",
        gap="4",
    )


def om_kpi_grid() -> rx.Component:
    """4 KPI cards matching React OM.tsx exactly"""
    return rx.grid(
        kpi_card(
            title="Energia Injetada (Total)",
            value=GlobalState.om_energia_injetada_fmt,
            icon="zap",
        ),
        kpi_card(
            title="Acumulado",
            value=GlobalState.om_acumulado_fmt,
            icon="zap",
            trend="Total",
            trend_type="neutral",
        ),
        kpi_card(
            title="Performance",
            value=GlobalState.om_performance_fmt,
            icon="arrow-down-to-dot",
            trend_type="positive",
        ),
        kpi_card(
            title="Fat. Líquido",
            value=GlobalState.om_fat_liquido_fmt,
            icon="calendar",
            is_money=True,
        ),
        columns=rx.breakpoints(initial="1", sm="2", lg="4"),
        spacing="6",
        width="100%",
    )


def om_chart() -> rx.Component:
    """Performance de Geração — FULL WIDTH composed chart.
    Glass panel with h-[400px] chart container.
    """
    return rx.box(
        rx.vstack(
            rx.text(
                "Performance de Geração",
                font_family=S.FONT_TECH,
                font_size="1.25rem",
                font_weight="700",
                color="white",
                margin_bottom="24px",
            ),
            # Chart container — FULL WIDTH, h-[400px]
            rx.box(
                composed_chart_om(
                    data=GlobalState.om_geracao_chart,
                    x_key="mes_ano",
                    bar_key="acumulado_kwh",
                    line1_key="geracao_prevista_kwh",
                    line2_key="energia_injetada_kwh",
                    height=400,
                ),
                width="100%",
                height="400px",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        width="100%",
    )


def om_table_row(item: dict) -> rx.Component:
    """Individual table row"""
    return rx.el.tr(
        rx.el.td(
            rx.text(
                item["mes_ano"],
                font_family=S.FONT_MONO,
                font_size="12px",
                color="white",
            ),
            padding="16px",
        ),
        rx.el.td(
            rx.text(
                item["energia_injetada_kwh"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color=S.PATINA,
                font_weight="700",
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                item["compensado_kwh"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color=S.TEXT_MUTED,
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                item["acumulado_kwh"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color="white",
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                "R$ " + item["valor_faturado"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color="white",
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                "R$ " + item["gestao"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color=S.DANGER,
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                "R$ " + item["faturamento_liquido"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color=S.COPPER,
                font_weight="700",
            ),
            padding="16px",
            text_align="right",
        ),
        _hover={"bg": "rgba(255, 255, 255, 0.02)"},
        transition="background 0.2s ease",
        border_bottom=f"1px solid {S.BORDER_SUBTLE}",
    )


def om_table() -> rx.Component:
    """Registros de O&M table — FULL WIDTH"""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.text(
                    "Registros de O&M",
                    font_family=S.FONT_TECH,
                    font_size="1.125rem",
                    font_weight="700",
                    color="white",
                ),
                padding="24px",
                border_bottom=f"1px solid {S.BORDER_SUBTLE}",
            ),
            rx.box(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th(
                                "DATA",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                            ),
                            rx.el.th(
                                "INJETADA (KWH)",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "COMPENSADA (KWH)",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "ACUMULADA (KWH)",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "VALOR FATURADO",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "GESTÃO",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "FAT. LÍQUIDO",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            bg="rgba(255, 255, 255, 0.02)",
                        ),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            GlobalState.om_table_data,
                            om_table_row,
                        ),
                    ),
                    width="100%",
                    style={"borderCollapse": "collapse"},
                ),
                overflow_x="auto",
                width="100%",
            ),
            spacing="0",
            width="100%",
        ),
        **{k: v for k, v in S.GLASS_CARD_NO_HOVER.items() if k != "padding"},
        padding="0",
        overflow="hidden",
        width="100%",
    )


def om_page() -> rx.Component:
    return rx.vstack(
        om_header(),
        rx.cond(
            GlobalState.is_loading,
            rx.center(rx.spinner(size="3"), width="100%", height="50vh"),
            rx.vstack(
                om_kpi_grid(),
                om_chart(),
                om_table(),
                width="100%",
                spacing="8",
            ),
        ),
        width="100%",
        spacing="6",
        class_name="animate-enter",
        on_mount=lambda: GlobalState.set_current_path("/om"),
    )
