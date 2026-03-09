"""
Alertas Proativos — Bomtempo Intelligence
Split-screen: Cronológicos (left) | Reativos (right)
Cards are purely informational. Registration form is the action core.
"""
from __future__ import annotations

import reflex as rx

from bomtempo.core import styles as S
from bomtempo.core.alert_service import ALERT_TYPES
from bomtempo.state.alertas_state import AlertasState
from bomtempo.state.global_state import GlobalState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> str:
    h = h.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    return "201,139,42"


def _section_label(text: str) -> rx.Component:
    return rx.text(
        text,
        font_family=S.FONT_TECH,
        font_size="0.65rem",
        font_weight="700",
        color=S.TEXT_MUTED,
        letter_spacing="0.18em",
        text_transform="uppercase",
        margin_bottom="8px",
    )


# ── Alert info card (purely explanatory) ──────────────────────────────────────

def _alert_card(alert_type: str) -> rx.Component:
    meta = ALERT_TYPES[alert_type]
    color = meta["color"]
    label = meta["label"]
    desc = meta["description"]
    schedule = meta["schedule"]
    icon = meta["icon"]
    count = AlertasState.subscription_counts.get(alert_type, 0)
    is_running = AlertasState.sweep_running_type == alert_type

    return rx.box(
        rx.vstack(
            # Header row
            rx.hstack(
                rx.hstack(
                    rx.icon(tag=icon, size=15, color=color),
                    rx.text(label, font_family=S.FONT_TECH, font_weight="700",
                            font_size="0.88rem", color=S.TEXT_PRIMARY, letter_spacing="0.02em"),
                    spacing="2", align="center",
                ),
                rx.spacer(),
                # Subtle trigger with tooltip
                rx.cond(
                    is_running,
                    rx.spinner(size="1", color=color),
                    rx.tooltip(
                        rx.icon(
                            tag="zap",
                            size=14,
                            color=color,
                            cursor="pointer",
                            opacity="0.45",
                            on_click=AlertasState.open_confirm_sweep(alert_type),
                            _hover={"opacity": "1"},
                            transition="opacity 0.15s ease",
                        ),
                        content="Disparar manualmente — envia emails agora para os destinatários cadastrados",
                    ),
                ),
                align="center",
                width="100%",
            ),
            # Description — fixed height so all cards are uniform
            rx.text(
                desc,
                font_size="0.72rem",
                color=S.TEXT_MUTED,
                line_height="1.5",
                flex="1",
            ),
            # Footer
            rx.hstack(
                rx.hstack(
                    rx.icon(tag="clock", size=11, color=S.TEXT_MUTED),
                    rx.text(schedule, font_size="0.67rem", color=S.TEXT_MUTED),
                    spacing="1", align="center",
                ),
                rx.spacer(),
                rx.cond(
                    count,
                    rx.hstack(
                        rx.icon(tag="mail", size=11, color=color),
                        rx.text(
                            rx.cond(count == 1, "1 dest.", count.to_string() + " dest."),
                            font_size="0.67rem", color=color, font_weight="600",
                        ),
                        spacing="1", align="center",
                    ),
                    rx.text("Sem destinatários", font_size="0.67rem", color=S.TEXT_MUTED),
                ),
                align="center",
                width="100%",
            ),
            # Inline sweep result
            rx.cond(
                AlertasState.sweep_results.get(alert_type, "") != "",
                rx.hstack(
                    rx.icon(tag="check-circle", size=12, color=S.PATINA),
                    rx.text(
                        AlertasState.sweep_results.get(alert_type, ""),
                        font_size="0.68rem", color=S.PATINA, flex="1",
                    ),
                    rx.icon(
                        tag="x", size=11, color=S.TEXT_MUTED, cursor="pointer",
                        on_click=AlertasState.clear_type_sweep_result(alert_type),
                        _hover={"color": S.TEXT_PRIMARY},
                    ),
                    spacing="2", align="center",
                    bg="rgba(42,157,143,0.08)",
                    border=f"1px solid {S.PATINA}30",
                    border_radius="8px",
                    padding="5px 9px",
                    width="100%",
                ),
            ),
            spacing="2",
            width="100%",
            height="100%",
            justify="between",
        ),
        bg="rgba(14,26,23,0.55)",
        border=f"1px solid {color}25",
        border_radius="12px",
        padding="14px",
        min_height="120px",
        transition="border-color 0.2s ease",
        _hover={"border_color": f"{color}50"},
        display="flex",
        flex_direction="column",
    )


