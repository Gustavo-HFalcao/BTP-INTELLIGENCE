"""
RDO Form — Wizard 5 Steps + Preview PDF Inline (Mobile-Ready)
"""

import reflex as rx

from bomtempo.core import styles as S
from bomtempo.state.global_state import GlobalState
from bomtempo.state.rdo_state import RDOState

# ── Paleta local ────────────────────────────────────────────
_STEP_LABELS = ["Cabeçalho", "Mão de Obra", "Equipamentos", "Atividades", "Materiais"]
_CLIMATES = ["Ensolarado", "Parcialmente Nublado", "Nublado", "Chuvoso", "Chuvoso Forte"]
_TURNOS = ["Diurno", "Noturno", "Integral"]
_STATUS_EQUIP = ["Operando", "Parado", "Em Manutenção"]
_UNIDADES = ["un", "m", "m²", "m³", "kg", "t", "L", "sc", "cx"]


# ── Step Indicator ──────────────────────────────────────────
def _step_dot(step_num: int) -> rx.Component:
    is_done = RDOState.current_step > step_num
    is_active = RDOState.current_step == step_num
    return rx.box(
        rx.text(
            str(step_num),
            font_size="11px",
            font_weight="700",
            color=rx.cond(is_active, "#0A1F1A", rx.cond(is_done, "white", S.TEXT_MUTED)),
        ),
        width="28px",
        height="28px",
        border_radius="50%",
        display="flex",
        align_items="center",
        justify_content="center",
        bg=rx.cond(is_active, S.COPPER, rx.cond(is_done, S.PATINA, "rgba(255,255,255,0.08)")),
        border=rx.cond(
            is_active,
            f"2px solid {S.COPPER}",
            rx.cond(is_done, f"2px solid {S.PATINA}", "2px solid rgba(255,255,255,0.15)"),
        ),
        flex_shrink="0",
        transition="all 0.3s ease",
    )


def _progress_bar() -> rx.Component:
    return rx.box(
        rx.hstack(
            *[
                rx.hstack(
                    _step_dot(i + 1),
                    (
                        rx.box(
                            height="2px",
                            flex="1",
                            bg=rx.cond(
                                RDOState.current_step > i + 1, S.PATINA, "rgba(255,255,255,0.1)"
                            ),
                            transition="background 0.3s ease",
                            display=rx.cond(i < 4, "block", "none"),
                        )
                        if i < 4
                        else rx.fragment()
                    ),
                    spacing="0",
                    align="center",
                    flex="1" if i < 4 else "0",
                )
                for i in range(5)
            ],
            width="100%",
            align="center",
            spacing="0",
        ),
        # Labels abaixo
        rx.hstack(
            *[
                rx.text(
                    label,
                    font_size="9px",
                    color=rx.cond(
                        RDOState.current_step == i + 1,
                        S.COPPER,
                        rx.cond(RDOState.current_step > i + 1, S.PATINA, S.TEXT_MUTED),
                    ),
                    text_align="center",
                    flex="1",
                    white_space="nowrap",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    font_weight=rx.cond(RDOState.current_step == i + 1, "700", "400"),
                )
                for i, label in enumerate(_STEP_LABELS)
            ],
            width="100%",
            margin_top="6px",
            spacing="0",
        ),
        width="100%",
        padding_x="4px",
    )


# ── Campo helpers ───────────────────────────────────────────
def _field(label: str, component: rx.Component, required: bool = False) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                label,
                font_size="11px",
                color=S.TEXT_MUTED,
                text_transform="uppercase",
                letter_spacing="0.06em",
                font_weight="600",
            ),
            rx.text("*", color=S.COPPER, font_size="11px") if required else rx.fragment(),
            spacing="1",
            align="center",
        ),
        component,
        spacing="1",
        width="100%",
    )


