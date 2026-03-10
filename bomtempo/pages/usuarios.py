"""
Página de Gerenciamento de Usuários e Perfis — Admin only.
Tab 1: Usuários (CRUD na tabela login)
Tab 2: Perfis de Acesso (CRUD na tabela roles com seleção de módulos)
"""
import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState
from bomtempo.state.usuarios_state import AVATAR_ICONS, MODULES, UsuariosState


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────


def _role_badge(role: str) -> rx.Component:
    color = rx.cond(
        role == "Administrador",
        "amber",
        rx.cond(
            (role == "Engenheiro") | (role == "engenheiro"),
            "teal",
            rx.cond(
                role == "Mestre de Obras",
                "blue",
                rx.cond(role == "", "gray", "bronze"),
            ),
        ),
    )
    variant = rx.cond(role == "", "surface", "solid")
    return rx.cond(
        role != "",
        rx.badge(role, color_scheme=color, variant=variant, size="1"),
        rx.text("—", font_size="13px", color="rgba(255,255,255,0.25)"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# User dialog
# ─────────────────────────────────────────────────────────────────────────────


def _user_form_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.icon(
                        tag=rx.cond(UsuariosState.is_editing_user, "user-pen", "user-plus"),
                        size=18,
                        color=S.COPPER,
                    ),
                    rx.text(
                        rx.cond(UsuariosState.is_editing_user, "Editar Usuário", "Novo Usuário"),
                        font_family=S.FONT_TECH,
                        font_size="1.05rem",
                        font_weight="700",
                        color="white",
                    ),
                    rx.spacer(),
                    rx.icon_button(
                        rx.icon(tag="x", size=16),
                        on_click=UsuariosState.close_user_dialog,
                        variant="ghost",
                        color_scheme="amber",
                        size="2",
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="12px",
                ),
                # Error
                rx.cond(
                    UsuariosState.user_form_error != "",
                    rx.callout.root(
                        rx.callout.icon(rx.icon(tag="triangle-alert", size=14)),
                        rx.callout.text(UsuariosState.user_form_error),
                        color_scheme="red",
                        variant="soft",
                        size="1",
                        width="100%",
                    ),
                ),
                # Login
                rx.vstack(
                    rx.text("Login", font_size="12px", font_weight="600", color=S.TEXT_MUTED),
                    rx.input(
                        placeholder="nome.sobrenome",
                        value=UsuariosState.edit_user_login,
                        on_change=UsuariosState.set_edit_user_login,
                        width="100%",
                        color_scheme="amber",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Password
                rx.vstack(
                    rx.text(
                        rx.cond(
                            UsuariosState.is_editing_user,
                            "Nova Senha (vazio = manter atual)",
                            "Senha",
                        ),
                        font_size="12px",
                        font_weight="600",
                        color=S.TEXT_MUTED,
                    ),
                    rx.input(
                        placeholder="senha",
                        type="password",
                        value=UsuariosState.edit_user_password,
                        on_change=UsuariosState.set_edit_user_password,
                        width="100%",
                        color_scheme="amber",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Role
                rx.vstack(
                    rx.text("Perfil de Acesso", font_size="12px", font_weight="600", color=S.TEXT_MUTED),
                    rx.select.root(
                        rx.select.trigger(width="100%", color_scheme="amber"),
                        rx.select.content(
                            rx.foreach(
                                UsuariosState.roles_list,
                                lambda r: rx.select.item(r["name"], value=r["name"]),
                            )
                        ),
                        value=UsuariosState.edit_user_role,
                        on_change=UsuariosState.set_edit_user_role,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Project (contract dropdown)
                rx.vstack(
                    rx.text(
                        "Contrato associado",
                        font_size="12px",
                        font_weight="600",
                        color=S.TEXT_MUTED,
                    ),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecionar contrato (opcional)",
                            width="100%",
                            color_scheme="amber",
                        ),
                        rx.select.content(
                            rx.select.item("Nenhum", value="__none__"),
                            rx.foreach(
                                GlobalState.contract_ids_list,
                                lambda c: rx.select.item(c, value=c),
                            ),
                        ),
                        value=UsuariosState.edit_user_project,
                        on_change=UsuariosState.set_edit_user_project,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Actions
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        on_click=UsuariosState.close_user_dialog,
                        variant="ghost",
                        color_scheme="gray",
                    ),
                    rx.button(
                        rx.cond(UsuariosState.is_editing_user, "Salvar", "Criar Usuário"),
                        on_click=UsuariosState.save_user,
                        color_scheme="amber",
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                    margin_top="8px",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="440px",
            background=S.BG_ELEVATED,
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        open=UsuariosState.show_user_dialog,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Role dialog
# ─────────────────────────────────────────────────────────────────────────────


def _module_checkbox(module: tuple) -> rx.Component:
    """Single module checkbox row."""
    slug = module[0]
    label = module[1]
    icon_tag = module[2]
    is_checked = UsuariosState.edit_role_modules.contains(slug)
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=is_checked,
                on_change=lambda _: UsuariosState.toggle_module(slug),
                color_scheme="amber",
                size="2",
            ),
            rx.icon(tag=icon_tag, size=14, color=rx.cond(is_checked, S.COPPER, S.TEXT_MUTED)),
            rx.text(
                label,
                font_size="13px",
                color=rx.cond(is_checked, "white", S.TEXT_MUTED),
                font_weight=rx.cond(is_checked, "600", "400"),
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        padding="8px 10px",
        border_radius="8px",
        bg=rx.cond(is_checked, "rgba(201,139,42,0.08)", "transparent"),
        border=rx.cond(is_checked, "1px solid rgba(201,139,42,0.3)", "1px solid transparent"),
        cursor="pointer",
        on_click=UsuariosState.toggle_module(slug),
        width="100%",
        transition="all 0.15s ease",
    )


def _role_icon_btn(item: tuple) -> rx.Component:
    """Single icon button in the role icon picker grid."""
    slug = item[0]
    label = item[1]
    is_sel = UsuariosState.edit_role_icon == slug
    return rx.tooltip(
        rx.box(
            rx.icon(tag=slug, size=15, color=rx.cond(is_sel, S.COPPER, S.TEXT_MUTED)),
            width="34px",
            height="34px",
            border_radius="8px",
            bg=rx.cond(is_sel, "rgba(201,139,42,0.15)", "rgba(255,255,255,0.04)"),
            border=rx.cond(is_sel, f"1.5px solid {S.COPPER}", "1.5px solid transparent"),
            display="flex",
            align_items="center",
            justify_content="center",
            cursor="pointer",
            on_click=UsuariosState.set_edit_role_icon(slug),
            transition="all 0.12s ease",
            _hover={"bg": "rgba(201,139,42,0.1)"},
        ),
        content=label,
    )


def _role_icon_picker() -> rx.Component:
    """Icon selection grid for the role form dialog."""
    return rx.vstack(
        rx.hstack(
            rx.text("Ícone do Perfil", font_size="12px", font_weight="600", color=S.TEXT_MUTED),
            rx.hstack(
                rx.icon(tag=UsuariosState.edit_role_icon, size=14, color=S.COPPER),
                rx.text(UsuariosState.edit_role_icon, font_size="11px", font_family=S.FONT_MONO, color=S.TEXT_MUTED),
                spacing="2",
                align="center",
            ),
            width="100%",
            justify="between",
            align="center",
        ),
        rx.flex(
            *[_role_icon_btn(item) for item in AVATAR_ICONS],
            wrap="wrap",
            gap="5px",
            width="100%",
        ),
        spacing="2",
        width="100%",
    )


def _role_form_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.icon(
                        tag=rx.cond(UsuariosState.is_editing_role, "shield-check", "shield-plus"),
                        size=18,
                        color=S.COPPER,
                    ),
                    rx.text(
                        rx.cond(
                            UsuariosState.is_editing_role,
                            "Editar Perfil de Acesso",
                            "Novo Perfil de Acesso",
                        ),
                        font_family=S.FONT_TECH,
                        font_size="1.05rem",
                        font_weight="700",
                        color="white",
                    ),
                    rx.spacer(),
                    rx.icon_button(
                        rx.icon(tag="x", size=16),
                        on_click=UsuariosState.close_role_dialog,
                        variant="ghost",
                        color_scheme="amber",
                        size="2",
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="12px",
                ),
                # Error
                rx.cond(
                    UsuariosState.role_form_error != "",
                    rx.callout.root(
                        rx.callout.icon(rx.icon(tag="triangle-alert", size=14)),
                        rx.callout.text(UsuariosState.role_form_error),
                        color_scheme="red",
                        variant="soft",
                        size="1",
                        width="100%",
                    ),
                ),
                # Role name
                rx.vstack(
                    rx.text("Nome do Perfil", font_size="12px", font_weight="600", color=S.TEXT_MUTED),
                    rx.input(
                        placeholder='ex: "Gerente de Obra 1"',
                        value=UsuariosState.edit_role_name,
                        on_change=UsuariosState.set_edit_role_name,
                        width="100%",
                        color_scheme="amber",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Icon picker
                _role_icon_picker(),
                # Modules header
                rx.hstack(
                    rx.text(
                        "Módulos com acesso",
                        font_size="12px",
                        font_weight="600",
                        color=S.TEXT_MUTED,
                    ),
                    rx.spacer(),
                    rx.badge(
                        UsuariosState.edit_role_modules.length().to_string()
                        + " / "
                        + str(len(MODULES)),
                        color_scheme="amber",
                        variant="soft",
                        size="1",
                    ),
                    width="100%",
                    align="center",
                ),
                # Modules grid (2 columns)
                rx.box(
                    rx.grid(
                        *[_module_checkbox(m) for m in MODULES],
                        columns="2",
                        spacing="1",
                        width="100%",
                    ),
                    max_height="320px",
                    overflow_y="auto",
                    padding="4px",
                    border=f"1px solid {S.BORDER_SUBTLE}",
                    border_radius="10px",
                    width="100%",
                    class_name="no-scrollbar",
                ),
                # Actions
                rx.hstack(
                    rx.button(
                        "Cancelar",
                        on_click=UsuariosState.close_role_dialog,
                        variant="ghost",
                        color_scheme="gray",
                    ),
                    rx.button(
                        rx.cond(UsuariosState.is_editing_role, "Salvar", "Criar Perfil"),
                        on_click=UsuariosState.save_role,
                        color_scheme="amber",
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                    margin_top="8px",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="620px",
            background=S.BG_ELEVATED,
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        open=UsuariosState.show_role_dialog,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Usuários
# ─────────────────────────────────────────────────────────────────────────────


def _user_row(user: dict) -> rx.Component:
    role = user["user_role"]
    avatar_color = rx.cond(
        role == "Administrador", "amber",
        rx.cond(
            (role == "Engenheiro") | (role == "engenheiro"), "teal",
            rx.cond(
                role == "Mestre de Obras", "blue",
                rx.cond(
                    role == "solicitacao_reembolso", "grass",
                    rx.cond(role == "data_edit", "violet", "bronze"),
                ),
            ),
        ),
    )
    badge_bg = rx.cond(
        role == "Administrador", "#C98B2A",
        rx.cond(
            (role == "Engenheiro") | (role == "engenheiro"), "#2A9D8F",
            rx.cond(
                role == "Mestre de Obras", "#3B82F6",
                rx.cond(
                    role == "solicitacao_reembolso", "#22c55e",
                    rx.cond(role == "data_edit", "#8B5CF6", "#92683a"),
                ),
            ),
        ),
    )
    role_icon = rx.cond(
        role == "Administrador", "shield-check",
        rx.cond(
            (role == "Engenheiro") | (role == "engenheiro"), "hard-hat",
            rx.cond(
                role == "Mestre de Obras", "hammer",
                rx.cond(
                    role == "solicitacao_reembolso", "fuel",
                    rx.cond(role == "data_edit", "database", "user"),
                ),
            ),
        ),
    )
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    rx.avatar(
                        fallback=user["user"][0].upper(),
                        size="2",
                        radius="full",
                        variant="soft",
                        color_scheme=avatar_color,
                    ),
                    rx.box(
                        rx.icon(tag=role_icon, size=8, color="white"),
                        position="absolute",
                        bottom="-2px",
                        right="-2px",
                        width="14px",
                        height="14px",
                        border_radius="50%",
                        bg=badge_bg,
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        border="1.5px solid #0E1A17",
                    ),
                    position="relative",
                    display="inline-flex",
                    flex_shrink="0",
                ),
                rx.text(user["user"], font_weight="600", color="white", font_size="14px"),
                spacing="3",
                align="center",
            )
        ),
        rx.table.cell(_role_badge(user["user_role"])),
        rx.table.cell(
            rx.text(
                rx.cond(user["project"] != "", user["project"], "—"),
                font_size="13px",
                font_family=rx.cond(user["project"] != "", S.FONT_MONO, "inherit"),
                color=rx.cond(user["project"] != "", S.TEXT_MUTED, "rgba(255,255,255,0.2)"),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(
                    rx.icon(tag="pencil", size=13),
                    on_click=UsuariosState.open_edit_user_dialog(user["id"]),
                    variant="ghost",
                    color_scheme="amber",
                    size="2",
                ),
                rx.icon_button(
                    rx.icon(tag="trash-2", size=13),
                    on_click=UsuariosState.delete_user(user["id"]),
                    variant="ghost",
                    color_scheme="red",
                    size="2",
                ),
                spacing="1",
            )
        ),
    )


def _usuarios_tab() -> rx.Component:
    return rx.vstack(
        # Actions bar
        rx.hstack(
            rx.text(
                UsuariosState.users_list.length().to_string() + " usuários cadastrados",
                font_size="13px",
                color=S.TEXT_MUTED,
            ),
            rx.spacer(),
            rx.button(
                rx.icon(tag="plus", size=15),
                "Novo Usuário",
                on_click=UsuariosState.open_add_user_dialog,
                color_scheme="amber",
                size="2",
                variant="soft",
            ),
            width="100%",
            align="center",
        ),
        # Table
        rx.box(
            rx.cond(
                UsuariosState.users_loading,
                rx.center(rx.spinner(size="3"), width="100%", padding="40px"),
                rx.cond(
                    UsuariosState.users_list,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Usuário"),
                                rx.table.column_header_cell("Perfil"),
                                rx.table.column_header_cell("Projeto"),
                                rx.table.column_header_cell(""),
                            )
                        ),
                        rx.table.body(rx.foreach(UsuariosState.users_list, _user_row)),
                        variant="ghost",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon(tag="users", size=36, color=S.TEXT_MUTED),
                            rx.text("Nenhum usuário encontrado", color=S.TEXT_MUTED, font_size="14px"),
                            align="center",
                        ),
                        padding="48px",
                    ),
                ),
            ),
            background=S.BG_GLASS,
            border=f"1px solid {S.BORDER_SUBTLE}",
            border_radius="14px",
            overflow="hidden",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Perfis de Acesso
# ─────────────────────────────────────────────────────────────────────────────


def _role_row(role: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.center(
                    rx.icon(tag="shield-check", size=14, color=S.COPPER),
                    width="28px",
                    height="28px",
                    border_radius="8px",
                    bg=S.COPPER_GLOW,
                ),
                rx.text(role["name"], font_weight="600", color="white", font_size="14px"),
                spacing="3",
                align="center",
            )
        ),
        rx.table.cell(
            rx.badge(
                role["module_count"] + " módulos",
                color_scheme="amber",
                variant="solid",
                size="1",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(
                    rx.icon(tag="pencil", size=13),
                    on_click=UsuariosState.open_edit_role_dialog(role["id"]),
                    variant="ghost",
                    color_scheme="amber",
                    size="2",
                ),
                rx.icon_button(
                    rx.icon(tag="trash-2", size=13),
                    on_click=UsuariosState.delete_role(role["id"]),
                    variant="ghost",
                    color_scheme="red",
                    size="2",
                ),
                spacing="1",
            )
        ),
    )


def _perfis_tab() -> rx.Component:
    return rx.vstack(
        # Actions bar
        rx.hstack(
            rx.text(
                UsuariosState.roles_list.length().to_string() + " perfis configurados",
                font_size="13px",
                color=S.TEXT_MUTED,
            ),
            rx.spacer(),
            rx.button(
                rx.icon(tag="plus", size=15),
                "Novo Perfil",
                on_click=UsuariosState.open_add_role_dialog,
                color_scheme="amber",
                size="2",
                variant="soft",
            ),
            width="100%",
            align="center",
        ),
        # Table
        rx.box(
            rx.cond(
                UsuariosState.roles_loading,
                rx.center(rx.spinner(size="3"), width="100%", padding="40px"),
                rx.cond(
                    UsuariosState.roles_list,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Perfil"),
                                rx.table.column_header_cell("Acesso"),
                                rx.table.column_header_cell(""),
                            )
                        ),
                        rx.table.body(rx.foreach(UsuariosState.roles_list, _role_row)),
                        variant="ghost",
                        width="100%",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon(tag="shield-off", size=36, color=S.TEXT_MUTED),
                            rx.text("Nenhum perfil encontrado", color=S.TEXT_MUTED, font_size="14px"),
                            rx.text(
                                "Crie um perfil para definir quais módulos cada tipo de usuário pode acessar.",
                                color="rgba(255,255,255,0.3)",
                                font_size="12px",
                                text_align="center",
                                max_width="320px",
                            ),
                            align="center",
                            spacing="2",
                        ),
                        padding="48px",
                    ),
                ),
            ),
            background=S.BG_GLASS,
            border=f"1px solid {S.BORDER_SUBTLE}",
            border_radius="14px",
            overflow="hidden",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────────────


def usuarios_page() -> rx.Component:
    return rx.cond(
        GlobalState.current_user_role == "Administrador",
        rx.vstack(
            _user_form_dialog(),
            _role_form_dialog(),
            # Header
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.center(
                            rx.icon(tag="users", size=20, color="#0A1F1A"),
                            padding="8px",
                            bg=S.COPPER,
                            border_radius="8px",
                        ),
                        rx.text(
                            "Gerenciar Usuários",
                            font_family=S.FONT_TECH,
                            font_size="1.8rem",
                            font_weight="900",
                            color="white",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    rx.text(
                        "Crie perfis com acesso granular por módulo e atribua usuários a esses perfis.",
                        color=S.TEXT_MUTED,
                        font_size="14px",
                    ),
                    spacing="1",
                ),
                width="100%",
                align="start",
            ),
            # Tabs
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        rx.hstack(
                            rx.icon(tag="users", size=15),
                            rx.text("Usuários"),
                            spacing="2",
                            align="center",
                        ),
                        value="usuarios",
                    ),
                    rx.tabs.trigger(
                        rx.hstack(
                            rx.icon(tag="shield-check", size=15),
                            rx.text("Perfis de Acesso"),
                            spacing="2",
                            align="center",
                        ),
                        value="perfis",
                    ),
                    color_scheme="amber",
                ),
                rx.tabs.content(
                    _usuarios_tab(),
                    value="usuarios",
                    padding_top="20px",
                ),
                rx.tabs.content(
                    _perfis_tab(),
                    value="perfis",
                    padding_top="20px",
                ),
                value=UsuariosState.active_tab,
                on_change=UsuariosState.set_active_tab,
                width="100%",
            ),
            spacing="6",
            width="100%",
            class_name="animate-enter",
        ),
        rx.center(
            rx.text("Acesso restrito a Administradores.", color=S.TEXT_MUTED),
            padding="80px",
        ),
    )
