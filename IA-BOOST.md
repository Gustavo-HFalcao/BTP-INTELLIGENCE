# IA-BOOST — Roadmap de Inteligência Artificial

> Documento vivo. Atualizado em 2026-04-08.
> Prioridade: **P0** crítico · **P1** alto impacto · **P2** diferencial · **P3** backlog qualificado

---

## PARTE 1 — UPGRADES NAS FEATURES EXISTENTES

Melhorias no que já está em produção. Cada uma pode ser feita de forma isolada.

---

### U1 · Chat IA — Suggestion Chips mais inteligentes `P1`

**Estado atual:** 4 chips fixos e genéricos — "Resumir dados", "Detectar riscos", "Status Financeiro", "Gerar insights". Não mudam com o contrato selecionado nem com o contexto da página.

**Upgrade:** Tornar chips **contextuais e dinâmicos** — gerados com base no contrato ativo e no estado real dos dados. Se há um contrato atrasado, chip "Analisar atraso em {contrato}". Se há sobre-custo, chip "Por que o custo do {contrato} está acima?". Se tem RDO recente, chip "O que o último RDO diz sobre progresso?".

**Impacto:** Zero fricção pra iniciar uma conversa útil. O chat deixa de parecer vazio para novos usuários.

**Arquivo:** `bomtempo/components/chat/chat_suggestions.py` + computed var em `GlobalState`

---

### U2 · Chat IA — Tool label granular no typing indicator `P1`

**Estado atual:** `chat_tool_label` só diferencia 2 estados: `"gerando gráfico..."` ou `"consultando banco..."`. O usuário não sabe se a IA está buscando schema, executando SQL ou fazendo a busca de documentos.

**Upgrade:** Label por tool chamada — `"📋 buscando schema..."`, `"🔍 executando query..."`, `"📄 lendo documentos..."`, `"📊 montando gráfico..."`. Ao fazer múltiplas tool calls sequenciais, mostrar qual está em execução agora.

**Impacto:** Transparência imediata. O usuário entende que a IA está trabalhando, não travada. Reduz abandono de sessão.

**Arquivo:** `bomtempo/state/global_state.py:449-451`

---

### U3 · Chat IA — Memória de sessão entre conversas `P1`

**Estado atual:** Cada sessão começa do zero — o bot não "lembra" do que foi discutido ontem. `chat_sessions` e `chat_messages` estão no banco mas nunca são lidos ao iniciar nova sessão.

**Upgrade:** Ao abrir o chat, buscar as últimas 3 mensagens de conversa (assistant + user) da sessão mais recente do mesmo usuário e injetar como contexto de "última conversa". Prefixo no system prompt: `"Na sua última sessão você perguntou sobre X e eu respondi Y. Continue de onde paramos."`

**Impacto:** O gestor volta no dia seguinte e o bot tem contexto. Feature que cria hábito de uso.

**Arquivo:** `bomtempo/state/global_state.py:load_chat_history()` + `stream_chat_bg`

---

### U4 · Chat IA — search_documents com busca cross-contrato `P2`

**Estado atual:** A tool `search_documents` busca documentos do contrato selecionado na UI. Se nenhum contrato está selecionado, a busca retorna vazio silenciosamente.

**Upgrade:** Quando `contrato=""` (busca em todos), a tool deve iterar os contratos disponíveis do tenant e retornar os N documentos mais relevantes com indicação do contrato de origem. Adicionar um fallback no sistema: se o usuário perguntar sobre cláusula sem contrato selecionado, o bot pergunta "Para qual contrato?" antes de chamar a tool.

**Impacto:** A busca documental funciona 100% do tempo, não só quando o usuário já navegou até um contrato.

**Arquivo:** `bomtempo/core/ai_tools.py:execute_tool("search_documents")`

---

### U5 · Agente de Atividades — Badge de confiança nos insights `P1`

**Estado atual:** Todos os insights aparecem com o mesmo visual independente de quantos dados embasaram o cálculo. Um insight baseado em 1 amostra de RDO parece igual a um com 10 amostras.