# ── Left panel — Cronológicos ─────────────────────────────────────────────────

def _panel_cronologico() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="calendar-clock", size=16, color=S.PATINA),
                rx.text("Cronológicos", font_family=S.FONT_TECH, font_weight="700",
                        font_size="0.9rem", color=S.TEXT_PRIMARY, text_transform="uppercase",
                        letter_spacing="0.1em"),
                spacing="2", align="center",
            ),
            rx.text("Disparos agendados em horário fixo, independente de gatilho.",
                    font_size="0.72rem", color=S.TEXT_MUTED, margin_bottom="2px"),
            *[_alert_card(at) for at in ("daily", "weekly", "monthly")],
            spacing="2",
            width="100%",
        ),
        **{**S.GLASS_CARD_NO_HOVER, "padding": "18px", "border_radius": "16px"},
        flex="1",
    )


# ── Right panel — Reativos ────────────────────────────────────────────────────

def _panel_reativo() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="radar", size=16, color=S.COPPER),
                rx.text("Reativos", font_family=S.FONT_TECH, font_weight="700",
                        font_size="0.9rem", color=S.TEXT_PRIMARY, text_transform="uppercase",
                        letter_spacing="0.1em"),
                spacing="2", align="center",
            ),
            rx.text("Disparo automático ao detectar condição crítica na obra.",
                    font_size="0.72rem", color=S.TEXT_MUTED, margin_bottom="2px"),
            *[_alert_card(at) for at in ("risk_high", "budget_overage", "rdo_pending")],
            spacing="2",
            width="100%",
        ),
        **{**S.GLASS_CARD_NO_HOVER, "padding": "18px", "border_radius": "16px"},
        flex="1",
    )


# ── Confirmation dialog ────────────────────────────────────────────────────────

def _confirm_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(
                rx.hstack(
                    rx.icon(tag="zap", size=18, color=S.COPPER),
                    rx.text("Confirmar Disparo Manual", font_family=S.FONT_TECH,
                            font_weight="700", color=S.TEXT_PRIMARY),
                    spacing="2", align="center",
                ),
            ),
            rx.alert_dialog.description(
                rx.vstack(
                    rx.text(
                        "Isso irá enviar emails reais para todos os destinatários cadastrados. "
                        "Tem certeza?",
                        font_size="0.85rem", color=S.TEXT_MUTED, line_height="1.6",
                    ),
                    # PT-BR label from state
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="zap", size=13, color=S.COPPER),
                            rx.text(AlertasState.confirm_sweep_label, font_size="0.82rem",
                                    color=S.COPPER, font_weight="700", font_family=S.FONT_TECH),
                            spacing="2", align="center",
                        ),
                        bg=S.COPPER_GLOW,
                        border=f"1px solid {S.COPPER}40",
                        border_radius="8px",
                        padding="8px 16px",
                        display="inline-block",
                    ),
                    spacing="3",
                    align="start",
                ),
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancelar",
                        on_click=AlertasState.cancel_confirm_sweep,
                        variant="outline",
                        color=S.TEXT_PRIMARY,
                        border=f"1px solid {S.BORDER_SUBTLE}",
                        cursor="pointer",
                        _hover={"bg": "rgba(255,255,255,0.06)", "border_color": S.TEXT_MUTED},
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="zap", size=14),
                            rx.text("Disparar Agora", font_weight="700", letter_spacing="0.05em"),
                            spacing="2", align="center",
                        ),
                        on_click=AlertasState.confirm_and_sweep,
                        bg=S.COPPER,
                        color="#000",
                        cursor="pointer",
                        font_family=S.FONT_TECH,
                        _hover={"bg": S.COPPER_LIGHT},
                    ),
                ),
                gap="12px",
                justify="end",
                margin_top="20px",
            ),
            bg=S.BG_ELEVATED,
            border=f"1px solid {S.BORDER_SUBTLE}",
            border_radius="16px",
            padding="28px",
            max_width="440px",
        ),
        open=AlertasState.confirm_sweep_type != "",
    )


