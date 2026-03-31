# UP-CRONOGRAMA — Roadmap para Módulo de Cronograma World-Class

> **Avaliação em:** 2026-03-31
> **Status atual:** ~62% do planejamento implementado — motor base sólido, lacunas críticas no controle avançado

---

## 1. O que está implementado hoje

### ✅ Motor base (Fase 1 — COMPLETO)
- Hierarquia macro/micro com `parent_id`, `nivel`, `peso_pct`
- Dependência Finish-to-Start via `dependencia_id` (UUID) — auto-preenche início ao selecionar
- `_add_working_days(start_iso, days)` — cálculo de dias úteis Mon-Fri
- `_recalc_macro_dates()` — recalcula datas da macro a partir das micros filhas
- Validação de peso: soma dos pesos das micros ≤ 100% antes de salvar
- Gantt visual com barras por fase_macro, detecção de overdue, barra EAC em roxo pontilhado

### ✅ Medição real (Fase 2 — COMPLETO)
- `total_qty`, `exec_qty`, `unidade` em `hub_atividades`
- RDO: campo `producao_dia` acumula em `exec_qty`, auto-calcula % se `total_qty > 0`
- `hub_atividade_historico`: `producao_dia`, `exec_qty_novo`, `total_qty`, `unidade` gravados por submit
- `status_atividade` com 8 estados; transição automática via RDO: `nao_iniciada → em_execucao → concluida`
- Atividades `cancelada`/`bloqueada` excluídas do dropdown do RDO

### ✅ Previsão / Forecast (Fase 3 — COMPLETO)
- `cron_forecast_rows`: prod_planejada_dia, prod_real_media, desvio_pct, tendencia, data_fim_prevista (EAC), desvio_dias
- `cron_kpi_dashboard`: programado hoje vs realizado, desvio pp, em_risco, atrasadas, adiantadas, produção total
- Painel `_cron_kpi_panel()` com grid uniforme de 6 KPIs
- Painel `_cron_forecast_panel()` com tabela de produtividade alinhada
- Gantt com barra EAC em dashed purple

### ✅ IA + Auditoria (Fase 4 — COMPLETO)
- `_log_schedule_diff_async()` — registra diff completo por campo em `hub_cronograma_log`
- 14 campos auditados por alteração (inicio, termino, pct, responsavel, peso, critico, etc.)
- AI impact note em background → atualiza `hub_timeline`
- Import via IA: upload Excel/CSV/PDF → parse → IA extrai JSON → preview dialog → `confirm_import_cronograma`
- Doc awareness no chatbot: lê conteúdo real de PDFs/DOCX do Supabase Storage
- Análise de impacto climático no Gantt

---

## 2. Matriz de Lacunas — O que falta

> **Legenda:** 🔴 Crítico | 🟠 Alto | 🟡 Médio | 🟢 Baixo
> **Complexidade:** ★ Simples | ★★ Médio | ★★★ Complexo | ★★★★ Muito complexo

