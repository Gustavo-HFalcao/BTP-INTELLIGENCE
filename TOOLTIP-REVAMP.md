Você vai implementar um sistema de tooltips premium enterprise no projeto BomTempo (Python + Reflex).
Stack: Python 3.12, Reflex 0.8.x, Recharts via rx.recharts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTO TÉCNICO CRÍTICO — LEIA ANTES DE QUALQUER COISA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O tooltip padrão do Recharts (graphing_tooltip com content_style/formatter) renderiza
um <ul><li> genérico e feio. A solução real é o prop `content=` que aceita uma função
React completa. Em Reflex isso se faz EXCLUSIVAMENTE assim:

    rx.recharts.graphing_tooltip(
        content=rx.Var.create(JS_STRING, _var_is_string=False),
        cursor={"strokeWidth": 1, "fill": "rgba(201,139,42,0.06)"},
    )

Onde JS_STRING é uma IIFE (Immediately Invoked Function Expression) que retorna
uma função React. React.createElement está disponível globalmente no bundle Reflex.
NÃO use JSX. NÃO tente importar React. NÃO crie componentes Reflex para isso.

Exemplo mínimo válido:
    js = """
    (function() {
      return function(props) {
        var active = props.active, payload = props.payload, label = props.label;
        if (!active || !payload || !payload.length) return null;
        return React.createElement('div', {
          style: {background:'#141414', border:'1px solid rgba(255,255,255,0.1)',
                  borderRadius:'12px', padding:'14px 16px', color:'#e8e6df',
                  fontSize:'13px', minWidth:'200px', pointerEvents:'none'}
        },
          React.createElement('div', {style:{fontWeight:'500',marginBottom:'8px'}}, label),
          payload.map(function(p, i) {
            return React.createElement('div', {key:i, style:{color:p.color}},
              p.name + ': ' + p.value
            );
          })
        );
      };
    })()
    """
    return rx.recharts.graphing_tooltip(
        content=rx.Var.create(js, _var_is_string=False)
    )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 1 — AUDITORIA (faça isso PRIMEIRO, sem criar nenhum arquivo ainda)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Busque em bomtempo/pages/ e bomtempo/components/ TODAS as ocorrências de:
   - graphing_tooltip
   - rx.recharts.tooltip
   - chart_tooltip
   - hover_card (existente)

2. Para cada ocorrência, registre:
   - Arquivo e número de linha
   - Função Python que contém o gráfico
   - Tipo de gráfico: bar_chart / area_chart / line_chart / pie_chart / composed_chart
   - data_key de cada série no gráfico
   - Contexto semântico (receita? físico? status? alerta?)

3. Mostre o inventário completo antes de avançar.
   Preciso aprovar antes de você tocar em qualquer arquivo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 2 — CRIAR bomtempo/components/tooltips.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Crie o arquivo bomtempo/components/tooltips.py com as seguintes 5 funções.
Implemente EXATAMENTE conforme as especificações abaixo, sem simplificar.

── DESIGN SYSTEM (aplicar em TODAS as funções) ──────────────

Variáveis CSS compartilhadas — cole isso como constantes Python no topo:

TOOLTIP_BASE_STYLE = "background:#141414;border:1px solid rgba(255,255,255,0.10);border-radius:12px;padding:14px 16px;min-width:220px;max-width:300px;box-shadow:0 8px 32px rgba(0,0,0,0.6);font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;font-size:13px;color:#e8e6df;pointer-events:none;"

Paleta:
- amber principal: #c98b2a
- verde sucesso: #4ead78
- vermelho alerta: #e05a5a
- azul info: #5282dc
- teal secundário: #2dd4bf
- texto primário: #f0ede6
- texto secundário: #7a7870
- divider: rgba(255,255,255,0.07)
- row border: rgba(255,255,255,0.04)

── FUNÇÃO 1: tooltip_money() ────────────────────────────────

Assinatura:
def tooltip_money(
    label_subtitle: str = "Receita contratada",
    icon: str = "🏗",
    show_progress: bool = True,
    currency: str = "R$",
) -> rx.Component

