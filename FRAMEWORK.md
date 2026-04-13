# Dashboard Framework — Guia Completo de Arquitetura

> Documento de referência para replicar a arquitetura, visual e comportamento deste sistema em qualquer novo projeto.
> Stack: **Reflex (Python) + Supabase + Recharts + Deep Tectonic Design System**

---

## Índice

1. [Stack & Dependências](#1-stack--dependências)
2. [Estrutura de Diretórios](#2-estrutura-de-diretórios)
3. [Design System — Deep Tectonic](#3-design-system--deep-tectonic)
4. [Componentes Visuais](#4-componentes-visuais)
5. [Arquitetura de Estado](#5-arquitetura-de-estado)
6. [Autenticação & RBAC](#6-autenticação--rbac)
7. [Loading Premium & Sequência de Boot](#7-loading-premium--sequência-de-boot)
8. [Conexão com Supabase](#8-conexão-com-supabase)
9. [Carregamento & Cache de Dados](#9-carregamento--cache-de-dados)
10. [Layout Shell — Sidebar & Top Bar](#10-layout-shell--sidebar--top-bar)
11. [Gráficos & Visualizações](#11-gráficos--visualizações)
12. [Padrões de Event Handlers](#12-padrões-de-event-handlers)
13. [Páginas Padrão do Sistema](#13-páginas-padrão-do-sistema)
14. [CSS, Animações & Tema Global](#14-css-animações--tema-global)
15. [Registro de Páginas & App Entry](#15-registro-de-páginas--app-entry)
16. [Checklist para Novo Projeto](#16-checklist-para-novo-projeto)

---

## 1. Stack & Dependências

```
reflex==0.8.x          # Framework Python fullstack (SSR + WebSocket)
pandas                 # Processamento de dados tabulares
httpx                  # HTTP client assíncrono (Supabase REST)
python-dotenv          # Variáveis de ambiente
PyPDF2                 # Extração de texto de PDFs
python-docx            # Extração de texto de DOCX
bcrypt / hashlib       # Hash de senhas (PBKDF2-HMAC-SHA256)
playwright             # Geração de PDFs via headless Chromium
```

**Fonts (Google Fonts CDN):**
```
Rajdhani   → títulos, tech labels, page headers
Outfit     → corpo, inputs, parágrafos
JetBrains Mono → dados, valores, monitoramento
```

---

## 2. Estrutura de Diretórios

```
projeto/
├── projeto/                    # Pacote Python principal
│   ├── projeto.py              # Entry point — app = rx.App(...), add_page(...)
│   ├── core/
│   │   ├── styles.py           # Design tokens (cores, tipografia, espaçamentos)
│   │   ├── config.py           # Config (URLs, credenciais, diretórios)
│   │   ├── supabase_client.py  # Pool HTTP + funções sb_select/insert/update/delete
│   │   ├── data_loader.py      # Cache multicamada + carregamento paralelo de tabelas
│   │   ├── auth_utils.py       # verify_password, hash_password (PBKDF2)
│   │   └── audit_logger.py     # Fire-and-forget → tabela system_logs
│   ├── state/
│   │   ├── global_state.py     # GlobalState — auth, dados, AI chat
│   │   └── ui_state.py         # UIState — modais, loading local, toasts
│   ├── pages/
│   │   ├── login.py            # Página de login (split-screen)
│   │   ├── index.py            # Visão Geral / Dashboard principal
│   │   ├── logs_auditoria.py   # Logs do sistema
│   │   └── usuarios.py         # Gerenciamento de usuários & perfis
│   ├── components/
│   │   ├── sidebar.py          # Sidebar colapsável + mobile drawer
│   │   ├── top_bar.py          # Header global + sub-tabs por página
│   │   ├── charts.py           # Wrappers Recharts (eixos, tooltips, KPI cards)
│   │   ├── loading_screen.py   # Boot loader animado + skeleton loaders
│   │   └── default.py          # Layout shell (sidebar + topbar + content)
│   └── layouts/
│       └── default.py          # Função default_layout() usada em add_page()
├── assets/
│   ├── style.css               # CSS global, variáveis, glassmorphism
│   ├── animations.css          # Keyframes: fadeInUp, shimmer, pulse, routeEnter
│   ├── light_theme.css         # Overrides para modo claro (opcional)
│   ├── banner.png              # Logo expandida (sidebar)
│   └── icon.png                # Favicon / logo colapsada
└── .env                        # SUPABASE_URL, SUPABASE_SERVICE_KEY, etc.
```

---

## 3. Design System — Deep Tectonic

### Paleta de Cores

```python
# ── Backgrounds ──────────────────────────────────
BG_VOID     = "#030504"               # fundo da página (quase preto esverdeado)
BG_DEPTH    = "#081210"               # seções mais fundas
BG_SURFACE  = "#0e1a17"              # superfícies, painéis
BG_GLASS    = "rgba(14, 26, 23, 0.7)"  # glassmorphism
BG_ELEVATED = "#142420"              # cards elevados
BG_INPUT    = "rgba(255, 255, 255, 0.03)"  # fundo de inputs

# ── Texto ─────────────────────────────────────────
TEXT_PRIMARY   = "#E0E0E0"
TEXT_SECONDARY = "#889999"
TEXT_MUTED     = "#889999"
TEXT_WHITE     = "#FFFFFF"

# ── Bordas ────────────────────────────────────────
BORDER_SUBTLE    = "rgba(255, 255, 255, 0.08)"
BORDER_ACCENT    = "rgba(201, 139, 42, 0.3)"    # cobre médio
BORDER_HIGHLIGHT = "rgba(201, 139, 42, 0.5)"    # cobre forte (hover)

# ── Marca: Cobre + Patina ─────────────────────────
COPPER       = "#C98B2A"                         # acento primário
COPPER_LIGHT = "#E0A63B"
COPPER_GLOW  = "rgba(201, 139, 42, 0.15)"

PATINA       = "#2A9D8F"                         # acento secundário (teal)
PATINA_DARK  = "#1d7066"
PATINA_GLOW  = "rgba(42, 157, 143, 0.15)"

# ── Status ────────────────────────────────────────
SUCCESS     = "#2A9D8F"   SUCCESS_BG = "rgba(42, 157, 143, 0.1)"
WARNING     = "#F59E0B"   WARNING_BG = "rgba(245, 158, 11, 0.12)"
DANGER      = "#EF4444"   DANGER_BG  = "rgba(239, 68, 68, 0.1)"
INFO        = "#3B82F6"   INFO_BG    = "rgba(59, 130, 246, 0.12)"
```

### Tipografia

```python
FONT_DISPLAY = "'Rajdhani', sans-serif"     # títulos de página, headers
FONT_TECH    = "'Rajdhani', sans-serif"     # labels técnicas, KPIs
FONT_BODY    = "'Outfit', sans-serif"       # corpo, inputs, parágrafos
FONT_MONO    = "'JetBrains Mono', monospace" # valores, dados, tooltips

# Estilos pré-prontos
PAGE_TITLE_STYLE = {
    "font_family": FONT_TECH,
    "font_size": "clamp(1.375rem, 4.5vw, 1.875rem)",
    "font_weight": "700",
    "color": TEXT_WHITE,
    "text_transform": "uppercase",
    "letter_spacing": "-0.02em",
}

SECTION_TITLE_STYLE = {
    "font_family": FONT_TECH,
    "font_size": "clamp(1rem, 3.5vw, 1.25rem)",
    "font_weight": "700",
    "color": TEXT_PRIMARY,
    "text_transform": "uppercase",
    "letter_spacing": "0.02em",
}

SECTION_SUBTITLE_STYLE = {
    "font_size": "clamp(0.65rem, 2vw, 0.75rem)",
    "color": TEXT_MUTED,
    "text_transform": "uppercase",
    "letter_spacing": "0.15em",
    "font_weight": "700",
}
```

### Espaçamentos & Raios

```python
R_CARD    = "6px"    # cards, painéis, modais
R_CONTROL = "3px"    # inputs, botões, badges

PADDING_HERO = "clamp(20px, 5vw, 48px)"   # header hero panels
PADDING_CARD = "clamp(16px, 3vw, 32px)"   # glass cards

SIDEBAR_WIDTH          = "288px"   # expandida
SIDEBAR_WIDTH_COLLAPSED = "64px"   # colapsada
```

### Glass Card (padrão)

```python
GLASS_CARD = {
    "background":       BG_GLASS,
    "backdrop_filter":  "blur(12px)",
    "border":           f"1px solid {BORDER_SUBTLE}",
    "border_radius":    R_CARD,
    "padding":          "32px",
    "box_shadow":       "0 4px 30px rgba(0, 0, 0, 0.3)",
    "transition":       "all 0.5s ease",
    "_hover": {
        "border_color": BORDER_HIGHLIGHT,
    },
}
```

### Variáveis CSS Globais (`assets/style.css`)

```css
:root {
  --bg-void:        #030504;
  --bg-depth:       #081210;
  --bg-surface:     #0e1a17;
  --bg-glass:       rgba(14, 26, 23, 0.7);
  --copper-500:     #C98B2A;
  --copper-400:     #E0A63B;
  --copper-glow:    rgba(201, 139, 42, 0.15);
  --patina-500:     #2A9D8F;
  --text-main:      #E0E0E0;
  --text-muted:     #889999;
  --border-subtle:  rgba(255, 255, 255, 0.08);
  --ease-out-expo:  cubic-bezier(0.16, 1, 0.3, 1);
}

/* Font scaling responsivo */
body                          { font-size: 16px; }
@media (max-width: 1600px)    { html { font-size: 14px; } }
@media (max-width: 1366px)    { html { font-size: 13px; } }
@media (max-width: 768px)     { html { font-size: 14px; } }
@media (max-width: 380px)     { html { font-size: 12px; } }

/* Scrollbar */
::-webkit-scrollbar       { width: 6px; }
::-webkit-scrollbar-thumb { background: var(--copper-500); border-radius: 3px; }
*                         { scrollbar-color: var(--copper-500) var(--bg-void); }

/* Seleção de texto */
::selection { background: rgba(201, 139, 42, 0.35); color: #fff; }
```

---

## 4. Componentes Visuais

### 4.1 KPI Card

O componente mais usado no sistema. Representa uma métrica principal com ícone, valor, tendência e efeito de hover.

```
┌─────────────────────────────────┐
│  [ÍCONE]           [TREND ▲+5%] │  ← cobre se positivo, vermelho se negativo
│                                 │
│  TÍTULO DA MÉTRICA              │  ← 12px, FONT_MONO, uppercase, TEXT_MUTED
│  R$ 12,5M                       │  ← 2.5rem, Rajdhani, TEXT_PRIMARY
│                          [◢]   │  ← decoração corner SVG cobre (top-right)
└─────────────────────────────────┘
```

**Estilo do card:**
```python
{
    "background":      BG_GLASS,
    "border":          f"1px solid {BORDER_SUBTLE}",
    "border_radius":   R_CARD,
    "padding":         "20px 24px",
    "transition":      "all 0.25s ease",
    "cursor":          "pointer",   # se clicável
    "_hover": {
        "transform":    "translateY(-4px)",
        "border_color": BORDER_HIGHLIGHT,
        "box_shadow":   f"0 12px 40px rgba(0,0,0,0.5), 0 0 30px {COPPER_GLOW}",
    },
}
```

**Ícone container:**
```python
{
    "background":    f"rgba(201, 139, 42, 0.08)",
    "border":        f"1px solid {BORDER_SUBTLE}",
    "border_radius": R_CARD,
    "padding":       "12px",
    "width":         "44px",
    "height":        "44px",
}
```

**Trend badge:**
```python
{
    "background":    SUCCESS_BG,    # ou DANGER_BG / WARNING_BG
    "color":         SUCCESS,       # ou DANGER / WARNING
    "border_radius": "999px",
    "padding":       "2px 10px",
    "font_size":     "11px",
    "font_family":   FONT_MONO,
    "font_weight":   "600",
}
```

**Corner decoration (SVG 20×20, top-right, posição absoluta):**
```python
rx.html("""
  <svg width="20" height="20" fill="none">
    <path d="M0 0 L20 0 L20 20" stroke="#C98B2A" stroke-width="1.5" opacity="0.4"/>
  </svg>
""")
```

---

### 4.2 Glass Card / Painel

```python
rx.box(
    content,
    background=BG_GLASS,
    backdrop_filter="blur(12px)",
    border=f"1px solid {BORDER_SUBTLE}",
    border_radius=R_CARD,
    padding=PADDING_CARD,
    box_shadow="0 4px 30px rgba(0, 0, 0, 0.3)",
    transition="all 0.5s ease",
    _hover={"border_color": BORDER_HIGHLIGHT},
)
```

---

### 4.3 Botões

**Primário (cobre):**
```python
rx.button(
    "Ação",
    background=f"linear-gradient(135deg, {COPPER}, {COPPER_LIGHT})",
    color=BG_VOID,
    font_family=FONT_TECH,
    font_weight="700",
    font_size="14px",
    letter_spacing="0.06em",
    text_transform="uppercase",
    height="44px",
    padding_x="24px",
    border_radius=R_CONTROL,
    border="none",
    cursor="pointer",
    _hover={"filter": "brightness(1.1)", "transform": "translateY(-1px)"},
    _active={"transform": "translateY(0)"},
)
```

**Secundário (outline cobre):**
```python
rx.button(
    "Ação",
    background="transparent",
    color=COPPER,
    border=f"1px solid {BORDER_ACCENT}",
    font_family=FONT_MONO,
    font_size="12px",
    height="36px",
    padding_x="16px",
    border_radius=R_CONTROL,
    _hover={"background": COPPER_GLOW, "border_color": COPPER},
)
```

**Ativo/Toggle (filtro selecionado):**
```python
# Ativo
{"background": COPPER, "color": BG_VOID, "font_weight": "700"}
# Inativo
{"background": "transparent", "color": TEXT_MUTED}
```

---

### 4.4 Inputs & Select

```python
rx.input(
    placeholder="...",
    background=BG_INPUT,
    border=f"1px solid {BORDER_SUBTLE}",
    border_radius=R_CONTROL,
    color=TEXT_PRIMARY,
    font_family=FONT_BODY,
    height="44px",
    padding_x="14px",
    _focus={
        "border_color": COPPER,
        "box_shadow": f"0 0 0 2px {COPPER_GLOW}",
        "outline": "none",
    },
    _placeholder={"color": TEXT_MUTED},
)
```

---

### 4.5 Badges & Status Pills

```python
def status_badge(label: str, color: str, bg: str):
    return rx.box(
        label,
        background=bg,
        color=color,
        border=f"1px solid {color}33",
        border_radius="4px",
        padding="2px 10px",
        font_size="11px",
        font_family=FONT_MONO,
        font_weight="600",
        text_transform="uppercase",
        letter_spacing="0.08em",
    )

# Exemplos:
status_badge("Ativo",    SUCCESS, SUCCESS_BG)
status_badge("Atenção",  WARNING, WARNING_BG)
status_badge("Crítico",  DANGER,  DANGER_BG)
status_badge("Em Curso", INFO,    INFO_BG)
```

---

### 4.6 Tooltips de Gráfico (Premium)

Dois estilos disponíveis:

**`TOOLTIP_STYLE`** — padrão Recharts com customização:
```python
TOOLTIP_STYLE = {
    "backgroundColor": BG_DEPTH,
    "borderColor":     BORDER_ACCENT,
    "borderRadius":    "8px",
    "boxShadow":       "0 10px 40px rgba(0, 0, 0, 0.5)",
    "fontSize":        "12px",
    "color":           TEXT_PRIMARY,
}
```

**`TOOLTIP_PREMIUM`** — glass ultra-dark, monospace, usado em gráficos principais:
```python
TOOLTIP_PREMIUM = {
    "background":     "rgba(6, 14, 12, 0.97)",
    "border":         f"1px solid {COPPER}",
    "borderRadius":   "6px",
    "boxShadow":      "0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(201,139,42,0.08)",
    "padding":        "10px 14px",
    "fontFamily":     "JetBrains Mono, monospace",
    "fontSize":       "11px",
    "color":          TEXT_PRIMARY,
    "backdropFilter": "blur(16px)",
    "minWidth":       "160px",
}

# Label do tooltip (título da série)
TOOLTIP_PREMIUM_LABEL = {
    "color":          COPPER,
    "fontWeight":     "700",
    "fontSize":       "10px",
    "letterSpacing":  "0.08em",
    "textTransform":  "uppercase",
    "marginBottom":   "6px",
    "paddingBottom":  "6px",
    "borderBottom":   "1px solid rgba(201,139,42,0.2)",
}
```

**Cursor do tooltip:**
```python
# Área (bar charts)
TOOLTIP_CURSOR = {"fill": "rgba(201,139,42,0.04)", "stroke": "rgba(201,139,42,0.15)", "strokeWidth": 1}
# Linha (line charts)
TOOLTIP_CURSOR_LINE = {"stroke": "rgba(201,139,42,0.3)", "strokeWidth": 1, "strokeDasharray": "4 2"}
```

---

### 4.7 Efeitos de Hover em Cards Navegáveis

Padrão para cards que são clicáveis e levam a outra página:

```python
_hover = {
    "background":   "rgba(14, 26, 23, 0.95)",
    "border_color": "rgba(201, 139, 42, 0.5)",
    "box_shadow": (
        "0 0 0 1px rgba(201,139,42,0.15),"
        "0 12px 40px rgba(0,0,0,0.5),"
        "0 0 50px rgba(201,139,42,0.07)"
    ),
    "transform":    "translateY(-3px)",
    "transition":   "all 0.2s ease",
    "cursor":       "pointer",
}
```

---

### 4.8 Section Header (padrão de página)

```python
rx.hstack(
    rx.vstack(
        rx.text("NOME DA PÁGINA", **PAGE_TITLE_STYLE),
        rx.text("Subtítulo descritivo", **PAGE_SUBTITLE_STYLE),
        align_items="flex-start",
        spacing="1",
    ),
    rx.spacer(),
    rx.hstack(
        # botões de ação: filtros, refresh, export
        spacing="2",
    ),
    width="100%",
    align="center",
    margin_bottom="24px",
)
```

---

## 5. Arquitetura de Estado

### 5.1 Hierarquia de States

```
GlobalState (rx.State)          ← raiz; autenticação, dados, AI chat
    │
    ├── UIState                 ← modais, loading local, toasts (herdado de GlobalState ou separado)
    ├── HubState                ← estado específico do Hub de Operações
    ├── FinanceiroState         ← filtros e computed vars do módulo financeiro
    └── [ModuleState]           ← um state por módulo (RDO, Reembolso, etc.)
```

### 5.2 GlobalState — Variáveis Principais

```python
class GlobalState(rx.State):
    # ── Auth ─────────────────────────────────────────────────
    is_authenticated:     bool = False
    current_user_name:    str  = ""
    current_user_role:    str  = ""
    current_client_id:    str  = ""
    current_client_name:  str  = ""
    allowed_modules:      List[str] = []   # slugs de módulos liberados pelo RBAC

    # ── Dados (DataFrames não-serializados — prefixo _) ──────
    _contratos_df:      pd.DataFrame = pd.DataFrame()
    _projetos_df:       pd.DataFrame = pd.DataFrame()
    _obras_df:          pd.DataFrame = pd.DataFrame()
    _financeiro_df:     pd.DataFrame = pd.DataFrame()
    _om_df:             pd.DataFrame = pd.DataFrame()

    # ── Listas serializáveis (para rx.foreach no frontend) ───
    contratos_list:     List[Dict[str, Any]] = []
    projetos_list:      List[Dict[str, Any]] = []
    obras_list:         List[Dict[str, Any]] = []

    # ── Seleção global de contrato ────────────────────────────
    selected_contrato:  str = ""

    # ── Controle de carregamento ──────────────────────────────
    is_loading:         bool = False
    data_version:       int  = 0        # incrementar para forçar re-render
    is_navigating:      bool = False    # overlay de navegação entre páginas

    # ── AI Chat ───────────────────────────────────────────────
    chat_history:       list[dict] = []
    chat_input:         str  = ""
    is_processing_chat: bool = False
    chat_session_id:    str  = ""
```

### 5.3 Regras de Nomenclatura

| Prefixo | Tipo | Exemplo |
|---------|------|---------|
| `_` | Não-serializado (DataFrame, listas Python) | `_contratos_df` |
| sem prefixo | Var reativa Reflex (sincronizada com frontend) | `contratos_list` |
| `is_` | Boolean de estado | `is_loading`, `is_authenticated` |
| `show_` | Boolean de modal/dialog | `show_kpi_detail` |
| `current_` | Seleção ativa | `current_user_name` |

### 5.4 Computed Vars

```python
@rx.var
def filtered_contratos(self) -> List[Dict[str, Any]]:
    """Filtro aplicado sobre a lista base — reativo automaticamente."""
    if not self.search_term:
        return self.contratos_list
    term = self.search_term.lower()
    return [c for c in self.contratos_list if term in c.get("nome", "").lower()]

@rx.var
def has_data(self) -> bool:
    return len(self.contratos_list) > 0
```

### 5.5 UIState — Variáveis de UI

```python
class UIState(rx.State):
    # Modais e dialogs
    show_novo_item:       bool = False
    show_edit_item:       bool = False
    show_kpi_detail:      str  = ""       # "" = fechado; "key" = qual KPI abrir

    # Loading granular por seção
    loading_sections:     dict = {}       # {"section_name": True/False}
    page_loading:         bool = False

    # Sidebar
    sidebar_open:         bool = True

    # Toast notifications
    toast_message:        str  = ""
    toast_type:           str  = "info"   # info | success | error | warning
    toast_visible:        bool = False

    # Filtros locais (sem DB query)
    search_ui:            str  = ""
```

---

## 6. Autenticação & RBAC

### 6.1 Modelo de Dados no Supabase

**Tabela `login`:**
```sql
id          uuid PRIMARY KEY DEFAULT gen_random_uuid()
user        text UNIQUE NOT NULL
password    text NOT NULL           -- PBKDF2-HMAC-SHA256, 260k iterations
user_role   text NOT NULL           -- nome do role (ex: "Administrador")
project     text                    -- contrato/projeto atribuído (ou NULL = todos)
avatar_icon text DEFAULT ''
avatar_type text DEFAULT 'initial'
client_id   uuid                    -- isolamento multi-tenant
```

**Tabela `roles`:**
```sql
id      uuid PRIMARY KEY DEFAULT gen_random_uuid()
name    text UNIQUE NOT NULL        -- "Administrador", "Engenheiro", etc.
modules jsonb NOT NULL DEFAULT '[]' -- array de slugs: ["visao_geral", "obras", ...]
icon    text DEFAULT 'user'         -- ícone lucide para o avatar do role
```

### 6.2 Slugs de Módulos (RBAC)

Cada módulo/página tem um slug. A tabela `roles` define quais slugs cada role acessa.

```python
MODULES = [
    "visao_geral",       # Dashboard principal
    "obras",             # Hub de Operações
    "projetos",          # Sub-páginas de projeto
    "financeiro",        # Módulo financeiro
    "om",                # O&M
    "analytics",         # Analytics
    "previsoes",         # Previsões/Forecast
    "relatorios",        # Geração de relatórios
    "chat_ia",           # Chat com IA
    "reembolso",         # Solicitação de reembolso
    "reembolso_dash",    # Dashboard de reembolsos
    "rdo_form",          # Formulário RDO
    "rdo_historico",     # Histórico RDO
    "rdo_dashboard",     # Dashboard RDO
    "editar_dados",      # Editor de tabelas BD
    "alertas",           # Alertas proativos
    "logs_auditoria",    # Logs do sistema
    "gerenciar_usuarios",# Admin de usuários/roles
]
```

### 6.3 Fluxo de Login

```
Usuário preenche username + password
           │
           ▼
GlobalState.check_login()
    │
    ├─ sb_select("login", filters={"user": username})
    │
    ├─ verify_password(input, hash)   ← PBKDF2-HMAC-SHA256
    │
    ├─ sb_select("roles", filters={"name": user_role})
    │     └─ popula allowed_modules: List[str]
    │
    ├─ is_authenticated = True
    ├─ current_user_name = username
    ├─ current_user_role = user_role
    ├─ current_client_id = client_id (multi-tenant)
    │
    └─ yield rx.redirect(destino baseado no role)
              │
              ├─ "Mestre de Obras" → /rdo-form
              ├─ "Solicitante"     → /reembolso
              └─ demais roles      → /  (Visão Geral)
```

### 6.4 Guard de Página

Toda página protegida tem um guard que redireciona se não autenticado:

```python
async def require_auth(self):
    """on_load guard — redireciona para login se não autenticado."""
    if not self.is_authenticated:
        yield rx.redirect("/login")
        return
    # Verificar módulo específico
    if "nome_modulo" not in self.allowed_modules:
        yield rx.redirect("/")
        return
```

### 6.5 Sidebar Controlada por RBAC

A sidebar não usa strings de role hardcoded. Cada item verifica o slug correspondente:

```python
def _sidebar_item(label, icon, href, module_slug):
    return rx.cond(
        GlobalState.allowed_modules.contains(module_slug),
        rx.link(
            rx.hstack(
                rx.icon(icon, size=18, color=_icon_color(href)),
                rx.text(label, display=rx.cond(GlobalState.sidebar_open, "block", "none")),
                spacing="3",
                align="center",
            ),
            href=href,
        ),
        rx.fragment(),  # não renderiza o item se não tem acesso
    )
```

### 6.6 Hash de Senha

```python
import hashlib, os, base64

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return base64.b64encode(salt + key).decode()

def verify_password(input_password: str, stored_hash: str) -> bool:
    raw = base64.b64decode(stored_hash.encode())
    salt = raw[:16]
    stored_key = raw[16:]
    input_key = hashlib.pbkdf2_hmac("sha256", input_password.encode(), salt, 260_000)
    return secrets.compare_digest(stored_key, input_key)
```

---

## 7. Loading Premium & Sequência de Boot

### 7.1 O que acontece ao abrir o sistema

```
1. Browser carrega /
        │
        ▼
2. index_page() com on_load=guard_index_page
        │
        ├─ is_authenticated? → NÃO → redirect /login
        │
        └─ SIM → on_load=GlobalState.load_data
                       │
                       ▼
3. load_data() inicia:
    ├─ is_loading = True   ← dispara loading screen no frontend
    ├─ yield               ← client recebe is_loading=True
    ├─ DataLoader.load_all()  ← consulta Supabase (paralelo, 5 workers)
    ├─ Popula todos _*_df e *_list
    ├─ is_loading = False
    └─ yield               ← cliente recebe dados + is_loading=False
```

### 7.2 Loading Screen Enterprise

Overlay full-screen com 5 passos animados sequencialmente via CSS.

**Estrutura visual:**
```
┌────────────────────────────────────────┐
│                                        │
│           [LOGO / BANNER]              │
│                                        │
│   [1] 🛡  Autenticando sessão...  ●    │
│   [2] 🗄  Conectando ao Supabase... ●  │
│   [3] 📊  Carregando módulos...    ●   │
│   [4] 📈  Preparando dados...      ●   │
│   [5] ⚡  Iniciando plataforma...  ●   │
│                                        │
│   ████████████░░░░░░░░░░░░░░░░░░░░░   │ ← progress bar 2px
│                                        │
└────────────────────────────────────────┘
```

**Implementação:**
```python
def loading_screen() -> rx.Component:
    return rx.cond(
        GlobalState.is_loading,
        rx.box(
            # Fundo
            rx.box(position="absolute", inset="0", background=BG_VOID, z_index="0"),
            # Grid overlay
            rx.box(position="absolute", inset="0",
                   background="radial-gradient(ellipse 80% 50% at 50% 40%, rgba(201,139,42,0.06) 0%, transparent 70%)",
                   z_index="1"),
            # Conteúdo centralizado
            rx.vstack(
                rx.image(src="/banner.png", height="48px"),
                rx.vstack(
                    *[_step_item(i+1, icon, label) for i, (icon, label) in enumerate(STEPS)],
                    spacing="3",
                    align_items="flex-start",
                ),
                rx.box(  # Progress bar
                    rx.box(class_name="loader-progress-fill",
                           height="2px", background=COPPER, border_radius="1px"),
                    width="300px", height="2px",
                    background="rgba(255,255,255,0.06)",
                    border_radius="1px",
                ),
                spacing="8",
                align="center",
                z_index="10",
            ),
            position="fixed", inset="0",
            z_index="9999",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.fragment(),
    )
```

**CSS para animação dos steps (`animations.css`):**
```css
/* Steps aparecem progressivamente */
.sync-step-1 { animation: fadeInUp 0.4s ease 0.2s both; }
.sync-step-2 { animation: fadeInUp 0.4s ease 0.6s both; }
.sync-step-3 { animation: fadeInUp 0.4s ease 1.0s both; }
.sync-step-4 { animation: fadeInUp 0.4s ease 1.4s both; }
.sync-step-5 { animation: fadeInUp 0.4s ease 1.8s both; }

/* Progress bar cresce da esquerda */
.loader-progress-fill {
    animation: progressGrow 2.2s var(--ease-out-expo) 0.2s both;
}
@keyframes progressGrow {
    from { width: 0%; }
    to   { width: 100%; }
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
```

### 7.3 Skeleton Loaders (estado de loading por seção)

Enquanto `is_loading` é true, mostrar skeletons no lugar dos conteúdos:

```python
def skeleton_line(width="100%", height="12px"):
    return rx.box(
        width=width, height=height,
        border_radius=R_CONTROL,
        background="rgba(255,255,255,0.06)",
        class_name="skeleton-shimmer",
    )

def skeleton_kpi():
    return rx.box(
        rx.vstack(
            skeleton_line("40px", "40px"),   # ícone
            skeleton_line("80px"),
            skeleton_line("120px", "32px"),
            skeleton_line("60px"),
            spacing="2",
        ),
        **GLASS_CARD,
    )

def skeleton_chart(height="300px"):
    return rx.box(
        skeleton_line(height=height),
        **GLASS_CARD,
    )

# CSS shimmer
# .skeleton-shimmer {
#     background: linear-gradient(90deg,
#         rgba(255,255,255,0.04) 25%,
#         rgba(255,255,255,0.08) 50%,
#         rgba(255,255,255,0.04) 75%);
#     background-size: 200% 100%;
#     animation: shimmerMove 2s linear infinite;
# }
# @keyframes shimmerMove {
#     from { background-position: -200% 0; }
#     to   { background-position:  200% 0; }
# }
```

**Padrão de uso com loading_wrapper:**
```python
def page_content():
    return rx.cond(
        GlobalState.is_loading,
        rx.vstack(skeleton_kpi_grid(), skeleton_chart(), spacing="4"),
        rx.vstack(actual_kpi_grid(), actual_chart(), spacing="4",
                  class_name="animate-enter"),
    )
```

---

## 8. Conexão com Supabase

### 8.1 Configuração (`core/supabase_client.py`)

```python
import httpx, threading

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service key bypassa RLS

BASE_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}

# Pool singleton thread-safe
_client: httpx.Client | None = None
_lock = threading.Lock()

def _get_client() -> httpx.Client:
    global _client
    with _lock:
        if _client is None or _client.is_closed:
            _client = httpx.Client(
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                    keepalive_expiry=20,
                ),
                timeout=httpx.Timeout(connect=8.0, read=20.0, write=30.0, pool=5.0),
            )
    return _client
```

### 8.2 Funções Core

```python
def sb_select(
    table: str,
    select: str = "*",
    filters: dict = None,          # {"col": "val"} → eq; {"col__ilike": "%val%"} → ILIKE
    order: str = None,             # "created_at.desc"
    limit: int = None,
) -> list[dict]:
    """GET — retorna lista de dicts ou [] em caso de erro."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {"select": select}
    if filters:
        for k, v in filters.items():
            if k.endswith("__ilike"):
                params[k[:-7]] = f"ilike.{v}"
            else:
                params[k] = f"eq.{v}"
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)
    resp = _get_client().get(url, headers=BASE_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()

def sb_insert(table: str, data: dict) -> dict:
    """POST — retorna o registro inserido."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {**BASE_HEADERS, "Prefer": "return=representation"}
    resp = _get_client().post(url, headers=headers, json=data)
    resp.raise_for_status()
    result = resp.json()
    return result[0] if isinstance(result, list) else result

def sb_update(table: str, data: dict, filters: dict) -> list[dict]:
    """PATCH — atualiza registros matching filters."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {k: f"eq.{v}" for k, v in filters.items()}
    resp = _get_client().patch(url, headers=BASE_HEADERS, params=params, json=data)
    resp.raise_for_status()
    return resp.json()

def sb_delete(table: str, filters: dict) -> None:
    """DELETE — remove registros matching filters."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {k: f"eq.{v}" for k, v in filters.items()}
    _get_client().delete(url, headers=BASE_HEADERS, params=params).raise_for_status()

def sb_upsert(table: str, data: dict, on_conflict: str = "id") -> dict:
    """INSERT OR UPDATE via Prefer: resolution=merge-duplicates."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        **BASE_HEADERS,
        "Prefer": f"return=representation,resolution=merge-duplicates",
        "on_conflict": on_conflict,
    }
    resp = _get_client().post(url, headers=headers, json=data)
    resp.raise_for_status()
    result = resp.json()
    return result[0] if isinstance(result, list) else result

def sb_select_paginated(
    table: str, page: int = 0, per_page: int = 50,
    filters: dict = None, order: str = None,
) -> tuple[list[dict], int]:
    """Retorna (rows, total_count) usando Range header do PostgREST."""
    start = page * per_page
    end   = start + per_page - 1
    url   = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        **BASE_HEADERS,
        "Range":       f"{start}-{end}",
        "Prefer":      "count=exact",
    }
    params = {"select": "*"}
    if filters:
        params.update({k: f"eq.{v}" for k, v in filters.items()})
    if order:
        params["order"] = order
    resp = _get_client().get(url, headers=headers, params=params)
    resp.raise_for_status()
    total = int(resp.headers.get("Content-Range", "*/0").split("/")[-1] or 0)
    return resp.json(), total

def sb_rpc(function_name: str, params: dict = None) -> any:
    """Chama uma Postgres function via /rpc/."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    resp = _get_client().post(url, headers=BASE_HEADERS, json=params or {})
    resp.raise_for_status()
    return resp.json()
```

### 8.3 Retry Logic

```python
import time

def _with_retry(fn, max_retries=2):
    """Retry automático em falhas de rede."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError) as e:
            if attempt == max_retries:
                raise
            # Recria o pool e tenta de novo
            _reset_client()
            time.sleep(0.5 * (attempt + 1))
```

---

## 9. Carregamento & Cache de Dados

### 9.1 DataLoader — Cache Multicamada

```
Supabase (fonte) → Cache Pickle 1h (fallback) → Estado do app
                      ↓
                Arquivo: /tmp/projeto_cache_{client_id[:8]}.pkl
```

```python
class DataLoader:
    def __init__(self, client_id: str):
        self.client_id = client_id
        safe = client_id[:8].replace("-", "")
        self._cache_path = Path(tempfile.gettempdir()) / f"projeto_cache_{safe}.pkl"
        self._cache_ttl  = 3600  # 1 hora

    def load_all(self) -> dict[str, pd.DataFrame]:
        """Carrega todas as tabelas. Usa cache se válido."""
        cached = self._load_cache()
        if cached:
            return cached
        data = self._fetch_all_parallel()
        self._save_cache(data)
        return data

    def _fetch_all_parallel(self) -> dict[str, pd.DataFrame]:
        """ThreadPoolExecutor com 5 workers — carrega tabelas em paralelo."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        TABLE_MAP = {
            "contratos":              "contratos",
            "hub_atividades":         "projeto",
            "fin_custos":             "financeiro",
            "om_geracoes":            "om",
        }

        results = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(sb_select, table, filters={"client_id": self.client_id}): key
                for table, key in TABLE_MAP.items()
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    rows = future.result()
                    results[key] = self._normalize(pd.DataFrame(rows))
                except Exception as e:
                    results[key] = pd.DataFrame()
        return results

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza colunas: strip acentos, parse BRL, parse %, datas."""
        df.columns = [_strip_accents(c).lower().replace(" ", "_") for c in df.columns]
        for col in df.select_dtypes(include="object").columns:
            if df[col].str.startswith("R$", na=False).any():
                df[col] = df[col].apply(_parse_brl)
            elif df[col].str.endswith("%", na=False).any():
                df[col] = pd.to_numeric(df[col].str.rstrip("%"), errors="coerce")
        return df
```

### 9.2 Conversores de Dados

```python
def _parse_brl(val: str) -> float:
    """'R$ 80.000,00' → 80000.0"""
    if not val or not isinstance(val, str):
        return 0.0
    val = val.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return 0.0

def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def _utc_to_brt(ts: str) -> str:
    """ISO UTC → 'DD/MM HH:MM' no fuso BRT (UTC-3)."""
    from datetime import datetime, timezone, timedelta
    BRT = timezone(timedelta(hours=-3))
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")[:32])
        return dt.astimezone(BRT).strftime("%d/%m %H:%M")
    except Exception:
        return ts[:16]
```

### 9.3 Padrão on_load em Páginas

```python
# Em cada página protegida:
app.add_page(
    minha_pagina,
    route="/minha-rota",
    on_load=[GlobalState.load_data, ModuleState.load_page],
)

# GlobalState.load_data — skip se dados já carregados:
async def load_data(self):
    if self.contratos_list:          # dados já presentes → skip
        return
    self.is_loading = True
    yield
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(
        None,
        lambda: DataLoader(client_id=self.current_client_id).load_all()
    )
    self._contratos_df = raw.get("contratos", pd.DataFrame())
    # ... popular demais dfs e listas serializadas
    self.is_loading = False
```

---

## 10. Layout Shell — Sidebar & Top Bar

### 10.1 Sidebar

**Dimensões e comportamento:**
```python
# Expandida: 288px | Colapsada: 64px
# Transição: width 0.25s cubic-bezier(0.4, 0, 0.2, 1)
# Mobile: drawer lateral (rx.drawer) com trigger no top bar
```

**Estrutura interna:**
```
┌──────────────────┐
│  [LOGO/BANNER]   │  64px altura — banner.png expandida / icon.png colapsado
├──────────────────┤
│  PRINCIPAL       │  ← section label (10px, FONT_MONO, TEXT_MUTED, uppercase)
│  ◈ Visão Geral   │
│  ◈ Hub Operações │
├──────────────────┤
│  OPERACIONAL     │
│  ◈ Financeiro    │
│  ◈ O&M           │
│  ◈ Analytics     │
│  ◈ Previsões     │
│  ◈ Chat IA       │
├──────────────────┤
│  ADMINISTRAÇÃO   │  ← visível apenas se módulo liberado
│  ◈ Relatórios    │
│  ◈ Editar Dados  │
├──────────────────┤
│  [AVATAR USER]   │  ← parte inferior, com popover
│  Nome / Role     │
│  [···] popover   │  → Logs, Alertas, Gerenciar Usuários, Logout
└──────────────────┘
```

**Item ativo vs inativo:**
```python
def _item_style(is_active: bool):
    return {
        "padding":         "9px 14px",
        "border_radius":   R_CONTROL,
        "border_left":     f"2px solid {'var(--copper-500)' if is_active else 'transparent'}",
        "background":      "rgba(201,139,42,0.08)" if is_active else "transparent",
        "color":           TEXT_WHITE if is_active else TEXT_MUTED,
        "transition":      "all 0.15s ease",
        "_hover": {
            "background":   "rgba(255,255,255,0.03)",
            "border_left":  f"2px solid rgba(201,139,42,0.3)",
            "color":        TEXT_PRIMARY,
        },
    }
```

**Toggle button (collapsar/expandir):**
```python
rx.box(
    rx.icon("chevron-left" if is_open else "chevron-right", size=14, color=TEXT_MUTED),
    position="absolute",
    right="-11px",
    top="52px",
    width="22px",
    height="22px",
    border_radius="50%",
    background=BG_SURFACE,
    border=f"1px solid {BORDER_SUBTLE}",
    display="flex",
    align_items="center",
    justify_content="center",
    cursor="pointer",
    on_click=GlobalState.toggle_sidebar,
    z_index="100",
)
```

### 10.2 Top Bar

**Altura:** 52px fixo, `position: sticky, top: 0, z_index: 40`

**Conteúdo:**
```
[PAGE TITLE]           [sub-tabs opcionais]           [user badge]
 Visão Geral           Tab1 | Tab2 | Tab3             Gustavo · Admin
```

**Sub-tabs (padrão para módulos com múltiplas visões):**
```python
def _tab_item(label: str, href: str, active: bool):
    return rx.link(
        label,
        href=href,
        font_family=FONT_MONO,
        font_size="12px",
        font_weight="700" if active else "400",
        color=COPPER if active else TEXT_MUTED,
        border_bottom=f"2px solid {COPPER if active else 'transparent'}",
        padding_x="12px",
        padding_y="14px",
        text_decoration="none",
        transition="color 0.15s ease, border-color 0.15s ease",
        _hover={"color": COPPER_LIGHT, "border_bottom": f"2px solid {COPPER_LIGHT}"},
    )
```

### 10.3 Layout Shell (default_layout)

```python
def default_layout(page_content: rx.Component) -> rx.Component:
    return rx.box(
        loading_screen(),           # overlay full-screen quando is_loading=True
        rx.hstack(
            sidebar(),              # fixo na esquerda
            rx.vstack(
                top_bar(),          # sticky no topo
                rx.box(
                    page_content,   # conteúdo da página
                    **MAIN_CONTENT_STYLE,
                    padding_x="clamp(16px, 3vw, 40px)",
                ),
                width="100%",
                height="100vh",
                overflow_y="auto",
                spacing="0",
            ),
            spacing="0",
            width="100%",
            height="100vh",
            overflow="hidden",
        ),
        background=BG_VOID,
        min_height="100vh",
    )

# Em add_page():
app.add_page(
    lambda: default_layout(my_page()),
    route="/minha-rota",
    on_load=[...],
)
```

---

## 11. Gráficos & Visualizações

### 11.1 Eixos Padrão

```python
# X-Axis
rx.recharts.x_axis(
    data_key="mes",
    stroke=TEXT_MUTED,
    font_size=12,
    tick_line=False,
    axis_line=False,
    tick=AXIS_TICK,    # {"fill": TEXT_MUTED, "fontSize": 10, "fontFamily": "JetBrains Mono"}
)

# Y-Axis
rx.recharts.y_axis(
    stroke=TEXT_MUTED,
    font_size=12,
    tick_line=False,
    axis_line=False,
    tick=AXIS_TICK,
    tick_formatter="(v) => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'k' : v",
)

# Grid
rx.recharts.cartesian_grid(
    stroke_dasharray="3 3",
    stroke="rgba(255, 255, 255, 0.04)",
    vertical=False,
)
```

### 11.2 Formatadores de Valor (JS inline)

```python
# Dinheiro: 1500000 → "1,5M" | 50000 → "50,0k"
MONEY_FORMATTER = (
    "(v) => {"
    "if (v >= 1e6) return (v/1e6).toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+'M';"
    "if (v >= 1e3) return (v/1e3).toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:0})+'k';"
    "return v.toLocaleString('pt-BR');"
    "}"
)

# Percentual: 75.3 → "75,3%"
PCT_FORMATTER = "(v) => v.toLocaleString('pt-BR', {minimumFractionDigits:1})+'%'"
```

### 11.3 Bar Chart (Horizontal)

```python
rx.recharts.bar_chart(
    rx.recharts.bar(
        data_key="valor",
        fill=COPPER,
        radius=[0, 3, 3, 0],      # cantos arredondados na ponta
        label={"position": "right", "fill": TEXT_MUTED, "fontSize": 10},
    ),
    rx.recharts.tooltip(
        content_style=TOOLTIP_PREMIUM,
        label_style=TOOLTIP_PREMIUM_LABEL,
        cursor=TOOLTIP_CURSOR,
    ),
    rx.recharts.x_axis(...),
    rx.recharts.y_axis(data_key="categoria", type_="category", width=120),
    data=GlobalState.chart_data,
    layout="vertical",
    height=350,
    width="100%",
    margin={"top": 0, "right": 60, "bottom": 0, "left": 0},
)
```

### 11.4 Line Chart (S-Curve / Série Temporal)

```python
rx.recharts.line_chart(
    rx.recharts.line(
        data_key="previsto",
        stroke=COPPER,
        stroke_width=2,
        dot=False,
        type_="monotone",
    ),
    rx.recharts.line(
        data_key="realizado",
        stroke=PATINA,
        stroke_width=2,
        dot={"fill": PATINA, "r": 4, "strokeWidth": 0},
        type_="monotone",
    ),
    rx.recharts.x_axis(data_key="mes", **AXIS_KWARGS),
    rx.recharts.y_axis(tick_formatter=PCT_FORMATTER, **AXIS_KWARGS),
    rx.recharts.legend(
        icon_type="circle",
        wrapper_style={"fontSize": "11px", "fontFamily": "JetBrains Mono"},
    ),
    rx.recharts.tooltip(
        content_style=TOOLTIP_PREMIUM,
        cursor=TOOLTIP_CURSOR_LINE,
    ),
    rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke="rgba(255,255,255,0.04)", vertical=False),
    data=GlobalState.scurve_data,
    height=300,
    width="100%",
)
```

### 11.5 Pie / Donut Chart

```python
rx.recharts.pie_chart(
    rx.recharts.pie(
        data=GlobalState.status_data,
        data_key="value",
        name_key="name",
        cx="50%",
        cy="50%",
        inner_radius=55,    # donut
        outer_radius=85,
        padding_angle=3,
        # Cada item do array pode ter "fill" próprio (use_data_fill=True)
    ),
    rx.recharts.tooltip(
        content_style=TOOLTIP_PREMIUM,
        formatter="(value, name) => [`${value}`, name]",
    ),
    rx.recharts.legend(
        layout="vertical",
        align="right",
        vertical_align="middle",
        icon_type="circle",
        icon_size=8,
        wrapper_style={"fontSize": "11px", "fontFamily": "JetBrains Mono", "color": TEXT_MUTED},
    ),
    height=240,
    width="100%",
)
```

### 11.6 Composed Chart (Bar + Line)

```python
rx.recharts.composed_chart(
    rx.recharts.bar(data_key="kwh_gerado", fill=COPPER, name="Geração"),
    rx.recharts.line(data_key="kwh_previsto", stroke=PATINA, stroke_width=2, dot=False, name="Previsto"),
    rx.recharts.x_axis(data_key="mes_ano", **AXIS_KWARGS),
    rx.recharts.y_axis(tick_formatter=NUMBER_FORMATTER),
    rx.recharts.tooltip(content_style=TOOLTIP_PREMIUM, cursor=TOOLTIP_CURSOR),
    rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke="rgba(255,255,255,0.04)", vertical=False),
    data=GlobalState.om_chart_data,
    height=400,
    width="100%",
    margin={"top": 10, "right": 20, "bottom": 0, "left": 10},
)
```

### 11.7 Status/Progresso em Cards de Projeto

```python
# Barra de progresso (3px, color varia por status)
rx.box(
    rx.box(
        width=f"{projeto['progresso']}%",
        height="3px",
        background=_status_color(projeto["status"]),
        border_radius="2px",
        transition="width 1.1s ease-out",
    ),
    width="100%",
    height="3px",
    background="rgba(255,255,255,0.06)",
    border_radius="2px",
)

# Cores de status
def _status_color(status: str) -> str:
    return {
        "ok":       "#22c55e",
        "atencao":  WARNING,
        "critico":  DANGER,
    }.get(status, COPPER)
```

---

## 12. Padrões de Event Handlers

### 12.1 Handler Assíncrono Simples

```python
async def load_page(self):
    """Carrega dados específicos do módulo."""
    self.module_loading = True
    yield
    loop = asyncio.get_event_loop()
    rows = await loop.run_in_executor(
        None, lambda: sb_select("minha_tabela", filters={"client_id": self.current_client_id})
    )
    self.my_list = [_normalize(r) for r in rows]
    self.module_loading = False
```

### 12.2 Background Event (para operações longas ou com loading overlay)

```python
@rx.event(background=True)
async def save_record(self):
    """
    CRÍTICO: Background events não seguram o state lock.
    Cada `async with self:` que sai envia um WS message independente.
    """
    # 1. Lê state necessário
    async with self:
        self.is_saving = True
        data = {"campo": self.form_value, "client_id": self.current_client_id}

    # 2. I/O fora do lock (não bloqueia outros eventos)
    import asyncio as _aio
    loop = _aio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, lambda: sb_insert("tabela", data))

        # 3. Atualiza state com resultado
        async with self:
            self.my_list.append(_normalize(result))
            self.is_saving = False
            yield rx.toast.success("Salvo com sucesso!")
    except Exception as e:
        async with self:
            self.is_saving = False
            yield rx.toast.error(f"Erro: {e}")
```

### 12.3 Loading Overlay de Navegação

```python
@rx.event(background=True)
async def navigate_to_detail(self, item_id: str):
    """
    Exibe overlay de loading, carrega dados, navega.
    Dois async with self: separados garantem dois WS flushes distintos.
    """
    async with self:
        self.is_navigating = True    # ← WS flush 1: overlay aparece

    await asyncio.sleep(0.15)        # garante render antes do I/O

    # I/O pesado fora do lock
    loop = asyncio.get_running_loop()
    detail = await loop.run_in_executor(
        None, lambda: sb_select("detalhes", filters={"id": item_id})
    )

    async with self:
        self.detail_data = detail
        self.is_navigating = False   # ← WS flush 2: overlay some
        yield rx.redirect(f"/detalhe/{item_id}")
```

### 12.4 Streaming de IA

```python
@rx.event(background=True)
async def stream_analysis(self):
    """Streaming de texto da IA via thread + asyncio.Queue."""
    import threading

    async with self:
        prompt = self.ai_prompt
        self.ai_text = ""
        self.ai_streaming = True

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _run_stream():
        try:
            for chunk in ai_client.stream(prompt):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

    threading.Thread(target=_run_stream, daemon=True).start()

    buffer = ""
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        buffer += chunk
        # Batch update a cada 200ms
        if len(buffer) > 50:
            async with self:
                self.ai_text += buffer
            buffer = ""
        await asyncio.sleep(0.05)

    if buffer:
        async with self:
            self.ai_text += buffer

    async with self:
        self.ai_streaming = False
```

### 12.5 Regras Críticas do Reflex

```python
# ❌ ERRADO — if em handler com valor reativo
if GlobalState.user_role == "Admin":    # pega o tipo, não o valor
    ...

# ✅ CORRETO — usar await get_state() dentro de background events
async with self:
    role = self.current_user_role       # lê o valor real

# ❌ ERRADO — I/O bloqueante dentro do lock
async with self:
    rows = httpx.get(url).json()        # bloqueia event loop

# ✅ CORRETO — I/O fora do lock
rows = await loop.run_in_executor(None, lambda: httpx.get(url).json())
async with self:
    self.rows = rows

# ❌ ERRADO — rx.callout com filhos diretos
rx.callout("Mensagem")                  # crash

# ✅ CORRETO
rx.callout.root(
    rx.callout.icon(rx.icon("info")),
    rx.callout.text("Mensagem"),
)

# ❌ ERRADO — rx.select.item com value vazio
rx.select.item("Nenhum", value="")      # crash em produção

# ✅ CORRETO — sentinel value
rx.select.item("Nenhum", value="__none__")
# No setter: if val == "__none__": val = ""
```

---

## 13. Páginas Padrão do Sistema

### 13.1 Login (`/login`)

**Layout split-screen:**

```
┌─────────────────────┬──────────────────────┐
│    PAINEL MARCA     │    PAINEL AUTH        │
│    (50% width)      │    (50% width)        │
│                     │                       │
│  Grid cobre fundo   │  [Logo]               │
│  Glow orbs blur     │                       │
│                     │  Nome do Sistema      │
│  Métricas 2x2       │  Tagline              │
│  ┌──┬──┐            │                       │
│  │  │  │            │  [Usuário   ______]   │
│  ├──┼──┤            │  [Senha     ______]   │
│  │  │  │            │                       │
│  └──┴──┘            │  [  ENTRAR  ███████]  │
│                     │                       │
│  Typewriter text    │  Esqueceu a senha?    │
│  Status ticker ──── │                       │
└─────────────────────┴──────────────────────┘
```

**Fundo do painel de marca:**
```css
background: linear-gradient(135deg, BG_DEPTH, BG_VOID);
/* Grid cobre: */
background-image: linear-gradient(rgba(201,139,42,0.04) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(201,139,42,0.04) 1px, transparent 1px);
background-size: 48px 48px;
```

**Glow orbs:**
```python
rx.box(position="absolute", width="300px", height="300px",
       border_radius="50%", top="-100px", left="-100px",
       background="radial-gradient(circle, rgba(201,139,42,0.08) 0%, transparent 70%)",
       filter="blur(40px)")
```

**Progress bar de autenticação (aparece durante check_login):**
```python
rx.cond(
    GlobalState.is_authenticating,
    rx.box(
        rx.box(class_name="auth-progress", height="2px", background=COPPER, border_radius="1px"),
        width="100%", height="2px", background="rgba(255,255,255,0.06)",
        position="absolute", bottom="0", left="0",
    ),
    rx.fragment(),
)
```

### 13.2 Visão Geral / Dashboard Principal (`/`)

**Estrutura da página:**
```
Hero Banner (full-width glass panel)
    ├── "System Online" badge
    ├── Título da página (PAGE_TITLE_STYLE)
    └── Subtítulo + filtro de contrato

KPI Grid (4 colunas, responsive)
    ├── Receita Total
    ├── Contratos Ativos
    ├── Velocidade Média
    └── Health Score

Charts Grid (2 colunas)
    ├── Bar Chart horizontal (Alocação por categoria)
    └── Pie/Donut Chart (Status do portfolio)

Tabela Resumo (opcional)
```

### 13.3 Logs & Auditoria (`/logs-auditoria`)

**Apenas roles com módulo `logs_auditoria`.**

**Estrutura:**
```
Header: título + filtros (categoria, status, username, data_from, busca)

Stats do Dia (4 mini-cards):
  Total  |  Logins  |  Edições  |  Erros

Tabela paginada (50/página):
  Timestamp | Usuário | Categoria | Ação | Status | [Detalhe]

Painel lateral de detalhe (slide-in ao clicar na linha):
  Metadata JSON formatado
```

**Tabela Supabase `system_logs`:**
```sql
id              uuid PRIMARY KEY DEFAULT gen_random_uuid()
created_at      timestamptz DEFAULT now()
username        text
action_category text    -- LOGIN, DATA_EDIT, RDO_CREATE, ERROR, etc.
action          text    -- descrição da ação
entity_type     text    -- "contrato", "rdo", etc.
entity_id       text
metadata        jsonb   -- dados adicionais
status          text    -- "success" | "error"
ip_address      text
client_id       uuid    -- isolamento multi-tenant
```

**Como logar (fire-and-forget):**
```python
from core.audit_logger import audit_log, AuditCategory
import threading

# Nunca bloqueia o handler principal
threading.Thread(
    target=lambda: audit_log(
        username=self.current_user_name,
        category=AuditCategory.DATA_EDIT,
        action="Editou célula",
        entity_type="contratos",
        entity_id=row_id,
        metadata={"campo": col, "antes": old_val, "depois": new_val},
        status="success",
        client_id=self.current_client_id,
    ),
    daemon=True,
).start()
```

### 13.4 Gerenciar Usuários (`/admin/usuarios`)

**Apenas roles com módulo `gerenciar_usuarios`.**

**2 tabs:**

1. **Usuários** — CRUD na tabela `login`:
   - Listar usuários (filtráveis)
   - Criar/editar (dialog): nome, senha, role (dropdown do BD), projeto atribuído
   - Excluir (confirmar)

2. **Perfis de Acesso** — CRUD na tabela `roles`:
   - Listar roles com ícone + módulos
   - Criar/editar (dialog): nome + ícone picker (24 ícones lucide) + grid de checkboxes (18 módulos, 2 colunas)
   - Excluir (confirmar)

---

## 14. CSS, Animações & Tema Global

### 14.1 Glassmorphism

```css
.glass-panel {
    background: var(--bg-glass);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.glass-panel:hover {
    border-color: var(--border-highlight);
    box-shadow: 0 0 20px var(--copper-glow);
}
```

### 14.2 Animações (`assets/animations.css`)

```css
/* Entrada de página / conteúdo */
.animate-enter {
    animation: routeEnter 0.4s var(--ease-out-expo) both;
}
@keyframes routeEnter {
    from { opacity: 0; transform: translateX(10px); }
    to   { opacity: 1; transform: translateX(0); }
}

/* Fade up */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Pulse Glow (badges de status, ícones ativos) */
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(201,139,42,0); }
    50%       { box-shadow: 0 0 20px 4px rgba(201,139,42,0.3); }
}
.pulse-glow { animation: pulseGlow 2s ease infinite; }

/* Shimmer skeleton */
@keyframes shimmerMove {
    from { background-position: -200% 0; }
    to   { background-position:  200% 0; }
}
.skeleton-shimmer {
    background: linear-gradient(90deg,
        rgba(255,255,255,0.04) 25%,
        rgba(255,255,255,0.08) 50%,
        rgba(255,255,255,0.04) 75%
    );
    background-size: 200% 100%;
    animation: shimmerMove 2s linear infinite;
}

/* Typewriter cursor */
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.typewriter-cursor { animation: blink 1s step-end infinite; }

/* Card hover interativo */
.card-interactive {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card-interactive:hover {
    transform: translateY(-3px);
}
.card-interactive:active {
    transform: translateY(-1px);
}
```

### 14.3 Tooltips Radix (componentes Reflex)

```css
/* Tooltips escuros no tema Deep Tectonic */
.rt-TooltipContent {
    background: #1e3530 !important;
    border: 1px solid rgba(201, 139, 42, 0.3) !important;
    color: #E0E0E0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    border-radius: 4px !important;
}
```

---

## 15. Registro de Páginas & App Entry

### 15.1 `projeto.py` (entry point)

```python
import reflex as rx
from projeto.core import styles as S
from projeto.pages.login import login_page
from projeto.pages.index import index_page
from projeto.pages.logs_auditoria import logs_auditoria_page
from projeto.pages.usuarios import usuarios_page
from projeto.state.global_state import GlobalState
from projeto.state.module_state import ModuleState
from projeto.layouts.default import default_layout

# ── App ──────────────────────────────────────────────────────
app = rx.App(
    style=S.GLOBAL_STYLE,
    stylesheets=[
        S.FONT_URL,             # Google Fonts (Rajdhani, Outfit, JetBrains Mono)
        "/style.css",           # tema + variáveis CSS + scrollbar
        "/animations.css",      # keyframes
    ],
    theme=rx.theme(
        appearance="inherit",   # não sobrescrever com tema Radix
        accent_color="amber",   # fallback para componentes Radix
        radius="none",          # border-radius controlado via styles.py
    ),
    head_components=[
        rx.el.script(           # força dark mode imediato (evita flash branco)
            "document.documentElement.setAttribute('data-color-mode','dark');"
        ),
    ],
)

# ── Páginas públicas ─────────────────────────────────────────
app.add_page(login_page, route="/login")

# ── Páginas protegidas ───────────────────────────────────────
app.add_page(
    lambda: default_layout(index_page()),
    route="/",
    on_load=[GlobalState.guard_index, GlobalState.load_data],
)

app.add_page(
    lambda: default_layout(logs_auditoria_page()),
    route="/logs-auditoria",
    on_load=[GlobalState.require_auth, LogsState.load_page],
)

app.add_page(
    lambda: default_layout(usuarios_page()),
    route="/admin/usuarios",
    on_load=[GlobalState.require_auth, UsuariosState.load_page],
)

# ── Páginas de módulo (exemplo) ───────────────────────────────
app.add_page(
    lambda: default_layout(meu_modulo_page()),
    route="/meu-modulo",
    on_load=[GlobalState.require_auth, MeuModuloState.load_page],
)
```

### 15.2 Ordem de Eventos ao Navegar para uma Página

```
1. Browser acessa /rota
2. Reflex executa on_load handlers em sequência:
   a. GlobalState.require_auth  → redireciona /login se não autenticado
   b. GlobalState.load_data     → skip se dados já carregados (otimização)
   c. ModuleState.load_page     → carrega dados específicos do módulo
3. Frontend recebe state atualizado via WebSocket
4. rx.cond(is_loading, skeleton, content) → renderiza skeleton → conteúdo
5. Animação .animate-enter no conteúdo
```

---

## 16. Checklist para Novo Projeto

### Setup Inicial

- [ ] `reflex init` → configura projeto base
- [ ] Criar estrutura de diretórios (ver seção 2)
- [ ] Copiar `styles.py` com tokens Deep Tectonic
- [ ] Criar `assets/style.css` com variáveis CSS + glassmorphism + scrollbar
- [ ] Criar `assets/animations.css` com keyframes
- [ ] Configurar `.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`

### Supabase

- [ ] Criar tabela `login` (id, user, password, user_role, project, client_id)
- [ ] Criar tabela `roles` (id, name, modules jsonb, icon)
- [ ] Criar tabela `system_logs` (id, created_at, username, action_category, action, entity_type, entity_id, metadata, status, client_id)
- [ ] Inserir primeiro usuário admin com senha hasheada (PBKDF2)
- [ ] Inserir role "Administrador" com todos os módulos em `modules`

### Core

- [ ] Implementar `supabase_client.py` com pool httpx + retry
- [ ] Implementar `data_loader.py` com cache pickle + ThreadPoolExecutor
- [ ] Implementar `auth_utils.py` (hash + verify PBKDF2)
- [ ] Implementar `audit_logger.py` (fire-and-forget)

### State

- [ ] `GlobalState` com vars de auth, dados, AI
- [ ] `UIState` com modais, loading, toasts
- [ ] `load_data()` com skip se já carregado
- [ ] `check_login()` com RBAC via tabela `roles`
- [ ] `require_auth()` guard

### Componentes

- [ ] `sidebar.py` — colapsável, RBAC-driven, mobile drawer
- [ ] `top_bar.py` — sticky, título dinâmico por rota, sub-tabs
- [ ] `loading_screen.py` — 5 steps animados + progress bar
- [ ] `charts.py` — eixos, tooltips, KPI card, bar, line, pie, composed
- [ ] `default.py` — layout shell

### Páginas Mínimas

- [ ] `/login` — split screen, autenticação, redirect por role
- [ ] `/` — dashboard principal, KPIs, gráficos
- [ ] `/logs-auditoria` — tabela paginada, filtros, stats do dia
- [ ] `/admin/usuarios` — CRUD usuários + roles + módulos

### Boas Práticas

- [ ] Todos os eventos I/O pesados em `run_in_executor` ou `@rx.event(background=True)`
- [ ] Loading overlay de navegação: dois `async with self:` separados com `sleep(0.15)` entre eles
- [ ] Sempre `on_load=GlobalState.load_data` — skip interno garante eficiência
- [ ] Nunca usar strings de role hardcoded no frontend — sempre via `allowed_modules`
- [ ] Audit log em todas as ações destrutivas (delete, edit, submit)
- [ ] `rx.select.item` nunca com `value=""` — usar `"__none__"` como sentinel
- [ ] Ops longas (AI, PDF, email) sempre em `threading.Thread(daemon=True)` fire-and-forget

---

*Este documento descreve o framework completo. Cada novo módulo de negócio replica os mesmos padrões: state próprio, page com default_layout, on_load guard + load_data + load_page, componentes do design system, audit log nas ações.*
