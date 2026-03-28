# Multi-Tenant — Task List para Continuação
**Última atualização**: 2026-03-28 | **Sessão**: S1+S2+S3 completos

---

## ✅ FEITO (não retomar)

### Banco de Dados
- [x] Tabela `clients` criada (id, name, is_master, ai_budget, status)
- [x] 3 tenants bootstrap: BTP MASTER (`000...`), BOMTEMPO (`111...`), PLENO (`222...`)
- [x] `client_id` adicionado em 16 tabelas via migração SQL
- [x] Dados existentes migrados para BOMTEMPO
- [x] View `master_stats` criada
- [x] Usuário `master` / senha `123` criado no banco com `client_id = 000...`
- [x] Roles copiadas para tenant MASTER na migração

### Isolamento de Dados (Backend)
- [x] `data_loader.py` — `DataLoader(client_id)`, cache por tenant (`bomtempo_cache_{id[:8]}.pkl`)
- [x] `data_loader.py` — `invalidate_cache(client_id)` tenant-aware
- [x] `global_state.py` — `load_data()` usa `DataLoader(client_id=self.current_client_id)` ← **bug crítico corrigido último**
- [x] `global_state.py` — `ensure_data_loaded()` usa `DataLoader(client_id=...)`
- [x] `global_state.py` — `stream_chat_bg()` usa `DataLoader(client_id=...)`
- [x] `global_state.py` — `logout()` limpa `current_client_id/name/client_is_master` + invalida cache
- [x] `global_state.py` — redirect pós-login: master → `/admin/master-gestion`
- [x] `global_state.py` — `chat_sessions` INSERT inclui `client_id` (×2)
- [x] `global_state.py` — `contratos` INSERT inclui `client_id`
- [x] `hub_state.py` — `hub_atividades` INSERT inclui `client_id`
- [x] `hub_state.py` — `hub_auditoria_imgs` INSERT inclui `client_id`
- [x] `hub_state.py` — `hub_timeline` INSERT inclui `client_id`
- [x] `hub_state.py` — `user_notifications` INSERT inclui `client_id`
- [x] `fin_service.py` — `save_custo()` param `client_id` adicionado
- [x] `fin_state.py` — passa `client_id` para `save_custo()`
- [x] `usuarios_state.py` — `load_users()` filtra por `client_id` quando não é master
- [x] `usuarios_state.py` — `load_roles()` filtra por `client_id` do tenant
- [x] `usuarios_state.py` — `save_user()` INSERT inclui `client_id` correto
- [x] `usuarios_state.py` — `roles` INSERT inclui `_current_client_id`

### AI Context
- [x] `ai_context.py` — `get_system_prompt(tenant_name)` inclui instrução de isolamento
- [x] `global_state.py` — passa `current_client_name` para `get_system_prompt`

### Master Console
- [x] `master_state.py` — guard via `get_state(GlobalState)`, `load_page`, `create_tenant()`
- [x] `master_console.py` — página com KPI, tabela de tenants, tabela de usuários, modal "Novo Cliente"
- [x] `master_metrics.py` — página stub de custos/utilização
- [x] `master_settings.py` — página stub de configurações
- [x] `bomtempo.py` — rotas `/admin/master-gestion`, `/admin/master-metrics`, `/admin/master-settings`
- [x] `sidebar.py` — já tinha `rx.cond(client_is_master, ...)` — master vê menu próprio

### Gerenciar Usuários (Master-aware)
- [x] `usuarios_state.py` — `tenants_options`, `form_roles_list`, `_is_master`, `_current_client_id`
- [x] `usuarios_state.py` — `set_edit_user_client_id()` recarrega roles do tenant selecionado + limpa contrato
- [x] `usuarios_state.py` — `open_add_user_dialog()` pré-carrega roles do primeiro tenant
- [x] `usuarios.py` — dropdown "Tenant / Cliente" aparece quando master (em âmbar)
- [x] `usuarios.py` — dropdown "Perfil" usa `form_roles_list` (filtrado por tenant)
- [x] `usuarios.py` — campo "Contrato" oculto quando master (`~GlobalState.client_is_master`)

---

## ✅ PENDENTES RESOLVIDOS (S4)

### P1 — 404 nas páginas `/admin/master-metrics` e `/admin/master-settings` ✅ FEITO
- `master_metrics.py`: lambda no foreach → função nomeada `_metrics_tenant_row`
- `master_settings.py`: `rx.grid` → `rx.hstack` + helper `_settings_card`

### P2 — `master_state.create_tenant()` — roles fallback ✅ FEITO
- `master_state.py`: se BOMTEMPO não tem roles com `client_id`, usa lista padrão (Administrador + Gestor)
- `sql_patch_master_stats.sql`: seed idempotente com `WHERE NOT EXISTS`

### P3 — Empty States para tenant PLENO ✅ ANALISADO
- Todos os `iloc[0]` já estão guardados com `if not sub.empty:`
- Todos os computed vars já retornam `0` / `[]` quando `df is None or df.empty`
- Não há crash esperado — tenant novo só mostrará KPIs zerados

