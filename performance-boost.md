# PROMPT — Performance & UX Fluidity Overhaul · Bomtempo Platform
> Cole este prompt diretamente no Claude Code. Ele contém todo o contexto necessário para executar as melhorias one-shot.

---

## Contexto do sistema

Você está trabalhando na plataforma **Bomtempo** (BTP Intelligence), uma aplicação **Python + Reflex** multi-tenant com RBAC. A stack é:

- **Frontend/State**: Reflex 0.8.x (WebSocket-based, event handlers em Python)
- **Backend**: Uvicorn single-worker (1 CPU + 1GB RAM)
- **DB**: Supabase via `httpx` (cliente sync e async já implementados)
- **Cache**: Redis opcional + Pickle fallback (`core/redis_cache.py`, `core/data_loader.py`)
- **Executors**: Thread pools dedicados (`core/executors.py`) — bt-ai(2), bt-heavy(3), bt-http(4), bt-db(8)
- **Circuit breakers**: `core/circuit_breaker.py` — ia, nominatim, email
- **Rate limiter**: `core/rate_limiter.py` — sliding window por tenant
- **Logging**: `core/logging_utils.py` — `get_bound_logger`
- **Multi-tenancy**: `GlobalState.current_client_id` presente em todos os handlers

### Arquivos principais de state
```
bomtempo/state/
  global_state.py    ← state raiz (GlobalState) — muito grande
  hub_state.py       ← estado do Hub de Atividades
  rdo_state.py       ← geração de RDO + IA
  fin_state.py       ← financeiro
  edit_state.py      ← edição de projetos/contratos
bomtempo/core/
  data_loader.py     ← carregamento de dados com cache
  supabase_client.py ← sb_select/insert/update/delete + variantes async
  executors.py       ← get_ai_executor, get_heavy_executor, get_http_executor, get_db_executor
  circuit_breaker.py ← ia_breaker, nominatim_breaker, email_breaker
  redis_cache.py     ← RedisCache com namespace por tenant
  logging_utils.py   ← get_bound_logger
```

### Regras arquiteturais já estabelecidas (NÃO violar)
1. Nunca I/O síncrono no event loop — usar `async_sb_select/insert/update/delete` ou `@rx.event(background=True)`
2. Sempre invalidar cache ao criar/editar/deletar (`DataLoader.invalidate_cache(client_id)`)
3. Circuit breaker em toda API externa
4. Multi-tenancy obrigatório — todo payload inclui `client_id`, toda query filtra por `client_id`
5. Executor dedicado por tipo de tarefa
6. Logs com contexto tenant via `get_bound_logger`

---

## Problema central

A plataforma está **lenta e travando** mesmo com um único usuário de teste. Qualquer clique demora segundos para responder. A navegação entre páginas parece pesada. Isso acontece em demos ao vivo e é crítico para o negócio.

### Causa raiz identificada

O Reflex funciona via WebSocket: cada evento serializa o **state inteiro** → envia para o Python → processa → serializa o diff → atualiza o frontend. Se o `GlobalState` é um objeto monolítico com centenas de vars e listas grandes, **cada clique — até fechar um modal — serializa e transmite dezenas de kilobytes**. Somado a handlers que não fazem `yield` intermediário e ausência de optimistic UI, o resultado é a sensação de lentidão relatada.

---

## O que você deve fazer

Implemente **todos os padrões abaixo** na ordem indicada. Leia cada arquivo relevante antes de editar. Preserve toda a lógica de negócio existente — estas são melhorias de arquitetura e UX, não reescritas.

---

## PARTE 1 — Separação de State (maior impacto, fazer primeiro)

### 1.1 Criar `UIState` separado do `GlobalState`

Crie `bomtempo/state/ui_state.py`:

