# Demo Seed — Usina Solar 120 kWp

**Data de criação:** 07/04/2026  
**Ambiente:** Supabase (projeto bomtempo)  
**Contrato:** `CONTRATO N° 306/2026`  
**client_id:** `11111111-1111-1111-1111-111111111111`

---

## Limpeza realizada

Todos os dados legados foram removidos com FK-safe order:

1. `hub_atividade_historico` → deletado primeiro (FK → hub_atividades)
2. `hub_cronograma_log` → deletado
3. `rdo_atividades` → deletado
4. `hub_atividades` → deletado
5. `rdo_master` → deletado (incluindo 4 com contrato=NULL)
6. `fin_custos` → deletado
7. `contratos` → deletados BT-3, TESTE1 (306/2026 mantido e atualizado)

Contratos legacy removidos: `A`, `B`, `BT-2024-001`, `BT-2024-002`, `BT-3`, `BTP-2026`, `CT-2024-001`, `TESTE1`, `VALIDAÇÃO`

---

## Contrato

| Campo | Valor |
|---|---|
| **contrato** | `CONTRATO N° 306/2026` |
| **projeto** | Usina Solar 120 kWp — Galpão Industrial Ferreira & Cia |
| **cliente** | Ferreira & Cia Ind. e Com. Ltda |
| **localização** | Av. das Indústrias, 1420, Distrito Industrial, Fortaleza / CE |
| **valor_contratado** | R$ 285.000,00 |
| **status** | Em Execução |
| **data_inicio** | 2026-04-01 |
| **data_termino** | 2026-04-14 |
| **potencia_kwp** | 120.00 |
| **tipo** | EPC |
| **prazo_contratual_dias** | 14 |
| **efetivo_planejado** | 8 |

---

## Hierarquia de Atividades (17 registros)

IDs usados: `aa000001-*`, `aa000002-*`, `aa000003-*` (fixos, sem gen_random_uuid)

### Macro 1 — Estrutura Metálica (`aa000001-...-0001`)
- Período: 01/04 – 05/04 | Peso: 35% | **Conclusão: 100%** | Status: concluida
- **Micro 1.1** Fundação e Ancoragem (`...-0002`) — 48 âncoras, 100%, concluida
  - Sub 1.1.1 — Perfuração das estruturas de concreto (`...-0003`) — 48 furos
  - Sub 1.1.2 — Injeção de resina epóxi e fixação (`...-0004`) — 48 un
- **Micro 1.2** Montagem das Calhas e Trilhos (`...-0005`) — 240m, 100%, concluida
- **Micro 1.3** Nivelamento e Inspeção (`...-0006`) — 1 conjunto, 100%, concluida

### Macro 2 — Módulos & Elétrica CC (`aa000002-...-0001`)
- Período: 04/04 – 10/04 | Peso: 40% | **Conclusão: 57%** | Status: em_execucao
- **Micro 2.1** Instalação dos Módulos FV (`...-0002`) — 300 módulos, 80% (240/300), em_execucao
  - Sub 2.1.1 — Descarregamento e conferência (`...-0003`) — 300 módulos, 100%, concluida
  - Sub 2.1.2 — Fixação nos trilhos (`...-0004`) — 300 módulos, 80% (240/300), em_execucao
  - Sub 2.1.3 — Cabeamento CC entre módulos (`...-0005`) — 600m, 67% (400m), em_execucao
- **Micro 2.2** String Box e Inversores (`...-0006`) — 4 un, 20% (1/4), pronta_iniciar
- **Micro 2.3** Aterramento e SPDA (`...-0007`) — 1 conjunto, 0%, nao_iniciada

### Macro 3 — Elétrica CA & Comissionamento (`aa000003-...-0001`)
- Período: 09/04 – 14/04 | Peso: 25% | **Conclusão: 0%** | Status: nao_iniciada
- **Micro 3.1** Quadro de Distribuição CA (`...-0002`) — 0%, nao_iniciada
- **Micro 3.2** Cabeamento CA e Rede (`...-0003`) — 180m, 0%, nao_iniciada
- **Micro 3.3** Comissionamento e Testes (`...-0004`) — 1 conjunto, 0%, nao_iniciada