def _input_style():
    return {
        "width": "100%",
        "height": "48px",
        "bg": "rgba(255,255,255,0.04)",
        "border": f"1px solid {S.BORDER_SUBTLE}",
        "color": S.TEXT_PRIMARY,
        "_focus": {"border_color": S.COPPER, "box_shadow": "0 0 0 2px rgba(201,139,42,0.2)"},
        "_placeholder": {"color": "rgba(255,255,255,0.38)"},
    }


def _input_style_sm():
    """Same as _input_style but with height=40px for compact add-rows."""
    return {**_input_style(), "height": "40px"}


def _section_title(icon: str, title: str) -> rx.Component:
    return rx.hstack(
        rx.icon(tag=icon, size=18, color=S.COPPER),
        rx.text(
            title,
            font_size="16px",
            font_weight="700",
            color=S.TEXT_PRIMARY,
            font_family=S.FONT_TECH,
        ),
        spacing="2",
        align="center",
        margin_bottom="16px",
    )


# ── Nav Buttons ─────────────────────────────────────────────
def _nav_buttons(
    next_label: str = "Próximo →",
    next_action=None,
    is_last: bool = False,
) -> rx.Component:
    return rx.hstack(
        rx.button(
            "← Voltar Etapa",
            on_click=RDOState.prev_step,
            variant="solid",
            color_scheme="gray",
            height="48px",
            min_width="120px",
            display=rx.cond(RDOState.current_step > 1, "flex", "none"),
        ),
        rx.spacer(),
        rx.button(
            next_label,
            on_click=next_action or RDOState.next_step,
            bg=S.COPPER if not is_last else S.PATINA,
            color="white" if not is_last else "#0A1F1A",
            height="48px",
            min_width="140px",
            font_weight="700",
            _hover={"opacity": "0.9"},
            is_loading=(RDOState.is_generating_preview | RDOState.is_submitting) if is_last else False,
        ),
        width="100%",
        padding_top="16px",
        border_top=f"1px solid {S.BORDER_SUBTLE}",
        margin_top="8px",
    )


# ── Inline Add Row ──────────────────────────────────────────
def _add_row(*inputs, btn_label: str = "+", btn_action=None) -> rx.Component:
    return rx.hstack(
        *inputs,
        rx.button(
            btn_label,
            on_click=btn_action,
            bg=S.COPPER,
            color="white",
            height="40px",
            min_width="44px",
            border_radius="8px",
            font_size="18px",
            font_weight="700",
            padding_x="0",
            flex_shrink="0",
        ),
        width="100%",
        align="end",
        spacing="2",
    )


def _remove_btn(on_click) -> rx.Component:
    return rx.icon_button(
        rx.icon(tag="x", size=14),
        on_click=on_click,
        variant="ghost",
        color_scheme="red",
        size="1",
        flex_shrink="0",
    )


