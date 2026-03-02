import reflex as rx

from bomtempo.state.voice_chat_state import VoiceChatState

# --- CSS Animations ---
ANIMATIONS_CSS = """
@keyframes pulse-ring {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 65, 54, 0.7); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 20px rgba(255, 65, 54, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 65, 54, 0); }
}
@keyframes spin { 
    100% { -webkit-transform: rotate(360deg); transform:rotate(360deg); } 
}
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
    100% { transform: translateY(0px); }
}
"""


def message_bubble(message: dict) -> rx.Component:
    is_user = message["role"] == "user"
    return rx.box(
        rx.text(message["content"], color="white", font_size="md", line_height="1.5"),
        padding="4",
        border_radius="2xl",
        border_bottom_right_radius=rx.cond(is_user, "0", "2xl"),
        border_bottom_left_radius=rx.cond(is_user, "2xl", "0"),
        background=rx.cond(
            is_user,
            "linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)",  # Blue Gradient
            "rgba(255, 255, 255, 0.1)",  # Glassmorphism
        ),
        backdrop_filter="blur(10px)",
        max_width="85%",
        align_self=rx.cond(is_user, "flex-end", "flex-start"),
        box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        animation="float 0.3s ease-out",
    )


def mic_button() -> rx.Component:
    """Botão Central de Microfone com Animações de Estado"""
    return rx.box(
        rx.cond(
            VoiceChatState.is_listening,
            # Estado: OUVINDO (Botão Pulsante)
            rx.button(
                rx.icon("mic", size=48, color="white"),
                on_click=VoiceChatState.stop_listening,
                width="120px",
                height="120px",
                border_radius="full",
                background="linear-gradient(135deg, #EF4444 0%, #DC2626 100%)",
                box_shadow="0 0 30px rgba(239, 68, 68, 0.5)",
                animation="pulse-ring 2s infinite",
                _hover={"transform": "scale(1.05)"},
                transition="all 0.3s ease",
            ),
            # Estado: PARADO ou PROCESSANDO
            rx.button(
                rx.cond(
                    VoiceChatState.is_processing,
                    rx.spinner(color="white", size="3"),  # Spinner quando processando
                    rx.icon("mic", size=48, color="white"),  # Mic quando idle
                ),
                on_click=VoiceChatState.start_listening,
                disabled=VoiceChatState.is_processing,
                width="120px",
                height="120px",
                border_radius="full",
                background=rx.cond(
                    VoiceChatState.is_processing,
                    "gray.700",
                    "linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)",
                ),
                box_shadow="0 10px 25px -5px rgba(59, 130, 246, 0.5)",
                _hover={
                    "transform": "scale(1.05)",
                    "box_shadow": "0 20px 25px -5px rgba(59, 130, 246, 0.6)",
                },
                transition="all 0.3s ease",
            ),
        ),
        position="relative",
        z_index="10",
    )


def status_text() -> rx.Component:
    return rx.center(
        rx.cond(
            VoiceChatState.is_listening,
            rx.text(
                "Ouvindo... Toque para parar",
                color="red.400",
                font_weight="medium",
                animation="float 2s infinite",
            ),
            rx.cond(
                VoiceChatState.is_processing,
                rx.text("Pensando...", color="blue.300", font_style="italic"),
                rx.text("Toque para falar", color="gray.400"),
            ),
        ),
        padding_bottom="4",
    )


def chat_interface():
    return rx.box(
        # Inject CSS
        rx.html(f"<style>{ANIMATIONS_CSS}</style>"),
        # Bridge Inputs (Hidden)
        rx.input(
            id="voice_transcript_input", on_change=VoiceChatState.process_transcript, display="none"
        ),
        rx.input(
            id="voice_status_input", on_change=VoiceChatState.on_voice_status_change, display="none"
        ),
        # Main Layout
        rx.vstack(
            # Header
            rx.hstack(
                rx.heading("Voice AI", size="6", color="white", letter_spacing="-0.02em"),
                rx.spacer(),
                rx.badge("BETA", variant="soft", color_scheme="blue", border_radius="full"),
                padding="6",
                width="100%",
                z_index="20",
                background="rgba(15, 23, 42, 0.8)",
                backdrop_filter="blur(10px)",
                border_bottom="1px solid rgba(255,255,255,0.05)",
            ),
            # Chat Area
            rx.box(
                rx.vstack(
                    rx.foreach(VoiceChatState.messages, message_bubble),
                    # Spacer invisível para garantir rolagem até o fim
                    rx.box(height="150px"),
                    spacing="6",
                    width="100%",
                    padding_x="6",
                ),
                height="100%",
                width="100%",
                overflow_y="auto",
                scroll_behavior="smooth",
                mask="linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)",
            ),
            # Footer Interaction Area
            rx.center(
                rx.vstack(status_text(), mic_button(), spacing="4", align="center"),
                position="absolute",
                bottom="40px",
                left="0",
                right="0",
                padding="4",
                background="linear-gradient(to top, #0f172a 0%, rgba(15,23,42,0) 100%)",
                height="250px",
                pointer_events="none",  # Click-through gradient
            ),
            height="100vh",
            width="100%",
            background="#0f172a",  # Slate 900
            position="relative",
            overflow="hidden",
        ),
    )


def voice_chat_page() -> rx.Component:
    return rx.container(chat_interface(), padding="0", max_width="100%")
