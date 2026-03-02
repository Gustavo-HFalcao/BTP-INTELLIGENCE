ESCOPO ESTRUTURADO - PROJETO BOMTEMPO | REFLEX + PYTHON
ANÁLISE DE COMPLEXIDADE E ORDEM OTIMIZADA DE IMPLEMENTAÇÃO

BASELINE CORE: TENHA EXTREMO CUIDADO COM A ESTRUTURA QUE JÁ CONSTRUÍMOS, CUIDADO PARA NÃO ATRAPALHAR NENHUMA FEATURE, PREFIRO QUE NÃO SEJA IMPLEMENTADO E VOCÊ ME AVISE DA BARREIRA QUE EXISTE PARA CONTORNARMOS DO QUE IMPLEMENTAR ALGO E QUEBRAR ALGO QUE JÁ EXISTE. REPITO, TENHA CUIDADO COM O QUE TEMOS, É UMA VERSÃO ESTÁVEL E FUNCIONAL, NOVAS FEATURES NÃO DEVEM QUEBRAR O QUE JÁ EXISTE. NOVOS MODULOS DEVEM SER CONFIÁVEIS E SEGUROS, ENTÃO SEM MUITAS GAMBIARRAS. SEJA CLARO E SINCERRO COMIGO NOS SEUS RETORNOS, SE NÃO FOR DIFÍCIL OU FOR COMPLEXO, ME AVISE QUE RECALCULO A ROTA. OUTRA COISA, NÃO LEVE TUDO QUE ESTÁ AQUI NO ESCOPO AO PÉ DA LETRA, VOCÊ TEM COMPLETO CONHECIMENTO DO NOSSO PROJETO, ENTÃO, SE ALGO AQUI TIVER INCONSISTENTE OU TIVER ALGUM CAMINHO MELHOR PARA FAZER A MESMA COISA, SIGA O CAMINHO MELHOR COM BASE NA NOSSA ARQUITETURA, AQUI É SOMENTE UM DOCUMENTO PARA SE BASEAR NAS NOVAS FEATURES E NÃO UMA GUIDELINE ESTRITA. TENHA TUDO ISSO EM MENTE AO IMPLEMENTAR ESSAS NOVAS FEATURES. TUDO QUE MENCIONAR BANCO DE DADOS, VAMOS PULAR POR ENQUANTO, VOU CRIAR E DISPONIBILIZAR NOVAS SHEETS E SEUS LINKS PARA UTILIZARMOS, COMO A SHEET DE RDO, ALERTAS, ETC.
ANTES DE IMPLEMENTAR QUALQUER FEATURE DE VERDADE VALIDE: SMOKE TESTS - GARANTINDO QUE O LOGIN TÁ FUNCIONANDO, SE O DASHBOARD CARREGA SEM ERROS, SE A API TÁ RESPONDENDO, ETC; TESTE AS INTEGRAÇÕES - SE TÁ PUXANDO OS DADOS DAS SHEETS CORRETAMENTE, SE AS APIS TÃO FUNCIONAIS, SE TUDO VAI RODAR PERFEITAMENTE; VEJA SE DADOS EXISTENTES NÃO FORAM CORROMPIDOS, SE A LÓGICA DA IMPLEMENTAÇÃO TÁ CONFIÁVEL; VEJA SE AS DEPENDENCIAS EXECUAM SEM CONFLITOS. SE ALGUM ITEM FALHAR, REVERTA A IMPLEMENTAÇÃO E REPORTE O PROBLEMA. SE VOCÊ (CLAUDE CODE) IDENTIFICAR QUE A IMPLEMENTAÇÃO:
- Requer mudanças em >5 arquivos existentes críticos
- Precisa de migration complexa com data transformation
- Tem risco >10% de quebrar funcionalidade existente

→ PARE e retorne: "⚠️ IMPLEMENTAÇÃO DE ALTO RISCO - REQUER REVISÃO MANUAL"

