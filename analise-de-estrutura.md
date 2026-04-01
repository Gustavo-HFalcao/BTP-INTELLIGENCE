# Auditoria de Arquitetura — Prompt para Claude Code

---

Você é um arquiteto sênior de sistemas Python/Reflex auditando uma aplicação multi-tenant, multi-role em produção. A stack é: **Reflex (Python), Supabase (PostgREST + RLS), Redis, single process Uvicorn, menos de 100 usuários ativos**.

Já sabemos que houve um incidente de travamento global causado por I/O síncrono bloqueando o event loop asyncio. Esse incidente foi corrigido. Agora quero uma auditoria completa para identificar todas as fragilidades restantes.

---

## Instrução de análise

Analise **todos os arquivos** do projeto, especialmente:
- `*_state.py` / `global_state.py` / `hub_state.py`
- `supabase_client.py` / qualquer módulo de acesso a dados
- handlers com `@rx.event`, `@rx.event(background=True)`
- jobs, crons, tasks em background
- qualquer módulo de upload, geração de arquivo, PDF
- arquivos de configuração e variáveis de ambiente

---

## Categorias de auditoria

Avalie cada item abaixo de **0 a 10**, onde:
- **10** = sem problemas encontrados, padrão correto aplicado
- **7-9** = problemas pontuais, baixo risco
- **4-6** = problemas recorrentes, risco médio
- **0-3** = problemas críticos, risco alto ou imediato

---

### C1 — Estado Reflex

| ID | O que auditar |
|----|--------------|
| C1.1 | Variáveis mutáveis declaradas no nível da classe State (listas/dicts como `var: list = []` fora do `__init__`) — causam compartilhamento de estado entre sessões |
| C1.2 | Vars que crescem indefinidamente por sessão sem paginação ou limpeza — listas acumuladas a cada reload |
| C1.3 | Handlers longos sem `yield` intermediário — usuário fica sem feedback e o browser pode timeout |
| C1.4 | Handlers síncronos (`def` sem `async`) que fazem qualquer I/O — DB, HTTP, arquivo |

---

### C2 — Vazamento de recursos

| ID | O que auditar |
|----|--------------|
| C2.1 | Arquivos temporários criados sem garantia de limpeza — sem `try/finally`, sem TTL, sem cleanup periódico |
| C2.2 | Conexões HTTP abertas sem context manager (`with`/`async with`) — vazamento de file descriptors |
| C2.3 | Background tasks sem timeout ou condição de saída garantida — podem rodar infinitamente |
| C2.4 | ThreadPoolExecutor ou ProcessPoolExecutor criados dentro de funções — novo pool a cada chamada, sem reuso |

---

### C3 — Isolamento multi-tenant

| ID | O que auditar |
|----|--------------|
| C3.1 | Queries ao Supabase sem filtro explícito por `tenant_id`/`client_id` no código Python — dependência exclusiva de RLS |
| C3.2 | Estado carregado no login e reutilizado sem revalidação de tenant — dados de sessão anterior podem vazar |
| C3.3 | Caminhos de arquivo (uploads, PDFs, exports) sem `tenant_id` no nome — dois tenants podem sobrescrever o mesmo arquivo |
| C3.4 | Chaves de cache sem namespace por tenant — cache de um tenant pode ser lido por outro |

---

### C4 — Tratamento de erros

| ID | O que auditar |
|----|--------------|
| C4.1 | Blocos `except Exception` que silenciam o erro sem logar — sistema parece funcionar quando falhou |
| C4.2 | Chamadas ao Supabase sem tratamento de erro — sem `try/except`, sem verificação de `.data` antes de usar |
| C4.3 | Operações críticas (salvar, submeter, gravar) sem transação/rollback — inconsistência silenciosa se etapa intermediária falhar |
| C4.4 | Stack traces ou detalhes internos retornados ao frontend em caso de erro |

---

### C5 — Performance de queries

| ID | O que auditar |
|----|--------------|
| C5.1 | Padrão N+1 — loops Python que fazem query ao Supabase por iteração em vez de buscar tudo de uma vez |
| C5.2 | Queries sem paginação em tabelas que crescem com o uso — `SELECT *` sem `limit` |
| C5.3 | Filtros em colunas provavelmente sem índice — colunas usadas em `.eq()`, `.filter()`, `.order()` que não sejam PK |
| C5.4 | Dados carregados inteiros em memória para fazer filtragem em Python — filtragem que deveria ser feita no banco |

---

### C6 — Jobs e tarefas periódicas

| ID | O que auditar |
|----|--------------|
| C6.1 | Jobs sem mecanismo de lock — podem rodar em duplicata após restart ou se atrasarem |
| C6.2 | Jobs sem limite de concorrência — atraso acumula execuções simultâneas |
| C6.3 | `asyncio.sleep` em loop infinito dentro de background task — sem saída garantida nem tratamento de exceção |

---

### C7 — Segurança e exposição

| ID | O que auditar |
|----|--------------|
| C7.1 | Chaves de API, tokens ou senhas hardcoded no código-fonte |
| C7.2 | Segredos logados via `print()` ou logger sem sanitização |
| C7.3 | Endpoints ou handlers que retornam informações internas do sistema para o cliente em caso de erro |
| C7.4 | Inputs do usuário usados diretamente em queries ou caminhos de arquivo sem sanitização |

---

## Formato de resposta obrigatório

Responda com uma matriz única neste formato exato:

```
| ID   | Categoria              | Nota | Risco    | Ocorrências encontradas                          | Correção prioritária                        |
|------|------------------------|------|----------|--------------------------------------------------|---------------------------------------------|
| C1.1 | Estado Reflex          |  X   | Alto     | arquivo.py:linha — descrição curta               | Descrição objetiva da correção              |
| C1.2 | ...                    |  X   | ...      | ...                                              | ...                                         |
```

**Coluna Risco**: use `Crítico` (0-3), `Alto` (4-5), `Médio` (6-7), `Baixo` (8-10).

Após a matriz, inclua:

**Top 5 correções por impacto** — liste os 5 IDs com pior combinação de nota + risco, em ordem de prioridade, com o trecho exato do código problemático e a correção sugerida.

**Score geral do sistema** — média ponderada das notas, onde C3 (isolamento multi-tenant) e C4 (erros) têm peso 2x, os demais peso 1x. Apresente como `X.X / 10`.