"""
Configurações globais do projeto BOMTEMPO (Reflex)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()


class Config:
    """Configurações centralizadas"""

    # Diretórios
    ROOT_DIR = Path(__file__).parent.parent.parent  # bomtempo-dashboard/
    ASSETS_DIR = ROOT_DIR / "assets"

    # FIX: Procurar em data/raw primeiro
    if (ROOT_DIR / "data" / "raw").exists():
        DATA_DIR = ROOT_DIR / "data" / "raw"
    elif (ROOT_DIR / "data").exists():
        DATA_DIR = ROOT_DIR / "data"
    else:
        DATA_DIR = ROOT_DIR

    # Arquivos de dados (Local)
    XLSX_MAP = {
        "contratos": DATA_DIR / "dContratos.xlsx",
        "projeto": DATA_DIR / "Projeto.xlsx",
        "obras": DATA_DIR / "Obras.xlsx",
        "financeiro": DATA_DIR / "Financeiro.xlsx",
        "om": DATA_DIR / "O&M.xlsx",
    }

    # Google Sheets URLs (Public - CSV Export) — login removido (migrado para Supabase)
    SHEET_URLS = {
        "contratos": "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0UNflAmzAFP-a9vkEmJaKIbw1OK3W5YX9we9hIk0B_lkwEK6DQE0Mw1m-381Qmg/pub?output=csv",
        "financeiro": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQihzHs7OCYWDH3fzSttNYtSOl4TA1Z5COfAyvrl9vbL9CPThhFwfruuIzPdXICww/pub?output=csv",
        "om": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSWKFafRZBwJL62bLd4GVmNPxEwX0GmW2B0wQgKL02bmVJfpD1w58Bsip_Jy8sGZQ/pub?output=csv",
        "obras": "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0g7dCm7eLbsRrnPnbsMwB7h2cQSivW36CJIKPinhjjrm9yQeQk5ZtdZ0FnWmK5g/pub?output=csv",
        "projeto": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQpREL_C8CymmOI585suScIBTsPuIA_INzjOZuo-iNIdlSvftYo31VkZnXz8JIUKw/pub?output=csv",
    }

    # ── RDO Configuration ────────────────────────────────────────────────────────
    # RDO dados 100% no Supabase — sem Google Sheets nem SQLite para RDO

    # Diretório para PDFs gerados — FORA da pasta do projeto para não
    # acionar o file-watcher do Reflex (que recompila o frontend)
    RDO_PDF_DIR = Path(os.environ.get("RDO_PDF_DIR", str(Path.home() / ".bomtempo_pdfs")))

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL = "https://nychzaapchxdlsffotcq.supabase.co"
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_hGsFo0P6OSkrFBPWbNLnCw_cn7ESLlx")

    # Gmail SMTP Configuration (via variáveis de ambiente)
    RDO_EMAIL_USER = os.getenv("RDO_EMAIL_USER", "rdos@bomtempo.com.br")
    RDO_EMAIL_PASSWORD = os.getenv("RDO_EMAIL_PASSWORD", "")
    RDO_SMTP_SERVER = "smtp.gmail.com"
    RDO_SMTP_PORT = 587

    # ── Fuel Reimbursement (FR) ────────────────────────────────────────────────
    FR_PDF_DIR = Path(os.environ.get("FR_PDF_DIR", str(Path.home() / ".bomtempo_pdfs")))
    FR_BUCKET_NF = "fuel_reimbursements_nf"
    FR_BUCKET_PDF = "fuel_reimbursements_pdfs"
    OPENAI_VISION_KEY = os.getenv("OPENAI_VISION_KEY", "")

    # Data sintética
    USE_SYNTHETIC_DATA = False
    SYNTHETIC_MULTIPLIER = 3
    SYNTHETIC_SEED = 42

    # Brand colors ref
    BRAND_COLORS = {
        "primary_green": "#0B5B3E",
        "dark_green": "#071D15",
        "light_green": "#0D7050",
        "gold": "#C98B2A",
        "light_gold": "#E0A63B",
        "gold_soft": "#F5D78E",
        "orange": "#E89845",
        "bg_void": "#030504",
        "bg_depth": "#081210",
        "bg_surface": "#0E1A17",
    }