# ── Form message ──────────────────────────────────────────────────────────────

def _form_message() -> rx.Component:
    return rx.cond(
        AlertasState.form_message != "",
        rx.box(
            rx.hstack(
                rx.icon(
                    tag=rx.cond(AlertasState.form_is_error, "alert-circle", "check-circle"),
                    size=15,
                    color=rx.cond(AlertasState.form_is_error, S.DANGER, S.SUCCESS),
                ),
                rx.text(
                    AlertasState.form_message,
                    font_size="0.8rem",
                    color=rx.cond(AlertasState.form_is_error, S.DANGER, S.SUCCESS),
                ),
                spacing="2", align="center",
            ),
            bg=rx.cond(AlertasState.form_is_error, "rgba(239,68,68,0.08)", "rgba(42,157,143,0.08)"),
            border=rx.cond(
                AlertasState.form_is_error,
                "1px solid rgba(239,68,68,0.3)",
                "1px solid rgba(42,157,143,0.3)",
            ),
            border_radius="10px",
            padding="10px 14px",
            width="100%",
        ),
    )


# ── Registration form ─────────────────────────────────────────────────────────

def _alert_type_option(at: str) -> rx.Component:
    meta = ALERT_TYPES[at]
    return rx.select.item(meta["label"], value=at)


def _registration_form() -> rx.Component:
    input_style = {
        "bg": S.BG_INPUT,
        "border": f"1px solid {S.BORDER_SUBTLE}",
        "border_radius": "10px",
        "color": S.TEXT_PRIMARY,
        "font_family": S.FONT_BODY,
        "font_size": "0.85rem",
        "_focus": {"border_color": S.COPPER, "box_shadow": f"0 0 0 2px {S.COPPER_GLOW}"},
        "_placeholder": {"color": S.TEXT_MUTED},
    }

    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.icon(tag="user-plus", size=18, color=S.COPPER),
                rx.vstack(
                    rx.text("Cadastro de Destinatários", font_family=S.FONT_TECH,
                            font_weight="700", font_size="1rem", color=S.TEXT_PRIMARY,
                            text_transform="uppercase", letter_spacing="0.06em"),
                    rx.text(
                        "Defina quais e-mails recebem cada tipo de alerta por contrato.",
                        font_size="0.75rem", color=S.TEXT_MUTED,
                    ),
                    spacing="0", align="start",
                ),
                spacing="3", align="center",
            ),
            # Form row
            rx.flex(
                # Alert type select
                rx.box(
                    _section_label("Tipo de Alerta"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecione...",
                            width="100%",
                            **input_style,
                        ),
                        rx.select.content(
                            *[_alert_type_option(at) for at in ALERT_TYPES],
                            bg=S.BG_ELEVATED,
                        ),
                        value=AlertasState.new_alert_type,
                        on_change=AlertasState.set_new_alert_type,
                    ),
                    flex="1.2",
                ),
                # Contract select
                rx.box(
                    _section_label("Contrato"),
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Selecione...",
                            width="100%",
                            **input_style,
                        ),
                        rx.select.content(
                            rx.foreach(
                                GlobalState.project_filter_options,
                                lambda opt: rx.select.item(opt, value=opt),
                            ),
                            bg=S.BG_ELEVATED,
                        ),
                        value=AlertasState.new_contract,
                        on_change=AlertasState.set_new_contract,
                    ),
                    flex="1.2",
                ),
                # Email input
                rx.box(
                    _section_label("E-mail do Destinatário"),
                    rx.input(
                        placeholder="nome@empresa.com.br",
                        value=AlertasState.new_email,
                        on_change=AlertasState.set_new_email,
                        type="email",
                        **input_style,
                        width="100%",
                    ),
                    flex="2",
                ),
                # Add button
                rx.box(
                    _section_label("\u00a0"),
                    rx.button(
                        rx.cond(
                            AlertasState.is_adding,
                            rx.hstack(
                                rx.spinner(size="1"),
                                rx.text("Adicionando...", font_weight="700"),
                                spacing="2", align="center",
                            ),
                            rx.hstack(
                                rx.icon(tag="plus", size=15),
                                rx.text("Adicionar", font_weight="700", letter_spacing="0.05em"),
                                spacing="1", align="center",
                            ),
                        ),
                        on_click=AlertasState.add_subscription,
                        disabled=AlertasState.is_adding,
                        bg=S.COPPER,
                        color="#000",
                        border_radius="10px",
                        padding_x="20px",
                        height="38px",
                        cursor="pointer",
                        font_family=S.FONT_TECH,
                        _hover={"bg": S.COPPER_LIGHT, "transform": "translateY(-1px)"},
                        transition="all 0.2s ease",
                    ),
                    flex="0",
                ),
                gap="12px",
                flex_wrap="wrap",
                align="end",
                width="100%",
            ),
            _form_message(),
            spacing="4",
            width="100%",
        ),
        **{**S.GLASS_CARD_NO_HOVER, "padding": "24px", "border_radius": "18px"},
        width="100%",
    )


