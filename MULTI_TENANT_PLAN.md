# Plano de Implementação Multi-Tenant — BTP Intelligence
**Versão**: 1.0 | **Data**: 2026-03-28 | **Status**: Planejamento Final

---

## 0. Diagnóstico do Estado Atual

### O que já existe (não refazer)
| Artefato | Estado | Observação |
|---|---|---|
| `sql_multi_tenant_migration_v2.sql` | ✅ Pronto para execução | Criar tabela `clients`, 3 tenants, migrar dados para BOMTEMPO |
| `GlobalState.current_client_id` | ✅ Implementado | Lido do campo `client_id` da tabela `login` no `check_login` |
| `GlobalState.client_is_master` | ✅ Implementado | Busca `clients` table pós-login e seta o bool |
| `GlobalState.check_login` | ✅ Compatível | Já lê `client_id` e popula o state |
| `supabase_client.py` | ⚠️ Sem isolamento | `sb_select` não filtra por `client_id` — risco crítico |
| `DataLoader.load_all()` | ❌ Não isolado | Cache compartilhado + queries sem filtro de tenant |
| Página Master Dashboard | ❌ Não existe | Nova página `/master` a criar |
| Sidebar condicional (Master vs Client) | ❌ Não existe | Navegação única para todos os roles |
| AI Context (`get_dashboard_context`) | ❌ Não isolado | Recebe `data` global, sem scoping por tenant |

### Riscos Críticos Identificados (não presentes no esboço original)

**R1 — Cache de dados não é tenant-aware (CRÍTICO)**
O arquivo `CACHE_FILE = tempfile.gettempdir()/bomtempo_data_cache.pkl` é único para todo o
processo. Se usuário A (BOMTEMPO) faz login e gera o cache, usuário B (PLENO) pode receber
os dados do BOMTEMPO em um cache hit. Isso quebra o isolamento por completo.

**R2 — service_role bypassa RLS (RISCO ARQUITETURAL)**
O app usa `SUPABASE_SERVICE_KEY` que ignora Row Level Security. Todo o isolamento é feito na
camada de aplicação (Python). Uma query sem filtro de `client_id` expõe dados de todos os
tenants. Não há segunda barreira de segurança.

**R3 — `roles` table: compartilhada ou por tenant?**
O esboço original adiciona `client_id` em `roles`. Se roles são configurações globais (Gestão,
Admin, Mestre de Obras), o isolamento pode quebrar o sistema de permissões. Decisão necessária
antes da migração.

**R4 — AI Tools executam SQL direto**
O agente de IA pode chamar `execute_sql` (via `execute_tool`). Se o prompt não incluir
`client_id`, a IA pode retornar dados de outros tenants em respostas.

**R5 — Empty State do PLENO**
Quando PLENO logar, todos os DataFrames virão vazios. Vários componentes do dashboard
assumem dados presentes e podem lançar exceções (`KeyError`, divisão por zero em KPIs).

---

## 1. Decisões de Arquitetura (Antes de Codar)

### D1: `roles` — Global ou por Tenant?
**Decisão**: Roles são **configuração global** da plataforma. A tabela `roles` NÃO entra no
escopo de filtragem por `client_id`. Cada tenant pode ter usuários com os mesmos roles.
> Consequência: Remover `roles` da lista de tabelas migradas no SQL V2, ou garantir que
> o `client_id` em `roles` sirva apenas para criação de roles customizados futuros, nunca
> como filtro obrigatório de leitura.

### D2: Estratégia de Cache Multi-tenant
**Decisão**: Cache separado por `client_id`. O `CACHE_FILE` passa a ser
`bomtempo_data_cache_{client_id[:8]}.pkl`. DataLoader recebe `client_id` como parâmetro.

