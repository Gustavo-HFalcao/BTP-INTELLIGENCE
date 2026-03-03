# ESTRATÉGIA DE PRODUTO 2026
## Bomtempo Intelligence — Do Diamante Bruto ao SaaS B2B Recorrente

> **Consultor:** Análise Estratégica de Produto & Posicionamento SaaS B2B  
> **Data:** Março 2026  
> **Versão:** 1.0 — Documento Fundacional

---

## 1. EXECUTIVE SUMMARY

O **Bomtempo Intelligence** é uma plataforma de gestão operacional e financeira construída sobre um stack moderno (Python/Reflex, Supabase, OpenAI). O produto resolve uma dor real e cara para empresas de engenharia e construção civil brasileiras: **a gestão fragmentada de obras, contratos e medições sem visibilidade consolidada em tempo real**.

O produto existe. O problema existe. A oportunidade é real.

**O que está faltando é a embalagem, o foco e o go-to-market.**

O diagnóstico honesto: o produto já contém funcionalidades que empresas pagam caro em ferramentas como MS Project + SAP + Totvs separadamente. O risco atual é morrer como software interno antes de virar produto. O plano a seguir define o caminho de R$ 0 → R$ 50k MRR em 12 meses com os ativos já existentes.

**Os 3 próximos passos imediatos desta semana:**
1. Fechar 1 cliente piloto para validação real (não precisa pagar ainda)
2. Listar e mapear os bugs críticos do fluxo de importação de dados
3. Definir o "Módulo Troféu" — a feature que vai ser o argumento de venda número 1

---

## 2. INVENTÁRIO E DIAGNÓSTICO DE FEATURES

### 2.1 Mapeamento Técnico → Dor do Empresário

| # | Módulo | O Que Faz | Dor Resolvida | Maturidade | Valor Percebido |
|---|--------|-----------|---------------|------------|-----------------|
| 1 | **Visão Geral (Dashboard)** | KPIs de receita, contratos ativos, velocidade operacional, gráficos de portfólio | "Não sei como está minha empresa hoje" | **Funcional** | **Alto** |
| 2 | **Financeiro** | Curva S, medições por cockpit, margem%, tabela detalhada por marco | "Não sei se estou ganhando ou perdendo em cada obra" | **Funcional** | **Alto** |
| 3 | **Field Operations (Obras)** | Progress por disciplina, gauge de avanço físico, widget de clima, alertas críticos | "Não sei o que está acontecendo no campo hoje" | **Funcional** | **Alto** |
| 4 | **Gestão de Projetos** | Cards de contratos, timeline de atividades, caminho crítico, filtro por fase | "Não sei quais atividades estão atrasando minha obra" | **Funcional** | **Alto** |
| 5 | **RDO — Formulário** | Registro diário de obra: clima, turno, MO, equipamentos, atividades, materiais, fotos, email automático | "Meu encarregado não manda relatório, ou manda no WhatsApp e eu perco" | **Polido** | **Muito Alto** |
| 6 | **RDO — Dashboard Analytics** | KPIs de RDOs, gráficos por dia, clima, MO por contrato, materiais, tabela histórica | "Não tenho visibilidade do que aconteceu em campo nos últimos 30 dias" | **Funcional** | **Muito Alto** |
| 7 | **RDO — Histórico** | Listagem temporal de RDOs com PDF para download | "Preciso de prova do que foi feito na obra para cobrar medição" | **Funcional** | **Alto** |
| 8 | **Reembolso (Combustível)** | Fluxo de solicitação de reembolso de combustível com PDF + email | "Perco tempo com planilha de reembolso e ainda erro o cálculo" | **Polido** | **Médio** |
| 9 | **Chat IA** | Chat conversacional com contexto das páginas do dashboard, análise por IA | "Não entendo os números, quero que alguém me explique o que tá errado" | **Funcional** | **Muito Alto** |
| 10 | **Voice Chat** | Chat por voz com TTS e STT | Acessibilidade e uso hands-free no campo | **Bruto** | **Médio** |
| 11 | **Editor de Dados** | Grid tipo Excel para edição direta de tabelas Supabase com import/export XLSX | Admin pode corrigir dados sem acessar o banco diretamente | **Bruto** (bugs críticos) | **Baixo (interno)** |
| 12 | **Previsões** | Página de previsões financeiras | Planejamento forward-looking | **Bruto** (placeholder) | **Alto (potencial)** |
| 13 | **OM (Ordens de Manutenção)** | Módulo de ordens de manutenção | "Não controlo minhas OMs de forma organizada" | **Bruto** | **Médio** |

### 2.2 Gaps Críticos

