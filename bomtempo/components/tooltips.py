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
    TOOLTIP_PCT_SCURVE     -- previsto / realizado (%) com delta
    TOOLTIP_PCT_DAILY      -- meta / realizado por dia com eficiência
    TOOLTIP_PCT_DISC       -- previsto_pct / realizado_pct (disciplinas) com mini-bar
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
# _JS_CARD_STYLE_FN built dynamically — dynamic left-border from first series color.

_JS_CARD_STYLE_FN = (
    "function(accentColor) {"
    "return {"
    "background:\"rgba(18,18,18,0.96)\","
    "border:\"1px solid rgba(255,255,255,0.10)\","
    "borderLeft:\"3px solid \" + (accentColor || \"#c98b2a\"),"
    "borderRadius:\"12px\","
    "padding:\"0\","
    "minWidth:\"220px\","
    "maxWidth:\"320px\","
    "boxShadow:\"0 12px 40px rgba(0,0,0,0.7)\","
    "fontFamily:\"-apple-system,BlinkMacSystemFont,sans-serif\","
    "fontSize:\"13px\","
    "color:\"#F0EDE6\","
    "pointerEvents:\"none\","
    "backdropFilter:\"blur(10px)\","
    "WebkitBackdropFilter:\"blur(10px)\","
    "overflow:\"hidden\""
    "};"
    "}"
)

# Zone styles — padding separated per zone
_JS_ZONE_HEADER = (
    "{"
    "padding:\"12px 14px 10px\","
    "borderBottom:\"1px solid rgba(255,255,255,0.06)\","
    "display:\"flex\",alignItems:\"center\",gap:\"8px\""
    "}"
)

_JS_ZONE_BODY = (
    "{"
    "padding:\"10px 14px\""
    "}"
)

_JS_ZONE_FOOTER = (
    "{"
    "padding:\"8px 14px 12px\","
    "borderTop:\"1px solid rgba(255,255,255,0.06)\","
    "background:\"rgba(255,255,255,0.02)\""
    "}"
)

# Row separator (applied from 2nd row onward via borderTop)
_JS_ROW_STYLE = (
    "{"
    "display:\"flex\",justifyContent:\"space-between\",alignItems:\"center\","
    "gap:\"16px\",padding:\"5px 0\","
    "borderTop:\"1px solid rgba(255,255,255,0.04)\""
    "}"
)

# First row in body zone — no top border
_JS_ROW_FIRST_STYLE = (
    "{"
    "display:\"flex\",justifyContent:\"space-between\",alignItems:\"center\","
    "gap:\"16px\",padding:\"5px 0\""
    "}"
)

# Dot style helper (inlined in JS as function call)
_JS_DOT_FN = (
    "function(color) {"
    "return React.createElement(\"div\",{"
    "style:{width:\"7px\",height:\"7px\",borderRadius:\"50%\","
    "background:color||\"#c98b2a\",flexShrink:\"0\","
    "boxShadow:\"0 0 0 2px rgba(255,255,255,0.08)\"}"
    "});"
    "}"
)

# ── Shared preamble for every IIFE ─────────────────────────────────────────────
_JS_PREAMBLE = (
    "var React = { createElement: (typeof jsx !== \"undefined\") ? jsx"
    " : (window.React ? window.React.createElement : function(){return null;}) };\n"
    "var _cardStyle = " + _JS_CARD_STYLE_FN + ";\n"
    "var _dot = " + _JS_DOT_FN + ";\n"
)


# ── TOOLTIP_MONEY ──────────────────────────────────────────────────────────────