### D3: Injeção de `client_id` no `sb_select`
**Decisão**: NÃO modificar a assinatura de `sb_select` (quebraria todo o código existente).
Em vez disso, criar um wrapper `tenant_select(table, client_id, ...)` que adiciona o filtro
automaticamente. Tabelas excluídas do filtro: `clients`, `roles`, `contract_features` (decidir).

### D4: Tabelas que NÃO precisam de filtro por tenant
| Tabela | Motivo |
|---|---|
| `clients` | É a própria tabela de tenants |
| `roles` | Configuração global de permissões |
| `rpc calls` | Depende da função — avaliar caso a caso |

### D5: Redirecionamento pós-login
- Master → `/master` (Console de Gestão)
- Client → `/` (Dashboard Operativo — comportamento atual)

---

## 2. Fase 1: Banco de Dados (SQL Migration)

**Objetivo**: Criar o modelo de 3 tenants e garantir que 100% dos dados existentes
sejam vinculados ao cliente BOMTEMPO. Executar uma única vez, no SQL Editor do Supabase.

### 2.1 Script de Migração (Refinado — V2.1)

O arquivo `sql_multi_tenant_migration_v2.sql` já está correto na lógica principal.
Os refinamentos abaixo devem ser aplicados antes da execução:

**Adicionar ao `clients` table:**
```sql
ALTER TABLE clients ADD COLUMN IF NOT EXISTS ai_budget numeric DEFAULT 100.00;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
```

**Remover `roles` da lista de tabelas migradas** (ou tratar separadamente):
- Mantê-la na lista mas não filtrar por `client_id` em queries de roles.

**Após a migração, enforce NOT NULL:**
```sql
-- Executar APÓS o UPDATE que preenche todos os NULLs
ALTER TABLE login ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE contratos ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE hub_atividades ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE fin_custos ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE om ALTER COLUMN client_id SET NOT NULL;
ALTER TABLE rdo_master ALTER COLUMN client_id SET NOT NULL;
```
> ⚠️ Não aplicar NOT NULL em tabelas com dados históricos potencialmente sem `client_id`
> antes de confirmar que o UPDATE cobriu 100% das linhas. Verificar com:
> `SELECT COUNT(*) FROM login WHERE client_id IS NULL;`

**Remover DEFAULT após migração** (evita inserção acidental sem client_id):
```sql
ALTER TABLE login ALTER COLUMN client_id DROP DEFAULT;
ALTER TABLE contratos ALTER COLUMN client_id DROP DEFAULT;
-- (repetir para todas as tabelas críticas)
```

**Adicionar constraint de FK com ON DELETE behavior:**
```sql
-- As FKs já são criadas sem ON DELETE — comportamento é RESTRICT por padrão.
-- Isso está correto: não queremos deletar um tenant e perder todos os dados em cascata.
-- Documentar: para desativar um tenant, use status = 'inactive', não DELETE.
```

### 2.2 Verificação Pós-Migração
```sql
-- Checklist de validação (executar após o script):
SELECT 'login' as t, COUNT(*) as total, COUNT(client_id) as com_client FROM login
UNION ALL
SELECT 'contratos', COUNT(*), COUNT(client_id) FROM contratos
UNION ALL
SELECT 'hub_atividades', COUNT(*), COUNT(client_id) FROM hub_atividades
UNION ALL
SELECT 'fin_custos', COUNT(*), COUNT(client_id) FROM fin_custos
UNION ALL
SELECT 'rdo_master', COUNT(*), COUNT(client_id) FROM rdo_master;
-- total deve ser igual a com_client em todas as linhas
```

**Verificar usuário master:**
```sql
SELECT username, client_id FROM login WHERE username = 'master';
-- deve retornar '00000000-0000-0000-0000-000000000000'
```

**Testar a view master_stats:**
```sql
SELECT * FROM master_stats;
-- deve mostrar 3 linhas: BTP MASTER, BOMTEMPO, PLENO
```

