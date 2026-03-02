import reflex as rx

from bomtempo.components.sidebar import typewriter
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


def login_page() -> rx.Component:
    """Modern Login Page with Glassmorphism"""
    return rx.box(
        # Background gradient overlay
        rx.box(
            position="absolute",
            top="0",
            left="0",
            width="100%",
            height="100%",
            bg=f"radial-gradient(circle at 30% 20%, {S.COPPER}15, transparent 50%), radial-gradient(circle at 70% 80%, {S.PATINA}10, transparent 50%)",
            z_index="1",
        ),
        # Login Card Container
        rx.center(
            rx.vstack(
                # Logo Section with Icon
                rx.vstack(
                    rx.center(
                        rx.icon(
                            tag="zap",
                            size=56,
                            color=S.COPPER,
                        ),
                        width="100px",
                        height="100px",
                        border_radius="50%",
                        bg=f"{S.COPPER_GLOW}",
                        border=f"2px solid {S.COPPER}",
                        box_shadow=f"0 0 40px {S.COPPER}40, 0 0 80px {S.COPPER}20",
                        margin_bottom="24px",
                    ),
                    rx.text(
                        "BOMTEMPO",
                        font_size="3.2rem",
                        font_weight="900",
                        font_family=S.FONT_TECH,
                        letter_spacing="0.1em",
                        color=S.COPPER,
                        line_height="1",
                    ),
                    rx.text(
                        "INTELLIGENCE",
                        font_size="1.2rem",
                        font_weight="700",
                        font_family=S.FONT_TECH,
                        letter_spacing="0.3em",
                        color=S.PATINA,
                        margin_top="8px",
                    ),
                    rx.vstack(
                        rx.text(
                            "Transformando dados em",
                            font_size="1rem",
                            color="rgba(255, 255, 255, 0.4)",
                            font_family=S.FONT_BODY,
                            white_space="nowrap",
                        ),
                        rx.box(
                            typewriter(
                                options={
                                    "strings": [
                                        "resultados.",
                                        "inovação.",
                                        "previsibilidade.",
                                        "engenharia pura.",
                                        "excelência.",
                                        "performance.",
                                    ],
                                    "autoStart": True,
                                    "loop": True,
                                    "delay": 50,
                                    "deleteSpeed": 30,
                                    "cursor": "|",
                                }
                            ),
                            font_size="1.5rem",
                            font_weight="bold",
                            color=S.COPPER,
                            font_family=S.FONT_TECH,
                        ),
                        spacing="0",
                        align="center",
                        justify="center",
                        margin_top="24px",
                    ),
                    spacing="0",
                    align="center",
                    margin_bottom="32px",
                ),
                # Login Card
                rx.box(
                    rx.vstack(
                        rx.text(
                            "Acesso à Plataforma",
                            font_size="1.5rem",
                            color="white",
                            font_weight="700",
                            font_family=S.FONT_TECH,
                            text_align="center",
                            margin_bottom="32px",
                        ),
                        # Username Input
                        rx.vstack(
                            rx.text(
                                "Usuário",
                                font_size="0.75rem",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                letter_spacing="0.1em",
                                font_weight="600",
                            ),
                            rx.input(
                                placeholder="Digite seu usuário",
                                value=GlobalState.username_input,
                                on_change=GlobalState.set_username_input,
                                bg="rgba(255, 255, 255, 0.05)",
                                border=f"1px solid {S.BORDER_SUBTLE}",
                                color="white",
                                width="100%",
                                height="48px",
                                padding_x="16px",
                                border_radius="12px",
                                transition="all 0.2s ease",
                            ),
                            spacing="2",
                            align="start",
                            width="100%",
                        ),
                        # Password Input
                        rx.vstack(
                            rx.text(
                                "Senha",
                                font_size="0.75rem",
                                color=S.TEXT_MUTED,
                                text_transform="uppercase",
                                letter_spacing="0.1em",
                                font_weight="600",
                            ),
                            rx.input(
                                placeholder="Digite sua senha",
                                type="password",
                                value=GlobalState.password_input,
                                on_change=GlobalState.set_password_input,
                                bg="rgba(255, 255, 255, 0.05)",
                                border=f"1px solid {S.BORDER_SUBTLE}",
                                color="white",
                                width="100%",
                                height="48px",
                                padding_x="16px",
                                border_radius="12px",
                                on_key_down=GlobalState.check_login_on_enter,
                                transition="all 0.2s ease",
                            ),
                            spacing="2",
                            align="start",
                            width="100%",
                        ),
                        # Error Message
                        rx.cond(
                            GlobalState.login_error != "",
                            rx.box(
                                rx.hstack(
                                    rx.icon(tag="alert-circle", size=16, color="#EF4444"),
                                    rx.text(
                                        GlobalState.login_error,
                                        color="#EF4444",
                                        font_size="0.875rem",
                                        font_weight="500",
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                padding="12px 16px",
                                bg="rgba(239, 68, 68, 0.1)",
                                border="1px solid rgba(239, 68, 68, 0.3)",
                                border_radius="8px",
                                width="100%",
                            ),
                        ),
                        # Login Button
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="log-in", size=20),
                                rx.text("ENTRAR", font_weight="700", letter_spacing="0.1em"),
                                spacing="2",
                                align="center",
                                justify="center",
                            ),
                            on_click=GlobalState.check_login,
                            bg=f"linear-gradient(135deg, {S.COPPER}, {S.COPPER_LIGHT})",
                            color="#0A1F1A",
                            width="100%",
                            height="56px",
                            border_radius="12px",
                            _hover={
                                "bg": f"linear-gradient(135deg, {S.COPPER_LIGHT}, {S.COPPER})",
                                "transform": "translateY(-2px)",
                                "boxShadow": f"0 8px 24px {S.COPPER}40",
                            },
                            transition="all 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
                            cursor="pointer",
                        ),
                        # Footer Info
                        rx.text(
                            "Plataforma de Gestão Integrada • v2.0",
                            font_size="0.75rem",
                            color=S.TEXT_MUTED,
                            text_align="center",
                            margin_top="24px",
                            font_weight="500",
                        ),
                        spacing="5",
                        width="100%",
                    ),
                    padding=["24px", "48px"],  # Responsive padding
                    bg=S.BG_ELEVATED,
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    border_radius="16px",
                    width="100%",
                    max_width=["90%", "460px"],  # Responsive max-width
                    box_shadow=f"0 20px 60px rgba(0, 0, 0, 0.5), 0 0 0 1px {S.BORDER_ACCENT}",
                    backdrop_filter="blur(20px)",
                    class_name="glass-reveal",  # Animation from animations.css
                ),
                align="center",
                justify="center",
                width="100%",
                max_width="500px",
                padding="24px",
                # Zoom-out effect to ensure fit
                transform="scale(0.9)",
                transform_origin="center center",
            ),
            width="100%",
            height="100vh",  # Changed back to height to lock the viewport
            z_index="2",
            position="relative",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        # Base background
        position="relative",
        width="100%",
        height="100vh",
        bg=S.BG_VOID,
        overflow="hidden",  # No scrollbars for login
    )