**Upgrade:** Adicionar ao JSON de cada insight um campo `"samples": N` (número de RDOs usados no cálculo). No card renderizar um badge discreto: `●●●` (3 amostras = médio), `●●●●●` (5+ = alto) com tooltip "Baseado em N RDOs". Para insights estimados (sem dados de produção), badge vermelho `"estimado"`.

**Impacto direto:** O gestor sabe em que pode confiar sem hesitar. Elimina a dúvida "isso é real ou inventado?".

**Arquivo:** `bomtempo/state/hub_state.py` (adicionar `samples` ao JSON) + `bomtempo/pages/hub_operacoes.py:_agente_insight_card()`

---

### U6 · Agente de Atividades — Atualização automática pós-RDO `P1`

**Estado atual:** O agente é acionado por `rdo_id` passado explicitamente ou pelo botão "forçar atualização". Na prática, após o Mestre submeter um RDO, o agente não roda automaticamente — requer ação manual do gestor.

**Upgrade:** No evento `submit_rdo` em `rdo_state.py`, após salvar com sucesso, disparar `HubState.run_agente_atividades(contrato=contrato, rdo_id=id_rdo)` em background. O gestor abre o Hub e os insights já estão atualizados — sem precisar pedir.

**Impacto:** O agente deixa de ser manual e passa a ser reativo. Cada RDO submetido enriquece automaticamente o painel.

**Arquivo:** `bomtempo/state/rdo_state.py:execute_submit()` (fim do fluxo de sucesso)

---

### U7 · Agente de Atividades — Insight de clima x atividade `P2`

**Estado atual:** O campo `weather` existe como tipo de insight e o agente menciona clima quando o RDO registrou interrupção. Mas não há cruzamento proativo com a previsão do tempo dos próximos dias vs atividades sensíveis ao clima no cronograma.

**Upgrade:** Injetar no prompt do agente os dados de previsão meteorológica dos próximos 3 dias (já temos `weather_api.py` e os dados carregados em `obras`). O agente cruza: "Concretagem de pilares está prevista para quarta-feira. Previsão: 18mm de chuva. Risco de interrupção."

**Impacto:** Antecipação real — o gestor reprograma antes que o problema aconteça.

**Arquivo:** `bomtempo/state/hub_state.py:run_agente_atividades()` + injetar `weather_data` no contexto

---

### U8 · FAB Briefing Executivo — Título dinâmico no dialog `P2`

**Estado atual:** O dialog de análise abre com título genérico sempre. O botão já muda de label ("Briefing Executivo" na Visão Geral vs "Análise Inteligente" nas outras páginas), mas o dialog interno não reflete isso.

**Upgrade:** Passar `page_name` como título do dialog. Adicionar subtítulo dinâmico: "Gerado em [hora BRT] · Dados de [data do último carregamento]". Isso ancora o briefing no tempo — o gestor sabe se está olhando dados de hoje ou de ontem.

**Arquivo:** `bomtempo/layouts/default.py:_kpi_detail_dialog()` + `GlobalState._pending_page_name`

---

### U9 · KPI Detail Popup — Análise IA inline `P1`

**Estado atual:** Os popups de KPI (total contratado, total medido, saldo, contratos ativos) mostram tabelas de dados mas sem nenhuma interpretação. Abrir o popup de "Saldo a Medir" mostra os contratos mas não explica o que está em risco.

**Upgrade:** Adicionar ao popup um parágrafo de 2-3 linhas gerado automaticamente ao abrir. Exemplo para saldo: "3 contratos concentram 78% do saldo. BOM-029 com maior exposição — vencimento em 18 dias." Usar `ai_client.query()` (não streaming) com os dados da tabela como contexto. Cache por 1h em state var.

**Impacto:** O popup passa de tabela passiva para inteligência ativa. Cada clique em KPI entrega um micro-briefing.

**Arquivo:** `bomtempo/state/global_state.py` (novo event handler `generate_kpi_popup_insight`) + `bomtempo/layouts/default.py:_kpi_detail_dialog()`

---

### U10 · Action AI — Feedback de HITL mais rico `P1`

