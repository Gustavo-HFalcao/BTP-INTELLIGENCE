# Plano de Implementação: Features Core "Enterprise"

Este documento detalha a arquitetura, estruturação e planejamento para a entrega das 4 features core do **Bomtempo Intelligence**, visando posicionamento enterprise, agregação de valor real e "Wow Factor". Criado para ser lido e executado de forma "one-shot" por agentes de IA.

## 1. Visão Geral e Estratégia
O objetivo é transformar os módulos existentes em ativos de alto valor agregado (SaaS B2B). Ao invés de meras exibições de dados, o sistema passará a oferecer **descoberta ativa, alertas inteligentes, insights aprofundados e rastreabilidade total**, poupando tempo e dinheiro do gestor.

### Matriz de Complexidade x Impacto
| Feature | Impacto no Gestor | Complexidade | Classificação |
|---------|-------------------|--------------|---------------|
| 1. Revamp UI & Módulo Obras | 🚀 Altíssimo | 🟡 Média | Quick-Win Absoluto ("Wow Factor" imediato) |
| 3. Módulo de Relatórios IA | 🚀 Altíssimo | 🟡 Média | Game-Changer Executivo |
| 2. Módulo de Alertas Proativos| ⭐ Alto | 🔴 Alta | Diferencial Enterprise (Requer CRON/Async) |
| 4. Módulo de Logs e Auditoria| 🛡️ Médio | 🟡 Média | Requisito Segurança Enterprise |

### Ordem Recomendada de Implantação
1. **Revamp Módulo Obras (`obras.py`)**: Gera impacto visual e resolve dores de visibilidade cruciais na porta de entrada da plataforma.
2. **Módulo de Relatórios (`relatorios.py` e `relatorios_state.py`)**: Entregará valor gerencial direto com relatórios exportáveis e IA generativa especializada.
3. **Módulo de Alertas (`alertas.py` e `alertas_state.py`)**: Envolve lógica de background (sweeps). Requer que a base de Obras já esteja rica em dados gerados na etapa 1 para "alarmar".
4. **Módulo de Logs (`logs_auditoria.py` e `logging_utils.py`)**: Como "cross-cutting concern", deve ser criado e depois integrado nos estados das etapas anteriores.

---

## 2. Detalhamento e Modificações Propostas

### Feature 1: Revamp UI e Módulo "Obras" (Espelho do Projetos + Esteroides)
**Problema Atual:** O módulo de obras detalha apenas uma única obra no load ou via select. Falta a visão macro interativa.
**Solução:** Espelhar o conceito de "Cards Clicáveis" de `projetos.py` para listar todas as obras, e ao clicar, aprofundar drasticamente os dados. As tooltips e gráficos devem ser vivos (ex: hover no gráfico financeiro explica *por que* estourou).

**Sugestão de Ampliação de Dados (Novas Colunas Supabase em `obras` ou tabelas satélite):**
- `budget_planejado` e `budget_realizado` (Mede estouro em tempo real).
- `equipe_presente_hoje` e `efetivo_planejado` (Alerta de falta de pessoal).
- `chuva_acumulada_mm` e `dias_parados_clima` (Ajuste automático de prazo).
- `risco_geral_score` (Ex: 0 a 100, calculado com base em atraso + financeiro).
- `ultima_vistoria_data` e `foto_destaque_url`.

**Arquitetura (`obras.py`):**
- **List View:** Grid de cards com mini-gauges de progresso, ícone de clima atual, indicador de status (Verde, Amarelo, Vermelho baseado no `risco_geral_score`).
- **Detail View:** Ao clicar, abre:
  1. Painel com Gauge de avanço físico.
  2. Gráfico "Burn-down" de prazos VS custo real.
  3. "Inteligência Ativa": Uma caixa de texto onde a IA escreve automaticamente 1 parágrafo: *"A obra está avançada estruturalmente, mas a disciplina Elétrica está bloqueada aguardando inversor logístico."*

---

### Feature 2: Módulo de Alertas Proativos (Chronological vs Reactive)
**Problema Atual:** O gestor precisa procurar a informação de risco. O SaaS precisa entregar o risco a ele mastigado.
**Solução:** Nova página `alertas.py` dividida em dois painéis, 100% configurável pelo usuário, regida por rotinas de background.

**Arquitetura e UI:**
- **Layout Split-Screen:** 
  - *Esquerda (Recorrentes/Cronológicos):* DRE Semanal, Resumo Diário às 18h, Fechamento de Medição todo dia 25.
  - *Direita (Reativos/Gatilhos):* RDO não validado por IA, Orçamento estourado > 5%, Clima severo iminente.
- **Configuração (Toggles):** Cada card de alerta terá um switch (Toggle UI) para o gestor ligar/desligar a assinatura daquela notificação.
**Modelagem do Banco de Dados Sugerida:**
- Tabela `alert_subscriptions`: `user_id`, `alert_type`, `is_active`, `channels (email, push)`.
- Tabela `alert_history`: `id`, `project_id`, `alert_type`, `message`, `timestamp`, `is_read`.

**Implementação Técnica (O "Sweep"):**
- Tarefas periódicas assíncronas (ex: via `apscheduler` associado ao FastAPI interno do Reflex ou loop de `asyncio` rodando paralelamente no backend).
- A rotina varre os KPIs críticos: `"SELECT id FROM contratos WHERE realizado_pct < previsto_pct - 10"`.
- Grava no `alert_history` e emite email se `is_active = True`.