# ── Email chip ────────────────────────────────────────────────────────────────

def _email_chip(chip) -> rx.Component:
    return rx.hstack(
        rx.text(chip.email, font_size="0.74rem", color=S.TEXT_PRIMARY,
                font_family=S.FONT_MONO),
        rx.icon(
            tag="x", size=11, color=S.TEXT_MUTED, cursor="pointer",
            on_click=AlertasState.delete_email_chip(chip.id),
            _hover={"color": S.DANGER},
        ),
        spacing="1", align="center",
        bg="rgba(255,255,255,0.05)",
        border="1px solid rgba(255,255,255,0.09)",
        border_radius="20px",
        padding="3px 10px",
        _hover={"border_color": "rgba(239,68,68,0.35)"},
        transition="all 0.15s ease",
    )


# ── Subscription row ──────────────────────────────────────────────────────────

def _subscription_row(sub) -> rx.Component:
    return rx.box(
        rx.flex(
            # Alert type badge
            rx.box(
                rx.hstack(
                    rx.box(width="7px", height="7px", border_radius="50%", bg=sub.alert_color,
                           flex_shrink="0"),
                    rx.text(sub.alert_label, font_family=S.FONT_TECH, font_weight="700",
                            font_size="0.8rem", color=S.TEXT_PRIMARY),
                    spacing="2", align="center",
                ),
                min_width="160px",
            ),
            # Contract
            rx.box(
                rx.text(sub.contract, font_family=S.FONT_MONO,
                        font_size="0.77rem", color=S.COPPER, font_weight="600"),
                min_width="110px",
            ),
            # Email chips
            rx.flex(
                rx.foreach(sub.email_chips, _email_chip),
                gap="5px",
                flex_wrap="wrap",
                flex="1",
                align="center",
            ),
            # Count
            rx.box(
                rx.text(
                    rx.cond(sub.count == "1", "1 email", rx.text.span(sub.count, " emails")),
                    font_size="0.68rem", color=S.TEXT_MUTED,
                ),
                min_width="55px",
                text_align="right",
            ),
            gap="14px",
            align="center",
            width="100%",
            flex_wrap="wrap",
        ),
        bg="rgba(14,26,23,0.45)",
        border="1px solid rgba(255,255,255,0.055)",
        border_radius="10px",
        padding="10px 14px",
        width="100%",
        _hover={"bg": "rgba(14,26,23,0.75)"},
        transition="background 0.15s ease",
    )


# ── Subscriptions panel ───────────────────────────────────────────────────────