**Estado atual:** O card de confirmação HITL mostra `hitl_summary` (1 frase) + `hitl_preview_lines` (lista de texto puro). A senha aparecia em texto puro (corrigido), mas o layout ainda parece uma lista genérica.

**Upgrade:** Diferenciar visualmente cada tipo de HITL:
- `change_password` → ícone de cadeado, campo de senha mascarado com indicador de força
- `create_user` → avatar placeholder com role badge  
- `create_alert` → ícone de sino + resumo da condição em linguagem natural
- `send_document` → preview do documento com destinatário destacado

**Impacto:** O usuário confirma com confiança, não com ansiedade. Reduz cliques em "Cancelar" por falta de clareza.

**Arquivo:** `bomtempo/components/action_ai_popup.py:_hitl_card()`

---

### U11 · Action AI — Histórico de ações executadas `P2`

**Estado atual:** Após confirmar uma ação HITL (criar usuário, alterar senha, etc.), a resposta é exibida na tela mas não há registro acessível ao usuário das ações tomadas via Action AI. Os logs de auditoria existem, mas o usuário não os vê no contexto do Action AI.

**Upgrade:** Adicionar aba "Histórico" no popup do Action AI com as últimas 5 ações executadas (lidas de `system_logs` com `action_category=DATA_EDIT` + `username=current_user`). Exibir: data, ação, status (✅ sucesso / ❌ erro). Zero cliques extras — contexto imediato de o que foi feito.

**Arquivo:** `bomtempo/components/action_ai_popup.py` + `bomtempo/state/action_ai_state.py`

---

### U12 · Análise de Clima — Mostrar no Hub de Operações `P2`

**Estado atual:** `AnalysisService.analyze_weather_impact()` existe e está funcional. É chamado em `global_state.py:analyze_weather_impact()`. Mas a análise de clima e o painel de clima do Hub de Operações estão desconectados — a análise textual não aparece junto ao widget de clima.

**Upgrade:** Integrar o resultado da análise climática como texto expandível abaixo do widget Windy no Hub. Acionado automaticamente quando a página carrega (via `on_mount`). Se o clima for favorável, mostrar mensagem curta. Se crítico, destaque vermelho com a ação recomendada.

**Arquivo:** `bomtempo/pages/hub_operacoes.py` + `bomtempo/state/global_state.py:analyze_weather_impact()`

---

### U13 · Chat IA — Variação de tom por role `P2`

**Estado atual:** O `system_prompt` tem branch para `is_mobile` (Gestão-Mobile), mas todos os outros roles recebem o mesmo prompt de "CFO/CPO sênior". Um Mestre de Obras e um CEO lendo a mesma resposta técnica.

**Upgrade:** Adicionar branch por role no `get_system_prompt()`:
- **Administrador/CFO**: tom atual — executivo, orientado a margem e risco
- **Engenheiro**: foco em prazo, atividades e campo — menos financeiro, mais operacional
- **Gestão-Mobile**: respostas ultracompactas, sem tabelas, bullets de 1 linha

**Impacto:** A IA fala a língua de quem pergunta. Engenheiro não precisa filtrar linguagem financeira.

**Arquivo:** `bomtempo/core/ai_context.py:get_system_prompt()`

---

## PARTE 2 — NOVAS FEATURES STATE-OF-THE-ART

Features que ainda não existem. Ordenadas por impacto percebido pelo cliente.

---

### N1 · Confidence Score — Transparência nos insights do Agente `P1`

**O que é:** Cada insight do Agente de Atividades exibe um badge de confiança calculado automaticamente com base em quantas amostras embasaram o número. Alto (5+ RDOs), Médio (2-4), Baixo (1 amostra ou estimado). Ao clicar no badge, abre painel mostrando as linhas exatas de `rdo_atividades` que geraram o cálculo.

**Por que o cliente percebe valor:** Elimina a principal objeção ao uso de IA em gestão: "como sei se esse número é real?". Com rastreabilidade de um clique, o gestor não precisa verificar manualmente.

