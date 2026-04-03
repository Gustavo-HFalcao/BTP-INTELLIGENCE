"""
Premium tooltip system for BomTempo dashboard.

Técnica para gráficos Recharts:
    rx.recharts.graphing_tooltip(
        content=rx.Var.create(JS_IIFE_STRING, _var_is_string=False)
    )

Para elementos HTML (Gantt, KPI cards):
    rx.hover_card.root / trigger / content

Regras JS (ES5 puro, sem arrow functions, const/let, template literals,
optional chaining). Aspas duplas em todos os valores de string JS.
style= sempre objeto JS {}, nunca string CSS.

Exports públicos (constantes pré-instanciadas):
    TOOLTIP_MONEY
    TOOLTIP_SPI
    TOOLTIP_PIE
    TOOLTIP_GENERIC
    TOOLTIP_PCT_SCURVE     -- previsto / realizado (%)
    TOOLTIP_PCT_DAILY      -- meta / realizado por dia
    TOOLTIP_PCT_DISC       -- previsto_pct / realizado_pct (disciplinas)
    TOOLTIP_PCT_GENERIC    -- genérico sem label map
    gantt_hover_content()  -- hover card Reflex para o Gantt HTML
"""
import reflex as rx


# ── Design tokens ──────────────────────────────────────────────────────────────

_BG      = "#141414"
_BORDER  = "rgba(255,255,255,0.10)"
_DIVIDER = "rgba(255,255,255,0.07)"
_ROW_SEP = "rgba(255,255,255,0.04)"
_AMBER   = "#c98b2a"
_GREEN   = "#4ead78"
_RED     = "#e05a5a"
_BLUE    = "#5282dc"
_TEXT    = "#f0ede6"
_MUTED   = "#7a7870"

_HOVER_CARD_STYLE = {
    "background":   _BG,
    "border":       f"1px solid {_BORDER}",
    "borderRadius": "12px",
    "padding":      "14px 16px",
    "minWidth":     "260px",
    "maxWidth":     "320px",
    "boxShadow":    "0 8px 32px rgba(0,0,0,0.6)",
    "fontFamily":   "-apple-system, BlinkMacSystemFont, 'Inter', sans-serif",
    "fontSize":     "13px",
    "color":        _TEXT,
    "zIndex":       "9999",
}

# Cursor styles for Recharts
_CURSOR_AREA  = {"strokeWidth": 1, "fill": "rgba(201,139,42,0.06)"}
_CURSOR_LINE  = {"strokeWidth": 1, "fill": "rgba(82,130,220,0.04)"}

# ── Shared JS fragments ────────────────────────────────────────────────────────
# These are inlined into every IIFE to avoid repetition.

_JS_CARD_STYLE = (
    "{"
    "background:\"#141414\","
    "border:\"1px solid rgba(255,255,255,0.10)\","
    "borderRadius:\"12px\","
    "padding:\"14px 16px\","
    "minWidth:\"200px\","
    "maxWidth:\"300px\","
    "boxShadow:\"0 8px 32px rgba(0,0,0,0.6)\","
    "fontFamily:\"-apple-system,BlinkMacSystemFont,sans-serif\","
    "fontSize:\"13px\","
    "color:\"#e8e6df\","
    "pointerEvents:\"none\""
    "}"
)

_JS_HEADER_STYLE = (
    "{"
    "display:\"flex\",alignItems:\"center\",gap:\"8px\","
    "marginBottom:\"10px\",paddingBottom:\"8px\","
    "borderBottom:\"1px solid rgba(255,255,255,0.07)\""
    "}"
)

_JS_ROW_STYLE = (
    "{"
    "display:\"flex\",justifyContent:\"space-between\",alignItems:\"center\","
    "gap:\"16px\",padding:\"3px 0\","
    "borderBottom:\"1px solid rgba(255,255,255,0.04)\""
    "}"
)

_JS_DOT = (
    "React.createElement(\"div\",{"
    "style:{width:\"8px\",height:\"8px\",borderRadius:\"50%\","
    "background:p.color||p.fill||\"#c98b2a\",flexShrink:\"0\"}"
    "})"
)