```python
import reflex as rx

class UIState(rx.State):
    """
    Estado exclusivo de UI — modais, abas, loading, toasts, sidebar.
    Separado do GlobalState para minimizar o payload serializado por evento.
    Qualquer clique que só afeta UI (abrir modal, trocar aba) só serializa este state leve.
    """
    # Modais
    show_novo_projeto_modal: bool = False
    show_delete_confirm_modal: bool = False
    show_edit_modal: bool = False
    delete_target_id: str = ""

    # Navegação interna
    active_tab: str = "hub"
    sidebar_collapsed: bool = False

    # Loading granular por seção (evita bloquear a tela inteira)
    # Chave = nome da seção ("hub", "fin", "rdo", etc.), valor = bool
    loading_sections: dict[str, bool] = {}

    # Toast / feedback inline
    toast_message: str = ""
    toast_type: str = "info"  # "info" | "success" | "error" | "warning"
    toast_visible: bool = False

    # Search / filtros locais (não precisam ir ao banco)
    search_query: str = ""
    active_filter: str = "todos"

    def set_loading(self, section: str, value: bool):
        self.loading_sections = {**self.loading_sections, section: value}

    def show_toast(self, msg: str, type_: str = "info"):
        self.toast_message = msg
        self.toast_type = type_
        self.toast_visible = True

    def hide_toast(self):
        self.toast_visible = False

    def open_modal(self, modal_name: str, target_id: str = ""):
        setattr(self, f"show_{modal_name}_modal", True)
        if target_id:
            self.delete_target_id = target_id

    def close_all_modals(self):
        self.show_novo_projeto_modal = False
        self.show_delete_confirm_modal = False
        self.show_edit_modal = False
        self.delete_target_id = ""
```

### 1.2 Migrar vars de UI do `GlobalState` para `UIState`

No `global_state.py`, identifique e **remova** todas as vars que são exclusivamente de UI (flags de modal, tabs ativas, loading flags genéricos, mensagens de erro/toast, search queries). Substitua por referências ao `UIState`.

Padrão de busca — vars para migrar:
```python
# Qualquer var com estes padrões de nome:
show_*: bool        # flags de modal/visibilidade
is_loading: bool    # loading genérico
active_*: str       # tab/view ativa
*_error: str        # mensagens de erro inline
*_query: str        # filtros de busca local
toast_*             # feedback ao usuário
```

**Atenção**: vars que são lidas em componentes que também acessam `GlobalState` podem continuar no `GlobalState` como `@rx.cached_var` que delegam para `UIState`. Evite import circular — `UIState` não importa `GlobalState`.

### 1.3 Converter computed vars para `@rx.cached_var`

Em **todos os state files**, identifique vars que são calculadas a partir de outras e converta para `@rx.cached_var`. Elas não são serialiadas no state — só recalculam quando suas dependências mudam.

Padrão de identificação:
```python
# ❌ Calculado no handler e guardado em var — RUIM
async def load_fin(self):
    rows = await async_sb_select(...)
    self.fin_data = rows
    self.total_contratado = sum(r["valor_contratado"] for r in rows)  # ← mover para cached_var
    self.projetos_ativos = len([r for r in rows if r["status"] == "ativo"])  # ← mover

# ✅ Como deve ficar
class FinState(rx.State):
    fin_data: list[dict] = []

    @rx.cached_var
    def total_contratado(self) -> float:
        return sum(r.get("valor_contratado", 0) for r in self.fin_data)

    @rx.cached_var
    def projetos_ativos(self) -> int:
        return len([r for r in self.fin_data if r.get("status") == "ativo"])

    @rx.cached_var
    def custo_por_categoria(self) -> list[dict]:
        # agrupamento, formatação, etc.
        ...
```

---

## PARTE 2 — Optimistic UI em todas as ações mutativas

Para **toda operação de criar, editar ou deletar**, implemente o padrão optimistic:

1. Guardar backup do estado atual
2. Atualizar o state localmente **imediatamente** (antes de ir ao banco)
3. `yield` — envia o diff mínimo ao frontend (usuário vê a mudança instantaneamente)
4. Executar a operação no banco
5. Se falhou: reverter para o backup + mostrar toast de erro

Implemente este padrão em:

### 2.1 `hub_state.py` — deleção e atualização de atividades

