# Plano de Melhorias — Fluxo RDO × Cronograma Integrado

> Criado em 2026-04-14 | Base: 17 pontos do usuário + melhorias identificadas internamente
> Status geral: 🟡 Planejamento — execução por etapas

---

## 🗂️ Índice rápido

| # | Título | Impacto | Complexidade | Status |
|---|--------|---------|-------------|--------|
| 1 | Data de referência do RDO guia tudo | 🔴 Crítico | Alta | ⬜ Pendente |
| 2 | Trigger de IA do RDO não disparou | 🔴 Crítico | Baixa | ⬜ Pendente |
| 3 | Cache do hub não invalida após RDO | 🟠 Alto | Média | ⬜ Pendente |
| 4 | SPI errôneo: 0.17 numa obra em dia | 🔴 Crítico | Média | ⬜ Pendente |
| 5 | Insight de equipe incorreto | 🟠 Alto | Baixa | ⬜ Pendente |
| 6 | Produtividade diária usa data de envio | 🔴 Crítico | Alta | ⬜ Pendente |
| 7 | Limpeza de dados de teste | 🟡 Médio | Baixa | ⬜ Pendente |
| 8 | Duplicação de atividades no RDO enviado | 🔴 Crítico | Baixa | ⬜ Pendente |
| 9 | Forecast usa data de envio, não referência | 🔴 Crítico | Alta | ⬜ Pendente |
| 10 | IA do hub sem awareness de observações/pendências do RDO | 🟠 Alto | Média | ⬜ Pendente |
| 11 | IA do RDO: marcos e quantidades sem tratamento | 🟠 Alto | Baixa | ⬜ Pendente |
| 12 | SPI: atraso ≠ ausência de dados | 🔴 Crítico | Média | ⬜ Pendente |
| 13 | Insight de antecipação não gerado | 🟡 Médio | Média | ⬜ Pendente |
| 14 | Background submit desloga usuário | 🔴 Crítico | Média | ⬜ Pendente |
| 15 | Campo de e-mail: on_change causando problemas | 🟡 Médio | Baixa | ⬜ Pendente |
| 16 | Foto EPI limitada a 1 imagem | 🟡 Médio | Baixa | ⬜ Pendente |
| 17 | Foto ferramentas: logout ao subir | 🔴 Crítico | Alta | ⬜ Pendente |
| A | Feedback visual pós-submit (notificação em background) | 🟠 Alto | Baixa | ⬜ Pendente |
| B | Orientações/pendências na IA do RDO | 🟠 Alto | Baixa | ⬜ Pendente |
| C | Hub não recarrega cronograma após submit | 🔴 Crítico | Baixa | ⬜ Pendente |
| D | Gráfico de produtividade diária: sem agrupamento por data_rdo | 🟠 Alto | Média | ⬜ Pendente |
| E | Consistência do tipo de atividade (marco vs %, vs qty) | 🟠 Alto | Média | ⬜ Pendente |
| F | Preenchimento retroativo: RDO de dias anteriores | 🟡 Médio | Alta | ⬜ Pendente |

---

## 🔴 CRÍTICOS — Resolvem antes de qualquer nova feature

---

### #1 — Data de referência do RDO deve guiar todos os cálculos

**Problema raiz**: O cronograma usa `date.today()` para calcular `dias_decorridos`, produtividade real, SPI, forecast e EAC. Se o mestre preenche o RDO do dia 13 às 10h do dia 14, todos os cálculos entendem que a execução aconteceu "hoje" (14/04), gerando dados errados.

**Causa técnica**:
- `hub_state.py` linha 399: `today = date.today()` — hardcoded para hoje
- `hub_state.py` linha 1355: mesma coisa na geração de insights
- `rdo_service.py` save: salva `data` (data de referência) corretamente, mas `hub_state.py` ignora ao recalcular
- `exec_qty` em `hub_atividades` é acumulado sem data — impossível saber "quanto foi executado até o dia X"

**Impacto**: Afeta pontos #1, #6, #9 — e indiretamente #4, #5, #12.

