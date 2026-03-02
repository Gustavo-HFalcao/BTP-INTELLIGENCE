"""
Elegant loading screen component with smooth animations
"""

import reflex as rx

from bomtempo.core import styles as S


def loading_screen() -> rx.Component:
    """Full-screen loading with animated progress"""
    return rx.box(
        rx.vstack(
            # Logo/Brand section
            rx.center(
                rx.icon(
                    tag="zap",
                    size=48,
                    color=S.COPPER,
                ),
                width="80px",
                height="80px",
                border_radius="50%",
                bg=f"{S.COPPER_GLOW}",
                border=f"2px solid {S.COPPER}",
                box_shadow=f"0 0 40px {S.COPPER}40, 0 0 80px {S.COPPER}20",
                class_name="pulse-slow",
            ),
            # Company name
            rx.vstack(
                rx.text(
                    "BOMTEMPO",
                    font_family=S.FONT_TECH,
                    font_size="2rem",
                    font_weight="900",
                    color="white",
                    letter_spacing="0.3em",
                ),
                rx.text(
                    "INTELLIGENCE",
                    font_family=S.FONT_TECH,
                    font_size="1.5rem",
                    font_weight="700",
                    color=S.COPPER,
                    letter_spacing="0.1em",
                ),
                margin_top="32px",
                spacing="0",  # Remove default spacing between the two texts
                align="center",
            ),
            # Loading bar
            rx.box(
                rx.box(
                    width="100%",
                    height="100%",
                    bg=f"linear-gradient(90deg, {S.PATINA}, {S.COPPER}, {S.PATINA})",
                    border_radius="9999px",
                    class_name="shimmer",
                ),
                width="200px",
                height="4px",
                bg="rgba(255, 255, 255, 0.1)",
                border_radius="9999px",
                overflow="hidden",
                margin_top="24px",
            ),
            # Status text
            rx.text(
                "Carregando dados do dashboard...",
                font_size="14px",
                color=S.TEXT_MUTED,
                font_weight="500",
                margin_top="16px",
                class_name="fade-in-out",
            ),
            align="center",
            justify="center",
            spacing="0",
        ),
        position="fixed",
        top="0",
        left="0",
        width="100vw",
        height="100vh",
        bg=S.BG_VOID,
        z_index="9999",
        display="flex",
        align_items="center",
        justify_content="center",
    )


def page_transition_wrapper(content: rx.Component, page_name: str = "") -> rx.Component:
    """Wraps page content with fade-in animation"""
    return rx.box(
        content,
        class_name="page-fade-in",
        animation_delay="0.1s",
    )


def skeleton_card() -> rx.Component:
    """Skeleton loader for cards during data loading"""
    return rx.box(
        rx.vstack(
            # Header skeleton
            rx.hstack(
                rx.box(
                    width="40px",
                    height="40px",
                    border_radius="50%",
                    bg="rgba(255, 255, 255, 0.05)",
                    class_name="skeleton-shimmer",
                ),
                rx.vstack(
                    rx.box(
                        width="120px",
                        height="12px",
                        border_radius="6px",
                        bg="rgba(255, 255, 255, 0.05)",
                        class_name="skeleton-shimmer",
                    ),
                    rx.box(
                        width="80px",
                        height="8px",
                        border_radius="4px",
                        bg="rgba(255, 255, 255, 0.03)",
                        class_name="skeleton-shimmer",
                    ),
                    spacing="2",
                    align="start",
                ),
                spacing="3",
                margin_bottom="16px",
            ),
            # Content skeletons
            rx.box(
                width="100%",
                height="60px",
                border_radius="8px",
                bg="rgba(255, 255, 255, 0.05)",
                class_name="skeleton-shimmer",
                margin_bottom="12px",
            ),
            rx.box(
                width="80%",
                height="12px",
                border_radius="6px",
                bg="rgba(255, 255, 255, 0.03)",
                class_name="skeleton-shimmer",
            ),
            width="100%",
            spacing="0",
        ),
        **S.GLASS_CARD,
        min_height="200px",
    )


