# Estabilização Sistêmica — Concorrência e Isolamento de Threads

## ⚠️ Problema Crítico Identificado
O sistema estava sofrendo de **Thread Starvation** e bloqueios severos no *Event Loop* principal do Reflex (Python/Asyncio). Isso ocorria devido ao uso do executor padrão (`loop.run_in_executor(None, ...)`) para tarefas de longa duração e alta intensidade computacional/IO, como:
1. Geração de relatórios complexos.
2. Análises de IA (streaming e síncronas).
3. Processamento de imagens (watermark) e PDFs.
4. Consultas extensas ao banco de dados (PostgREST).

Quando várias dessas tarefas rodavam simultaneamente, o pool de threads padrão do Python (limitado a `min(32, cpu_count + 4)`) era saturado, impedindo que novas requisições (como o login ou navegação básica) fossem processadas. O resultado era um sistema "congelado" ou um crash sistêmico.

## 🚀 Solução Arquitetural
Implementamos uma arquitetura de **Executores Categorizados** localizada em `bomtempo.core.executors`. Esta arquitetura segrega o trabalho em pools de threads independentes e limitados:

| Executor | Categoria | Limite | Motivo |
| :--- | :--- | :--- | :--- |
| `get_db_executor()` | Banco de Dados (Supabase) | 8 workers | Consultas rápidas e frequentes. |
| `get_ai_executor()` | IA (Claude, OpenAI) | 2 workers | Tarefas lentas (5-30s). Evita saturação de IA. |
| `get_heavy_executor()` | Heavy IO/CPU (Chromium, Imagem) | 1 worker | **Crítico:** chromium consome >500MB RAM. |
| `get_http_executor()` | HTTP Externo (SMTP, Geocoding) | 4 workers | Isolamento de latência de rede externa. |

## 🛠️ Mudanças Realizadas (Fevereiro/Março 2026)
Realizamos um varredura completa em toda a codebase (`/state` e `/pages`) substituindo 100% das chamadas bloqueantes:

- **Refatoração Global**: Todos os arquivos de estado (`hub_state`, `rdo_state`, `reembolso_state`, `usuarios_state`, `alertas_state`, `edit_state`, `relatorios_state`, etc.) foram migrados.
- **Isolamento de CRUD**: Operações de edição de dados e carregamento de logs agora rodam no pool de DB/HTTP dedicado.
- **Proteção de Relatórios**: A geração de relatórios, identificada como a principal causa de crashes, agora está estritamente isolada no `heavy_executor`.
- **Prevenção de Regressão**: Adicionada documentação em `executors.py` e regra de ouro: **NUNCA use `None` como executor**.

## 📝 Nota para Futuros Agentes (Claude Code / Cursor)
Ao adicionar novos handlers que realizam IO síncrono ou processamento pesado:
1. **Importe** o executor adequado: `from bomtempo.core.executors import get_db_executor`.
2. **Utilize** sempre: `await loop.run_in_executor(get_db_executor(), lambda: minha_funcao())`.
3. **Mantenha** chamadas de IA isoladas para não degradar a experiência de navegação do usuário.

Este fix garante que, mesmo que um relatório falhe ou demore, o resto do sistema (Login, Dashboard, RDO) permaneça responsivo.

---

## ⚠️ Crash Sistêmico — Redis Lock & Background Tasks (Abril 2026)

### Causa Raiz Identificada
O `execute_submit` do RDO fazia `await self.get_state(GlobalState)` **DENTRO** de um bloco `async with self:`. Isso segurava o **Redis lock** do estado enquanto aguardava uma segunda operação Redis para carregar GlobalState — uma deadlock-like condition que causava `LockExpiredError` após 10s.

A cadeia de falhas:
1. `execute_submit` → `async with self:` → await `get_state(GlobalState)` → lock expira em 10s
2. `LockExpiredError` em `set_navigating` → exceção não capturada em `AsyncServer._handle_event_internal`
3. WebSocket do usuário entra em estado quebrado → nenhum evento processa até reconexão

**Adicionalmente:** `check_login` e `load_initial_data_smooth` NÃO tinham `@rx.event(background=True)`, segurando o Redis lock por 1–5 segundos enquanto faziam I/O de rede.

### Fixes Aplicados (Abril 2026)

1. **`execute_submit`** (`rdo_state.py`): Movido `get_state(GlobalState)` para **antes** do `async with self:`. Adicionado `try/except` em todos os blocos `async with self:` de status update. Limpeza de estado grande (`signatory_sig_b64`, `hub_atividades_options`) logo após snapshot inicial para reduzir tamanho da serialização Redis.