# ── TOOLTIP_MONEY ──────────────────────────────────────────────────────────────

def tooltip_money(
    label_subtitle: str = "Valores financeiros",
    icon: str = "🏗",
    currency: str = "R$",
) -> rx.Component:
    """
    Tooltip premium para gráficos monetários.
    Formata valores >= 1M como '3,2M', >= 1k como '450k', senão inteiro.
    """
    js = """
(function() {
  var React = { createElement: (typeof jsx !== "undefined") ? jsx : (window.React ? window.React.createElement : function(){return null;}) };
  var CURRENCY = \"""" + currency + """\";
  var SUBTITLE = \"""" + label_subtitle + """\";
  var ICON     = \"""" + icon + """\";
  var LABELS = {
    "valor":"Valor",
    "previsto":"Planejado",
    "realizado":"Realizado",
    "executado":"Executado",
    "previsto_acum":"Planejado Acum.",
    "executado_acum":"Realizado Acum.",
    "total_contratado":"Contratado",
    "total_realizado":"Realizado",
    "cumulative_planned":"Previsto Acum.",
    "cumulative_actual":"Realizado Acum.",
    "total":"Total",
    "meta":"Meta"
  };

  var fmt = function(v) {
    var n = parseFloat(v);
    if (isNaN(n)) return String(v);
    if (n >= 1000000) return CURRENCY + " " + (n/1000000).toFixed(1).replace(".",",") + "M";
    if (n >= 1000)    return CURRENCY + " " + (n/1000).toFixed(1).replace(".",",") + "k";
    return CURRENCY + " " + n.toFixed(0);
  };

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var header = React.createElement("div", {style:""" + _JS_HEADER_STYLE + """},
      React.createElement("span", {style:{fontSize:"16px",lineHeight:"1"}}, ICON),
      React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#f0ede6"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"10px",color:"#7a7870",marginTop:"1px"}}, SUBTITLE)
      )
    );

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      var name = LABELS[p.dataKey] || LABELS[p.name] || p.name;
      rows.push(React.createElement("div", {key:i, style:""" + _JS_ROW_STYLE + """},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"6px"}},
          React.createElement("div", {style:{width:"8px",height:"8px",borderRadius:"50%",background:p.color||p.fill||"#c98b2a",flexShrink:"0"}}),
          React.createElement("span", {style:{color:"#7a7870",fontSize:"11px"}}, name)
        ),
        React.createElement("span", {style:{color:"#f0ede6",fontSize:"12px",fontWeight:"600"}}, fmt(p.value))
      ));
    }

    return React.createElement("div", {style:""" + _JS_CARD_STYLE + """}, header, rows);
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── TOOLTIP_PCT ────────────────────────────────────────────────────────────────

def tooltip_pct(
    label_map: dict | None = None,
    title: str = "",
    icon: str = "📈",
) -> rx.Component:
    """
    Tooltip premium para gráficos de percentual.
    label_map: {'data_key': 'Label legível'} — traduz nomes das séries.
    """
    map_js = (
        "{"
        + ", ".join('"' + k + '":"' + v + '"' for k, v in (label_map or {}).items())
        + "}"
    )
    js = """
(function() {
  var React = { createElement: (typeof jsx !== "undefined") ? jsx : (window.React ? window.React.createElement : function(){return null;}) };
  var LABELS = """ + map_js + """;
  var TITLE  = \"""" + title + """\";
  var ICON   = \"""" + icon + """\";

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var headerChildren = [
      React.createElement("span", {key:"ic", style:{fontSize:"16px",lineHeight:"1"}}, ICON),
      React.createElement("div", {key:"hd"},
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#f0ede6"}}, String(label != null ? label : ""))
      )
    ];
    if (TITLE) {
      headerChildren[1] = React.createElement("div", {key:"hd"},
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#f0ede6"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"10px",color:"#7a7870",marginTop:"1px"}}, TITLE)
      );
    }
    var header = React.createElement("div", {style:""" + _JS_HEADER_STYLE + """}, headerChildren);

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p    = payload[i];
      var name = LABELS[p.dataKey] || LABELS[p.name] || p.name;
      var v    = parseFloat(p.value);
      var fmt  = isNaN(v) ? String(p.value) : v.toFixed(1) + "%";
      rows.push(React.createElement("div", {key:i, style:""" + _JS_ROW_STYLE + """},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"6px"}},
          React.createElement("div", {style:{width:"8px",height:"8px",borderRadius:"50%",background:p.color||p.fill||"#c98b2a",flexShrink:"0"}}),
          React.createElement("span", {style:{color:"#7a7870",fontSize:"11px"}}, name)
        ),
        React.createElement("span", {style:{color:"#f0ede6",fontSize:"12px",fontWeight:"600"}}, fmt)
      ));
    }

    return React.createElement("div", {style:""" + _JS_CARD_STYLE + """}, header, rows);
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── TOOLTIP_SPI ────────────────────────────────────────────────────────────────

