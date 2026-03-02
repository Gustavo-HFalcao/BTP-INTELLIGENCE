# Documentação de Cálculos e Métricas - Bomtempo Dashboard v7.1

Este documento detalha todos os cálculos, fontes de dados e lógicas de negócios implementadas no Dashboard Bomtempo.

## 1. Fonte de Dados

O sistema utiliza arquivos Excel localizados na pasta `data/` (ou `data/raw`) como fonte única de verdade.
A classe `DataLoader` (`bomtempo/core/data_loader.py`) carrega e normaliza estes dados.

| Arquivo Original | Nome Interno | Descrição |
| :--- | :--- | :--- |
| `dContratos.xlsx` | `contratos` | Lista de contratos, clientes e status. |
| `Projeto.xlsx` | `projeto` | Cronogramas detalhados, atividades e físico. |
| `Obras.xlsx` | `obras` | Acompanhamento de campo, avanço físico e medições. |
| `Financeiro.xlsx` | `financeiro` | Valores contratados, medidos e cockpits de custo. |
| `O&M.xlsx` | `om` | Geração de energia, performance e faturamento O&M. |

> **Nota:** O sistema normaliza os nomes das colunas para *snake_case* (ex: "Valor Contratado" vira `valor_contratado`) para uso no código.

---

## 2. Visão Geral (`index.py`)

Painel executivo com métricas consolidadas de todas as obras e contratos.

### KPI Cards

#### **a) Receita Total**
*   **Cálculo:** Soma da coluna `valor_contratado` de todos os contratos.
    *   *Lógica:* `GlobalState.valor_tcv = sum(contratos['valor_contratado'])`
    *   *Formatação:* Arredondado para Milhões (M) ou Milhares (k).
*   **Fonte:** `dContratos.xlsx`. Se não houver coluna de valor, o sistema tenta calcular somando os itens do `Financeiro.xlsx` vinculados ao contrato.
*   **O que afeta:** Novos contratos ou aditivos financeiros.

#### **b) Contratos Ativos**
*   **Cálculo:** Contagem de linhas na planilha `contratos` onde o status é **"Em Execução"**.
*   **Fonte:** `dContratos.xlsx` (Coluna Status).
*   **O que afeta:** Mudança de status na planilha.

#### **c) Velocidade Média**
*   **Cálculo:** Média aritmética do percentual de conclusão (`conclusao_pct`) de todos os projetos ativos.
    *   *Lógica:* `mean(projetos['conclusao_pct'])`
*   **Fonte:** `Projeto.xlsx` (Coluna Conclusão).
*   **O que afeta:** Avanço nas atividades do cronograma.

#### **d) Health Score**
*   **Cálculo:** **Estático (Hardcoded)**.
    *   *Valor Atual:* "94.2".
*   **Nota:** Esta métrica está fixada no código (`index.py`) e não reflete dados reais no momento. Deve ser implementada futuramente com lógica de risco.

### Gráficos

#### **Alocação de Volume (Gráfico de Barras)**
*   **Visualização:** Faturamento total agrupado por Cliente.
*   **Cálculo:** Agrupamento de `contratos` por `cliente` somando `valor_contratado`.
*   **Fonte:** `dContratos.xlsx`.

#### **Status do Portfolio (Gráfico de Rosca)**
*   **Visualização:** Quantidade de contratos por Status.
*   **Cálculo:** Contagem simples (`value_counts`) da coluna `status`.
*   **Fonte:** `dContratos.xlsx`.

---

## 3. Financeiro (`financeiro.py`)

Controle de custos, medições e margem (saldo).

### KPI Cards

#### **a) Total Contratado**
*   **Cálculo:** Soma de `servico_contratado` + `material_contratado`.
*   **Filtros:** Afetado pelo filtro de projeto selecionado no topo da página.
*   **Fonte:** `Financeiro.xlsx`.

#### **b) Total Medido (Executado)**
*   **Cálculo:** Soma de `servico_realizado` + `material_realizado`.
*   **Fonte:** `Financeiro.xlsx`.

#### **c) Saldo à Medir (Pendente)**
*   **Cálculo:** `Total Contratado` - `Total Medido`.
*   **Significado:** Valor financeiro que ainda falta ser medido/executado.
*   **Nota:** No código a variável chama-se `margem_bruta`, mas no contexto do dashboard representa o saldo pendente do contrato.

