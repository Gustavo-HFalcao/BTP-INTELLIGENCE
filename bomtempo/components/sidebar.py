import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState


class Typewriter(rx.Component):
    library = "typewriter-effect"
    tag = "Typewriter"
    options: rx.Var[dict]
    is_default = True


typewriter = Typewriter.create


# ─────────────────────────────────────────────────────────────
# Section label helper
# ─────────────────────────────────────────────────────────────

def _section_label(label: str) -> rx.Component:
    """Micro-section label — visible when expanded, thin divider when collapsed."""
    return rx.cond(
        GlobalState.sidebar_open,
        rx.text(
            label,
            font_size="9px",
            font_weight="700",
            letter_spacing="0.2em",
            color=S.TEXT_MUTED,
            text_transform="uppercase",
            opacity="0.5",
            padding_x="16px",
            padding_top="20px",
            padding_bottom="4px",
            width="100%",
            class_name="sidebar-section-label",
        ),
        rx.box(
            width="32px",
            height="1px",
            bg=S.BORDER_SUBTLE,
            margin_y="10px",
            margin_x="auto",
        ),
    )


# ─────────────────────────────────────────────────────────────
# Sidebar item
# ─────────────────────────────────────────────────────────────

def sidebar_item(text: str, icon: str, url: str) -> rx.Component:
    """Sidebar navigation item with dynamic collapse support."""
    current = rx.State.router.page.path
    is_root_path = (current == "/") | (current == "") | (current == "/index")
    is_path_match = (current == url) | (current == f"{url}/")
    is_active = rx.cond(url == "/", is_root_path, is_path_match)

    return rx.link(
        rx.hstack(
            rx.icon(
                tag=icon, size=17,
                color=rx.cond(is_active, S.COPPER, S.TEXT_MUTED),
            ),
            rx.cond(
                GlobalState.sidebar_open,
                rx.text(
                    text,
                    font_family=S.FONT_TECH,
                    font_weight="700",
                    font_size="13px",
                    color=rx.cond(is_active, "white", S.TEXT_MUTED),
                    letter_spacing="0.04em",
                    white_space="nowrap",
                    opacity=rx.cond(GlobalState.sidebar_open, "1", "0"),
                    transition="opacity 0.2s ease",
                    class_name="font-tech",
                ),
            ),
            spacing="3",
            align="center",
            width="100%",
            padding_y="9px",
            padding_x=rx.cond(GlobalState.sidebar_open, "14px", "0"),
            justify=rx.cond(GlobalState.sidebar_open, "start", "center"),
            border_radius=S.R_CONTROL,
            transition="all 0.15s ease",
            bg=rx.cond(is_active, "rgba(201, 139, 42, 0.08)", "transparent"),
            border_left=rx.cond(is_active, f"2px solid {S.COPPER}", "2px solid transparent"),
            _hover={
                "bg": "rgba(255, 255, 255, 0.03)",
                "borderLeftColor": f"rgba(201,139,42,0.3)",
            },
        ),
        href=url,
        on_click=GlobalState.set_navigating,
        on_mouse_enter=GlobalState.prefetch_route(url),
        width="100%",
        style={"text_decoration": "none"},
    )


# ─────────────────────────────────────────────────────────────
# Sidebar content
# ─────────────────────────────────────────────────────────────