### 2.3 Ordem de Execução
1. Backup do banco (snapshot no Supabase Dashboard)
2. Executar `sql_multi_tenant_migration_v2.sql` (com os refinamentos da seção 2.1)
3. Executar o checklist de verificação (seção 2.2)
4. Se OK: aplicar NOT NULL e DROP DEFAULT
5. Se ERRO: restaurar backup e investigar

---

## 3. Fase 2: Backend — Isolamento de Dados

**Objetivo**: Garantir que nenhuma query retorne dados de outros tenants.

### 3.1 Corrigir o Cache Multi-tenant (`data_loader.py`)

**Problema**: `CACHE_FILE` é uma string estática compartilhada por todos os tenants.

**Solução**: DataLoader recebe `client_id` e usa cache path por tenant.

```python
# ANTES (data_loader.py linha ~21):
CACHE_FILE = os.path.join(tempfile.gettempdir(), "bomtempo_data_cache.pkl")

# DEPOIS: cache separado por tenant
def _cache_path(client_id: str) -> str:
    safe_id = client_id[:8] if client_id else "global"
    return os.path.join(tempfile.gettempdir(), f"bomtempo_cache_{safe_id}.pkl")
```

**Assinatura do DataLoader:**
```python
class DataLoader:
    def __init__(self, client_id: str = ""):
        self.client_id = client_id
        self.cache_file = _cache_path(client_id)

    def load_all(self) -> dict:
        # usa self.cache_file e self.client_id
        # ao chamar _fetch(table, key), passa filters={"client_id": self.client_id}
```

**Tabelas sem filtro de tenant** (globais):
```python
GLOBAL_TABLES = {"clients", "roles"}  # lidas sem filtro de client_id

def _fetch(self, table: str, key: str):
    if table in GLOBAL_TABLES:
        rows = sb_select(table)
    else:
        rows = sb_select(table, filters={"client_id": self.client_id})
    return key, rows
```

### 3.2 Atualizar `GlobalState` para passar `client_id` ao DataLoader

Todos os lugares que instanciam `DataLoader()` devem passar `self.current_client_id`:

```python
# ANTES (global_state.py ~94):
loader = DataLoader()
self._data = loader.load_all()

# DEPOIS:
loader = DataLoader(client_id=self.current_client_id)
self._data = loader.load_all()
```

Localizar todos os pontos de instanciação com: `grep -n "DataLoader()" global_state.py`
(atualmente: `ensure_data_loaded` ~linha 94 e `stream_chat_bg` ~linha 165)

### 3.3 Invalidar Cache no Logout

```python
# global_state.py — método logout (linha ~977):
async def logout(self):
    # Invalidar cache do tenant antes de limpar o state
    if self.current_client_id:
        DataLoader.invalidate_cache(client_id=self.current_client_id)
    # ... resto do logout
```

Ajustar `invalidate_cache` para ser tenant-aware:
```python
@staticmethod
def invalidate_cache(client_id: str = ""):
    path = _cache_path(client_id)
    if os.path.exists(path):
        os.remove(path)
```

### 3.4 Garantir Isolamento em Writes (INSERT/UPDATE)

Todo `sb_insert` e `sb_update` que escreve em tabelas de dados deve incluir `client_id`.

Localizar todos os `sb_insert` no codebase:
```
grep -rn "sb_insert" bomtempo/
```
Para cada chamada, verificar se o `data` dict inclui `client_id`. Se não incluir e a tabela
for tenant-scoped, adicionar o campo.

**Padrão recomendado** em qualquer EventHandler que faz write:
```python
# Qualquer state que herde de GlobalState ou tenha acesso ao current_client_id:
data = {
    "client_id": self.current_client_id,
    # ... outros campos
}
sb_insert("tabela", data)
```

### 3.5 Redirecionamento Pós-Login

No `check_login` (linha ~1686), após setar `self.is_authenticated = True`:

```python
# Após setar client_is_master (~linha 1704):
if self.client_is_master:
    yield rx.redirect("/master")
else:
    yield rx.redirect("/")
```