def inline_spinner(text: str = "Processando...") -> rx.Component:
    """Inline loading indicator for buttons/actions"""
    return rx.hstack(
        rx.spinner(
            size="1",
            color=S.COPPER,
        ),
        rx.text(
            text,
            font_size="12px",
            color=S.TEXT_MUTED,
            font_weight="500",
        ),
        spacing="2",
        align="center",
    )


# ── Enterprise UX — New Components ────────────────────────────────────────────


def skeleton_line(width: str = "100%", height: str = "12px", radius: str = "6px") -> rx.Component:
    """Single shimmer skeleton line — parametric width/height."""
    return rx.box(
        width=width,
        height=height,
        border_radius=radius,
        bg="rgba(255, 255, 255, 0.05)",
        class_name="skeleton-shimmer",
    )


def skeleton_block(width: str = "100%", height: str = "60px", radius: str = "8px") -> rx.Component:
    """Shimmer skeleton block for chart/image placeholders."""
    return rx.box(
        width=width,
        height=height,
        border_radius=radius,
        bg="rgba(255, 255, 255, 0.05)",
        class_name="skeleton-shimmer",
    )


def skeleton_kpi() -> rx.Component:
    """Skeleton for a single KPI card — matches kpi_card() layout."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                skeleton_block(width="44px", height="44px", radius="12px"),
                rx.spacer(),
                skeleton_line(width="60px", height="22px"),
                width="100%",
            ),
            skeleton_line(width="80px", height="36px"),
            skeleton_line(width="120px", height="10px"),
            spacing="4",
            width="100%",
        ),
        background=S.BG_GLASS,
        backdrop_filter="blur(12px)",
        border=f"1px solid {S.BORDER_SUBTLE}",
        border_radius="16px",
        padding="24px",
        min_height="130px",
    )


def skeleton_chart(height: str = "300px") -> rx.Component:
    """Skeleton for a chart with glass card wrapper."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                skeleton_line(width="160px", height="18px"),
                rx.spacer(),
                skeleton_line(width="80px", height="12px"),
                width="100%",
            ),
            skeleton_block(width="100%", height=height, radius="12px"),
            spacing="4",
            width="100%",
        ),
        background=S.BG_GLASS,
        backdrop_filter="blur(12px)",
        border=f"1px solid {S.BORDER_SUBTLE}",
        border_radius="24px",
        padding="32px",
        width="100%",
    )


def skeleton_kpi_grid() -> rx.Component:
    """4-column KPI skeleton grid — mirrors the real kpi_grid()."""
    return rx.grid(
        skeleton_kpi(),
        skeleton_kpi(),
        skeleton_kpi(),
        skeleton_kpi(),
        columns=rx.breakpoints(initial="1", sm="2", lg="4"),
        spacing="6",
        width="100%",
    )


def loading_wrapper(
    is_loading,
    skeleton_layout: rx.Component,
    content: rx.Component,
) -> rx.Component:
    """
    Universal anti-flicker loading wrapper.
    Shows skeleton while loading, fades in content when done.
    Never renders zero-values mid-load.
    """
    return rx.cond(
        is_loading,
        skeleton_layout,
        rx.box(content, class_name="animate-enter"),
    )


def empty_state(
    title: str = "Nenhum dado encontrado",
    subtitle: str = "Os dados aparecerão aqui quando disponíveis.",
    icon: str = "inbox",
) -> rx.Component:
    """
    Standard empty state component.
    Use when a list/table has no items — never leave an isolated empty grid.
    """
    return rx.center(
        rx.vstack(
            rx.box(
                rx.icon(tag=icon, size=48, color=S.TEXT_MUTED),
                class_name="empty-state-icon",
            ),
            rx.text(title, class_name="empty-state-title"),
            rx.text(subtitle, class_name="empty-state-subtitle"),
            class_name="empty-state",
            align="center",
            spacing="2",
        ),
        width="100%",
        min_height="200px",
    )