| Gap | Impacto | Como Resolver com Stack Atual |
|-----|---------|-------------------------------|
| **Autenticação multi-tenant real** | Bloqueador de venda | Supabase RLS (Row Level Security) por `empresa_id` |
| **Onboarding de dados** | Bloqueador de escala | Assistente guiado de importação + templates Excel pré-formatados |
| **Alertas proativos (push/email)** | Diferencial | Cron job Python + SMTP já existente em `email_service.py` |
| **Módulo de Previsões** está vazio | Feature crucial | IA generativa + dados históricos do Supabase |
| **Bug crítico no Editor de Dados** | Impede uso interno | Fix da serialização UUID → Supabase REST |
| **Mobile** (apenas chat mobile) | Limita adoção campo | PWA ou React Native — campo só usa celular |
| **Precificação visível** (sem paywall) | Sem receita | Planos definidos + Stripe integration |
| **Relatório executivo exportável** | Demanda enterprise | PDF automático do dashboard via weasyprint/wkhtmltopdf | -

---

## 3. TABELA DE REPOSICIONAMENTO DE MÓDULOS

| Módulo Atual | Nome Técnico | Renomear Para | Proposta de Valor (Empresário) |
|---|---|---|---|
| Dashboard / Visão Geral | `index.py` | **Centro de Comando** | "Em 10 segundos você sabe se sua empresa está saudável hoje" |
| Financeiro | `financeiro.py` | **Raio-X Financeiro** | "Você vê onde cada real está sendo gasto — e recupera margem perdida" |
| Field Operations | `obras.py` | **Situação do Campo** | "Você sabe o que está acontecendo na obra agora, mesmo sem ligar para o encarregado" |
| Gestão de Projetos | `projetos.py` | **Painel de Contratos** | "Você decide quais obras priorizar com base em dados, não em intuição" |
| RDO Formulário | `rdo_form.py` | **Diário de Campo Digital** | "O encarregado preenche em 5 minutos no celular. Você recebe no mesmo instante." |
| RDO Dashboard | `rdo_dashboard.py` | **Inteligência de Campo** | "Você identifica gargalos, atrasos e riscos antes que virem problema" |
| Reembolso Combustível | `reembolso_form.py` | **Controle de Despesas** | "Zero planilha, zero erro. Aprovação em 1 clique, comprovante automático." |
| Chat IA | `chat_ia.py` | **Consultor 24h** | "Faça qualquer pergunta sobre sua empresa e receba uma resposta direta com base nos seus dados" |
| Previsões | `previsoes.py` | **Projetor de Receita** | "Veja quanto você vai faturar no próximo trimestre antes que aconteça" |
| Editor de Dados | `editar_dados.py` | *(Módulo Interno)* | *(Não expor ao cliente final — ferramenta de admin)* |

---

## 4. ICP DETALHADO (IDEAL CUSTOMER PROFILE)

### Perfil da Empresa
- **Setor:** Construção civil, energia solar, infraestrutura, saneamento
- **Porte:** 10-150 funcionários diretos
- **Faturamento:** R$ 3M – R$ 50M anuais
- **Número de Obras simultâneas:** 2 a 15
- **Localização:** Brasil (inicialmente Sul/Sudeste onde há maior concentração de contratos de energia solar e infraestrutura)

### Perfil do Decisor
- **Cargo:** Diretor/CEO, Gerente de Obras, CFO de PME
- **Idade:** 35-55 anos
- **Dor:** Vive apagando incêndio. Toma decisão por feeling ou por planilha desatualizada
- **Sonho:** Ter o controle que grandes construtoras têm, sem precisar de 10 funcionários de backoffice
- **Tech-savviness:** Usa WhatsApp Business, tenta usar Excel, resiste mas quer praticidade

### Principais Dores Hoje
1. **"Não sei o status real das minhas obras sem ligar para o encarregado"** → Field Operations + RDO resolvem isso
2. **"Minha medição demora 15 dias para fechar porque ninguém sabe o que foi feito"** → RDO Histórico + Financeiro resolvem isso
3. **"Perco margem e nunca sei onde"** → Raio-X Financeiro + Chat IA resolvem isso
4. **"Minha equipe perde tempo com planilhas e WhatsApp"** → Formulário de RDO + Reembolso Digital resolvem isso
5. **"Já tentei outros sistemas mas são complexos demais"** → Design do produto já é limpo — mantenha assim

### Como o Cliente Mede Sucesso
- `Tempo de fechamento de medição` reduzido de 15 dias → 3 dias
- `Horas de reunião de alinhamento` reduzidas (tem o dashboard para isso)
- `Perdas por atraso identificadas` antes de virarem aditivo de contrato
- `Sensação de controle` sem precisar ligar para o campo

