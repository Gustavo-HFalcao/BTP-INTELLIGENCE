
import reflex as rx
import reflex_recharts as recharts
from .data import contracts, activities, financials, construction_records, om_records
from .components import kpi_card, sidebar_item
from google import genai
import os

class State(rx.State):
    """O estado da aplicação - Backend Python."""
    active_page: str = "overview"
    sidebar_collapsed: bool = False
    
    # Filtros e Seleções
    project_search: str = ""
    selected_contract_id: str = ""
    finance_cockpit: str = "Todos"
    om_time_filter: str = "Mês"
    
    # Chat IA
    chat_input: str = ""
    chat_history: list[dict] = [
        {"role": "ai", "content": "Olá! Sou o Assistente BOMTEMPO. Analiso dados de engenharia em tempo real. Como posso ajudar?"}
    ]
    is_typing: bool = False

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed

    def set_page(self, page: str):
        self.active_page = page

    def set_contract(self, contract: str):
        self.selected_contract_id = contract

    # Lógica de IA (Google Gemini)
    async def send_message(self):
        if not self.chat_input:
            return
            
        user_msg = self.chat_input
        self.chat_history.append({"role": "user", "content": user_msg})
        self.chat_input = ""
        self.is_typing = True
        yield
        
        # Simulação de contexto (Na prática, você enviaria os JSONs de dados relevantes)
        context = f"Contexto de dados: Contratos ativos={len(contracts)}, Faturamento Total={sum(c['value'] for c in contracts)}"
        
        try:
            client = genai.Client(api_key=os.environ.get("API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Você é um assistente de engenharia. {context}. Pergunta do usuário: {user_msg}"
            )
            self.chat_history.append({"role": "ai", "content": response.text})
        except Exception as e:
            self.chat_history.append({"role": "ai", "content": "Erro ao conectar com Gemini. Verifique a API Key."})
        
        self.is_typing = False

# --- ESTILOS COMPARTILHADOS ---
tooltip_style = {
    "backgroundColor": "rgba(8, 18, 16, 0.95)",
    "borderColor": "rgba(201, 139, 42, 0.3)",
    "borderRadius": "12px",
    "borderWidth": "1px",
    "padding": "12px",
    "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.5)",
    "backdropFilter": "blur(8px)",
    "color": "#E0E0E0",
    "fontFamily": "Rajdhani, sans-serif",
    "textTransform": "uppercase",
    "fontSize": "12px",
    "letterSpacing": "0.05em"
}

item_style = {
    "color": "#C98B2A",
    "fontFamily": "JetBrains Mono, monospace",
    "fontSize": "14px",
    "fontWeight": "bold"
}

# --- PÁGINAS ---

def overview_view():
    """Visão Geral / Command Center."""
    total_val = sum(c['value'] for c in contracts) / 1000000
    active_len = len([c for c in contracts if c['status'] == 'Em Execução'])
    
    # Dados para gráfico de barras
    bar_data = [{"name": c['cliente'].split()[0], "value": c['value']/1000000} for c in contracts]
    
    return rx.vstack(
        # Header
        rx.box(
            rx.vstack(
                rx.flex(
                    rx.text("SYSTEM ONLINE", class_name="px-2 py-1 bg-copper text-void text-[10px] font-bold uppercase tracking-widest rounded-sm"),
                    rx.box(class_name="h-[1px] w-12 bg-copper/50"),
                    align="center", spacing="3", class_name="mb-4"
                ),
                rx.heading("VISÃO GERAL", class_name="text-5xl font-bold text-white mb-4 font-tech"),
                rx.text("Telemetria financeira e operacional em tempo real.", class_name="text-[#889999] text-lg font-light"),
                align="start"
            ),
            class_name="glass-panel p-12 rounded-3xl w-full relative overflow-hidden animate-enter"
        ),
        
        # KPIs
        rx.grid(
            kpi_card("Receita Total", f"R$ {total_val:.1f}M", "dollar-sign", "+12.5%", True, 100),
            kpi_card("Contratos Ativos", str(active_len), "hard-hat", None, True, 200),
            kpi_card("Velocidade Média", "45%", "trending-up", "+2.1%", True, 300),
            kpi_card("Health Score", "94.2", "target", None, True, 400),
            gap="6", width="100%", class_name="grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
        ),
        
        # Gráficos
        rx.grid(
            rx.box(
                rx.heading("Alocação de Volume", class_name="text-[#E0E0E0] font-tech text-xl font-bold mb-8"),
                rx.box(
                    recharts.bar_chart(
                        recharts.bar(data_key="value", fill="#C98B2A", radius=[4, 4, 0, 0]),
                        recharts.x_axis(data_key="name", stroke="#889999", font_size=10),
                        recharts.y_axis(stroke="#889999", font_size=10, unit="M"),
                        recharts.cartesian_grid(stroke_dasharray="3 3", stroke="#ffffff0a", vertical=False),
                        recharts.tooltip(
                            cursor={"fill": "rgba(255, 255, 255, 0.05)"},
                            content_style=tooltip_style,
                            item_style=item_style,
                            separator=": R$ "
                        ),
                        data=bar_data,
                    ),
                    height="300px", width="100%"
                ),
                class_name="glass-panel p-8 rounded-3xl lg:col-span-2"
            ),
            rx.box(
                rx.heading("Status", class_name="text-[#E0E0E0] font-tech text-xl font-bold mb-8"),
                # Simplificado Pie Chart para Reflex
                rx.center(
                    rx.text(f"{len(contracts)} Projetos", class_name="text-4xl font-bold text-white font-tech"),
                    class_name="h-[300px]"
                ),
                class_name="glass-panel p-8 rounded-3xl"
            ),
            gap="8", width="100%", class_name="grid-cols-1 lg:grid-cols-3"
        ),
        spacing="8", width="100%"
    )

def projects_view():
    """Gestão de Projetos e Gantt."""
    return rx.vstack(
        rx.flex(
            rx.heading("GESTÃO DE PROJETOS", class_name="text-3xl font-tech font-bold text-white"),
            rx.input(
                placeholder="Buscar contrato...", 
                value=State.project_search,
                on_change=State.set_project_search,
                class_name="bg-[#ffffff05] border border-[#ffffff0a] text-white px-4 py-2 rounded-xl"
            ),
            justify="between", width="100%", align="center"
        ),
        rx.cond(
            State.selected_contract_id == "",
            # Lista
            rx.grid(
                rx.foreach(
                    contracts,
                    lambda c: rx.box(
                        rx.heading(c['cliente'], class_name="text-white font-bold text-xl"),
                        rx.text(c['contrato'], class_name="text-copper font-tech font-bold"),
                        rx.progress(value=c['progress'], class_name="mt-4 bg-[#ffffff0a]", color="var(--patina-500)"),
                        on_click=lambda: State.set_contract(c['contrato']),
                        class_name="glass-panel p-6 rounded-2xl cursor-pointer hover:border-copper transition-all"
                    )
                ),
                gap="6", width="100%", class_name="grid-cols-1 md:grid-cols-3"
            ),
            # Detalhe (Gantt)
            rx.vstack(
                rx.button("Voltar", on_click=lambda: State.set_contract(""), class_name="text-copper mb-4"),
                rx.box(
                    rx.heading("Cronograma de Atividades", class_name="text-white font-tech font-bold mb-6"),
                    rx.vstack(
                        rx.foreach(
                            activities,
                            lambda act: rx.box(
                                rx.flex(
                                    rx.text(act['atividade'], class_name="text-white text-xs font-bold"),
                                    rx.text(act['fase'], class_name="text-[#889999] text-xs"),
                                    justify="between", class_name="mb-1"
                                ),
                                rx.box(
                                    rx.box(
                                        width=f"{act['conclusao']}%",
                                        class_name=rx.cond(
                                            act['critico'], 
                                            "h-full rounded-full bg-gradient-to-r from-red-500 to-red-700",
                                            "h-full rounded-full bg-gradient-to-r from-copper to-yellow-500"
                                        )
                                    ),
                                    class_name="h-4 bg-[#ffffff05] rounded-full overflow-hidden w-full"
                                ),
                                width="100%"
                            )
                        ),
                        spacing="4", width="100%"
                    ),
                    class_name="glass-panel p-8 rounded-3xl w-full"
                ),
                width="100%"
            )
        ),
        width="100%", spacing="6"
    )

def construction_view():
    """Acompanhamento de Obras (Velocímetro/Barras)."""
    return rx.vstack(
        rx.heading("FIELD OPS - ACOMPANHAMENTO", class_name="text-3xl font-tech font-bold text-white"),
        rx.grid(
            # Coluna Principal
            rx.vstack(
                rx.box(
                    rx.heading("Progresso por Disciplina", class_name="text-white font-tech text-xl font-bold mb-6"),
                    rx.vstack(
                        rx.foreach(
                            construction_records,
                            lambda rec: rx.box(
                                rx.flex(
                                    rx.text(rec['categoria'], class_name="text-sm font-bold text-white"),
                                    rx.text(f"R: {rec['realizado']*100}%", class_name="text-xs font-mono text-patina"),
                                    justify="between", class_name="mb-1"
                                ),
                                rx.box(
                                    rx.box(
                                        width=f"{rec['realizado']*100}%",
                                        class_name="h-full bg-patina absolute top-0 left-0 z-20"
                                    ),
                                    rx.box(
                                        width=f"{rec['previsto']*100}%",
                                        class_name="h-full bg-white/20 absolute top-0 left-0 z-10 border-r-2 border-white/50"
                                    ),
                                    class_name="h-2 bg-[#ffffff05] rounded-full overflow-hidden relative w-full"
                                ),
                                width="100%"
                            )
                        ),
                        spacing="6", width="100%"
                    ),
                    class_name="glass-panel p-8 rounded-3xl w-full"
                ),
                class_name="lg:col-span-2"
            ),
            # Coluna Lateral (Velocímetro simulado)
            rx.box(
                rx.center(
                    rx.heading("82%", class_name="text-6xl font-tech font-bold text-white"),
                    rx.text("AVANÇO FÍSICO GLOBAL", class_name="text-xs text-[#889999] tracking-widest mt-2"),
                    direction="column", class_name="h-full"
                ),
                class_name="glass-panel p-8 rounded-3xl h-[300px]"
            ),
            gap="8", width="100%", class_name="grid-cols-1 lg:grid-cols-3"
        ),
        width="100%"
    )

def finance_view():
    """Financeiro: Medido vs A Medir."""
    return rx.vstack(
        rx.flex(
            rx.heading("FINANCEIRO", class_name="text-3xl font-tech font-bold text-white"),
            rx.select(
                ["Todos", "Contrato", "Terceirizado", "Operação"],
                value=State.finance_cockpit,
                on_change=State.set_finance_cockpit,
                class_name="bg-[#030504] border border-[#ffffff0a] text-white"
            ),
            justify="between", width="100%"
        ),
        rx.grid(
            kpi_card("Total Contratado", "R$ 485.0k", "wallet"),
            kpi_card("Total Medido", "R$ 254.5k", "dollar-sign", "Executado", True),
            kpi_card("Saldo à Medir", "R$ 230.5k", "trending-up", "Pendente", False),
            gap="6", width="100%", class_name="grid-cols-1 md:grid-cols-3"
        ),
        # Tabela Detalhada
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Cockpit", class_name="text-[#889999]"),
                        rx.table.column_header_cell("Marco", class_name="text-[#889999]"),
                        rx.table.column_header_cell("Valor (R$)", class_name="text-[#889999] text-right"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        financials,
                        lambda f: rx.table.row(
                            rx.table.cell(f['cockpit'], class_name="text-white"),
                            rx.table.cell(f['marco'], class_name="text-copper"),
                            rx.table.cell(f['servicoContratado'], class_name="text-white font-mono text-right"),
                        )
                    )
                ),
                width="100%"
            ),
            class_name="glass-panel p-6 rounded-3xl w-full"
        ),
        width="100%", spacing="8"
    )

