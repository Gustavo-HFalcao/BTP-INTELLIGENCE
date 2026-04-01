# Architecture Boost — Bomtempo Platform

> **Propósito**: Rastrear melhorias arquiteturais de resiliência, performance e multi-tenancy.
> Este arquivo DEVE ser consultado antes de criar qualquer nova feature, módulo ou tabela.
> Atualizar o status conforme implementações avançam.

---

## Status das Implementações

### Fase 1 — Event Loop Protection (CRÍTICO — causa raiz dos travamentos)

| Status | Item | Arquivo | Descrição |
|--------|------|---------|-----------|
| ✅ Feito | `load_data` async | `state/global_state.py` | Convertido para async generator + `run_in_executor` — elimina bloqueio global do event loop |
| ✅ Feito | `save_novo_projeto` cache | `state/global_state.py` | Invalida cache + limpa `contratos_list` antes do reload — projetos aparecem imediatamente |
| ✅ Feito | `save_novo_projeto` geocoding | `state/global_state.py` | Geocoding HTTP movido para `run_in_executor` — não bloqueia mais event loop |
| ✅ Feito | `confirm_cron_delete` UI | `state/hub_state.py` | Optimistic UI removal — atividade some imediatamente na UI antes do DB confirmar |
| ✅ Feito | `execute_submit` IA timeout | `state/rdo_state.py` | `asyncio.wait_for` 45s — RDO nunca mais fica gerando infinito |
| ✅ Feito | `save_avatar_pref` | `state/global_state.py` | `@rx.event(background=True)` — não bloqueia event loop |
| ✅ Feito | `save_password` | `state/global_state.py` | `@rx.event(background=True)` — não bloqueia event loop |
| ✅ Feito | `save_contact` | `state/global_state.py` | `@rx.event(background=True)` — não bloqueia event loop |
| ✅ Feito | `check_login` DB call | `state/global_state.py` | Usa `async_sb_select` — login não bloqueia event loop |
| ✅ Feito | `save_chat_msg` | `state/global_state.py` | `@rx.event(background=True)` — persistência de chat não bloqueia event loop |
| ✅ Feito | `force_refresh_data` | `state/global_state.py` | Corrigido bug de `CACHE_FILE` inexistente — usa `DataLoader.invalidate_cache()` |

### Fase 2 — Infraestrutura de Resiliência

| Status | Item | Arquivo | Descrição |
|--------|------|---------|-----------|
| ✅ Feito | Circuit Breaker | `core/circuit_breaker.py` | Breakers para IA, Nominatim, Email — proteção contra cascata de falhas |
| ✅ Feito | Dedicated Executors | `core/executors.py` | Thread pools separados: AI (2), Heavy I/O (3), HTTP (4), DB (8) |
| ✅ Feito | Structured Logging | `core/logging_utils.py` | `get_bound_logger(name, tenant_id=..., user_id=...)` para rastreabilidade multi-tenant |
| ✅ Feito | Async Supabase Client | `core/supabase_client.py` | `async_sb_select/insert/update/delete` — httpx.AsyncClient sem run_in_executor |
| ✅ Feito | RDO dedicated executors | `state/rdo_state.py` | IA usa `get_ai_executor()`, PDF usa `get_heavy_executor()` |

### Fase 3 — Cache & Performance

| Status | Item | Arquivo | Descrição |
|--------|------|---------|-----------|
| ✅ Feito | Redis cache por tenant | `core/redis_cache.py` | Cache Redis com namespace `t:{tenant_id}:{resource}` + fallback automático para pickle. Ativa com `REDIS_URL` no `.env` |
| ✅ Feito | DataLoader usa Redis | `core/data_loader.py` | Redis como primário, pickle como fallback. `invalidate_cache` limpa ambos |
| ✅ Feito | Rate limiter in-process | `core/rate_limiter.py` | Sliding window por tenant. Redis quando disponível, in-process como fallback. Sem Nginx necessário |
| ✅ Feito | Redis session state | `rxconfig.py` | Sessões Reflex persistem em restarts/deploys quando `REDIS_URL` configurado |
| ⏳ Pendente | Paginação no DataLoader | `core/data_loader.py` | Server-side pagination para datasets grandes. **Requer**: mudanças na UI de listagem. `sb_select_paginated` já existe no `supabase_client.py`. Priorizar quando qualquer tenant atingir >5k registros em `hub_atividades` ou `fin_custos`. |
| ⚠️ Monitorar | `alert_service.py` scheduler | `core/alert_service.py` | Daemon thread com `while True + time.sleep(60)` faz 24 queries/ciclo. Não bloqueia asyncio (thread separada), mas pressiona o connection pool. Refatorar para APScheduler se alertas crescerem. |

### Fase 4 — Escala Horizontal

> ⚠️ **Ambiente atual: 1 CPU + 1GB RAM — múltiplos workers são CONTRAINDICADOS.**
>
> Cada worker Python consome ~150–200MB RAM. Com 4 workers: 800MB só de processos → OOM.
> Com 1 CPU, workers disputam o mesmo núcleo sem ganho real de throughput.
> Nosso async I/O (run_in_executor + background tasks) já garante concorrência adequada.
> **Revisite quando o servidor escalar para ≥2 CPUs e ≥4GB RAM.**

| Status | Item | Descrição |
|--------|------|-----------|
| ⏳ Pendente | Múltiplos workers Uvicorn | **Pré-requisito: ≥2 CPUs + ≥4GB RAM.** N workers + Redis state + sticky sessions no Nginx. Hoje: skip. |
| ⏳ Pendente | Nginx rate limiting | `limit_req_zone` por tenant. Necessário apenas com múltiplos workers. Hoje: `rate_limiter.py` in-process é suficiente. |

