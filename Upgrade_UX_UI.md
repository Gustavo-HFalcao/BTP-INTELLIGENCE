# 📦 EXECUTION SCOPE – UX/UI ENTERPRISE REFACTOR

**Stack:** Python + Reflex + Supabase + OpenAI

---

## 1️⃣ GLOBAL DESIGN SYSTEM (OBRIGATÓRIO)
### 1.1 Criar Design Tokens Globais
Criar arquivo:
`components/theme.py`

**Definir:**
*   **Colors**
    *   `primary`: #4F46E5
    *   `primary_hover`: #4338CA
    *   `background_main`: #0F172A
    *   `background_card`: #1E293B
    *   `background_soft`: #334155
    *   `border_subtle`: #334155
    *   `text_primary`: #F8FAFC
    *   `text_secondary`: #CBD5E1
    *   `text_muted`: #94A3B8
    *   `success`: #22C55E
    *   `warning`: #F59E0B
    *   `danger`: #EF4444
*   **Radius**
    *   `sm`: 8px
    *   `md`: 14px
    *   `lg`: 20px
*   **Spacing Scale**
    *   4px base grid
    *   Use 8, 12, 16, 24, 32, 48
*   **Typography Scale**
    *   `h1`: 28px semibold
    *   `h2`: 22px semibold
    *   `h3`: 18px medium
    *   `body`: 15px regular
    *   `caption`: 13px

*Apply globally via Reflex theme configuration.*

---

## 2️⃣ GLOBAL LOADING SYSTEM
### 2.1 Criar componente Skeleton
Criar:
`components/skeleton.py`

**Componente:**
*   Animated pulse
*   Border radius `md`
*   Height customizável
*   Width customizável

### 2.2 Criar wrapper universal de loading
Criar HOC:
`components/loading_wrapper.py`

**Props:**
*   `is_loading`: bool
*   `skeleton_layout`: component
*   `content`: component

**Regra:**
*   Nunca renderizar valores 0 durante loading.
*   Se `is_loading = True` → mostrar skeleton.
*   Após data load → fade in 150ms.

### 2.3 Delay anti-flicker
**Implementar:**
*   Tempo mínimo de loading visual: 350ms (Mesmo que API responda em 50ms).

---

## 3️⃣ CHAT – REFATORAÇÃO COMPLETA
**Criar:**
```text
components/chat/
    chat_container.py
    chat_bubble.py
    chat_input.py
    chat_suggestions.py
```

### 3.1 Layout do Chat
**Estrutura:**
*   Header fixo com: Nome "Assistente Executivo" | Badge (Contexto atual da página).
*   Área scrollável central.
*   Input fixo inferior.
*   Desktop: Max width 760px, Centralizado.
*   Mobile: 100% width, Padding lateral 12px.

### 3.2 Chat Bubble
*   **Usuário:** Alinhado à direita, Background `primary`, Texto branco.
*   **Assistente:** Alinhado à esquerda, Background `background_card`, Borda sutil.
*   **Padding:** 14px 18px
*   **Radius:** `lg`
*   **Spacing vertical:** 16px entre mensagens.

### 3.3 Streaming Real
**Implementar:**
*   Resposta parcial incremental.
*   Atualizar state string progressivamente.
*   Intervalo 20–40ms por chunk.
*   Cursor piscando `▍` no final.
*   Remover cursor ao finalizar.

### 3.4 Estado de Resposta
**Enquanto aguardando:**
*   Mostrar bubble vazia com 3 dots animados pulsing.
*   OU Skeleton lines com largura variável.
*   *Nunca deixar área parada.*

### 3.5 Prompt Suggestions
**Abaixo do input:**
Botões:
*   "Resumir dados"
*   "Detectar riscos"
*   "Explicar queda"
*   "Gerar insights estratégicos"
*   *Ao Clicar:* Preenche input automaticamente e dispara submit.

### 3.6 Botão Flutuante Global
**Se chat for global:**
*   Floating action button (Bottom-right).
*   Glow sutil animado.
*   Tooltip: "Assistente IA".
*   Ao clicar: Abrir painel lateral com slide 200ms.

---