2. **`lock_expiration`** (`rxconfig.py`): Aumentado de 10s para 60s via `state_manager_lock_expiration=60000`. Dá margem segura para Redis sob carga sem risco de lock zombie.

3. **`check_login`** (`global_state.py`): Convertido para `@rx.event(background=True)`. Todas as queries Supabase (1–2s) agora ocorrem **fora** de qualquer lock. Lock é segurado apenas milissegundos para ler/escrever variáveis em memória. `check_login_on_enter` atualizado para usar `yield GlobalState.check_login` em vez de chamar diretamente como generator.

4. **`load_initial_data_smooth`** (`global_state.py`): Convertido para `@rx.event(background=True)`. O `asyncio.sleep(5s)` agora ocorre **fora** de qualquer lock Redis. Antes, segurava o lock por 5s inteiros causando lock warnings e bloqueando todos os eventos do usuário.

### Regra de Ouro — `@rx.event(background=True)`
> **NUNCA faça `await` dentro de `async with self:`** a menos que seja uma operação trivialmente rápida.
> Qualquer I/O de rede (DB, HTTP, Redis) deve acontecer **fora** do bloco `async with self:`.
> Padrão correto:
> ```python
> gs = await self.get_state(OtherState)  # I/O fora da lock
> async with self:                         # lock ~1ms
>     self.some_var = gs.some_value
> ```

---

## Hierarquia de Atividades — Consistência Macro/Micro (Abril 2026)

- `fase_macro` de atividades **micro/sub** é somente leitura — herdada do pai.
- UI: campo "Fase Macro" exibido como display (não input) para nivel micro/sub.
- Backend: renomear uma macro agora cascateia `fase_macro` para todos os filhos (micros e subs) automaticamente.
- Guard no `set_cron_edit_fase_macro`: retorna sem alterar se `nivel in ("micro", "sub")`.

---

## OOM Kill Global — Substituição do Playwright/Chromium (Abril 2026)

### Causa Raiz do Crash Global
O processo de geração de PDF usava **Playwright/Chromium**, que consome 300–500 MB de RAM por chamada. No container Fly.io com apenas 1 GB de RAM total, uma única geração de PDF empurrava o processo Python para o limite → o kernel disparava um **OOM Kill** → o processo Reflex era reiniciado → **TODAS as conexões WebSocket caíam simultaneamente** → todos os usuários viam "Reconectando" ao mesmo tempo.

O problema NÃO era lock Redis — era **eliminação do processo pelo kernel por falta de memória**. Um crash de processo é global por natureza.

### Solução Arquitetural — Isolamento de Processo

**Antes:** Playwright rodava em thread no MESMO processo → OOM mata tudo.  
**Depois:** xhtml2pdf roda em subprocess isolado via `multiprocessing.Process` → se o worker OOM, SOMENTE ele morre. O servidor Reflex e todos os WebSockets continuam vivos.

**Mudanças em `pdf_utils.py`:**
1. Substituído Playwright/Chromium por **xhtml2pdf** (pico de RAM: ~20–40 MB, sem dependências binárias)
2. PDF generation roda em `multiprocessing.get_context("spawn").Process` — processo completamente isolado
3. Timeout de 120s (era 90s) — processo worker é `kill()`-ado se exceder
4. Qualquer RuntimeError no worker é capturado e retornado como `RuntimeError` para o chamador
5. Dependência adicionada em `requirements.txt`: `xhtml2pdf==0.2.16`

**Mudanças em `rdo_service.py` — redução de RAM do PIL:**
- `_MAX_DIM`: 2048 → 1440 px (reduz pico de memória PIL ~44%)
- `_OUTPUT_DIM`: 1920 → 1440 px (sem impacto visual perceptível no relatório)

### Regra de Ouro — Isolamento de Processos Pesados
> **NUNCA** rode Playwright, Chromium, wkhtmltopdf, ou qualquer binário externo de >100MB RAM em thread no processo principal do Reflex.
> Use `multiprocessing.Process(context="spawn")` para isolar o crash. O processo filho pode morrer; o servidor principal deve sobreviver.

## Watermark — Qualidade e Consistência (Abril 2026)

- Font size: `max(28, w//40)` → `max(40, out_w//32)` — calculado sobre a largura de **saída** (não processamento).
- Normalização de saída: usa `max(foto_w, foto_h)` em vez de apenas `w`. Portrait iPhone agora normaliza corretamente para 1920px no lado maior.
- JPEG quality: 88 → 92 para melhor legibilidade do texto da watermark.