TENHA NOÇÃO DAS ÁREAS DE CÓDIGO INTOCÁVEIS E ESTA É UMA VERSÃO ESTÁVEL E FUNCIONAL EM PRODUÇÃO. NOVAS FEATURES:
✅ DEVEM ser isoladas (novos arquivos, rotas, tabelas)
✅ DEVEM respeitar arquitetura existente
✅ DEVEM ter feature flags (módulos complexos)
✅ DEVEM ter migrations reversíveis
✅ DEVEM passar por checklist de validação

❌ NÃO PODEM modificar código em [áreas intocáveis - lista acima]
❌ NÃO PODEM quebrar funcionalidades existentes
❌ NÃO PODEM degradar performance (ver benchmarks)

SEJA CLARO E SINCERO NOS SEUS RETORNOS:
- Se algo for complexo/arriscado: AVISE
- Se precisar modificar código crítico: PROPONHA alternativa
- Se detectar inconsistência no escopo: QUESTIONE

ORDEM RECOMENDADA DE IMPLEMENTAÇÃO
1º → Infraestrutura Base + Módulo RDO (Complexidade: MÉDIA)
2º → Módulo de Relatórios (Complexidade: MÉDIA-ALTA)
3º → Módulo de Alertas (Complexidade: ALTA)
4º → Upgrade Chat Agentic AI (Complexidade: MUITO ALTA)

DETALHAMENTO POR MÓDULO
1. INFRAESTRUTURA BASE (IMPLEMENTAR PRIMEIRO)
Complexidade: MÉDIA
Prioridade: CRÍTICA - base para todos os módulos

Componentes Essenciais
Sistema RBAC (Role-Based Access Control)

Roles: admin, gestor, mestre_obras, viewer

Tabela: users, roles, permissions, user_roles

Middleware Reflex para verificação de permissões em cada route

Decorator @requires_permission() para proteger event handlers

Lib sugerida: implementação custom com PostgreSQL ou sqlalchemy + tabelas de permissão

Sistema de Jobs/Scheduler

APScheduler (recomendado para Reflex - mais leve que Celery)

Background tasks Reflex nativos para jobs curtos
​

Jobs necessários:

refresh_data_job: atualização de dados (a cada X minutos)

reactive_alerts_job: verificação de alertas reativos (a cada 5-15min)

scheduled_alerts_job: envio de alertas programados (cron diário/semanal)

rdo_email_job: envio de RDOs após geração

Refresh de Dados

Job prioritário que roda antes de qualquer operação crítica

Cache Redis (opcional) para dados frequentes

Flag last_refresh_timestamp para tracking

Trigger manual via botão + automático via scheduler

Sistema de Email

smtplib nativo Python + email.mime

Templates HTML com Jinja2

Queue de emails (PostgreSQL tabela email_queue)

Retry logic para falhas

Provider: Gmail SMTP, SendGrid ou AWS SES

2. MÓDULO RDO (IMPLEMENTAR SEGUNDO)
Complexidade: MÉDIA
Justificativa: Fluxo mais linear, menos dependências de IA, aproveita infraestrutura base já implementada

Arquitetura Dual-Login
Login Tipo 1: Mestre de Obras (preenchimento)

text
Permissions: ['rdo:create', 'rdo:view_own']
Features:
- Tela principal: formulário de preenchimento RDO
- Tab secundária: acompanhamento de RDOs próprios
- Input de e-mails destinatários (salvar em tabela `rdo_recipients`)
Login Tipo 2: Gestor (visualização)

text
Permissions: ['rdo:view_all', 'rdo:analytics']
Features:
- Dashboard consolidado
- Indicadores: taxa de preenchimento, obras críticas, atrasos
- Filtros: obra, período, responsável
Fluxo RDO
1. Preenchimento

Formulário Reflex com validação client-side

Campos: obra, data, atividades, recursos, observações, clima, etc

Upload de fotos (opcional)

2. Validação

Backend validation (campos obrigatórios, ranges, formatos)

Preview antes de gerar

3. Geração

Salvar dados em PostgreSQL (rdo_entries table)