def om_view():
    """O&M View: Gráfico Composto e Tabela."""
    return rx.vstack(
        rx.heading("O&M - GESTÃO DE ATIVOS", class_name="text-3xl font-tech font-bold text-white"),
        rx.box(
            rx.heading("Performance de Geração (Mês)", class_name="text-white font-tech text-xl font-bold mb-6"),
            rx.box(
                recharts.composed_chart(
                    recharts.bar(data_key="kwhAcumulado", fill="#ffffff10", bar_size=20, y_axis_id="right", name="Acumulado"),
                    recharts.line(data_key="energiaInjetada", stroke="#2A9D8F", stroke_width=3, y_axis_id="left", name="Injetada"),
                    recharts.line(data_key="geracaoPrevista", stroke="#E0A63B", stroke_dasharray="5 5", y_axis_id="left", name="Prevista"),
                    recharts.x_axis(data_key="mes", stroke="#889999", font_size=10),
                    recharts.y_axis(y_axis_id="left", stroke="#889999", font_size=10, unit="kWh"),
                    recharts.y_axis(y_axis_id="right", orientation="right", stroke="#889999", font_size=10, unit="kWh"),
                    recharts.cartesian_grid(stroke_dasharray="3 3", stroke="#ffffff0a", vertical=False),
                    recharts.tooltip(
                        cursor={"fill": "rgba(255, 255, 255, 0.05)"},
                        content_style=tooltip_style,
                        item_style=item_style
                    ),
                    recharts.legend(),
                    data=om_records,
                ),
                height="400px", width="100%"
            ),
            class_name="glass-panel p-8 rounded-3xl w-full"
        ),
        width="100%"
    )