**Solução proposta**:
1. Criar coluna `last_rdo_date` em `hub_atividades` (atualizada junto com `exec_qty`)
2. Em `_compute_forecast_rows()`, quando `last_rdo_date` está preenchida, usar `min(date.today(), last_rdo_date)` como "hoje efetivo" para `dias_decorridos`
3. Nunca avançar `dias_decorridos` além da data do último RDO recebido para aquela atividade
4. No `finalize_rdo`, propagar a `data` do RDO para `hub_atividades` ao atualizar `exec_qty`

**Tasklist**:
- [ ] Adicionar migration SQL: `ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS last_rdo_date date`
- [ ] `rdo_service.py` — ao atualizar `exec_qty` em `hub_atividades`, salvar `last_rdo_date = rdo_data["data"]`
- [ ] `hub_state.py` `_compute_forecast_rows()` — substituir `today` por `effective_today = min(date.today(), last_rdo_date)` quando disponível
- [ ] `hub_state.py` insights/agente — mesma substituição
- [ ] Testar: preencher RDO retroativo e confirmar que SPI/forecast não avança

---

### #4 — SPI errôneo (0.17) em obra que está em dia

**Problema raiz**: SPI baixo quando obra está ok = cálculo de `prod_plan` inflado.

**Causa técnica provável** (a confirmar via MCP):
- `dias_plan` na atividade pode estar incorreto (muito baixo = produtividade planejada muito alta)
- `exec_qty` pode estar zerado enquanto `conclusao_pct > 0` (inconsistência de dados)
- Atividades do tipo "marco" (exec_qty=0, total_qty=0) sendo incluídas na média de SPI com peso incorreto
- Atividade de nível "macro" sendo usada no cálculo quando deveria usar somente "micro"

**Solução proposta**:
1. Excluir atividades de tipo "marco" (ou onde `total_qty == 0`) do cálculo de SPI por produtividade
2. Excluir atividades sem `exec_qty > 0` do cálculo de `prod_real` (threshold mínimo de dados)
3. SPI "sem dados" ≠ SPI "ruim" — diferenciar os estados
4. Adicionar logs/debug mode para rastrear quais atividades arrastaram o SPI

**Tasklist**:
- [ ] Checar via MCP os dados reais de `hub_atividades` do contrato que deu SPI 0.17
- [ ] Identificar se o problema é de dados ou de lógica
- [ ] `hub_state.py` `_compute_forecast_rows()`: filtrar atividades sem qty antes do cálculo de SPI
- [ ] Diferenciar `spi_sem_dados` de `spi_baixo` no output do agente de IA
- [ ] Testar com o contrato real

---

### #8 — Atividades duplicadas ao enviar RDO

**Problema raiz**: O payload `atividades` no `_build_payload()` (rdo_state.py linha 1921-1934) soma:
- Entrada principal (`rdo_atividade_id + rdo_atividade_nome`)
- `atividades_items` (lista separada)
- `rdo_novas_atividades`
- `rdo_extra_atividades`

Se o mestre usa o seletor de atividade do cronograma E adiciona a mesma via `atividades_items`, ela aparece duas vezes. O dedup do `rdo_view.py` foi feito para a *exibição*, mas o problema está no *salvamento*.

**Solução proposta**:
1. Dedup por nome no `_build_payload()` antes de montar a lista final
2. Ou preferir a entrada do cronograma (`rdo_atividade_id`) sobre `atividades_items` quando os nomes batem

**Tasklist**:
- [ ] `rdo_state.py` `_build_payload()`: dedup por `atividade.lower().strip()` antes de retornar lista
- [ ] Manter a entrada de cronograma como "fonte de verdade" quando há conflito
- [ ] Testar: selecionar atividade do cronograma + adicionar item extra com mesmo nome

---

### #12 — SPI: ausência de dados ≠ atraso

**Problema raiz**: Hoje à noite, a obra ainda está ocorrendo. O atraso só existe quando o dia passa E não chegou RDO. Enquanto não chegou o RDO do dia, aquele dia não tem atraso prático — tem apenas ausência de informação.

