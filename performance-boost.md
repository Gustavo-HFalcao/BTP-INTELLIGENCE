# Performance Boost — Rodada 2
> Segunda rodada de melhorias após a Rodada 1 já ter sido implementada.
> Foco: I/O síncrono bloqueante, serialização de listas grandes, re-renders em cascata, persistência client-side.

---

## O que já foi feito (Rodada 1 — não refazer)

- ✅ `UIState` criado em `bomtempo/state/ui_state.py` — state leve para modal/loading/toast
- ✅ `sidebar_open`, `show_risk_breakdown`, `show_alertas_ia_dialog` migrados para `UIState`
- ✅ `data_version: int` adicionado ao `GlobalState`, incrementado em todos os pontos de recarga
- ✅ `@rx.var` já usa `cache=True` por padrão no Reflex 0.8.26 — nenhuma conversão necessária
- ✅ Todos os handlers pesados já são `@rx.event(background=True)` com `async with self:`
- ✅ `DataLoader.load_all()` já usa `ThreadPoolExecutor(max_workers=5)` para queries paralelas
- ✅ Optimistic UI + rollback implementado em `confirm_cron_delete` no `hub_state.py`

---

## Contexto do sistema

- **Reflex 0.8.26** — computed vars são `@rx.var(cache=True)` por padrão. Não existe `@rx.cached_var`.
- **`rx.LocalStorage`** disponível via `rx.LocalStorage('default', name='key')` — persiste no browser, elimina necessidade do servidor guardar preferências de UI entre sessões.
- **Supabase async**: `async_sb_select`, `async_sb_insert`, `async_sb_update`, `async_sb_delete` disponíveis em `bomtempo/core/supabase_client.py`.
- **Executors**: `get_db_executor()` (8 threads), `get_heavy_executor()` (3 threads) disponíveis em `bomtempo/core/executors.py`.

---

## ITEM 1 — I/O síncrono bloqueando o event loop (impacto crítico)

### Problema

Três handlers regulares (não-background) fazem `sb_insert`/`sb_select` **síncronos diretamente**, bloqueando o event loop do Uvicorn enquanto aguardam o Supabase:

```python
# global_state.py — load_chat_history (linha ~187)
async def load_chat_history(self):
    new_sess = sb_insert("chat_sessions", {...})  # ← BLOQUEIA o event loop
    ...

# global_state.py — new_conversation (linha ~198)
async def new_conversation(self):
    new_sess = sb_insert("chat_sessions", {...})  # ← BLOQUEIA o event loop
    ...

# rdo_state.py — init_page (linha ~329)
async def init_page(self):
    # FeatureFlagsService.get_features_for_contract() faz sb_select síncrono
    self.rdo_active_features = FeatureFlagsService.get_features_for_contract(_contrato)
```

Como o Uvicorn usa **single worker**, qualquer I/O síncrono congela **todos os WebSockets ativos** enquanto aguarda resposta do banco.

### Correção

Mover para `run_in_executor` ou `async_sb_insert`:

```python
# ✅ global_state.py — load_chat_history
async def load_chat_history(self):
    import asyncio as _asyncio
    username = self.current_user_name or "anonymous"
    loop = _asyncio.get_running_loop()
    new_sess = await loop.run_in_executor(
        None,
        lambda: sb_insert("chat_sessions", {"title": "Conversa", "username": username, "client_id": self.current_client_id or None})
    )
    if new_sess:
        self.chat_session_id = new_sess["id"] if isinstance(new_sess, dict) else new_sess[0]["id"]
    self.chat_history = [_msg("assistant", "👋 Olá! Sou o Bomtempo Intelligence. Como posso ajudar?")]
    self.is_processing_chat = False
    yield rx.call_script("setTimeout(function(){ window.scrollToBottom('chat-container'); }, 150);")

# ✅ Mesmo padrão para new_conversation — trocar sb_insert por run_in_executor

# ✅ rdo_state.py — init_page
# Envolver a chamada síncrona do FeatureFlagsService em run_in_executor:
async def init_page(self):
    ...
    import asyncio as _asyncio
    loop = _asyncio.get_running_loop()
    try:
        _contrato_val = contrato or str(gs.current_user_contrato or "")
        if _contrato_val and _contrato_val not in ("nan", "None", ""):
            self.rdo_active_features = await loop.run_in_executor(
                None,
                lambda: FeatureFlagsService.get_features_for_contract(_contrato_val)
            )
        else:
            self.rdo_active_features = list(gs.active_features or [])
    except Exception:
        self.rdo_active_features = list(gs.active_features or [])
```

**Arquivos a editar**: `global_state.py` (load_chat_history, new_conversation), `rdo_state.py` (init_page).

---

## ITEM 2 — `rx.LocalStorage` para preferências de UI

### Problema

Vars como `sidebar_open` estão em `UIState` (servidor). A cada reconexão WebSocket (refresh, deploy, timeout), o estado é **resetado** — a sidebar abre, tabs voltam ao padrão. O usuário perde a preferência visual.