| # | Feature | Prioridade | Complexidade | Impacto Gerencial | Observações |
|---|---------|-----------|-------------|------------------|-------------|
| **A1** | Cascade recalculation (efeito dominó nas dependências) | 🔴 | ★★★ | Altíssimo — sem isso, mover uma atividade não propaga para as sucessoras | Loop sobre dependentes, recalc em profundidade |
| **A2** | Cycle detection nas dependências | 🔴 | ★★ | Crítico de integridade — sem isso, pode travar o sistema | DFS antes de salvar dependência |
| **A3** | Baseline freeze + versionamento | 🔴 | ★★★ | Fundamental para governança — sem isso não há "programado vs realizado" real | Tabela `hub_cronograma_versao` já existe no schema; falta UI e lógica de bloqueio |
| **A4** | Lag days nas dependências | 🟠 | ★★ | Alto — obras reais têm espera entre atividades (cura de concreto, etc.) | Campo `lag_dias_uteis` na tabela + lógica no setter |
| **A5** | Tipos de dependência (FS, SS, FF, SF) | 🟠 | ★★★ | Alto — SS (start-to-start) é muito usado em obras paralelas | Enum + lógica de cálculo de data por tipo |
| **A6** | Caminho crítico automático | 🟠 | ★★★★ | Altíssimo — identifica quais atividades não têm folga, direcionando atenção | CPM (Critical Path Method) sobre o grafo de dependências |
| **A7** | Cenário de reajuste IA (gerar + aprovar) | 🟠 | ★★★★ | Alto — diferencial competitivo, mas complexo de implementar bem | IA gera `hub_cronograma_versao` com `tipo=cenario_ia`; UI para aprovar/rejeitar |
| **A8** | Gantt multi-camada com toggle | 🟡 | ★★★ | Alto visual — comparar programado vs realizado vs previsto no mesmo Gantt | Barra realizada (verde) + barra cenário (azul) + toggle UI |
| **A9** | RDO approval flow integrado | 🟡 | ★★ | Médio — hoje RDO enviado acumula direto; deveria esperar aprovação | Flag `status_rdo=aprovado` antes de acumular exec_qty |
| **A10** | Média móvel de produtividade | 🟡 | ★★ | Médio — evita distorção por dias atípicos na previsão | Janela configurável (ex: últimos 7 dias) no `cron_forecast_rows` |
| **A11** | Filtros Gantt por frente/equipe | 🟡 | ★ | Médio — gestores por frente só querem ver "o seu" | `frente_servico` já existe no schema; só falta filtro na UI |
| **A12** | Lookahead 2 semanas | 🟡 | ★★ | Médio — visão operacional do que vem a seguir | Vista filtrada do Gantt com janela de 14 dias úteis à frente |
| **A13** | Validação: soma pesos = exatamente 100% | 🟡 | ★ | Médio — hoje bloqueia se > 100%, mas deveria exigir = 100% para publicar | Adicionar validação "publicar cronograma" |
| **A14** | Distribuição de peso automática | 🟢 | ★★ | Baixo — proporcional a qty ou custo | Botão "distribuir proporcionalmente" no dialog da micro |
| **A15** | Lookahead por equipe / frente | 🟢 | ★★ | Baixo | Extensão de A11 + A12 |
| **A16** | Configuração de calendário da obra | 🟢 | ★★★ | Médio a longo prazo — feriados regionais, turnos, exceções | Hoje usa Mon-Fri genérico; falta tabela de calendário por obra |
| **A17** | Múltiplas predecessoras por atividade | 🟠 | ★★★ | Alto — atividade que só inicia quando 2 outras terminam | Tabela de dependências N:N em vez de `dependencia_id` (1:1 atual) |
| **A18** | Edição inline no Gantt | 🟢 | ★★★ | Médio — UX premium | Drag de barra = alterar data; resize = alterar duração |
| **A19** | Exportar cronograma (PDF / Excel) | 🟢 | ★★ | Baixo-Médio | Usando Playwright ou openpyxl |
| **A20** | Notificação proativa de desvio | 🟡 | ★★ | Médio — alertas automáticos quando atividade atrasa N dias | Integrar com módulo de alertas existente |

---

## 3. Análise crítica do que temos vs o spec

### O que o spec pede e nós temos diferente

| Item do Spec | Nossa impl | Gap real |
|---|---|---|
| "Macroatividade derivada das micros, nunca controlada manualmente" | ✅ Parcial — `_recalc_macro_dates` recalcula após salvar micro | ❌ Sem cascade automático: alterar uma micro não propaga para as dependentes da macro |
| "Dependência com tipo FS/SS/FF/SF + lag" | ✅ FS implícito | ❌ Sem tipos alternativos, sem lag |
| "Múltiplas predecessoras" | ❌ | Campo `dependencia_id` é 1:1 — máximo 1 predecessora |
| "Baseline congelada + cenário IA separado" | Schema OK | ❌ Sem UI, sem lógica de freeze, sem comparação baseline vs atual |
| "RDO só acumula após aprovação" | ❌ | Acumula no submit direto |
| "Produtividade com mínimo de dias/% para prever" | ❌ | Sem threshold configurável |
| "Proibir ciclos de dependência" | ❌ | Sem validação |
| "Caminho crítico automático" | ❌ | Só flag manual `critico=true` |

### O que temos que o spec não detalha mas é diferencial

- **Análise de impacto climático** (Windy API) no Gantt
- **Doc awareness real** no chatbot (lê conteúdo do PDF, não só metadados)
- **Audit log granular** por campo (`hub_cronograma_log`)
- **Timeline visual** com eventos, custos e documentos no mesmo feed
- **Import assistido por IA** com preview/aprovação por item

---

## 4. Recomendação de execução — próximas fases

### Fase 5 — Integridade do grafo (2-3 sessões)
**Por que agora:** sem isso, o módulo não é confiável para obras reais.

1. **[A2] Cycle detection** — DFS antes de salvar dependência. Simples, crítico.
2. **[A17] Múltiplas predecessoras** — Migrar `dependencia_id` (1:1) para tabela `hub_atividade_dependencias` (N:N)
3. **[A1] Cascade recalculation** — Ao salvar uma atividade, propagar datas para todos os dependentes downstream
4. **[A4] Lag days** — Adicionar `lag_dias` na tabela de dependências + cálculo

### Fase 6 — Baseline e governança (1-2 sessões)
**Por que agora:** sem baseline, não há comparação "programado vs realizado" real — tudo é apenas "atual".

