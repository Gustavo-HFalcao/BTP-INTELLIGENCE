"""
State para gerenciamento de usuários e perfis de acesso.
Tabelas: login (usuários), roles (perfis com módulos)
Audit logging integrado em todas as operações CRUD.
"""
from typing import Any, Dict, List

import reflex as rx

from bomtempo.core.audit_logger import AuditCategory, audit_error, audit_log
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.supabase_client import sb_delete, sb_insert, sb_select, sb_update

logger = get_logger(__name__)

# Canonical module list: (slug, label, icon)
MODULES: List[tuple] = [
    ("visao_geral",       "Visão Geral",       "layout-dashboard"),
    ("obras",             "Obras",             "hard-hat"),
    ("projetos",          "Projetos",          "briefcase"),
    ("financeiro",        "Financeiro",        "wallet"),
    ("om",                "O&M",               "zap"),
    ("analytics",         "Analytics",         "bar-chart-3"),
    ("previsoes",         "Previsões ML",      "trending-up"),
    ("relatorios",        "Relatórios",        "file-text"),
    ("chat_ia",           "Chat IA",           "message-square"),
    ("reembolso",         "Reembolso Form",    "fuel"),
    ("reembolso_dash",    "Reembolso Dash",    "receipt"),
    ("rdo_form",          "RDO Diário",        "clipboard-list"),
    ("rdo_historico",     "Meus RDOs",         "clock"),
    ("rdo_dashboard",     "RDO Analytics",     "chart-bar"),
    ("editar_dados",      "Editar Dados",      "database"),
    ("alertas",           "Alertas",           "bell-ring"),
    ("logs_auditoria",    "Logs & Auditoria",  "shield-check"),
    ("gerenciar_usuarios","Gerenciar Usuários","users"),
]

MODULE_SLUGS: List[str] = [m[0] for m in MODULES]
MODULE_LABELS: Dict[str, str] = {m[0]: m[1] for m in MODULES}

# Curated icon set for role/avatar personalization: (lucide-slug, label-PT)
AVATAR_ICONS: List[tuple] = [
    ("user",           "Usuário"),
    ("shield-check",   "Admin"),
    ("hard-hat",       "Engenheiro"),
    ("hammer",         "Mestre"),
    ("briefcase",      "Gestor"),
    ("building-2",     "Empresa"),
    ("bar-chart-3",    "Analista"),
    ("database",       "TI"),
    ("file-text",      "Editor"),
    ("fuel",           "Campo"),
    ("truck",          "Logística"),
    ("zap",            "Operações"),
    ("star",           "Destaque"),
    ("award",          "Especialista"),
    ("target",         "Coordenador"),
    ("compass",        "Diretor"),
    ("layers",         "Supervisor"),
    ("settings-2",     "Técnico"),
    ("users",          "Equipe"),
    ("wallet",         "Financeiro"),
    ("globe",          "Projetos"),
    ("eye",            "Auditor"),
    ("clipboard-list", "RDO"),
    ("wrench",         "Manutenção"),
]


