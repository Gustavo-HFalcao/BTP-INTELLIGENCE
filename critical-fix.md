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