def tooltip_spi() -> rx.Component:
    """Tooltip premium para gráfico SPI — valor + interpretação colorida."""
    js = """
(function() {
  var React = { createElement: (typeof jsx !== "undefined") ? jsx : (window.React ? window.React.createElement : function(){return null;}) };
  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      if (p.dataKey === "baseline") {
        rows.push(React.createElement("div", {key:i, style:""" + _JS_ROW_STYLE + """},
          React.createElement("span", {style:{color:"#7a7870",fontSize:"11px"}}, "Linha Base"),
          React.createElement("span", {style:{color:"#f0ede6",fontSize:"12px"}}, "1,00")
        ));
      } else {
        var v = parseFloat(p.value);
        var interp = "";
        var interpColor = "#7a7870";
        if (!isNaN(v)) {
          if (v >= 1.05) { interp = "  \u25b2 Adiantado"; interpColor = "#4ead78"; }
          else if (v >= 0.95) { interp = "  \u25cf No prazo"; interpColor = "#c98b2a"; }
          else { interp = "  \u25bc Atrasado"; interpColor = "#e05a5a"; }
        }
        rows.push(React.createElement("div", {key:i, style:""" + _JS_ROW_STYLE + """},
          React.createElement("span", {style:{color:"#7a7870",fontSize:"11px"}}, "SPI"),
          React.createElement("span", {style:{color:interpColor,fontSize:"12px",fontWeight:"600"}},
            isNaN(v) ? "\u2014" : v.toFixed(2) + interp
          )
        ));
      }
    }

    return React.createElement("div", {style:""" + _JS_CARD_STYLE + """},
      React.createElement("div", {style:""" + _JS_HEADER_STYLE + """},
        React.createElement("span", {style:{fontSize:"16px",color:"#5282dc"}}, "SPI"),
        React.createElement("div", null,
          React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#f0ede6"}}, String(label != null ? label : "")),
          React.createElement("div", {style:{fontSize:"10px",color:"#7a7870"}}, "Schedule Performance Index")
        )
      ),
      rows
    );
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_LINE,
    )


# ── TOOLTIP_PIE ────────────────────────────────────────────────────────────────

def tooltip_pie() -> rx.Component:
    """Tooltip premium para pie/donut charts. Mostra nome, valor, percentual."""
    js = """