Paralelamente atualizar Google Sheets (API gspread) para histórico

Gerar PDF com ReportLab ou WeasyPrint

Template HTML → PDF estruturado e padronizado

4. Assinatura Digital

Opção A (Simples): Assinatura via upload de imagem PNG 

Opção B - buscar alguma solução ainda mais simples, tipo, assinatura só com o nome do mestre de obras

Solução Recomendada para v1: Campo de assinatura texto + timestamp + IP tracking (não bloqueia envio)

PDF gerado → salvo como DRAFT → mestre assina digitalmente → status muda para SIGNED → dispara envio automático

5. Envio Automático

Após assinatura, job adiciona email na email_queue

Template HTML personalizado com logo Bomtempo

Anexo: PDF do RDO

Destinatários: lista configurada + gestor(es) automaticamente

Dados Históricos
Google Sheets Integration

Antes de gerar PDF, fazer append row no Sheets

Campos estruturados: obra_id, data, mestre_id, campos_preenchidos

Permite análise histórica para gestor via Power BI ou dashboards internos

Indicadores Gestor
Total de RDOs no período

Taxa de preenchimento diário/semanal

Obras com RDOs atrasados

Heatmap de atividades por obra

Timeline de progresso por projeto

3. MÓDULO DE RELATÓRIOS (IMPLEMENTAR TERCEIRO)
Complexidade: MÉDIA-ALTA
Justificativa: Requer integração IA moderada, mas sem memória de longo prazo ainda

Estrutura
Cards Pré-Prontos (3-4 tipos)

text
Exemplos:
- Relatório Financeiro: receitas, despesas, projeções
- Relatório Operacional: obras ativas, recursos alocados, timeline
- Relatório Técnico: medições, avanço físico, qualidade
Interface por Card

Dropdown: selecionar projeto(s)

Radio buttons: abordagem IA

Descritiva: "O que aconteceu" (fatos e números)

Estratégica: "O que fazer" (insights e recomendações)

Analítica: "Por que aconteceu" (causas e correlações)

Botão: Gerar Relatório

Template HTML Estruturado

Criar templates em templates/relatorios/

Estrutura fixa: cabeçalho, seções, rodapé

Placeholders para IA preencher: {{analise_ia}}, {{insights}}, {{graficos_descricao}}

CSS inline para garantir renderização consistente

Chat de Relatório Personalizado

Input texto ou voz (Speech-to-Text com Whisper API ou Google Speech)

Context: dados completos do projeto selecionado

Prompt estruturado: gere um prompt completo e infalível para que o relatório saia com qualidade e confiabilidade.

LLM: Use uma das duas chaves de APi que temos, atualmente é a openai e moonshotai, priorize openai por enquanto.

Processar resposta

Renderizar em HTML

Opção de download PDF (WeasyPrint)

Awareness de Dados

Antes de chamar IA, executar refresh_data_job ou verificar timestamp

Injetar no context: tabelas relevantes (agregadas, não raw)

Schema awareness: passar estrutura das tabelas para IA entender

4. MÓDULO DE ALERTAS (IMPLEMENTAR QUARTO)
Complexidade: ALTA
Justificativa: Requer jobs complexos, lógica de detecção, templates dinâmicos, configurações avançadas

Tipos de Alerta
1. Alerta Reativo

Job: reactive_alerts_job (a cada 5-15 minutos)

Lógica:

python
# Pseudocódigo
criterios = fetch_active_alert_rules()
for criterio in criterios:
    dados_atuais = query_database(criterio.query)
    if criterio.condicao_atendida(dados_atuais):
        alerta = criar_alerta(criterio, dados_atuais)
        enviar_para_ia_analisar(alerta)
IA analisa contexto e gera output estruturado (gravidade, ação sugerida)

Envio imediato via email

2. Alerta Programado (Diário/Semanal/Mensal)

Job: scheduled_alerts_job com cron

Coleta alertas ativos no período

Gera resumo consolidado

4 cards (um por módulo): RDO, Financeiro, Operacional, Técnico