---

## RDOs (7 registros)

IDs fixos: `bb000001-...-0001` a `bb000007-...-0001`

| RDO | Data | Clima | Interrupção | Acidente | Equipe | Destaque |
|---|---|---|---|---|---|---|
| RDO-306-001 | 01/04 | Ensolarado | Não | Não | 8 | Início obra, 52 furos (meta 48) |
| RDO-306-002 | 02/04 | Nublado | Não | Não | 8 | Âncoras OK + 90m trilhos |
| RDO-306-003 | 03/04 | Chuva forte | **Sim** (13h) | Não | 8 | 60m trilhos + conferência módulos |
| RDO-306-004 | 04/04 | Ensolarado | Não | Não | 8 | Recuperação: estrutura 100% + 80 módulos |
| RDO-306-005 | 05/04 | Ensolarado | Não | Não | 8 | 100 módulos (meta 90) + cabeamento |
| RDO-306-006 | 06/04 | Chuva mod. | **Sim** (10h) | **Sim** | 7 | 60 módulos. Josué Silva — contusão tornozelo, CAT emitida |
| RDO-306-007 | 07/04 | Ensolarado | Não | Não | 7 | Briefing segurança + 240 módulos acumulados (80%) |

### rdo_atividades: 15 registros (2–3 por RDO)

---

## Lançamentos Financeiros — fin_custos (13 registros)

| Categoria | Descrição | Previsto | Executado | Status |
|---|---|---|---|---|
| Material | Perfis e trilhos alumínio 240m | 18.000 | 18.000 | executado |
| Material | Âncoras químicas + resina (48 conj.) | 4.800 | 4.800 | executado |
| Mão de Obra | Equipe Carlos Menezes — 5d/4h | 12.000 | 12.000 | executado |
| Equipamento | Furadeira + torquímetro — 5d | 1.500 | 1.500 | executado |
| Material | Módulos FV 400W — 300 un | 114.000 | 91.200 | parcial |
| Material | Cabo CC 6mm² — 600m | 3.600 | 2.400 | parcial |
| Mão de Obra | Equipe Ricardo Sousa — 4d/5h | 14.400 | 14.400 | executado |
| Outros | EPIs adicionais pós-acidente RDO-006 | 850 | 850 | executado |
| Outros | Atendimento médico Josué + CAT | 320 | 320 | executado |
| Material | String Box + 4 inversores 30kW (WEG) | 52.000 | 0 | previsto |
| Material | QDC, disjuntores CA, medidor bidirecional | 18.500 | 0 | previsto |
| Mão de Obra | Equipe Felipe Araújo — 6d/4h | 14.400 | 0 | previsto |
| Serviço | Engenheiro RT — vistoria + ART startup | 3.800 | 0 | previsto |

**Total previsto:** R$ 259.170 | **Total executado:** R$ 145.470 (56,1%)

---

## Estado do projeto em 07/04

- **Macro 1** (Estrutura): ✅ 100% — concluída no prazo após chuva dia 03
- **Macro 2** (Módulos/CC): 🔄 57% — em execução, módulos a 80%, string box iniciando
- **Macro 3** (CA/Comissionamento): ⏳ 0% — não iniciada (começa 09/04)
- **Progresso geral:** ~57% (ponderado pesos 35/40/25)
- **Ocorrência relevante:** Acidente leve 06/04 (Josué Silva, afastamento 2d), CAT emitida
- **Financeiro executado:** R$ 145.470 / R$ 285.000 = 51%

---

## Notas para retomada

- Status `hub_atividades`: `nao_iniciada`, `pronta_iniciar`, `em_execucao`, `concluida`, `atrasada`, `paralisada`, `bloqueada`, `cancelada`
- Status `fin_custos`: `previsto`, `executado`, `parcial`, `cancelado`, `em_andamento`, `concluido`
- FK order para nova limpeza: `hub_atividade_historico` → `hub_cronograma_log` → `rdo_atividades` → `hub_atividades` → `rdo_master` → `fin_custos` → `contratos`
- Cache invalidado automaticamente na próxima carga (`on_load=GlobalState.load_data`)
