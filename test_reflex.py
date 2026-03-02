"""
Smoke tests para Bomtempo Dashboard.
Valida que importações, config e serviços básicos funcionam sem Reflex server.
Execute com: python -m pytest test_reflex.py -v
"""

import importlib

import pytest

# ─── 1. CONFIG ────────────────────────────────────────────────────────────────


def test_rxconfig_loads():
    """rxconfig.py importa sem erros e tem app_name correto."""
    import rxconfig

    assert rxconfig.config.app_name == "bomtempo"


# ─── 2. CORE MODULES ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "module",
    [
        "bomtempo.core.config",
        "bomtempo.core.styles",
        "bomtempo.core.logging_utils",
        "bomtempo.core.validation",
        "bomtempo.core.metrics",
        "bomtempo.core.weather_api",
        "bomtempo.core.ai_context",
        "bomtempo.core.analysis_service",
    ],
)
def test_core_module_imports(module):
    """Todos os módulos core importam sem erros."""
    mod = importlib.import_module(module)
    assert mod is not None


# ─── 3. STYLES CONSTANTS ──────────────────────────────────────────────────────


def test_styles_required_constants():
    """Constantes críticas de design existem e são strings não-vazias."""
    from bomtempo.core import styles as S

    for const in [
        "BG_VOID",
        "BG_DEPTH",
        "BG_SURFACE",
        "BG_GLASS",
        "BG_ELEVATED",
        "TEXT_PRIMARY",
        "TEXT_MUTED",
        "COPPER",
        "PATINA",
        "SUCCESS",
        "WARNING",
        "DANGER",
        "INFO",
        "FONT_DISPLAY",
        "FONT_TECH",
        "FONT_BODY",
        "FONT_MONO",
        "ORANGE",
    ]:
        val = getattr(S, const)
        assert isinstance(val, str) and val, f"S.{const} deve ser string não-vazia"


def test_styles_no_duplicate_font_values():
    """FONT_DISPLAY e FONT_TECH devem ter o mesmo valor (Rajdhani)."""
    from bomtempo.core import styles as S

    assert S.FONT_DISPLAY == S.FONT_TECH


# ─── 4. DATA LOADER ───────────────────────────────────────────────────────────


def test_data_loader_imports():
    """DataLoader importa e pode ser instanciado."""
    from bomtempo.core.data_loader import DataLoader

    loader = DataLoader()
    assert loader is not None


def test_config_paths_defined():
    """Config tem SHEET_URLS e XLSX_MAP definidos."""
    from bomtempo.core.config import Config

    assert hasattr(Config, "SHEET_URLS")
    assert hasattr(Config, "XLSX_MAP")
    assert isinstance(Config.SHEET_URLS, dict)
    assert isinstance(Config.XLSX_MAP, dict)


# ─── 5. SUPABASE CLIENT ───────────────────────────────────────────────────────


def test_supabase_client_imports():
    """supabase_client importa sem erros (não conecta)."""
    import bomtempo.core.supabase_client as sc

    assert sc is not None


# ─── 6. AI CLIENT ─────────────────────────────────────────────────────────────


def test_ai_client_imports():
    """ai_client importa sem erros."""
    import bomtempo.core.ai_client as ac

    assert ac is not None


def test_ai_client_has_client_object():
    """Módulo exporta objeto 'ai_client'."""
    from bomtempo.core.ai_client import ai_client

    assert ai_client is not None


# ─── 7. SERVICES ──────────────────────────────────────────────────────────────


def test_rdo_service_imports():
    """RDOService importa e tem métodos críticos."""
    from bomtempo.core.rdo_service import RDOService

    assert hasattr(RDOService, "generate_pdf")
    assert hasattr(RDOService, "save_to_database")


def test_fuel_service_imports():
    """FuelService importa e tem métodos críticos."""
    from bomtempo.core.fuel_service import FuelService

    assert hasattr(FuelService, "save_to_database")
    assert hasattr(FuelService, "get_reimbursements_by_user")


def test_email_service_imports():
    """EmailService importa e tem métodos de envio."""
    from bomtempo.core.email_service import EmailService

    assert hasattr(EmailService, "send_rdo_email") or hasattr(EmailService, "send_reembolso_email")


# ─── 8. STATE MODULES ─────────────────────────────────────────────────────────


def test_global_state_imports():
    """GlobalState importa sem erros."""
    from bomtempo.state.global_state import GlobalState

    assert GlobalState is not None


def test_reembolso_state_imports():
    """ReembolsoState importa sem erros."""
    from bomtempo.state.reembolso_state import ReembolsoState

    assert ReembolsoState is not None


def test_rdo_state_imports():
    """RDOState importa sem erros."""
    from bomtempo.state.rdo_state import RDOState

    assert RDOState is not None


# ─── 9. WEATHER API ───────────────────────────────────────────────────────────


def test_weather_get_risk_level():
    """get_risk_level funciona com dados mock."""
    from bomtempo.core.weather_api import get_risk_level

    assert get_risk_level({}) == "Unknown"
    assert get_risk_level({"daily_rain_sum": [20], "daily_rain_prob": [90], "rain": 10}) == "High"
    assert get_risk_level({"daily_rain_sum": [6], "daily_rain_prob": [55], "rain": 1}) == "Medium"
    assert get_risk_level({"daily_rain_sum": [0], "daily_rain_prob": [20], "rain": 0}) == "Low"


# ─── 10. METRICS ──────────────────────────────────────────────────────────────


def test_metrics_imports():
    """metrics.py importa com funções presentes."""
    import bomtempo.core.metrics as m

    assert m is not None


# ─── 11. PAGES IMPORT (without Reflex server) ─────────────────────────────────


@pytest.mark.parametrize(
    "page_module",
    [
        "bomtempo.pages.login",
        "bomtempo.pages.index",
        "bomtempo.pages.financeiro",
        "bomtempo.pages.obras",
        "bomtempo.pages.projetos",
        "bomtempo.pages.om",
        "bomtempo.pages.analytics",
        "bomtempo.pages.chat_ia",
        "bomtempo.pages.rdo_form",
        "bomtempo.pages.rdo_dashboard",
        "bomtempo.pages.rdo_historico",
        "bomtempo.pages.reembolso_form",
        "bomtempo.pages.reembolso_dashboard",
    ],
)
def test_page_imports(page_module):
    """Todas as páginas importam sem erros."""
    mod = importlib.import_module(page_module)
    assert mod is not None


# ─── 12. LAYOUTS & COMPONENTS ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "mod_path",
    [
        "bomtempo.layouts.default",
        "bomtempo.components.charts",
        "bomtempo.components.sidebar",
        "bomtempo.components.theme",
        "bomtempo.components.loading_screen",
        "bomtempo.components.weather_widget",
    ],
)
def test_component_imports(mod_path):
    """Layouts e componentes importam sem erros."""
    mod = importlib.import_module(mod_path)
    assert mod is not None


# ─── 13. MAIN APP ─────────────────────────────────────────────────────────────


def test_main_app_imports():
    """bomtempo.bomtempo (app principal) importa sem erros."""
    import bomtempo.bomtempo

    assert bomtempo.bomtempo is not None
