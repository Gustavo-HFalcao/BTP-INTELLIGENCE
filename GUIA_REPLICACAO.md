# Guia de Replicação e Estrutura - Bomtempo Dashboard

Este guia serve como manual para replicar a estrutura do **Bomtempo Dashboard** para outros projetos ou clientes (White-label), bastando substituir os dados e configurações.

## 1. Stack Tecnológico

*   **Linguagem:** Python 3.9+
*   **Framework Web:** [Reflex](https://reflex.dev/) (Antigo Pynecone)
*   **Frontend Reference:** React + TypeScript (estrutura de componentes espelhada em Python)
*   **Manipulação de Dados:** Pandas
*   **Fonte de Dados:** Excel (.xlsx)

---

## 2. Estrutura de Pastas Fundamental

Para replicar o projeto, mantenha a seguinte estrutura de diretórios, que é o padrão esperado pelo código:

```
/
├── bomtempo/                 # Código Fonte (Application Logic)
│   ├── bomtempo.py           # Entry point (App Def)
│   ├── core/                 # Configurações e Utilitários
│   ├── state/                # Lógica de Estado (GlobalState)
│   ├── pages/                # Telas (Layouts e Views)
│   └── components/           # Componentes UI Reutilizáveis
├── data/                     # Fonte de Dados (Excel)
│   └── ... (arquivos .xlsx)
├── assets/                   # Imagens, CSS, Fontes
├── rxconfig.py               # Configuração do Reflex
└── requirements.txt          # Dependências
```

---

## 3. Passo a Passo para Replicação (Novo Projeto)

### Passo 1: Clonar e Limpar
Copie a estrutura da pasta `bomtempo-dashboard` para o novo diretório do cliente.
Mantenha os arquivos `.py` e a estrutura de pastas.

### Passo 2: Substituir os Dados
Acesse a pasta `data/` e substitua os arquivos Excel pelos dados do novo escopo.
**Importante:** Mantenha os nomes das colunas originais do Excel para garantir que o `DataLoader` funcione automaticamente. O sistema trata internamente a normalização dos nomes.

**Arquivos necessários:**
1.  `dContratos.xlsx` (Cadastro de Contratos)
2.  `Projeto.xlsx` (Cronograma)
3.  `Obras.xlsx` (Medições)
4.  `Financeiro.xlsx` (Custos e Receitas)
5.  `O&M.xlsx` (Dados de Geração)

### Passo 3: Configuração Base (`rxconfig.py`)
Edite o arquivo `rxconfig.py` se desejar mudar o nome da aplicação:

```python
import reflex as rx

config = rx.Config(
    app_name="novo_cliente_dashboard", # Alterar aqui
)
```

### Passo 4: Configurações de Negócio (`core/config.py`)
No arquivo `bomtempo/core/config.py`, você pode ajustar:
1.  **Caminhos dos Arquivos:** Se os nomes dos Excels mudarem, atualize o `XLSX_MAP`.
2.  **Cores da Marca:** Atualize o dicionário `BRAND_COLORS` para refletir a identidade visual do novo cliente.

```python
BRAND_COLORS = {
    "primary_green": "#NOVA_COR",
    "gold": "#NOVA_COR_SECUNDARIA",
    ...
}
```

### Passo 5: Inicializar
No terminal, dentro da pasta raiz:

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Inicializar Reflex (apenas na primeira vez)
reflex init

# 3. Rodar em modo desenvolvimento
reflex run
```

---

## 4. Customização Avançada

### Alterar Lógica de Cálculo
Toda a lógica de negócios e processamento de dados está centralizada em:
*   `bomtempo/state/global_state.py`

Se o novo cliente tiver regras diferentes (ex: cálculo de margem diferente), edite as propriedades (`@rx.var`) nesta classe.

### Alterar Layouts
*   `bomtempo/pages/`: Contém a estrutura de cada página.
*   `bomtempo/components/`: Componentes visuais (Cards, Gráficos).

### Hardcoded Values (Atenção)
Alguns componentes visuais possuem valores estáticos (ex: Gauge Chart em Obras). Para um projeto 100% dinâmico, lembre-se de vincular estes componentes a variáveis do `GlobalState` em `bomtempo/pages/obras.py`.

---

## 5. Deploy

Para produção:
1.  Gere o build estático/backend: `reflex export`.
2.  O Reflex gera um backend (FastAPI) e um frontend (NextJS static).
3.  Hospede o backend em um servidor Python e o frontend em qualquer static host (Vercel, Netlify) ou sirva ambos via Docker.