Card extra: relatório personalizado IA

Template HTML rico

Envio em horário fixo (ex: 8h da manhã)

Interface de Configuração
Tela de Alertas

Lista de alertas configurados

Switch: ativar/desativar alerta

Botão: Criar Novo Alerta

Formulário de Criação

text
Campos:
- Nome do alerta
- Tipo: reativo | programado
- Frequência (se programado): diário/semanal/mensal + horário
- Módulo relacionado: RDO | Relatório | Financeiro | etc
- Condição SQL: query personalizada ou builder visual
- Threshold: valor limite
- Destinatários: input múltiplo de emails (salvar em tabela `alert_recipients`)
- Template de email: dropdown de templates pré-formatados
Storage de Configurações

Tabela: alert_rules

Campos: id, nome, tipo, frequencia, condicao_sql, threshold, modulo, ativo, template_id, created_at

Tabela: alert_recipients (many-to-many)

Templates de Email

Criar biblioteca em templates/alertas/

Variáveis dinâmicas: {{gravidade}}, {{dados}}, {{insights_ia}}, {{acoes_sugeridas}}

Design responsivo HTML + CSS inline

Detecção de Alertas
Opção A (Sistema detecta + IA valida):

python
# Sistema roda query SQL
resultados = executar_condicao_sql(alert_rule)
if len(resultados) > 0:
    # IA valida e enriquece
    context = {"alerta": alert_rule, "dados": resultados}
    analise_ia = llm.generate(prompt_validacao, context)
    if analise_ia.confirma_alerta:
        disparar_email(analise_ia.output_estruturado)
Opção B (IA detecta diretamente): Não recomendado - mais lento e caro

Garantia de Dados Atualizados
reactive_alerts_job roda APÓS refresh_data_job

Dependência explícita no scheduler

Timestamp checking antes de cada análise

5. UPGRADE CHAT AGENTIC AI (IMPLEMENTAR POR ÚLTIMO)
Complexidade: MUITO ALTA
Justificativa: Arquitetura complexa, memória de longo prazo, aprendizado contínuo, múltiplas integrações

Componentes Agentic
1. Short-Term Memory (Conversacional)

Buffer in-memory da sessão atual

Últimas 10-20 interações

Implementação: ConversationBufferMemory do LangChain
​

2. Long-Term Memory (Persistente)

Vector Database: Pinecone, Weaviate ou Qdrant

Armazenar:

Perguntas históricas + respostas

Insights gerados

Contexto dos projetos

Padrões detectados

Embeddings: OpenAI text-embedding-3 ou sentence-transformers

3. Awareness Layer (Full Context)

Schema dos dados: tabelas, colunas, tipos, relacionamentos

Estatísticas descritivas: ranges, valores únicos, nulls

Metadados de projetos: nome, cliente, datas, status

Documentos: contratos, especificações técnicas (via OCR + embeddings)

4. Aprendizado Contínuo

Feedback Loop

python
# Após cada resposta IA
user_feedback = request_feedback()  # thumbs up/down
if user_feedback == "positive":
    salvar_embedding_com_peso_alto(pergunta, resposta)
elif user_feedback == "negative":
    marcar_para_refinamento(pergunta, resposta)
Pattern Recognition

Agrupar perguntas similares (clustering de embeddings)

Detectar temas recorrentes

Job semanal: learning_job analisa padrões e gera "conhecimento consolidado"

API External Learning (Opcional)

Integrar com Perplexity API para enriquecer respostas com dados externos

Groq API para inferência rápida [baseado no perfil do usuário]

5. Análise de Página Integrada

Chat pode referenciar análises passadas

"Lembra da análise financeira do Projeto X que fizemos semana passada?"

Busca semântica no vector DB retorna contexto relevante

Arquitetura Técnica
Stack Recomendado

text
Framework: LangChain + LangGraph (orquestração de agentes)
LLM: Claude Sonnet 4.5 (via Anthropic API)
Vector DB: Qdrant (open-source, self-hosted)
Embeddings: OpenAI text-embedding-3-large
Memory: PostgreSQL (metadata) + Qdrant (semantic search)
Orchestration: LangGraph para multi-step reasoning
Fluxo Agentic

