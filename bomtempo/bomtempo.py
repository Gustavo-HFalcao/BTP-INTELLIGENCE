# ruff: noqa: E402
import reflex as rx

# Install global error hooks BEFORE any app code — captures unhandled exceptions in production
from bomtempo.core.error_logger import install_global_handler
install_global_handler()

# Patch Reflex state event processing to log handler exceptions to app_errors.
# Reflex catches exceptions in _process_event internally (never reaches sys.excepthook).
# This patch runs BEFORE the Reflex app is created, so it wraps all event handlers.
try:
    import reflex.state as _rx_state
    import traceback as _tb

    _orig_process = _rx_state.State._process_event

    async def _patched_process_event(self, **kwargs):
        try:
            async for update in _orig_process(self, **kwargs):
                yield update
        except Exception as _exc:
            try:
                from bomtempo.core.error_logger import _write_async as _log
                _tb_str = "".join(_tb.format_exception(type(_exc), _exc, _exc.__traceback__))[:5000]
                fn = kwargs.get("handler") or kwargs.get("fn")
                _log(
                    severity="error",
                    error_type=type(_exc).__name__[:100],
                    module=getattr(fn, "__module__", "reflex.state")[:200],
                    function_name=getattr(fn, "__name__", "event_handler")[:100],
                    error_message=str(_exc)[:2000],
                    traceback=_tb_str,
                    username="",
                )
            except Exception:
                pass
            raise  # re-raise so Reflex shows the error normally in the UI

    _rx_state.State._process_event = _patched_process_event
except Exception:
    pass  # Never break startup due to patch failure

from bomtempo.core import styles as S
from bomtempo.layouts.default import default_layout
from bomtempo.state.global_state import GlobalState
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
from bomtempo.pages.rdo_view import rdo_view_page, RDOViewState
from bomtempo.state.rdo_state import RDOState
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
from bomtempo.pages.contract_features import contract_features_page
from bomtempo.state.feature_flags_state import FeatureFlagsState
from bomtempo.pages.app_mobile import app_mobile_page
from bomtempo.pages.observabilidade import observabilidade_page
from bomtempo.state.observability_state import ObservabilityState
from bomtempo.state.action_ai_state import ActionAIState

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


from bomtempo.components.action_ai_popup import ACTION_AI_JS

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
    # Favicon server-rendered — SVG com fundo escuro, sem branco-no-branco na aba do browser.
    # head_components é injetado no HTML pelo servidor antes de qualquer JS/hidratação,
    # então não depende de MutationObserver nem de timing de script.
    head_components=[
        rx.el.link(rel="icon", type="image/svg+xml", href="/favicon-badge.svg"),
        rx.el.link(rel="shortcut icon", href="/favicon-badge.svg"),
    ],
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
    rdo_form,
    route="/rdo-form",
    title="BOMTEMPO | RDO Diário",
    on_load=[GlobalState.load_data, RDOState.init_page, RDOState.check_for_draft, ActionAIState.apply_rdo_prefill],
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
app.add_page(
    rdo_view_page,
    route="/rdo-view/[token]",
    title="BOMTEMPO | Visualizar RDO",
    on_load=RDOViewState.load_rdo,
)

# Reembolso Pages
app.add_page(
    reembolso,
    route="/reembolso",
    title="BOMTEMPO | Reembolso Combustível",
    on_load=[GlobalState.load_data, ReembolsoState.load_my_reimbursements, ReembolsoState.load_form_features, ActionAIState.apply_reembolso_prefill],
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


def contract_features():
    return default_layout(contract_features_page())


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

app.add_page(
    contract_features,
    route="/admin/contract-features",
    title="BOMTEMPO | Feature Flags",
    on_load=[GlobalState.load_data, FeatureFlagsState.load_page],
)


def observabilidade():
    return default_layout(observabilidade_page())


app.add_page(
    observabilidade,
    route="/admin/observabilidade",
    title="BOMTEMPO | Observabilidade LLM",
    on_load=[GlobalState.load_data, ObservabilityState.load_page],
)


def app_mobile():
    return default_layout(app_mobile_page())


app.add_page(
    app_mobile,
    route="/app-mobile",
    title="BOMTEMPO | App Mobile",
    on_load=GlobalState.load_data,
)