def chat_view():
    """Chat IA com Gemini."""
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.foreach(
                    State.chat_history,
                    lambda msg: rx.box(
                        rx.text(msg['content']),
                        class_name=rx.cond(
                            msg['role'] == 'user',
                            "bg-copper text-void p-4 rounded-2xl rounded-tr-none self-end max-w-[80%]",
                            "bg-depth border border-copper/20 text-white p-4 rounded-2xl rounded-tl-none self-start max-w-[80%]"
                        )
                    )
                ),
                spacing="4", width="100%", align="stretch"
            ),
            class_name="flex-1 overflow-y-auto p-6 space-y-4"
        ),
        rx.box(
            rx.flex(
                rx.input(
                    value=State.chat_input,
                    on_change=State.set_chat_input,
                    placeholder="Pergunte sobre rentabilidade ou prazos...",
                    class_name="flex-1 bg-depth border border-white/10 text-white p-4 rounded-xl mr-2 focus:border-copper outline-none"
                ),
                rx.button(
                    rx.icon("send", size=20),
                    on_click=State.send_message,
                    class_name="bg-copper text-void p-4 rounded-xl hover:bg-copper/80"
                ),
                width="100%"
            ),
            class_name="p-4 border-t border-white/10 bg-void/50"
        ),
        class_name="h-[calc(100vh-8rem)] glass-panel rounded-3xl flex flex-col overflow-hidden w-full"
    )