text
User Query
    ↓
Intent Classification (router)
    ↓
├─> Simple Query → Direct Answer
├─> Data Query → SQL Agent → Execute → Format
├─> Analysis Query → Retrieve Context → Reasoning Agent → Generate Insight
└─> Complex Query → Multi-Agent Orchestration
    ↓
Generate Response
    ↓
Store in Long-Term Memory (embedding + metadata)
    ↓
Update Learning Patterns
SQL Agent

Text-to-SQL com validação

Sandbox query execution (read-only user)

Explain query antes de executar

Reasoning Agent

Acessa memória de longo prazo

Conecta insights passados com pergunta atual

Gera insights novos baseados em padrões

Context Manager

Gerencia janela de contexto (100k tokens Claude)

Prioriza informações relevantes

Comprime histórico antigo

Implementação de Memória
Tabelas PostgreSQL

sql
CREATE TABLE ai_conversations (
    id SERIAL PRIMARY KEY,
    session_id UUID,
    user_id INT,
    projeto_id INT,
    query TEXT,
    response TEXT,
    feedback INT,  -- -1, 0, 1
    embedding_id VARCHAR,  -- ref para Qdrant
    timestamp TIMESTAMP
);

CREATE TABLE ai_insights (
    id SERIAL PRIMARY KEY,
    projeto_id INT,
    insight_text TEXT,
    confidence FLOAT,
    categoria VARCHAR,
    embedding_id VARCHAR,
    created_at TIMESTAMP
);

CREATE TABLE ai_learning_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR,
    frequency INT,
    last_seen TIMESTAMP,
    metadata JSONB
);
Qdrant Collections

python
# Collection: conversations
{
    "vector": [0.1, 0.2, ...],  # embedding da query+response
    "payload": {
        "conversation_id": 123,
        "projeto_id": 5,
        "timestamp": "2026-02-17T09:00:00",
        "feedback": 1
    }
}

# Collection: insights
{
    "vector": [...],
    "payload": {
        "insight_id": 456,
        "projeto_id": 5,
        "categoria": "financeiro",
        "confidence": 0.92
    }
}
Retrieval Strategy

python
# Hybrid search
def retrieve_context(query, projeto_id):
    # 1. Semantic search (Qdrant)
    similar_convs = qdrant.search(
        collection="conversations",
        query_vector=embed(query),
        filter={"projeto_id": projeto_id},
        limit=5
    )
    
    # 2. Keyword search (PostgreSQL FTS)
    keyword_results = db.query(
        "SELECT * FROM ai_conversations WHERE to_tsvector(query) @@ to_tsquery(%s)",
        query
    )
    
    # 3. Merge + rank
    context = merge_and_rank(similar_convs, keyword_results)
    return context
PREOCUPAÇÕES TRANSVERSAIS
1. Refresh de Dados
Estratégia Multi-Layer

python
# Layer 1: Cache em memória (Reflex State) - 5min
# Layer 2: Cache Redis - 15min
# Layer 3: PostgreSQL - source of truth

# Job refresh_data_job
def refresh_data():
    # 1. Fetch de fontes externas (APIs, Sheets, etc)
    # 2. Transform + validate
    # 3. Upsert PostgreSQL
    # 4. Invalidate caches
    # 5. Update timestamp global
Trigger Manual

Botão "Atualizar Dados" com loading state

Reflex event handler chama job síncrono

Feedback visual de progresso

2. RBAC Detalhado
Permissions Granulares

python
PERMISSIONS = {
    'admin': ['*'],
    'gestor': [
        'rdo:view_all', 'rdo:analytics',
        'relatorio:view_all', 'relatorio:generate',
        'alerta:view', 'alerta:configure',
        'chat:use', 'chat:history'
    ],
    'mestre_obras': [
        'rdo:create', 'rdo:view_own',
        'relatorio:view_own',
        'chat:use_limited'
    ],
    'viewer': [
        'relatorio:view_all',
        'alerta:view'
    ]
}
Middleware Reflex