**Lógica proposta**:
- Se `date.today() <= termino_previsto` E não há RDO do dia de hoje ainda: `SPI = "aguardando dados"`
- Se `date.today() > último RDO recebido` por mais de 1 dia útil: aí sim `SPI < 1`
- O agente de IA deve comunicar essa diferença: "Sem RDO de hoje ainda — aguardando lançamento"

**Tasklist**:
- [ ] `hub_state.py`: calcular `dias_sem_rdo = (today - last_rdo_date).days` se `last_rdo_date` disponível
- [ ] Threshold: se `dias_sem_rdo <= 1`: não penalizar SPI (é dia em andamento)
- [ ] Agente de IA: incluir `dias_sem_rdo` no contexto para diferenciar "atrasado" de "aguardando"
- [ ] Badge no dashboard: "⏳ Aguardando RDO de hoje" vs "🔴 X dias sem RDO"

---

### #14 — Background submit desloga usuário

**Problema**: `execute_submit` é `@rx.event(background=True)`. Durante execução, pode acontecer:
- `get_state(GlobalState)` retorna sessão expirada ou diferente
- Ao finalizar, `yield rx.redirect(...)` pode invalidar a sessão do cliente
- Token de autenticação expira durante os 30-90s de processamento

**Investigar**:
- O log provavelmente mostra `session changed` ou `token expired`
- Se o redirect final está indo para `/login` por erro, não por intenção

**Tasklist**:
- [ ] Ler logs do submit que causou o logout
- [ ] Verificar se `execute_submit` faz qualquer `yield rx.redirect("/login")` em path de erro
- [ ] Se sim: substituir por toast de erro sem redirecionar
- [ ] Confirmar que o token da sessão não expira durante o processing (heartbeat)

---

### #17 — Foto de ferramentas: logout e perda de progresso

**Problema**: Upload de foto no mobile (possivelmente foto da galeria grande) → sistema redireciona para login → rascunho perdido.

**Causa provável**:
1. Foto grande (>5MB de celular) → timeout no upload → exception não tratada → estado corrompido → redirect para login
2. Ou: event loop bloqueado pelo upload → WebSocket timeout → sessão considerada morta

**Solução**:
1. Garantir que `is_uploading_ferramentas = False` em `finally` (já feito, mas verificar)
2. Adicionar limite de tamanho de arquivo explícito antes do upload com toast de aviso
3. Compressão de imagem no cliente antes do upload (via JS hook) ou no servidor
4. Garantir que NUNCA um erro de upload resulta em redirect para login

**Tasklist**:
- [ ] `rdo_state.py` `upload_ferramentas_files`: adicionar verificação de tamanho > 15MB com toast de aviso
- [ ] Confirmar que `try/finally` reseta `is_uploading_ferramentas` (foi feito na sessão anterior)
- [ ] Verificar se o auto-save do draft está sendo chamado antes de qualquer upload
- [ ] Adicionar `draft_saved_at` atualizado ANTES de iniciar upload, garantindo checkpoint

---

## 🟠 ALTOS — Próxima sprint

---

### #2 — Trigger de IA do RDO não disparou

**Análise**: `execute_submit` chama `analyze_now` via `get_ai_executor()` com `asyncio.wait_for(timeout=30s)`. Se a IA demorou >30s (timeout) ou se o `ai_executor` estava ocupado, a análise é pulada silenciosamente.

**Evidência**: Timeout de 30s é muito curto para Claude em horário de pico.

**Solução**:
1. Aumentar timeout para 60s
2. Se timeout/erro: salvar `ai_summary = "pending"` e disparar retry em background separado
3. Adicionar log explícito quando análise é pulada por timeout

**Tasklist**:
- [ ] `rdo_service.py` `analyze_now`: timeout 30s → 60s
- [ ] `rdo_state.py` `execute_submit`: se `ai_result` vazio, salvar `ai_summary="pending"` + agendar retry
- [ ] Criar `retry_ai_analysis(id_rdo)` bg event chamado 2min depois se `ai_summary == "pending"`

---

### #3/#C — Cache do hub desatualizado após submit RDO

**Problema**: Após submit do RDO, `DataLoader.invalidate_cache()` é chamado (linha 1832), mas o `_cron_forecast_cache` de `HubState` não é invalidado. O usuário vê dados antigos no hub sem perceber.