```python
# Padrão a seguir para QUALQUER deleção em hub_state.py
async def delete_atividade(self, item_id: str):
    log = get_bound_logger(__name__, tenant_id=self.current_client_id)

    # 1. Backup
    backup = list(self.hub_list)

    # 2. Optimistic remove — usuário vê instantaneamente
    self.hub_list = [x for x in self.hub_list if x.get("id") != item_id]
    yield  # ← CRÍTICO: envia diff ao frontend antes de ir ao banco

    # 3. Persiste
    try:
        result = await async_sb_delete("hub_atividades", {"id": item_id, "client_id": self.current_client_id})
        if not result:
            raise ValueError("Delete retornou vazio")
        log.info("atividade deletada", extra={"item_id": item_id})
    except Exception as e:
        # 4. Rollback
        self.hub_list = backup
        async with self:
            self.toast_message = "Erro ao remover atividade. Tente novamente."
            self.toast_visible = True
        log.error("falha ao deletar atividade", extra={"item_id": item_id, "error": str(e)})
        yield
```

### 2.2 `global_state.py` — criação de projetos

```python
async def save_novo_projeto(self):
    # 1. Cria item temporário com ID local e status visual "saving"
    temp_id = f"temp_{uuid4().hex[:8]}"
    novo_item = {
        "id": temp_id,
        "nome": self.form_nome_projeto,
        "status": "ativo",
        "client_id": self.current_client_id,
        "_saving": True,  # flag visual para skeleton/spinner no card
    }

    # 2. Adiciona imediatamente à lista
    self.contratos_list = [novo_item] + list(self.contratos_list)
    yield  # usuário vê o novo projeto na lista imediatamente

    # 3. Persiste no banco
    try:
        payload = {
            "nome": self.form_nome_projeto,
            # ... demais campos do formulário
            "client_id": self.current_client_id,
        }
        result = await async_sb_insert("contratos", payload)
        real_id = result[0]["id"] if result else None

        if not real_id:
            raise ValueError("Insert não retornou ID")

        # 4. Substitui item temporário pelo real
        self.contratos_list = [
            {**x, "id": real_id, "_saving": False} if x["id"] == temp_id else x
            for x in self.contratos_list
        ]

        # 5. Invalida cache
        self.contratos_list_filtered = []
        DataLoader.invalidate_cache(self.current_client_id)

    except Exception as e:
        # 6. Rollback — remove item temporário
        self.contratos_list = [x for x in self.contratos_list if x["id"] != temp_id]
        self.toast_message = "Erro ao salvar projeto."
        self.toast_visible = True
    yield
```

### 2.3 Aplicar o mesmo padrão em `fin_state.py` e `edit_state.py`

Para cada `sb_insert`, `sb_update`, `sb_delete` encontrado nesses arquivos, aplicar o mesmo padrão de 4 passos acima.

---

## PARTE 3 — Yield imediato e Skeleton Screens

### 3.1 Regra do yield em 100ms

Todo handler que faz I/O deve executar um `yield` dentro dos primeiros 100ms — antes de qualquer chamada ao banco ou API. Isso garante que o usuário receba feedback visual imediato.

```python
# ❌ Handler sem yield — UI trava durante toda a execução
async def load_relatorio(self):
    self.is_loading = True  # ← nunca chegará ao frontend antes dos dados
    data = await async_sb_select("fin_custos", filters={"client_id": self.current_client_id})
    self.fin_data = data
    self.is_loading = False

# ✅ Handler com yield imediato
async def load_relatorio(self):
    self.is_loading_fin = True
    yield  # ← PRIMEIRO: usuário vê o skeleton imediatamente

    try:
        data = await async_sb_select("fin_custos", filters={"client_id": self.current_client_id})
        self.fin_data = data or []
    except Exception as e:
        self.toast_message = "Erro ao carregar dados financeiros."
        self.toast_visible = True
    finally:
        self.is_loading_fin = False
        yield  # ← ÚLTIMO: remove skeleton
```

### 3.2 Criar componente `skeleton_card` e `skeleton_table` reutilizáveis

Crie `bomtempo/components/skeletons.py`:

```python
import reflex as rx

def skeleton_line(width: str = "100%", height: str = "16px") -> rx.Component:
    """Linha de skeleton animada."""
    return rx.box(
        width=width,
        height=height,
        background="var(--gray-4)",
        border_radius="4px",
        # Animação de shimmer via keyframes CSS
        animation="shimmer 1.5s infinite",
        style={
            "@keyframes shimmer": {
                "0%": {"opacity": "0.6"},
                "50%": {"opacity": "1"},
                "100%": {"opacity": "0.6"},
            }
        }
    )

def skeleton_card(lines: int = 3) -> rx.Component:
    """Card de loading para usar enquanto dados carregam."""
    return rx.box(
        rx.vstack(
            *[skeleton_line(
                width=f"{100 - (i * 15)}%",
                height="14px"
              ) for i in range(lines)],
            spacing="2",
            align_items="flex-start",
            width="100%",
        ),
        padding="16px",
        border_radius="8px",
        border="1px solid var(--gray-5)",
        width="100%",
    )

def skeleton_table_row(cols: int = 4) -> rx.Component:
    """Linha de tabela skeleton."""
    return rx.tr(
        *[rx.td(skeleton_line(width="80%", height="12px"), padding="12px") for _ in range(cols)]
    )

def skeleton_table(rows: int = 5, cols: int = 4) -> rx.Component:
    """Tabela inteira skeleton."""
    return rx.table(
        rx.tbody(
            *[skeleton_table_row(cols) for _ in range(rows)]
        ),
        width="100%",
    )
```

### 3.3 Usar skeleton em todas as seções que carregam dados

Em cada página/componente que exibe dados carregados por um handler, aplique:

```python
# Padrão para qualquer seção com dados
def hub_section() -> rx.Component:
    return rx.cond(
        UIState.loading_sections.get("hub", False),
        # Loading state — skeleton imediato
        rx.vstack(
            *[skeleton_card(lines=3) for _ in range(4)],
            width="100%",
        ),
        # Estado normal com dados
        rx.vstack(
            rx.foreach(HubState.hub_list, hub_atividade_card),
            width="100%",
        )
    )
```

---

## PARTE 4 — Navegação suave entre páginas

### 4.1 Padrão de `on_load` não-bloqueante

O `on_load` de uma página **nunca deve bloquear** a renderização. A página deve renderizar imediatamente com skeletons e carregar os dados em paralelo.

```python
# ❌ on_load bloqueante — página fica em branco até carregar
app.add_page(hub_page, route="/hub", on_load=HubState.load_hub_data)

# ✅ on_load não-bloqueante com skeleton
# No state:
class HubState(rx.State):
    hub_list: list[dict] = []
    _hub_loaded: bool = False  # var privada (não serializada)

    async def on_load_hub(self):
        if self._hub_loaded and self.hub_list:
            return  # já carregado, não recarrega
        
        # Mostra skeleton imediatamente
        async with self:
            self.set_loading("hub", True)
        yield

        # Carrega dados
        try:
            data = await async_sb_select(
                "hub_atividades",
                filters={"client_id": self.current_client_id},
                order={"column": "created_at", "desc": True},
                limit=50,  # paginação inicial
            )
            async with self:
                self.hub_list = data or []
                self._hub_loaded = True
        except Exception as e:
            log = get_bound_logger(__name__, tenant_id=self.current_client_id)
            log.error("falha ao carregar hub", extra={"error": str(e)})
        finally:
            async with self:
                self.set_loading("hub", False)
            yield
```

### 4.2 Cache de dados entre navegações

Se o usuário navega de `/hub` para `/fin` e volta para `/hub`, os dados não devem ser recarregados do banco — usar o state em memória. Só recarregar se:
- O cache Redis/pickle foi invalidado (por uma mutação)
- Passaram mais de 5 minutos desde o último load

```python
import time

class HubState(rx.State):
    hub_list: list[dict] = []
    _last_loaded_at: float = 0.0
    CACHE_TTL = 300  # 5 minutos

    async def on_load_hub(self):
        now = time.time()
        cache_valid = (
            self.hub_list and
            (now - self._last_loaded_at) < self.CACHE_TTL
        )
        if cache_valid:
            return  # dados ainda frescos — não vai ao banco

        async with self:
            self.set_loading("hub", True)
        yield

        # ... carrega dados ...

        async with self:
            self._last_loaded_at = now
            self.set_loading("hub", False)
        yield
```

### 4.3 Transição visual na troca de página

No componente de layout principal (`bomtempo/components/layout.py` ou equivalente), adicione uma barra de progresso no topo que aparece durante navegação. Reflex oferece `rx.progress` — use-o vinculado a `UIState.page_loading`:

```python
# Em UIState, adicionar:
page_loading: bool = False

# No layout raiz:
def root_layout(page_content: rx.Component) -> rx.Component:
    return rx.box(
        # Barra de progresso no topo — só aparece durante navegação/loading
        rx.cond(
            UIState.page_loading,
            rx.progress(
                value=None,  # indeterminate
                width="100%",
                position="fixed",
                top="0",
                left="0",
                z_index="9999",
                height="2px",
                color_scheme="blue",
            ),
            rx.fragment(),
        ),
        page_content,
        width="100%",
    )
```

---

## PARTE 5 — Reduzir payload do state serializado

### 5.1 Vars privadas para estado interno

Vars prefixadas com `_` no Reflex **não são serializadas** para o frontend. Use isso para estado interno que o frontend não precisa ver:

```python
class GlobalState(rx.State):
    # ✅ Público — serializado, frontend pode acessar
    contratos_list: list[dict] = []
    current_client_id: str = ""

    # ✅ Privado — NÃO serializado, só Python tem acesso
    _data_cache: dict = {}          # cache interno
    _last_load_time: float = 0.0    # timestamp do último load
    _pending_operations: list = []   # operações em fila
```

### 5.2 Paginar listas grandes desde o load inicial

Nunca carregar mais de 50 itens por vez em qualquer lista. Implementar paginação ou scroll infinito.

```python
class HubState(rx.State):
    hub_list: list[dict] = []
    hub_page: int = 0
    hub_has_more: bool = True
    HUB_PAGE_SIZE: int = 50

    async def load_hub_page(self, page: int = 0):
        offset = page * self.HUB_PAGE_SIZE
        data = await async_sb_select(
            "hub_atividades",
            filters={"client_id": self.current_client_id},
            order={"column": "created_at", "desc": True},
            limit=self.HUB_PAGE_SIZE + 1,  # +1 para saber se tem mais
            offset=offset,
        )
        items = (data or [])[:self.HUB_PAGE_SIZE]
        has_more = len(data or []) > self.HUB_PAGE_SIZE

        if page == 0:
            self.hub_list = items
        else:
            self.hub_list = list(self.hub_list) + items

        self.hub_page = page
        self.hub_has_more = has_more

    async def load_more_hub(self):
        if self.hub_has_more:
            await self.load_hub_page(self.hub_page + 1)
```

### 5.3 Filtrar no banco, não em Python

Qualquer filtro que o usuário aplica (por status, data, categoria) deve gerar uma nova query ao banco — **não filtrar uma lista gigante em memória**.

```python
# ❌ Filtragem em memória — carrega tudo e filtra em Python
@rx.cached_var
def hub_filtrado(self) -> list[dict]:
    return [x for x in self.hub_list if x["status"] == self.filtro_status]

# ✅ Filtragem no banco — só traz o que precisa
async def aplicar_filtro_hub(self, status: str):
    self.filtro_status = status
    async with self:
        self.set_loading("hub", True)
    yield

    filters = {"client_id": self.current_client_id}
    if status != "todos":
        filters["status"] = status

    data = await async_sb_select("hub_atividades", filters=filters, limit=50)
    async with self:
        self.hub_list = data or []
        self.set_loading("hub", False)
    yield
```

---

## PARTE 6 — Background tasks para operações longas

### 6.1 Toda operação > 200ms deve ser background task

Use `@rx.event(background=True)` para qualquer operação que demora mais de 200ms e não precisa de streaming de atualizações intermediárias.

```python
# Exportação de relatório, envio de e-mail, geração de PDF — sempre background
@rx.event(background=True)
async def exportar_relatorio_pdf(self):
    async with self:
        self.export_status = "gerando"
        self.export_progress = 0
    # yield não funciona em background tasks — usar async with self

    try:
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(
            get_heavy_executor(),
            lambda: generate_pdf(self.fin_data, self.current_client_id)
        )
        async with self:
            self.export_url = upload_to_storage(pdf_bytes)
            self.export_status = "pronto"
    except Exception as e:
        async with self:
            self.export_status = "erro"
            self.toast_message = "Erro ao gerar PDF."
```