def index():
    """Layout Principal."""
    return rx.flex(
        # Sidebar Container
        rx.cond(
            State.sidebar_collapsed,
            rx.box(
                rx.vstack(
                    rx.button(rx.icon("menu"), on_click=State.toggle_sidebar, class_name="text-white mb-8"),
                    sidebar_item("layout-dashboard", "", "overview", State.active_page, True, lambda: State.set_page("overview")),
                    sidebar_item("briefcase", "", "projects", State.active_page, True, lambda: State.set_page("projects")),
                    sidebar_item("construction", "", "construction", State.active_page, True, lambda: State.set_page("construction")),
                    sidebar_item("wallet", "", "finance", State.active_page, True, lambda: State.set_page("finance")),
                    sidebar_item("zap", "", "om", State.active_page, True, lambda: State.set_page("om")),
                    sidebar_item("message-square", "", "ai_chat", State.active_page, True, lambda: State.set_page("ai_chat")),
                    class_name="p-4 items-center"
                ),
                class_name="glass-panel w-20 h-[calc(100vh-2rem)] my-4 ml-4 rounded-2xl sticky top-4 transition-all"
            ),
            # Sidebar Expandida
            rx.box(
                rx.vstack(
                    rx.flex(
                        rx.box(
                            rx.text("BOMTEMPO", class_name="text-copper font-bold text-2xl font-tech"),
                            rx.text("ENGENHARIA", class_name="text-[#889999] text-[9px] uppercase font-bold tracking-[0.3em]"),
                        ),
                        rx.button(rx.icon("x", size=16), on_click=State.toggle_sidebar, class_name="text-[#889999]"),
                        justify="between", width="100%", class_name="mb-8"
                    ),
                    sidebar_item("layout-dashboard", "VISÃO GERAL", "overview", State.active_page, False, lambda: State.set_page("overview")),
                    sidebar_item("briefcase", "PROJETOS", "projects", State.active_page, False, lambda: State.set_page("projects")),
                    sidebar_item("construction", "OBRAS", "construction", State.active_page, False, lambda: State.set_page("construction")),
                    sidebar_item("wallet", "FINANCEIRO", "finance", State.active_page, False, lambda: State.set_page("finance")),
                    sidebar_item("zap", "O&M", "om", State.active_page, False, lambda: State.set_page("om")),
                    sidebar_item("message-square", "CHAT IA", "ai_chat", State.active_page, False, lambda: State.set_page("ai_chat")),
                    class_name="p-6"
                ),
                class_name="glass-panel w-72 h-[calc(100vh-2rem)] my-4 ml-4 rounded-2xl sticky top-4 transition-all"
            )
        ),
        
        # Conteúdo Principal
        rx.box(
            rx.cond(State.active_page == "overview", overview_view()),
            rx.cond(State.active_page == "projects", projects_view()),
            rx.cond(State.active_page == "construction", construction_view()),
            rx.cond(State.active_page == "finance", finance_view()),
            rx.cond(State.active_page == "om", om_view()),
            rx.cond(State.active_page == "ai_chat", chat_view()),
            class_name="flex-1 p-6 overflow-x-hidden min-h-screen"
        ),
        class_name="min-h-screen bg-void text-[#E0E0E0] font-body"
    )

app = rx.App(stylesheets=["/styles.css"])
app.add_page(index)