python
def require_permission(permission: str):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if not self.current_user.has_permission(permission):
                return rx.redirect("/unauthorized")
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
3. Jobs Architecture
APScheduler Setup

python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url='postgresql://...')
}

scheduler = BackgroundScheduler(jobstores=jobstores)

# Refresh job (prioritário)
scheduler.add_job(
    refresh_data_job,
    'interval',
    minutes=15,
    id='refresh_data',
    max_instances=1
)

# Alerta reativo (após refresh)
scheduler.add_job(
    reactive_alerts_job,
    'interval',
    minutes=10,
    id='reactive_alerts',
    depends_on=['refresh_data']  # Custom logic
)

# Alerta programado
scheduler.add_job(
    scheduled_alerts_job,
    'cron',
    hour=8,
    minute=0,
    id='daily_alerts'
)

scheduler.start()
4. Email Queue & Retry
Tabela de Queue

sql
CREATE TABLE email_queue (
    id SERIAL PRIMARY KEY,
    destinatarios TEXT[],
    assunto VARCHAR,
    corpo_html TEXT,
    anexos JSONB,
    status VARCHAR,  -- pending, sent, failed
    tentativas INT DEFAULT 0,
    erro TEXT,
    created_at TIMESTAMP,
    sent_at TIMESTAMP
);
Worker Job

python
def email_worker_job():
    pending = db.query("SELECT * FROM email_queue WHERE status='pending' AND tentativas < 3")
    for email in pending:
        try:
            send_email(email)
            db.update(email.id, status='sent', sent_at=now())
        except Exception as e:
            db.update(email.id, tentativas=email.tentativas+1, erro=str(e))
FERRAMENTAS & LIBS ESSENCIAIS
Backend Core
Reflex: framework principal
​

PostgreSQL: banco de dados principal

SQLAlchemy: ORM

Pydantic: validação de dados

Jobs & Tasks
APScheduler: scheduler de jobs

Redis (opcional): cache e queue

IA & ML
LangChain: framework agentic
​

LangGraph: orquestração multi-agent

Qdrant: vector database

OpenAI API: embeddings

Anthropic API: Claude Sonnet 4.5

Email
smtplib: envio SMTP

Jinja2: templates HTML

email.mime: formatação de emails

Documentos
ReportLab ou WeasyPrint: geração PDF

gspread: integração Google Sheets

python-docx (opcional): geração Word

Autenticação & Segurança
bcrypt: hash de senhas

PyJWT: tokens JWT

python-dotenv: variáveis de ambiente

Extras
Whisper API: speech-to-text (para chat de voz)

Pillow: processamento de imagens (assinatura)

ESTRUTURA DE PASTAS SUGERIDA
text
bomtempo-reflex/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── state.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── login.py
│   │   ├── dashboard.py
│   │   ├── rdo/
│   │   │   ├── preenchimento.py
│   │   │   ├── acompanhamento.py
│   │   │   └── gestao.py
│   │   ├── relatorios/
│   │   │   ├── cards.py
│   │   │   └── personalizado.py
│   │   ├── alertas/
│   │   │   ├── lista.py
│   │   │   └── configuracao.py
│   │   └── chat/
│   │       └── agentic.py
│   ├── components/
│   │   ├── auth.py
│   │   ├── navbar.py
│   │   └── modals.py
│   ├── models/
│   │   ├── user.py
│   │   ├── rdo.py
│   │   ├── alerta.py
│   │   └── ai_memory.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── email_service.py
│   │   ├── pdf_service.py
│   │   ├── sheets_service.py
│   │   ├── ai_service.py
│   │   └── alert_service.py
│   ├── jobs/
│   │   ├── scheduler.py
│   │   ├── refresh_job.py
│   │   ├── alert_jobs.py
│   │   ├── email_worker.py
│   │   └── learning_job.py
│   ├── agents/
│   │   ├── sql_agent.py
│   │   ├── reasoning_agent.py
│   │   └── orchestrator.py
│   └── utils/
│       ├── permissions.py
│       ├── validators.py
│       └── helpers.py
├── templates/
│   ├── emails/
│   │   ├── rdo_envio.html
│   │   ├── alerta_reativo.html
│   │   └── alerta_programado.html
│   └── relatorios/
│       ├── financeiro.html
│       ├── operacional.html
│       └── tecnico.html
├── migrations/
├── tests/
├── .env
├── requirements.txt
└── rxconfig.py
CHECKLIST DE QUALIDADE PROFISSIONAL
Código
 Type hints em todas as funções

 Docstrings (Google style)

 Error handling robusto (try-except + logging)

 Validação de inputs (Pydantic)

 Tests unitários (pytest) - mínimo 70% coverage

