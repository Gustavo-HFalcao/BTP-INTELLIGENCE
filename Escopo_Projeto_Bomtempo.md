# Hub de Inteligência Executiva – Bomtempo Engenharia
**Documento de Escopo Arquitetural e Funcional do Projeto**

Este documento descreve a infraestrutura tecnológica, as integrações de dados e os módulos funcionais da plataforma de inteligência executiva em desenvolvimento. O objetivo é servir como base de contexto (prompt context) para inteligências artificiais e desenvolvedores envolvidos no projeto.

---

## 1. Visão Geral do Sistema
O sistema não é um ERP transacional clássico, mas um **Customized Management Cockpit** (Hub de Inteligência Executiva) voltado para a alta gestão e coordenação de campo da Bomtempo Engenharia. 
Seu valor principal reside em compilar fontes de dados fragmentadas (Planilhas, Pipefy, Smartsheet), digitalizar apontamentos operacionais de campo e processar e cruzar esses dados usando Inteligência Artificial para prover *insights* acionáveis em tempo real.

## 2. Stack Tecnológica Base
*   **Framework Principal:** Python + **Reflex** (Framework Full-Stack que compila Python puro estruturado para React/Next.js no frontend e FastAPI no backend).
*   **Banco de Dados & Autenticação:** **Supabase** (PostgreSQL). Utilização intensiva de RLS (Row-Level Security) para controle multi-tenant/roles da malha de usuários.
*   **Storage (Arquivos):** Supabase Storage Buckets para armazenamento de imagens de comprovantes e arquivos PDF.
*   **Inteligência Artificial:** OpenAI API (**GPT-4o e GPT-4o-Vision**). Utilizada para OCR cognitivo, análise semântica de relatórios e assistente virtual contextual.
*   **Geração de Documentos:** ReportLab (Geração de PDFs dinâmicos com tipografia e posicionamento algorítmico).
*   **Hospedagem & Deploy:** Fly.io com conteinerização Docker.

---

## 3. Módulos Core (Gestão & Analytics)

### 3.1. Dashboards Corporativos
*   **Painel Comercial:** Integração via API GraphQL com o Pipefy. Computa MRR, funil de vendas, taxas de conversão e carteira ativa.
*   **Projetos & Obras:** Conectado ao Smartsheet (e bases internas) para rastrear avanço físico-financeiro (S-Curve) de múltiplos projetos simultâneos.
*   **Financeiro:** Visão gerencial de DRE, fluxo de caixa e conciliação de contas a pagar/receber.
*   **O&M (Operação e Manutenção):** Focado no monitoramento de usinas solares. Traz kWH gerado, indicadores progressivos (acumulado M-o-M) e taxa de falhas.
*   **Customer 360 (Health Score):** Algoritmo proprietário que pondera engajamento, satisfação NPS, volume de incidentes (SLA) e status de inadimplência para gerar o "Índice de Saúde" unificado do cliente.

---

## 4. Módulos Operacionais de Campo (Field Service - Mobile Ready)

Estes módulos são operados na ponta (pelos técnicos/engenheiros) e monitorados via plataforma pela gestão.

### 4.1. RDO Digital (Relatório Diário de Obra)
Formulário digital rápido desenhado para dispositivos móveis, substituindo o papel.
*   **Apontamentos:** Permite relatar equipe alocada (mão de obra), maquinário pesado, serviços diários, materiais aplicados, condições climáticas e interrupções.
*   **Geração Automatizada de PDF:** O sistema captura o *state* da tela e renderiza um PDF profissional de múltiplas páginas com o logotipo e identidade visual corporativa da Bomtempo usando a ferramenta nativa do backend.
*   **Análise Cognitiva (IA):** Um prompt de sistema pré-lê o RDO preenchido e devolve uma avaliação gerencial automática dividida em: Resumo Executivo, Impacto no Escopo, Alertas/Riscos e Recomendações de ação para o dia seguinte.
*   **Envio Configurado:** Notifica stakeholders via E-mail anexando o ReportLab-PDF automaticamente quando submetido.

### 4.2. Reembolso de Combustível Inteligente
Módulo focado em auditar e acelerar o pedido de reembolso da frota.
*   **Submissão OCR Vision:** O solicitante envia a foto da Nota Fiscal do posto e digita os dados. O **GPT-4o Vision** lê a imagem da NF e o sistema cruza matematicamente se: Litros × Preço/L corresponde ao Total cobrado, garantindo proteção contra enganos ou fraude.
*   **Mecanica de Override:** Se a IA reprovar a nota três vezes (borrada ou errada), o sistema habilita o botão de "Forçar Envio Sob Auditoria", criando travas de governança.
*   **Anomaly Detection de Despesas:** O sistema calcula *km_driven*, eficiência (km/L) e *custo por km*, pontuando matematicamente o Desvio (%) deste motorista específico contra o Histórico dele mesmo e contra a Média da Frota global da empresa no Supabase.

---

## 5. Módulos de Inteligência e Automação Expandidos

### 5.1. IA Consultor Contextual (Hub)
*   **Agente RAG local:** Um assistente Flutuante (ChatBot) disponível dentro da aplicação preenchido ativamente com o "Contexto da Sessão" do usuário. Quando o usuário clica em "Analisar Página", o backend puxa DataFrames limpos do Supabase relativos à aba aberta e ejeta no prompt da OpenAI, respondendo dúvidas cruzadas (Exemplo: *"Com base nos RDOs recentes listados, porque a obra X atrasou ontem?"*).

### 5.2. Módulo de Relatórios (Reports Builder)
*   **Objetivo:** Permitir ao usuário administrador compilar "Kits de Resumo" juntando peças. Exemplo: Baixar um PDF Dossiê que tenha os KPIs Financeiros + Uma tabela consolidada dos 5 RDOs críticos da semana + O Gráfico de O&M do mês.
*   **Robustez:** Engine centralizada via ReportLab ou motor headless capaz de capturar charts do dashboard Reflex e encapsulá-los via *buffer* de memória em relatórios de alto nível enviados automaticamente na sexta-feira à tarde.

### 5.3. Módulo de Alertas Automatizados (Anomaly / Trigger Motor)
*   **Objetivo:** Um painel de vigília (Watchdog). Em vez do gestor precisar abrir o dashboard de Reembolso para ver desvios, a plataforma fará o trabalho reverso, enviando alertas em tempo real ("Push").
*   **Robustez:** 
    *   **Regras de Negócio Hardcoded/Dinâmicas:** Triggers ativos quando (a) Um RDO aponta status de "Houve Acidente" ou Clima Crítico; (b) Reembolso marca -30% de eficiência de frota (Roubo de carga/Vazamento); (c) Health Score de um grande cliente cai abaixo de 50 pontos.
    *   **Notificações:** Integração multi-canal (Envio de email de ALERTA VERMELHO formatado usando SMTP corporativo ou possivelmente Webhook para Microsoft Teams/Slack do PMO da diretoria).

---

## Conclusão da Entrega
Com a adição orgânica dos módulos de **Relatório** e **Alerta**, a aplicação sobe do patamar de um dashboard puramente passivo (onde o humano escava o dado) para uma torre de controle pró-ativa inteligente. Onde a plataforma lê a operação diária no nível do solo (via RDO Mobile e OCR de Notas Fiscais) e eleva a anomalia (via Alertas/IA) à C-Level de forma destilada, mitigando riscos de estouro de escopo e atraso financeiro antes que eles contaminem os ciclos de fechamento.