# ══════════════════════════════════════════════════════════════
# STEP 1 — Cabeçalho
# ══════════════════════════════════════════════════════════════
def step1_cabecalho() -> rx.Component:
    return rx.vstack(
        _section_title("clipboard-list", "Informações do Relatório"),
        rx.grid(
            _field(
                "Data",
                rx.input(
                    type="date",
                    value=RDOState.rdo_data,
                    on_change=RDOState.set_rdo_data,
                    **_input_style(),
                ),
                required=True,
            ),
            _field(
                "Contrato",
                rx.input(
                    placeholder="Ex: BOM-001",
                    value=RDOState.rdo_contrato,
                    on_change=RDOState.set_rdo_contrato,
                    **_input_style(),
                ),
                required=True,
            ),
            columns=rx.breakpoints(initial="1", sm="2"),
            gap="16px",
            width="100%",
        ),
        _field(
            "Cliente",
            rx.input(
                placeholder="Nome do cliente",
                value=RDOState.rdo_cliente,
                on_change=RDOState.set_rdo_cliente,
                **_input_style(),
            ),
        ),
        _field(
            "Localização / Endereço da Obra",
            rx.input(
                placeholder="Ex: Av. Principal, 1234 — Belo Horizonte/MG",
                value=RDOState.rdo_localizacao,
                on_change=RDOState.set_rdo_localizacao,
                **_input_style(),
            ),
        ),
        rx.grid(
            _field(
                "Condição Climática",
                rx.select(
                    _CLIMATES,
                    value=RDOState.rdo_clima,
                    on_change=RDOState.set_rdo_clima,
                    width="100%",
                ),
            ),
            _field(
                "Turno",
                rx.select(
                    _TURNOS,
                    value=RDOState.rdo_turno,
                    on_change=RDOState.set_rdo_turno,
                    width="100%",
                ),
            ),
            columns=rx.breakpoints(initial="1", sm="2"),
            gap="16px",
            width="100%",
        ),
        rx.grid(
            _field(
                "Início",
                rx.input(
                    type="time",
                    value=RDOState.rdo_hora_inicio,
                    on_change=RDOState.set_rdo_hora_inicio,
                    **_input_style(),
                ),
            ),
            _field(
                "Término",
                rx.input(
                    type="time",
                    value=RDOState.rdo_hora_termino,
                    on_change=RDOState.set_rdo_hora_termino,
                    **_input_style(),
                ),
            ),
            columns=rx.breakpoints(initial="1", sm="2"),
            gap="16px",
            width="100%",
        ),
        # Toggle Interrupção
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "Houve interrupção no serviço?",
                        font_size="13px",
                        color=S.TEXT_PRIMARY,
                        font_weight="600",
                    ),
                    rx.text(
                        "Chuva, falta de material, acidente, etc.",
                        font_size="12px",
                        color=S.TEXT_MUTED,
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.switch(
                    checked=RDOState.rdo_houve_interrupcao,
                    on_change=RDOState.set_rdo_houve_interrupcao,
                    color_scheme="yellow",
                ),
                width="100%",
                align="center",
            ),
            padding="14px 16px",
            border_radius="10px",
            bg="rgba(255,255,255,0.03)",
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        rx.cond(
            RDOState.rdo_houve_interrupcao,
            _field(
                "Motivo da Interrupção",
                rx.text_area(
                    placeholder="Descreva o motivo da interrupção...",
                    value=RDOState.rdo_motivo_interrupcao,
                    on_change=RDOState.set_rdo_motivo_interrupcao,
                    width="100%",
                    height="80px",
                    bg="rgba(255,255,255,0.04)",
                    border=f"1px solid {S.WARNING}",
                ),
            ),
        ),
        _nav_buttons(next_label="Mão de Obra →"),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════════════════════════
# STEP 2 — Mão de Obra
# ══════════════════════════════════════════════════════════════
# Os campos temporários e métodos add_* agora vivem em RDOState


