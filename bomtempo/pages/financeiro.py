import reflex as rx

from bomtempo.components.charts import (
    chart_tooltip,
    dark_cartesian_grid,
    kpi_card,
    money_formatter_js,
    pie_chart_donut,
)
from bomtempo.components.skeletons import page_loading_skeleton
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def finance_header() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text("Financeiro", **S.PAGE_TITLE_STYLE),
            rx.text("Controle de Custos e Medições", **S.PAGE_SUBTITLE_STYLE),
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
                value=GlobalState.fin_project_filter,
                on_change=GlobalState.set_fin_project_filter,
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
        width="100%",
        align="end",
        class_name="animate-enter",
    )


def finance_kpi_grid() -> rx.Component:
    return rx.grid(
        kpi_card(
            title="Total Contratado",
            value=GlobalState.financeiro_contratado_fmt,
            icon="wallet",
            is_money=True,
            on_click=GlobalState.set_show_kpi_detail("total_contratado"),
        ),
        kpi_card(
            title="Total Medido",
            value=GlobalState.financeiro_realizado_fmt,
            icon="dollar-sign",
            trend="Executado",
            trend_type="positive",
            is_money=True,
            on_click=GlobalState.set_show_kpi_detail("total_medido"),
        ),
        kpi_card(
            title="Saldo à Medir",
            value=GlobalState.margem_bruta_fmt,
            icon="trending-up",
            trend="Pendente",
            trend_type="negative",
            is_money=True,
            on_click=GlobalState.set_show_kpi_detail("saldo_medir"),
        ),
        columns=rx.breakpoints(initial="1", sm="2", lg="3"),
        spacing="6",
        width="100%",
    )


