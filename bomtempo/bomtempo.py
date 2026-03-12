# ruff: noqa: E402
import reflex as rx

from bomtempo.core import styles as S
from bomtempo.core.rdo_service import RDOService
from bomtempo.layouts.default import default_layout
from bomtempo.state.global_state import GlobalState

# Inicializar SQLite RDO
RDOService.init_database()
from bomtempo.pages.analytics import analytics_page
from bomtempo.pages.chat_ia import chat_ia_page
from bomtempo.pages.financeiro import financeiro_page
from bomtempo.pages.index import index_page
from bomtempo.pages.obras import obras_page
from bomtempo.pages.om import om_page
from bomtempo.pages.previsoes import previsoes_page
from bomtempo.pages.projetos import projetos_page
from bomtempo.pages.rdo_dashboard import rdo_dashboard_page
from bomtempo.state.rdo_dashboard_state import RDODashboardState
from bomtempo.pages.rdo_form import rdo_form_page
from bomtempo.pages.rdo_historico import RDOHistoricoState, rdo_historico_page
from bomtempo.pages.reembolso_dashboard import reembolso_dashboard_page
from bomtempo.pages.reembolso_form import reembolso_form_page
from bomtempo.state.reembolso_state import ReembolsoState
from bomtempo.pages.editar_dados import editar_dados_page
from bomtempo.state.edit_state import EditState
from bomtempo.pages.relatorios import relatorios_page
from bomtempo.state.relatorios_state import RelatoriosState
from bomtempo.pages.alertas import alertas_page
from bomtempo.state.alertas_state import AlertasState
from bomtempo.core.alert_service import start_alert_scheduler
from bomtempo.pages.logs_auditoria import logs_auditoria_page
from bomtempo.state.logs_state import LogsState
from bomtempo.pages.usuarios import usuarios_page
from bomtempo.state.usuarios_state import UsuariosState

# Start proactive alerts background scheduler
start_alert_scheduler()

def index():
    return default_layout(index_page())


def financeiro():
    return default_layout(financeiro_page())


def obras():
    return default_layout(obras_page())


def projetos():
    return default_layout(projetos_page())


def om():
    return default_layout(om_page())


def analytics():
    return default_layout(analytics_page())


def previsoes():
    return default_layout(previsoes_page())


from bomtempo.pages.mobile_chat import mobile_chat_page


def chat_ia():
    return default_layout(chat_ia_page())


def mobile_chat():
    # No default_layout for mobile
    return mobile_chat_page()


def rdo_form():
    return default_layout(rdo_form_page())


def rdo_historico():
    return default_layout(rdo_historico_page())


def rdo_dashboard():
    return default_layout(rdo_dashboard_page())


def reembolso():
    # Standalone sem sidebar — menu é as 3 tabs da própria página
    return reembolso_form_page()


def reembolso_dash():
    return default_layout(reembolso_dashboard_page())


app = rx.App(
    style=S.GLOBAL_STYLE,
    stylesheets=[
        S.FONT_URL,
        "/style.css",
        "/animations.css",  # Smooth transitions and loading animations
    ],
    theme=rx.theme(
        appearance="dark",
        accent_color="amber",
        radius="none",
    ),
)

app.add_page(index, route="/", title="BOMTEMPO | Visão Geral", on_load=GlobalState.guard_index_page)
app.add_page(
    financeiro, route="/financeiro", title="BOMTEMPO | Financeiro", on_load=GlobalState.load_data
)
app.add_page(
    obras, route="/obras", title="BOMTEMPO | Operações de Campo", on_load=GlobalState.load_data
)
app.add_page(
    projetos,
    route="/projetos",
    title="BOMTEMPO | Portfólio de Projetos",
    on_load=GlobalState.load_data,
)
app.add_page(om, route="/om", title="BOMTEMPO | O&M Performance", on_load=GlobalState.load_data)
app.add_page(
    analytics,
    route="/analytics",
    title="BOMTEMPO | Analytics & Insights",
    on_load=GlobalState.load_data,
)
app.add_page(
    previsoes, route="/previsoes", title="BOMTEMPO | Previsões", on_load=GlobalState.load_data
)
app.add_page(chat_ia, route="/chat-ia", title="BOMTEMPO | Chat IA", on_load=GlobalState.load_data)
app.add_page(
    mobile_chat, route="/mobile-chat", title="BOMTEMPO | Mobile AI", on_load=GlobalState.load_data
)

# RDO Pages
app.add_page(
    rdo_form, route="/rdo-form", title="BOMTEMPO | RDO Diário", on_load=GlobalState.load_data
)
app.add_page(
    rdo_historico,
    route="/rdo-historico",
    title="BOMTEMPO | Meus RDOs",
    on_load=[GlobalState.load_data, RDOHistoricoState.load_rdos],
)
app.add_page(
    rdo_dashboard,
    route="/rdo-dashboard",
    title="BOMTEMPO | RDO Analytics",
    on_load=[GlobalState.load_data, RDODashboardState.load_dashboard],
)

# Reembolso Pages
app.add_page(
    reembolso,
    route="/reembolso",
    title="BOMTEMPO | Reembolso Combustível",
    on_load=[GlobalState.load_data, ReembolsoState.load_my_reimbursements],
)
app.add_page(
    reembolso_dash,
    route="/reembolso-dash",
    title="BOMTEMPO | Reembolso Dashboard",
    on_load=[GlobalState.load_data, ReembolsoState.load_dashboard],
)

def relatorios():
    return default_layout(relatorios_page())


def editar_dados():
    # Only Admin sees the sidebar normally. data_edit role is configured to hide other items inside sidebar.
    from bomtempo.layouts.default import default_layout
    return default_layout(editar_dados_page())


def alertas():
    return default_layout(alertas_page())


def logs_auditoria():
    return default_layout(logs_auditoria_page())


def usuarios():
    return default_layout(usuarios_page())


app.add_page(
    relatorios,
    route="/relatorios",
    title="BOMTEMPO | Central de Relatórios",
    on_load=[GlobalState.load_data, RelatoriosState.load_page],
)

app.add_page(
    editar_dados,
    route="/admin/editar_dados",
    title="BOMTEMPO | Data Editor Dashboard",
    on_load=[GlobalState.load_data, EditState.load_projetos],
)

app.add_page(
    alertas,
    route="/alertas",
    title="BOMTEMPO | Alertas Proativos",
    on_load=[GlobalState.load_data, AlertasState.load_page],
)

app.add_page(
    logs_auditoria,
    route="/logs-auditoria",
    title="BOMTEMPO | Logs & Auditoria",
    on_load=[GlobalState.load_data, LogsState.load_page],
)

app.add_page(
    usuarios,
    route="/admin/usuarios",
    title="BOMTEMPO | Gerenciar Usuários",
    on_load=[GlobalState.load_data, UsuariosState.load_page],
)

from bomtempo.pages.voice_chat_page import voice_chat_page

app.add_page(voice_chat_page, route="/voice-chat", title="BOMTEMPO | Chat de Voz (Web Audio)")

from bomtempo.pages.debug_audio import debug_audio_page

app.add_page(debug_audio_page, route="/debug-audio", title="Debug Audio Lab")

from bomtempo.pages.test_audio import test_audio_page


def test_audio():
    return test_audio_page()


app.add_page(test_audio, route="/test-audio", title="Diagnóstico de Áudio")
