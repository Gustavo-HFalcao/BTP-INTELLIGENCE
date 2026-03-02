# Planejamento de Upgrades - Bomtempo Dashboard vNext

Este documento define o roteiro estratégico e técnico para a evolução do Dashboard Bomtempo. O objetivo é transformar a ferramenta de visualização atual em uma plataforma segura, dinâmica e inteligente.

## 📅 Roadmap de Execução

A execução está dividida em 3 fases, priorizando segurança e autonomia de dados antes de funcionalidades avançadas.

---

## FASE 1: Fundação, Segurança e Acesso
**Foco:** Garantir que o dashboard possa ser publicado na web de forma segura e que os dados sejam vivos (editáveis pelo cliente).

### 1.1. Sistema de Login Simplificado (Credencial Única)
*   **Complexidade:** Baixa (3/10)
*   **Impacto:** Crítico (10/10) - Bloqueador de deploy público.
*   **Escopo:**
    *   Criar uma página de Login como rota inicial (`/`).
    *   Proteger todas as outras rotas (`/visao-geral`, `/obras`, etc.) verificando uma flag de autenticação no `GlobalState`.
    *   Implementar `rx.cond` no layout principal: Se não autenticado → Redirecionar para Login.
    *   Credencial fixa definida em `core/config.py` (env var preferencialmente) para acesso tipo "senha da obra".
    *   Feedback visual de erro de senha e loading state.

### 1.2. Integração Google Sheets (Data Live)
*   **Complexidade:** Média (5/10)
*   **Impacto:** Alto (10/10) - Autonomia para o cliente atualizar dados.
*   **Escopo:**
    *   Substituir a leitura de arquivos locais Excel (`dContratos.xlsx`, etc.) por leitura direta de planilhas Google publicadas ou via API (gspread).
    *   Criar adaptador em `core/data_loader.py`: `GoogleSheetsLoader`.
    *   Implementar cache (TTL 5-10 min) para não estourar cota de requisições.
    *   Manter a normalização de colunas existente para que o resto do código não precise mudar.
    *   **Fallback:** Se falhar a conexão, carregar os Excels locais de backup.

### 1.3. Otimização Mobile (Mobile First)
*   **Complexidade:** Média (6/10)
*   **Impacto:** Alto (9/10) - Acesso em campo (obras).
*   **Escopo:**
    *   Revisar `kpi_grid`: Garantir quebra de linha correta (1 coluna no mobile, 2 no tablet, 4 no desktop).
    *   Ajustar Sidebar: Implementar menu "hambúrguer" que abre um Drawer/Overlay no mobile, em vez de empurrar o conteúdo.
    *   Tabelas: Adicionar scroll horizontal (`overflow_x="auto"`) em todas as tabelas para não quebrar o layout.
    *   Gráficos: Ajustar altura dinâmica para caber em telas verticais.

---

## FASE 2: Interatividade e Inteligência Artificial
**Foco:** Transformar dados estáticos em insights acionáveis e navegação profunda.

### 2.1. Cards Clicáveis e Drill-Down
*   **Complexidade:** Média (4/10)
*   **Impacto:** Alto (8/10) - Melhor UX e investigação de dados.
*   **Escopo:**
    *   Transformar KPIs de "Visão Geral" em botões.
    *   Ao clicar em "Receita Total", navegar para `Financeiro` com filtro "Todos" aplicado.
    *   Ao clicar em "Obras em Atraso", navegar para `Obras` filtrando apenas as críticas.
    *   Implementar modais (`rx.dialog`) para detalhes rápidos sem sair da página (ex: lista rápida dos contratos compondo aquele KPI).

### 2.2. Chat com IA Real (LLM Integration)
*   **Complexidade:** Alta (7/10)
*   **Impacto:** Muito Alto (9/10) - Diferencial "Uau" e acessibilidade.
*   **Escopo:**
    *   Substituir a lógica `if/else` atual do `chat_ia.py`.
    *   Integrar API da OpenAI (GPT-4o-mini ou GPT-3.5) ou Anthropic.
    *   **Contexto:** Preparar um resumo JSON leve dos dados do `GlobalState` (Tabelas resumidas) para enviar no System Prompt.
    *   **Prompt Engineering:** "Você é um analista sênior da Bomtempo Engenharia. Responda com base nestes dados JSON...".
    *   Interface de chat com streaming de resposta (chunked response) para parecer natural.

---

## FASE 3: Analytics Profundo e Monitoramento
**Foco:** Refinamento técnico e métricas avançadas para gestão de longo prazo.

### 3.1. Analytics Extenso
*   **Complexidade:** Média (5/10) - Depende da definição de negócio.
*   **Impacto:** Médio (6/10)
*   **Escopo:**
    *   Criar página dedicada de relatórios.
    *   Novas métricas: Curva S físico-financeira acumulada, Histórico de medições (evolução temporal), Comparativo de performance entre Gerentes de Projeto.
    *   Botão de Download de Relatórios (PDF/CSV) processados pelo Pandas.

### 3.2. Sistema de Logs e Monitoramento
*   **Complexidade:** Baixa (3/10)
*   **Impacto:** Médio (5/10) - Debug e Manutenção.
*   **Escopo:**
    *   Configurar `logging` do Python para salvar em arquivo rotativo (`app.log`).
    *   Registrar: Falhas de login, erros de carga do Google Sheets, exceções em renderização de gráficos.
    *   Criar uma rota oculta `/admin/logs` (protegida) para visualizar os últimos erros sem precisar acessar o servidor via terminal.