def tooltip_money(
    label_subtitle: str = "Valores Financeiros",
    icon: str = "[obra]",
    currency: str = "R$",
) -> rx.Component:
    """
    Tooltip premium para gráficos monetários.
    Formata valores >= 1M como '3,2M', >= 1k como '450k'.
    Exibe percentual relativo ao total como badge âmbar separado.
    """
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  var CURRENCY = \"""" + currency + """\";
  var SUBTITLE = \"""" + label_subtitle + """\";
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

  var fmtLabel = function(k) {
    return k.replace(/_/g, " ").replace(/\\b\\w/g, function(c) { return c.toUpperCase(); });
  };

  var fmt = function(v) {
    var n = parseFloat(v);
    if (isNaN(n)) return String(v);
    if (n >= 1000000) return CURRENCY + "\u00a0" + (n/1000000).toFixed(1).replace(".",",") + "M";
    if (n >= 1000)    return CURRENCY + "\u00a0" + (n/1000).toFixed(1).replace(".",",") + "k";
    return CURRENCY + "\u00a0" + n.toFixed(0);
  };

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var accentColor = payload[0] ? (payload[0].color || payload[0].fill || "#c98b2a") : "#c98b2a";

    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
      React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase",marginTop:"2px"}}, SUBTITLE)
      )
    );

    // Compute total for percentage
    var total = 0;
    for (var k = 0; k < payload.length; k++) {
      var nv = parseFloat(payload[k].value);
      if (!isNaN(nv) && nv > 0) total += nv;
    }

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      var rawKey = p.dataKey || p.name || "";
      var name = LABELS[rawKey] || fmtLabel(rawKey);
      var numVal = parseFloat(p.value);
      var rowStyle = i === 0 ? """ + _JS_ROW_FIRST_STYLE + """ : """ + _JS_ROW_STYLE + """;

      var pctBadge = null;
      if (total > 0 && !isNaN(numVal) && numVal > 0) {
        var pctNum = Math.round(numVal / total * 100);
        pctBadge = React.createElement("span", {
          style:{
            padding:"2px 7px 3px",
            borderRadius:"4px",
            fontSize:"11px",
            fontWeight:"600",
            letterSpacing:"0.01em",
            background:"rgba(251,191,36,0.12)",
            color:"#FBBF24",
            marginLeft:"6px",
            display:"inline-block"
          }
        }, pctNum + "%");
      }

      rows.push(React.createElement("div", {key:i, style:rowStyle},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"8px"}},
          _dot(p.color||p.fill||"#c98b2a"),
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, name)
        ),
        React.createElement("div", {style:{display:"flex",alignItems:"center"}},
          React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}},
            fmt(p.value)
          ),
          pctBadge
        )
      ));
    }

    var bodyEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """}, rows);

    return React.createElement("div", {style:_cardStyle(accentColor)}, header, bodyEl);
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── TOOLTIP_PCT (base) ─────────────────────────────────────────────────────────

def tooltip_pct(
    label_map: dict | None = None,
    title: str = "",
    icon: str = "[up]",
) -> rx.Component:
    """Tooltip base para percentuais — sem delta extra (para uso genérico)."""
    map_js = (
        "{"
        + ", ".join('"' + k + '":"' + v + '"' for k, v in (label_map or {}).items())
        + "}"
    )
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  var LABELS = """ + map_js + """;
  var TITLE  = \"""" + title + """\";
  var ICON   = \"""" + icon + """\";

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var accentColor = payload[0] ? (payload[0].color || payload[0].fill || "#c98b2a") : "#c98b2a";

    var headerInner = React.createElement("div", null,
      React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, String(label != null ? label : ""))
    );
    if (TITLE) {
      headerInner = React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase",marginTop:"2px"}}, TITLE)
      );
    }
    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """}, headerInner);

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p    = payload[i];
      var name = LABELS[p.dataKey] || LABELS[p.name] || p.name;
      var v    = parseFloat(p.value);
      var fmt  = isNaN(v) ? String(p.value) : v.toFixed(1) + "%";
      var rowStyle = i === 0 ? """ + _JS_ROW_FIRST_STYLE + """ : """ + _JS_ROW_STYLE + """;
      rows.push(React.createElement("div", {key:i, style:rowStyle},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"8px"}},
          _dot(p.color||p.fill||"#c98b2a"),
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, name)
        ),
        React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, fmt)
      ));
    }

    var bodyEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """}, rows);

    return React.createElement("div", {style:_cardStyle(accentColor)}, header, bodyEl);
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── TOOLTIP_PCT_SCURVE (especializado — com delta previsto vs realizado) ────────

def tooltip_pct_scurve() -> rx.Component:
    """Tooltip para Curva S: mostra previsto, realizado e delta colorido."""
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  var LABELS = {"previsto":"Planejado","realizado":"Realizado"};
  var TITLE  = "Curva S \u2014 Avan\u00e7o F\u00edsico";

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var accentColor = "#2a9d8f";

    var labelStr = (label != null && !isNaN(parseInt(label, 10)))
      ? "Sem.\u00a0" + label
      : String(label != null ? label : "");

    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
      React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, labelStr),
        React.createElement("div", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase",marginTop:"2px"}}, TITLE)
      )
    );

    var rows = [];
    var prevVal = null, realVal = null;
    for (var i = 0; i < payload.length; i++) {
      var p    = payload[i];
      var name = LABELS[p.dataKey] || LABELS[p.name] || p.name;
      var v    = parseFloat(p.value);
      var fmt  = isNaN(v) ? String(p.value) : v.toFixed(1) + "%";
      if (p.dataKey === "previsto") prevVal = v;
      if (p.dataKey === "realizado") realVal = v;
      var rowStyle = i === 0 ? """ + _JS_ROW_FIRST_STYLE + """ : """ + _JS_ROW_STYLE + """;
      rows.push(React.createElement("div", {key:i, style:rowStyle},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"8px"}},
          _dot(p.color||p.fill||"#c98b2a"),
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, name)
        ),
        React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, fmt)
      ));
    }

    var bodyEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """}, rows);

    // Delta section in footer zone
    var deltaEl = null;
    if (prevVal !== null && realVal !== null && !isNaN(prevVal) && !isNaN(realVal)) {
      var delta = realVal - prevVal;
      var deltaColor  = delta >= 0 ? "#4ADE80" : "#F87171";
      var deltaSign   = delta >= 0 ? "+" : "";
      var deltaLabel  = delta >= 0 ? " \u25b2 Adiantado" : " \u25bc Atrasado";
      var deltaFmt    = deltaSign + delta.toFixed(1) + "pp" + deltaLabel;
      var deltaBadgeBg = delta >= 0 ? "rgba(74,222,128,0.12)" : "rgba(248,113,113,0.12)";
      deltaEl = React.createElement("div", {style:""" + _JS_ZONE_FOOTER + """},
        React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center"}},
          React.createElement("span", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase"}}, "Delta"),
          React.createElement("span", {style:{
            padding:"2px 7px 3px",
            borderRadius:"4px",
            fontSize:"11px",
            fontWeight:"600",
            letterSpacing:"0.01em",
            background:deltaBadgeBg,
            color:deltaColor
          }}, deltaFmt)
        )
      );
    }

    return React.createElement("div", {style:_cardStyle(accentColor)}, header, bodyEl, deltaEl);
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── TOOLTIP_PCT_DAILY (especializado — com eficiência meta vs realizado) ────────