---

## Regras Arquiteturais OBRIGATÓRIAS

> Toda nova feature, módulo ou tabela DEVE seguir estas regras. PRs que violarem devem ser bloqueados.

### Regra 1 — Nunca I/O síncrono no event loop

```python
# ❌ PROIBIDO — bloqueia o event loop, trava TODOS os usuários
def meu_handler(self):
    rows = sb_select("tabela", filters={"id": 1})  # BLOQUEIA

# ✅ CORRETO — opção A: handler async com async client
async def meu_handler(self):
    rows = await async_sb_select("tabela", filters={"id": 1})

# ✅ CORRETO — opção B: background task com sync client
@rx.event(background=True)
async def meu_handler(self):
    rows = sb_select("tabela", filters={"id": 1})  # OK em background

# ✅ CORRETO — opção C: run_in_executor explícito
async def meu_handler(self):
    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(get_db_executor(), lambda: sb_select("tabela"))
```

### Regra 2 — Sempre invalidar cache ao criar/editar/deletar

```python
# Após qualquer mutação em `contratos`:
async with self:
    self.contratos_list = []
    DataLoader.invalidate_cache(self.current_client_id)
yield GlobalState.load_data()
```

### Regra 3 — Circuit breaker para APIs externas

```python
from bomtempo.core.circuit_breaker import ia_breaker, nominatim_breaker, email_breaker

# IA
result = ia_breaker.call(lambda: ai_client.query(messages), fallback="")

# Geocoding
coords = nominatim_breaker.call(lambda: geocode(address), fallback=None)

# Email
email_breaker.call(lambda: send_email(to, subject, body))
```

### Regra 4 — Multi-tenancy obrigatório

```python
# TODO novo módulo/tabela DEVE ter client_id
payload = {
    "campo": valor,
    "client_id": self.current_client_id,  # OBRIGATÓRIO
}
# Toda query DEVE filtrar por client_id
rows = await async_sb_select("tabela", filters={"client_id": self.current_client_id})
```

### Regra 5 — Executor dedicado por tipo de tarefa

```python
from bomtempo.core.executors import get_ai_executor, get_heavy_executor, get_http_executor, get_db_executor

# IA (OpenAI, Claude, etc.)
result = await loop.run_in_executor(get_ai_executor(), lambda: ai_call())

# PDF/Chromium/uploads
pdf = await loop.run_in_executor(get_heavy_executor(), lambda: generate_pdf())

# Geocoding/webhooks HTTP
coords = await loop.run_in_executor(get_http_executor(), lambda: nominatim_geocode(addr))

# DB queries síncronas
rows = await loop.run_in_executor(get_db_executor(), lambda: sb_select(...))
```

### Regra 6 — Logs com contexto tenant

```python
from bomtempo.core.logging_utils import get_bound_logger

# No início de cada handler crítico:
log = get_bound_logger(__name__, tenant_id=self.current_client_id, user_id=self.current_user_name)
log.info("ação iniciada", extra={"action": "save_projeto"})
```

---

## Stack de Referência

| Camada | Tecnologia | Observação |
|--------|-----------|------------|
| Frontend/State | Reflex 0.8.x | Event handlers: async generator, background task |
| Workers | **1 worker** (1 CPU + 1GB RAM) | Async I/O garante concorrência. Revisar se servidor escalar |
| DB Client sync | `httpx.Client` (supabase_client.py) | Para uso em background tasks / executors |
| DB Client async | `httpx.AsyncClient` (supabase_client.py) | Para uso em handlers async diretos |
| Cache primário | Redis (`core/redis_cache.py`) | Namespace `t:{tenant_id}:{resource}`, TTL 1h, ativa com `REDIS_URL` |
| Cache fallback | Pickle file (`data_loader.py`) | Automático quando Redis não disponível |
| Session state | Redis via `rxconfig.py` | Sessões persistem em restarts. Ativa com `REDIS_URL` |
| Thread pools | `core/executors.py` | 4 pools: bt-ai(2), bt-heavy(3), bt-http(4), bt-db(8) |
| Circuit breaker | `core/circuit_breaker.py` | ia, nominatim, email, storage — in-process |
| Rate limiting | `core/rate_limiter.py` | Sliding window por tenant, Redis ou in-process |
| Logging | `core/logging_utils.py` + `get_bound_logger` | JSON mode via `LOG_FORMAT=json` env var |

## Configuração necessária no .env para ativar Redis

```env
# Adicione ao .env para ativar Redis cache + session state + rate limiting
REDIS_URL=redis://localhost:6379/0

# Para Redis Cloud ou Upstash (produção):
# REDIS_URL=redis://default:senha@host:port/0

# Opcional: TTL do cache de dados (default 3600s = 1 hora)
CACHE_TTL_SECONDS=3600

# Opcional: logs em JSON para produção (filtrável por tenant_id)
LOG_FORMAT=json
```

---

## Histórico de Incidentes

| Data | Incidente | Causa Raiz | Fix Aplicado |
|------|-----------|-----------|--------------|
| 2026-03-31 | Plataforma travou durante geração de RDO em demo | `load_data` síncrono bloqueava event loop asyncio em cada page load | Convertido para async generator + `run_in_executor` (Fase 1) |
| 2026-03-31 | Projetos novos não apareciam sem re-login | `save_novo_projeto` não invalidava cache antes de recarregar | Adicionado `contratos_list = []` + `invalidate_cache()` (Fase 1) |