---

### Feature 3: Módulo de Relatórios (Generalista e Inteligente)
**Problema Atual:** Relatórios precisam ser construídos em Excel e copiados de DREs. Falta automação e exportação ágil.
**Solução:** Nova página `relatorios.py`. O gestor gera relatórios de alto nível "board-ready".

**Arquitetura e Fluxo:**
- **Seleção Inicial:** Dropdown do Projeto/Contrato.
- **Opções de Geração (Cards):**
  1. **Relatório Estático (Dossier):** Layout HTML estruturado (Estátisticas reais da API, imagens de RDOs recentes, tabelas financeiras). Botão *"Exportar PDF"*.
  2. **Relatório IA Generativa:** Comboboxes para escolher "Abordagem" (Descritiva para auditoria, Estratégica para diretoria, Analítica para financeira).
- **Chatbot Criador de Relatórios (O "Wow Factor"):**
  - Ficará no bottom da página: "Precisa de um formato específico? Peça à nossa IA."
  - **Voice Integration:** Aproveitar lógica do `mobile_chat.py` / `voice_chat_page.py`.
  - **Sistema de Guardrails (Prompt):** *"Você é um gerador de relatórios executivos rígido. Retorne EXCLUSIVAMENTE conteúdo em Markdown usando o esquema de cores e estrutura corporativa. Use os dados de contexto fornecidos. Não crie conversas genéricas."*
- Renderiza o resultado da IA dentro de um card tipo pergaminho digital customizado, com botão "Copiar/Baixar".
- **Gráficos Dinâmicos Gerados por IA (Recharts):**
  - A IA não deve apenas gerar texto, mas também *gráficos reais* interativos integrados com a biblioteca nativa `recharts` do Reflex.
  - **Atenção à Implementação:** Para evitar que o gráfico renderize vazio (eixos sem dados), a inteligência precisa pré-estruturar ou responder com os objetos/dados (JSON) necessários **antes ou durante** a geração do componente, atrelando os 'data keys' corretamente ao estado da aplicação antes da renderização do componente gráfico visual. Essa extração de payload da IA deve ser blindada.

---

### Feature 4: Módulo de Logs e Auditoria (Zero Impacto de Performance)
**Problema Atual:** Nenhuma rastreabilidade das ações do usuário ou interações com a IA, dificultando suporte e métricas de adoção.
**Solução:** Implementar um logging transparente, leve e não bloqueante.

**Estratégia do Banco de Dados (One Table to Rule Them All):**
Usar apenas **UMA tabela generalizada**, para manter simplicidade e índices performáticos.
- Tabela `system_logs`:
  - `id` (UUID)
  - `created_at` (Timestamp)
  - `user_email` / `user_id` (Quem fez)
  - `action_category` (Enum: `LOGIN`, `DATA_EDIT`, `IA_INSIGHT`, `IA_CHAT`, `REPORT_GEN`)
  - `entity_id` (Opcional - Ex: ID da obra/tabela afetada)
  - `metadata` (JSONB - *Crucial! Permite salvar dados antigos/novos de edits sem poluir as colunas*).
  - `client_info` (IP, User-Agent)

**Performance Guardrails (`logging_utils.py`):**
- Ao disparar um evento na UI (ex: botão salvar no `edit_state.py`), a gravação do log acontecerá via **Fire-and-Forget**.
- `asyncio.create_task(supabase.table("system_logs").insert(...))` garante que a thread do painel não aguardará a resposta do banco de dados para liberar a UI para o usuário. 
- A visualização será na página `logs_auditoria.py` com filtros de busca (Tabela reflex.data_table com paginação via banco para não travar a memória).

---

## 3. Plano de Verificação (Testes)

Para confirmar o sucesso dessa implementação "One-Shot" para as 4 features:

1. **Obra Revamp:** 
   - Acessar `/obras`.
   - Clicar em um card de obra; a página deve exibir o painel demográfico sem travar. 
   - Verificar as animações do novo Gauge e o painel de insights.
   
2. **Relatórios IA e Gráficos:**
   - Acessar `/relatorios`.
   - Escolher um projeto mockado e mandar gerar relatório com perfil "Estratégico".
   - Confirmar se a IA retorna Markdown válido e renderiza corretamente o Reflex Markdown component.
   - Solicitar um relatório *com gráficos comparativos* e garantir que os componentes de `recharts` renderizem os dados sem que fiquem zerados no carregamento.
   - Usar gravação de voz (mock) e garantir que o texto gerado aciona o relatório.
   
3. **Logs (Background Testing):**
   - Editar um valor aleatório no `Editor de Dados`.
   - Acessar área de admin `/logs` e conferir se o registro (Quem, Quando, Valor Anterior/Novo em JSON) foi capturado instantaneamente.
   
4. **Alarme Sweep:**
   - Ativar uma trigger manual do script de Job Scheduler simulando virada de relógio para meia-noite.
   - Conferir na UI de "Alertas" se os riscos proativos apareceram na coluna da direita com ícone vermelho.

----------
**INSTRUÇÃO FINAL PARA AGENTES (PROMPT LATER):** Todo o stack deve seguir o estilo atual (`S.COPPER`, `S.PATINA`, componentes Glass), mantendo-se perfeitamente coeso. Utilize placeholders criativos nas tabelas novas caso o backend relacional Supabase demore para ser provisionado, para demonstrar o visual UX e justificar a venda imediatamente.
