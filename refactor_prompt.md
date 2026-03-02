# Prompt de Engenharia de Software para Refatoração de Dashboard (Reflex/Python)

**Role:** Atue como um Engenheiro Sênior Especialista em Reflex (Python) e Data Engineering.

**Contexto do Projeto:**
Um dashboard financeiro/operacional construído com `reflex`, `pandas` e `plotly/recharts`. O visual está aprovado (KPIs, Gráficos, Dark Mode), mas a camada de dados e lógica está instável.

**Problemas Atuais (Critical Bugs):**
1. **Dados Sumindo/Não Carregando:** A aplicação falha silenciosamente ao carregar dados do Google Sheets, resultando em gráficos vazios ou "telas brancas".
2. **Travamentos:** A navegação entre páginas trava ou demora devido a processamento síncrono no `GlobalState`.
3. **Regressão:** Últimas atualizações quebraram a renderização de componentes chave (`kpi_card`, gráficos).

**Seus Objetivos (Deliverables):**

### 1. Blindar o Carregamento de Dados (`DataLoader` e `GlobalState`)
- **Robustez:** Reescreva `DataLoader.load_all` para que ele **NUNCA** retorne dicionários vazios ou `None` se houver qualquer dado disponível (seja Web, Cache ou Arquivo Local).
- **Fallback Obrigatório:** Se a conexão Web falhar e o Cache não existir, deve-se usar dados "mock" ou "arquivo de backup" explicitamente, com um aviso no log, para que a UI nunca fique quebrada.
- **Correção de Tipagem:** Garanta que `pandas.DataFrame` seja instanciado corretamente mesmo com dados sujos, evitando erros de `NoneType has no attribute columns`.

### 2. Otimizar Fluidez e UX (`index.py` e Componentes)
- **Estado Reativo:** Otimize `GlobalState` para usar `rx.var` computadas de forma eficiente, mas removendo a complexidade excessiva de cache que está causando bugs. Simplifique: Carregar -> Processar -> Exibir.
- **Feedback Visual:** Garanta que o spinner de carregamento (`rx.cond(is_loading, spinner, content)`) funcione corretamente durante qualquer operação de IO.
- **Drill-down:** Verifique se os `on_click` dos Cards estão redirecionando corretamente e se as páginas de destino (`/financeiro`, `/projetos`) estão recebendo os dados do estado global.

### 3. Restrições Estritas (Do NOT Touch)
- **NÃO altere o design visual.** Cores, fontes, espaçamentos, glassmorphism e layout DEVEM permanecer idênticos.
- **NÃO remova funcionalidades.** Apenas conserte o que está quebrado.
- **NÃO adicione novas libs** a menos que estritamente necessário para corrigir o bug.

**Instrução de Execução para o Claude Code:**
1. Analise `bomtempo/core/data_loader.py` e `bomtempo/state/global_state.py`. Identifique onde o fluxo de dados é interrompido (retornos prematuros, excepts silenciosos).
2. Refatore `load_data` para ser à prova de falhas.
3. Verifique `bomtempo/pages/index.py` para garantir que os componentes recebam dados válidos.
4. Execute e valide se os dados aparecem na tela inicial.

**Comando Sugerido:**
`refactor global_state.py and data_loader.py to ensure robust data loading with failover mechanims, fix silent failures, and verify async UI updates, keeping visual style intact.`
