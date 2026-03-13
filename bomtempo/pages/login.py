import reflex as rx

from bomtempo.components.sidebar import typewriter
from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


# ─────────────────────────────────────────────────────────────
# Left Brand Panel — matches enterprise-preview.html
# ─────────────────────────────────────────────────────────────

def _stat_item(label: str, value: str, color: str) -> rx.Component:
    """Single stat cell in the 2×2 grid."""
    return rx.vstack(
        rx.text(
            label,
            font_size="clamp(8px, 0.7vw, 9px)",
            font_weight="700",
            letter_spacing="0.15em",
            color=S.TEXT_MUTED,
            text_transform="uppercase",
            font_family=S.FONT_MONO,
        ),
        rx.text(
            value,
            font_family=S.FONT_TECH,
            font_size="clamp(1.1rem, 2vw, 1.75rem)",
            font_weight="900",
            color=color,
            line_height="1",
        ),
        spacing="1",
        padding="clamp(10px, 1.2vw, 16px)",
        bg="rgba(255,255,255,0.02)",
        border=f"1px solid {S.BORDER_SUBTLE}",
        border_radius=S.R_CONTROL,
        align="start",
        width="100%",
    )


def _brand_panel() -> rx.Component:
    """Left decorative brand + stats panel (hidden on mobile)."""
    return rx.box(
        # Grid background (decorative)
        rx.box(
            position="absolute",
            top="0", left="0", right="0", bottom="0",
            opacity="0.04",
            background_image=(
                "linear-gradient(rgba(201,139,42,0.6) 1px, transparent 1px),"
                " linear-gradient(90deg, rgba(201,139,42,0.6) 1px, transparent 1px)"
            ),
            background_size="48px 48px",
            pointer_events="none",
        ),
        # Copper glow orb — top left
        rx.box(
            position="absolute",
            top="-80px", left="-80px",
            width="320px", height="320px",
            border_radius="50%",
            bg="rgba(201, 139, 42, 0.06)",
            filter="blur(80px)",
            pointer_events="none",
        ),
        # Patina glow orb — bottom right
        rx.box(
            position="absolute",
            bottom="-60px", right="-60px",
            width="250px", height="250px",
            border_radius="50%",
            bg="rgba(42, 157, 143, 0.05)",
            filter="blur(70px)",
            pointer_events="none",
        ),
        # Right border accent
        rx.box(
            position="absolute",
            top="0", right="0",
            width="1px", height="100%",
            bg="linear-gradient(180deg, transparent, rgba(201,139,42,0.3) 30%, rgba(201,139,42,0.3) 70%, transparent)",
        ),
        # ── Panel content ────────────────────────────────────────
        rx.vstack(
            # Section label
            rx.hstack(
                rx.box(width="24px", height="1px", bg=S.PATINA),
                rx.text(
                    "PLATAFORMA OPERACIONAL",
                    font_size="9px",
                    font_weight="700",
                    letter_spacing="0.22em",
                    color=S.PATINA,
                    text_transform="uppercase",
                    font_family=S.FONT_MONO,
                ),
                spacing="3",
                align="center",
            ),
            # Brand hero — banner da nova identidade visual
            rx.image(
                src="/banner.png",
                max_width="min(360px, 80%)",
                max_height="clamp(80px, 22vh, 200px)",
                width="100%",
                object_fit="contain",
                opacity="0.95",
            ),
            # Subtitle
            rx.text(
                "Intelligence Platform v2.0",
                font_size="clamp(0.6rem, 1vw, 0.72rem)",
                letter_spacing="0.18em",
                color=S.TEXT_MUTED,
                font_family=S.FONT_MONO,
            ),
            # Description
            rx.text(
                "Plataforma centralizada de dados operacionais, controle financeiro e analytics preditivo para gestão de obras e contratos de engenharia.",
                font_size="clamp(0.75rem, 1.1vw, 0.85rem)",
                color="rgba(255,255,255,0.45)",
                line_height="1.6",
                width="100%",
            ),
            # Typewriter tagline
            rx.hstack(
                rx.text(
                    "Transformando dados em",
                    font_size="0.8rem",
                    color="rgba(255, 255, 255, 0.3)",
                    font_family=S.FONT_BODY,
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
                            ],
                            "autoStart": True,
                            "loop": True,
                            "delay": 50,
                            "deleteSpeed": 30,
                            "cursor": "|",
                        }
                    ),
                    font_size="0.9rem",
                    font_weight="700",
                    color=S.COPPER,
                    font_family=S.FONT_TECH,
                ),
                spacing="2",
                align="center",
            ),
            # Stats grid 2×2
            rx.grid(
                _stat_item("CONTRATOS ATIVOS", "147", S.COPPER),
                _stat_item("RDOS PROCESSADOS", "8.4k", S.PATINA),
                _stat_item("VOLUME GERENCIADO", "R$ 2.1B", S.COPPER),
                _stat_item("UPTIME", "99.97%", S.PATINA),
                columns="2",
                spacing="3",
                width="100%",
            ),
            rx.spacer(),
            # Bottom status ticker
            rx.hstack(
                rx.box(
                    width="6px", height="6px",
                    border_radius="50%",
                    bg=S.PATINA,
                    flex_shrink="0",
                    class_name="animate-pulse",
                ),
                rx.text(
                    "SISTEMAS OPERACIONAIS  ·  INFRAESTRUTURA OK  ·  UTC-3 BRT",
                    font_size="10px",
                    color=S.TEXT_MUTED,
                    font_family=S.FONT_MONO,
                    letter_spacing="0.08em",
                    opacity="0.55",
                ),
                spacing="2",
                align="center",
            ),
            spacing="3",
            padding=["24px 20px", "28px 24px", "32px 28px", "48px 40px"],
            position="relative",
            z_index="1",
            align="start",
            justify="start",
            class_name="login-brand-inner",
        ),
        position="relative",
        overflow="hidden",
        bg=S.BG_DEPTH,
        width="50%",
        height="100%",
        display=["none", "none", "none", "flex"],
        flex_direction="column",
    )


