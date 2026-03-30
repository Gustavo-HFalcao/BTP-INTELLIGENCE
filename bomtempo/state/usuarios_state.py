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
    _is_master: bool = False
    _current_client_id: str = ""

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
    edit_user_old_login: str = ""   # original username — used as filter fallback
    edit_user_password: str = ""
    edit_user_role: str = ""
    edit_user_project: str = ""
    edit_user_client_id: str = ""   # tenant vinculado ao usuário (master only)
    edit_user_email: str = ""
    edit_user_whatsapp: str = ""
    user_form_error: str = ""

    # Tenants disponíveis para seleção (master only)
    tenants_options: List[Dict[str, str]] = []  # [{id, name}]

    # Roles filtradas pelo tenant selecionado no form (master only)
    form_roles_list: List[str] = ["Administrador"]

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

    # ── Computed ──────────────────────────────────────────────────

    @rx.var
    def role_names_list(self) -> List[str]:
        """Role name strings for the simplified rx.select items list."""
        return [r["name"] for r in self.roles_list]

    @rx.var
    def edit_user_project_display(self) -> str:
        """Maps empty project to 'Nenhum' so the select shows the right option."""
        return self.edit_user_project if self.edit_user_project else "Nenhum"

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
        """Called on on_load — caches admin context and loads both lists."""
        from bomtempo.state.global_state import GlobalState
        gs = await self.get_state(GlobalState)
        self._admin_username = str(gs.current_user_name or "unknown")
        self._is_master = bool(gs.client_is_master)
        self._current_client_id = str(gs.current_client_id or "")
        if self._is_master:
            self._load_tenants_options()
        self.load_users()
        self.load_roles()

    def _load_tenants_options(self):
        try:
            rows = sb_select("clients", filters={"is_master": False}) or []
            self.tenants_options = [
                {"id": str(r.get("id", "")), "name": str(r.get("name", ""))}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Erro ao carregar tenants: {e}")

    def load_users(self):
        self.users_loading = True
        try:
            # Master vê todos; tenant-admin vê apenas seus usuários
            if self._is_master:
                rows = sb_select("login", order="username") or []
                # Mapa client_id → name para exibição
                clients = sb_select("clients") or []
                client_map = {str(c.get("id", "")): str(c.get("name", "—")) for c in clients}
            else:
                filters = {"client_id": self._current_client_id} if self._current_client_id else {}
                rows = sb_select("login", filters=filters, order="username") or []
                client_map = {}

            self.users_list = [
                {
                    "id":          str(r.get("id", "")),
                    "username":    str(r.get("username", r.get("user", ""))),
                    "user_role":   str(r.get("user_role", "")),
                    "project":     str(r.get("project", "") or ""),
                    "client_id":   str(r.get("client_id", "") or ""),
                    "client_name": client_map.get(str(r.get("client_id", "")), "—") if self._is_master else "",
                    "email":       str(r.get("email", "") or ""),
                    "whatsapp":    str(r.get("whatsapp", "") or ""),
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
            # Roles filtradas por tenant (ou todas se master)
            if self._is_master or not self._current_client_id:
                rows = sb_select("roles") or []
            else:
                rows = sb_select("roles", filters={"client_id": self._current_client_id}) or []
            # Deduplica por nome (master pode ver duplicatas de tenants diferentes)
            seen = set()
            unique_rows = []
            for r in rows:
                name = str(r.get("name", ""))
                if name not in seen:
                    seen.add(name)
                    unique_rows.append(r)
            self.roles_list = [
                {
                    "id": str(r.get("id", "")),
                    "name": str(r.get("name", "")),
                    "icon": str(r.get("icon", "user") or "user"),
                    "modules": list(r.get("modules", [])),
                    "module_count": str(len(r.get("modules", []))),
                }
                for r in unique_rows
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
        self.edit_user_old_login = ""
        self.edit_user_password = ""
        self.edit_user_project = ""
        self.edit_user_email = ""
        self.edit_user_whatsapp = ""
        self.user_form_error = ""
        if self._is_master:
            # Master: pré-seleciona primeiro tenant não-master; roles serão carregadas ao selecionar
            first_tenant_id = self.tenants_options[0]["id"] if self.tenants_options else ""
            self.edit_user_client_id = first_tenant_id
            self.form_roles_list = ["Administrador"]
            self.edit_user_role = "Administrador"
            # Carrega roles do primeiro tenant imediatamente
            if first_tenant_id:
                try:
                    rows = sb_select("roles", filters={"client_id": first_tenant_id}) or []
                    names = [str(r.get("name", "")) for r in rows if r.get("name")]
                    if "Administrador" not in names:
                        names = ["Administrador"] + names
                    self.form_roles_list = names if names else ["Administrador"]
                    self.edit_user_role = self.form_roles_list[0]
                except Exception:
                    pass
        else:
            self.edit_user_client_id = self._current_client_id
            self.form_roles_list = [r["name"] for r in self.roles_list] or ["Administrador"]
            self.edit_user_role = self.roles_list[0]["name"] if self.roles_list else ""
        self.show_user_dialog = True

    def open_edit_user_dialog(self, user_id: str):
        self.is_editing_user = True
        self.edit_user_id = user_id
        self.user_form_error = ""
        for u in self.users_list:
            if u["id"] == user_id:
                self.edit_user_login = u["username"]
                self.edit_user_old_login = u["username"]  # capture for filter
                self.edit_user_password = ""
                self.edit_user_role = u["user_role"]
                self.edit_user_project = u["project"]
                self.edit_user_email = u.get("email", "")
                self.edit_user_whatsapp = u.get("whatsapp", "")
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
        # "__none__" / "Nenhum" sentinel → store empty string (no contract)
        self.edit_user_project = "" if val in ("__none__", "Nenhum") else val

    def set_edit_user_email(self, val: str):
        self.edit_user_email = val

    def set_edit_user_whatsapp(self, val: str):
        self.edit_user_whatsapp = val

    def set_edit_user_client_id(self, val: str):
        """Quando master muda o tenant do form: recarrega roles daquele tenant e limpa contrato."""
        self.edit_user_client_id = val
        self.edit_user_project = ""  # contrato do outro tenant não se aplica
        self.edit_user_role = ""
        # Carrega roles do tenant selecionado
        try:
            if val:
                rows = sb_select("roles", filters={"client_id": val}) or []
                names = [str(r.get("name", "")) for r in rows if r.get("name")]
                # Garante que Administrador sempre está presente
                if "Administrador" not in names:
                    names = ["Administrador"] + names
                self.form_roles_list = names if names else ["Administrador"]
            else:
                self.form_roles_list = ["Administrador"]
            self.edit_user_role = self.form_roles_list[0]
        except Exception:
            self.form_roles_list = ["Administrador"]
            self.edit_user_role = "Administrador"

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
                    "email": self.edit_user_email.strip(),
                    "whatsapp": self.edit_user_whatsapp.strip(),
                }
                if password:
                    from bomtempo.core.auth_utils import hash_password
                    data["pw_hash"] = hash_password(password)

                if self.edit_user_id:
                    sb_update("login", filters={"id": self.edit_user_id}, data=data)
                elif self.edit_user_old_login:
                    sb_update("login", filters={"username": self.edit_user_old_login}, data=data)
                else:
                    raise ValueError("Não foi possível identificar o usuário para atualização.")

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
                from bomtempo.core.auth_utils import hash_password
                # Determina o tenant: master escolhe explicitamente; tenant-admin usa o próprio
                target_client_id = (
                    self.edit_user_client_id
                    if self._is_master and self.edit_user_client_id
                    else self._current_client_id
                )
                insert_data: Dict[str, Any] = {
                    "username": username,
                    "password": hash_password(password),
                    "user_role": self.edit_user_role,
                    "project": self.edit_user_project.strip(),
                    "email": self.edit_user_email.strip(),
                    "whatsapp": self.edit_user_whatsapp.strip(),
                    "client_id": target_client_id,
                }
                result = sb_insert("login", insert_data)
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
            yield rx.toast(f"❌ Erro ao salvar: {str(e)[:80]}", position="top-center")
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
                result = sb_insert("roles", {"name": name, "icon": self.edit_role_icon, "modules": self.edit_role_modules, "client_id": self._current_client_id or None})
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
