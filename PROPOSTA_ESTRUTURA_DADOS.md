# PROPOSTA DE ESTRUTURA DE DADOS - MVP
## Bomtempo Dashboard - Módulos Alarmes e RDO

---

## 📋 RESUMO EXECUTIVO

**Status Atual**:
- ✅ Sheet Alarmes: 3 colunas básicas (vazia)
- ✅ Sheet RDO Cabeçalho: 17 colunas (vazia)
- ❌ Sheets RDO detalhes (mao_obra, equipamentos, atividades, materiais): **NÃO ENCONTRADAS**

**Ação Necessária**:
1. Adicionar colunas ao sheet de Alarmes para suportar RBAC
2. Criar 4 sheets adicionais para RDO (ou usar abas na mesma sheet)
3. Popular com dados de exemplo vinculados aos contratos existentes
4. Adicionar coluna `role` na sheet de Login para RBAC

---

## 🚨 1. SHEET DE ALARMES

### Estrutura Proposta (colunas adicionais)

```
alarme_id          | int    | PK - ID único do alarme
tipo_alarme        | string | "reativo" ou "programado"
status             | string | "ativo" ou "inativo"
nome_alarme        | string | Nome descritivo (ex: "Atraso Crítico em Obras")
descricao          | string | Descrição detalhada do que o alarme monitora
modulo             | string | "financeiro", "obras", "rdo", "om", "geral"
condicao_sql       | string | Query/condição que dispara o alarme (simplificado)
threshold          | float  | Valor limite (ex: 10 para "atraso > 10%")
frequencia         | string | "continuo", "diario", "semanal", "mensal" (apenas para programados)
horario_envio      | string | HH:MM (ex: "08:00") - apenas para programados
contrato           | string | Contrato específico (vazio = todos) - para mestre de obras
destinatarios      | string | E-mails separados por vírgula
criado_em          | string | Data de criação (YYYY-MM-DD)
criado_por         | string | Usuário que criou
ultima_execucao    | string | Data/hora da última vez que disparou
```

### Dados de Exemplo (8 alarmes base)

#### Alarmes Reativos (4)
```csv
1,reativo,ativo,"Atraso Crítico em Obras","Dispara quando atraso físico > 15%",obras,"realizado_pct < previsto_pct - 15",15,continuo,,,"admin@bomtempo.com,gestor@bomtempo.com",2026-02-01,gustavo,2026-02-18 08:30

2,reativo,ativo,"Saldo Financeiro Baixo","Dispara quando margem < 10%",financeiro,"margem_pct < 10",10,continuo,,,"admin@bomtempo.com,financeiro@bomtempo.com",2026-02-01,gustavo,

3,reativo,ativo,"RDO Não Preenchido","Dispara quando RDO não é preenchido por 2 dias",rdo,"dias_sem_rdo > 2",2,continuo,,BOM010-24,"gestor@bomtempo.com,mestre1@bomtempo.com",2026-02-01,gustavo,

4,reativo,ativo,"Geração O&M Abaixo do Esperado","Dispara quando performance < 80%",om,"performance_pct < 80",80,continuo,,,"admin@bomtempo.com,operacao@bomtempo.com",2026-02-01,gustavo,
```

#### Alarmes Programados (4)
```csv
5,programado,ativo,"Resumo Diário de Obras","Resumo consolidado de todas as obras",obras,,,diario,08:00,,"admin@bomtempo.com,gestor@bomtempo.com",2026-02-01,gustavo,2026-02-18 08:00

6,programado,ativo,"Relatório Semanal Financeiro","Análise financeira semanal",financeiro,,,semanal,09:00,,"admin@bomtempo.com,financeiro@bomtempo.com",2026-02-01,gustavo,2026-02-17 09:00

7,programado,ativo,"Consolidado Mensal RDO","Consolidação mensal de RDOs preenchidos",rdo,,,mensal,10:00,,"admin@bomtempo.com,gestor@bomtempo.com",2026-02-01,gustavo,

8,programado,inativo,"Dashboard Executivo Semanal","Resumo executivo completo (INATIVO para teste)",geral,,,semanal,07:00,,"admin@bomtempo.com",2026-02-01,gustavo,
```

---

## 📝 2. SHEETS DE RDO (5 tabelas relacionadas)

### 2.1 RDO Cabeçalho (já existe)
**URL atual**: https://docs.google.com/spreadsheets/d/e/2PACX-1vQs1Qz7TOgcmzdflhhv-GBgJlC6UkNHlzxthZXulkyzp1aKgETHbMm27DudCODlYkvRnqROHoAy6cbM/pub?output=csv

✅ **Colunas corretas** (17 colunas já definidas)