## 4️⃣ TRANSIÇÕES ENTRE PÁGINAS
**Implementar sistema global:**
*   Fade out 120ms.
*   Mostrar skeleton layout da próxima página.
*   Fade in 150ms.
*   *Nunca permitir:* Flash de valores zerados ou Layout saltando.

---

## 5️⃣ DASHBOARD IMPROVEMENTS
### 5.1 Cards
**Atualizar todos os cards:**
*   Padding interno 24px
*   Border radius `lg`
*   Shadow suave
*   Hover subtle `translateY(-2px)`

### 5.2 Hierarquia Visual
*   **Título seção:** `h2`, Margin-bottom 16px
*   **Subtítulo:** `caption`, `text_secondary`
*   *Nunca usar mesmo peso para tudo.*

### 5.3 Empty States
**Se tabela vazia:**
*   Mostrar: Ícone + Texto "Nenhum dado encontrado" + Subtexto explicativo.
*   *Nunca deixar apenas tabela vazia vazando grid isolado.*

---

## 6️⃣ MOBILE-FIRST – RDO
**Refatorar como Wizard:**
Criar `components/rdo/stepper.py`

**Etapas:** Equipe → Equipamentos → Serviços → Ocorrências → Revisão.

**Mobile:**
*   1 etapa por tela.
*   Botão fixo inferior: "Próximo" / "Voltar".
*   Inputs: Min height 48px, Margin-bottom 16px, Labels acima do campo.

---

## 7️⃣ MOBILE-FIRST – REEMBOLSO
**Layout ideal:**
*   Botão grande: "Tirar Foto"
*   Preview imagem.
*   Card resultado IA:
    *   *Se validado:* Border verde, Badge "Validado".
    *   *Se divergência:* Border amarelo, Badge "Divergência detectada".
    *   *Se falha 3x:* Mostrar botão "Forçar envio sob auditoria".

---

## 8️⃣ MICROINTERAÇÕES
**Implementar:**
*   Hover states suaves (120ms)
*   Click scale 0.98
*   Botões com feedback visual
*   Inputs com focus ring `primary`

---

## 9️⃣ RESPONSIVIDADE COMPLETA
**Grid:**
*   Desktop: 12 col grid
*   Tablet: 8 col
*   Mobile: 4 col

**Breakpoints:**
*   sm: 640px
*   md: 768px
*   lg: 1024px
*   xl: 1280px

**No mobile:**
*   Sidebar vira drawer
*   Cards 100% width
*   Tabelas viram scroll horizontal nativo.

---

## 🔟 PERFORMANCE
*   Lazy load de gráficos.
*   Memoizar DataFrames transformados.
*   Não re-renderizar chat inteiro a cada token.
*   Separar estado de streaming do estado global.

---

## 1️⃣1️⃣ QUALIDADE VISUAL FINAL
**Objetivo visual:**
*   Espaçamento generoso (Nunca elementos colados juntas).
*   Consistência total de radius e hierarquia top down.
*   Cores com contraste AA mínimo.
*   Dark mode consistente ao extremo.

---

## 1️⃣2️⃣ EXPECTATIVA FINAL E INSTRUÇÕES PRO CLAUDE CODE
**Após implementação:**
A UX deve subir drasticamente para nível comparável a interfaces Tier 1 *(Stripe Dashboard, Linear, Notion AI, Vercel Analytics)*.

**INSTRUÇÃO FINAL PARA CLAUDE CODE:**
Refatorar a aplicação inteira aplicando restritamente os pontos deste framework:
1.  Design System Global
2.  Loading Universal Anti-flicker
3.  Chat Premium com Streaming Real
4.  Wizard Mobile no RDO
5.  Reembolso com Feedback Visual Imersivo (IA)
6.  Transições Suaves
7.  Sistema Responsivo Real

**Restrições CRÍTICAS de Engenharia:**
> ⚠️ **NÃO** alterar regras de negócio.
> ⚠️ **NÃO** alterar consultas e integrações de Banco (Supabase) ou chamadas da API (OpenAI / ReportLab).
> ⚠️ APENAS melhoria estrutural de marcação (Componentização Reflex) e visual/estilo.
> Implementar tudo de forma **modular** em `components/` puxando o token de paleta como base de design, e não hardcoded nas páginas de destino.
