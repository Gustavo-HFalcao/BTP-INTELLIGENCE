import reflex as rx

from bomtempo.components.charts import (
    bar_chart_horizontal,
    kpi_card,
    pie_chart_donut,
)
from bomtempo.components.skeletons import page_loading_skeleton
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def header_banner() -> rx.Component:
    """Overview header — full-width glass panel matching React reference exactly."""
    return rx.box(
        # Gradient overlay
        rx.box(
            position="absolute",
            inset="0",
            background="linear-gradient(90deg, rgba(201,139,42,0.1) 0%, transparent 50%)",
            pointer_events="none",
        ),
        # Background icon
        rx.box(
            rx.icon(tag="activity", size=200, stroke_width=0.5, color=S.TEXT_MUTED),
            position="absolute",
            right="0",
            top="0",
            padding="48px",
            opacity="0.1",
            pointer_events="none",
        ),
        # Content
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.text(
                        "System Online",
                        font_size="10px",
                        font_weight="700",
                        text_transform="uppercase",
                        letter_spacing="0.15em",
                        color=S.BG_VOID,
                    ),
                    bg=S.COPPER,
                    padding="4px 10px",
                    border_radius="2px",
                ),
                rx.box(
                    width="48px",
                    height="1px",
                    bg=f"{S.COPPER}80",
                ),
                align="center",
                spacing="3",
            ),
            rx.text(
                "VISÃO GERAL",
                font_family=S.FONT_TECH,
                font_size="3rem",
                font_weight="700",
                color="white",
                letter_spacing="-0.02em",
                line_height="1",
                margin_top="16px",
            ),
            rx.text(
                "Centro de Comando BOMTEMPO INTELLIGENCE. Telemetria financeira, velocidade operacional e marcadores estratégicos em tempo real.",
                color=S.TEXT_MUTED,
                font_size="1.125rem",
                font_weight="300",
                max_width="640px",
                margin_top="8px",
            ),
            align="start",
            spacing="0",
            position="relative",
            z_index="10",
            max_width="640px",
        ),
    # Glass panel styling — FULL WIDTH
    position="relative",
    overflow="hidden",
    padding="48px",
    border_radius=S.R_CARD,
    width="100%",
    border_left=f"3px solid {S.COPPER}",
    class_name="glass-panel animate-enter",
)


def filter_bar() -> rx.Component:
    """Global project/client filter — top-right enterprise pill."""
    return rx.hstack(
        rx.spacer(),
        rx.hstack(
            rx.icon(tag="filter", size=13, color=S.COPPER),
            rx.text(
                "Filtro:",
                font_size="11px",
                color=S.TEXT_MUTED,
                font_weight="700",
                font_family=S.FONT_MONO,
                letter_spacing="0.1em",
                text_transform="uppercase",
            ),
            rx.el.select(
                rx.foreach(
                    GlobalState.project_filter_options,
                    lambda opt: rx.el.option(
                        opt, value=opt, style={"background": S.BG_ELEVATED, "color": S.COPPER}
                    ),
                ),
                value=GlobalState.global_project_filter,
                on_change=GlobalState.set_global_project_filter,
                background="transparent",
                color=S.COPPER,
                border="none",
                outline="none",
                font_size="13px",
                font_family=S.FONT_MONO,
                font_weight="700",
                padding_x="4px",
                cursor="pointer",
            ),
            bg="rgba(201,139,42,0.06)",
            padding_x="12px",
            padding_y="7px",
            border_radius=S.R_CONTROL,
            border=f"1px solid rgba(201,139,42,0.25)",
            align="center",
            spacing="2",
            transition="all 0.15s ease",
            _hover={"bg": "rgba(201,139,42,0.1)", "border_color": S.COPPER},
        ),
        width="100%",
        align="center",
    )


def kpi_grid() -> rx.Component:
    return rx.grid(
        kpi_card(
            title="Receita Total",
            value=GlobalState.valor_carteira_formatado,
            icon="dollar-sign",
            trend="+12.5%",
            trend_type="positive",
            is_money=True,
            on_click=GlobalState.set_show_kpi_detail("receita_total"),
        ),
        kpi_card(
            title="Contratos Ativos",
            value=GlobalState.contratos_ativos.to_string(),
            icon="hard-hat",
            on_click=GlobalState.set_show_kpi_detail("contratos_ativos"),
        ),
        kpi_card(
            title="Velocidade Média",
            value=GlobalState.avanco_fisico_geral_fmt,
            icon="trending-up",
            trend="+2.1%",
            trend_type="positive",
            on_click=rx.redirect("/obras"),
        ),
        kpi_card(
            title="Health Score",
            value="94.2",
            icon="target",
            trend_type="positive",
        ),
        columns=rx.breakpoints(initial="1", sm="2", lg="4"),
        spacing="6",
        width="100%",
    )