**Dados de Exemplo** (3 RDOs):
```csv
1,BOM010-24,Escola Municipal A,2026-02-17,manha,João Silva,Mestre de Obras,Ensolarado,nao,,12,3,"Fundação completa, início estrutura metálica",nenhum,nenhuma,aprovado,2026-02-17 18:30

2,BOM010-24,Escola Municipal A,2026-02-18,manha,João Silva,Mestre de Obras,Nublado,sim,Atraso de 2h por chuva,10,2,"Continuação estrutura metálica - 40% concluída",nenhum,Falta EPI capacete amarelo,rascunho,2026-02-18 12:00

3,BOM011-24,Hospital Regional,2026-02-17,tarde,Maria Santos,Engenheira Civil,Parcialmente nublado,nao,,18,5,"Instalação elétrica pavimento 2, pintura externa",nenhum,nenhuma,aprovado,2026-02-17 19:00
```

### 2.2 RDO Mão de Obra
**⚠️ PRECISA CRIAR SHEET SEPARADA** ou aba adicional

```
id_mao_obra               | int
id_rdo                    | int    | FK -> rdo_cabecalho
funcao                    | string
empresa                   | string
quantidade_trabalhadores  | int
horas_normais             | float
horas_extras              | float
custo_hora                | float
observacoes               | string
```

**Dados de Exemplo**:
```csv
1,1,Pedreiro,Construtora XYZ,5,8,0,45.00,
2,1,Servente,Construtora XYZ,4,8,0,25.00,
3,1,Soldador,Metalúrgica ABC,3,8,2,65.00,Horas extras para finalizar fundação
4,2,Pedreiro,Construtora XYZ,4,6,0,45.00,Reduzido por chuva
5,2,Servente,Construtora XYZ,3,6,0,25.00,Reduzido por chuva
6,3,Eletricista,Elétrica DEF,8,8,0,55.00,
7,3,Pintor,Pinturas GHI,10,8,0,40.00,
```

### 2.3 RDO Equipamentos
**⚠️ PRECISA CRIAR SHEET SEPARADA** ou aba adicional

```
id_equipamento_rdo  | int
id_rdo              | int    | FK -> rdo_cabecalho
tipo_equipamento    | string
codigo_patrimonio   | string
status_operacao     | string | "operacional", "manutencao", "parado"
horas_uso           | float
observacoes         | string
```

**Dados de Exemplo**:
```csv
1,1,Betoneira,EQ-2024-001,operacional,8.0,
2,1,Grua,EQ-2024-015,operacional,7.5,
3,1,Compactador,EQ-2024-032,operacional,4.0,
4,2,Betoneira,EQ-2024-001,operacional,4.0,Parada por chuva das 10h às 14h
5,2,Grua,EQ-2024-015,parado,0,Parado preventivamente por chuva
6,3,Furadeira Industrial,EQ-2024-120,operacional,8.0,
7,3,Andaime Elétrico,EQ-2024-089,operacional,8.0,
8,3,Compressor,EQ-2024-045,manutencao,2.0,Manutenção preventiva realizada
```

### 2.4 RDO Atividades
**⚠️ PRECISA CRIAR SHEET SEPARADA** ou aba adicional

```
id_atividade_rdo      | int
id_rdo                | int    | FK -> rdo_cabecalho
descricao_atividade   | string
local_execucao        | string
quantidade_executada  | float
unidade               | string | "m²", "m³", "un", "m", "kg"
percentual_atividade  | float  | % de conclusão desta atividade
inicio_atividade      | string | HH:MM
fim_atividade         | string | HH:MM
responsavel_execucao  | string
```

**Dados de Exemplo**:
```csv
1,1,Concretagem de fundação,Bloco A - Eixo 1 a 4,45.5,m³,100,07:00,15:30,João Silva
2,1,Montagem estrutura metálica,Bloco A - Viga principal,12.0,m,25,13:00,17:00,Carlos Mendes
3,2,Montagem estrutura metálica,Bloco A - Viga principal,8.0,m,40,07:00,12:00,Carlos Mendes
4,2,Alvenaria,Bloco B - Parede externa,25.0,m²,15,08:00,11:30,Pedro Costa
5,3,Instalação elétrica,Pavimento 2 - Salas 201-210,450.0,m,60,13:00,18:00,Roberto Lima
6,3,Pintura externa,Fachada Norte,180.0,m²,80,07:00,17:00,Ana Paula
```

### 2.5 RDO Materiais
**⚠️ PRECISA CRIAR SHEET SEPARADA** ou aba adicional