**Implementação:**
1. Adicionar campo `"samples": N` e `"source_rows": [...]` ao JSON do agente
2. Renderizar badge de confiança em `_agente_insight_card()`
3. Sheet/dialog de detalhe mostrando cada linha de `rdo_atividades` que contribuiu

---

### N2 · EVM — Earned Value Management integrado `P1`

**O que é:** Calcular automaticamente os índices padrão de gerenciamento de projetos:
- **CPI** (Cost Performance Index): valor realizado / custo real — se < 1, cada R$ está gerando menos de R$ 1 de avanço
- **SPI** (Schedule Performance Index): já calculado em `hub_state.py` — expor no UI
- **EAC** (Estimate at Completion): custo total estimado se a tendência atual continuar = orçamento / CPI
- **VAC** (Variance at Completion): orçamento - EAC

**Por que o cliente percebe valor:** É linguagem de PMO e construtora enterprise. Ao ver CPI e SPI no dashboard, o gestor sabe que a plataforma fala a mesma língua que o mercado. Diferencial imediato vs concorrentes.

**Implementação:**
- Dados disponíveis: `fin_custos` (custos reais) + `hub_atividades` (valor planejado via `peso_pct`)
- Novo computed var `evm_metrics` em `GlobalState` por contrato
- Card no Hub com semáforo: CPI > 1.0 ✅ | 0.9-1.0 🟡 | < 0.9 🔴

---

### N3 · Briefing Matinal Automatizado — Push proativo `P1`

**O que é:** Todo dia às 7h um background job gera para cada contrato ativo um briefing de 5 itens: status de ontem vs meta, clima do dia (já temos API), próximas atividades críticas, alerta de equipe se gap detectado, ação recomendada. Enviado por email antes do expediente.

**Por que o cliente percebe valor:** A plataforma passa de reativa (o gestor abre e analisa) para proativa (a plataforma avisa antes que ele pergunte). Aumenta drasticamente o valor percebido — "o sistema me avisou antes de eu chegar na obra".

**Implementação:**
- `CronCreate` já disponível via skills do Claude Code
- Novo módulo `bomtempo/core/morning_briefing.py` — reutiliza `AIContext.get_dashboard_context()` + `AnalysisService`
- Trigger: `alert_service.py` pattern já estabelecido
- Email: `EmailService` já funcional

---

### N4 · Detecção de Anomalias — Alertas proativos via série temporal `P1`

**O que é:** Monitor automático que analisa `hub_atividade_historico` diariamente e detecta: queda de produtividade > 25% em relação à média dos 7 dias anteriores em atividade crítica, aceleração inesperada (pode indicar erro de registro), 3+ dias consecutivos sem registro numa atividade em andamento.

**Por que o cliente percebe valor:** Detecção antes do problema virar crise. O gestor é alertado quando a queda começa, não quando o prazo já estourou. Nenhum dashboard de obra do mercado faz isso automaticamente.

**Implementação:**
- SQL query com window functions: `LAG()` e `AVG() OVER (PARTITION BY atividade_id ORDER BY created_at)`
- Integrar ao `alert_service.py` como novo tipo `"anomalia_producao"`
- Threshold configurável por contrato (default: 25%)

---

### N5 · Benchmarking Interno entre Contratos `P2`

**O que é:** Com histórico de `rdo_atividades` em múltiplos contratos, calcular a taxa média da empresa por tipo de serviço. Exibir no insight do agente: "Instalação de módulos: média empresa 18 módulos/pessoa/dia — Contrato 306: **16 módulos** (-11% da média)."

**Por que o cliente percebe valor:** Contexto que o gestor não tem de nenhuma outra forma. Não é "você está atrasado", é "você está 11% abaixo da média dos seus próprios projetos — aqui está o que as outras equipes fazem diferente".

**Implementação:**
- View materializada no Supabase: `atividade_benchmark` agregando taxa média por nome de atividade
- Injetar no prompt do agente: `"## BENCHMARK INTERNO\n- {atividade}: média empresa {X}/pessoa/dia"`
- Cache de 24h (dados mudam lentamente)

---

