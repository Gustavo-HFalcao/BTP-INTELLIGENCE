"""
RDO v2 Form — Formulário unificado, single-page, sem wizard.
Rota: /rdo-form
"""

import reflex as rx

from bomtempo.state.rdo_state import RDOState


# ── Paleta ──────────────────────────────────────────────────────────────────
_BG         = "#0B1A15"
_CARD       = "rgba(255,255,255,0.04)"
_BORDER     = "rgba(255,255,255,0.10)"
_COPPER     = "#C98B2A"
_PATINA     = "#2A9D8F"
_TEXT       = "#E8F0EE"
_MUTED      = "#6B9090"
_DANGER     = "#E05252"
_INPUT_BG   = "rgba(255,255,255,0.06)"
_BTN_PRI    = "linear-gradient(135deg,#C98B2A,#9B6820)"
_BTN_GHOST  = "rgba(255,255,255,0.06)"


# ── Shared primitives ────────────────────────────────────────────────────────

def _label(text: str) -> rx.Component:
    return rx.text(text, size="1", weight="medium", color=_MUTED,
                   style={"text_transform": "uppercase", "letter_spacing": "0.5px"})


def _input(
    value: rx.Var,
    on_change,
    placeholder: str = "",
    type_: str = "text",
    width: str = "100%",
) -> rx.Component:
    return rx.input(
        value=value,
        on_change=on_change,
        placeholder=placeholder,
        type=type_,
        width=width,
        style={
            "background": _INPUT_BG,
            "border": f"1px solid {_BORDER}",
            "border_radius": "6px",
            "color": _TEXT,
            "padding": "10px 14px",
            "font_size": "16px",  # ≥16px evita zoom no iOS
            "min_height": "44px",  # touch target mínimo
            "_focus": {"border_color": _COPPER, "outline": "none"},
        },
    )


def _select(value: rx.Var, on_change, options: list | rx.Var, width: str = "100%") -> rx.Component:
    return rx.select.root(
        rx.select.trigger(width=width),
        rx.select.content(
            rx.foreach(
                options,
                lambda opt: rx.select.item(opt, value=opt),
            ),
        ),
        value=value,
        on_change=on_change,
    )


def _section_card(*children, title: str = "", icon: str = "", badge: str = "") -> rx.Component:
    header_parts = []
    if icon:
        header_parts.append(rx.icon(icon, size=16, color=_COPPER))
    if title:
        header_parts.append(
            rx.text(title, size="2", weight="bold", color=_TEXT,
                    style={"text_transform": "uppercase", "letter_spacing": "0.8px"})
        )

    if isinstance(badge, rx.Var):
        header_parts.append(
            rx.cond(
                badge != "",
                rx.badge(badge, color_scheme="amber", variant="soft", size="1"),
                rx.fragment()
            )
        )
    elif badge:
        header_parts.append(
            rx.badge(badge, color_scheme="amber", variant="soft", size="1")
        )

    return rx.box(
        rx.hstack(*header_parts, spacing="2", margin_bottom="16px"),
        *children,
        padding=["14px", "20px"],
        background=_CARD,
        border=f"1px solid {_BORDER}",
        border_radius="12px",
        style={"backdrop_filter": "blur(8px)"},
    )


def _add_btn(on_click, label: str = "Adicionar") -> rx.Component:
    return rx.button(
        rx.icon("plus", size=14),
        label,
        on_click=on_click,
        size="3",
        style={
            "background": "rgba(201,139,42,0.15)",
            "border": f"1px solid {_COPPER}",
            "color": _COPPER,
            "border_radius": "6px",
            "cursor": "pointer",
            "min_height": "44px",
            "_hover": {"background": "rgba(201,139,42,0.25)"},
        },
    )


def _remove_btn(on_click) -> rx.Component:
    return rx.button(
        rx.icon("x", size=12),
        on_click=on_click,
        size="1",
        style={
            "background": "rgba(224,82,82,0.10)",
            "border": "1px solid rgba(224,82,82,0.3)",
            "color": _DANGER,
            "border_radius": "4px",
            "cursor": "pointer",
            "padding": "4px 8px",
            "_hover": {"background": "rgba(224,82,82,0.2)"},
        },
    )


def _readonly_badge(label: str, value: rx.Var, color: str = _TEXT) -> rx.Component:
    return rx.vstack(
        _label(label),
        rx.box(
            rx.text(value, size="2", color=color, weight="medium"),
            padding="7px 12px",
            background="rgba(255,255,255,0.03)",
            border=f"1px solid {_BORDER}",
            border_radius="6px",
            width="100%",
            min_height="36px",
        ),
        spacing="1",
        width="100%",
    )


# ── Sticky Header ────────────────────────────────────────────────────────────

