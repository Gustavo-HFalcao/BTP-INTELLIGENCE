"""
Página de Histórico de RDOs
"""

import reflex as rx

from bomtempo.core import styles as S
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.rdo_service import RDOService
from bomtempo.core.supabase_client import sb_delete, sb_insert, sb_select
from bomtempo.state.global_state import GlobalState

logger = get_logger(__name__)


class RDOHistoricoState(rx.State):
    """Estado da página de histórico"""

    rdos_list: list[dict] = []

    # ── Email Config Dialog ──────────────────────────────────
    show_email_config: bool = False
    email_config_list: list[dict] = []
    new_email_input: str = ""
    email_config_loading: bool = False
    email_config_error: str = ""

    async def load_rdos(self):
        """Carrega RDOs conforme role e contrato do usuário"""
        global_state = await self.get_state(GlobalState)
        current_role = str(global_state.current_user_role)
        current_contrato = str(global_state.current_user_contrato)

        # Admin/Gestor sem filtro de contrato (vazio ou "Todos") → vê tudo
        admin_roles = ["Administrador", "Gestão-Mobile", "Engenheiro"]
        if current_role in admin_roles and current_contrato.strip() in ["", "Todos", "nan", "None"]:
            self.rdos_list = RDOService.get_all_rdos(limit=100)
        elif current_role in admin_roles and current_contrato.strip():
            # Admin com contrato específico → filtra
            self.rdos_list = RDOService.get_rdos_by_contract(current_contrato.strip(), limit=100)
        elif current_role == "Mestre de Obras":
            self.rdos_list = RDOService.get_rdos_by_contract(current_contrato.strip(), limit=50)
        else:
            self.rdos_list = []

    # ── Email Config Methods ─────────────────────────────────

    async def open_email_config(self):
        """Abre dialog e carrega emails do contrato atual"""
        global_state = await self.get_state(GlobalState)
        current_contrato = str(global_state.current_user_contrato).strip()
        self.email_config_error = ""
        self.new_email_input = ""
        self.email_config_loading = True
        self.show_email_config = True
        yield

        try:
            rows = sb_select("email_sender", filters={"contract": current_contrato})
            self.email_config_list = rows or []
        except Exception as e:
            logger.error(f"Erro ao carregar emails: {e}")
            self.email_config_error = f"Erro ao carregar emails: {str(e)}"
            self.email_config_list = []
        finally:
            self.email_config_loading = False

    def close_email_config(self):
        """Fecha dialog de configuração de emails"""
        self.show_email_config = False
        self.new_email_input = ""
        self.email_config_error = ""

    async def add_email_recipient(self):
        """Adiciona novo email destinatário para o contrato"""
        email = self.new_email_input.strip()
        if not email or "@" not in email:
            self.email_config_error = "Digite um email válido"
            return

        global_state = await self.get_state(GlobalState)
        current_contrato = str(global_state.current_user_contrato).strip()
        current_user = str(global_state.current_user_name).strip()

        self.email_config_loading = True
        yield

        try:
            from datetime import datetime

            result = sb_insert(
                "email_sender",
                {
                    "contract": current_contrato,
                    "email": email,
                    "created_by": current_user,
                    "updated_date": datetime.now().isoformat(),
                },
            )
            if result:
                rows = sb_select("email_sender", filters={"contract": current_contrato})
                self.email_config_list = rows or []
                self.new_email_input = ""
                self.email_config_error = ""
                yield rx.toast(f"✅ Email adicionado: {email}", position="top-center")
            else:
                self.email_config_error = "Falha ao salvar email. Tente novamente."
        except Exception as e:
            logger.error(f"Erro ao adicionar email: {e}")
            self.email_config_error = f"Erro: {str(e)}"
        finally:
            self.email_config_loading = False

    async def delete_email_recipient(self, email_id: int):
        """Remove email destinatário"""
        global_state = await self.get_state(GlobalState)
        current_contrato = str(global_state.current_user_contrato).strip()

        self.email_config_loading = True
        yield

        try:
            ok = sb_delete("email_sender", filters={"id": email_id})
            if ok:
                rows = sb_select("email_sender", filters={"contract": current_contrato})
                self.email_config_list = rows or []
                yield rx.toast("🗑️ Email removido", position="top-center")
            else:
                self.email_config_error = "Falha ao remover email"
        except Exception as e:
            logger.error(f"Erro ao remover email: {e}")
            self.email_config_error = f"Erro: {str(e)}"
        finally:
            self.email_config_loading = False