# ─────────────────────────────────────────────────────────────
# Right Auth Panel
# ─────────────────────────────────────────────────────────────

def _auth_panel() -> rx.Component:
    """Right side authentication form panel."""
    return rx.box(
        rx.center(
            rx.vstack(
                # Mobile-only logo badge
                rx.box(
                    rx.hstack(
                        rx.icon(tag="zap", size=16, color=S.COPPER),
                        rx.text(
                            "BOMTEMPO",
                            font_family=S.FONT_TECH,
                            font_size="1rem",
                            font_weight="900",
                            color=S.COPPER,
                            letter_spacing="0.1em",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    display=["flex", "flex", "none"],
                    margin_bottom="32px",
                ),
                # Section label
                rx.text(
                    "ACESSO SEGURO",
                    font_size="9px",
                    font_weight="700",
                    letter_spacing="0.22em",
                    color=S.PATINA,
                    text_transform="uppercase",
                    font_family=S.FONT_MONO,
                ),
                # Title
                rx.text(
                    "Autentique-se",
                    font_family=S.FONT_BODY,
                    font_size="2rem",
                    font_weight="700",
                    color="white",
                    line_height="1.1",
                    margin_top="-4px",
                ),
                # Username input
                rx.vstack(
                    rx.text(
                        "USUÁRIO",
                        font_size="9px",
                        font_weight="700",
                        letter_spacing="0.18em",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        font_family=S.FONT_MONO,
                    ),
                    rx.input(
                        placeholder="Digite seu usuário",
                        value=GlobalState.username_input,
                        on_change=GlobalState.set_username_input,
                        bg="rgba(255, 255, 255, 0.04)",
                        border=f"1px solid {S.BORDER_SUBTLE}",
                        color="white",
                        width="100%",
                        height="44px",
                        padding_x="14px",
                        border_radius=S.R_CONTROL,
                        font_family=S.FONT_MONO,
                        font_size="13px",
                        transition="border-color 0.15s ease",
                        is_disabled=GlobalState.is_authenticating,
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                # Password input
                rx.vstack(
                    rx.text(
                        "SENHA",
                        font_size="9px",
                        font_weight="700",
                        letter_spacing="0.18em",
                        color=S.TEXT_MUTED,
                        text_transform="uppercase",
                        font_family=S.FONT_MONO,
                    ),
                    rx.input(
                        placeholder="••••••••",
                        type="password",
                        value=GlobalState.password_input,
                        on_change=GlobalState.set_password_input,
                        bg="rgba(255, 255, 255, 0.04)",
                        border=rx.cond(
                            GlobalState.login_error != "",
                            "1px solid rgba(239, 68, 68, 0.5)",
                            f"1px solid {S.BORDER_SUBTLE}",
                        ),
                        color="white",
                        width="100%",
                        height="44px",
                        padding_x="14px",
                        border_radius=S.R_CONTROL,
                        font_family=S.FONT_MONO,
                        font_size="13px",
                        on_key_down=GlobalState.check_login_on_enter,
                        transition="border-color 0.15s ease",
                        is_disabled=GlobalState.is_authenticating,
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                # Login button + progress bar
                rx.vstack(
                    rx.button(
                        rx.hstack(
                            rx.cond(
                                GlobalState.is_authenticating,
                                rx.spinner(size="1", color="inherit"),
                                rx.icon(tag="log-in", size=16),
                            ),
                            rx.text(
                                rx.cond(
                                    GlobalState.login_error != "",
                                    "TENTAR NOVAMENTE",
                                    "ENTRAR",
                                ),
                                font_family=S.FONT_TECH,
                                font_weight="700",
                                font_size="14px",
                                letter_spacing="0.1em",
                            ),
                            spacing="3",
                            align="center",
                            justify="center",
                        ),
                        on_click=GlobalState.check_login,
                        bg=rx.cond(
                            GlobalState.is_authenticating,
                            "rgba(201, 139, 42, 0.15)",
                            f"linear-gradient(135deg, {S.COPPER}, {S.COPPER_LIGHT})",
                        ),
                        color=rx.cond(GlobalState.is_authenticating, S.COPPER, "#0A1F1A"),
                        border=rx.cond(
                            GlobalState.is_authenticating,
                            f"1px solid {S.COPPER}",
                            "1px solid transparent",
                        ),
                        width="100%",
                        height="48px",
                        border_radius=S.R_CONTROL,
                        cursor=rx.cond(GlobalState.is_authenticating, "not-allowed", "pointer"),
                        is_disabled=GlobalState.is_authenticating,
                        transition="all 0.2s ease",
                        _hover=rx.cond(
                            GlobalState.is_authenticating,
                            {},
                            {"opacity": "0.92", "transform": "translateY(-1px)"},
                        ),
                    ),
                    # Auth progress bar — visible only while authenticating
                    rx.cond(
                        GlobalState.is_authenticating,
                        rx.box(
                            rx.box(class_name="auth-progress-fill"),
                            width="100%",
                            height="2px",
                            bg="rgba(255,255,255,0.05)",
                            border_radius="0",
                            overflow="hidden",
                        ),
                        rx.box(height="2px"),
                    ),
                    spacing="0",
                    width="100%",
                    gap="6px",
                ),
                # Error message — below button, red bordered
                rx.cond(
                    GlobalState.login_error != "",
                    rx.hstack(
                        rx.icon(tag="circle-alert", size=13, color="#EF4444"),
                        rx.text(
                            GlobalState.login_error,
                            color="#EF4444",
                            font_size="12px",
                            font_weight="500",
                            font_family=S.FONT_MONO,
                        ),
                        spacing="2",
                        align="center",
                        padding="10px 14px",
                        bg="rgba(239, 68, 68, 0.06)",
                        border=f"1px solid rgba(239, 68, 68, 0.25)",
                        border_radius=S.R_CONTROL,
                        width="100%",
                    ),
                ),
                # Footer note
                rx.text(
                    "BOMTEMPO INTELLIGENCE  ·  PLATAFORMA RESTRITA  ·  ACESSO MONITORADO",
                    font_size="9px",
                    color=S.TEXT_MUTED,
                    text_align="center",
                    font_family=S.FONT_MONO,
                    letter_spacing="0.1em",
                    opacity="0.4",
                    margin_top="8px",
                ),
                spacing="5",
                width="100%",
                max_width="460px",
                class_name="glass-reveal",
            ),
            width="100%",
            height="100%",
            padding="48px 40px",
        ),
        flex="1",
        bg=S.BG_ELEVATED,
        height="100%",
        border_left=f"1px solid {S.BORDER_SUBTLE}",
        display="flex",
        align_items="center",
        justify_content="center",
    )


# ─────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────

def login_page() -> rx.Component:
    """Enterprise split-screen login — brand panel left, auth panel right."""
    return rx.box(
        rx.flex(
            _brand_panel(),
            _auth_panel(),
            direction="row",
            width="100%",
            height="100vh",
        ),
        position="relative",
        width="100%",
        height="100vh",
        bg=S.BG_VOID,
        overflow="hidden",
    )