(function() {
  var React = { createElement: (typeof jsx !== "undefined") ? jsx : (window.React ? window.React.createElement : function(){return null;}) };
  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    if (!active || !payload || !payload.length) return null;
    var item = payload[0];
    if (!item) return null;

    var name  = item.name || (item.payload && item.payload.name) || "";
    var value = item.value != null ? item.value : "";
    var raw   = item.payload ? item.payload : {};
    var pct   = raw.percent != null ? raw.percent : (item.percent != null ? item.percent : null);
    var color = raw.fill || item.fill || item.color || "#c98b2a";
    var pctFmt = pct != null ? (parseFloat(pct) * 100).toFixed(1) + "%" : "";

    return React.createElement("div", {style:""" + _JS_CARD_STYLE.replace('"minWidth":"200px"', '"minWidth":"180px"') + """},
      React.createElement("div", {style:""" + _JS_HEADER_STYLE + """},
        React.createElement("div", {style:{width:"12px",height:"12px",borderRadius:"50%",background:color,flexShrink:"0"}}),
        React.createElement("span", {style:{fontSize:"13px",fontWeight:"600",color:"#f0ede6"}}, name)
      ),
      React.createElement("div", {style:{fontSize:"26px",fontWeight:"700",color:color,textAlign:"center",margin:"6px 0"}},
        String(value)
      ),
      pctFmt ? React.createElement("div", {style:""" + _JS_ROW_STYLE + """},
        React.createElement("span", {style:{color:"#7a7870",fontSize:"11px"}}, "Participa\u00e7\u00e3o"),
        React.createElement("span", {style:{color:color,fontSize:"12px",fontWeight:"600"}}, pctFmt)
      ) : null
    );
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=False,
    )


# ── TOOLTIP_GENERIC ────────────────────────────────────────────────────────────

def tooltip_generic(icon: str = "📋") -> rx.Component:
    """
    Tooltip genérico para contagens e valores não monetários / não percentuais.
    Exibe nome + valor bruto de cada série.
    """
    js = """
(function() {
  var React = { createElement: (typeof jsx !== "undefined") ? jsx : (window.React ? window.React.createElement : function(){return null;}) };
  var ICON = \"""" + icon + """\";
  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      rows.push(React.createElement("div", {key:i, style:""" + _JS_ROW_STYLE + """},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"6px"}},
          React.createElement("div", {style:{width:"8px",height:"8px",borderRadius:"50%",background:p.color||p.fill||"#c98b2a",flexShrink:"0"}}),
          React.createElement("span", {style:{color:"#7a7870",fontSize:"11px"}}, p.name)
        ),
        React.createElement("span", {style:{color:"#f0ede6",fontSize:"12px",fontWeight:"600"}}, String(p.value))
      ));
    }

    return React.createElement("div", {style:""" + _JS_CARD_STYLE + """},
      React.createElement("div", {style:{fontSize:"12px",fontWeight:"600",color:"#f0ede6",marginBottom:"8px",paddingBottom:"6px",borderBottom:"1px solid rgba(255,255,255,0.07)"}},
        String(label != null ? label : "")
      ),
      rows
    );
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── Module-level pre-instantiated constants ────────────────────────────────────
# Importe as constantes, não as funções, para evitar duplicação no bundle.

TOOLTIP_MONEY       = tooltip_money()
TOOLTIP_SPI         = tooltip_spi()
TOOLTIP_PIE         = tooltip_pie()
TOOLTIP_GENERIC     = tooltip_generic()

TOOLTIP_PCT_SCURVE  = tooltip_pct(
    {"previsto": "Planejado", "realizado": "Realizado"},
    title="Curva S — Avanço Físico",
)
TOOLTIP_PCT_DAILY   = tooltip_pct(
    {"meta": "Meta/dia", "realizado": "Realizado/dia"},
    title="Produtividade Diária",
)
TOOLTIP_PCT_DISC    = tooltip_pct(
    {"previsto_pct": "Planejado", "realizado_pct": "Realizado"},
    title="Disciplinas",
)
TOOLTIP_PCT_GENERIC = tooltip_pct(icon="📊")


# ── GANTT hover card (Reflex native — não é Recharts) ─────────────────────────

def _divider() -> rx.Component:
    return rx.box(height="1px", width="100%", background=_DIVIDER, flex_shrink="0")


def _row(label: str, value_component: rx.Component) -> rx.Component:
    return rx.hstack(
        rx.text(label, font_size="11px", color=_MUTED, flex="1"),
        value_component,
        width="100%",
        align="center",
        padding_y="1px",
    )


def gantt_hover_content(item: dict) -> rx.Component:
    """
    Hover card content para uma linha do Gantt.
    Recebe o dict reativo do rx.foreach (gantt_rows).

    Campos usados:
        atividade, fase_macro, responsavel, color,
        conclusao_pct, gantt_overdue, critico, dependencia,
        inicio_previsto, termino_previsto
    """
    status_color = rx.cond(
        item["gantt_overdue"] == "1",
        _RED,
        rx.cond(item["conclusao_pct"] == "100", _GREEN, _BLUE),
    )
    status_label = rx.cond(
        item["gantt_overdue"] == "1",
        "⚠ Atrasada",
        rx.cond(item["conclusao_pct"] == "100", "✓ Concluída", "🔵 Em execução"),
    )
    progress_color = rx.cond(
        item["conclusao_pct"] == "100",
        _GREEN,
        rx.cond(item["gantt_overdue"] == "1", _RED, _BLUE),
    )
    termino_color = rx.cond(item["gantt_overdue"] == "1", _RED, _TEXT)

    return rx.hover_card.content(
        rx.vstack(
            # ── Header ────────────────────────────────────────────
            rx.hstack(
                rx.text("⚡", font_size="20px", flex_shrink="0", line_height="1"),
                rx.vstack(
                    rx.text(
                        item["atividade"],
                        font_size="13px",
                        font_weight="600",
                        color=_TEXT,
                        white_space="nowrap",
                        overflow="hidden",
                        text_overflow="ellipsis",
                        max_width="220px",
                    ),
                    rx.text(
                        item["fase_macro"],
                        font_size="10px",
                        font_weight="500",
                        color=item["color"],
                        letter_spacing="0.02em",
                    ),
                    spacing="0",
                    align_items="flex-start",
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            _divider(),
            # ── Responsável ───────────────────────────────────────
            _row("Responsável", rx.text(item["responsavel"], font_size="11px", color=_TEXT)),
            # ── Progresso + barra ─────────────────────────────────
            _row(
                "Progresso",
                rx.text(
                    item["conclusao_pct"] + "%",
                    font_size="12px",
                    font_weight="700",
                    color=progress_color,
                ),
            ),
            rx.box(
                rx.box(
                    width=item["conclusao_pct"] + "%",
                    height="100%",
                    background=progress_color,
                    border_radius="2px",
                ),
                width="100%",
                height="4px",
                background="rgba(255,255,255,0.08)",
                border_radius="2px",
                overflow="hidden",
            ),
            # ── Status ────────────────────────────────────────────
            _row(
                "Status",
                rx.text(status_label, font_size="11px", font_weight="500", color=status_color),
            ),
            # ── Crítico badge (condicional) ───────────────────────
            rx.cond(
                item["critico"] == "1",
                _row(
                    "Prioridade",
                    rx.box(
                        rx.text(
                            "CRÍTICO",
                            font_size="9px",
                            font_weight="800",
                            color="#E89845",
                            letter_spacing="0.06em",
                        ),
                        padding="1px 6px",
                        border_radius="3px",
                        border="1px solid rgba(232,152,69,0.5)",
                        background="rgba(232,152,69,0.10)",
                    ),
                ),
            ),
            _divider(),
            # ── Datas ─────────────────────────────────────────────
            rx.hstack(
                rx.vstack(
                    rx.text("INÍCIO", font_size="9px", color=_MUTED, font_weight="700", letter_spacing="0.08em"),
                    rx.text(item["inicio_previsto"], font_size="12px", color=_TEXT, font_family="monospace", font_weight="500"),
                    spacing="0",
                    align_items="flex-start",
                ),
                rx.box(width="1px", height="32px", background=_DIVIDER),
                rx.vstack(
                    rx.text("TÉRMINO", font_size="9px", color=_MUTED, font_weight="700", letter_spacing="0.08em"),
                    rx.text(item["termino_previsto"], font_size="12px", color=termino_color, font_family="monospace", font_weight="500"),
                    spacing="0",
                    align_items="flex-start",
                ),
                width="100%",
                justify="between",
            ),
            # ── Predecessoras (condicional) ───────────────────────
            rx.cond(
                item["dependencia"] != "",
                _row("Predecessora", rx.text(item["dependencia"], font_size="11px", color=_MUTED)),
            ),
            spacing="2",
            align_items="flex-start",
            width="100%",
        ),
        style=_HOVER_CARD_STYLE,
        side="right",
        side_offset=8,
        avoid_collisions=True,
    )