class UsuariosState(rx.State):
    """State para a página de gerenciamento de usuários e perfis."""

    # Private — populated via get_state(GlobalState) on load_page
    _admin_username: str = ""

    # ── Tab ───────────────────────────────────────────────────────
    active_tab: str = "usuarios"

    # ── Usuários ──────────────────────────────────────────────────
    users_list: List[Dict[str, str]] = []
    users_loading: bool = True
    is_saving_user: bool = False          # feedback imediato no botão Salvar
    show_user_dialog: bool = False
    is_editing_user: bool = False

    # Confirmação de exclusão (#13)
    pending_delete_id: str = ""           # ID do usuário aguardando confirmação
    pending_delete_name: str = ""         # Nome exibido no dialog de confirmação
    show_delete_confirm: bool = False     # Controla dialog de confirmação

    edit_user_id: str = ""
    edit_user_login: str = ""
    edit_user_password: str = ""
    edit_user_role: str = ""
    edit_user_project: str = ""
    user_form_error: str = ""

    # ── Perfis (roles) ────────────────────────────────────────────
    # NOTE: Dict[str, str] for Reflex type inference; 'modules' field is list[str] in practice (accessed only in Python handlers)
    roles_list: List[Dict[str, str]] = []
    roles_loading: bool = True
    show_role_dialog: bool = False
    is_editing_role: bool = False

    edit_role_id: str = ""
    edit_role_name: str = ""
    edit_role_icon: str = "user"
    edit_role_modules: list[str] = []
    role_form_error: str = ""

    # ── Module metadata (read-only reference for UI) ──────────────
    module_slugs: list[str] = MODULE_SLUGS

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _get_admin(self) -> str:
        return self._admin_username or "unknown"

    # ── Tab switch ────────────────────────────────────────────────
    def set_active_tab(self, tab: str):
        self.active_tab = tab
        if tab == "usuarios" and not self.users_list:
            self.load_users()
        elif tab == "perfis" and not self.roles_list:
            self.load_roles()

    # ─────────────────────────────────────────────────────────────
    # Data loaders
    # ─────────────────────────────────────────────────────────────

    async def load_page(self):
        """Called on on_load — caches admin username and loads both lists."""
        from bomtempo.state.global_state import GlobalState
        gs = await self.get_state(GlobalState)
        self._admin_username = str(gs.current_user_name or "unknown")
        self.load_users()
        self.load_roles()

    def load_users(self):
        self.users_loading = True
        try:
            rows = sb_select("login") or []
            self.users_list = [
                {
                    "id": str(r.get("id", "")),
                    "username": str(r.get("username", r.get("user", ""))),
                    "user_role": str(r.get("user_role", "")),
                    "project": str(r.get("project", "") or ""),
                }
                for r in rows
            ]
        except Exception as e:
            from bomtempo.core.error_logger import log_error
            log_error(e, module=__name__, function_name="load_users")
            logger.error(f"Erro ao carregar usuários: {e}")
        finally:
            self.users_loading = False

    def load_roles(self):
        self.roles_loading = True
        try:
            rows = sb_select("roles") or []
            self.roles_list = [
                {
                    "id": str(r.get("id", "")),
                    "name": str(r.get("name", "")),
                    "icon": str(r.get("icon", "user") or "user"),
                    "modules": list(r.get("modules", [])),
                    "module_count": str(len(r.get("modules", []))),
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Erro ao carregar roles: {e}")
        finally:
            self.roles_loading = False

    # ─────────────────────────────────────────────────────────────
    # Usuários CRUD
    # ─────────────────────────────────────────────────────────────

    def open_add_user_dialog(self):
        self.is_editing_user = False
        self.edit_user_id = ""
        self.edit_user_login = ""
        self.edit_user_password = ""
        self.edit_user_role = self.roles_list[0]["name"] if self.roles_list else ""
        self.edit_user_project = ""
        self.user_form_error = ""
        self.show_user_dialog = True

    def open_edit_user_dialog(self, user_id: str):
        self.is_editing_user = True
        self.edit_user_id = user_id
        self.user_form_error = ""
        for u in self.users_list:
            if u["id"] == user_id:
                self.edit_user_login = u["username"]
                self.edit_user_password = ""
                self.edit_user_role = u["user_role"]
                self.edit_user_project = u["project"]
                break
        self.show_user_dialog = True

    def close_user_dialog(self):
        self.show_user_dialog = False

    def set_edit_user_login(self, val: str):
        self.edit_user_login = val

    def set_edit_user_password(self, val: str):
        self.edit_user_password = val

    def set_edit_user_role(self, val: str):
        self.edit_user_role = val

    def set_edit_user_project(self, val: str):
        # "__none__" sentinel used by Select.Item (empty string is disallowed as item value)
        self.edit_user_project = "" if val == "__none__" else val

    async def save_user(self):
        """Salva usuário com feedback imediato no botão (#6)."""
        self.user_form_error = ""
        username = self.edit_user_login.strip()
        password = self.edit_user_password.strip()

        if not username:
            self.user_form_error = "Login é obrigatório."
            return
        if not self.is_editing_user and not password:
            self.user_form_error = "Senha é obrigatória para novo usuário."
            return
        if not self.edit_user_role:
            self.user_form_error = "Perfil é obrigatório."
            return

        self.is_saving_user = True
        yield

        try:
            if self.is_editing_user:
                # Determine what changed for audit metadata
                old_user = next((u for u in self.users_list if u["id"] == self.edit_user_id), {})
                changed: Dict[str, Any] = {}
                if old_user.get("username") != username:
                    changed["login"] = {"de": old_user.get("username"), "para": username}
                if old_user.get("user_role") != self.edit_user_role:
                    changed["role"] = {"de": old_user.get("user_role"), "para": self.edit_user_role}
                if old_user.get("project") != self.edit_user_project.strip():
                    changed["project"] = {"de": old_user.get("project"), "para": self.edit_user_project.strip()}
                if password:
                    changed["senha"] = "alterada"

                data: Dict[str, Any] = {
                    "username": username,
                    "user_role": self.edit_user_role,
                    "project": self.edit_user_project.strip(),
                }
                if password:
                    data["password"] = password

                sb_update("login", filters={"id": self.edit_user_id}, data=data)

                audit_log(
                    category=AuditCategory.USER_MGMT,
                    action=f"Usuário '{username}' atualizado por '{self._get_admin()}'",
                    username=self._get_admin(),
                    entity_type="login",
                    entity_id=self.edit_user_id,
                    metadata={"alteracoes": changed, "usuario_alvo": username},
                )
                logger.info(f"Usuário '{username}' atualizado por '{self._get_admin()}'")

            else:
                result = sb_insert("login", {
                    "username": username,
                    "password": password,
                    "user_role": self.edit_user_role,
                    "project": self.edit_user_project.strip(),
                })
                new_id = str(result.get("id", "")) if result else ""

                audit_log(
                    category=AuditCategory.USER_MGMT,
                    action=f"Novo usuário '{username}' criado por '{self._get_admin()}'",
                    username=self._get_admin(),
                    entity_type="login",
                    entity_id=new_id,
                    metadata={
                        "usuario_criado": username,
                        "role": self.edit_user_role,
                        "project": self.edit_user_project.strip(),
                    },
                )
                logger.info(f"Novo usuário '{username}' criado por '{self._get_admin()}'")

            self.show_user_dialog = False
            self.load_users()

        except Exception as e:
            logger.error(f"Erro ao salvar usuário: {e}")
            audit_error(
                action=f"Falha ao salvar usuário '{username}'",
                username=self._get_admin(),
                entity_type="login",
                error=e,
            )
            self.user_form_error = f"Erro ao salvar: {e}"
        finally:
            self.is_saving_user = False

    # ── Delete com confirmação (#13) ──────────────────────────────

    def request_delete_user(self, user_id: str):
        """Abre dialog de confirmação antes de excluir (#13)."""
        target = next((u for u in self.users_list if u["id"] == user_id), {})
        self.pending_delete_id = user_id
        self.pending_delete_name = target.get("username", user_id)
        self.show_delete_confirm = True

    def cancel_delete_user(self):
        self.pending_delete_id = ""
        self.pending_delete_name = ""
        self.show_delete_confirm = False

    def delete_user(self, user_id: str):
        self.show_delete_confirm = False
        target = next((u for u in self.users_list if u["id"] == user_id), {})
        target_name = target.get("username", user_id)
        try:
            sb_delete("login", filters={"id": user_id})
            audit_log(
                category=AuditCategory.USER_MGMT,
                action=f"Usuário '{target_name}' excluído por '{self._get_admin()}'",
                username=self._get_admin(),
                entity_type="login",
                entity_id=user_id,
                metadata={"usuario_excluido": target_name, "role": target.get("user_role")},
            )
            logger.info(f"Usuário '{target_name}' excluído por '{self._get_admin()}'")
            self.load_users()
        except Exception as e:
            logger.error(f"Erro ao excluir usuário: {e}")
            audit_error(
                action=f"Falha ao excluir usuário '{target_name}'",
                username=self._get_admin(),
                entity_type="login",
                entity_id=user_id,
                error=e,
            )

    # ─────────────────────────────────────────────────────────────
    # Roles CRUD
    # ─────────────────────────────────────────────────────────────

    def open_add_role_dialog(self):
        self.is_editing_role = False
        self.edit_role_id = ""
        self.edit_role_name = ""
        self.edit_role_icon = "user"
        self.edit_role_modules = []
        self.role_form_error = ""
        self.show_role_dialog = True

    def open_edit_role_dialog(self, role_id: str):
        self.is_editing_role = True
        self.edit_role_id = role_id
        self.role_form_error = ""
        for r in self.roles_list:
            if r["id"] == role_id:
                self.edit_role_name = r["name"]
                self.edit_role_icon = str(r.get("icon", "user") or "user")
                self.edit_role_modules = list(r["modules"])
                break
        self.show_role_dialog = True

    def close_role_dialog(self):
        self.show_role_dialog = False

    def set_edit_role_name(self, val: str):
        self.edit_role_name = val

    def set_edit_role_icon(self, val: str):
        self.edit_role_icon = val

    def toggle_module(self, slug: str):
        """Toggle a module slug in/out of edit_role_modules."""
        current = list(self.edit_role_modules)
        if slug in current:
            current.remove(slug)
        else:
            current.append(slug)
        self.edit_role_modules = current

    def save_role(self):
        self.role_form_error = ""
        name = self.edit_role_name.strip()
        if not name:
            self.role_form_error = "Nome do perfil é obrigatório."
            return

        try:
            if self.is_editing_role:
                old_role = next((r for r in self.roles_list if r["id"] == self.edit_role_id), {})
                old_modules = old_role.get("modules", [])
                added = [m for m in self.edit_role_modules if m not in old_modules]
                removed = [m for m in old_modules if m not in self.edit_role_modules]

                sb_update(
                    "roles",
                    filters={"id": self.edit_role_id},
                    data={"name": name, "icon": self.edit_role_icon, "modules": self.edit_role_modules},
                )
                audit_log(
                    category=AuditCategory.USER_MGMT,
                    action=f"Perfil '{name}' atualizado por '{self._get_admin()}'",
                    username=self._get_admin(),
                    entity_type="roles",
                    entity_id=self.edit_role_id,
                    metadata={
                        "perfil": name,
                        "modulos_adicionados": added,
                        "modulos_removidos": removed,
                        "total_modulos": len(self.edit_role_modules),
                    },
                )
                logger.info(f"Perfil '{name}' atualizado por '{self._get_admin()}'")

            else:
                result = sb_insert("roles", {"name": name, "icon": self.edit_role_icon, "modules": self.edit_role_modules})
                new_id = str(result.get("id", "")) if result else ""

                audit_log(
                    category=AuditCategory.USER_MGMT,
                    action=f"Novo perfil '{name}' criado por '{self._get_admin()}'",
                    username=self._get_admin(),
                    entity_type="roles",
                    entity_id=new_id,
                    metadata={
                        "perfil": name,
                        "modulos": self.edit_role_modules,
                        "total_modulos": len(self.edit_role_modules),
                    },
                )
                logger.info(f"Novo perfil '{name}' criado por '{self._get_admin()}'")

            self.show_role_dialog = False
            self.load_roles()

        except Exception as e:
            logger.error(f"Erro ao salvar role: {e}")
            audit_error(
                action=f"Falha ao salvar perfil '{name}'",
                username=self._get_admin(),
                entity_type="roles",
                error=e,
            )
            self.role_form_error = f"Erro ao salvar: {e}"

    def delete_role(self, role_id: str):
        target = next((r for r in self.roles_list if r["id"] == role_id), {})
        role_name = target.get("name", role_id)
        try:
            sb_delete("roles", filters={"id": role_id})
            audit_log(
                category=AuditCategory.USER_MGMT,
                action=f"Perfil '{role_name}' excluído por '{self._get_admin()}'",
                username=self._get_admin(),
                entity_type="roles",
                entity_id=role_id,
                metadata={"perfil_excluido": role_name, "modulos": target.get("modules", [])},
            )
            logger.info(f"Perfil '{role_name}' excluído por '{self._get_admin()}'")
            self.load_roles()
        except Exception as e:
            logger.error(f"Erro ao excluir perfil: {e}")
            audit_error(
                action=f"Falha ao excluir perfil '{role_name}'",
                username=self._get_admin(),
                entity_type="roles",
                entity_id=role_id,
                error=e,
            )
