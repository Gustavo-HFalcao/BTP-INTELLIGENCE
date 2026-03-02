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
from bomtempo.pages.rdo_form import rdo_form_page
from bomtempo.pages.rdo_historico import RDOHistoricoState, rdo_historico_page
from bomtempo.pages.reembolso_dashboard import reembolso_dashboard_page
from bomtempo.pages.reembolso_form import reembolso_form_page
from bomtempo.state.reembolso_state import ReembolsoState


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
        radius="medium",
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
    on_load=GlobalState.load_data,
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

from bomtempo.pages.voice_chat_page import voice_chat_page

app.add_page(voice_chat_page, route="/voice-chat", title="BOMTEMPO | Chat de Voz (Web Audio)")

from bomtempo.pages.debug_audio import debug_audio_page

app.add_page(debug_audio_page, route="/debug-audio", title="Debug Audio Lab")

from bomtempo.pages.test_audio import test_audio_page


def test_audio():
    return test_audio_page()


app.add_page(test_audio, route="/test-audio", title="Diagnóstico de Áudio")