### 3.3. Previsões ML (Machine Learning Real)
*   **Complexidade:** Muito Alta (9/10)
*   **Impacto:** Alto (7/10) - Exige dados históricos.
*   **Escopo:**
    *   Coletar histórico de medições (snapshoting mensal dos dados).
    *   Implementar regressão linear simples (Scikit-Learn) para prever "Data de Término Provável" baseada na velocidade média real vs. cronograma.
    *   Exibir cone de incerteza nos gráficos de prazo.
    *   *Nota:* Só implementável quando houver histórico de dados suficiente no banco/planilha.

---

## 🛠️ Stack Tecnológica Sugerida para Upgrades
*   **Auth:** Reflex State & LocalStorage (Simples) ou Firebase Auth (Robusto).
*   **Dados:** `gspread` + `pandas` + `cachetools` (para Google Sheets).
*   **AI:** `openai` (Python SDK).
*   **Logs:** Biblioteca padrão `logging`.

---

## 🚀 Plano de Implantação Detalhado

Este roteiro técnico descreve passo-a-passo como implementar cada funcionalidade.

### 🔐 FASE 1: Fundação & Segurança

#### 1. Login Simples (Autenticação Fixa)
1.  **Backend (State):**
    *   Adicionar `is_authenticated: bool = False` no `GlobalState`.
    *   Criar método `check_login(password: str)`.
    *   Validar contra `os.getenv("DASHBOARD_PASSWORD")` ou config fixa.
2.  **Frontend (Page):**
    *   Criar arquivo `bomtempo/pages/login.py`.
    *   Desenvolver layout simples com input de senha e botão "Entrar".
    *   Redirecionar para `/` (index) em caso de sucesso.
3.  **Proteção de Rotas:**
    *   Criar um componente wrapper `require_auth(component)` que verifica `GlobalState.is_authenticated`.
    *   Se `False`, exibe o componente de Login em vez da página solicitada.

#### 2. Integração Google Sheets
1.  **Google Cloud Console:**
    *   Habilitar Google Sheets API e Google Drive API.
    *   Criar Service Account e baixar JSON de credenciais.
    *   Compartilhar as planilhas do Drive com o email da Service Account.
2.  **Backup/Fallback:**
    *   Modificar `DataLoader` para aceitar `source_type="sheets" | "local"`.
    *   Criar rotina `cache_data()` que salva os dados baixados do Sheets localmente como backup (JSON ou CSV).
    *   Se a API do Google falhar, carregar do backup local mais recente.
3.  **Implementação:**
    *   Usar `gspread` para converter abas em DataFrames Pandas: `pd.DataFrame(worksheet.get_all_records())`.

#### 3. Mobile First (Refinamento CSS)
1.  **Sidebar Responsiva:**
    *   Adicionar botão "Menu" no topo visível apenas mobile (`display=["block", "block", "none"]`).
    *   Transformar Sidebar em um `rx.drawer` que desliza lateralmente no mobile.
2.  **Ajuste de Gráficos:**
    *   Configurar `rx.recharts` com `height` responsivo ou usar `AspectRatio` container.
    *   Garantir tamanhos de fonte legíveis em telas pequenas (12px min).

---

### 🧠 FASE 2: Interatividade & IA

#### 4. Drill-Down (Cards Clicáveis)
1.  **Interatividade:**
    *   Adicionar cursor pointer e `_hover` nos `kpi_card`.
    *   Vincular `on_click` a ações de filtro no `GlobalState` (ex: `set_status_filter("Atrasado")`).
2.  **Navegação:**
    *   Usar `rx.redirect` para levar o usuário à página detalhada correspondente.

#### 5. Chat com IA Real
1.  **Engenharia de Prompt:**
    *   Criar função `get_context_summary()` no `GlobalState`: retorna string com "Total Contratos: X, Valor TCV: Y, Obras Atrasadas: [A, B]".
    *   Prompt do Sistema: *"Atue como gerente de projetos. Use APENAS este contexto JSON para responder. Se a resposta não estiver no contexto, diga que não sabe."*
2.  **Conexão API:**
    *   Instalar `openai`.
    *   Criar método assíncrono `ask_gpt(question)` no State.
    *   Usar Streaming Response do Reflex para UX fluida (texto aparecendo aos poucos).

---

### 📈 FASE 3: Analytics & Monitoramento

#### 6. Analytics Extenso
1.  **Novas Visões:**
    *   Criar `bomtempo/pages/relatorios.py`.
    *   Gráficos temporais (LineChart): Evolução do "Previsto vs Realizado" mês a mês.
    *   Tabela pivô de performance financeira por Centro de Custo.

#### 7. Logs de Sistema
1.  **Configuração:**
    *   Configurar `logging.FileHandler` apontando para `logs/app.log`.
    *   Formato: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.
2.  **Visualizador:**
    *   Ler as últimas 100 linhas do arquivo de log e exibir em um modal protegido por senha de admin.

#### 8. Machine Learning (Futuro)
1.  **Coleta de Dados:**
    *   Criar rotina cron (externa ou no data_loader) que salva snapshot dos KPIs todo dia 1º do mês.
    *   Armazenar histórico em CSV acumulativo ou SQLite.
2.  **Modelo:**
    *   Treinar `LinearRegression` simples usando histórico (X=meses, Y=avanço).
    *   Prever data de atingimento de 100%.