### N6 · Painel de Produtividade por Atividade — Visualização temporal `P2`

**O que é:** Página ou aba no Hub mostrando gráfico de linha: eixo X = data, eixo Y = quantidade/pessoa/dia, uma série por atividade. Com linha tracejada de meta planejada (`prod_planejada_dia` já existe em `hub_atividades`). Hover mostra: data, quantidade, efetivo, clima daquele dia.

**Por que o cliente percebe valor:** O visual que o agente descreve em texto, tornado gráfico. Identifica padrões que o texto não consegue (ex.: toda sexta a produção cai 30% — equipe vai embora cedo).

**Implementação:**
- Dados: `rdo_atividades JOIN rdo_master` (já queryado pelo agente)
- Recharts AreaChart por atividade (padrão do projeto)
- Adicionar como aba "Produtividade" dentro do Hub de Operações

---

### N7 · Rastreabilidade de Decisão da IA `P2`

**O que é:** Ao clicar em qualquer número num insight do Agente, abre um painel "Origem do dado" mostrando as linhas brutas de `rdo_atividades` que geraram o cálculo. Exemplo: "Taxa de 18 módulos/dia = média de 5 registros: 04/04 (20), 05/04 (21), 06/04 (0-chuva), 07/04 (0), 08/04 (60)."

**Por que o cliente percebe valor:** Auditabilidade completa. O cliente enterprise exige saber de onde vem cada número antes de tomar uma decisão de contratação baseada no dado.

**Implementação:**
- Adicionar campo `"source_data": [{...}]` no JSON do agente (linhas brutas de `rdo_atividades`)
- Sheet lateral ao clicar no card — tabela simples com os registros
- Zero custo de IA adicional — os dados já foram buscados pelo agente

---

### N8 · Memória de Contrato no Chat `P1`

**O que é:** Ao perguntar sobre o mesmo contrato em sessões diferentes, o chat injeta automaticamente um "resumo da última conversa sobre {contrato}" no contexto. "Na sessão de ontem você perguntou sobre o atraso em Fundações Bloco A — desde então foram registrados 2 novos RDOs com avanço de 15pp."

**Por que o cliente percebe valor:** O chat deixa de ser uma ferramenta de consulta e passa a ser um acompanhamento contínuo. Cada sessão evolui a conversa anterior.

**Implementação:**
- Ao iniciar sessão com contrato selecionado: `sb_select("chat_messages", filters={"session_id": last_session_id_for_contrato})`
- Resumir últimas 5 mensagens com prompt curto (não injetar tudo — muito token)
- Injetar como `"## Contexto da última sessão\n{resumo}"` no system prompt

---

### N9 · Variação de Tom por Role no Chat `P2`

**O que é:** O system prompt do chat se adapta ao papel do usuário logado. Engenheiro recebe respostas focadas em campo e atividades. Gestor financeiro recebe foco em margem e fluxo. Mestre de obras recebe linguagem simples e respostas curtas. Administrador recebe visão completa.

**Por que o cliente percebe valor:** A IA fala a língua de quem usa. Um Mestre de Obras não precisa ler "margem operacional negativa implica risco de covenant" para entender que tem problema.

**Implementação:**
- Branch em `AIContext.get_system_prompt()` por `user_role`
- 4 personas: executivo (atual), engenheiro, campo (simples), mobile (ultracompacto)

---

## MATRIZ DE PRIORIDADE

