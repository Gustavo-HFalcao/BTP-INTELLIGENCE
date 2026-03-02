import reflex as rx

from bomtempo.components.charts import dual_area_chart
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def previsoes_header() -> rx.Component:
    """Header matching React Forecasts.tsx reference"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.center(
                    rx.icon(tag="brain-circuit", size=24, color="#0A1F1A"),
                    padding="8px",
                    bg=S.COPPER,
                    border_radius="8px",
                ),
                rx.text(
                    "Previsões Rainforest ML",
                    font_family=S.FONT_TECH,
                    font_size="2.25rem",
                    font_weight="900",
                    color="white",
                ),
                align="center",
                spacing="3",
            ),
            rx.text(
                "Utilizando algoritmos de Random Forest treinados com o histórico da BOMTEMPO para prever atrasos e desvios financeiros antes que ocorram.",
                color="#A0A0A0",
                max_width="640px",
                margin_top="8px",
            ),
            spacing="2",
            position="relative",
            z_index="10",
        ),
        padding="48px",
        border_radius="24px",
        background="linear-gradient(90deg, #1A3A30, #0A1F1A)",
        border=f"1px solid {S.BORDER_ACCENT}",
        overflow="hidden",
        position="relative",
        class_name="animate-enter",
    )


def delay_probability_card() -> rx.Component:
    """Probabilidade de Atraso matching React reference"""
    items = [
        {"project": "BOM010-24 (Escola A)", "prob": 15, "status": "Baixo Risco", "color": S.PATINA},
        {
            "project": "BOM011-24 (Hospital B)",
            "prob": 68,
            "status": "Risco Elevado",
            "color": S.DANGER,
        },
        {"project": "BOM012-24 (Shopping C)", "prob": 42, "status": "Moderado", "color": S.WARNING},
    ]

    return rx.box(
        rx.vstack(
            rx.text(
                "Probabilidade de Atraso (Próximos 30 dias)",
                font_family=S.FONT_TECH,
                font_size="1.25rem",
                font_weight="900",
                color="white",
                margin_bottom="24px",
            ),
            rx.vstack(
                *[
                    rx.box(
                        rx.hstack(
                            rx.text(
                                item["project"], font_weight="700", color="white", font_size="14px"
                            ),
                            rx.spacer(),
                            rx.text(
                                item["status"],
                                font_size="12px",
                                font_weight="900",
                                text_transform="uppercase",
                                color=item["color"],
                            ),
                            width="100%",
                            margin_bottom="8px",
                        ),
                        rx.box(
                            rx.box(
                                width=f"{item['prob']}%",
                                height="100%",
                                bg=item["color"],
                                border_radius="9999px",
                                transition="width 1s ease-out",
                            ),
                            height="8px",
                            bg="#0A1F1A",
                            border_radius="9999px",
                            overflow="hidden",
                        ),
                        width="100%",
                        margin_bottom="24px",
                    )
                    for item in items
                ],
                spacing="0",
                width="100%",
            ),
            width="100%",
        ),
        bg="#0D2A23",
        padding="32px",
        border_radius="24px",
        border="1px solid #1A3A30",
    )


def margin_forecast_card() -> rx.Component:
    """Previsão de Margem Final matching React reference"""
    return rx.box(
        rx.vstack(
            rx.icon(tag="trending-up", size=48, color=S.COPPER),
            rx.text(
                "Previsão de Margem Final",
                font_family=S.FONT_TECH,
                font_size="1.5rem",
                font_weight="900",
                color="white",
                margin_top="16px",
            ),
            rx.text(
                "O modelo Rainforest estima uma margem consolidada de 18.5% para o Q4.",
                color="#A0A0A0",
                text_align="center",
                margin_bottom="24px",
            ),
            rx.box(
                rx.text(
                    "CONFIANÇA DO MODELO: 92%",
                    font_weight="900",
                    color="#0A1F1A",
                    font_size="14px",
                ),
                bg=S.COPPER,
                padding="8px 24px",
                border_radius="9999px",
            ),
            spacing="2",
            align="center",
            justify="center",
            text_align="center",
            width="100%",
        ),
        bg="#0D2A23",
        padding="32px",
        border_radius="24px",
        border="1px solid #1A3A30",
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="center",
    )


def forecast_chart() -> rx.Component:
    """Revenue forecast chart"""
    return rx.box(
        rx.vstack(
            rx.text(
                "Previsão de Receita (Real vs Previsto)",
                **S.SECTION_TITLE_STYLE,
            ),
            dual_area_chart(
                data=GlobalState.forecast_revenue_chart,
                x_key="name",
                y1_key="real",
                y2_key="previsto",
                name1="Real",
                name2="Previsto",
                height=400,
            ),
            width="100%",
        ),
        **S.GLASS_CARD,
        width="100%",
    )


def previsoes_page() -> rx.Component:
    return rx.vstack(
        previsoes_header(),
        rx.cond(
            GlobalState.is_loading,
            rx.center(rx.spinner(size="3"), width="100%", height="50vh"),
            rx.vstack(
                rx.grid(
                    delay_probability_card(),
                    margin_forecast_card(),
                    columns=rx.breakpoints(initial="1", lg="2"),
                    spacing="8",
                    width="100%",
                ),
                forecast_chart(),
                width="100%",
                spacing="8",
            ),
        ),
        width="100%",
        spacing="8",
    )
