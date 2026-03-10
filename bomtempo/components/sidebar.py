import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


class Typewriter(rx.Component):
    library = "typewriter-effect"
    tag = "Typewriter"
    options: rx.Var[dict]
    is_default = True


typewriter = Typewriter.create


def sidebar_item(text: str, icon: str, url: str) -> rx.Component:
    """Sidebar navigation item with dynamic collapse support"""

    # Robust active logic
    current = rx.State.router.page.path
    is_root_path = (current == "/") | (current == "") | (current == "/index")
    is_path_match = (current == url) | (current == f"{url}/")
    is_active = rx.cond(url == "/", is_root_path, is_path_match)

    return rx.link(
        rx.hstack(
            rx.icon(tag=icon, size=20, color=rx.cond(is_active, S.COPPER, S.TEXT_MUTED)),
            rx.cond(
                GlobalState.sidebar_open,
                rx.text(
                    text,
                    font_family=S.FONT_TECH,
                    font_weight="700",
                    font_size="14px",
                    color=rx.cond(is_active, "white", S.TEXT_MUTED),
                    letter_spacing="0.05em",
                    white_space="nowrap",
                    opacity=rx.cond(GlobalState.sidebar_open, "1", "0"),
                    transition="opacity 0.2s ease",
                ),
            ),
            spacing="3",
            align="center",
            width="100%",
            padding_y="12px",
            padding_x=rx.cond(GlobalState.sidebar_open, "16px", "0"),
            justify=rx.cond(GlobalState.sidebar_open, "start", "center"),
            border_radius="12px",
            transition="all 0.2s ease",
            bg=rx.cond(
                is_active,
                "rgba(255, 255, 255, 0.05)",
                "transparent",
            ),
            border=rx.cond(
                is_active,
                f"1px solid {S.COPPER}",
                "1px solid transparent",
            ),
            _hover={
                "bg": "rgba(255, 255, 255, 0.03)",
                "color": "white",
            },
        ),
        href=url,
        width="100%",
        style={"text_decoration": "none"},
    )