# ── Email Config Dialog ──────────────────────────────────────
def _email_config_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.icon(tag="mail", size=20, color=S.COPPER),
                    rx.text(
                        "Destinatários de Email",
                        font_size="16px",
                        font_weight="700",
                        color=S.TEXT_PRIMARY,
                        font_family=S.FONT_TECH,
                    ),
                    rx.spacer(),
                    rx.dialog.close(
                        rx.icon_button(
                            rx.icon(tag="x", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="1",
                            on_click=RDOHistoricoState.close_email_config,
                        )
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                ),
                rx.text(
                    "Emails cadastrados receberão automaticamente cada RDO enviado.",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                ),
                rx.divider(color=S.BORDER_SUBTLE, margin_y="8px"),
                # Lista de emails
                rx.cond(
                    RDOHistoricoState.email_config_loading,
                    rx.center(rx.spinner(size="3", color=S.COPPER), padding="24px"),
                    rx.cond(
                        RDOHistoricoState.email_config_list,
                        rx.vstack(
                            rx.foreach(
                                RDOHistoricoState.email_config_list,
                                lambda row: rx.hstack(
                                    rx.icon(tag="mail", size=14, color=S.PATINA),
                                    rx.text(
                                        row["email"],
                                        font_size="13px",
                                        color=S.TEXT_PRIMARY,
                                        flex="1",
                                    ),
                                    rx.text(
                                        row["created_by"],
                                        font_size="11px",
                                        color=S.TEXT_MUTED,
                                    ),
                                    rx.icon_button(
                                        rx.icon(tag="trash-2", size=13),
                                        on_click=RDOHistoricoState.delete_email_recipient(
                                            row["id"]
                                        ),
                                        variant="ghost",
                                        color_scheme="red",
                                        size="1",
                                    ),
                                    padding="10px 12px",
                                    border_radius="8px",
                                    bg="rgba(255,255,255,0.02)",
                                    border=f"1px solid {S.BORDER_SUBTLE}",
                                    width="100%",
                                    align="center",
                                    spacing="2",
                                ),
                            ),
                            width="100%",
                            spacing="2",
                            max_height="240px",
                            overflow_y="auto",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="inbox", size=32, color=S.TEXT_MUTED),
                                rx.text(
                                    "Nenhum email cadastrado", font_size="13px", color=S.TEXT_MUTED
                                ),
                                align="center",
                                spacing="2",
                            ),
                            padding="24px",
                        ),
                    ),
                ),
                rx.divider(color=S.BORDER_SUBTLE, margin_y="4px"),
                # Adicionar novo email
                rx.vstack(
                    rx.text(
                        "Adicionar email",
                        font_size="11px",
                        color=S.TEXT_MUTED,
                        font_weight="600",
                        text_transform="uppercase",
                    ),
                    rx.hstack(
                        rx.input(
                            placeholder="nome@empresa.com",
                            value=RDOHistoricoState.new_email_input,
                            on_change=RDOHistoricoState.set_new_email_input,
                            type="email",
                            width="100%",
                            height="40px",
                            bg="rgba(255,255,255,0.04)",
                            border=f"1px solid {S.BORDER_SUBTLE}",
                            color=S.TEXT_PRIMARY,
                            _focus={"border_color": S.COPPER},
                            _placeholder={"color": S.TEXT_MUTED},
                        ),
                        rx.button(
                            rx.icon(tag="plus", size=16),
                            on_click=RDOHistoricoState.add_email_recipient,
                            bg=S.COPPER,
                            color="white",
                            height="40px",
                            min_width="40px",
                            padding_x="0",
                            flex_shrink="0",
                            is_loading=RDOHistoricoState.email_config_loading,
                        ),
                        width="100%",
                        align="end",
                        spacing="2",
                    ),
                    rx.cond(
                        RDOHistoricoState.email_config_error != "",
                        rx.text(
                            RDOHistoricoState.email_config_error,
                            font_size="12px",
                            color="#ff6b6b",
                        ),
                    ),
                    width="100%",
                    spacing="2",
                ),
                spacing="3",
                width="100%",
            ),
            bg=S.BG_ELEVATED,
            border=f"1px solid {S.BORDER_ACCENT}",
            border_radius="16px",
            padding="24px",
            max_width="480px",
            width="90vw",
        ),
        open=RDOHistoricoState.show_email_config,
    )