Adicionalmente, o servidor não precisa manter essas preferências em memória entre sessões — o browser pode guardar sozinho.

### Correção

Em `bomtempo/state/ui_state.py`, trocar as vars de preferência de UI para `rx.LocalStorage`:

```python
# ✅ Sintaxe correta para Reflex 0.8.26
from reflex import LocalStorage

class UIState(rx.State):
    # Persiste no browser — sobrevive a refresh, deploy, timeout
    # O servidor lê o valor do browser na hidratação inicial
    sidebar_open: str = LocalStorage("true", name="btp_sidebar")
    # Atenção: LocalStorage só suporta str. Converter bool → str ao ler:
    # rx.cond(UIState.sidebar_open == "true", "236px", "64px")
```

**Atenção**: `LocalStorage` em Reflex 0.8.26 é subclasse de `str` — não `bool`. Ajustar componentes que leem `sidebar_open` para comparar com `"true"` / `"false"` em vez de truthy direto.

**Variáveis candidatas**: `sidebar_open`, `avatar_modal_tab` (última aba aberta pelo usuário).

**Arquivos a editar**: `ui_state.py`, `sidebar.py` (ajustar `rx.cond` para `== "true"`), `top_bar.py` (idem).

---

## ITEM 3 — Remover bindings de GlobalState em componentes folha

### Problema

O maior custo silencioso do Reflex: qualquer componente que referencia uma var do `GlobalState` **re-renderiza toda vez que qualquer var do GlobalState mudar**, mesmo que seja uma var completamente diferente da que ele usa.

Exemplos de componentes folha que provavelmente têm esse problema em `hub_operacoes.py`:

```python
# ❌ Card que re-renderiza em QUALQUER mudança do GlobalState
def _projeto_card(data: dict) -> rx.Component:
    return rx.box(
        rx.text(GlobalState.current_user_name),  # ← binding desnecessário
        rx.text(data["projeto"]),
    )

# ❌ Item de lista que re-renderiza desnecessariamente
def _atividade_row(item: dict) -> rx.Component:
    return rx.tr(
        rx.td(GlobalState.selected_project),  # ← binding em GlobalState gigante
        rx.td(item["titulo"]),
    )
```

```python
# ✅ Componente folha sem binding em GlobalState
def _projeto_card(data: dict) -> rx.Component:
    return rx.box(
        rx.text(data["projeto"]),  # dado passado como dict — sem binding de state
        rx.text(data["cliente"]),
    )
```

### Como identificar

Buscar em `hub_operacoes.py`, `default.py`, `top_bar.py` por `GlobalState.` dentro de funções chamadas por `rx.foreach`. Cada binding de `GlobalState` dentro de um `rx.foreach` multiplica os re-renders pelo tamanho da lista.

### Exceções válidas

Bindings que são **necessários** e não podem ser removidos:
- `GlobalState.selected_project` num card que muda visual ao ser selecionado
- `GlobalState.is_loading` para mostrar/esconder skeleton

Para esses, considerar passar o valor como parâmetro via `rx.foreach(list, lambda item: componente(item))` onde o dado extra vem da lista, não do state.

**Arquivos a auditar**: `hub_operacoes.py` (principalmente dentro de `rx.foreach`), `default.py`.

---

## ITEM 4 — Event batching e `asyncio.gather` nos handlers de seção

### Problema A — queries em série dentro de um handler

Handlers que carregam múltiplas tabelas independentes fazem as queries **sequencialmente** em vez de em paralelo:

```python
# ❌ 3 queries em série — tempo total = t1 + t2 + t3
async def load_dashboard(self):
    self.hub_data = await async_sb_select("hub_atividades", ...)   # espera
    self.fin_data = await async_sb_select("fin_custos", ...)       # espera
    self.rdo_data = await async_sb_select("rdo_master", ...)       # espera
```

```python
# ✅ 3 queries em paralelo — tempo total = max(t1, t2, t3)
import asyncio

async def load_dashboard(self):
    hub, fin, rdo = await asyncio.gather(
        async_sb_select("hub_atividades", filters={"contrato": code}),
        async_sb_select("fin_custos",     filters={"contrato": code}),
        async_sb_select("rdo_master",     filters={"contrato": code, "limit": 20}),
    )
    self.hub_data = hub or []
    self.fin_data = fin or []
    self.rdo_data = rdo or []
```

### Problema B — múltiplos yields desnecessários

```python
# ❌ 3 round-trips WebSocket onde 2 seriam suficientes
async def load_section(self):
    self.is_loading = True
    yield                          # round-trip 1: mostra loading
    self.data_a = await fetch_a()
    yield                          # round-trip 2: atualiza parcial (desnecessário)
    self.data_b = await fetch_b()
    self.is_loading = False
    yield                          # round-trip 3: fim
```

