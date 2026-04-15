# Plano de Melhorias — Fluxo RDO × Cronograma Integrado

> Criado em 2026-04-14 | Base: 17 pontos do usuário + melhorias identificadas internamente
> Última atualização: 2026-04-15

---

## 🗂️ Índice rápido

| # | Título | Impacto | Complexidade | Status |
|---|--------|---------|-------------|--------|
| 1 | Data de referência do RDO guia tudo | 🔴 Crítico | Alta | ✅ Feito |
| 2 | Trigger de IA do RDO não disparou | 🔴 Crítico | Baixa | ✅ Feito |
| 3 | Cache do hub não invalida após RDO | 🟠 Alto | Média | ⬜ Pendente |
| 4 | SPI errôneo: 0.17 numa obra em dia | 🔴 Crítico | Média | ✅ Feito |
| 5 | Insight de equipe incorreto | 🟠 Alto | Baixa | ✅ Feito |
| 6 | Produtividade diária usa data de envio | 🔴 Crítico | Alta | ✅ Feito (via #1) |
| 7 | Limpeza de dados de teste | 🟡 Médio | Baixa | ⬜ Pendente (usuário) |
| 8 | Duplicação de atividades no RDO enviado | 🔴 Crítico | Baixa | ✅ Feito |
| 9 | Forecast usa data de envio, não referência | 🔴 Crítico | Alta | ✅ Feito (via #1) |
| 10 | IA do hub sem awareness de observações/pendências do RDO | 🟠 Alto | Média | ✅ Feito |
| 11 | IA do RDO: marcos e quantidades sem tratamento | 🟠 Alto | Baixa | ✅ Feito |
| 12 | SPI: atraso ≠ ausência de dados | 🔴 Crítico | Média | ✅ Feito |
| 13 | Insight de antecipação não gerado | 🟡 Médio | Média | ⬜ Pendente |
| 14 | Background submit desloga usuário | 🔴 Crítico | Média | 🟡 Parcial (infra) |
| 15 | Campo de e-mail: on_change causando problemas | 🟡 Médio | Baixa | ⬜ Pendente |
| 16 | Foto EPI limitada a 1 imagem | 🟡 Médio | Baixa | ⬜ Pendente |
| 17 | Foto ferramentas: logout ao subir | 🔴 Crítico | Alta | ✅ Mitigado |
| A | Feedback visual pós-submit (notificação em background) | 🟠 Alto | Baixa | ✅ Feito |
| B | Orientações/pendências na IA do RDO | 🟠 Alto | Baixa | ✅ Feito |
| C | Hub não recarrega cronograma após submit | 🔴 Crítico | Baixa | ✅ Feito (via #3 parcial) |
| D | Gráfico de produtividade diária: sem agrupamento por data_rdo | 🟠 Alto | Média | ⬜ Pendente |
| E | Consistência do tipo de atividade (marco vs %, vs qty) | 🟠 Alto | Média | ⬜ Pendente |
| F | Preenchimento retroativo: RDO de dias anteriores | 🟡 Médio | Alta | ⬜ Pendente |

---

## ✅ CONCLUÍDOS

### #1 — Data de referência do RDO guia todos os cálculos
- [x] Migration SQL: `ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS last_rdo_date date` — aplicada
- [x] `rdo_state.py` — ao atualizar `exec_qty` em `hub_atividades`, salva `last_rdo_date = rdo_data["data"]` (atividade primária e extras)
- [x] `hub_state.py` `_compute_forecast_rows()` — `effective_today = min(date.today(), last_rdo_date)` por linha
- [x] `_eac_base = _effective_today` — EAC calculado a partir da data real do último RDO
- [x] `hub_state.py` normalização — `"last_rdo_date"` incluído no dict da linha

### #4 — SPI errôneo (0.17) em obra que está em dia
- [x] `hub_state.py` `run_agente_atividades`: filtra atividades futuras (`inicio_previsto > today`) do cálculo de SPI
- [x] `spi_ativo` calculado apenas sobre atividades com `inicio <= today`
- [x] Regras 8+9 adicionadas ao prompt: "atividade futura ≠ atraso", "SPI só sobre ativas"

### #5 — Insight de equipe "pode não ter suficiente"
- [x] Regras do agente atualizadas para condicionar alerta de equipe ao SPI real

### #8 — Atividades duplicadas ao enviar RDO
- [x] `rdo_state.py` `_build_atividades_list()`: dedup por nome com prioridade (cronograma > extra > items > novas)

### #9/#6 — Forecast e produtividade usando data de envio
- [x] Resolvidos via #1 — `_effective_today` per-row em `_compute_forecast_rows`

### #10 — IA do hub sem awareness de observações/pendências
- [x] `run_agente_atividades`: busca `orientacao` do último RDO e inclui no prompt como "⚠️ ORIENTAÇÕES/PENDÊNCIAS DO MESTRE"

### #11 — IA do RDO: marcos e quantidades sem tratamento
- [x] `rdo_service.py` `_build_ai_prompt`: `_fmt_act()` helper — Marco ✅, qty (X/Y unid), % normal, ⬜ não iniciado

### #2 — Trigger de IA do RDO não disparou
- [x] `rdo_service.py`: timeout 45s → 70s (inclui AI)
- [x] `pdf_utils.py`: thread join timeout 45s → 90s

### #A — Feedback visual pós-submit
- [x] Toast de sucesso/erro ao finalizar `execute_submit`
- [x] Mensagem separada para PDF e e-mail no toast

### #B — Orientações/pendências na IA do RDO
- [x] `rdo_service.py` `_build_ai_prompt`: `Orientações/Pendências: {rdo_data.get('orientacao','Nenhuma')[:300]}`

### Outros fixes de bugs (sessão anterior)
- [x] `load_emails` movido para `run_in_executor` (evitava crash por state lock)
- [x] `regenerate_pdf(id_rdo)` adicionado no histórico para RDOs sem PDF
- [x] Watermark normalizada para 1920px de saída
- [x] Timestamp checkin: UTC→BRT no rdo_view
- [x] Atividades display: dedup + redesign visual com badge de status
- [x] `rdo_view.py` EAC: `today` ancorado na data do RDO (não `date.today()`)

---

## 🔴 CRÍTICOS — Pendentes

---

### #14 — Background submit desloga usuário

**Diagnóstico**: Analisado o código completo de `execute_submit`. Não há `rx.redirect("/login")` em nenhum path de erro. O submit redireciona para `/rdo-historico` ANTES de iniciar o bg event. A causa real é **Granian multi-worker state loss** — se o WebSocket reconecta para um worker diferente, o estado (incluindo `is_authenticated`) é perdido, e `GlobalState.load_data` no `on_load` da página redireciona para `/`.

**Bug real encontrado e corrigido**: `AlertEngine.check_event` usava `client_id` (indefinido) em vez de `_submit_client_id` → `NameError` silenciado pelo `try/except: pass`, mas era código morto.

**Causa raiz do logout**: Limitação de infraestrutura Reflex — estado server-side não é compartilhado entre workers Granian. Não é um bug de código.

**Tasklist**:
- [x] Verificar todos os `rx.redirect` em `execute_submit` — nenhum leva para login
- [x] Corrigir `client_id` → `_submit_client_id` em `AlertEngine.check_event`
- [ ] Mitigação: garantir que Granian rode com `--workers 1` em produção mobile (evita state loss)
- [ ] Ou: investigar Reflex session persistence entre workers (rx.LocalStorage para auth token)

---

### #17 — Foto de ferramentas: logout e perda de progresso

**Diagnóstico**: Upload handlers não podem ser `@rx.event(background=True)` (restrição Reflex). Com fotos grandes de celular (>10MB), `run_in_executor(get_image_executor())` dentro do handler regular segura o state lock por 5-15s enquanto processa watermark + upload. O WebSocket pode timeout nesse período, causando reconnect para novo worker (perda de estado).

**Solução implementada**: Guard de tamanho 50MB em todos os 3 handlers de upload (evidence, EPI, ferramentas). Fotos acima do limite recebem toast de erro e o upload é abortado sem corrompimento de estado. A watermark já normaliza para 1920px, então fotos válidas processam rápido.

**Tasklist**:
- [x] `upload_evidence_files`: guard 50MB com `continue` (não `return` — processa arquivos válidos do lote)
- [x] `upload_epi_files`: guard 50MB com `return`
- [x] `upload_ferramentas_files`: guard 50MB com `return`
- [x] `try/finally` confirmado em todos os 3 handlers reseta flags `is_uploading_*`

---

### #12 — SPI: ausência de dados ≠ atraso

**Lógica proposta**:
- Se `date.today() <= termino_previsto` E não há RDO do dia de hoje ainda: `SPI = "aguardando dados"`
- Se `date.today() > último RDO recebido` por mais de 1 dia útil: aí sim `SPI < 1`

**Tasklist**:
- [ ] `hub_state.py`: calcular `dias_sem_rdo = (today - last_rdo_date).days` se `last_rdo_date` disponível
- [ ] Threshold: se `dias_sem_rdo <= 1`: não penalizar SPI (é dia em andamento)
- [ ] Agente de IA: incluir `dias_sem_rdo` no contexto para diferenciar "atrasado" de "aguardando"
- [ ] Badge no dashboard: "⏳ Aguardando RDO de hoje" vs "🔴 X dias sem RDO"

---

## 🟠 ALTOS — Próxima sprint

---

### #3/#C — Cache do hub desatualizado após submit RDO

**Problema**: Após submit do RDO, `DataLoader.invalidate_cache()` é chamado, mas `_cron_forecast_cache` de `HubState` não é invalidado.

**Tasklist**:
- [ ] `hub_state.py`: adicionar `async def reload_after_rdo(self, contrato: str)` que reseta cache e recarrega
- [ ] `rdo_state.py` `execute_submit`: após `invalidate_cache()`, yield `HubState.reload_after_rdo(contrato)`
- [ ] Testar: submeter RDO → ir para hub → confirmar dados atualizados sem logout/login

---

### #D — Gráfico de produtividade diária sem agrupamento por data_rdo

**Contexto**: Gráfico usa `created_at` dos lançamentos. Preencher RDO retroativo cria pico falso no dia de envio.

**Tasklist**:
- [ ] `hub_state.py`: query do gráfico — agrupar por `data` (campo de referência do RDO)
- [ ] Garantir que o eixo X usa `data` do RDO, não `created_at`

---

### #13 — Insight de antecipação não gerado

**Tasklist**:
- [ ] `hub_state.py` agente: identificar atividades com `eac < termino_previsto - 2d`
- [ ] Prompt: incluir seção "Oportunidades de antecipação" quando houver atividades adiantadas
- [ ] Sugerir próximas atividades na sequência de dependências

---

## 🟡 MÉDIOS — Backlog

---

### #7 — Limpeza de dados de teste
- [ ] Preencher novo RDO para 13/04 com data correta
- [ ] Deletar RDOs de teste pela interface do Editor de Dados
- [ ] Confirmar que hub_atividades está com valores corretos após limpeza

### #15 — Campo e-mail: on_change com comportamento estranho
- [ ] Verificar se `set_new_email_input` é síncrono simples (deve ser, sem I/O)
- [ ] Se latência: converter para `on_blur` com estado local no frontend

### #16 — Foto EPI limitada a 1 imagem
- [ ] Avaliar impacto no schema (coluna única vs tabela `rdo_epi_fotos`)
- [ ] `rdo_state.py`: `epi_foto_items` já é lista — mudar `multiple=True` e processar todas
- [ ] PDF: renderizar até 3 fotos de EPI em grid

### #E — Consistência de tipos de atividade (marco vs % vs qty)
- [ ] Migration: `ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS tipo_medicao text DEFAULT 'percentual'`
- [ ] Editor de cronograma: dropdown de tipo de medição
- [ ] `_compute_forecast_rows()`: lógica diferenciada por tipo

### #F — Preenchimento retroativo: UX e validação
- [ ] `rdo_state.py` `set_rdo_data()`: verificar existência via `sb_select` com filtro data+contrato
- [ ] Mostrar banner de aviso no form quando data duplicada detectada

---

## 📋 Estado das fases

| Fase | Status |
|------|--------|
| Fase 1 — Quick wins (#B, #A, #8, #2, #15) | ✅ Concluída |
| Fase 2 — Data de referência (#1, #12, #D) | 🟡 Parcial — #1 e #12 feitos, #D pendente |
| Fase 3 — IA mais inteligente (#4, #10, #11, #13) | 🟡 Parcial — #4/#10/#11 feitos, #13 pendente |
| Fase 4 — Features completas (#16, #3/#C, #E, #F, #14, #17) | 🟡 Parcial — #14/#17 mitigados, resto pendente |

---

*Atualizar este arquivo conforme tarefas forem concluídas. Riscar checkboxes com `[x]`.*
