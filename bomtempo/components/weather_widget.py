import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def weather_widget() -> rx.Component:
    """Weather widget with fixed card layout matching gauge component"""
    return rx.box(
        rx.cond(
            GlobalState.weather_loading,
            # Loading state - fixed card
            rx.vstack(
                rx.text(
                    "PREVISÃO DO TEMPO",
                    font_size="0.75rem",
                    color=S.TEXT_MUTED,
                    text_transform="uppercase",
                    letter_spacing="0.15em",
                    font_weight="700",
                    text_align="center",
                ),
                rx.center(
                    rx.vstack(
                        rx.spinner(color=S.COPPER, size="3"),
                        rx.text(
                            "Carregando previsão do tempo...",
                            font_size="12px",
                            color=S.TEXT_MUTED,
                            margin_top="16px",
                            text_align="center",
                        ),
                        align="center",
                        spacing="3",
                    ),
                    height="180px",
                ),
                align="center",
                justify="center",
                width="100%",
                spacing="4",
            ),
            # Loaded state
            rx.cond(
                GlobalState.weather_risk_level != "Unknown",
                rx.vstack(
                    rx.text(
                        "PREVISÃO DO TEMPO",
                        font_size="0.75rem",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.15em",
                        font_weight="700",
                        margin_bottom="16px",
                        text_align="center",
                        width="100%",
                    ),
                    rx.vstack(
                        # Icon Section (Larger)
                        rx.center(
                            rx.icon(
                                tag=rx.cond(
                                    GlobalState.weather_risk_level == "High", "cloud-rain", "sun"
                                ),
                                color="white",
                                size=48,
                            ),
                            bg=rx.cond(
                                GlobalState.weather_risk_level == "High",
                                "rgba(239, 68, 68, 0.2)",  # Red bg
                                rx.cond(
                                    GlobalState.weather_risk_level == "Medium",
                                    "rgba(249, 115, 22, 0.2)",  # Orange bg
                                    "rgba(16, 185, 129, 0.2)",  # Green bg
                                ),
                            ),
                            padding="24px",
                            border_radius="20px",
                            border=rx.cond(
                                GlobalState.weather_risk_level == "High",
                                "2px solid #EF4444",
                                rx.cond(
                                    GlobalState.weather_risk_level == "Medium",
                                    "2px solid #F97316",
                                    "2px solid #10B981",
                                ),
                            ),
                            margin_bottom="16px",
                        ),
                        # Info Section (Centralized and Large)
                        rx.vstack(
                            rx.text(
                                GlobalState.weather_location_name,
                                font_size="1.25rem",
                                color="#9CA3AF",
                                font_weight="600",
                                text_align="center",
                            ),
                            rx.text(
                                f"{GlobalState.weather_data['temp']}°C",
                                font_size="4rem",  # Large prominent font
                                font_weight="900",
                                color="white",
                                font_family=S.FONT_TECH,
                                line_height="1",
                            ),
                            rx.badge(
                                GlobalState.weather_risk_level,
                                color_scheme=rx.cond(
                                    GlobalState.weather_risk_level == "High",
                                    "red",
                                    rx.cond(
                                        GlobalState.weather_risk_level == "Medium",
                                        "orange",
                                        "green",
                                    ),
                                ),
                                variant="solid",
                                size="3",
                            ),
                            spacing="3",
                            align="center",
                            width="100%",
                        ),
                        spacing="0",
                        align="center",
                        width="100%",
                    ),
                    # Analysis Button
                    rx.button(
                        rx.hstack(
                            rx.icon("scan-eye", size=16),
                            rx.text("Analisar Impacto", font_size="10px"),
                            spacing="2",
                        ),
                        size="1",
                        variant="ghost",
                        color=S.COPPER,
                        on_click=GlobalState.analyze_weather_impact,
                        width="100%",
                        margin_top="24px",
                    ),
                    align="center",
                    justify="center",
                    width="100%",
                    spacing="0",
                ),
                # No data state
                rx.vstack(
                    rx.text(
                        "PREVISÃO DO TEMPO",
                        font_size="0.75rem",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        letter_spacing="0.15em",
                        font_weight="700",
                    ),
                    rx.text(
                        "Sem dados meteorológicos",
                        font_size="12px",
                        color="#666",
                        text_align="center",
                    ),
                    align="center",
                    justify="center",
                    height="180px",
                    spacing="3",
                ),
            ),
        ),
        **S.GLASS_CARD,
        min_height="320px",
        height="100%",
        width="100%",
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="center",
    )