1. **[A3] Baseline freeze** — UI para "congelar cronograma" → `hub_cronograma_versao` com `tipo=baseline_inicial`
2. **Gantt comparativo** — Barra cinza = baseline; barra colorida = atual; barra roxa = EAC
3. **[A9] RDO approval flow** — exec_qty só acumula se `status_rdo=aprovado`

### Fase 7 — IA avançada + caminho crítico (2-3 sessões)
1. **[A6] Caminho crítico (CPM)** — Algoritmo forward/backward pass sobre o grafo
2. **[A7] Cenário de reajuste IA** — IA propõe novo cronograma como `hub_cronograma_versao cenario_ia`; UI de aprovação
3. **[A10] Média móvel** — Janela de N dias configurável para produtividade real

### Fase 8 — UX avançado (1-2 sessões)
1. **[A8] Gantt multi-camada com toggle** — 4 camadas visuais
2. **[A11] Filtros por frente/equipe** — `frente_servico` já no schema
3. **[A12] Lookahead 2 semanas**
4. **[A20] Notificações de desvio** — Integrar com `AlertService` existente

---

## 5. Schema pendente

### Tabela `hub_atividade_dependencias` (nova — substitui `dependencia_id` 1:1)
```sql
CREATE TABLE hub_atividade_dependencias (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    contrato      text NOT NULL,
    client_id     uuid,
    origem_id     uuid NOT NULL REFERENCES hub_atividades(id) ON DELETE CASCADE,
    destino_id    uuid NOT NULL REFERENCES hub_atividades(id) ON DELETE CASCADE,
    tipo          text NOT NULL DEFAULT 'FS' CHECK (tipo IN ('FS','SS','FF','SF')),
    lag_dias      int  NOT NULL DEFAULT 0,
    ativa         boolean DEFAULT true,
    created_at    timestamptz DEFAULT now(),
    UNIQUE (origem_id, destino_id)
);
CREATE INDEX ON hub_atividade_dependencias (destino_id);
CREATE INDEX ON hub_atividade_dependencias (contrato);
```

### Alterações em `hub_atividades`
```sql
-- Manter dependencia_id como fallback legado, mas não usar para novos registros
ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS folga_total_dias int DEFAULT 0;
ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS no_caminho_critico boolean DEFAULT false;
ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS data_inicio_real date;
ALTER TABLE hub_atividades ADD COLUMN IF NOT EXISTS data_fim_real date;
```

### Tabela `hub_cronograma_versao` (já existe no schema — falta UI)
```sql
-- Já criada via migration. Adicionar coluna comparacao:
ALTER TABLE hub_cronograma_versao ADD COLUMN IF NOT EXISTS is_ativo boolean DEFAULT false;
```

---

## 6. Score atual vs world-class

| Dimensão | Atual | World-class | Gap |
|---|---|---|---|
| Estrutura de dados (hierarquia, tipos, unidades) | 8/10 | 10/10 | Falta multi-predecessoras e calendário de obra |
| Cálculo de datas (dias úteis, dependências) | 6/10 | 10/10 | Falta lag, tipos FS/SS/FF/SF, cascade, ciclos |
| Medição de progresso (RDO integrado, qty) | 8/10 | 10/10 | Falta approval flow antes de acumular |
| Forecast / EAC | 7/10 | 10/10 | Falta média móvel, thresholds, confiança |
| Baseline e governança | 3/10 | 10/10 | Maior lacuna — sem baseline, sem freeze, sem compare |
| Visualização Gantt | 6/10 | 10/10 | Falta camadas, toggle, edição inline |
| IA e cenários | 5/10 | 10/10 | Import OK; falta cenário de reajuste, CPM, sugestão |
| Auditoria e rastreabilidade | 9/10 | 10/10 | Muito bom — log granular por campo implementado |
| **TOTAL** | **6.5/10** | **10/10** | **~3.5 pontos para world-class** |

---

## 7. O que fazer primeiro para maior retorno

Se só der para fazer 1 coisa: **Fase 5 item A2 + A1** — cycle detection + cascade recalculation.
Sem isso, o sistema é confiável para planejamento inicial mas quebra na gestão dinâmica da obra.

Se der para fazer 2: adicionar **Baseline freeze (A3)**.
Com baseline + cascade, o sistema passa a ter comparação real "programado vs atual" — que é o coração de qualquer ferramenta séria de cronograma.

O diferencial competitivo de longo prazo é a **Fase 7 (IA + CPM)**: detectar automaticamente o caminho crítico e propor cenários de recuperação com IA é raro mesmo em softwares pagos como o Primavera P6.

---

*Documento gerado em 2026-03-31. Atualizar a cada sprint de implementação.*