### 6.2 Padrão de progresso em background tasks longas

```python
@rx.event(background=True)
async def processar_importacao(self, arquivo: list):
    total = len(arquivo)
    async with self:
        self.import_total = total
        self.import_progresso = 0
        self.import_status = "processando"

    for i, linha in enumerate(arquivo):
        await async_sb_insert("contratos", {**linha, "client_id": self.current_client_id})
        if i % 5 == 0:  # atualiza progresso a cada 5 itens
            async with self:
                self.import_progresso = int((i / total) * 100)

    async with self:
        self.import_status = "concluido"
        self.import_progresso = 100
        DataLoader.invalidate_cache(self.current_client_id)
```

---

## PARTE 7 — Toast system global

Substitua qualquer mecanismo de feedback inline por um sistema de toast centralizado no `UIState`. O toast deve aparecer e desaparecer automaticamente.

### 7.1 Componente de toast

Crie `bomtempo/components/toast.py`:

```python
import reflex as rx
from bomtempo.state.ui_state import UIState

def toast_notification() -> rx.Component:
    """Toast global — posicionado no canto inferior direito."""
    color_map = {
        "success": "green",
        "error": "red",
        "warning": "yellow",
        "info": "blue",
    }
    return rx.cond(
        UIState.toast_visible,
        rx.box(
            rx.hstack(
                rx.text(UIState.toast_message, size="2"),
                rx.icon_button(
                    rx.icon("x", size=12),
                    on_click=UIState.hide_toast,
                    size="1",
                    variant="ghost",
                ),
                justify="between",
                align="center",
                width="100%",
            ),
            position="fixed",
            bottom="24px",
            right="24px",
            z_index="10000",
            min_width="280px",
            max_width="400px",
            padding="12px 16px",
            border_radius="8px",
            border="1px solid",
            background=rx.color(UIState.toast_type, 2),
            border_color=rx.color(UIState.toast_type, 6),
            color=rx.color(UIState.toast_type, 11),
            box_shadow="0 4px 12px rgba(0,0,0,0.08)",
        ),
        rx.fragment(),
    )
```

Inclua `toast_notification()` no layout raiz da aplicação. Substitua todos os `rx.alert`, mensagens de erro inline e `rx.toast` por chamadas ao `UIState.show_toast(msg, type_)`.

---

## PARTE 8 — Audit e limpeza de handlers existentes

Percorra **todos os handlers** em `global_state.py`, `hub_state.py`, `rdo_state.py`, `fin_state.py`, `edit_state.py` e aplique este checklist em cada um:

```
Para cada handler (def ou async def com @rx.event):

[ ] 1. Tem yield imediato antes do primeiro I/O?
[ ] 2. Usa async_sb_* em vez de sb_* (quando não é background task)?
[ ] 3. Todo payload de insert/update inclui client_id?
[ ] 4. Tem try/except com rollback e toast de erro?
[ ] 5. Vars computadas viraram @rx.cached_var?
[ ] 6. Vars de UI foram removidas e substituídas por UIState?
[ ] 7. Operações > 200ms usam @rx.event(background=True)?
[ ] 8. Listas sendo carregadas têm limit (máx 50 no load inicial)?
```

---

## PARTE 9 — Melhorias de componentes React/Reflex

### 9.1 Debounce em campos de busca

Campos de busca não devem disparar evento a cada tecla. Use debounce de 300ms:

```python
# Em UIState:
async def on_search_change(self, value: str):
    self.search_query = value
    # Não vai ao banco aqui — o componente usa on_change com debounce
    # A busca efetiva é disparada por on_blur ou por um botão

# No componente:
rx.input(
    value=UIState.search_query,
    on_change=UIState.set_search_query,  # só atualiza o var local
    on_blur=HubState.buscar_por_query,   # vai ao banco quando sai do campo
    debounce=300,  # Reflex 0.8 suporta debounce nativo
    placeholder="Buscar atividades...",
)
```

### 9.2 Lazy loading de seções ocultas

Seções em abas ou accordions que estão ocultas não devem carregar dados até serem abertas:

```python
def financeiro_tab() -> rx.Component:
    return rx.cond(
        UIState.active_tab == "financeiro",
        rx.vstack(
            rx.cond(
                UIState.loading_sections.get("fin", False),
                skeleton_table(rows=6, cols=5),
                financeiro_content(),
            )
        ),
        rx.fragment(),  # ← não renderiza nada enquanto aba inativa
    )
```

---

## PARTE 10 — Verificações finais

Após implementar todas as partes acima, execute estas verificações:

### 10.1 Verificar tamanho do state serializado

Adicione temporariamente ao `GlobalState` um handler de diagnóstico:

```python
async def debug_state_size(self):
    import json, sys
    state_dict = self.dict()
    size_bytes = sys.getsizeof(json.dumps(state_dict))
    print(f"[DEBUG] State size: {size_bytes / 1024:.1f} KB")
    print(f"[DEBUG] Vars count: {len(state_dict)}")
    # Listas grandes:
    for k, v in state_dict.items():
        if isinstance(v, list) and len(v) > 10:
            print(f"[DEBUG]   {k}: {len(v)} items")
```

O tamanho do state serializado após a refatoração deve ser **< 5KB por evento de UI** (clique em botão, abrir modal, etc.).

### 10.2 Testar o fluxo crítico de demo

Simule o fluxo exato que causa vergonha em demos:

1. Login → dashboard carrega com skeleton (< 200ms até ver algo na tela)
2. Clicar em "Hub" → troca de aba instantânea, dados carregam em background
3. Deletar uma atividade → some imediatamente da lista, sem esperar banco
4. Criar novo projeto → aparece na lista imediatamente com indicador de "salvando"
5. Abrir modal → abre instantaneamente (UIState only, zero latência)
6. Gerar RDO → botão fica em loading, barra de progresso aparece, usuário pode navegar enquanto gera

### 10.3 Checklist de regressão

```
[ ] Login ainda funciona (check_login intacto)
[ ] Multi-tenancy preservado (todos os inserts têm client_id)
[ ] Cache invalidation funciona (novo projeto aparece imediatamente)
[ ] Circuit breakers ainda ativos (ia_breaker, nominatim_breaker, email_breaker)
[ ] Background tasks de RDO com timeout de 45s mantido
[ ] Logs estruturados com tenant_id em todos os handlers críticos
[ ] Redis session state mantido (rxconfig.py inalterado)
```

---

## Ordem de execução recomendada

Execute na seguinte ordem para maximizar impacto e minimizar risco de regressão:

```
1. Criar ui_state.py (sem tocar em nada existente)
2. Adicionar @rx.cached_var em FinState e HubState (baixo risco)
3. Converter vars de UI do GlobalState para UIState (médio risco — testar após)
4. Implementar optimistic UI em hub_state.py (alto impacto, testar delete/create)
5. Adicionar yield imediato em todos os handlers de load (alto impacto)
6. Criar skeleton components e integrar nas páginas (visual, sem lógica)
7. Implementar cache entre navegações (evitar reloads desnecessários)
8. Toast system global (substituir feedbacks inline)
9. Debounce em buscas + lazy loading de abas
10. Paginação (50 itens por load)
11. Debug de tamanho do state + ajuste fino
```

---

## Arquivos a criar (novos)
- `bomtempo/state/ui_state.py`
- `bomtempo/components/skeletons.py`
- `bomtempo/components/toast.py`

## Arquivos a modificar (principais)
- `bomtempo/state/global_state.py` — remover vars de UI, adicionar cached_vars, yield em handlers
- `bomtempo/state/hub_state.py` — optimistic UI, yield, paginação
- `bomtempo/state/fin_state.py` — cached_vars, yield, filtros no banco
- `bomtempo/state/rdo_state.py` — verificar yield, progress em background task
- `bomtempo/state/edit_state.py` — optimistic UI em edições
- `bomtempo/components/layout.py` (ou equivalente) — adicionar toast + barra de progresso
- Páginas em `bomtempo/pages/` — integrar skeletons, on_load não-bloqueante

---

> **Lembre-se**: O objetivo é passar a sensação de leveza e responsividade ao usuário. Mesmo que uma operação leve 2 segundos no backend, o usuário deve ver feedback visual em menos de 100ms. Optimistic UI + skeleton screens + yield imediato são os três pilares disso.