### Objeções Prováveis e Respostas
| Objeção | Resposta do Produto |
|---------|---------------------|
| "Já uso Excel" | Excel não te avisa quando uma obra atrasa. O produto sim. |
| "É difícil de usar?" | O encarregado preenche o RDO no celular em 5 minutos. |
| "É caro?" | Quanto você perde por mês por não saber o status das obras? |
| "E meus dados?" | Supabase brasileiro, backup automático, você é dono dos dados. |
| "Já tentei outro sistema" | Mostre o dashboard. A pergunta vai mudar para "quando começo?" |

---

## 5. ROADMAP 2026

### Q1 2026 (Jan-Mar) — VALIDAR E ESTABILIZAR

**Prioridade:** Fechar bugs críticos, validar com cliente piloto real.

- [ ] Fix crítico: Bug de bulk save no Editor de Dados (UUID + tipagem Postgres)
- [ ] Definir 1 cliente piloto de construção/energia solar no Brasil
- [ ] Entrevistas com 5 gestores de obra (roteiro: "Me conta como você controla suas obras hoje")
- [ ] Mapear formato de planilhas que os clientes já usam — criar templates Excel compatíveis
- [ ] Feature: Alertas automáticos por email quando uma disciplina atrasa > X dias

**Perguntas para o empresário (entrevista):**
1. Quantas obras você gerencia simultaneamente?
2. Como você fica sabendo do andamento da obra hoje?
3. Quanto tempo leva para fechar a medição mensal?
4. O que você faria diferente se tivesse essa informação em tempo real?
5. Quanto você pagaria por uma ferramenta que resolva isso?

**Análise de Concorrentes Diretos:**

| Concorrente | Preço | O que entrega | Onde falha |
|-------------|-------|--------------|------------|
| **SIENGE** | R$ 800-3.000/mês | ERP completo para construção | Complexo, caro, onboarding de meses |
| **GooConstruct** | R$ 299-799/mês | Gestão de obras simplificada | Pouca inteligência analítica, sem IA |
| **Volare (Totvs)** | R$ 1.500+/mês | ERP construção + financeiro | Legado, interface antiga, treinamento extenso |
| **Bomtempo Intelligence** | *A definir* | BI + Campo + IA em 1 lugar | *(Ainda sem produto packaged)* |

**Gap de mercado claro:** Ninguém entrega **BI visual + diário de campo digital + IA conversacional** em uma interface moderna e acessível para PMEs.

---

### Q2 2026 (Abr-Jun) — LAPIDAR O DIAMANTE

**Prioridade:** As 3 features com maior WOW imediato.

#### Feature WOW #1: RDO → Medição Automática
> Quando o encarregado registra o RDO, o sistema calcula automaticamente o % de medição elegível e gera um pré-relatório de medição para aprovação do gestor.
- Impacto: Reduz fechamento de medição de 15 → 3 dias
- Stack: Lógica Python + Supabase + PDF existente

#### Feature WOW #2: Alerta de Margem em Risco
> Se a diferença entre Previsto e Realizado de qualquer cockpit financeiro ultrapassar X%, o gestor recebe um alerta no email e no dashboard.
- Impacto: "Você descobre o buraco antes de cair nele"
- Stack: Cron job Python + email_service.py já existe

#### Feature WOW #3: Chat IA com Contexto Total
> O consultor IA responde com base nos dados reais do cliente: "Qual obra está em atraso?" → resposta com dado real, não genérico.
- Impacto: Justifica assinatura de tier superior
- Stack: `ai_context.py` já existe, refinamento de prompts

**Reformulação de UX/Q2:**
- Adicionar página de boas-vindas/onboarding para novos clientes
- Simplificar o menu lateral para máx 5 itens visíveis (ocultar admin)
- Adicionar tooltips contextuais nas métricas financeiras
- Mobile: versão responsiva do RDO Form (já existe no `mobile_chat.py`, expandir para RDO)

---

### Q3 2026 (Jul-Set) — CRESCIMENTO E RECEITA

#### Modelo de Precificação Sugerido

| Plano | Preço/mês | O que inclui | ICP |
|-------|-----------|-------------|-----|
| **Operacional** | R$ 397 | Dashboard + RDO + Campo (até 5 obras) | Empreiteiras pequenas |
| **Gestão** | R$ 797 | Tudo + Financeiro + Chat IA + Reembolso (até 15 obras) | Construtoras médias |
| **Empresa** | R$ 1.497 | Tudo + Múltiplos usuários + API + SLA | Empresas com 10+ obras |

> **Benchmark:** GooConstruct cobra R$ 299-799. SIENGE cobra R$ 800-3.000. A faixa R$ 397-797 com diferencial de IA é defensável.

#### Estratégia de Aquisição