def _subscriptions_panel() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon(tag="bell-ring", size=17, color=S.COPPER),
                    rx.text("Alertas Ativos", font_family=S.FONT_TECH, font_weight="700",
                            font_size="0.95rem", color=S.TEXT_PRIMARY, text_transform="uppercase",
                            letter_spacing="0.06em"),
                    spacing="2", align="center",
                ),
                rx.spacer(),
                rx.cond(
                    AlertasState.subscriptions,
                    rx.box(
                        rx.text(
                            rx.cond(
                                AlertasState.subscriptions.length() == 1,
                                "1 grupo",
                                AlertasState.subscriptions.length().to_string() + " grupos",
                            ),
                            font_size="0.7rem", color=S.PATINA, font_weight="700",
                        ),
                        bg="rgba(42,157,143,0.1)",
                        border=f"1px solid {S.PATINA}40",
                        border_radius="6px",
                        padding="3px 10px",
                    ),
                ),
                align="center",
                width="100%",
            ),
            # Column headers
            rx.box(
                rx.flex(
                    rx.text("TIPO", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", min_width="160px"),
                    rx.text("CONTRATO", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", min_width="110px"),
                    rx.text("DESTINATÁRIOS", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", flex="1"),
                    gap="14px",
                    width="100%",
                ),
                padding_x="14px",
                padding_y="8px",
                border_bottom=f"1px solid {S.BORDER_SUBTLE}",
            ),
            # Rows
            rx.cond(
                AlertasState.subscriptions,
                rx.vstack(
                    rx.foreach(AlertasState.subscriptions, _subscription_row),
                    spacing="2",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon(tag="bell-off", size=28, color=S.TEXT_MUTED),
                        rx.text("Nenhum destinatário cadastrado ainda.",
                                font_size="0.82rem", color=S.TEXT_MUTED),
                        rx.text("Use o formulário acima para configurar alertas.",
                                font_size="0.72rem", color=S.TEXT_MUTED),
                        spacing="2", align="center",
                    ),
                    width="100%", padding="36px", text_align="center",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        **{**S.GLASS_CARD_NO_HOVER, "padding": "22px", "border_radius": "18px"},
        width="100%",
    )


# ── History row ───────────────────────────────────────────────────────────────

def _history_row(item: dict) -> rx.Component:
    color = item["alert_color"]
    return rx.flex(
        rx.text(item["timestamp"], font_family=S.FONT_MONO, font_size="0.72rem",
                color=S.TEXT_MUTED, min_width="125px"),
        rx.box(
            rx.hstack(
                rx.box(width="6px", height="6px", border_radius="50%", bg=color, flex_shrink="0"),
                rx.text(item["alert_label"], font_size="0.72rem", font_weight="700", color=color),
                spacing="1", align="center",
            ),
            min_width="150px",
        ),
        rx.text(item["contract"], font_family=S.FONT_MONO, font_size="0.72rem",
                color=S.COPPER, font_weight="600", min_width="105px"),
        rx.text(item["message"], font_size="0.7rem", color=S.TEXT_SECONDARY,
                flex="1", overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
        gap="14px",
        align="center",
        width="100%",
        padding="9px 14px",
        border_bottom=f"1px solid {S.BORDER_SUBTLE}",
        _hover={"bg": "rgba(255,255,255,0.02)"},
        transition="background 0.15s ease",
    )


# ── History panel ─────────────────────────────────────────────────────────────

def _history_panel() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon(tag="history", size=17, color=S.PATINA),
                    rx.text("Histórico de Disparos", font_family=S.FONT_TECH, font_weight="700",
                            font_size="0.95rem", color=S.TEXT_PRIMARY, text_transform="uppercase",
                            letter_spacing="0.06em"),
                    spacing="2", align="center",
                ),
                rx.spacer(),
                rx.text(AlertasState.history.length().to_string() + " eventos",
                        font_size="0.7rem", color=S.TEXT_MUTED),
                align="center",
                width="100%",
            ),
            # Headers
            rx.box(
                rx.flex(
                    rx.text("DATA/HORA", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", min_width="125px"),
                    rx.text("TIPO", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", min_width="150px"),
                    rx.text("CONTRATO", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", min_width="105px"),
                    rx.text("MENSAGEM", font_size="0.62rem", font_weight="700",
                            color=S.TEXT_MUTED, letter_spacing="0.15em", flex="1"),
                    gap="14px",
                    width="100%",
                ),
                padding="8px 14px",
                border_bottom=f"1px solid {S.BORDER_ACCENT}",
            ),
            # Rows
            rx.cond(
                AlertasState.history,
                rx.vstack(
                    rx.foreach(AlertasState.history, _history_row),
                    spacing="0",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.icon(tag="inbox", size=28, color=S.TEXT_MUTED),
                        rx.text("Nenhum alerta disparado ainda.",
                                font_size="0.82rem", color=S.TEXT_MUTED),
                        rx.text("Use o ⚡ nos cards acima para testar.",
                                font_size="0.72rem", color=S.TEXT_MUTED),
                        spacing="2", align="center",
                    ),
                    width="100%", padding="36px", text_align="center",
                ),
            ),
            # Load more
            rx.cond(
                AlertasState.history,
                rx.button(
                    rx.hstack(
                        rx.icon(tag="chevrons-down", size=14),
                        rx.text("Ver mais", font_size="0.78rem", font_weight="600"),
                        spacing="2", align="center",
                    ),
                    on_click=AlertasState.load_more_history,
                    variant="ghost",
                    color_scheme="gray",
                    width="100%",
                    cursor="pointer",
                    border_top=f"1px solid {S.BORDER_SUBTLE}",
                    border_radius="0",
                    padding_y="10px",
                    _hover={"bg": "rgba(255,255,255,0.03)"},
                ),
            ),
            spacing="0",
            width="100%",
        ),
        **{**S.GLASS_CARD_NO_HOVER, "padding": "22px", "border_radius": "18px"},
        width="100%",
    )


# ── Page header ───────────────────────────────────────────────────────────────

def _page_header() -> rx.Component:
    total_subs = AlertasState.subscriptions.length()
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="bell-ring", size=20, color=S.COPPER),
                    rx.text(
                        "ALERTAS PROATIVOS",
                        font_family=S.FONT_TECH,
                        font_size="1.6rem",
                        font_weight="700",
                        color=S.TEXT_WHITE,
                        letter_spacing="-0.01em",
                    ),
                    spacing="3", align="center",
                ),
                rx.text(
                    "Monitoramento automático e notificações em tempo real para C-level e gestão",
                    font_size="0.82rem",
                    color=S.TEXT_MUTED,
                ),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.cond(
                    AlertasState.sweep_running,
                    rx.hstack(
                        rx.spinner(size="2", color=S.COPPER),
                        rx.text("Disparando...", font_size="0.78rem",
                                color=S.COPPER, font_weight="700"),
                        spacing="2", align="center",
                        bg=S.COPPER_GLOW,
                        border=f"1px solid {S.COPPER}50",
                        border_radius="10px",
                        padding="7px 13px",
                    ),
                ),
                rx.box(
                    rx.hstack(
                        rx.box(width="7px", height="7px", border_radius="50%",
                               bg=S.SUCCESS, box_shadow=f"0 0 6px {S.SUCCESS}"),
                        rx.text("Scheduler Ativo", font_size="0.75rem",
                                color=S.SUCCESS, font_weight="700"),
                        spacing="2", align="center",
                    ),
                    bg=S.SUCCESS_BG,
                    border=f"1px solid {S.SUCCESS}50",
                    border_radius="10px",
                    padding="7px 13px",
                ),
                rx.cond(
                    AlertasState.subscriptions,
                    rx.box(
                        rx.hstack(
                            rx.icon(tag="mail", size=13, color=S.COPPER),
                            rx.text(
                                rx.cond(total_subs == 1, "1 grupo ativo",
                                        total_subs.to_string() + " grupos ativos"),
                                font_size="0.75rem", color=S.COPPER, font_weight="700",
                            ),
                            spacing="2", align="center",
                        ),
                        bg=S.COPPER_GLOW,
                        border=f"1px solid {S.COPPER}50",
                        border_radius="10px",
                        padding="7px 13px",
                    ),
                ),
                spacing="2",
            ),
            align="center",
            width="100%",
        ),
        width="100%",
    )


# ── Main page ─────────────────────────────────────────────────────────────────

def alertas_page() -> rx.Component:
    return rx.box(
        _confirm_dialog(),
        rx.vstack(
            _page_header(),
            # Split-screen panels
            rx.flex(
                _panel_cronologico(),
                _panel_reativo(),
                gap="14px",
                flex_wrap=["wrap", "wrap", "nowrap"],
                width="100%",
                align="stretch",
            ),
            # Registration form
            _registration_form(),
            # Active subscriptions
            _subscriptions_panel(),
            # History
            _history_panel(),
            spacing="4",
            width="100%",
        ),
        padding=["12px", "16px", "22px"],
        max_width="1320px",
        margin="0 auto",
        width="100%",
    )
