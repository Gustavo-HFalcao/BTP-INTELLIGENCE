"""
Chat Bubble Component — Premium Glassmorphic
User: right-aligned, copper/14 transparent bg, white text, copper border, sharp top-right corner.
AI:   left-aligned, white/4 glassmorphic card, subtle white border, copper sparkles avatar.
"""

import reflex as rx

from bomtempo.core import styles as S


def message_bubble(message: dict) -> rx.Component:
    """
    Premium glassmorphic chat bubble with hover lift.
    Skips system messages silently.
    """
    is_user = message["role"] == "user"

    return rx.cond(
        message["role"] == "system",
        rx.fragment(),
        rx.box(
            rx.hstack(
                # ── AI Avatar (left) ──────────────────────────────────────
                rx.cond(
                    ~is_user,
                    rx.center(
                        rx.icon(tag="sparkles", size=14, color="#0A1F1A"),
                        width="34px",
                        height="34px",
                        border_radius="50%",
                        bg=S.COPPER,
                        flex_shrink="0",
                        margin_top="4px",
                        box_shadow="0 0 16px rgba(201, 139, 42, 0.5)",
                    ),
                ),
                # ── Message Content ───────────────────────────────────────
                rx.box(
                    rx.markdown(
                        message["content"],
                        color="white",
                        component_map={
                            "h2": lambda *children, **props: rx.heading(
                                *children,
                                size="4",
                                color=S.COPPER,
                                font_family=S.FONT_TECH,
                                margin_top="1em",
                                margin_bottom="0.3em",
                                **props,
                            ),
                            "h3": lambda *children, **props: rx.heading(
                                *children,
                                size="3",
                                color=S.COPPER_LIGHT,
                                font_family=S.FONT_TECH,
                                margin_top="0.8em",
                                margin_bottom="0.3em",
                                **props,
                            ),
                            "p": lambda *children, **props: rx.el.p(
                                *children,
                                style={
                                    "color": "white",
                                    "lineHeight": "1.7",
                                    "marginBottom": "6px",
                                    "wordSpacing": "0.02em",
                                },
                            ),
                            "strong": lambda *children, **props: rx.el.strong(
                                *children,
                                style={
                                    "color": S.COPPER_LIGHT,
                                    "fontWeight": "700",
                                },
                                **props,
                            ),
                            "em": lambda *children, **props: rx.el.em(
                                *children,
                                style={
                                    "color": S.TEXT_MUTED,
                                    "fontStyle": "normal",
                                    "fontSize": "0.92em",
                                },
                                **props,
                            ),
                            "li": lambda *children, **props: rx.el.li(
                                *children,
                                style={
                                    "color": "white",
                                    "marginBottom": "4px",
                                    "lineHeight": "1.6",
                                },
                                **props,
                            ),
                            "code": lambda *children, **props: rx.el.code(
                                *children,
                                style={
                                    "background": "rgba(255,255,255,0.08)",
                                    "color": S.COPPER_LIGHT,
                                    "padding": "1px 5px",
                                    "borderRadius": "3px",
                                    "fontFamily": S.FONT_MONO,
                                    "fontSize": "0.85em",
                                },
                                **props,
                            ),
                            "table": lambda *children, **props: rx.el.table(
                                *children,
                                style={
                                    "width": "100%",
                                    "borderCollapse": "collapse",
                                    "marginTop": "10px",
                                    "marginBottom": "10px",
                                    "fontSize": "12px",
                                    "border": f"1px solid {S.BORDER_ACCENT}",
                                },
                                **props,
                            ),
                            "thead": lambda *children, **props: rx.el.thead(
                                *children,
                                style={"backgroundColor": "rgba(10,31,26,0.8)"},
                                **props,
                            ),
                            "tbody": lambda *children, **props: rx.el.tbody(
                                *children, **props
                            ),
                            "tr": lambda *children, **props: rx.el.tr(
                                *children,
                                style={"borderBottom": f"1px solid {S.BORDER_SUBTLE}"},
                                **props,
                            ),
                            "th": lambda *children, **props: rx.el.th(
                                *children,
                                style={
                                    "padding": "8px 12px",
                                    "textAlign": "left",
                                    "fontWeight": "700",
                                    "color": S.COPPER_LIGHT,
                                    "borderRight": f"1px solid {S.BORDER_SUBTLE}",
                                    "fontSize": "11px",
                                    "letterSpacing": "0.04em",
                                    "backgroundColor": "rgba(10,31,26,0.9)",
                                },
                                **props,
                            ),
                            "td": lambda *children, **props: rx.el.td(
                                *children,
                                style={
                                    "padding": "7px 12px",
                                    "color": "white",
                                    "borderRight": f"1px solid {S.BORDER_SUBTLE}",
                                    "fontSize": "12px",
                                    "lineHeight": "1.5",
                                },
                                **props,
                            ),
                        },
                    ),
                    bg=rx.cond(
                        is_user,
                        "rgba(201, 139, 42, 0.14)",
                        "rgba(255, 255, 255, 0.04)",
                    ),
                    backdrop_filter=rx.cond(~is_user, "blur(12px)", "none"),
                    padding="14px 18px",
                    border_radius="18px",
                    border_top_right_radius=rx.cond(is_user, "4px", "18px"),
                    border_top_left_radius=rx.cond(~is_user, "4px", "18px"),
                    border=rx.cond(
                        is_user,
                        "1px solid rgba(201, 139, 42, 0.30)",
                        "1px solid rgba(255, 255, 255, 0.07)",
                    ),
                    box_shadow=rx.cond(
                        ~is_user,
                        "0 4px 24px rgba(0, 0, 0, 0.3)",
                        "0 4px 16px rgba(201, 139, 42, 0.1)",
                    ),
                    max_width="80%",
                    font_weight=rx.cond(is_user, "500", "400"),
                    overflow_x="auto",
                    class_name=rx.cond(is_user, "chat-bubble-user", "chat-bubble-ai"),
                ),
                # ── User Avatar (right) ───────────────────────────────────
                rx.cond(
                    is_user,
                    rx.center(
                        rx.icon(tag="user", size=14, color=S.COPPER),
                        width="34px",
                        height="34px",
                        border_radius="50%",
                        bg="rgba(201, 139, 42, 0.15)",
                        border="1px solid rgba(201, 139, 42, 0.35)",
                        flex_shrink="0",
                        margin_top="4px",
                    ),
                ),
                align="start",
                justify=rx.cond(is_user, "end", "start"),
                spacing="3",
                width="100%",
                flex_direction=rx.cond(is_user, "row-reverse", "row"),
            ),
            width="100%",
            padding_y="6px",
        ),
    )