| Canal | Tática | CAC Estimado |
|-------|--------|-------------|
| **LinkedIn** | Conteúdo orgânico: "Vídeos de gestão de obra" + casos reais | R$ 0-200 |
| **Indicação** | Cliente piloto → 30% desconto por indicação válida | R$ 0 |
| **Associações setoriais** | CBIC, SINDUSCON, ABSOLAR — parceria ou presença em evento | R$ 500-2.000 |
| **Google Ads** | "software gestão de obras", "RDO digital" | R$ 50-150/lead |
| **WhatsApp + Cold Outreach** | Lista de construtoras locais | R$ 0-50 |

---

### Q4 2026 (Out-Dez) — ESCALA E RETENÇÃO

**Expansão de Módulos com Base em Feedback:**
- Módulo de Orçamento e BDI (integração com medições)
- Integração com ERPs (SAP, Totvs via API)
- App mobile nativo para encarregados de campo
- Relatórios executivos automáticos (PDF semanal/mensal no email)

**Métricas de Sucesso do Cliente (Health Score):**
- `RDOs preenchidos / dias de obra` > 80% = cliente saudável
- Login ativo > 3x/semana = cliente engajado
- Fechamento de medição usando o sistema = cliente retido

**Estratégia de Upsell:**
- Cliente Operacional → ofertarChat IA após 45 dias
- Cliente Gestão → oferta de módulo Previsões após 90 dias
- Cliente Empresa → oferta de integração ERP após 6 meses

---

## 6. PROJEÇÃO DE RECEITA

### Cenários de MRR (Receita Mensal Recorrente)

| Período | Clientes | Mix de Planos | MRR | ARR |
|---------|----------|--------------|-----|-----|
| **Q1 2026** | 0-2 pilotos | Gratuito | R$ 0 | R$ 0 |
| **Q2 2026** | 5-10 clientes | 60% Operacional, 40% Gestão | R$ 4.000-7.000 | R$ 48k-84k |
| **Q3 2026** — Conservador | 15 clientes | Mix | R$ 8.000 | R$ 96k |
| **Q3 2026** — Realista | 25 clientes | Mix | R$ 15.000 | R$ 180k |
| **Q3 2026** — Otimista | 40 clientes | Mix c/ Empresa | R$ 28.000 | R$ 336k |
| **Q4 2026** — Conservador | 25 clientes | Mix | R$ 12.000 | R$ 144k |
| **Q4 2026** — Realista | 50 clientes | Mix | R$ 30.000 | R$ 360k |
| **Q4 2026** — Otimista | 80 clientes | Mix | R$ 55.000 | R$ 660k |

> **Premissas:** Churn de 5%/mês, CAC médio R$ 400, LTV mínimo 12 meses (pressupõe produto estável e onboarding eficiente).

---

## 7. PRÓXIMOS 3 PASSOS IMEDIATOS (ESTA SEMANA)

### Passo 1 — Fix Técnico (hoje/amanhã)
Resolver o bug de commit do Editor de Dados (UUID + tipagem PostgreSQL).  
**Por que esta semana:** Impede a importação de dados por admin. Sem isso, onboarding de cliente é manual.

### Passo 2 — Identificar o Cliente Piloto (até sexta)
Escolher 1 empresa de construção ou energia solar de relacionamento próximo.  
Proposta: usar o produto gratuitamente por 60 dias em troca de feedback semanal de 30 minutos.  
**Meta da reunião:** Entender quais módulos resolvem a maior dor deles imediatamente.

### Passo 3 — Definir o "Módulo Troféu" (até domingo)
Com base na estrutura deste documento, decidir qual feature vai ser a **âncora de venda**:
- **Candidato mais forte:** RDO Digital (Diário de Campo) → é concreto, resolve dor imediata, competitor fraco aqui
- **Segundo candidato:** Chat IA com dados reais → diferencial de mercado ainda inexplorado

Documentar em 1 parágrafo: "O Bomtempo resolve [dor específica] para [perfil de empresa] e a prova é [feature específica]. O cliente sabe que funciona porque [resultado mensurável]."

---

## APÊNDICE — Stack Técnico Atual

| Componente | Tecnologia | Status |
|------------|-----------|--------|
| Frontend/Backend | Python + Reflex 0.8.x | Produção |
| Banco de Dados | Supabase (PostgreSQL) | Produção |
| IA/Chat | OpenAI GPT (streaming) | Funcional |
| Email | SMTP customizado (`email_service.py`) | Funcional |
| PDF | WeasyPrint/fpdf (`pdf_utils.py`) | Funcional |
| Clima | WeatherAPI (`weather_api.py`) | Funcional |
| TTS/STT | OpenAI Whisper + TTS (`tts_service.py`) | Bruto |
| Hosting | Reflex Deploy (cloud) | Ativo |

---

*Documento gerado em Março 2026. Revisar trimestralmente com base em feedback de clientes reais.*