def _rdo_card(rdo: dict) -> rx.Component:
    """Card de um RDO no histórico"""
    return rx.box(
        rx.hstack(
            # Ícone
            rx.box(
                rx.icon(tag="file-text", size=24, color=S.COPPER),
                bg=S.COPPER_GLOW,
                padding="10px",
                border_radius="10px",
            ),
            # Info — chaves conforme schema Supabase (case-sensitive)
            rx.vstack(
                rx.text(
                    rdo["ID_RDO"],
                    font_weight="700",
                    font_size="14px",
                    color=S.TEXT_PRIMARY,
                    font_family=S.FONT_TECH,
                ),
                rx.hstack(
                    rx.badge(
                        rdo["Contrato"],
                        color_scheme="yellow",
                        variant="soft",
                        size="1",
                    ),
                    rx.text(
                        rdo["Data"],
                        font_size="12px",
                        color=S.TEXT_MUTED,
                    ),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            # Download PDF — só mostra se pdf_path for uma URL real (não None/vazio)
            rx.cond(
                rdo["pdf_path"],
                rx.link(
                    rx.button(
                        rx.icon(tag="download", size=16),
                        rx.text("PDF", display=["none", "inline", "inline"]),
                        size="2",
                        variant="soft",
                        color_scheme="yellow",
                        cursor="pointer",
                    ),
                    href=rdo["pdf_path"],
                    is_external=True,
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon(tag="download", size=16),
                        size="2",
                        variant="ghost",
                        disabled=True,
                        color_scheme="gray",
                    ),
                    content="PDF não disponível",
                ),
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="16px",
        border_radius="12px",
        bg="rgba(255, 255, 255, 0.02)",
        border=f"1px solid {S.BORDER_SUBTLE}",
        _hover={"bg": "rgba(255, 255, 255, 0.04)", "border_color": S.BORDER_ACCENT},
        transition="all 0.2s ease",
    )


def rdo_historico_page() -> rx.Component:
    """Lista de RDOs enviados"""

    return rx.vstack(
        # Email Config Dialog
        _email_config_dialog(),
        # Header
        rx.hstack(
            rx.icon(tag="file-text", size=32, color=S.COPPER),
            rx.vstack(
                rx.text("MEUS RDOS", **S.PAGE_TITLE_STYLE),
                rx.text("Histórico de Relatórios Enviados", **S.PAGE_SUBTITLE_STYLE),
                spacing="0",
                align="start",
            ),
            rx.spacer(),
            # Botão configurar emails
            rx.button(
                rx.icon(tag="mail", size=16),
                rx.text("Emails", display=["none", "inline", "inline"]),
                on_click=RDOHistoricoState.open_email_config,
                variant="outline",
                color_scheme="yellow",
                size="2",
                cursor="pointer",
            ),
            spacing="4",
            width="100%",
            margin_bottom="24px",
            align="center",
        ),
        # Lista de RDOs
        rx.box(
            rx.cond(
                RDOHistoricoState.rdos_list,
                rx.vstack(
                    # Cabeçalho da lista
                    rx.hstack(
                        rx.text(
                            "Relatórios enviados",
                            font_size="13px",
                            color=S.TEXT_MUTED,
                            text_transform="uppercase",
                            letter_spacing="0.05em",
                        ),
                        rx.spacer(),
                        rx.text(
                            "Clique em PDF para baixar",
                            font_size="12px",
                            color=S.TEXT_MUTED,
                        ),
                        width="100%",
                        margin_bottom="12px",
                    ),
                    rx.foreach(
                        RDOHistoricoState.rdos_list,
                        _rdo_card,
                    ),
                    spacing="3",
                    width="100%",
                ),
                # Estado vazio
                rx.center(
                    rx.vstack(
                        rx.icon(tag="inbox", size=64, color=S.TEXT_MUTED),
                        rx.text(
                            "Nenhum RDO enviado ainda",
                            font_size="18px",
                            color=S.TEXT_MUTED,
                            font_weight="600",
                        ),
                        rx.text(
                            "Preencha seu primeiro RDO clicando em 'RDO DIÁRIO'",
                            font_size="14px",
                            color=S.TEXT_MUTED,
                        ),
                        rx.link(
                            rx.button(
                                rx.icon(tag="plus", size=16),
                                "Novo RDO",
                                bg=S.COPPER,
                                color="white",
                                margin_top="8px",
                            ),
                            href="/rdo-form",
                        ),
                        spacing="3",
                        text_align="center",
                        align="center",
                    ),
                    padding="64px",
                ),
            ),
            **S.GLASS_CARD,
            max_width="1000px",
            margin="0 auto",
            width="100%",
        ),
        width="100%",
        padding=["16px", "24px", "32px"],
        spacing="4",
        on_mount=RDOHistoricoState.load_rdos,
    )