**Solução**:
1. Após `finalize_rdo`, yield `HubState.reload_cronograma_after_rdo(contrato)` — um bg event simples que limpa o cache e recarrega
2. Ou: ao entrar na página `/obras`, verificar se `last_rdo_date` mudou desde o último carregamento

**Tasklist**:
- [ ] `hub_state.py`: adicionar `async def reload_after_rdo(self, contrato: str)` que reseta `_cron_forecast_cache` e chama `load_cronograma`
- [ ] `rdo_state.py` `execute_submit`: após `invalidate_cache()`, yield `HubState.reload_after_rdo(contrato)`
- [ ] Testar: submeter RDO → ir para hub → confirmar dados atualizados sem logout/login

---

### #5 — Insight de equipe "pode não ter suficiente"

**Causa**: O agente usa o tamanho atual da equipe (`equipe_alocada`) e compara com uma estimativa baseada em produtividade. Se a lógica não considera o SPI real (já vimos que é bugado), ela pode gerar alerta incorreto.

**Solução**: Vincular o insight de equipe ao SPI correto. Se `SPI >= 0.95`, não emitir alerta de equipe insuficiente a menos que o forecast EAC mostre atraso > 5 dias úteis.

**Tasklist**:
- [ ] `hub_state.py` agente: condicionar alerta de equipe a `SPI < 0.9 AND eac > termino_previsto + 5d`
- [ ] Revisar o prompt do agente para incluir essa condicional explicitamente

---

### #10 — IA do hub sem awareness de observações/pendências do RDO

**Problema**: O agente (`run_agente_atividades`) busca o último RDO para contexto de clima/equipe, mas não lê `observacoes` e `orientacao` (pendências). Se o mestre avisou "falta madeira para o andaime", o agente deveria mencionar isso.

**Solução**: Incluir `observacoes` e `orientacao` do RDO mais recente no prompt do agente.

**Tasklist**:
- [ ] `hub_state.py` `_fetch_last_rdo()`: adicionar campos `observacoes` e `orientacao` no select
- [ ] Prompt do agente: adicionar seção "Pendências/Observações do último RDO: ..."
- [ ] Se `orientacao` não vazia: destacar como item de atenção no insight gerado

---

### #11 — IA do RDO: marcos e quantidades sem tratamento adequado

**Problema**: O prompt atual monta as atividades como `nome (X%) [status]`. Para atividades de tipo "marco" (ex: "Entrega de material"), o `%` é sempre 0 pois é binário. Para atividades com qty (ex: "Concretagem: 12/50 m³"), a % não representa o que foi feito hoje.

**Solução**: No `_build_ai_prompt`, diferenciar os tipos:
- Tipo `%`: `Pintura (45%)`
- Tipo `qty`: `Concretagem — 12 m³ de 50 m³ previstos`
- Tipo `marco`: `Entrega de material ✅ Concluído` ou `⬜ Pendente`