def _sticky_header() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Brand + back
            rx.hstack(
                rx.button(
                    rx.icon("arrow-left", size=16),
                    on_click=rx.redirect("/rdo-historico"),
                    size="2",
                    variant="ghost",
                    color=_MUTED,
                ),
                rx.vstack(
                    rx.text("RDO v2", size="1", color=_MUTED, weight="bold",
                            style={"text_transform": "uppercase", "letter_spacing": "2px"}),
                    rx.hstack(
                        rx.text(RDOState.rdo_contrato, size="3", weight="bold", color=_COPPER),
                        rx.text("·", color=_MUTED),
                        rx.text(RDOState.rdo_data_display, size="3", color=_TEXT),
                        spacing="2",
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            # Submit status / save status
            rx.hstack(
                # Status text — oculto no mobile, visível em tablet+
                rx.box(
                    rx.cond(
                        RDOState.is_submitting,
                        rx.hstack(
                            rx.spinner(size="1"),
                            rx.text(RDOState.submit_status, size="1", color=_COPPER),
                            spacing="1",
                        ),
                        rx.cond(
                            RDOState.is_draft_saving,
                            rx.hstack(
                                rx.spinner(size="1"),
                                rx.text("Salvando…", size="1", color=_MUTED),
                                spacing="1",
                            ),
                            rx.cond(
                                RDOState.draft_saved_at != "",
                                rx.hstack(
                                    rx.icon("check", size=12, color=_PATINA),
                                    rx.text(
                                        rx.text.span("Rascunho "),
                                        rx.text.span(RDOState.draft_saved_at),
                                        size="1",
                                        color=_MUTED,
                                    ),
                                    spacing="1",
                                ),
                                rx.fragment(),
                            ),
                        ),
                    ),
                    display=["none", "flex"],
                    align_items="center",
                ),
                rx.button(
                    rx.icon("save", size=14),
                    rx.text("Salvar", display=["none", "inline"]),
                    on_click=RDOState.save_draft,
                    size="3",
                    style={
                        "background": _BTN_GHOST,
                        "border": f"1px solid {_BORDER}",
                        "color": _TEXT,
                        "border_radius": "6px",
                        "cursor": "pointer",
                        "min_height": "44px",
                        "padding": "0 12px",
                    },
                ),
                rx.button(
                    rx.icon("send", size=14),
                    "Enviar",
                    on_click=RDOState.open_confirm,
                    size="3",
                    loading=RDOState.is_submitting,
                    style={
                        "background": _BTN_PRI,
                        "color": "#fff",
                        "border_radius": "6px",
                        "font_weight": "600",
                        "cursor": "pointer",
                        "min_height": "44px",
                    },
                ),
                spacing="2",
                align="center",
            ),
            align="center",
            width="100%",
        ),
        position="sticky",
        top="0",
        z_index="50",
        background="rgba(11,26,21,0.95)",
        border_bottom=f"1px solid {_BORDER}",
        padding=["10px 16px", "12px 24px"],
        style={"backdrop_filter": "blur(12px)"},
    )


# ── Draft resume banner ──────────────────────────────────────────────────────

def _draft_banner() -> rx.Component:
    return rx.cond(
        RDOState.has_draft_to_resume,
        rx.box(
            rx.hstack(
                rx.icon("file-clock", size=16, color=_COPPER),
                rx.text("Você tem um rascunho não enviado.", size="2", color=_TEXT),
                rx.spacer(),
                rx.button(
                    "Retomar",
                    on_click=RDOState.resume_draft,
                    size="1",
                    style={"background": _BTN_PRI, "color": "#fff", "border_radius": "6px"},
                ),
                rx.button(
                    "Descartar",
                    on_click=RDOState.discard_draft_offer,
                    size="1",
                    variant="ghost",
                    color=_MUTED,
                ),
                spacing="3",
                align="center",
            ),
            padding="12px 20px",
            background="rgba(201,139,42,0.12)",
            border="1px solid rgba(201,139,42,0.3)",
            border_radius="8px",
            margin_bottom="16px",
        ),
    )


# ── Section: Header info (read-only badges + editable fields) ────────────────

def _section_header_info() -> rx.Component:
    return _section_card(
        # Read-only: contract, projeto, cliente, localização, tipo tarefa
        rx.grid(
            _readonly_badge("Contrato", RDOState.rdo_contrato, _COPPER),
            _readonly_badge("Projeto", RDOState.rdo_projeto),
            _readonly_badge("Cliente", RDOState.rdo_cliente),
            _readonly_badge("Localização / Endereço da Obra", RDOState.rdo_localizacao),
            _readonly_badge("Tipo de Tarefa", RDOState.rdo_tipo_tarefa),
            columns={"initial": "1", "sm": "2"},
            gap="12px",
            width="100%",
        ),
        rx.box(height="12px"),
        # Editable fields
        rx.grid(
            # Data
            rx.vstack(
                _label("Data *"),
                _input(RDOState.rdo_data, RDOState.set_rdo_data, type_="date"),
                spacing="1",
            ),
            # Clima
            rx.vstack(
                _label("Clima"),
                _select(RDOState.rdo_clima, RDOState.set_rdo_clima, RDOState.clima_options),
                spacing="1",
            ),
            # Turno
            rx.vstack(
                _label("Turno"),
                _select(RDOState.rdo_turno, RDOState.set_rdo_turno, RDOState.turno_options),
                spacing="1",
            ),
            columns={"initial": "1", "sm": "3"},
            gap="12px",
            width="100%",
        ),
        rx.box(height="12px"),
        # Orientação / Escopo
        rx.vstack(
            _label("Orientação / Escopo do Dia"),
            rx.text_area(
                value=RDOState.rdo_orientacao,
                on_change=RDOState.set_rdo_orientacao,
                placeholder="Ex: Fixação de 24 painéis fotovoltaicos, cabamento da subestrutura do módulo L12…",
                rows="3",
                width="100%",
                style={
                    "background": _INPUT_BG,
                    "border": f"1px solid {_BORDER}",
                    "border_radius": "6px",
                    "color": _TEXT,
                    "padding": "10px 12px",
                    "font_size": "16px",
                    "_focus": {"border_color": _COPPER, "outline": "none"},
                    "resize": "vertical",
                },
            ),
            spacing="1",
            width="100%",
        ),
        rx.box(height="12px"),
        # Interrupção
        rx.hstack(
            rx.checkbox(
                "Houve interrupção no dia",
                checked=RDOState.rdo_houve_interrupcao,
                on_change=RDOState.set_rdo_houve_interrupcao,
                color_scheme="amber",
            ),
            spacing="2",
            align="center",
        ),
        rx.cond(
            RDOState.rdo_houve_interrupcao,
            rx.box(
                rx.vstack(
                    _label("Motivo da Interrupção"),
                    _input(RDOState.rdo_motivo_interrupcao, RDOState.set_rdo_motivo_interrupcao,
                           placeholder="Descreva o motivo da interrupção"),
                    spacing="1",
                    width="100%",
                ),
                margin_top="12px",
            ),
        ),
        title="Informações do RDO",
        icon="file-text",
    )


# ── Section: GPS Check-in / Check-out ────────────────────────────────────────

def _gps_tag(lat: rx.Var, lng: rx.Var, endereco: rx.Var, _ts: rx.Var, label: str, show_dist: bool = False) -> rx.Component:
    dist_row = rx.cond(
        RDOState.checkin_distancia_str != "",
        rx.hstack(
            rx.icon("ruler", size=11, color=RDOState.checkin_distancia_color),
            rx.text(
                RDOState.checkin_distancia_str,
                size="1",
                weight="bold",
                color=RDOState.checkin_distancia_color,
            ),
            spacing="1",
            align="center",
            margin_top="3px",
        ),
    ) if show_dist else rx.fragment()

    return rx.cond(
        lat != 0.0,
        rx.box(
            rx.hstack(
                rx.icon("map-pin", size=14, color=_PATINA),
                rx.vstack(
                    rx.text(label, size="1", color=_MUTED, weight="bold",
                            style={"text_transform": "uppercase"}),
                    rx.text(endereco, size="2", color=_TEXT),
                    rx.text(
                        rx.text.span(lat.to_string()),
                        rx.text.span(", "),
                        rx.text.span(lng.to_string()),
                        size="1",
                        color=_MUTED,
                        style={"font_family": "monospace"},
                    ),
                    dist_row,
                    spacing="0",
                    align="start",
                ),
                spacing="2",
                align="start",
            ),
            padding="10px 14px",
            background="rgba(42,157,143,0.10)",
            border="1px solid rgba(42,157,143,0.3)",
            border_radius="8px",
        ),
    )


def _section_gps() -> rx.Component:
    return _section_card(
        rx.flex(
            # Check-in
            rx.vstack(
                rx.hstack(
                    rx.text("Check-in", size="2", weight="bold", color=_TEXT),
                    rx.cond(
                        RDOState.checkin_hora_str != "",
                        rx.badge(
                            rx.icon("clock", size=11),
                            rx.text.span(" "),
                            rx.text.span(RDOState.checkin_hora_str),
                            color_scheme="teal",
                            variant="soft",
                            size="1",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.cond(
                    RDOState.checkin_done,
                    _gps_tag(RDOState.checkin_lat, RDOState.checkin_lng,
                             RDOState.checkin_endereco, RDOState.checkin_timestamp, "Check-in",
                             show_dist=True),
                    rx.box(),
                ),
                rx.button(
                    rx.cond(
                        RDOState.is_getting_checkin,
                        rx.hstack(rx.spinner(size="1"), rx.text("Obtendo…"), spacing="1"),
                        rx.hstack(
                            rx.icon("map-pin", size=14),
                            rx.text(rx.cond(RDOState.checkin_done, "Atualizar Check-in", "Registrar Check-in")),
                            spacing="1",
                        ),
                    ),
                    on_click=RDOState.do_checkin,
                    disabled=RDOState.is_getting_checkin,
                    size="3",
                    width="100%",
                    style={
                        "background": rx.cond(RDOState.checkin_done, "rgba(42,157,143,0.15)", _BTN_GHOST),
                        "border": rx.cond(RDOState.checkin_done, "1px solid rgba(42,157,143,0.4)", f"1px solid {_BORDER}"),
                        "color": rx.cond(RDOState.checkin_done, _PATINA, _TEXT),
                        "border_radius": "6px",
                        "min_height": "48px",
                    },
                ),
                spacing="2",
                align="start",
                flex="1",
                width=["100%", "auto"],
            ),
            # Divider + km badge (oculto no mobile — layout vertical)
            rx.vstack(
                rx.icon("arrow-right", size=20, color=_MUTED),
                rx.cond(
                    RDOState.km_percorrido_calc != "",
                    rx.badge(
                        rx.icon("navigation", size=11),
                        rx.text.span(" "),
                        rx.text.span(RDOState.km_percorrido_calc),
                        color_scheme="amber",
                        variant="soft",
                        size="1",
                    ),
                    rx.fragment(),
                ),
                align="center",
                spacing="1",
                padding_top="24px",
                display=["none", "flex"],
            ),
            # Check-out
            rx.vstack(
                rx.hstack(
                    rx.text("Check-out", size="2", weight="bold", color=_TEXT),
                    rx.cond(
                        RDOState.checkout_hora_str != "",
                        rx.badge(
                            rx.icon("clock", size=11),
                            rx.text.span(" "),
                            rx.text.span(RDOState.checkout_hora_str),
                            color_scheme="teal",
                            variant="soft",
                            size="1",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.cond(
                    RDOState.checkout_done,
                    _gps_tag(RDOState.checkout_lat, RDOState.checkout_lng,
                             RDOState.checkout_endereco, RDOState.checkout_timestamp, "Check-out"),
                    rx.box(),
                ),
                rx.button(
                    rx.cond(
                        RDOState.is_getting_checkout,
                        rx.hstack(rx.spinner(size="1"), rx.text("Obtendo…"), spacing="1"),
                        rx.hstack(
                            rx.icon("map-pin", size=14),
                            rx.text(rx.cond(RDOState.checkout_done, "Atualizar Check-out", "Registrar Check-out")),
                            spacing="1",
                        ),
                    ),
                    on_click=RDOState.do_checkout,
                    disabled=RDOState.is_getting_checkout,
                    size="3",
                    width="100%",
                    style={
                        "background": rx.cond(RDOState.checkout_done, "rgba(42,157,143,0.15)", _BTN_GHOST),
                        "border": rx.cond(RDOState.checkout_done, "1px solid rgba(42,157,143,0.4)", f"1px solid {_BORDER}"),
                        "color": rx.cond(RDOState.checkout_done, _PATINA, _TEXT),
                        "border_radius": "6px",
                        "min_height": "48px",
                    },
                ),
                spacing="2",
                align="start",
                flex="1",
                width=["100%", "auto"],
            ),
            direction={"initial": "column", "sm": "row"},
            gap="16px",
            align="start",
            width="100%",
        ),
        title="GPS — Check-in / Check-out",
        icon="map-pin",
        badge=rx.cond(RDOState.checkin_done, "✓", ""),
    )


# ── Section: Foto EPIs ───────────────────────────────────────────────────────

def _upload_photo_zone(
    upload_id: str,
    on_drop,
    is_uploading: rx.Var,
    existing_url: rx.Var,
    label: str,
    icon_name: str,
    on_remove=None,
) -> rx.Component:
    feedback_id = f"{upload_id}_scan_feedback"
    smart_scan_script = f"""
<script src="/js/smart_scan.js"></script>
<div id="{feedback_id}" style="display:none;font-size:12px;font-weight:600;padding:6px 10px;border-radius:8px;margin-bottom:6px;background:rgba(255,255,255,0.06);transition:all 0.3s ease;"></div>
<script>
(function(){{
  var _scanner = null;
  var _video   = null;
  var _canvas  = null;

  function _initSmartScan(){{
    var zone = document.getElementById('{upload_id}');
    if(!zone) return;
    var inp = zone.querySelector('input[type="file"]');
    if(!inp || inp._smartScanBound) return;
    inp._smartScanBound = true;

    inp.addEventListener('click', function(){{
      if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
      var feedback = document.getElementById('{feedback_id}');
      if(!_video){{
        _video  = document.createElement('video');
        _canvas = document.createElement('canvas');
        _video.style.display  = 'none';
        _canvas.style.display = 'none';
        document.body.appendChild(_video);
        document.body.appendChild(_canvas);
      }}
      if(window.SmartScanPreview){{
        if(_scanner) _scanner.stopCamera();
        _scanner = new SmartScanPreview(null, null, null);
        _scanner.video    = _video;
        _scanner.canvas   = _canvas;
        _scanner.ctx      = _canvas.getContext('2d');
        _scanner.updateFeedback = function(msg, color){{
          if(!feedback) return;
          feedback.textContent = msg;
          feedback.style.color = color;
          feedback.style.display = 'block';
        }};
        _scanner.startCamera();
      }}
    }});

    inp.addEventListener('change', function(){{
      if(_scanner){{ _scanner.stopCamera(); _scanner = null; }}
      var feedback = document.getElementById('{feedback_id}');
      if(feedback) feedback.style.display = 'none';
    }});
  }}

  if(document.readyState === 'loading'){{
    document.addEventListener('DOMContentLoaded', _initSmartScan);
  }} else {{
    setTimeout(_initSmartScan, 800);
  }}
}})();
</script>
"""
    return rx.vstack(
        rx.html(smart_scan_script),
        # Existing photo preview with lightbox + X
        rx.cond(
            existing_url != "",
            rx.box(
                # Image with hover overlay (lightbox)
                rx.box(
                    rx.image(
                        src=existing_url,
                        width="100%",
                        height="180px",
                        object_fit="cover",
                        style={"border_radius": "8px 8px 0 0" if on_remove else "8px", "display": "block"},
                    ),
                    rx.box(
                        rx.icon("zoom-in", size=24, color="white"),
                        position="absolute",
                        top="0", left="0", right="0", bottom="0",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        background="rgba(0,0,0,0)",
                        border_radius="8px 8px 0 0" if on_remove else "8px",
                        style={
                            "transition": "background 0.2s",
                            "cursor": "pointer",
                            "_hover": {"background": "rgba(0,0,0,0.45)"},
                        },
                        on_click=RDOState.open_lightbox(existing_url),
                    ),
                    position="relative",
                ),
                # X button row (only when on_remove provided)
                rx.cond(
                    on_remove is not None,
                    rx.hstack(
                        rx.spacer(),
                        rx.button(
                            rx.icon("x", size=12),
                            "Remover",
                            on_click=on_remove,
                            size="1",
                            variant="ghost",
                            style={
                                "color": _DANGER,
                                "cursor": "pointer",
                                "padding": "4px 8px",
                                "border_radius": "0 0 8px 8px",
                                "_hover": {"background": "rgba(224,82,82,0.15)"},
                            },
                        ),
                        width="100%",
                        padding="4px 8px",
                        background="rgba(255,255,255,0.04)",
                        border_radius="0 0 8px 8px",
                    ),
                    rx.fragment(),
                ),
                border=f"1px solid {_BORDER}",
                border_radius="8px",
                overflow="hidden",
                margin_bottom="10px",
            ),
        ),
        # Upload zone
        rx.upload(
            rx.vstack(
                rx.cond(
                    is_uploading,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Processando imagem…", size="2", color=_MUTED),
                        spacing="2",
                        align="center",
                    ),
                    rx.vstack(
                        rx.icon(icon_name, size=28, color=_MUTED),
                        rx.text(label, size="2", color=_MUTED, text_align="center"),
                        rx.text("JPG, PNG · Toque para abrir câmera ou galeria",
                                size="1", color=_MUTED, opacity="0.55", text_align="center"),
                        spacing="2",
                        align="center",
                        padding="4px",
                    ),
                ),
                align="center",
                width="100%",
            ),
            id=upload_id,
            accept={"image/*": [".jpg", ".jpeg", ".png", ".webp", ".heic"]},
            multiple=False,
            max_size=15_000_000,
            on_drop=on_drop,
            border=f"2px dashed {_BORDER}",
            border_radius="10px",
            padding="24px 20px",
            width="100%",
            style={
                "cursor": "pointer",
                "background": "rgba(255,255,255,0.02)",
                "transition": "border-color 0.2s",
                "_hover": {"border_color": _COPPER, "background": "rgba(201,139,42,0.04)"},
            },
        ),
        width="100%",
        spacing="0",
    )


def _section_epi() -> rx.Component:
    return _section_card(
        _upload_photo_zone(
            upload_id="rdo_epi_upload",
            on_drop=RDOState.upload_epi_files(rx.upload_files(upload_id="rdo_epi_upload")),
            is_uploading=RDOState.is_uploading_epi,
            existing_url=RDOState.epi_foto_url,
            label="Foto da Equipe com EPIs — toque para capturar",
            icon_name="shield-check",
            on_remove=RDOState.remove_epi_photo,
        ),
        title="Equipe com EPIs",
        icon="shield-check",
        badge=rx.cond(RDOState.epi_foto_url != "", "✓", ""),
    )


# ── Section: Atividades ──────────────────────────────────────────────────────

def _section_atividades() -> rx.Component:
    return _section_card(
        rx.vstack(
            rx.foreach(
                RDOState.atividades_items,
                lambda item, index: rx.hstack(
                    rx.text(item["atividade"], size="2", color=_TEXT, flex="1"),
                    rx.badge(
                        rx.text.span(item.get("progresso_percentual", "0")),
                        rx.text.span("%"),
                        color_scheme="teal",
                        variant="soft",
                        size="1",
                    ),
                    rx.badge(item.get("status", "Em andamento"), color_scheme="amber", variant="outline", size="1"),
                    _remove_btn(RDOState.remove_at(index)),
                    spacing="2",
                    align="center",
                    padding="8px 10px",
                    background="rgba(255,255,255,0.03)",
                    border_radius="6px",
                    border=f"1px solid {_BORDER}",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        rx.box(height="8px"),
        rx.vstack(
            # Linha 1: Descrição — largura total
            _input(RDOState.at_desc, RDOState.set_at_desc, "Descrição do serviço executado"),
            # Linha 2: Controles — % + status + botão (wrappam em telas muito pequenas)
            rx.flex(
                _input(RDOState.at_pct, RDOState.set_at_pct, "% concluído", type_="number", width="90px"),
                rx.box(
                    _select(RDOState.at_status, RDOState.set_at_status, RDOState.at_status_options),
                    flex="1",
                    min_width="130px",
                ),
                _add_btn(RDOState.add_at, "Adicionar"),
                gap="8px",
                align="end",
                wrap="wrap",
                width="100%",
            ),
            spacing="2",
            width="100%",
        ),
        title="Serviços Executados",
        icon="clipboard-check",
        badge=RDOState.atividades_items.length().to_string(),
    )


# ── Section: Evidências (fotos do dia) ───────────────────────────────────────

def _ev_card(item) -> rx.Component:
    return rx.box(
        # Imagem clicável para lightbox
        rx.box(
            rx.image(
                src=item["foto_url"],
                width="100%",
                height="140px",
                object_fit="cover",
                style={"border_radius": "6px 6px 0 0", "display": "block"},
            ),
            # Overlay hover: ícone lupa
            rx.box(
                rx.icon("zoom-in", size=24, color="white"),
                position="absolute",
                top="0", left="0", right="0", bottom="0",
                display="flex",
                align_items="center",
                justify_content="center",
                background="rgba(0,0,0,0)",
                border_radius="6px 6px 0 0",
                style={
                    "transition": "background 0.2s",
                    "cursor": "pointer",
                    "_hover": {"background": "rgba(0,0,0,0.45)"},
                },
                on_click=RDOState.open_lightbox(item["foto_url"]),
            ),
            position="relative",
        ),
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.text(item["legenda"], size="1", color=_TEXT, weight="medium"),
                    rx.cond(
                        item["exif_endereco"] != "",
                        rx.hstack(
                            rx.icon("map-pin", size=10, color=_PATINA),
                            rx.text(item["exif_endereco"], size="1", color=_PATINA),
                            spacing="1",
                            align="center",
                        ),
                    ),
                    spacing="1",
                    align="start",
                    flex="1",
                ),
                # Botão X excluir
                rx.button(
                    rx.icon("x", size=12),
                    on_click=RDOState.remove_evidence(item["foto_url"]),
                    size="1",
                    variant="ghost",
                    style={
                        "color": _DANGER,
                        "cursor": "pointer",
                        "padding": "2px 4px",
                        "border_radius": "4px",
                        "_hover": {"background": "rgba(224,82,82,0.15)"},
                    },
                ),
                align="center",
                width="100%",
                spacing="1",
            ),
            padding="7px 8px",
            background="rgba(255,255,255,0.05)",
        ),
        border=f"1px solid {_BORDER}",
        border_radius="8px",
        overflow="hidden",
    )


def _section_evidencias() -> rx.Component:
    return _section_card(
        # exifr CDN + interceptor — fires before on_drop, sends EXIF to Reflex via hidden input
        rx.html("""
<script src="https://cdn.jsdelivr.net/npm/exifr@7/dist/lite.umd.js"></script>
<script>
(function(){
  function _sendExifToState(meta){
    var inp = document.getElementById('rdo-exif-bridge');
    if(!inp){ console.warn('[exifr] bridge input not found'); return; }
    var json = JSON.stringify(meta);
    console.log('[exifr] sending meta:', json);
    try {
      var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      setter.call(inp, json);
    } catch(e){ inp.value = json; }
    inp.dispatchEvent(new Event('input', {bubbles:true}));
    inp.dispatchEvent(new Event('change', {bubbles:true}));
  }

  function _initExifrInterceptor(){
    var uploadZone = document.getElementById('rdo_evidence_upload');
    if(!uploadZone) return;
    var fileInput = uploadZone.querySelector('input[type="file"]');
    if(!fileInput || fileInput._exifrBound) return;
    fileInput._exifrBound = true;
    console.log('[exifr] interceptor bound to upload input');

    fileInput.addEventListener('change', async function(e){
      var files = e.target.files;
      if(!files || !files.length) return;
      var file = files[0];
      var meta = {datetime:'', lat:0, lng:0, lastModified: String(file.lastModified || 0)};
      console.log('[exifr] file selected:', file.name, 'lastModified:', new Date(file.lastModified).toISOString());
      try {
        if(window.exifr){
          // Use exifr.gps() for most reliable GPS extraction (handles all formats)
          var gpsData = await exifr.gps(file).catch(function(){ return null; });
          if(gpsData && typeof gpsData.latitude === 'number'){
            meta.lat = gpsData.latitude;
            meta.lng = gpsData.longitude;
            console.log('[exifr] GPS found:', meta.lat, meta.lng);
          }
          // Parse full EXIF for DateTimeOriginal
          var parsed = await exifr.parse(file, {tiff:true, exif:true, gps:false}).catch(function(){ return null; });
          if(parsed && parsed.DateTimeOriginal){
            var d = parsed.DateTimeOriginal;
            meta.datetime = (d instanceof Date) ? d.toISOString() : String(d);
            console.log('[exifr] DateTimeOriginal:', meta.datetime);
          }
        } else {
          console.warn('[exifr] library not loaded yet');
        }
      } catch(ex){ console.warn('[exifr] parse error:', ex); }
      _sendExifToState(meta);
    });
  }

  var _t;
  var _obs = new MutationObserver(function(){clearTimeout(_t);_t=setTimeout(_initExifrInterceptor,80);});
  _obs.observe(document.body,{childList:true,subtree:true});
  [100,300,700,1500,3000].forEach(function(ms){setTimeout(_initExifrInterceptor,ms);});
})();
</script>
"""),
        # Invisible bridge input — JS sets value + dispatches change, Reflex on_change fires receive_exif_json
        rx.el.input(
            id="rdo-exif-bridge",
            default_value="",
            on_change=RDOState.receive_exif_json,
            style={
                "position": "absolute",
                "width": "1px",
                "height": "1px",
                "opacity": "0",
                "pointerEvents": "none",
                "overflow": "hidden",
            },
        ),
        # Photo grid
        rx.cond(
            RDOState.evidencias_items.length() > 0,
            rx.box(
                rx.grid(
                    rx.foreach(RDOState.evidencias_items, _ev_card),
                    columns={"initial": "2", "sm": "3"},
                    gap="12px",
                    width="100%",
                ),
                margin_bottom="16px",
            ),
        ),
        # Caption input
        rx.vstack(
            _label("Legenda para as próximas fotos (opcional)"),
            _input(RDOState.ev_legenda, RDOState.set_ev_legenda,
                   "Ex: Fundação concluída, armação do pilar…"),
            spacing="1",
            width="100%",
        ),
        rx.box(height="10px"),
        # Upload drop zone (on_drop fires on selection — no separate button needed)
        rx.upload(
            rx.vstack(
                rx.cond(
                    RDOState.is_uploading_evidence,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Processando imagem…", size="2", color=_MUTED),
                        spacing="2",
                        align="center",
                    ),
                    rx.vstack(
                        rx.icon("image-plus", size=28, color=_MUTED),
                        rx.text("Arraste fotos aqui ou toque para selecionar",
                                size="2", color=_MUTED, text_align="center"),
                        rx.text("JPG, PNG · EXIF + GPS extraído · marca d'água aplicada",
                                size="1", color=_MUTED, opacity="0.55", text_align="center"),
                        spacing="2",
                        align="center",
                        padding="4px",
                    ),
                ),
                align="center",
                width="100%",
            ),
            id="rdo_evidence_upload",
            accept={"image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"], "image/webp": [".webp"], "image/heic": [".heic"]},
            multiple=True,
            max_size=15_000_000,
            on_drop=RDOState.upload_evidence_files(rx.upload_files(upload_id="rdo_evidence_upload")),
            border=f"2px dashed {_BORDER}",
            border_radius="10px",
            padding="24px 20px",
            width="100%",
            style={
                "cursor": "pointer",
                "background": "rgba(255,255,255,0.02)",
                "transition": "border-color 0.2s",
                "_hover": {"border_color": _COPPER, "background": "rgba(201,139,42,0.04)"},
            },
        ),
        title="Fotos do Dia",
        icon="camera",
        badge=RDOState.evidencias_items.length().to_string(),
    )


# ── Section: Observações ─────────────────────────────────────────────────────

def _section_observacoes() -> rx.Component:
    return _section_card(
        rx.text_area(
            value=RDOState.rdo_observacoes,
            on_change=RDOState.set_rdo_observacoes,
            placeholder="Descreva ocorrências gerais, problemas encontrados, decisões tomadas, pendências para o próximo dia…",
            rows="5",
            width="100%",
            style={
                "background": _INPUT_BG,
                "border": f"1px solid {_BORDER}",
                "border_radius": "6px",
                "color": _TEXT,
                "padding": "10px 12px",
                "font_size": "14px",
                "_focus": {"border_color": _COPPER, "outline": "none"},
                "resize": "vertical",
            },
        ),
        title="Observações Gerais",
        icon="message-square",
    )


# ── Section: Ferramentas ─────────────────────────────────────────────────────

def _section_ferramentas() -> rx.Component:
    return _section_card(
        _upload_photo_zone(
            upload_id="rdo_ferramentas_upload",
            on_drop=RDOState.upload_ferramentas_files(rx.upload_files(upload_id="rdo_ferramentas_upload")),
            is_uploading=RDOState.is_uploading_ferramentas,
            existing_url=RDOState.ferramentas_foto_url,
            label="Foto das Ferramentas Limpas e Organizadas — toque para capturar",
            icon_name="wrench",
            on_remove=RDOState.remove_ferramentas_photo,
        ),
        title="Ferramentas Limpas e Organizadas",
        icon="wrench",
        badge=rx.cond(RDOState.ferramentas_foto_url != "", "✓", ""),
    )


# ── Section: Assinatura ──────────────────────────────────────────────────────

def _section_assinatura() -> rx.Component:
    return _section_card(
        rx.grid(
            rx.vstack(
                _label("Nome do Responsável"),
                _input(RDOState.signatory_name, RDOState.set_signatory_name,
                       placeholder="Nome completo do responsável"),
                spacing="1",
            ),
            rx.vstack(
                _label("CPF ou RG"),
                _input(RDOState.signatory_doc, RDOState.set_signatory_doc,
                       placeholder="000.000.000-00"),
                spacing="1",
            ),
            columns={"initial": "1", "sm": "2"},
            gap="12px",
            width="100%",
        ),
        rx.box(height="16px"),
        rx.vstack(
            _label("Assinatura Digital"),
            rx.text(
                "Assine com o dedo ou mouse abaixo. A assinatura é salva automaticamente ao enviar.",
                size="1",
                color=_MUTED,
                margin_bottom="6px",
            ),
            rx.el.canvas(
                id="sig-canvas",
                width="800",
                height="240",
                style={
                    "border": "1px solid rgba(255,255,255,0.15)",
                    "borderRadius": "6px",
                    "background": "rgba(255,255,255,0.04)",
                    "width": "100%",
                    "minHeight": "180px",
                    "cursor": "crosshair",
                    "touchAction": "none",
                    "display": "block",
                    "userSelect": "none",
                },
            ),
            rx.hstack(
                rx.button(
                    rx.icon("trash-2", size=13),
                    "Limpar",
                    on_click=RDOState.clear_signature_canvas,
                    size="1",
                    style={
                        "background": "rgba(224,82,82,0.10)",
                        "border": "1px solid rgba(224,82,82,0.3)",
                        "color": _DANGER,
                        "border_radius": "6px",
                        "cursor": "pointer",
                        "padding": "5px 14px",
                    },
                ),
                rx.button(
                    rx.icon("check", size=13),
                    "Confirmar Assinatura",
                    on_click=RDOState.capture_signature,
                    size="1",
                    style={
                        "background": "rgba(42,157,143,0.12)",
                        "border": "1px solid rgba(42,157,143,0.3)",
                        "color": _PATINA,
                        "border_radius": "6px",
                        "cursor": "pointer",
                        "padding": "5px 14px",
                    },
                ),
                rx.cond(
                    RDOState.signatory_sig_b64 != "",
                    rx.hstack(
                        rx.icon("check-circle", size=14, color=_PATINA),
                        rx.text("Assinatura capturada ✓", size="1", color=_PATINA, weight="medium"),
                        spacing="1",
                        align="center",
                    ),
                    rx.text("Aguardando confirmação…", size="1", color=_MUTED),
                ),
                spacing="2",
                align="center",
                margin_top="8px",
                flex_wrap="wrap",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        title="Assinatura do Responsável",
        icon="pen-line",
        badge=rx.cond(RDOState.signatory_sig_b64 != "", "✓", ""),
    )


# ── Section: Eventos Condicionais (feature flag: conditional_fields) ─────────

def _section_eventos_condicionais() -> rx.Component:
    """Campos de Chuva e Acidente — aparecem somente se feature 'conditional_fields' estiver ativa."""
    return rx.cond(
        RDOState.feat_conditional_fields,
        _section_card(
            # ── Chuva ──
            rx.vstack(
                rx.hstack(
                    rx.checkbox(
                        "Houve chuva no período",
                        checked=RDOState.rdo_houve_chuva,
                        on_change=RDOState.set_rdo_houve_chuva,
                        color_scheme="amber",
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.cond(
                    RDOState.rdo_houve_chuva,
                    rx.box(
                        rx.vstack(
                            _label("Intensidade da Chuva"),
                            _select(
                                RDOState.rdo_quantidade_chuva,
                                RDOState.set_rdo_quantidade_chuva,
                                RDOState.chuva_options,
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        margin_top="12px",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.box(height="16px"),
            # ── Acidente ──
            rx.vstack(
                rx.hstack(
                    rx.checkbox(
                        "Houve acidente / ocorrência no dia",
                        checked=RDOState.rdo_houve_acidente,
                        on_change=RDOState.set_rdo_houve_acidente,
                        color_scheme="red",
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.cond(
                    RDOState.rdo_houve_acidente,
                    rx.box(
                        rx.vstack(
                            _label("Descrição da Ocorrência"),
                            rx.text_area(
                                value=RDOState.rdo_descricao_acidente,
                                on_change=RDOState.set_rdo_descricao_acidente,
                                placeholder="Descreva o acidente/ocorrência, providências tomadas e envolvidos...",
                                rows="4",
                                style={
                                    "background": _INPUT_BG,
                                    "border": f"1px solid rgba(224,82,82,0.4)",
                                    "border_radius": "6px",
                                    "color": _TEXT,
                                    "padding": "10px 14px",
                                    "font_size": "15px",
                                    "width": "100%",
                                    "resize": "vertical",
                                    "_focus": {"border_color": "#E05252", "outline": "none"},
                                },
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        margin_top="12px",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            title="Eventos do Dia",
            icon="alert-triangle",
        ),
        rx.fragment(),
    )


# ── Confirm Dialog ───────────────────────────────────────────────────────────

def _confirm_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Confirmar Envio"),
            rx.dialog.description(
                "O RDO será finalizado, o PDF gerado e enviado por e-mail. Deseja continuar?"
            ),
            rx.vstack(
                rx.hstack(
                    rx.icon("file-text", size=14, color=_MUTED),
                    rx.text("Contrato: ", rx.text.span(RDOState.rdo_contrato, color=_COPPER), size="2"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.icon("calendar", size=14, color=_MUTED),
                    rx.text("Data: ", rx.text.span(RDOState.rdo_data_display), size="2"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.icon("clipboard-check", size=14, color=_MUTED),
                    rx.text(
                        rx.text.span(RDOState.atividades_items.length()),
                        rx.text.span(" serviço(s) executado(s) · "),
                        rx.text.span(RDOState.evidencias_items.length()),
                        rx.text.span(" foto(s)"),
                        size="2",
                    ),
                    spacing="2",
                ),
                rx.cond(
                    RDOState.signatory_name != "",
                    rx.hstack(
                        rx.icon("pen-line", size=14, color=_MUTED),
                        rx.text("Responsável: ", rx.text.span(RDOState.signatory_name), size="2"),
                        spacing="2",
                    ),
                ),
                spacing="2",
                padding="16px",
                background="rgba(255,255,255,0.04)",
                border_radius="8px",
                margin_y="16px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button("Cancelar", variant="soft", color_scheme="gray", on_click=RDOState.close_confirm),
                ),
                rx.button(
                    rx.icon("send", size=14),
                    "Enviar RDO",
                    on_click=RDOState.submit_rdo,
                    loading=RDOState.is_submitting,
                    style={"background": _BTN_PRI, "color": "#fff", "border_radius": "6px"},
                ),
                justify="end",
                spacing="2",
            ),
            style={"max_width": "min(480px, 96vw)", "width": "100%"},
        ),
        open=RDOState.show_confirm_dialog,
    )


# ── Page ─────────────────────────────────────────────────────────────────────

def _sig_capture_init() -> rx.Component:
    """Placeholder — captura de assinatura ocorre em open_confirm via rx.call_script."""
    return rx.fragment()


def _photo_lightbox() -> rx.Component:
    """Lightbox fullscreen para visualizar fotos com zoom + download."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header bar
                rx.hstack(
                    rx.hstack(
                        rx.icon("image", size=14, color=_COPPER),
                        rx.dialog.title(
                            rx.text(
                                "Visualizar Foto",
                                size="2",
                                weight="bold",
                                color=_TEXT,
                                font_family="'Rajdhani', sans-serif",
                                letter_spacing="0.04em",
                            ),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.el.a(
                            rx.icon("download", size=14),
                            href=RDOState.photo_lightbox_url,
                            download=True,
                            target="_blank",
                            style={
                                "color": _COPPER,
                                "cursor": "pointer",
                                "padding": "6px 10px",
                                "border": f"1px solid rgba(201,139,42,0.4)",
                                "borderRadius": "6px",
                                "display": "flex",
                                "alignItems": "center",
                                "textDecoration": "none",
                                "background": "rgba(201,139,42,0.06)",
                            },
                        ),
                        rx.dialog.close(
                            rx.button(
                                rx.icon("x", size=14),
                                on_click=RDOState.close_lightbox,
                                size="1",
                                variant="ghost",
                                style={
                                    "color": _MUTED,
                                    "cursor": "pointer",
                                    "border": "1px solid rgba(255,255,255,0.08)",
                                    "border_radius": "6px",
                                    "padding": "6px",
                                },
                            )
                        ),
                        spacing="2",
                        align="center",
                    ),
                    align="center",
                    width="100%",
                    padding_bottom="12px",
                    border_bottom=f"1px solid rgba(255,255,255,0.07)",
                    margin_bottom="14px",
                ),
                # Foto
                rx.image(
                    src=RDOState.photo_lightbox_url,
                    max_width="100%",
                    max_height="78vh",
                    object_fit="contain",
                    border_radius="8px",
                    style={
                        "display": "block",
                        "margin": "0 auto",
                        "boxShadow": "0 8px 32px rgba(0,0,0,0.5)",
                    },
                ),
                spacing="0",
                width="100%",
            ),
            style={
                "background": "#0B1A15",
                "border": "1px solid rgba(201,139,42,0.2)",
                "borderRadius": "14px",
                "padding": "18px 20px 20px",
                "maxWidth": "92vw",
                "width": "92vw",
                "boxShadow": "0 24px 64px rgba(0,0,0,0.7)",
            },
        ),
        open=RDOState.photo_lightbox_url != "",
        on_open_change=RDOState.close_lightbox,
    )


def rdo_form_page() -> rx.Component:
    return rx.box(
        _sig_capture_init(),
        _sticky_header(),
        rx.box(
            _draft_banner(),
            # 1. Header info (locked badges + editable: data, clima, turno, orientação, interrupção)
            _section_header_info(),
            rx.box(height="16px"),
            # 2. GPS Check-in / Check-out (with auto hora badge + km calc)
            _section_gps(),
            rx.box(height="16px"),
            # 3. Foto EPIs
            _section_epi(),
            rx.box(height="16px"),
            # 4. Serviços Executados (atividades)
            _section_atividades(),
            rx.box(height="16px"),
            # 5. Fotos do Dia (evidências)
            _section_evidencias(),
            rx.box(height="16px"),
            # 6. Observações
            _section_observacoes(),
            rx.box(height="16px"),
            # 7. Ferramentas Limpas e Organizadas
            _section_ferramentas(),
            rx.box(height="16px"),
            # 8. Eventos Condicionais (Chuva / Acidente) — feature flag
            _section_eventos_condicionais(),
            rx.cond(
                RDOState.feat_conditional_fields,
                rx.box(height="16px"),
                rx.fragment(),
            ),
            # 9. Assinatura
            _section_assinatura(),
            rx.box(height="32px"),
            # Bottom submit — full-width on mobile, right-aligned on desktop
            rx.button(
                rx.icon("send", size=16),
                "Finalizar e Enviar RDO",
                on_click=RDOState.open_confirm,
                size="3",
                loading=RDOState.is_submitting,
                width=["100%", "auto"],
                style={
                    "background": _BTN_PRI,
                    "color": "#fff",
                    "border_radius": "8px",
                    "font_weight": "700",
                    "font_size": "16px",
                    "padding": "14px 28px",
                    "min_height": "54px",
                    "cursor": "pointer",
                    "_hover": {"opacity": "0.9"},
                    "align_self": ["stretch", "flex-end"],
                },
            ),
            rx.box(height="40px"),
            padding=["16px", "24px"],
            max_width="960px",
            margin="0 auto",
        ),
        _confirm_dialog(),
        _photo_lightbox(),
        min_height="100vh",
        background=_BG,
    )