---

## 4. Fase 3: Interface — Console de Gestão Master

**Objetivo**: Criar a página `/master` com métricas reais e ferramentas de provisionamento.

### 4.1 Novo arquivo: `bomtempo/pages/master_console.py`

**Componentes da página:**

```
/master
├── Header: "BTP Intelligence — Console de Gestão"
├── KPI Cards (4 cards)
│   ├── Total de Tenants ativos
│   ├── Total de usuários na plataforma
│   ├── Mensagens de IA (últimas 24h)
│   └── Logs de sistema (últimas 24h)
├── Tabela de Tenants
│   ├── Nome | Usuários | Logs | Msgs IA | Status | Ações
│   └── Botão "Provisionar Novo Cliente"
├── Gráfico de Uso (barras empilhadas por tenant / dia)
│   └── Dados de system_logs.created_at agrupados por client_id + dia
└── Modal "Novo Cliente"
    ├── Campo: Nome do cliente
    ├── Campo: ai_budget (limite de custo IA)
    └── Botão: Criar (chama RPC ou INSERT direto)
```

### 4.2 Novo arquivo: `bomtempo/state/master_state.py`

```python
class MasterState(rx.State):
    tenant_list: list[dict] = []       # dados de master_stats view
    is_loading: bool = False
    show_new_tenant_modal: bool = False
    new_tenant_name: str = ""
    new_tenant_budget: float = 100.0

    async def load_master_data(self):
        rows = sb_select("master_stats")  # sem filtro — view global
        self.tenant_list = rows or []

    async def create_tenant(self):
        # INSERT na tabela clients
        # CREATE usuário admin para o novo tenant
        # Feedback ao usuário
        pass
```

### 4.3 Sidebar Condicional

Modificar `bomtempo/components/sidebar.py` para condicional com `GlobalState.client_is_master`:

```python
# Sidebar do Master (Console)
def master_sidebar() -> rx.Component:
    return rx.vstack(
        sidebar_item("Console", "layout-dashboard", "/master"),
        sidebar_item("Tenants", "building-2", "/master/tenants"),
        sidebar_item("Logs Globais", "activity", "/logs"),
    )

# Sidebar do Cliente (atual)
def client_sidebar() -> rx.Component:
    return rx.vstack(
        # ... itens atuais do sidebar
    )

# Wrapper condicional
def sidebar() -> rx.Component:
    return rx.cond(
        GlobalState.client_is_master,
        master_sidebar(),
        client_sidebar(),
    )
```

### 4.4 Registrar rota no `bomtempo.py`

```python
from bomtempo.pages.master_console import master_console_page
from bomtempo.state.master_state import MasterState

# na definição do app:
app.add_page(master_console_page, route="/master", on_load=MasterState.load_master_data)
```

### 4.5 Proteção de Rota

A página `/master` deve redirecionar usuários não-master para `/`.
Implementar via `on_load` no MasterState:

```python
async def load_master_data(self):
    if not self.client_is_master:
        yield rx.redirect("/")
        return
    rows = sb_select("master_stats")
    self.tenant_list = rows or []
```

---

## 5. Fase 4: IA Multi-tenant

**Objetivo**: Garantir que o contexto da IA só inclua dados do tenant logado.

### 5.1 `AIContext.get_dashboard_context` — sem mudança necessária

O método recebe `data_snapshot` que já virá filtrado pelo `DataLoader` com `client_id`.
Nenhuma mudança é necessária nessa função — o isolamento acontece upstream no DataLoader.

### 5.2 `AIContext.get_system_prompt` — adicionar awareness multi-tenant

```python
@staticmethod
def get_system_prompt(is_mobile: bool = False, tenant_name: str = "") -> str:
    base = "..." # prompt atual
    if tenant_name:
        base += f"\n\nVocê está operando exclusivamente no contexto do cliente '{tenant_name}'. "
        base += "NUNCA retorne dados, comparações ou referências de outros clientes. "
        base += "Todos os dados disponíveis nesta sessão pertencem exclusivamente a este cliente."
    return base
```