def tooltip_pct_daily() -> rx.Component:
    """Tooltip produtividade diária: meta/realizado + eficiência colorida."""
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  var LABELS = {"meta":"Meta/dia","realizado":"Realizado/dia"};
  var TITLE  = "Produtividade Di\u00e1ria";

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var accentColor = "#e89845";

    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
      React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase",marginTop:"2px"}}, TITLE)
      )
    );

    var metaVal = null, realVal = null;
    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p    = payload[i];
      var name = LABELS[p.dataKey] || LABELS[p.name] || p.name;
      var v    = parseFloat(p.value);
      var fmt  = isNaN(v) ? String(p.value) : v.toFixed(2) + "pp";
      if (p.dataKey === "meta")      metaVal = v;
      if (p.dataKey === "realizado") realVal = v;
      var rowStyle = i === 0 ? """ + _JS_ROW_FIRST_STYLE + """ : """ + _JS_ROW_STYLE + """;
      rows.push(React.createElement("div", {key:i, style:rowStyle},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"8px"}},
          _dot(p.color||p.fill||"#e89845"),
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, name)
        ),
        React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, fmt)
      ));
    }

    var bodyEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """}, rows);

    // Efficiency ratio in footer zone
    var effEl = null;
    if (metaVal !== null && realVal !== null && !isNaN(metaVal) && metaVal > 0) {
      var eff = (realVal / metaVal) * 100;
      var effColor = eff >= 100 ? "#4ADE80" : (eff >= 80 ? "#FBBF24" : "#F87171");
      var effBadgeBg = eff >= 100 ? "rgba(74,222,128,0.12)" : (eff >= 80 ? "rgba(251,191,36,0.12)" : "rgba(248,113,113,0.12)");
      var effLabel = eff >= 100 ? "\u2713 Meta atingida" : (eff >= 80 ? "\u25cf Abaixo da meta" : "\u25bc Cr\u00edtico");
      effEl = React.createElement("div", {style:""" + _JS_ZONE_FOOTER + """},
        React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center"}},
          React.createElement("span", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase"}}, "Efici\u00eancia"),
          React.createElement("span", {style:{
            padding:"2px 7px 3px",
            borderRadius:"4px",
            fontSize:"11px",
            fontWeight:"600",
            letterSpacing:"0.01em",
            background:effBadgeBg,
            color:effColor
          }}, eff.toFixed(0) + "% " + effLabel)
        )
      );
    }

    return React.createElement("div", {style:_cardStyle(accentColor)}, header, bodyEl, effEl);
  };
})()
"""
    return rx.recharts.graphing_tooltip(
        special_props=[rx.Var("{content: " + js + "}")],
        wrapper_style={"zIndex": 9999, "outline": "none"},
        allow_escape_view_box={"x": True, "y": True},
        cursor=_CURSOR_AREA,
    )