| # | Feature | Tipo | Prioridade | Esforço | Impacto Percebido |
| :--- | :--- | :---: | :---: | :---: | :--- |
| U5 | Badge de confiança nos insights | Upgrade | P1 | Baixo | Alto — elimina desconfiança |
| U6 | Atualização automática pós-RDO | Upgrade | P1 | Baixo | Alto — fluxo automático |
| U2 | Tool label granular no typing | Upgrade | P1 | Baixo | Médio — transparência |
| U1 | Suggestion chips contextuais | Upgrade | P1 | Médio | Alto — onboarding |
| U3 | Memória de sessão entre conversas | Upgrade | P1 | Médio | Alto — retenção |
| U9 | KPI popup com análise IA inline | Upgrade | P1 | Médio | Alto — cada clique agrega |
| N1 | Confidence Score + Rastreabilidade | Nova | P1 | Médio | Crítico — confiabilidade |
| N2 | EVM (CPI/SPI/EAC) integrado | Nova | P1 | Médio | Alto — linguagem enterprise |
| N3 | Briefing matinal automatizado | Nova | P1 | Alto | Crítico — proatividade |
| N4 | Detecção de anomalias automática | Nova | P1 | Alto | Alto — antecipação |
| U4 | search_documents cross-contrato | Upgrade | P2 | Baixo | Médio — completude |
| U7 | Insights de clima x cronograma | Upgrade | P2 | Baixo | Médio — campo |
| U8 | Título dinâmico no dialog | Upgrade | P2 | Baixo | Baixo — polish |
| U10 | HITL visual por tipo de ação | Upgrade | P1 | Médio | Médio — confiança |
| U11 | Histórico de ações no Action AI | Upgrade | P2 | Médio | Médio — auditabilidade |
| U12 | Análise de clima no Hub | Upgrade | P2 | Baixo | Médio — integração |
| U13 | Variação de tom por role | Upgrade | P2 | Baixo | Médio — UX |
| N5 | Benchmarking interno | Nova | P2 | Médio | Alto — contexto único |
| N6 | Painel de produtividade visual | Nova | P2 | Alto | Alto — visualização |
| N7 | Rastreabilidade de decisão (UI) | Nova | P2 | Médio | Alto — auditabilidade |
| N8 | Memória de contrato no chat | Nova | P1 | Médio | Alto — retenção |
| N9 | Variação de tom por role | Nova | P2 | Baixo | Médio — UX |

---

## SPRINT SUGERIDO (próximas 2 semanas)

### Sprint 1 — Confiabilidade (impacto imediato no dia-a-dia)
1. **U5** — Badge de confiança nos insights (1 dia)
2. **U6** — Atualização automática pós-RDO (0.5 dia)
3. **U2** — Tool labels granulares (0.5 dia)
4. **N1** — Confidence score + rastreabilidade completa (2 dias)
5. **U9** — KPI popup com análise IA inline (1 dia)

### Sprint 2 — Proatividade (muda a percepção da plataforma)
1. **N3** — Briefing matinal automatizado (3 dias)
2. **N4** — Detecção de anomalias (2 dias)
3. **U1** — Suggestion chips contextuais (1 dia)
4. **U3 / N8** — Memória de sessão + memória de contrato (2 dias)

---

## ARQUITETURA DE DADOS VALIDADA (MCP — 2026-04-08)

Tabelas confirmadas via inspeção direta do Supabase:

| Tabela | Uso nas features de IA |
| :--- | :--- |
| `rdo_atividades` | Fonte primária de produtividade — `quantidade`, `efetivo`, `unidade` por atividade/dia |
| `rdo_master` | Contexto do RDO — `equipe_alocada`, `condicao_climatica`, `houve_chuva`, `houve_acidente` |
| `hub_atividade_historico` | Série temporal de avanço — `producao_dia`, `exec_qty_novo`, `conclusao_pct_anterior/novo` |
| `hub_atividades` | Cronograma base — `prod_planejada_dia`, `prod_real_media`, `desvio_prod_pct` já calculados |
| `hub_timeline` | Documentos do contrato — busca de cláusulas via `search_documents` |
| `agente_insights` | Cache de insights gerados — `insights JSONB`, `last_rdo_id`, `updated_at` |
| `hub_intelligence` | Cache de análises — TTL 24h, por contrato + tipo |
| `chat_sessions` + `chat_messages` | Histórico de conversas — base para memória entre sessões |

**Decisão registrada:** Agente de Atividades usa `rdo_atividades JOIN rdo_master` (SQL via `execute_safe_query`) e NÃO injeta objetos RDO inteiros. Motivo: dados granulares por atividade, taxa calculável por worker, sem desperdício de tokens.

---

*Documento mantido por Gustavo. Próxima revisão: após Sprint 1.*