def finance_measurement_chart() -> rx.Component:
    """Status de Medição Global - Donut chart with legend"""
    return rx.box(
        rx.vstack(
            rx.text(
                "Status de Medição Global",
                font_family=S.FONT_TECH,
                font_size="1.25rem",
                font_weight="700",
                color="white",
                margin_bottom="24px",
            ),
            rx.box(
                pie_chart_donut(
                    data=GlobalState.status_contratos_dist,
                    name_key="name",
                    value_key="value",
                    height=280,
                    use_data_fill=True,
                ),
                width="100%",
                height="280px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            # Legend
            rx.vstack(
                rx.foreach(
                    GlobalState.status_contratos_dist,
                    lambda item: rx.hstack(
                        rx.hstack(
                            rx.box(
                                width="10px",
                                height="10px",
                                border_radius="2px",
                                bg=item["fill"],
                            ),
                            rx.text(
                                item["name"],
                                font_size="0.8rem",
                                font_weight="700",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            align="center",
                            spacing="3",
                        ),
                        rx.spacer(),
                        rx.text(
                            item["value"].to_string(),
                            font_family=S.FONT_MONO,
                            font_size="0.8rem",
                            color="white",
                            font_weight="700",
                        ),
                        width="100%",
                        padding="10px 12px",
                        border_radius="8px",
                        bg="rgba(255, 255, 255, 0.02)",
                        border="1px solid rgba(255, 255, 255, 0.03)",
                    ),
                ),
                spacing="2",
                width="100%",
                margin_top="16px",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
    )


def finance_cost_chart() -> rx.Component:
    """Custos por Centro (Cockpit) - Horizontal bar with R$ formatting"""
    return rx.box(
        rx.vstack(
            rx.text(
                "Custos por Centro (Cockpit)",
                font_family=S.FONT_TECH,
                font_size="1.25rem",
                font_weight="700",
                color="white",
                margin_bottom="24px",
            ),
            rx.box(
                rx.recharts.bar_chart(
                    dark_cartesian_grid(),
                    rx.recharts.x_axis(
                        type_="number",
                        stroke=S.TEXT_MUTED,
                        font_size=10,
                        tick_formatter=money_formatter_js(),
                    ),
                    rx.recharts.y_axis(
                        data_key="cockpit",
                        type_="category",
                        stroke=S.TEXT_PRIMARY,
                        font_size=12,
                        width=90,
                    ),
                    chart_tooltip(formatter=money_formatter_js()),
                    rx.recharts.bar(
                        rx.recharts.label_list(
                            data_key="formatted_total",
                            position="right",
                            fill=S.TEXT_PRIMARY,
                            font_size=10,
                        ),
                        data_key="total_contratado",
                        fill=S.COPPER,
                        radius=[0, 4, 4, 0],
                    ),
                    data=GlobalState.financeiro_cockpit_chart,
                    layout="vertical",
                    height=300,
                    margin={"left": 20, "right": 80},
                ),
                width="100%",
                height="300px",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
    )


def finance_table_row(item: dict) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.text(item["cockpit"], font_weight="700", font_size="12px", color="white"),
            padding="16px",
        ),
        rx.el.td(
            rx.text(
                "R$ " + item["total_contratado"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color="white",
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                "R$ " + item["total_realizado"].to_string(),
                font_family=S.FONT_MONO,
                font_size="12px",
                color=S.PATINA,
            ),
            padding="16px",
            text_align="right",
        ),
        rx.el.td(
            rx.text(
                item["margem_pct"].to_string() + "%",
                font_family=S.FONT_MONO,
                font_size="12px",
                font_weight="700",
                color=rx.cond(
                    item["margem_pct"].to(float) >= 0,
                    S.PATINA,
                    S.DANGER,
                ),
            ),
            padding="16px",
            text_align="right",
        ),
        _hover={"bg": "rgba(255, 255, 255, 0.02)"},
        transition="background 0.2s ease",
        border_bottom=f"1px solid {S.BORDER_SUBTLE}",
    )


def finance_scurve_chart() -> rx.Component:
    """S-Curve: Cumulative Planned vs Actual Spending"""
    return rx.box(
        rx.vstack(
            rx.text(
                "Curva S - Avanço Financeiro Acumulado",
                font_family=S.FONT_TECH,
                font_size="1.25rem",
                font_weight="700",
                color="white",
                margin_bottom="24px",
            ),
            rx.box(
                rx.recharts.area_chart(
                    dark_cartesian_grid(),
                    rx.recharts.x_axis(
                        data_key="cockpit",
                        stroke=S.TEXT_MUTED,
                        font_size=11,
                    ),
                    rx.recharts.y_axis(
                        stroke=S.TEXT_PRIMARY,
                        font_size=11,
                        tick_formatter=money_formatter_js(),
                    ),
                    chart_tooltip(formatter=money_formatter_js()),
                    # Planned cumulative (lighter color)
                    rx.recharts.area(
                        data_key="cumulative_planned",
                        name="Planejado",
                        stroke=S.TEXT_MUTED,
                        fill=f"{S.COPPER}30",
                        stroke_width=2,
                    ),
                    # Actual cumulative (primary color)
                    rx.recharts.area(
                        data_key="cumulative_actual",
                        name="Realizado",
                        stroke=S.PATINA,
                        fill=f"{S.PATINA}40",
                        stroke_width=3,
                    ),
                    data=GlobalState.financeiro_scurve_chart,
                    height=350,
                ),
                width="100%",
                height="350px",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        width="100%",
    )


def finance_table() -> rx.Component:
    """Detailed financial table — FULL WIDTH"""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.text(
                    "Detalhamento Financeiro por Marco",
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
                                "COCKPIT",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            rx.el.th(
                                "CONTRATADO",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "MEDIDO",
                                padding="16px",
                                font_size="10px",
                                font_weight="900",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                text_align="right",
                            ),
                            rx.el.th(
                                "MARGEM %",
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
                            GlobalState.financeiro_cockpit_chart,
                            finance_table_row,
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


def financeiro_page() -> rx.Component:
    return rx.vstack(
        finance_header(),
        rx.cond(
            GlobalState.is_loading,
            page_loading_skeleton(),
            rx.vstack(
                finance_kpi_grid(),
                rx.grid(
                    finance_measurement_chart(),
                    finance_cost_chart(),
                    columns=rx.breakpoints(initial="1", lg="2"),
                    spacing="8",
                    width="100%",
                ),
                # S-Curve FULL WIDTH
                finance_scurve_chart(),
                # Table FULL WIDTH — not inside grid
                finance_table(),
                width="100%",
                spacing="8",
            ),
        ),
        width="100%",
        spacing="8",
        on_mount=lambda: GlobalState.set_current_path("/financeiro"),
        class_name="animate-enter",
    )