# ── TOOLTIP_PCT_DISC (especializado — com mini progress bar visual) ─────────────

def tooltip_pct_disc() -> rx.Component:
    """Tooltip disciplinas: previsto_pct / realizado_pct com mini barra visual."""
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  var LABELS = {"previsto_pct":"Planejado","realizado_pct":"Realizado"};
  var TITLE  = "Disciplinas";

  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var accentColor = payload[0] ? (payload[0].color || payload[0].fill || "#c98b2a") : "#c98b2a";

    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
      React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em",maxWidth:"200px",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase",marginTop:"2px"}}, TITLE)
      )
    );

    var prevVal = null, realVal = null;
    var prevColor = "#888999";
    var realColor = "#2a9d8f";

    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      if (p.dataKey === "previsto_pct")  { prevVal = parseFloat(p.value); prevColor = p.color||p.fill||prevColor; }
      if (p.dataKey === "realizado_pct") { realVal = parseFloat(p.value); realColor = p.color||p.fill||realColor; }
    }

    // Mini double bar visualization in body zone
    // Each bar: label+value on same line (Nível 3 left, Nível 4 right), bar below
    var barEl = null;
    if (prevVal !== null && realVal !== null && !isNaN(prevVal) && !isNaN(realVal)) {
      var maxV = Math.max(prevVal, realVal, 1);
      var prevW = Math.min((prevVal / maxV) * 100, 100).toFixed(0) + "%";
      var realW = Math.min((realVal / maxV) * 100, 100).toFixed(0) + "%";
      var delta = realVal - prevVal;
      var deltaColor = delta >= 0 ? "#4ADE80" : "#F87171";
      var deltaStr = (delta >= 0 ? "+" : "") + delta.toFixed(1) + "pp";
      var deltaBadgeBg = delta >= 0 ? "rgba(74,222,128,0.12)" : "rgba(248,113,113,0.12)";

      barEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """},
        // Planejado row + bar
        React.createElement("div", {style:{marginBottom:"8px"}},
          React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"4px"}},
            React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, "Planejado"),
            React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, prevVal.toFixed(1) + "%")
          ),
          React.createElement("div", {style:{width:"100%",height:"3px",background:"rgba(255,255,255,0.07)",borderRadius:"2px"}},
            React.createElement("div", {style:{width:prevW,height:"100%",background:prevColor,borderRadius:"2px"}})
          )
        ),
        // Realizado row + bar
        React.createElement("div", null,
          React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"4px"}},
            React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, "Realizado"),
            React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, realVal.toFixed(1) + "%")
          ),
          React.createElement("div", {style:{width:"100%",height:"3px",background:"rgba(255,255,255,0.07)",borderRadius:"2px"}},
            React.createElement("div", {style:{width:realW,height:"100%",background:realColor,borderRadius:"2px"}})
          )
        )
      );
    }

    var deltaFooter = null;
    if (prevVal !== null && realVal !== null && !isNaN(prevVal) && !isNaN(realVal)) {
      var delta2 = realVal - prevVal;
      var deltaColor2 = delta2 >= 0 ? "#4ADE80" : "#F87171";
      var deltaStr2 = (delta2 >= 0 ? "+" : "") + delta2.toFixed(1) + "pp";
      var deltaBadgeBg2 = delta2 >= 0 ? "rgba(74,222,128,0.12)" : "rgba(248,113,113,0.12)";
      deltaFooter = React.createElement("div", {style:""" + _JS_ZONE_FOOTER + """},
        React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center"}},
          React.createElement("span", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase"}}, "Delta"),
          React.createElement("span", {style:{
            padding:"2px 7px 3px",
            borderRadius:"4px",
            fontSize:"11px",
            fontWeight:"600",
            letterSpacing:"0.01em",
            background:deltaBadgeBg2,
            color:deltaColor2
          }}, deltaStr2)
        )
      );
    }

    return React.createElement("div", {style:_cardStyle(accentColor)}, header, barEl, deltaFooter);
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
    """Tooltip premium para gráfico SPI — valor + interpretação + escala visual."""
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var spiVal = null;
    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      if (p.dataKey === "baseline") {
        rows.push(React.createElement("div", {key:i, style:""" + _JS_ROW_FIRST_STYLE + """},
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, "Base"),
          React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, "1,00")
        ));
      } else {
        var v = parseFloat(p.value);
        spiVal = v;
        var interp = "";
        var interpColor = "#7A7870";
        var interpBadgeBg = "rgba(255,255,255,0.06)";
        if (!isNaN(v)) {
          if (v >= 1.05) { interp = "\u25b2 Adiantado"; interpColor = "#4ADE80"; interpBadgeBg = "rgba(74,222,128,0.12)"; }
          else if (v >= 0.95) { interp = "\u25cf No prazo"; interpColor = "#FBBF24"; interpBadgeBg = "rgba(251,191,36,0.12)"; }
          else { interp = "\u25bc Atrasado"; interpColor = "#F87171"; interpBadgeBg = "rgba(248,113,113,0.12)"; }
        }
        var rowStyle = rows.length === 0 ? """ + _JS_ROW_FIRST_STYLE + """ : """ + _JS_ROW_STYLE + """;
        rows.push(React.createElement("div", {key:i, style:rowStyle},
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, "SPI"),
          React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"6px"}},
            React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}},
              isNaN(v) ? "\u2014" : v.toFixed(2)
            ),
            interp ? React.createElement("span", {style:{
              padding:"2px 7px 3px",
              borderRadius:"4px",
              fontSize:"11px",
              fontWeight:"600",
              letterSpacing:"0.01em",
              background:interpBadgeBg,
              color:interpColor
            }}, interp) : null
          )
        ));
      }
    }

    var bodyEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """}, rows);

    // SPI scale bar 0.5→1.5 with tick markers
    var scaleEl = null;
    if (spiVal !== null && !isNaN(spiVal)) {
      var pct = Math.max(0, Math.min(1, (spiVal - 0.5) / 1.0)) * 100;
      var markerColor = spiVal >= 1.05 ? "#4ADE80" : (spiVal >= 0.95 ? "#FBBF24" : "#F87171");
      scaleEl = React.createElement("div", {style:""" + _JS_ZONE_FOOTER + """},
        React.createElement("div", {style:{display:"flex",justifyContent:"space-between",marginBottom:"5px"}},
          React.createElement("span", {style:{color:"#5A5852",fontSize:"9px"}}, "0.5"),
          React.createElement("span", {style:{color:"#5A5852",fontSize:"9px",textTransform:"uppercase",letterSpacing:"0.06em"}}, "Escala SPI"),
          React.createElement("span", {style:{color:"#5A5852",fontSize:"9px"}}, "1.5")
        ),
        React.createElement("div", {style:{position:"relative",width:"100%",height:"4px",borderRadius:"2px",background:"linear-gradient(to right, #e05a5a 0%, #e05a5a 35%, #c98b2a 45%, #c98b2a 55%, #4ead78 65%, #4ead78 100%)"}},
          React.createElement("div", {style:{position:"absolute",left:"0%",top:"-2px",width:"1px",height:"8px",background:"rgba(255,255,255,0.2)"}}),
          React.createElement("div", {style:{position:"absolute",left:"50%",top:"-2px",width:"1px",height:"8px",background:"rgba(255,255,255,0.2)"}}),
          React.createElement("div", {style:{position:"absolute",left:"100%",top:"-2px",width:"1px",height:"8px",background:"rgba(255,255,255,0.2)"}}),
          React.createElement("div", {style:{
            position:"absolute",
            left:pct + "%",
            top:"-4px",
            transform:"translateX(-50%)",
            width:"12px",
            height:"12px",
            borderRadius:"50%",
            background:markerColor,
            border:"2px solid #141414",
            boxShadow:"0 0 6px " + markerColor
          }})
        )
      );
    }

    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
      React.createElement("span", {style:{fontSize:"14px",color:"#60A5FA",fontWeight:"700",letterSpacing:"-0.01em"}}, "SPI"),
      React.createElement("div", null,
        React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, String(label != null ? label : "")),
        React.createElement("div", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase",marginTop:"2px"}}, "Schedule Performance Index")
      )
    );

    return React.createElement("div", {style:_cardStyle("#5282dc")}, header, bodyEl, scaleEl);
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
    """Tooltip premium para pie/donut charts. Mostra nome, valor, percentual e barra visual."""
    js = """
(function() {
  """ + _JS_PREAMBLE + """
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
    var pctVal = pct != null ? parseFloat(pct) * 100 : null;
    var pctFmt = pctVal !== null ? pctVal.toFixed(1) + "%" : "";

    // Progress bar for participation
    var barEl = pctVal !== null ? React.createElement("div", {style:{marginTop:"6px"}},
      React.createElement("div", {style:{width:"100%",height:"3px",background:"rgba(255,255,255,0.07)",borderRadius:"2px",overflow:"hidden"}},
        React.createElement("div", {style:{width:Math.min(pctVal, 100).toFixed(0) + "%",height:"100%",background:color,borderRadius:"2px"}})
      )
    ) : null;

    var smallCard = {
      background:"rgba(18,18,18,0.96)",
      border:"1px solid rgba(255,255,255,0.10)",
      borderLeft:"3px solid " + color,
      borderRadius:"12px",
      padding:"0",
      minWidth:"180px",
      maxWidth:"260px",
      boxShadow:"0 12px 40px rgba(0,0,0,0.7)",
      fontFamily:"-apple-system,BlinkMacSystemFont,sans-serif",
      fontSize:"13px",
      color:"#F0EDE6",
      pointerEvents:"none",
      backdropFilter:"blur(10px)",
      WebkitBackdropFilter:"blur(10px)",
      overflow:"hidden"
    };

    return React.createElement("div", {style:smallCard},
      React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
        React.createElement("div", {style:{width:"7px",height:"7px",borderRadius:"50%",background:color,flexShrink:"0",boxShadow:"0 0 0 2px rgba(255,255,255,0.08)"}}),
        React.createElement("span", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em"}}, name)
      ),
      React.createElement("div", {style:""" + _JS_ZONE_BODY + """},
        React.createElement("div", {style:{fontSize:"26px",fontWeight:"700",color:color,textAlign:"center",margin:"4px 0",fontVariantNumeric:"tabular-nums"}},
          String(value)
        ),
        pctFmt ? React.createElement("div", null,
          React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"5px 0"}},
            React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, "Participa\u00e7\u00e3o"),
            React.createElement("span", {style:{color:color,fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, pctFmt)
          ),
          barEl
        ) : null
      )
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

def tooltip_generic(icon: str = "[lista]") -> rx.Component:
    """
    Tooltip genérico para contagens e valores não monetários / não percentuais.
    Exibe nome + valor bruto de cada série + indicador de tendência se múltiplas séries.
    """
    js = """