def main_bar_chart() -> rx.Component:
    """Main bar chart - Alocação de Volume"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Alocação de Volume",
                        font_family=S.FONT_TECH,
                        font_size="1.25rem",
                        font_weight="700",
                        color=S.TEXT_PRIMARY,
                    ),
                    rx.text(
                        "RECEITA POR ENTIDADE",
                        font_size="0.75rem",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.15em",
                        font_weight="700",
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.box(width="12px", height="12px", border_radius="50%", bg=S.COPPER),
                    rx.box(width="12px", height="12px", border_radius="50%", bg=S.PATINA),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
                margin_bottom="32px",
            ),
            rx.box(
                bar_chart_horizontal(
                    data=GlobalState.faturamento_por_cliente,
                    x_key="valor_contratado",
                    y_key="cliente",
                    label_key="formatted_valor",
                    height=350,
                ),
                width="100%",
                height="350px",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        class_name="chart-enter delay-300",
    )


def portfolio_status_chart() -> rx.Component:
    """Pie chart - Status do Portfolio"""
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.text(
                    "Status do Portfolio",
                    font_family=S.FONT_TECH,
                    font_size="1.25rem",
                    font_weight="700",
                    color=S.TEXT_PRIMARY,
                ),
                rx.text(
                    "DISTRIBUIÇÃO OPERACIONAL",
                    font_size="0.75rem",
                    color=S.TEXT_MUTED,
                    text_transform="uppercase",
                    letter_spacing="0.15em",
                    font_weight="700",
                ),
                spacing="1",
                margin_bottom="32px",
                width="100%",
            ),
            # Donut chart with center stat
            rx.box(
                pie_chart_donut(
                    data=GlobalState.status_contratos_dist,
                    name_key="name",
                    value_key="value",
                    height=250,
                    use_data_fill=True,
                ),
                # Center text
                rx.box(
                    rx.vstack(
                        rx.text(
                            GlobalState.total_contratos.to_string(),
                            font_family=S.FONT_TECH,
                            font_size="1.875rem",
                            font_weight="700",
                            color="white",
                        ),
                        rx.text(
                            "TOTAL",
                            font_size="9px",
                            color=S.TEXT_MUTED,
                            text_transform="uppercase",
                            letter_spacing="0.15em",
                        ),
                        spacing="0",
                        align="center",
                    ),
                    position="absolute",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    pointer_events="none",
                ),
                position="relative",
                height="250px",
                width="100%",
            ),
            # Legend items
            rx.vstack(
                rx.foreach(
                    GlobalState.status_contratos_dist,
                    lambda item: rx.hstack(
                        rx.hstack(
                            rx.box(
                                width="8px",
                                height="8px",
                                border_radius="2px",
                                bg=item["fill"],
                            ),
                            rx.text(
                                item["name"],
                                font_size="0.75rem",
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
                            font_size="0.75rem",
                            color="white",
                        ),
                        width="100%",
                        padding="12px",
                        border_radius="8px",
                        bg="rgba(255, 255, 255, 0.02)",
                        border="1px solid rgba(255, 255, 255, 0.03)",
                    ),
                ),
                spacing="3",
                width="100%",
                margin_top="24px",
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        class_name="chart-enter delay-400",
    )


def charts_section() -> rx.Component:
    return rx.grid(
        rx.box(
            main_bar_chart(),
            grid_column=rx.breakpoints(initial="span 1", lg="span 2"),
        ),
        rx.box(
            portfolio_status_chart(),
            grid_column="span 1",
        ),
        columns=rx.breakpoints(initial="1", lg="3"),
        spacing="8",
        width="100%",
    )


def index_page() -> rx.Component:
    return rx.cond(
        (GlobalState.current_user_role == "Administrador")
        | (GlobalState.current_user_role == "Engenheiro")
        | (GlobalState.current_user_role == "Gestão-Mobile")
        | (GlobalState.current_user_role == ""),  # Allows fade in while login loads
        rx.vstack(
            filter_bar(),
            # Error Display
            rx.cond(
                GlobalState.error_message != "",
                rx.box(
                    rx.callout(
                        GlobalState.error_message,
                        icon="triangle-alert",
                        color_scheme="red",
                        variant="surface",
                        width="100%",
                    ),
                    width="100%",
                    margin_bottom="16px",
                ),
            ),
            header_banner(),
            rx.cond(
                GlobalState.is_loading,
                page_loading_skeleton(),
                rx.vstack(
                    kpi_grid(),
                    charts_section(),
                    width="100%",
                    spacing="8",
                ),
            ),
            width="100%",
            spacing="8",
            on_mount=lambda: GlobalState.set_current_path("/"),
        ),
        # Restricted access fallback (black screen during redirect)
        rx.center(
            rx.vstack(
                rx.spinner(size="3", color=S.COPPER),
                rx.text(
                    "Verificando acessos...",
                    color=S.TEXT_MUTED,
                    font_size="14px",
                    font_family=S.FONT_TECH,
                ),
                align="center",
                spacing="4",
            ),
            width="100%",
            height="100vh",
            bg=S.BG_VOID,
        ),
    )