Segurança
 SQL injection prevention (parametrized queries)

 XSS protection (sanitização HTML)

 CSRF tokens

 Rate limiting (API calls)

 Secrets em .env (nunca no código)

Performance
 Queries otimizadas (indexes, EXPLAIN ANALYZE)

 Lazy loading de dados pesados

 Pagination em listas grandes

 Cache estratégico (Redis)

 Async operations onde possível

UX
 Loading states em operações longas

 Mensagens de erro claras

 Confirmações em ações destrutivas

 Design responsivo (mobile-friendly)

 Acessibilidade (ARIA labels)

Observabilidade
 Logging estruturado (loguru)

 Metrics (Prometheus ou similar)

 Error tracking (Sentry)

 Job monitoring dashboard

PROMPT PARA CLAUDE CODE (ANTIGRAVITY)
text
CONTEXTO:
Projeto profissional Bomtempo - dashboard de gestão de obras usando Reflex (Python framework full-stack).
Cliente: empresa de construção civil.
Stack: Reflex + PostgreSQL + APScheduler + LangChain + Claude API.

OBJETIVO ATUAL: [Substituir pelo módulo específico]

ARQUITETURA:
- Backend: Reflex states + event handlers
- Database: PostgreSQL com SQLAlchemy ORM
- Auth: JWT + RBAC (roles: admin, gestor, mestre_obras, viewer)
- Jobs: APScheduler background tasks
- Email: smtplib + Jinja2 templates
- IA: Claude Sonnet 4.5 via Anthropic API
- Memory: Qdrant vector DB + PostgreSQL metadata

REQUISITOS NÃO-FUNCIONAIS:
- Type hints obrigatórios
- Error handling robusto com logging
- Validação Pydantic
- SQL parametrizado (sem injection)
- Async onde possível
- Tests unitários críticos

ESTRUTURA DE PASTAS: [colar estrutura acima]

MÓDULO A IMPLEMENTAR: [detalhar módulo específico com todas as informações acima]

ENTREGÁVEIS:
1. Models (SQLAlchemy)
2. Services (business logic)
3. Pages (Reflex components)
4. Jobs (se aplicável)
5. Templates (HTML se aplicável)
6. Migrations (Alembic)
7. Tests básicos

RESTRIÇÕES:
- Não usar ORMs alternativos (apenas SQLAlchemy)
- Não hardcode secrets (usar .env)
- Seguir padrões Reflex oficiais
- Código production-ready (não protótipo)

COMECE PELA CAMADA DE DADOS (models) E SUBA PARA UI.
RESUMO EXECUTIVO PARA IMPLEMENTAÇÃO
Módulo	Complexidade	Prazo Estimado	Dependências Críticas
Infraestrutura Base	Média	1-2 semanas	PostgreSQL, APScheduler, RBAC
RDO	Média	2-3 semanas	Infraestrutura, PDF gen, Sheets API
Relatórios	Média-Alta	2-3 semanas	Infraestrutura, Claude API
Alertas	Alta	3-4 semanas	Todos anteriores, jobs complexos
Chat Agentic	Muito Alta	4-6 semanas	Todos anteriores, Qdrant, LangChain