```
id_material_rdo    | int
id_rdo             | int    | FK -> rdo_cabecalho
tipo_material      | string
descricao          | string
quantidade         | float
unidade            | string | "m³", "kg", "un", "saco", "L"
fornecedor         | string
nota_fiscal        | string
valor_unitario     | float
observacoes        | string
```

**Dados de Exemplo**:
```csv
1,1,Concreto,Concreto FCK 30,50.0,m³,Concreteira Recife,NF-12345,450.00,
2,1,Aço,Barra CA-50 12mm,850.0,kg,Aço Forte Ltda,NF-12346,8.50,
3,1,Cimento,CP II-Z-32,100,saco,Cimentos PE,NF-12347,35.00,
4,2,Telha metálica,Telha trapezoidal,120,un,Coberturas ABC,NF-12348,45.00,
5,2,Tijolo,Tijolo cerâmico 8 furos,2000,un,Cerâmica São José,NF-12349,0.85,
6,3,Fio elétrico,Fio 2.5mm² - 100m,15,rolo,Elétrica Central,NF-12350,85.00,
7,3,Tinta,Tinta acrílica branca 18L,25,galão,Tintas Premium,NF-12351,120.00,
```

---

## 👤 3. RBAC - SHEET DE LOGIN

### Colunas Adicionais Propostas

**Estrutura Atual**:
```
login      | string
senha      | string
permissao  | string | "Administrador", "Engenheiro" (usado como role básico)
```

**Proposta de Expansão** (adicionar colunas):
```
login           | string
senha           | string
permissao       | string | Mantém compatibilidade ("Administrador", "Gestão-Mobile")
role            | string | NOVO: "admin", "gestor", "mestre_obras", "viewer"
nome_completo   | string | NOVO: Nome para exibição
email           | string | NOVO: E-mail para notificações
contrato_vinculado | string | NOVO: Para mestre_obras (ex: "BOM010-24")
ativo           | string | NOVO: "sim" ou "nao"
criado_em       | string | NOVO: Data de criação
```

**Dados de Exemplo Atualizados**:
```csv
gustavo,1,Administrador,admin,Gustavo Bomtempo,gustavo@bomtempo.com,,sim,2026-01-15
renato,2,Engenheiro,gestor,Renato Silva,renato@bomtempo.com,,sim,2026-01-15
mobile,1,Gestão-Mobile,mestre_obras,João Silva (Mobile),joao.silva@bomtempo.com,BOM010-24,sim,2026-02-01
viewer,3,Visitante,viewer,Cliente Externo,cliente@empresa.com,,sim,2026-02-10
```

---

## 🔄 4. PRÓXIMOS PASSOS DE IMPLEMENTAÇÃO

### Fase 1: Infraestrutura de Dados (AGORA - Baixo Risco)
1. ✅ Adicionar URLs no `config.py`
2. ✅ Criar normalização no `data_loader.py`
3. ✅ Adicionar listas no `global_state.py`
4. ✅ Testar carregamento sem quebrar nada

### Fase 2: Popular Sheets (VOCÊ FAZ MANUALMENTE)
1. Copiar dados de exemplo acima
2. Colar nas sheets do Google
3. ⚠️ **CRIAR 4 SHEETS ADICIONAIS** para RDO (mao_obra, equipamentos, atividades, materiais)
   - Opção A: Criar 4 sheets separadas com URLs próprias
   - Opção B: Usar abas na mesma planilha (precisa publicar cada aba separadamente)

### Fase 3: UI Básica (DEPOIS - Risco Médio)
1. Página de listagem de Alarmes (somente leitura)
2. Página de listagem de RDOs (somente leitura)
3. Filtros por role/contrato

### Fase 4: Funcionalidades Avançadas (FUTURO - Alto Risco)
1. Formulário de preenchimento de RDO
2. Sistema de alertas reativos
3. Envio de e-mails
4. Geração de PDF

---

## ❓ DECISÕES NECESSÁRIAS

**URGENTE - Preciso que você decida:**

1. **Sheets RDO Detalhes**:
   - [ ] Criar 4 sheets separadas (URLs individuais)
   - [ ] Usar abas na mesma planilha (mais organizado mas precisa publicar cada aba)
   - [ ] Por enquanto, implementar só o cabeçalho

2. **Colunas de Alarmes**:
   - [ ] Aprovar estrutura proposta acima
   - [ ] Sugerir modificações

3. **RBAC**:
   - [ ] Adicionar colunas novas na sheet Login
   - [ ] Manter apenas `permissao` (mais simples)

4. **Popular Dados**:
   - [ ] Eu populo manualmente com os CSVs acima
   - [ ] Claude gera script Python para popular via API do Google Sheets
   - [ ] Deixar vazio por enquanto

**Aguardando suas decisões para prosseguir com a implementação! 🚀**