```python
# ✅ 2 round-trips + queries em paralelo
async def load_section(self):
    self.is_loading = True
    yield                                      # round-trip 1: mostra loading imediato

    data_a, data_b = await asyncio.gather(fetch_a(), fetch_b())
    self.data_a = data_a or []
    self.data_b = data_b or []
    self.is_loading = False
    yield                                      # round-trip 2: tudo de uma vez
```

**Onde aplicar**: Qualquer handler que faz 2+ chamadas `await async_sb_select` em sequência.
**Nota**: O `DataLoader.load_all()` já usa `ThreadPoolExecutor` — não duplicar esse esforço.

---

## ITEM 5 — Banner de reconexão WebSocket

### Problema

Quando o WebSocket cai (deploy, timeout, instabilidade de rede), o app fica **silenciosamente morto** — o usuário clica e nada acontece. Sem feedback visual, parece que o app travou.

### Correção

Adicionar banner de reconexão usando `rx.State.is_hydrated` no layout principal (`default.py` ou `layouts/default.py`):

```python
# Em bomtempo/layouts/default.py — adicionar no topo do layout
def _connection_banner() -> rx.Component:
    """Banner visível apenas quando WebSocket não está conectado."""
    return rx.cond(
        ~rx.State.is_hydrated,
        rx.box(
            rx.hstack(
                rx.spinner(size="1"),
                rx.text("Reconectando...", size="1", weight="medium"),
                spacing="2",
                align="center",
            ),
            background="var(--amber-3)",
            color="var(--amber-11)",
            border_bottom="1px solid var(--amber-6)",
            padding="6px 16px",
            width="100%",
            text_align="center",
            position="fixed",
            top="0",
            left="0",
            z_index="9999",
        ),
        rx.fragment(),
    )
```

Inserir `_connection_banner()` como primeiro filho do componente raiz do layout.

**Arquivo a editar**: `bomtempo/layouts/default.py` (e possivelmente `bomtempo/pages/login.py`).

---

## ITEM 6 — Paginação/filtragem de `financeiro_list` no Supabase

### Problema

`financeiro_list` em `GlobalState` é serializada inteira para o browser em cada delta que toca essa lista. O código já tem um warning quando passa de 500 linhas. Com o crescimento natural dos dados, isso se tornará um gargalo crítico.

Atualmente `load_data` carrega `fin_custos` **sem filtro de contrato** — traz TODOS os custos do tenant, independente de qual projeto está sendo visualizado.

### Correção

Carregar `fin_custos` apenas para o contrato selecionado via `FinState.load_financeiro(contrato)` (que já existe e faz esse carregamento seletivo), e remover `financeiro_list` do carregamento inicial do `DataLoader`/`load_data`.

```python
# Em DataLoader.load_all() — remover fin_custos do carregamento inicial
TABLE_MAP = [
    ("contratos",              "contratos"),
    ("hub_atividades",         "projeto"),
    ("hub_atividade_historico","hub_historico"),
    # ("fin_custos",           "financeiro"),  ← REMOVER do load inicial
    ("om_geracoes",            "om"),
]
# fin_custos será carregado on-demand via FinState.load_financeiro(contrato)
```

```python
# Em GlobalState.load_data() — remover o bloco de financeiro:
# if "financeiro" in self._data:  ← REMOVER
#     df = get_df("financeiro")   ← REMOVER
#     ...

# As computed vars financeiras (total_financeiro_contratado, etc.)
# que hoje leem de self._data["financeiro"] devem migrar para ler
# de self.financeiro_list (já populada por FinState.load_financeiro)
```

**Impacto**: Reduz o payload inicial de load_data em N linhas × M colunas de fin_custos.
**Atenção**: Auditar todas as `@rx.var` que leem `self._data.get("financeiro")` antes de remover.

---

## Resumo de impacto estimado

| Item | Impacto | Risco | Arquivo(s) |
|------|---------|-------|-----------|
| 1 — I/O síncrono → run_in_executor | **Alto** — desbloqueia event loop | Baixo | `global_state.py`, `rdo_state.py` |
| 2 — `rx.LocalStorage` para sidebar | Médio — UX de persistência | Baixo | `ui_state.py`, `sidebar.py`, `top_bar.py` |
| 3 — Remover bindings em folha | **Alto** — elimina re-renders em cascata | Médio | `hub_operacoes.py` |
| 4 — asyncio.gather + batching | **Alto** — cargas 2-3× mais rápidas | Baixo | handlers com múltiplos await |
| 5 — Banner de reconexão | Baixo — UX básico | Muito Baixo | `layouts/default.py` |
| 6 — Paginar financeiro_list | **Alto** — payload cresce com dados | Médio | `data_loader.py`, `global_state.py` |

**Ordem recomendada de implementação**: 5 → 1 → 4 → 2 → 3 → 6
- 5 é trivial e melhora UX imediatamente
- 1 e 4 têm maior impacto de performance sem risco de quebrar lógica
- 2 é simples mas exige ajuste de componentes que leem `sidebar_open`
- 3 requer auditoria cuidadosa de `rx.foreach` antes de editar
- 6 exige auditoria das computed vars antes de remover do DataLoader