def sidebar_content() -> rx.Component:
    """Content inside the sidebar"""
    return rx.vstack(
        # ── Header / Logo ──
        rx.vstack(
            rx.cond(
                GlobalState.sidebar_open,
                rx.vstack(
                    rx.text(
                        "BOMTEMPO",
                        font_size="1.8rem",
                        font_weight="900",
                        font_family=S.FONT_TECH,
                        letter_spacing="0.1em",
                        color=S.COPPER,
                        line_height="1",
                    ),
                    rx.text(
                        "INTELLIGENCE",
                        font_size="0.85rem",
                        font_weight="700",
                        font_family=S.FONT_TECH,
                        letter_spacing="0.3em",
                        color=S.PATINA,
                        margin_top="2px",
                    ),
                    # ── Typewriter Effect ──
                    rx.vstack(
                        rx.text(
                            "Transformando dados em",
                            font_size="0.75rem",
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
                            font_size="1rem",
                            font_weight="bold",
                            color=S.COPPER,
                            font_family=S.FONT_TECH,
                        ),
                        spacing="0",
                        align="center",
                        margin_top="12px",
                    ),
                    align="center",
                    spacing="0",
                    width="100%",
                ),
                # Collapsed Logo (Simple "B")
                rx.text(
                    "B",
                    font_size="2rem",
                    font_weight="900",
                    font_family=S.FONT_TECH,
                    color=S.COPPER,
                ),
            ),
            align="center",
            width="100%",
            padding_y="32px",
            padding_x="24px",
            border_bottom=f"1px solid {S.BORDER_SUBTLE}",
            margin_bottom="16px",
        ),
        # ── Navigation (permission-based via allowed_modules) ──
        rx.vstack(
            rx.cond(
                GlobalState.allowed_modules.contains("visao_geral"),
                sidebar_item("VISÃO GERAL", "layout-dashboard", "/"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("obras"),
                sidebar_item("OBRAS", "hard-hat", "/obras"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("projetos"),
                sidebar_item("PROJETOS", "briefcase", "/projetos"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("financeiro"),
                sidebar_item("FINANCEIRO", "wallet", "/financeiro"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("om"),
                sidebar_item("O&M", "zap", "/om"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("analytics"),
                sidebar_item("ANALYTICS", "bar-chart-3", "/analytics"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("previsoes"),
                sidebar_item("PREVISÕES ML", "trending-up", "/previsoes"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("relatorios"),
                sidebar_item("RELATÓRIOS", "file-text", "/relatorios"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("chat_ia"),
                sidebar_item("CHAT IA", "message-square", "/chat-ia"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("reembolso"),
                sidebar_item("REEMBOLSO", "fuel", "/reembolso"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("reembolso_dash"),
                sidebar_item("REEMBOLSO DASH", "receipt", "/reembolso-dash"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("rdo_form"),
                sidebar_item("RDO DIÁRIO", "clipboard-list", "/rdo-form"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("rdo_historico"),
                sidebar_item("MEUS RDOS", "clock", "/rdo-historico"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("rdo_dashboard"),
                sidebar_item("RDO ANALYTICS", "chart-bar", "/rdo-dashboard"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("editar_dados"),
                sidebar_item("EDITAR DADOS", "database", "/admin/editar_dados"),
            ),
            width="100%",
            spacing="2",
            padding_x="16px",
            overflow_y="auto",
            flex="1",
            class_name="no-scrollbar",
        ),
        # ── User Info (with popover menu) ──
        rx.popover.root(
            rx.popover.trigger(
                rx.box(
                    rx.hstack(
                        rx.cond(
                            GlobalState.current_user_avatar_type == "icon",
                            rx.box(
                                rx.icon(
                                    tag=GlobalState.effective_avatar_icon,
                                    size=18,
                                    color=S.COPPER,
                                ),
                                width="36px",
                                height="36px",
                                border_radius="full",
                                bg="rgba(201,139,42,0.15)",
                                border="1.5px solid rgba(201,139,42,0.4)",
                                display="flex",
                                align_items="center",
                                justify_content="center",
                                flex_shrink="0",
                            ),
                            rx.avatar(
                                fallback=GlobalState.current_user_name.to_string()[0].upper(),
                                size="3",
                                radius="full",
                                variant="soft",
                                color_scheme="bronze",
                            ),
                        ),
                        rx.cond(
                            GlobalState.sidebar_open,
                            rx.hstack(
                                rx.vstack(
                                    rx.text(
                                        GlobalState.current_user_name,
                                        font_weight="bold",
                                        font_size="14px",
                                        color="white",
                                    ),
                                    rx.text(
                                        GlobalState.current_user_role,
                                        font_size="11px",
                                        color=S.TEXT_MUTED,
                                    ),
                                    spacing="0",
                                    align="start",
                                ),
                                rx.spacer(),
                                rx.icon(tag="chevron-up", size=14, color=S.TEXT_MUTED),
                                align="center",
                                width="100%",
                            ),
                        ),
                        spacing="3",
                        align="center",
                        justify=rx.cond(GlobalState.sidebar_open, "start", "center"),
                        width="100%",
                    ),
                    width="100%",
                    padding_x="24px",
                    padding_bottom="24px",
                    border_top=f"1px solid {S.BORDER_SUBTLE}",
                    padding_top="16px",
                    cursor="pointer",
                    _hover={"bg": "rgba(255,255,255,0.03)"},
                ),
            ),
            rx.popover.content(
                rx.vstack(
                    # Logs & Auditoria
                    rx.cond(
                        GlobalState.allowed_modules.contains("logs_auditoria"),
                        rx.link(
                            rx.hstack(
                                rx.icon(tag="shield-check", size=16, color=S.COPPER),
                                rx.text("Logs & Auditoria", font_size="14px", color="white"),
                                spacing="3",
                                align="center",
                            ),
                            href="/logs-auditoria",
                            style={"text_decoration": "none"},
                            width="100%",
                            padding="8px 12px",
                            border_radius="8px",
                            _hover={"bg": "rgba(255,255,255,0.06)"},
                        ),
                    ),
                    # Alertas
                    rx.cond(
                        GlobalState.allowed_modules.contains("alertas"),
                        rx.link(
                            rx.hstack(
                                rx.icon(tag="bell-ring", size=16, color=S.COPPER),
                                rx.text("Alertas", font_size="14px", color="white"),
                                spacing="3",
                                align="center",
                            ),
                            href="/alertas",
                            style={"text_decoration": "none"},
                            width="100%",
                            padding="8px 12px",
                            border_radius="8px",
                            _hover={"bg": "rgba(255,255,255,0.06)"},
                        ),
                    ),
                    # Gerenciar Usuários
                    rx.cond(
                        GlobalState.allowed_modules.contains("gerenciar_usuarios"),
                        rx.link(
                            rx.hstack(
                                rx.icon(tag="users", size=16, color=S.COPPER),
                                rx.text("Gerenciar Usuários", font_size="14px", color="white"),
                                spacing="3",
                                align="center",
                            ),
                            href="/admin/usuarios",
                            style={"text_decoration": "none"},
                            width="100%",
                            padding="8px 12px",
                            border_radius="8px",
                            _hover={"bg": "rgba(255,255,255,0.06)"},
                        ),
                    ),
                    # Meu Perfil
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="user-circle", size=16, color=S.COPPER),
                            rx.text("Meu Perfil", font_size="14px", color="white"),
                            spacing="3",
                            align="center",
                        ),
                        width="100%",
                        padding="8px 12px",
                        border_radius="8px",
                        cursor="pointer",
                        on_click=GlobalState.open_avatar_modal,
                        _hover={"bg": "rgba(255,255,255,0.06)"},
                    ),
                    # Alterar Senha
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="key-round", size=16, color=S.COPPER),
                            rx.text("Alterar Senha", font_size="14px", color="white"),
                            spacing="3",
                            align="center",
                        ),
                        width="100%",
                        padding="8px 12px",
                        border_radius="8px",
                        cursor="pointer",
                        on_click=GlobalState.open_password_modal,
                        _hover={"bg": "rgba(255,255,255,0.06)"},
                    ),
                    rx.separator(width="100%"),
                    # Logout
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="log-out", size=16, color="#EF4444"),
                            rx.text("Logout", font_size="14px", color="#EF4444"),
                            spacing="3",
                            align="center",
                        ),
                        width="100%",
                        padding="8px 12px",
                        border_radius="8px",
                        cursor="pointer",
                        on_click=GlobalState.logout,
                        _hover={"bg": "rgba(239,68,68,0.08)"},
                    ),
                    spacing="1",
                    width="200px",
                    padding="4px",
                ),
                bg=S.BG_ELEVATED,
                border=f"1px solid {S.BORDER_SUBTLE}",
                border_radius="12px",
                side="top",
                align="start",
                padding="8px",
            ),
        ),
        # ── Navigation ──
        height="100%",
        spacing="0",
        width="100%",
        align="center",
    )


def sidebar() -> rx.Component:
    """Desktop Sidebar (Hidden on mobile)"""
    return rx.box(
        sidebar_content(),
        # ── Toggle Button ──
        rx.box(
            rx.icon(
                tag=rx.cond(GlobalState.sidebar_open, "chevron-left", "chevron-right"),
                size=16,
                color=S.COPPER,
            ),
            on_click=GlobalState.toggle_sidebar,
            position="absolute",
            right="-12px",
            top="48px",
            bg=S.BG_ELEVATED,
            border=f"1px solid {S.BORDER_SUBTLE}",
            border_radius="50%",
            padding="6px",
            cursor="pointer",
            z_index="51",
            transition="transform 0.2s",
            _hover={"transform": "scale(1.1)", "borderColor": S.COPPER},
        ),
        # Properties
        width=rx.cond(GlobalState.sidebar_open, "240px", "88px"),
        height="100vh",
        position="sticky",
        top="0",
        left="0",
        bg=S.BG_ELEVATED,
        border_right=f"1px solid {S.BORDER_SUBTLE}",
        z_index="50",
        transition="width 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        display=["none", "none", "block"],  # Hide on Mobile/Tablet
    )


def mobile_sidebar() -> rx.Component:
    """Mobile Drawer Sidebar"""
    return rx.drawer.root(
        rx.drawer.trigger(
            rx.icon(tag="menu", size=24, color=S.COPPER),
        ),
        rx.drawer.overlay(),
        rx.drawer.portal(
            rx.drawer.content(
                rx.vstack(
                    # Close button
                    rx.box(
                        rx.drawer.close(rx.icon(tag="x", size=24, color=S.TEXT_MUTED)),
                        width="100%",
                        align_items="end",
                        display="flex",
                        justify_content="flex-end",
                        padding="16px",
                    ),
                    sidebar_content(),
                    height="100%",
                    width="100%",
                    spacing="0",
                ),
                bg=S.BG_ELEVATED,
                width="240px",
                height="100%",
                top="0",
                left="0",
                position="fixed",
                z_index="9999",
                border_right=f"1px solid {S.BORDER_SUBTLE}",
            )
        ),
        direction="left",
    )
