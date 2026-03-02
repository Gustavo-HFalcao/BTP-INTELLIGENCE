
import reflex as rx

def kpi_card(label: str, value: str, icon: str, delta: str = None, is_positive: bool = True, delay: int = 0):
    """Um Card KPI reutilizável com estilo Glassmorphism."""
    return rx.box(
        rx.flex(
            rx.box(
                rx.icon(tag=icon, size=24, stroke_width=1.5),
                class_name="p-3 bg-[#ffffff05] rounded-xl border border-[#ffffff0a] text-copper group-hover:scale-110 transition-transform duration-300"
            ),
            rx.cond(
                delta is not None,
                rx.text(
                    f"{'▲' if is_positive else '▼'} {delta}",
                    class_name=f"px-2 py-1 rounded-md text-[10px] font-bold tracking-wider border {'bg-[#2A9D8F]/10 border-[#2A9D8F]/20 text-[#2A9D8F]' if is_positive else 'bg-[#EF4444]/10 border-[#EF4444]/20 text-[#EF4444]'}"
                )
            ),
            justify="between",
            align="start",
            class_name="mb-4"
        ),
        rx.box(
            rx.text(label, class_name="text-[#889999] text-[10px] uppercase font-bold tracking-[0.2em]"),
            rx.text(value, class_name="text-3xl text-[#E0E0E0] font-tech font-semibold tracking-tight"),
            class_name="space-y-1 relative z-10"
        ),
        # Elemento Decorativo
        rx.box(
            class_name="absolute top-0 right-0 p-2 opacity-30 w-4 h-4 border-t border-r border-copper rounded-tr-lg"
        ),
        class_name=f"glass-panel p-6 rounded-2xl relative group hover:border-copper/50 transition-all duration-500 animate-enter delay-[{delay}ms]"
    )

def sidebar_item(icon: str, label: str, page_id: str, current_page: str, is_collapsed: bool, on_click):
    """Item individual da sidebar."""
    is_active = current_page == page_id
    
    return rx.button(
        rx.icon(tag=icon, size=20, stroke_width=1.5),
        rx.cond(
            ~is_collapsed,
            rx.text(label, class_name="ml-4 text-xs font-bold tracking-widest font-tech")
        ),
        on_click=on_click,
        class_name=f"""
            w-full flex items-center p-3 rounded-lg transition-all duration-300 group relative overflow-hidden
            {'bg-copper/10 text-copper border border-copper/30' if is_active else 'text-[#889999] hover:text-[#E0E0E0] hover:bg-[#ffffff05] border border-transparent'}
        """
    )