### Gráficos e Tabelas

#### **Custos por Centro (Cockpit)**
*   **Visualização:** Comparativo Contratado x Realizado por centro de custo (Cockpit).
*   **Fonte:** `Financeiro.xlsx` (Agrupado pela coluna `Cockpit`).
*   **Cálculo da Margem % (Tabela):**
    *   `(Total Contratado - Total Realizado) / Total Contratado`
    *   Representa o % do orçamento que ainda não foi consumido/medido.

---

## 4. Obras (`obras.py`)

Acompanhamento físico e operacional.

### Filtros
*   **Seleção de Contrato:** Dropdown que filtra **toda** a página para um contrato específico.

### Painel de Detalhes
*   **Dados:** Cliente, OS, Potência, Prazo.
*   **Cálculo do Prazo (Dias):** Diferença entre a maior data e a menor data encontradas na planilha de obras para aquele contrato.
    *   `max(data) - min(data)` dos registros de obra.
*   **Fonte:** `dContratos.xlsx` e `Obras.xlsx`.

### Progresso por Disciplina
*   **Visualização:** Comparação entre % Previsto e % Realizado por categoria (Civil, Elétrica, etc.).
*   **Cálculo:** Último registro (por data) ou média dos registros de cada categoria.
*   **Fonte:** `Obras.xlsx` (Colunas `Categoria`, `Previsto`, `Realizado`).
*   **Alerta:** Se `Realizado < Previsto`, exibe "Atraso detectado" em vermelho.

### Avanço Físico Global (Gauge)
*   **Cálculo:** **Estático (Hardcoded)** na visualização.
    *   *Valor Exibido:* "34%".
    *   *Nota:* Existe uma variável `GlobalState.avanco_fisico_geral` calculada, mas o componente visual (`gauge_component` em `obras.py`) está com o valor fixado no HTML SVG.
    *   *Recomendação:* Atualizar o componente para usar `{GlobalState.avanco_fisico_geral}`.

### Alertas Críticos
*   **Conteúdo:** **Estático (Hardcoded)**.
    *   Exibe alertas fixos de "Atraso: Módulo Solar" e "Logística Inversor".
    *   Não reflete dados reais da planilha no momento.

---

## 5. Projetos (`projetos.py`)

Cronograma detalhado (Gantt simplificado e Lista).

### Lista de Projetos
*   **Progresso Global:** Média do % de conclusão de todas as atividades do contrato.
    *   `GlobalState.filtered_contratos` enriquece a lista de contratos calculando a média de `conclusao_pct` da planilha `Projeto.xlsx`.

### Detalhe do Projeto (Timeline)
*   **Atividades:** Lista as atividades do contrato selecionado.
*   **Barra de Progresso:** Visualiza `conclusao_pct` (0 a 100).
*   **Caminho Crítico:** Se a coluna `Critico` for "Sim", a barra fica vermelha e exibe um alerta.
*   **Filtro de Fase:** Filtra as atividades por fase (ex: Engenharia, Suprimentos, Obra).

---

## 6. O&M (`om.py`)

Operação e Manutenção de usinas.

### KPI Cards

#### **a) Energia Injetada**
*   **Cálculo:** Soma da coluna `energia_injetada_kwh`.
*   **Fonte:** `O&M.xlsx`.

#### **b) Performance**
*   **Cálculo:** `(Energia Injetada / Geração Prevista) * 100`.
*   **Fonte:** `O&M.xlsx`.

#### **c) Faturamento Líquido**
*   **Cálculo:** Soma da coluna `faturamento_liquido`.
*   **Fonte:** `O&M.xlsx`.

### Gráficos
*   **Performance de Geração:** Gráfico composto.
    *   *Linha:* Geração Prevista vs Injetada.
    *   *Barra:* Acumulado KWh.
    *   Agrupado por `Mes/Ano`.

---

## 7. Analytics (`analytics.py`) e Chat IA

*   **Analytics:** Métricas calculadas como "Risco de Churn" (Baseado em status "Em Risco") e "Atraso Médio" (Diferença entre Realizado e Previsto nas obras).
*   **Chat IA:** Simulação de chat (`chat_ia.py`).
    *   Lógica simples de palavras-chave (`if "faturamento" in question...`).
    *   Não utiliza LLM real, apenas responde com dados formatados do `GlobalState`.