def step2_mao_obra() -> rx.Component:
    return rx.vstack(
        _section_title("users", "Mão de Obra em Campo"),
        # Add row
        rx.box(
            rx.vstack(
                rx.text(
                    "Adicionar profissional",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_weight="600",
                    margin_bottom="8px",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Função (ex: Pedreiro)",
                        value=RDOState.mo_funcao,
                        on_change=RDOState.set_mo_funcao,
                        **_input_style_sm(),
                    ),
                    rx.input(
                        placeholder="Qtd",
                        value=RDOState.mo_qtd,
                        on_change=RDOState.set_mo_qtd,
                        type="number",
                        min="1",
                        **_input_style_sm(),
                    ),
                    rx.input(
                        placeholder="Obs (opcional)",
                        value=RDOState.mo_obs,
                        on_change=RDOState.set_mo_obs,
                        **_input_style_sm(),
                    ),
                    rx.button(
                        rx.icon(tag="plus", size=18),
                        on_click=RDOState.add_mo,
                        bg=S.COPPER,
                        color="white",
                        height="40px",
                        width="40px",
                        padding="0",
                        flex_shrink="0",
                        border_radius="8px",
                    ),
                    columns=rx.breakpoints(initial="2", sm="3", lg="4"),
                    gap="8px",
                    width="100%",
                ),
                spacing="2",
            ),
            padding="14px",
            border_radius="10px",
            bg="rgba(255,255,255,0.02)",
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        # Lista existente
        rx.cond(
            RDOState.mao_obra_items,
            rx.vstack(
                rx.foreach(
                    RDOState.mao_obra_items,
                    lambda item, i: rx.hstack(
                        rx.icon(tag="user", size=16, color=S.PATINA),
                        rx.box(
                            rx.text(
                                item["funcao"],
                                " · ",
                                item["quantidade"],
                                font_size="13px",
                                color=S.TEXT_PRIMARY,
                            ),
                            rx.cond(
                                item["obs"] != "",
                                rx.text(item["obs"], font_size="11px", color=S.TEXT_MUTED),
                                rx.fragment(),
                            ),
                            flex="1",
                        ),
                        rx.icon_button(
                            rx.icon(tag="x", size=12),
                            on_click=RDOState.remove_mao_obra(i),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                        ),
                        padding="10px 12px",
                        border_radius="8px",
                        bg="rgba(42,157,143,0.06)",
                        border="1px solid rgba(42,157,143,0.15)",
                        width="100%",
                        align="center",
                        spacing="2",
                    ),
                ),
                width="100%",
                spacing="2",
            ),
            rx.center(
                rx.text(
                    "Nenhum profissional adicionado ainda", font_size="13px", color=S.TEXT_MUTED
                ),
                padding="24px",
            ),
        ),
        _nav_buttons(next_label="Equipamentos →"),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════════════════════════
# STEP 3 — Equipamentos
# ══════════════════════════════════════════════════════════════
def step3_equipamentos() -> rx.Component:
    return rx.vstack(
        _section_title("truck", "Equipamentos Mobilizados"),
        rx.box(
            rx.vstack(
                rx.text(
                    "Adicionar equipamento",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_weight="600",
                    margin_bottom="8px",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Descrição (ex: Betoneira)",
                        value=RDOState.eq_desc,
                        on_change=RDOState.set_eq_desc,
                        **_input_style_sm(),
                    ),
                    rx.input(
                        placeholder="Qtd",
                        value=RDOState.eq_qtd,
                        on_change=RDOState.set_eq_qtd,
                        type="number",
                        min="1",
                        **_input_style_sm(),
                    ),
                    rx.select(
                        _STATUS_EQUIP,
                        value=RDOState.eq_status,
                        on_change=RDOState.set_eq_status,
                        width="100%",
                    ),
                    rx.button(
                        rx.icon(tag="plus", size=18),
                        on_click=RDOState.add_eq,
                        bg=S.COPPER,
                        color="white",
                        height="40px",
                        width="40px",
                        padding="0",
                        flex_shrink="0",
                        border_radius="8px",
                    ),
                    columns=rx.breakpoints(initial="2", sm="3", lg="4"),
                    gap="8px",
                    width="100%",
                ),
                spacing="2",
            ),
            padding="14px",
            border_radius="10px",
            bg="rgba(255,255,255,0.02)",
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        rx.cond(
            RDOState.equipamentos_items,
            rx.vstack(
                rx.foreach(
                    RDOState.equipamentos_items,
                    lambda item, i: rx.hstack(
                        rx.icon(tag="truck", size=16, color=S.COPPER),
                        rx.text(
                            item["descricao"],
                            " · ",
                            item["quantidade"],
                            " · ",
                            item["status"],
                            font_size="13px",
                            color=S.TEXT_PRIMARY,
                            flex="1",
                        ),
                        rx.icon_button(
                            rx.icon(tag="x", size=12),
                            on_click=RDOState.remove_equipamento(i),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                        ),
                        padding="10px 12px",
                        border_radius="8px",
                        bg="rgba(201,139,42,0.06)",
                        border="1px solid rgba(201,139,42,0.15)",
                        width="100%",
                        align="center",
                        spacing="2",
                    ),
                ),
                width="100%",
                spacing="2",
            ),
            rx.center(
                rx.text(
                    "Nenhum equipamento adicionado ainda", font_size="13px", color=S.TEXT_MUTED
                ),
                padding="24px",
            ),
        ),
        _nav_buttons(next_label="Atividades →"),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════════════════════════
# STEP 4 — Atividades
# ══════════════════════════════════════════════════════════════
def step4_atividades() -> rx.Component:
    return rx.vstack(
        _section_title("list-checks", "Atividades Executadas"),
        rx.box(
            rx.vstack(
                rx.text(
                    "Adicionar atividade",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_weight="600",
                    margin_bottom="8px",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Descreva a atividade executada",
                        value=RDOState.at_desc,
                        on_change=RDOState.set_at_desc,
                        **_input_style_sm(),
                        flex="1",
                    ),
                    rx.hstack(
                        rx.input(
                            placeholder="100",
                            value=RDOState.at_pct,
                            on_change=RDOState.set_at_pct,
                            type="number",
                            min="0",
                            max="100",
                            **{**_input_style_sm(), "width": "70px"},
                        ),
                        rx.text("%", color=S.TEXT_MUTED, font_size="13px"),
                        spacing="1",
                        align="center",
                    ),
                    rx.button(
                        rx.icon(tag="plus", size=18),
                        on_click=RDOState.add_at,
                        bg=S.COPPER,
                        color="white",
                        height="40px",
                        width="40px",
                        padding="0",
                        flex_shrink="0",
                        border_radius="8px",
                    ),
                    width="100%",
                    align="end",
                    spacing="2",
                ),
                spacing="2",
            ),
            padding="14px",
            border_radius="10px",
            bg="rgba(255,255,255,0.02)",
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        rx.cond(
            RDOState.atividades_items,
            rx.vstack(
                rx.foreach(
                    RDOState.atividades_items,
                    lambda item, i: rx.hstack(
                        rx.icon(tag="check-circle", size=16, color=S.PATINA),
                        rx.text(
                            item["atividade"], font_size="13px", color=S.TEXT_PRIMARY, flex="1"
                        ),
                        rx.badge(
                            item["percentual"], "%", color_scheme="teal", variant="soft", size="1"
                        ),
                        rx.icon_button(
                            rx.icon(tag="x", size=12),
                            on_click=RDOState.remove_atividade(i),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                        ),
                        padding="10px 12px",
                        border_radius="8px",
                        bg="rgba(42,157,143,0.06)",
                        border="1px solid rgba(42,157,143,0.15)",
                        width="100%",
                        align="center",
                        spacing="2",
                    ),
                ),
                width="100%",
                spacing="2",
            ),
            rx.center(
                rx.text("Nenhuma atividade adicionada ainda", font_size="13px", color=S.TEXT_MUTED),
                padding="24px",
            ),
        ),
        _nav_buttons(next_label="Materiais →"),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════════════════════════
# STEP 5 — Materiais + Observações + Preview
# ══════════════════════════════════════════════════════════════
def step5_materiais() -> rx.Component:
    return rx.vstack(
        _section_title("package", "Materiais Utilizados"),
        rx.box(
            rx.vstack(
                rx.text(
                    "Adicionar material",
                    font_size="12px",
                    color=S.TEXT_MUTED,
                    font_weight="600",
                    margin_bottom="8px",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Descrição (ex: Cimento CP-II)",
                        value=RDOState.mt_desc,
                        on_change=RDOState.set_mt_desc,
                        **_input_style_sm(),
                    ),
                    rx.input(
                        placeholder="Qtd",
                        value=RDOState.mt_qtd,
                        on_change=RDOState.set_mt_qtd,
                        type="number",
                        **_input_style_sm(),
                    ),
                    rx.select(
                        _UNIDADES,
                        value=RDOState.mt_unid,
                        on_change=RDOState.set_mt_unid,
                        width="100%",
                    ),
                    rx.button(
                        rx.icon(tag="plus", size=18),
                        on_click=RDOState.add_mt,
                        bg=S.COPPER,
                        color="white",
                        height="40px",
                        width="40px",
                        padding="0",
                        flex_shrink="0",
                        border_radius="8px",
                    ),
                    columns=rx.breakpoints(initial="2", sm="3", lg="4"),
                    gap="8px",
                    width="100%",
                ),
                spacing="2",
            ),
            padding="14px",
            border_radius="10px",
            bg="rgba(255,255,255,0.02)",
            border=f"1px solid {S.BORDER_SUBTLE}",
        ),
        rx.cond(
            RDOState.materiais_items,
            rx.vstack(
                rx.foreach(
                    RDOState.materiais_items,
                    lambda item, i: rx.hstack(
                        rx.icon(tag="package", size=16, color=S.COPPER),
                        rx.text(
                            item["descricao"],
                            " · ",
                            item["quantidade"],
                            " ",
                            item["unidade"],
                            font_size="13px",
                            color=S.TEXT_PRIMARY,
                            flex="1",
                        ),
                        rx.icon_button(
                            rx.icon(tag="x", size=12),
                            on_click=RDOState.remove_material(i),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                        ),
                        padding="10px 12px",
                        border_radius="8px",
                        bg="rgba(201,139,42,0.06)",
                        border="1px solid rgba(201,139,42,0.15)",
                        width="100%",
                        align="center",
                        spacing="2",
                    ),
                ),
                width="100%",
                spacing="2",
            ),
        ),
        # Observações
        _section_title("message-square", "Observações Gerais"),
        rx.text_area(
            placeholder="Descreva ocorrências, pendências, situação geral da obra no dia...",
            value=RDOState.rdo_observacoes,
            on_change=RDOState.set_rdo_observacoes,
            width="100%",
            min_height="120px",
            bg="rgba(255,255,255,0.04)",
            border=f"1px solid {S.BORDER_SUBTLE}",
            _focus={"border_color": S.COPPER},
            _placeholder={"color": "rgba(255,255,255,0.38)"},
        ),
        # Botão gerar preview
        _nav_buttons(
            next_label="Gerar Preview do PDF →",
            next_action=RDOState.generate_preview,
            is_last=True,
        ),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════════════════════════
# PREVIEW PDF INLINE
# ══════════════════════════════════════════════════════════════
def _preview_section() -> rx.Component:
    return rx.vstack(
        # Header preview
        rx.hstack(
            rx.icon(tag="file-check", size=24, color=S.PATINA),
            rx.vstack(
                rx.text(
                    "Preview do RDO",
                    font_size="18px",
                    font_weight="700",
                    color=S.TEXT_PRIMARY,
                    font_family=S.FONT_TECH,
                ),
                rx.text(
                    "Verifique o relatório antes de enviar", font_size="13px", color=S.TEXT_MUTED
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        # iframe do PDF
        rx.box(
            rx.el.iframe(
                src=RDOState.preview_pdf_url,
                width="100%",
                height="100%",
                style={"border": "none", "border_radius": "8px"},
            ),
            width="100%",
            height=["60vh", "70vh", "75vh"],
            border_radius="12px",
            border=f"1px solid {S.BORDER_ACCENT}",
            bg="rgba(255,255,255,0.02)",
            overflow="hidden",
        ),
        # Botões de ação
        rx.box(
            rx.button(
                rx.icon(tag="edit", size=18),
                "Editar Informações",
                on_click=RDOState.edit_form,
                bg="rgba(255,255,255,0.05)",
                color=S.TEXT_PRIMARY,
                border=f"1px solid {S.BORDER_SUBTLE}",
                height="52px",
                width="100%",
                font_weight="600",
                _hover={"bg": "rgba(255,255,255,0.1)"},
            ),
            rx.button(
                rx.icon(tag="send", size=18),
                "Enviar RDO",
                on_click=RDOState.submit_rdo,
                bg=S.PATINA,
                color="white",
                height="52px",
                width="100%",
                font_weight="700",
                _hover={"opacity": "0.9"},
                is_loading=RDOState.is_submitting,
            ),
            display="grid",
            grid_template_columns=["1fr", "1fr", "1fr 1fr"],
            gap="12px",
            width="100%",
        ),
        rx.text(
            "✉️  Ao enviar, o PDF será salvo e enviado por email automaticamente com análise de IA.",
            font_size="12px",
            color=S.TEXT_MUTED,
            text_align="center",
        ),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════════════════════════
# PÁGINA PRINCIPAL
# ══════════════════════════════════════════════════════════════
def _submitting_overlay() -> rx.Component:
    """Full-screen overlay shown while submitting the RDO"""
    return rx.cond(
        RDOState.is_submitting,
        rx.box(
            rx.vstack(
                rx.spinner(size="3", color=S.COPPER),
                rx.text(
                    "Enviando RDO...",
                    color="white",
                    font_weight="700",
                    font_size="18px",
                    font_family=S.FONT_TECH,
                ),
                rx.text(
                    "Gerando PDF e enviando por email. Aguarde...",
                    color=S.TEXT_MUTED,
                    font_size="13px",
                    text_align="center",
                ),
                spacing="4",
                align="center",
            ),
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            z_index="9999",
            bg="rgba(3, 5, 4, 0.85)",
            display="flex",
            align_items="center",
            justify_content="center",
            backdrop_filter="blur(4px)",
        ),
    )


def rdo_form_page() -> rx.Component:
    return rx.vstack(
        # Submitting overlay (fixed, full-screen)
        _submitting_overlay(),
        # Header
        rx.hstack(
            rx.icon(tag="clipboard-list", size=28, color=S.COPPER),
            rx.vstack(
                rx.text("RDO DIÁRIO", **S.PAGE_TITLE_STYLE),
                rx.text(
                    rx.cond(
                        RDOState.is_preview, "Revisar Relatório", "Novo Relatório Diário de Obra"
                    ),
                    **S.PAGE_SUBTITLE_STYLE,
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            width="100%",
            margin_bottom="16px",
        ),
        # Card principal
        rx.box(
            rx.vstack(
                # Progress bar (só no wizard, não no preview)
                rx.cond(
                    ~RDOState.is_preview,
                    rx.box(
                        _progress_bar(),
                        margin_bottom="24px",
                        padding_bottom="16px",
                        border_bottom=f"1px solid {S.BORDER_SUBTLE}",
                    ),
                ),
                # Conteúdo: wizard ou preview
                rx.cond(
                    RDOState.is_preview,
                    _preview_section(),
                    rx.box(
                        rx.cond(RDOState.current_step == 1, step1_cabecalho()),
                        rx.cond(RDOState.current_step == 2, step2_mao_obra()),
                        rx.cond(RDOState.current_step == 3, step3_equipamentos()),
                        rx.cond(RDOState.current_step == 4, step4_atividades()),
                        rx.cond(RDOState.current_step == 5, step5_materiais()),
                        width="100%",
                    ),
                ),
                spacing="0",
                width="100%",
            ),
            **S.GLASS_CARD,
            max_width="800px",
            margin="0 auto",
            width="100%",
        ),
        width="100%",
        padding=["16px", "20px", "32px"],
        spacing="4",
        on_mount=[GlobalState.load_data, RDOState.init_from_user_profile],
    )