(function() {
  """ + _JS_PREAMBLE + """
  var ICON = \"""" + icon + """\";
  return function(props) {
    var active  = props.active;
    var payload = props.payload;
    var label   = props.label;
    if (!active || !payload || !payload.length) return null;

    var accentColor = payload[0] ? (payload[0].color || payload[0].fill || "#c98b2a") : "#c98b2a";

    var rows = [];
    for (var i = 0; i < payload.length; i++) {
      var p = payload[i];
      var rowStyle = i === 0 ? """ + _JS_ROW_FIRST_STYLE + """ : """ + _JS_ROW_STYLE + """;
      rows.push(React.createElement("div", {key:i, style:rowStyle},
        React.createElement("div", {style:{display:"flex",alignItems:"center",gap:"8px"}},
          _dot(p.color||p.fill||"#c98b2a"),
          React.createElement("span", {style:{color:"#7A7870",fontSize:"12px",fontWeight:"400"}}, p.name)
        ),
        React.createElement("span", {style:{color:"#F0EDE6",fontSize:"13px",fontWeight:"600",fontVariantNumeric:"tabular-nums"}}, String(p.value))
      ));
    }

    var bodyEl = React.createElement("div", {style:""" + _JS_ZONE_BODY + """}, rows);

    // Trend indicator: compare first two series
    var trendEl = null;
    if (payload.length >= 2) {
      var v0 = parseFloat(payload[0].value);
      var v1 = parseFloat(payload[1].value);
      if (!isNaN(v0) && !isNaN(v1) && v1 !== 0) {
        var diff = v0 - v1;
        var trendDir   = diff >= 0 ? "\u25b2" : "\u25bc";
        var trendColor = diff >= 0 ? "#4ADE80" : "#F87171";
        var trendBadgeBg = diff >= 0 ? "rgba(74,222,128,0.12)" : "rgba(248,113,113,0.12)";
        var trendPct   = Math.abs(diff / v1 * 100).toFixed(0) + "%";
        trendEl = React.createElement("div", {style:""" + _JS_ZONE_FOOTER + """},
          React.createElement("div", {style:{display:"flex",justifyContent:"space-between",alignItems:"center"}},
            React.createElement("span", {style:{fontSize:"11px",fontWeight:"400",color:"#5A5852",letterSpacing:"0.02em",textTransform:"uppercase"}}, "Varia\u00e7\u00e3o"),
            React.createElement("span", {style:{
              padding:"2px 7px 3px",
              borderRadius:"4px",
              fontSize:"11px",
              fontWeight:"600",
              letterSpacing:"0.01em",
              background:trendBadgeBg,
              color:trendColor
            }}, trendDir + " " + trendPct)
          )
        );
      }
    }

    var header = React.createElement("div", {style:""" + _JS_ZONE_HEADER + """},
      React.createElement("div", {style:{fontSize:"13px",fontWeight:"600",color:"#F0EDE6",letterSpacing:"-0.01em",display:"flex",alignItems:"center",gap:"6px"}},
        React.createElement("span", {style:{fontSize:"14px"}}, ICON),
        React.createElement("span", null, String(label != null ? label : ""))
      )
    );

    return React.createElement("div", {style:_cardStyle(accentColor)}, header, bodyEl, trendEl);
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

TOOLTIP_PCT_SCURVE  = tooltip_pct_scurve()
TOOLTIP_PCT_DAILY   = tooltip_pct_daily()
TOOLTIP_PCT_DISC    = tooltip_pct_disc()
TOOLTIP_PCT_GENERIC = tooltip_pct(icon="[grafico]")


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
        "\u26a0 Atrasada",
        rx.cond(item["conclusao_pct"] == "100", "\u2713 Conclu\u00edda", "\u25cf Em execu\u00e7\u00e3o"),
    )
    status_badge_bg = rx.cond(
        item["gantt_overdue"] == "1",
        "rgba(248,113,113,0.12)",
        rx.cond(
            item["conclusao_pct"] == "100",
            "rgba(74,222,128,0.12)",
            "rgba(96,165,250,0.12)",
        ),
    )
    progress_color = rx.cond(
        item["conclusao_pct"] == "100",
        _GREEN,
        rx.cond(item["gantt_overdue"] == "1", _RED, _BLUE),
    )
    termino_color = rx.cond(item["gantt_overdue"] == "1", _RED, _TEXT)

    # Nivel badge color and label
    nivel_color = rx.cond(
        item["nivel"] == "sub", "#8B5CF6",
        rx.cond(item["nivel"] == "micro", "#2A9D8F", "#C98B2A"),
    )
    nivel_label = rx.cond(
        item["nivel"] == "sub", "SUB-ATIVIDADE",
        rx.cond(item["nivel"] == "micro", "MICRO", "MACRO"),
    )

    return rx.hover_card.content(
        rx.vstack(
            # ── Header ────────────────────────────────────────────
            rx.hstack(
                rx.text("\u26a1", font_size="20px", flex_shrink="0", line_height="1"),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            item["atividade"],
                            font_size="13px",
                            font_weight="600",
                            color=_TEXT,
                            white_space="nowrap",
                            overflow="hidden",
                            text_overflow="ellipsis",
                            max_width="180px",
                            letter_spacing="-0.01em",
                        ),
                        rx.box(
                            rx.text(nivel_label, font_size="7px", font_weight="800", color=nivel_color, letter_spacing="0.06em"),
                            padding="1px 4px", border_radius="2px",
                            border=rx.cond(item["nivel"] == "sub", "1px solid rgba(139,92,246,0.5)", rx.cond(item["nivel"] == "micro", "1px solid rgba(42,157,143,0.5)", "1px solid rgba(201,139,42,0.5)")),
                            bg=rx.cond(item["nivel"] == "sub", "rgba(139,92,246,0.08)", rx.cond(item["nivel"] == "micro", "rgba(42,157,143,0.08)", "rgba(201,139,42,0.08)")),
                            flex_shrink="0",
                        ),
                        spacing="2", align="center",
                    ),
                    rx.text(
                        item["fase_macro"],
                        font_size="11px",
                        font_weight="400",
                        color=item["color"],
                        letter_spacing="0.02em",
                        text_transform="uppercase",
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
            _row("Responsável", rx.text(item["responsavel"], font_size="12px", color=_TEXT)),
            # ── Progresso + barra ─────────────────────────────────
            _row(
                "Progresso",
                rx.text(
                    item["conclusao_pct"] + "%",
                    font_size="13px",
                    font_weight="600",
                    color=progress_color,
                    font_variant_numeric="tabular-nums",
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
                height="3px",
                background="rgba(255,255,255,0.07)",
                border_radius="2px",
                overflow="hidden",
            ),
            # ── Status badge ──────────────────────────────────────
            _row(
                "Status",
                rx.box(
                    rx.text(
                        status_label,
                        font_size="11px",
                        font_weight="600",
                        color=status_color,
                        letter_spacing="0.01em",
                    ),
                    padding="2px 7px 3px",
                    border_radius="4px",
                    background=status_badge_bg,
                ),
            ),
            # ── Crítico badge (condicional) ───────────────────────
            rx.cond(
                item["critico"] == "1",
                _row(
                    "Prioridade",
                    rx.box(
                        rx.text(
                            "CR\u00cdTICO",
                            font_size="9px",
                            font_weight="800",
                            color="#FBBF24",
                            letter_spacing="0.06em",
                        ),
                        padding="2px 7px 3px",
                        border_radius="4px",
                        border="1px solid rgba(251,191,36,0.3)",
                        background="rgba(251,191,36,0.10)",
                    ),
                ),
            ),
            _divider(),
            # ── Datas — layout flexbox com divisor central ─────────
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "IN\u00cdCIO",
                        font_size="9px",
                        color=_MUTED,
                        font_weight="400",
                        letter_spacing="0.08em",
                        text_transform="uppercase",
                    ),
                    rx.text(
                        item["inicio_previsto"],
                        font_size="13px",
                        color=_TEXT,
                        font_family="monospace",
                        font_weight="600",
                        letter_spacing="-0.01em",
                    ),
                    spacing="0",
                    align_items="flex-start",
                ),
                rx.box(width="1px", height="28px", background="rgba(255,255,255,0.08)"),
                rx.vstack(
                    rx.text(
                        "T\u00c9RMINO",
                        font_size="9px",
                        color=_MUTED,
                        font_weight="400",
                        letter_spacing="0.08em",
                        text_transform="uppercase",
                    ),
                    rx.text(
                        item["termino_previsto"],
                        font_size="13px",
                        color=termino_color,
                        font_family="monospace",
                        font_weight="600",
                        letter_spacing="-0.01em",
                    ),
                    spacing="0",
                    align_items="flex-start",
                ),
                width="100%",
                justify="between",
                align="center",
            ),
            # ── Qtd executada (quando rastreada) ─────────────────
            rx.cond(
                item["total_qty"] != "0",
                _row(
                    "Executado",
                    rx.text(
                        item["exec_qty"] + " / " + item["total_qty"] + " " + item["unidade"],
                        font_size="12px",
                        color=_TEXT,
                        font_family="monospace",
                        font_weight="600",
                    ),
                ),
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