Passar `tenant_name` no `stream_chat_bg`:
```python
# global_state.py ~linha 159:
tenant_name = ""  # buscar do state — adicionar campo GlobalState.current_client_name
system_prompt = AIContext.get_system_prompt(is_mobile=is_mobile, tenant_name=tenant_name)
```

Adicionar `current_client_name: str = ""` ao `GlobalState` e populá-lo no `check_login`
com `client_info[0].get("name", "")`.

### 5.3 AI Tools: Queries SQL diretas (`execute_tool`)

Quando a IA executa uma query SQL via tool, ela deve sempre incluir `WHERE client_id = '...'`.
Adicionar ao schema context (`get_schema_context` RPC):

```sql
-- Modificar a função get_schema_context para incluir nota de isolamento:
-- "IMPORTANTE: Todas as queries devem incluir WHERE client_id = '{client_id}'"
```

Alternativamente, criar variante `get_schema_context_for_tenant(p_client_id uuid)` que
retorna o schema com a instrução de isolamento embutida.

---

## 6. Fase 5: Empty State — Tenant PLENO

**Objetivo**: Garantir que a UI não quebre quando um tenant não tem dados.

### 6.1 Pontos de risco

Identificar componentes que assumem DataFrames não-vazios:
```
grep -rn "\.iloc\[0\]\|\.values\[0\]\|len(df) > 0\|df\.empty" bomtempo/
```

Padrão defensivo nos KPI cards e gráficos:
```python
# ANTES:
valor = df["valor_contratado"].sum()

# DEPOIS:
valor = df["valor_contratado"].sum() if not df.empty else 0.0
```

### 6.2 Mensagem de Empty State

Criar componente reutilizável:
```python
def empty_state_card(message: str = "Nenhum dado cadastrado ainda.") -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("inbox", size=48, color=S.TEXT_MUTED),
            rx.text(message, color=S.TEXT_MUTED),
        ),
        padding="60px",
    )
```

---

## 7. Roadmap de Execução (Sequência Recomendada)

### Sprint 1 — Fundação de Dados (sem toque no frontend)
| # | Tarefa | Arquivo | Risco |
|---|---|---|---|
| 1.1 | Backup do banco no Supabase | — | Precondição |
| 1.2 | Executar SQL V2 refinado + verificação | `sql_multi_tenant_migration_v2.sql` | Alto |
| 1.3 | Validar checklist SQL (seção 2.2) | — | — |
| 1.4 | Aplicar NOT NULL + DROP DEFAULT | SQL Editor | Médio |

### Sprint 2 — Isolamento no Backend
| # | Tarefa | Arquivo | Risco |
|---|---|---|---|
| 2.1 | Adicionar `client_id` ao DataLoader (cache + queries) | `data_loader.py` | Alto |
| 2.2 | Atualizar todos os pontos de instanciação do DataLoader | `global_state.py` | Médio |
| 2.3 | Adicionar `current_client_name` ao GlobalState | `global_state.py` | Baixo |
| 2.4 | Adicionar redirecionamento pós-login (master → /master) | `global_state.py` | Baixo |
| 2.5 | Auditar todos os `sb_insert` — garantir `client_id` em writes | `**/state/*.py` | Alto |
| 2.6 | Invalidar cache tenant-aware no logout | `global_state.py` | Baixo |

### Sprint 3 — Validação de Isolamento
| # | Tarefa | Como Validar |
|---|---|---|
| 3.1 | Login como `master` → ver Console (sem dados operativos) | Manual |
| 3.2 | Login como usuário BOMTEMPO → ver dashboard com dados | Manual |
| 3.3 | Login como usuário PLENO (criar um) → ver dashboard vazio sem erros | Manual |
| 3.4 | Confirmar que BOMTEMPO não vê dados do PLENO (e vice-versa) | Manual |