**Tasklist**:
- [ ] `rdo_service.py` `_build_ai_prompt`: detectar se `progresso_percentual` == "0" e `status` == "Concluído" → tratar como marco
- [ ] Adicionar campo `exec_qty_hoje` e `unidade` ao payload de atividades do RDO quando vem do cronograma
- [ ] Prompt: instruir a IA a não dizer "0%" para marcos — usar "concluído/pendente"
- [ ] Adicionar `orientacao` do RDO ao prompt (ponto #B abaixo)

---

### #A — Feedback visual pós-submit

**Problema**: O submit é background. O usuário não sabe que o RDO foi enviado, o PDF foi gerado, o email foi mandado. Aparece nada — só um "finalizado" no status se ele navegar para o histórico.

**Solução**:
1. Ao finalizar `execute_submit`: `yield rx.toast.success("✅ RDO enviado! PDF sendo gerado e e-mails enviados.", duration=8000)`
2. Quando PDF terminar (em thread separada): `yield rx.toast.info("📄 PDF gerado com sucesso!")` via bg event separado
3. Quando email terminar: toast de confirmação de envio

**Tasklist**:
- [ ] `rdo_state.py` `execute_submit`: adicionar toast de sucesso após `finalize_rdo`
- [ ] PDF thread: callback que dispara `yield RDOState.notify_pdf_done(id_rdo)` bg event
- [ ] Email thread: callback que dispara `yield RDOState.notify_email_done(recipients_count)` bg event

---

### #B — Orientações/pendências na análise de IA do RDO

**Problema**: `orientacao` (campo "Orientações/Pendências") está no PDF mas não no prompt de IA (linha 1646 só inclui `observacoes`).

**Solução**: Uma linha de código.

**Tasklist**:
- [ ] `rdo_service.py` `_build_ai_prompt`: adicionar `Orientações/Pendências: {rdo_data.get('orientacao','Nenhuma')[:300]}` ao prompt
- [ ] Testar com RDO que tem orientação preenchida

---

## 🟡 MÉDIOS — Backlog

---

### #6/#9 — Produtividade e forecast usam data de envio

Dependem diretamente da correção do #1 (data de referência). Ao implementar `last_rdo_date` em `hub_atividades`, esses dois pontos se resolvem automaticamente.

---

### #13 — Insight de antecipação não gerado

**Problema**: O mestre executou uma atividade prevista para hoje, ontem. O sistema deveria detectar que a atividade está adiantada e sugerir o que adiantar em seguida.

**Solução**: No agente, quando `tendencia == "acima"` e `eac < termino_previsto`, gerar insight: "Atividade X adiantada X dias. Considere antecipar Y e Z do cronograma."

**Tasklist**:
- [ ] `hub_state.py` agente: identificar atividades com `eac < termino_previsto - 2d`
- [ ] Prompt: incluir seção "Oportunidades de antecipação" quando houver atividades adiantadas
- [ ] Sugerir próximas atividades na sequência de dependências

---

### #15 — Campo e-mail: on_change com comportamento estranho

**Análise**: `rdo_historico.py` linha 469 usa `on_change=RDOHistoricoState.set_new_email_input`. Isso é correto e normal. O problema mencionado pode ser que cada keystroke no campo dispara um event handler no servidor — latência perceptível em conexões lentas.

**Solução**: Manter `on_change` para binding local, mas throttle ou usar `on_blur` para validação.

**Tasklist**:
- [ ] Verificar se `set_new_email_input` é síncrono simples (deve ser, sem I/O)
- [ ] Se latência: converter para `on_blur` com estado local no frontend

---

### #16 — Foto EPI limitada a 1 imagem

**Problema**: `multiple=False` em ambos os campos de upload (EPI e ferramentas). O BD salva apenas `epi_foto_items[0]`.

**Análise**: Mudar para múltiplas fotos requer:
- `multiple=True` no input
- Loop de upload para cada foto
- Mudança de schema: `epi_foto_url` vira lista ou tabela separada
- PDF precisa renderizar múltiplas fotos

**Decisão de escopo**: Liberar múltiplas fotos para EPI é feature completa. Inicialmente: liberar 3 fotos máximo com galeria no RDO view.

**Tasklist**:
- [ ] Avaliar impacto no schema (coluna única vs tabela `rdo_epi_fotos`)
- [ ] Se tabela: migration + service update
- [ ] `rdo_state.py`: `epi_foto_items` já é lista — mudar `multiple=True` e processar todas
- [ ] PDF: renderizar até 3 fotos de EPI em grid
- [ ] RDO view: galeria de fotos EPI

---

### #7 — Limpeza de dados de teste

**Solução**: O usuário vai criar um novo RDO correto para o dia 13. Depois deletar os dados de teste via `/editar-dados` ou diretamente via MCP/SQL.

**Tasklist**:
- [ ] Preencher novo RDO para 13/04 com data correta
- [ ] Deletar RDOs de teste pela interface do Editor de Dados
- [ ] Confirmar que hub_atividades está com valores corretos após limpeza

---

## 🔍 MELHORIAS IDENTIFICADAS INTERNAMENTE (não listadas pelo usuário)

---

### #D — Gráfico de produtividade diária sem agrupamento por data_rdo

**Contexto**: O gráfico mostra produção por dia usando `created_at` dos lançamentos de RDO. Preencher um RDO retroativo cria um pico falso no dia de envio.

**Solução**: Agrupar o gráfico pela coluna `data` (data de referência) do `rdo_master`, não por `created_at`.

**Tasklist**:
- [ ] `hub_state.py`: query do gráfico de produtividade — agrupar por `data` (campo de referência)
- [ ] Garantir que o eixo X usa `data` do RDO, não `created_at`

---

### #E — Consistência de tipos de atividade (marco vs % vs qty)

**Contexto**: O sistema atual trata tudo como `conclusao_pct` (0-100%). Mas existem 3 tipos distintos:
- **Marco**: binário (feito/não feito) — ex: "Emissão de ART"
- **Percentual**: ex: "Pintura — 45%"
- **Quantidade**: ex: "Concretagem — 12/50 m³"

O SPI, EAC e insights tratam todos como quantidade, gerando inconsistências.

**Solução**: Adicionar coluna `tipo_medicao` em `hub_atividades` (`marco` | `percentual` | `quantidade`). Adaptar todos os cálculos.

**Tasklist**:
- [ ] Migration: `ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS tipo_medicao text DEFAULT 'percentual'`
- [ ] Editor de cronograma: dropdown de tipo de medição
- [ ] `_compute_forecast_rows()`: lógica diferenciada por tipo
- [ ] IA e relatórios: formatação diferenciada por tipo

---

### #F — Preenchimento retroativo: UX e validação

**Contexto**: O campo `rdo_data` pode ser alterado para uma data passada, mas o sistema não avisa se já existe um RDO para aquela data/contrato. O mestre pode criar duplicatas sem querer.

**Solução**:
1. Ao mudar `rdo_data`, verificar se já existe RDO finalizado para aquela data + contrato
2. Se sim: mostrar aviso "Já existe um RDO finalizado para XX/XX/XXXX. Tem certeza?"
3. Oferecer opção de "Ver RDO existente" ou "Criar novo (complementar)"

**Tasklist**:
- [ ] `rdo_state.py` `set_rdo_data()`: verificar existência via `sb_select` com filtro data+contrato
- [ ] Mostrar banner de aviso no form quando data duplicada detectada
- [ ] Adicionar flag `is_complementar: bool` no RDO para distinguir dos principais

---

## 📋 Ordem de execução recomendada

### 🚀 Fase 1 — Fundação (resolve a maioria dos bugs com 20% do esforço)
1. **#B** — Orientações no prompt de IA do RDO *(5 min, 1 linha)*
2. **#A** — Feedback visual pós-submit *(30 min)*
3. **#8** — Dedup de atividades no payload *(20 min)*
4. **#2** — Timeout de IA: 30s → 60s *(10 min)*
5. **#15** — Campo e-mail: verificar e ajustar *(15 min)*

### 🔧 Fase 2 — Data de referência (resolve #1, #6, #9, #12 juntos)
6. **#1** — Migration `last_rdo_date` + propagação no finalize_rdo
7. **#12** — Lógica "sem dados ≠ atraso" no SPI
8. **#D** — Gráfico produtividade por data_rdo

### 🧠 Fase 3 — IA mais inteligente
9. **#4** — Debug e fix do SPI 0.17
10. **#10** — Agente do hub com observações/pendências do RDO
11. **#11** — Tipos de atividade no prompt (marco vs qty vs %)
12. **#13** — Insights de antecipação

### 🏗️ Fase 4 — Features completas
13. **#16** — Múltiplas fotos EPI/ferramentas
14. **#3/#C** — Invalidação de cache após submit
15. **#E** — `tipo_medicao` no cronograma
16. **#F** — Detecção de RDO duplicado retroativo
17. **#14** — Investigar e resolver logout no background submit
18. **#17** — Upload de foto: crash mobile

---

## 🗃️ Estado da sessão

| Fase | Status |
|------|--------|
| Fase 1 | ⬜ Não iniciada |
| Fase 2 | ⬜ Não iniciada |
| Fase 3 | ⬜ Não iniciada |
| Fase 4 | ⬜ Não iniciada |

---

*Atualizar este arquivo conforme tarefas forem concluídas. Riscar checkboxes com `[x]`.*