O que renderiza:
- Header: ícone 28x28px (fundo rgba(201,139,42,0.15)) + título (vem do `label` do Recharts) + subtitle
- Uma row por série do payload: dot colorido (cor da série) + nome + valor formatado
  - Formatação: >= 1M → "R$ 3,2M", >= 1K → "R$ 450K", senão decimais pt-BR
- Barra de progresso (se show_progress=True E payload.length >= 2):
  - Calcula % = (payload[1].value / payload[0].value) * 100
  - Cor da barra: >= 80% verde, >= 50% amber, < 50% vermelho
  - Label "Execução financeira" + percentual colorido à direita
- cursor: {"strokeWidth": 1, "fill": "rgba(201,139,42,0.06)"}

── FUNÇÃO 2: tooltip_scurve() ────────────────────────────────

Assinatura:
def tooltip_scurve(currency: str = "R$") -> rx.Component

Espera estas data_keys no payload (extrai por p.dataKey):
- previsto_pct, realizado_pct (valores em %)
- previsto_fin, realizado_fin (valores monetários)

O que renderiza:
- Header: ícone 📈 + label do período + "Curva S — Físico / Financeiro"
- 4 rows: Previsto físico (#c98b2a), Realizado físico (#4ead78),
         Previsto financeiro (#5282dc), Realizado financeiro (#2dd4bf)
- Divider
- Row SPI = realizado_pct / previsto_pct:
  - >= 1.0 → badge verde "▲ X.XXX · Adiantado"
  - >= 0.9 → badge amber "▼ X.XXX · Atenção"
  - < 0.9  → badge vermelho "▼ X.XXX · Em atraso"
- Row CPI = realizado_fin / previsto_fin (mesma lógica de cores)
- cursor: {"strokeWidth": 1, "fill": "rgba(82,130,220,0.04)"}

── FUNÇÃO 3: tooltip_pie() ────────────────────────────────

Assinatura:
def tooltip_pie(
    title_field: str = "name",
    value_label: str = "projetos",
) -> rx.Component

O que renderiza:
- Header: ícone 📋 + nome do segmento + "Status do Portfolio"
- Número grande (32px, cor do segmento) centralizado + label "de N projetos totais"
  - Total: usa item.payload.total se existir, senão calcula via item.percent
- Row "Participação" + percentual (cor do segmento)
- Row "Status" + badge colorido baseado no nome:
  "Em execução" → verde, "Em planejamento" → amber,
  "Concluído" → azul, "Atrasado" / "Pausado" → vermelho
- cursor: False (pie chart não usa cursor)

── FUNÇÃO 4: tooltip_gantt() ────────────────────────────────

Assinatura:
def tooltip_gantt() -> rx.Component

Lê os campos do payload[0].payload (objeto de dados):
name, categoria, responsavel, progresso (0-100), status
("em_execucao"|"concluido"|"em_planejamento"|"atrasado"),
inicio, fim, hoje, dias_restantes, predecessoras

O que renderiza:
- Header: ícone ⚡ + name (truncado com text-overflow:ellipsis) + categoria
- Row "Responsável" (só se existir no payload)
- Row "Progresso" com valor colorido (>= 80 verde, >= 40 azul, < 40 amber)
- Barra de progresso: gradient linear #5282dc → #2dd4bf
- Row "Dias restantes" (só se existir)
- Row "Status" com badge mapeado:
  em_execucao → azul "🔵 Em execução"
  concluido   → verde "✓ Concluído"
  em_planejamento → amber "⏳ Planejado"
  atrasado    → vermelho "⚠ Atrasado"
- Seção de datas (3 colunas: Início | Hoje (amber) | Término)
  border-top separando do corpo principal
- Row "Predecessoras" (só se existir)
- cursor: {"fill": "rgba(82,130,220,0.04)", "strokeWidth": 0}

── FUNÇÃO 5: hover_card_kpi() ────────────────────────────────

Assinatura:
def hover_card_kpi(
    trigger: rx.Component,
    title: str,
    subtitle: str,
    icon: str = "📊",
    icon_bg: str = "rgba(201,139,42,0.15)",
    rows: list[tuple[str, str, str]],  # (label, valor, cor)
    footer: str = "",
    footer_badge: str = "",
    footer_badge_color: str = "amber",
) -> rx.Component

Usa rx.hover_card.root / trigger / content.
O content é um rx.vstack com os mesmos padrões visuais das outras funções
(fundo #141414, border, etc.) mas construído com componentes Reflex nativos.

cor nos rows mapeia para: green→#4ead78, amber→#c98b2a, red→#e05a5a,
blue→#5282dc, ""→#f0ede6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 3 — APLICAR EM TODOS OS ARQUIVOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Após criar tooltips.py, aplique em TODOS os arquivos do inventário da Fase 1.
Para cada arquivo:

1. Adicione o import no topo:
   from bomtempo.components.tooltips import (
       tooltip_money, tooltip_scurve, tooltip_pie,
       tooltip_gantt, hover_card_kpi,
   )

2. Mapeamento de qual função usar por contexto semântico:
   - gráficos de receita, custo, financeiro → tooltip_money()
   - curvas S, avanço físico+financeiro → tooltip_scurve()
   - pizza/donut de status, distribuição → tooltip_pie()
   - gantt, cronograma, atividades → tooltip_gantt()
   - qualquer gráfico de barra simples sem financeiro → tooltip_money(show_progress=False)
   - KPI cards, números fora de gráficos → hover_card_kpi()

3. Remova completamente os imports antigos que ficarem órfãos
   (chart_tooltip, money_formatter_js, etc.) SE não forem usados em mais nada.

4. Após cada arquivo: rode `python -c "from bomtempo.pages.[modulo] import *"`
   para confirmar que não há erros de import antes de avançar pro próximo.

Ordem de execução:
1. bomtempo/components/charts.py (manter compatibilidade — só adicionar exports novos)
2. bomtempo/pages/hub_operacoes.py (maior, mais impacto)
3. bomtempo/pages/financeiro.py
4. bomtempo/pages/rdo_dashboard.py
5. bomtempo/pages/reembolso_dashboard.py
6. Todos os outros pages/ com tooltips identificados no inventário

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 4 — HOVER_CARD NOS KPIs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Identifique nos arquivos de pages os elementos que exibem KPIs numéricos:
totais de alertas, valores financeiros agregados, contagens de projetos, etc.

REGRA: só adicione hover_card_kpi() onde os dados já existem no State.
Se o dado não existir, anote como TODO mas NÃO invente dados nem crie
novos campos no State — isso é fora do escopo desta tarefa.

Para cada KPI encontrado com dados disponíveis:
- Envolva o componente existente com hover_card_kpi(trigger=..., rows=[...])
- Use os campos do State que já estão sendo exibidos na página

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 5 — VERIFICAÇÃO FINAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rode estes greps e confirme que o resultado está zerado:
1. grep -r "content_style=_TOOLTIP_STYLE" bomtempo/
2. grep -r "chart_tooltip(formatter=" bomtempo/
3. grep -r "rx.recharts.tooltip(" bomtempo/pages/

Se algum resultado aparecer, substitua antes de encerrar.

Entregue um resumo final com:
- Total de tooltips substituídos por arquivo
- Funções usadas por arquivo
- Lista de TODOs (hover_cards que precisariam de novos dados no State)
- Qualquer arquivo ignorado e por quê

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESTRIÇÕES — NÃO FAÇA ISSO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NÃO use sed/regex cego para substituição em massa
- NÃO use JSX dentro das strings JavaScript
- NÃO importe React no JS (já está disponível globalmente)
- NÃO crie novos State vars ou backend code
- NÃO modifique bomtempo/core/ — apenas components/ e pages/
- NÃO simplifique o design das funções "para economizar linhas"
- NÃO avance para a próxima fase sem confirmar que a atual não quebrou nada


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APÊNDICE TÉCNICO — ERROS CONHECIDOS E COMO EVITÁ-LOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O Reflex compila Python → JSX via Vite/OXC. O OXC é um parser Rust extremamente
rígido com JS. Os erros abaixo JÁ ACONTECERAM neste projeto. Siga as regras
ou o build vai quebrar com "Invalid Character" ou "Unexpected token".

── ERRO #1 (CRÍTICO): CSS string vs JS style object ─────────────────────────

ERRADO — passa uma string CSS onde o React espera um objeto JS:
    style: "background:#141414; border:1px solid rgba(0,0,0,0.1); padding:14px;"

CERTO — sempre um objeto JS com camelCase:
    style: {background:'#141414', border:'1px solid rgba(0,0,0,0.1)', padding:'14px'}

REGRA: dentro de React.createElement, o prop `style` é SEMPRE um objeto {}.
Nunca uma string. Nunca CSS inline. Nem mesmo para strings longas.

── ERRO #2 (CRÍTICO): aspas simples dentro de strings Python ────────────────

Python usa aspas simples para delimitar a string JS. Font-families com espaço
precisam de aspas na CSS — isso cria conflito de delimitadores.

ERRADO:
    js = "fontFamily: 'JetBrains Mono, monospace'"
    # O OXC lê: fontFamily: '  → abre string
    #           JetBrains Mono, monospace  → texto fora da string
    #           '  → fecha string que não estava aberta → crash

CERTO — use aspas duplas dentro do objeto JS para valores de string:
    js = 'fontFamily: "JetBrains Mono, monospace"'

OU — use template Python para isolar:
    FONT = '"JetBrains Mono, monospace"'
    js = f"fontFamily: {FONT}"

REGRA GERAL para o arquivo tooltips.py inteiro:
- Use aspas DUPLAS para todos os valores de string dentro do JS
- Use aspas SIMPLES apenas para delimitar a string Python
- NUNCA misture aspas simples dentro de strings Python simples

Exemplo correto completo:
    js = """
    (function() {
      return function(props) {
        return React.createElement("div", {
          style: {
            background: "#141414",
            fontFamily: "'Inter', sans-serif",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "12px"
          }
        }, "Conteúdo");
      };
    })()
    """

── ERRO #3: quebras de linha e indentação dentro do JS ──────────────────────

Python f-strings com triple-quotes preservam newlines e indentação.
O OXC não tolera newlines no meio de strings JS não terminadas.

ERRADO (newline no meio de um valor de string JS):
    style_str = """
    background: #141414;
    border: 1px solid red;
    """
    js = f"style: '{style_str}'"
    # Resulta em: style: '
    #   background: #141414;   ← newline inesperado → crash

CERTO — nunca quebre valores de string JS em múltiplas linhas:
    js = """
    React.createElement("div", {style: {background: "#141414", border: "1px solid red"}})
    """

── ERRO #4: f-strings Python com chaves JS ──────────────────────────────────

Objetos JS usam {}. f-strings Python interpretam {} como interpolação.

ERRADO:
    js = f"var d = payload[0]; return React.createElement('div', {style:{color:'red'}})"
    # Python tenta interpolar {style:{color:'red'}} como expressão Python → SyntaxError

CERTO — em f-strings, duplique TODAS as chaves JS:
    js = f"var d = payload[0]; return React.createElement('div', {{style:{{color:'red'}}}})"

OU — use string comum (sem f) quando não precisar de interpolação Python:
    js = "var d = payload[0]; return React.createElement('div', {style:{color:'red'}})"

REGRA: prefira strings Python normais (sem f) para o corpo JS. Use f-string
apenas na linha de invocação final para interpolar 1-2 parâmetros Python.

Exemplo do padrão correto:
    def tooltip_money(currency: str = "R$") -> rx.Component:
        # Parâmetros Python viram constantes JS no topo da IIFE
        js = """
    (function() {
      var CURRENCY = \"""" + currency + """\";
      var fmt = function(v) {
        if (v >= 1e6) return CURRENCY + ' ' + (v/1e6).toFixed(1) + 'M';
        return CURRENCY + ' ' + v.toFixed(2);
      };
      return function(props) {
        if (!props.active || !props.payload || !props.payload.length) return null;
        return React.createElement("div", {
          style: {background:"#141414", borderRadius:"12px", padding:"14px 16px",
                  border:"1px solid rgba(255,255,255,0.1)", color:"#e8e6df",
                  fontSize:"13px", minWidth:"200px", pointerEvents:"none"}
        },
          props.payload.map(function(p, i) {
            return React.createElement("div", {key: i}, fmt(p.value));
          })
        );
      };
    })()
    """
        return rx.recharts.graphing_tooltip(
            content=rx.Var.create(js, _var_is_string=False),
            cursor={"strokeWidth": 1, "fill": "rgba(201,139,42,0.06)"},
        )

── ERRO #5: rx.Var.create e aspas no argumento ──────────────────────────────

ERRADO:
    content=rx.Var.create(f'({js})', _var_is_string=False)
    # Se js contiver aspas simples, a f-string corrompe o valor

CERTO:
    content=rx.Var.create(js, _var_is_string=False)
    # Passa a string Python diretamente, sem f-string no wrap

── VALIDAÇÃO OBRIGATÓRIA ANTES DE CADA COMMIT ───────────────────────────────

Após criar/modificar tooltips.py, rode:

    python -c "
    from bomtempo.components.tooltips import (
        tooltip_money, tooltip_scurve, tooltip_pie,
        tooltip_gantt, hover_card_kpi
    )
    import reflex as rx
    # Testa que cada função retorna um Component válido
    t1 = tooltip_money()
    t2 = tooltip_scurve()
    t3 = tooltip_pie()
    t4 = tooltip_gantt()
    print('OK — todos os tooltips instanciam sem erro Python')
    print('Tipo t1:', type(t1))
    "

Se passar, o Python está correto. O único jeito de testar o JS é no browser
(reflex run), mas erros de JS sempre aparecem no console do browser como
"Invalid Character" ou "Unexpected token" — não são erros Python.

Se aparecer erro de Vite/OXC no browser, o diagnóstico é:
1. Abrir .web/app/routes/[pagina]._index.jsx
2. Ir para a linha indicada no erro
3. Procurar: aspas simples dentro de strings JS, CSS strings em vez de
   objetos JS, ou chaves {} não duplicadas em f-strings Python
4. Corrigir em tooltips.py e rodar `reflex run` novamente

── COMPATIBILIDADE CONFIRMADA: o que FUNCIONA em Reflex 0.8.x ──────────────

✓ rx.Var.create(string_js, _var_is_string=False) no prop content=
✓ React.createElement disponível globalmente no bundle
✓ props.active, props.payload, props.label acessíveis normalmente
✓ props.payload[i].value, .name, .color, .dataKey, .fill, .payload
✓ Objetos JS aninhados em style: {{...}}
✓ Array.map(), ternários, IIFEs, var/function (ES5 puro)
✓ rx.hover_card.root/trigger/content funciona normalmente

✗ JSX dentro da string JS (escreva React.createElement, nunca <div>)
✗ Arrow functions (=>) — use function() {} por segurança com OXC
✗ Template literals JS (`) — use concatenação de string normal
✗ import/require dentro da string JS
✗ CSS strings no prop style (sempre objeto {})
✗ Aspas simples em valores de font-family dentro de strings Python simples

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APÊNDICE 2 — HEADSUP DE STACK ESPECÍFICOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── PONTO 1: _var_is_string=False vs versões do Reflex ───────────────────────

Em Reflex 0.8.x existem duas formas de injetar JS puro. USE APENAS A FORMA 1:

FORMA 1 — correta para este projeto:
    rx.Var.create(js_string, _var_is_string=False)

FORMA 2 — nova API, só existe em versões mais recentes:
    rx.Var(js_string, _var_is_string_without_curly_braces=True)

Antes de usar, verifique qual existe:
    python -c "import inspect, reflex as rx; print(inspect.signature(rx.Var.__init__))"

Se `_var_is_string_without_curly_braces` aparecer na assinatura, use a Forma 2.
Se não aparecer, use a Forma 1. Não tente usar ambas.

── PONTO 2: o cache do .web precisa ser limpo em certos casos ───────────────

Reflex cacheia o bundle compilado em .web/. Se você modificar a string JS
dentro de um rx.Var e o Vite não pegar a mudança (tooltip antigo ainda aparece),
rode antes de `reflex run`:

    Remove-Item -Recurse -Force .web\app\routes   # PowerShell (Windows)
    # ou
    rm -rf .web/app/routes                         # bash

Isso força recompilação de todas as rotas. Só necesário quando o HMR
não detectar a mudança — acontece porque o rx.Var é gerado em Python,
não é um arquivo .js que o Vite observa diretamente.

── PONTO 3: tamanho da string JS e o compilador Vite/OXC ────────────────────

O OXC (Rust) tem limite implícito de complexidade por linha. Strings JS longas
geradas como uma linha única única podem causar "stack overflow" no parser.

ERRADO — tudo em uma linha:
    js = "(function(){var fmt=function(v){if(v>=1e6)return 'R$ '+(v/1e6).toFixed(1)+'M';...}; return function(props){...};})()"

CERTO — use triple-quotes com quebras de linha reais no JS:
    js = """
    (function() {
      var fmt = function(v) {
        if (v >= 1e6) return "R$ " + (v/1e6).toFixed(1) + "M";
        ...
      };
      return function(props) {
        ...
      };
    })()
    """

O OXC parseia linha por linha internamente. Linhas longas causam mais
problemas que muitas linhas curtas.

── PONTO 4: ES5 puro — sem nenhuma sintaxe ES6+ ─────────────────────────────

A versão do OXC bundled com este projeto pode ser mais restritiva que o
Babel clássico. Use APENAS ES5. Checklist completo:

✗ Arrow functions:    (p) => p.value         → use function(p) { return p.value; }
✗ Template literals:  `R$ ${v}`              → use "R$ " + v
✗ Destructuring:      var {active, payload}  → use var active=props.active; var payload=props.payload;
✗ const/let:          const x = 1            → use var x = 1
✗ Spread operator:    {...obj, key: val}      → use Object.assign({}, obj, {key: val})
✗ Optional chaining:  payload?.[0]?.value    → use payload && payload[0] && payload[0].value
✗ Nullish coalescing: val ?? "default"       → use val != null ? val : "default"
✗ Default params:     function(x = 0)        → use function(x) { x = x !== undefined ? x : 0; }

O erro do Vite que você viu ("Invalid Character `0`") foi causado por
optional chaining (?.) sendo interpretado incorretamente pelo OXC.
O `?` foi lido como início de ternário, o `.` como acesso de propriedade,
e o `[0]` como index — gerando um token inválido no contexto.

── PONTO 5: multi-tenant — a string JS é estática, isso é uma vantagem ──────

O conteúdo do tooltip (a string JS injetada via rx.Var) é gerado em
tempo de compilação Python, não em tempo de requisição. Isso significa:

- A mesma string JS serve todos os tenants — zero overhead por tenant
- Não há risco de vazamento de dados entre tenants no tooltip
  (os dados do tooltip vêm do `props.payload` do Recharts, que é
  populado pelo State do usuário autenticado no momento)
- NÃO tente passar State vars do Reflex dentro da string JS assim:
    js = f"var tenant = '{GlobalState.tenant_id}';"  ← ERRADO
  O State.tenant_id é um Var dinâmico — não existe em compile time.
  Se precisar de contexto do tenant no tooltip, passe como campo
  extra no próprio dado do gráfico (no payload), não como State var.

── PONTO 6: performance — não chame tooltip_money() dentro de loops ─────────

Cada chamada a tooltip_money() instancia um novo rx.Var e gera
uma nova string JS no bundle. Se você usar rx.foreach para renderizar
N gráficos, e chamar tooltip_money() dentro do loop, vai gerar N
cópias idênticas da mesma string no bundle.

ERRADO:
    rx.foreach(
        State.projetos,
        lambda p: rx.recharts.bar_chart(
            ...
            tooltip_money(),   ← nova instância por iteração
        )
    )

CERTO — instancie uma vez fora e reutilize:
    _TOOLTIP_RECEITA = tooltip_money(label_subtitle="Receita por projeto")

    def grafico_projeto(projeto):
        return rx.recharts.bar_chart(
            ...
            _TOOLTIP_RECEITA,  ← mesma instância reutilizada
        )

    rx.foreach(State.projetos, grafico_projeto)

Defina todas as instâncias como módulo-level constants no topo de tooltips.py:
    TOOLTIP_MONEY   = tooltip_money()
    TOOLTIP_SCURVE  = tooltip_scurve()
    TOOLTIP_PIE     = tooltip_pie()
    TOOLTIP_GANTT   = tooltip_gantt()

E nos pages, importe as constantes, não as funções:
    from bomtempo.components.tooltips import TOOLTIP_MONEY, TOOLTIP_PIE

── PONTO 7: hover_card e z-index no Radix/Reflex ────────────────────────────

rx.hover_card.content renderiza dentro de um Radix Portal, que tem z-index
gerenciado pelo Radix. Em dashboards com sidebar fixo e overlays, pode
acontecer do hover_card aparecer atrás de outro elemento.

Se isso acontecer, adicione no hover_card.content:
    rx.hover_card.content(
        ...,
        z_index="9999",          ← força para frente
        side="top",              ← "top"|"bottom"|"left"|"right"
        side_offset=8,           ← gap em px entre trigger e card
        avoid_collisions=True,   ← reposiciona se sair da viewport
    )

Para o sidebar da BomTempo especificamente: se o sidebar tiver
z-index definido em bomtempo/components/sidebar.py, o hover_card
precisa de z-index maior que esse valor.

── PONTO 8: como debugar quando o tooltip não aparece (mas não dá erro) ──────

Sequência de diagnóstico se o tooltip não aparecer no browser:

1. Abra o DevTools → Console
   Procure por: "Cannot read properties of undefined" ou "is not a function"
   Se aparecer: sua string JS tem um bug lógico (ex: acessou payload[0]
   sem checar se payload existe)

2. DevTools → Elements → inspecione o SVG do gráfico
   Procure por um div com class "recharts-tooltip-wrapper"
   Se existir mas estiver com visibility:hidden → o `active` prop nunca
   é true. Causa: data_key do gráfico não bate com o que o tooltip espera.

3. Abra .web/app/routes/[pagina]._index.jsx e busque pelo nome da função
   do tooltip (ex: "tooltip_money"). Verifique se a string JS está
   presente e bem formada.

4. Se a string JS estiver com escape incorreto (ex: \\n em vez de newline):
   python -c "from bomtempo.components.tooltips import TOOLTIP_MONEY; print(repr(str(TOOLTIP_MONEY)))"
   A saída deve ser uma expressão JS legível, não cheia de \\n ou \\'.

── PONTO 9: sobre criar uma skill para o Claude Code ────────────────────────

Crie o arquivo .claude/SKILLS.md (ou adicione em CLAUDE.md se já existir)
com este conteúdo fixo para que o Claude Code leia automaticamente:

---
## Tooltip System (tooltips.py)

Stack: Python 3.12 + Reflex 0.8.x + Recharts

Técnica central:
    rx.recharts.graphing_tooltip(
        content=rx.Var.create(JS_IIFE_STRING, _var_is_string=False)
    )

Regras de JS na string:
- ES5 puro (sem arrow functions, const/let, template literals, optional chaining)
- Aspas duplas para todos os valores de string JS
- React.createElement disponível globalmente — não importar
- style= sempre objeto JS {}, nunca string CSS
- Chaves JS em f-strings Python devem ser duplicadas: {{ }}
- Nunca concatenar State vars do Reflex dentro da string JS

Módulo principal: bomtempo/components/tooltips.py
Exports: TOOLTIP_MONEY, TOOLTIP_SCURVE, TOOLTIP_PIE, TOOLTIP_GANTT, hover_card_kpi()

Ao modificar tooltips.py:
1. python -c "from bomtempo.components.tooltips import *"
2. Se mudar string JS: rm -rf .web/app/routes antes de reflex run
3. Testar no browser: DevTools Console não deve ter erros de JS

Erros conhecidos do OXC Vite:
- "Invalid Character" → aspas simples dentro de string Python simples, ou CSS string em style=
- "Unexpected token" → sintaxe ES6 (arrow fn, template literal, optional chaining)
- "stack overflow" → string JS muito longa em uma única linha
---━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APÊNDICE 3 — FIX CRÍTICO: React is not defined
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── O QUE ACONTECEU ──────────────────────────────────────────────────────────

React 17+ usa o "new JSX transform". O Vite não injeta mais `React` como
global — ele importa apenas helpers internos como `_jsx`, `_jsxs`.

O arquivo gerado pelo Reflex confirma isso:
    import {Fragment, useEffect} from "react"
    import {jsx} from "@emotion/react"       ← isso é o que está disponível

`React.createElement` não está em scope. Mas `jsx` (do Emotion) ESTÁ.
A assinatura de `jsx` é idêntica à de `React.createElement`:
    jsx(type, props, ...children)
Emotion's jsx é um wrapper que passa tudo para React.createElement internamente.

── O FIX — UMA LINHA ────────────────────────────────────────────────────────

No topo de CADA IIFE em tooltips.py, como PRIMEIRA linha dentro do
`(function() {`, adicione:

    var React = { createElement: jsx };

Isso cria um objeto React local que delega para o `jsx` que JÁ ESTÁ em
scope. Todo o código existente com React.createElement(...) funciona
sem nenhuma outra mudança.

ANTES (crashava):
    js = """
    (function() {
      var fmt = function(v) { ... };
      return function(props) {
        if (!props.active) return null;
        return React.createElement("div", {...}, ...);
      };
    })()
    """

DEPOIS (funciona):
    js = """
    (function() {
      var React = { createElement: jsx };
      var fmt = function(v) { ... };
      return function(props) {
        if (!props.active) return null;
        return React.createElement("div", {...}, ...);
      };
    })()
    """

Aplique em todas as 4 funções: tooltip_money, tooltip_scurve,
tooltip_pie, tooltip_gantt.

── POR QUE FUNCIONA ─────────────────────────────────────────────────────────

Nossa IIFE roda dentro do módulo _index.jsx gerado pelo Reflex.
Esse módulo tem `jsx` importado no topo como binding de módulo.
Bindings de módulo ficam no closure de TUDO que roda nesse módulo —
incluindo nossa string injetada via rx.Var.

Então `jsx` é acessível. `React` não é. Criamos `React` localmente
apontando para `jsx`. Problema resolvido sem nenhuma dependência nova.

── VALIDAÇÃO RÁPIDA ─────────────────────────────────────────────────────────

Após aplicar o fix:

1. Salve tooltips.py
2. Delete o cache: Remove-Item -Recurse -Force .web\app\routes  (PowerShell)
   ou:             rm -rf .web/app/routes                        (bash/WSL)
3. reflex run
4. Passe o mouse sobre qualquer gráfico — não deve mais crashar
5. DevTools → Console → confirmar que não há erros de JS

── SE AINDA FALHAR: fallback de segurança ───────────────────────────────────

Se por alguma razão `jsx` também não estiver em scope (versão diferente
do Reflex que usa outro import), use o fallback mais defensivo:

    var React = { createElement: (typeof jsx !== "undefined") ? jsx :
                  (typeof window !== "undefined" && window.React) ?
                  window.React.createElement :
                  function() { return null; } };

Isso nunca vai crashar — no pior caso, o tooltip simplesmente não renderiza
(retorna null) em vez de quebrar a página inteira.

── REGRA PARA QUALQUER TOOLTIP FUTURO ───────────────────────────────────────

Todo tooltip novo em tooltips.py DEVE ter como primeira linha da IIFE:

    var React = { createElement: jsx };

Sem essa linha, vai crashar em produção no momento em que o usuário
passar o mouse sobre um gráfico. Trate isso como boilerplate obrigatório,
não como workaround opcional.