### Sprint 4 — Master Console UI
| # | Tarefa | Arquivo |
|---|---|---|
| 4.1 | Criar `master_state.py` com `load_master_data` | `bomtempo/state/master_state.py` |
| 4.2 | Criar `master_console.py` (página) | `bomtempo/pages/master_console.py` |
| 4.3 | Registrar rota `/master` no `bomtempo.py` | `bomtempo/bomtempo.py` |
| 4.4 | Sidebar condicional (Master vs Client) | `bomtempo/components/sidebar.py` |
| 4.5 | Proteção de rota em `load_master_data` | `master_state.py` |

### Sprint 5 — IA Multi-tenant
| # | Tarefa | Arquivo |
|---|---|---|
| 5.1 | Passar `tenant_name` ao `get_system_prompt` | `global_state.py`, `ai_context.py` |
| 5.2 | Modificar/criar `get_schema_context_for_tenant` | SQL/RPC no Supabase |

### Sprint 6 — Empty States & Hardening
| # | Tarefa |
|---|---|
| 6.1 | Auditar KPI cards e gráficos para empty state |
| 6.2 | Criar componente `empty_state_card` reutilizável |
| 6.3 | Teste end-to-end com tenant PLENO (zero dados) |

---

## 8. O que NÃO fazer (Anti-padrões)

1. **Não usar RLS como isolamento primário agora** — o app usa `service_role`. RLS como
   defesa em profundidade é valioso mas é Sprint 7+, não agora.

2. **Não modificar a assinatura de `sb_select`** para injetar `client_id` automaticamente —
   isso quebraria queries globais (clients, roles). Use o wrapper `tenant_select()` ou
   passe o filtro explicitamente no DataLoader.

3. **Não criar um tenant "PLENO" com UUID fixo `222...222` em produção real** — UUIDs
   fixos são apenas para o ambiente de demonstração/dev. Em produção, gerar UUIDs reais via
   `gen_random_uuid()`.

4. **Não usar `client_id IS NULL` como "dados globais"** — após a migração, não deve
   existir nenhuma linha com `client_id IS NULL` nas tabelas tenant-scoped.

5. **Não cachear dados sem incluir `client_id` na chave do cache** — qualquer cache
   tenant-scoped deve incluir o `client_id` no identificador.

---

## 9. Inventário de Arquivos Afetados

```
bomtempo/
├── bomtempo.py                        → Registrar rota /master
├── core/
│   ├── data_loader.py                 → Cache por tenant + queries com client_id
│   └── ai_context.py                 → get_system_prompt recebe tenant_name
├── state/
│   ├── global_state.py               → DataLoader(client_id=...), redirect master, client_name
│   ├── master_state.py               → NOVO: estado do console master
│   ├── fin_state.py                  → Verificar sb_insert com client_id
│   ├── edit_state.py                 → Verificar sb_insert com client_id
│   └── [outros states]               → Auditoria de writes
├── pages/
│   └── master_console.py             → NOVO: página /master
└── components/
    └── sidebar.py                    → Sidebar condicional Master vs Client
```

---

## 10. Critérios de Aceite

- [ ] Usuário `master` não vê dados de obras/contratos/financeiro
- [ ] Usuário BOMTEMPO vê todos os dados atuais, sem regressão
- [ ] Usuário PLENO (novo) entra em dashboard vazio sem erros de runtime
- [ ] Cache separado por tenant (verificar `tempdir` com 2 sessões simultâneas)
- [ ] Todos os `sb_insert` em tabelas tenant-scoped incluem `client_id`
- [ ] IA não retorna dados de outros tenants
- [ ] Página `/master` só acessível pelo Master (proteção de rota)
- [ ] Sidebar mostra itens diferentes para Master vs Client