### P4 — tenant isolation no schema context da IA ✅ FEITO
- `action_ai_state.py`: captura `client_id` e `tenant_name` do GlobalState
- Passa `tenant_name` para `get_system_prompt`
- Appenda instrução `WHERE client_id = '...'` no `schema_context`

### P5 — `admin_tools.py` `create_user` sem `client_id` ✅ FEITO
- `action_ai_state.py`: injeta `data["_client_id"]` no payload de HITL
- `admin_tools.py`: INSERT `login` inclui `client_id: data.get("_client_id")`

### P6 — `fuel_reimbursements` INSERT sem `client_id` ✅ FEITO
- `fuel_service.py`: `save_to_database(..., client_id="")` — novo parâmetro + record inclui `client_id`
- `reembolso_state.py`: captura `gs.current_client_id` e passa para `save_to_database`

### P7 — NOT NULL enforcement no banco [PRIORIDADE BAIXA — MANUAL]

**⚠️ AÇÃO MANUAL NECESSÁRIA — executar `sql_patch_master_stats.sql` no Supabase SQL Editor**
- Recria view `master_stats` com `status`, `ai_budget`, `session_count` (estavam faltando)
- Faz seed das roles BOMTEMPO (idempotente — só insere se não existir)

Após confirmar que todos os rows têm `client_id` preenchido:
```sql
-- Verificar que não há NULLs:
SELECT COUNT(*) FROM login WHERE client_id IS NULL;
SELECT COUNT(*) FROM contratos WHERE client_id IS NULL;
SELECT COUNT(*) FROM hub_atividades WHERE client_id IS NULL;
SELECT COUNT(*) FROM fin_custos WHERE client_id IS NULL;
-- Se todos = 0, aplicar:
ALTER TABLE login ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE contratos ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE hub_atividades ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE fin_custos ALTER COLUMN client_id SET NOT NULL;
```

---

## 🧪 CHECKLIST DE VALIDAÇÃO (você testa)

```
[ ] Login master/123 → redireciona para /admin/master-gestion
[ ] Master Console exibe 3 tenants (BTP MASTER, BOMTEMPO, PLENO)
[ ] Master Console exibe todos os usuários com coluna de tenant
[ ] "Novo Cliente" abre modal → criar tenant → aparece na lista
[ ] Ao criar usuário com tenant PLENO → roles mostra só "Administrador"
[ ] Campo "Contrato" não aparece no form quando master
[ ] Login usuário BOMTEMPO → vê dados normais (contratos, financeiro, etc.)
[ ] Login usuário PLENO → vê dashboard vazio SEM ERRO de runtime
[ ] Logout BOMTEMPO → login PLENO → não herda dados do BOMTEMPO (cache isolado)
[ ] Chat IA como BOMTEMPO → não menciona dados de PLENO
[ ] /admin/master-metrics → 404 ou página (documentar)
[ ] /admin/master-settings → 404 ou página (documentar)
```

---

## 🗒️ NOTAS TÉCNICAS PARA PRÓXIMA SESSÃO

### Arquivos-chave modificados nesta sessão
| Arquivo | O que mudou |
|---|---|
| `bomtempo/core/data_loader.py` | `__init__(client_id)`, cache path por tenant, `_fetch` filtra, `invalidate_cache(client_id)` |
| `bomtempo/core/ai_context.py` | `get_system_prompt(tenant_name)` |
| `bomtempo/core/fin_service.py` | `save_custo(..., client_id="")` |
| `bomtempo/state/global_state.py` | `load_data()` usa `DataLoader(client_id=...)`, logout limpa tenant fields, redirect master, chat_sessions com client_id, contratos com client_id |
| `bomtempo/state/hub_state.py` | 4 inserts com client_id |
| `bomtempo/state/fin_state.py` | passa `client_id` para `save_custo` |
| `bomtempo/state/master_state.py` | NOVO — guard, load_page, create_tenant, all_users |
| `bomtempo/state/usuarios_state.py` | `_is_master`, `_current_client_id`, `form_roles_list`, load filtrado, set_edit_user_client_id |
| `bomtempo/pages/master_console.py` | NOVO — KPI + tabela tenants + tabela users + modal |
| `bomtempo/pages/master_metrics.py` | NOVO — stub |
| `bomtempo/pages/master_settings.py` | NOVO — stub |
| `bomtempo/pages/usuarios.py` | dropdown tenant, roles via form_roles_list, contrato oculto para master |
| `bomtempo/bomtempo.py` | 3 rotas master registradas |

### UUID dos tenants bootstrap
| Tenant | UUID |
|---|---|
| BTP MASTER | `00000000-0000-0000-0000-000000000000` |
| BOMTEMPO | `11111111-1111-1111-1111-111111111111` |
| PLENO | `22222222-2222-2222-2222-222222222222` |

### Usuário master
- **login**: `master` | **senha**: `123` | **role**: `Administrador` | **client_id**: `000...`