def sidebar_content() -> rx.Component:
    """Grouped sidebar content — 4 sections."""
    return rx.vstack(
        # ── Header / Logo ──────────────────────────────────────────────
        rx.box(
            rx.cond(
                GlobalState.sidebar_open,
                rx.image(
                    src="/banner.png",
                    width="100%",
                    height="100%",
                    object_fit="contain",
                    object_position="left center",
                    class_name="sidebar-logo-img",
                ),
                rx.center(
                    rx.image(
                        src="/icon.png",
                        width="32px",
                        height="32px",
                        border_radius=S.R_CONTROL,
                        object_fit="cover",
                        class_name="sidebar-logo-img",
                    ),
                ),
            ),
            width="100%",
            height="64px",
            display="flex",
            align_items="center",
            padding_x=rx.cond(GlobalState.sidebar_open, "16px", "8px"),
            border_bottom=f"1px solid {S.BORDER_SUBTLE}",
            flex_shrink="0",
        ),
        # ── Navigation ─────────────────────────────────────────────────
        rx.vstack(
            # PRINCIPAL
            _section_label("PRINCIPAL"),
            rx.cond(
                GlobalState.allowed_modules.contains("visao_geral"),
                sidebar_item("VISÃO GERAL", "layout-dashboard", "/"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("obras") | GlobalState.allowed_modules.contains("projetos"),
                sidebar_item("HUB DE OPERAÇÕES", "hard-hat", "/hub"),
            ),

            # OPERACIONAL
            _section_label("OPERACIONAL"),
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

            # RDO
            _section_label("RDO"),
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

            # ADMINISTRAÇÃO
            _section_label("ADMINISTRAÇÃO"),
            rx.cond(
                GlobalState.allowed_modules.contains("alertas"),
                sidebar_item("GESTÃO DE ALERTAS", "bell", "/alertas"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("logs_auditoria"),
                sidebar_item("LOGS & AUDITORIA", "shield-check", "/logs-auditoria"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("gerenciar_usuarios"),
                sidebar_item("FEATURE FLAGS", "toggle-right", "/admin/contract-features"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("editar_dados"),
                sidebar_item("EDITAR DADOS", "database", "/admin/editar_dados"),
            ),
            rx.cond(
                GlobalState.allowed_modules.contains("gerenciar_usuarios"),
                sidebar_item("OBSERVABILIDADE", "activity", "/admin/observabilidade"),
            ),

            spacing="1",
            width="100%",
            padding_x="10px",
            overflow_y="auto",
            flex="1",
            class_name="no-scrollbar",
            padding_bottom="12px",
        ),

        # Outer vstack props
        height="100%",
        spacing="0",
        width="100%",
        align="start",
    )


# ─────────────────────────────────────────────────────────────
# Desktop Sidebar
# ─────────────────────────────────────────────────────────────

def sidebar() -> rx.Component:
    """Desktop sidebar — flush to viewport, grouped sections."""
    return rx.box(
        sidebar_content(),
        # Toggle button
        rx.box(
            rx.icon(
                tag=rx.cond(GlobalState.sidebar_open, "chevron-left", "chevron-right"),
                size=13,
                color=S.COPPER,
            ),
            on_click=GlobalState.toggle_sidebar,
            position="absolute",
            right="-11px",
            top="52px",
            bg=S.BG_ELEVATED,
            border=f"1px solid {S.BORDER_SUBTLE}",
            border_radius=S.R_CONTROL,
            padding="5px",
            cursor="pointer",
            z_index="51",
            transition="all 0.15s ease",
            _hover={"border_color": S.COPPER, "bg": "rgba(201,139,42,0.08)"},
        ),
        # Container props
        width=rx.cond(GlobalState.sidebar_open, "236px", "64px"),
        height="100vh",
        position="sticky",
        top="0",
        left="0",
        bg=S.BG_ELEVATED,
        border_right=f"1px solid {S.BORDER_SUBTLE}",
        z_index="50",
        transition="width 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        display=["none", "none", "block"],
        overflow="visible",
    )


# ─────────────────────────────────────────────────────────────
# Mobile Drawer Sidebar
# ─────────────────────────────────────────────────────────────

def mobile_sidebar() -> rx.Component:
    """Mobile drawer sidebar."""
    return rx.drawer.root(
        rx.drawer.trigger(
            rx.icon(tag="menu", size=24, color=S.COPPER),
        ),
        rx.drawer.overlay(),
        rx.drawer.portal(
            rx.drawer.content(
                rx.vstack(
                    rx.box(
                        rx.drawer.close(rx.icon(tag="x", size=20, color=S.TEXT_MUTED)),
                        width="100%",
                        display="flex",
                        justify_content="flex-end",
                        padding="14px",
                    ),
                    sidebar_content(),
                    height="100%",
                    width="100%",
                    spacing="0",
                ),
                bg=S.BG_ELEVATED,
                width="236px",
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
