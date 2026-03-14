"""
Carregamento e normalização de dados — Usando APENAS dados reais da planilha.
"""

import os
import pickle
import time
import unicodedata

import pandas as pd

from bomtempo.core.config import Config
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.supabase_client import sb_select

logger = get_logger(__name__)

import tempfile

# Cache absoluto completamente FORA do diretório do projeto 
# Isso garante 100% que o Reflex (watchfiles) não vai dar hot-reload ao deletar/salvar o cache
CACHE_FILE = os.path.join(tempfile.gettempdir(), "bomtempo_data_cache.pkl")
CACHE_TTL = 3600  # 1 hora


def _strip_accents(text: str) -> str:
    """Remove acentos para comparação segura de colunas."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _parse_brl(val) -> float:
    """Converte 'R$ 80.000,00' ou '4.661.063 kWh' para float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()

    # Remove tudo que não for número, ponto ou vírgula (ex: " R$", " kWh")
    import re

    s = re.sub(r"[^\d,.-]", "", s)

    if s in ("-", "", "—", "–"):
        return 0.0

    # BRL: "80.000,00" → "80000.00"
    # Note: we assume DD.MMM,CC format.
    # If there is a comma, it's the decimal separator.
    if "," in s:
        s = s.replace(".", "").replace(",", ".")

    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


class DataLoader:
    """Carrega e normaliza todas as planilhas"""

    def load_all(self) -> dict:
        """Carrega todos os dados (Cache -> Supabase), normaliza e retorna."""
        data = {}

        # 1. Tentar cache recente (< 1h)
        cached = self._try_load_cache(fresh_only=True)
        if cached:
            logger.info("✅ Dados carregados do Cache (< 1h)")
            return cached

        # 2. Carregar do Supabase
        logger.info("Carregando dados do Supabase...")
        tables = ["contratos", "projetos", "obras", "financeiro", "om"]
        sucesso = False
        
        for table in tables:
            try:
                # 'projeto' is named 'projetos' in DB
                key = "projeto" if table == "projetos" else table
                
                rows = sb_select(table)
                if rows:
                    data[key] = pd.DataFrame(rows)
                    logger.info(f"  {key}: {len(rows)} linhas (Supabase)")
                    sucesso = True
                else:
                    data[key] = pd.DataFrame()
                    logger.warning(f"  {key}: tabela vazia no Supabase")
            except Exception as e:
                logger.error(f"Erro ao carregar {table} do Supabase: {e}")
                data[key] = pd.DataFrame()

        # Fallbacks antigos foram removidos conforme instrução.

        # 3. Normalizar colunas
        data = self._normalize_all(data)

        # 4. Salvar cache (já normalizado)
        if sucesso:
            self._save_cache(data)

        logger.info("✅ Carga de dados concluída")
        return data

    # ── Helpers ───────────────────────────────────────────────────

    def _try_load_cache(self, fresh_only: bool = True):
        if not os.path.exists(CACHE_FILE):
            return None
        try:
            if fresh_only:
                mtime = os.path.getmtime(CACHE_FILE)
                if (time.time() - mtime) >= CACHE_TTL:
                    return None
            with open(CACHE_FILE, "rb") as f:
                data = pickle.load(f)
            if data and isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")
        return None

    def _save_cache(self, data: dict):
        try:
            with open(CACHE_FILE, "wb") as f:
                pickle.dump(data, f)
            logger.info("Cache atualizado (dados normalizados)")
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")

    # ── Normalização ──────────────────────────────────────────────

    def _normalize_all(self, data: dict) -> dict:
        """Normaliza colunas reais para snake_case usado no código."""

        # ── Contratos ────────────────────────────────────────────
        if "contratos" in data and not data["contratos"].empty:
            df = data["contratos"]
            rename = {}
            for col in df.columns:
                cl = _strip_accents(col).lower()
                if cl == "projeto":
                    rename[col] = "projeto"
                elif cl == "contrato":
                    rename[col] = "contrato"
                elif cl == "cliente":
                    rename[col] = "cliente"
                elif cl == "terceirizado":
                    rename[col] = "terceirizado"
                elif "localiza" in cl:
                    rename[col] = "localizacao"
                elif "valor" in cl and "contratado" in cl:
                    rename[col] = "valor_contratado"
                elif cl == "status":
                    rename[col] = "status"
            df = df.rename(columns=rename)

            if "valor_contratado" not in df.columns:
                df["valor_contratado"] = 0.0
            if "status" not in df.columns:
                df["status"] = "Em Execução"

            data["contratos"] = df

        # ── Projeto ──────────────────────────────────────────────
        if "projeto" in data and not data["projeto"].empty:
            df = data["projeto"]
            rename = {}
            for col in df.columns:
                cl = _strip_accents(col).lower()
                if cl == "id":
                    rename[col] = "id"
                elif cl == "fase" or cl == "fase do projeto" or col == "Fase":
                    rename[col] = "fase"
                elif cl == "atividade":
                    rename[col] = "atividade"
                elif cl == "critico":
                    rename[col] = "critico"
                elif cl == "inicio":
                    rename[col] = "inicio_previsto"
                elif cl == "termino":
                    rename[col] = "termino_previsto"
                elif "conclusao" in cl and "%" in cl:
                    rename[col] = "conclusao_pct"
                elif cl == "dependencia":
                    rename[col] = "dependencia"
                elif cl == "cliente":
                    rename[col] = "cliente"
                elif cl == "projeto":
                    rename[col] = "projeto"
                elif cl == "responsavel":
                    rename[col] = "responsavel"
                elif cl == "contrato":
                    rename[col] = "contrato"
                elif "fase" in cl and "macro" in cl:
                    rename[col] = "fase_macro"
            df = df.rename(columns=rename)
            for col in ["inicio_previsto", "termino_previsto"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            if "conclusao_pct" in df.columns:
                df["conclusao_pct"] = pd.to_numeric(df["conclusao_pct"], errors="coerce").fillna(0)
            data["projeto"] = df

        # ── Obras ────────────────────────────────────────────────
        if "obras" in data and not data["obras"].empty:
            df = data["obras"]
            rename = {}
            for col in df.columns:
                cl = _strip_accents(col).lower()
                if cl == "data":
                    rename[col] = "data"
                elif cl == "contrato":
                    rename[col] = "contrato"
                elif cl == "projeto":
                    rename[col] = "projeto"
                elif cl == "cliente":
                    rename[col] = "cliente"
                elif cl == "terceirizado":
                    rename[col] = "terceirizado"
                elif cl == "categoria":
                    rename[col] = "categoria"
                elif "previsto" in cl and "%" in cl:
                    rename[col] = "previsto_pct"
                elif "realizado" in cl and "%" in cl:
                    rename[col] = "realizado_pct"
                elif cl == "tipo":
                    rename[col] = "tipo"
                elif cl == "marco":
                    rename[col] = "marco"
                elif "localiza" in cl:
                    rename[col] = "localizacao"
                elif cl == "inicio":
                    rename[col] = "inicio"
                elif "termino" in cl:
                    rename[col] = "termino"
                elif "ordem" in cl:
                    rename[col] = "os"
                elif "potencia" in cl:
                    rename[col] = "potencia_kwp"
                elif "prazo" in cl:
                    rename[col] = "prazo_contratual"
                elif "comentario" in cl:
                    rename[col] = "comentario"
            df = df.rename(columns=rename)

            # Parse date columns (Supabase uses YYYY-MM-DD ISO)
            for date_col in ["data", "inicio", "termino"]:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

            # Parse potencia_kwp: extract numeric value from "100 kWp - 70 kW" format
            if "potencia_kwp" in df.columns:
                df["potencia_kwp"] = (
                    df["potencia_kwp"]
                    .astype(str)
                    .str.extract(r"(\d+\.?\d*)", expand=False)  # Extract first number
                    .astype(float, errors="ignore")
                )

            # Parse percentage columns
            for col in ["previsto_pct", "realizado_pct"]:
                if col in df.columns:
                    # Strip "%" before converting
                    df[col] = df[col].astype(str).str.replace("%", "", regex=False).str.strip()
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                    if df[col].max() <= 1.0 and df[col].max() > 0:
                        df[col] = df[col] * 100

            data["obras"] = df

        # ── Financeiro ───────────────────────────────────────────
        if "financeiro" in data and not data["financeiro"].empty:
            df = data["financeiro"]
            rename = {}
            for col in df.columns:
                cl = _strip_accents(col).lower()
                if cl == "data":
                    rename[col] = "data"
                elif cl == "contrato":
                    rename[col] = "contrato"
                elif cl == "projeto":
                    rename[col] = "projeto"
                elif cl == "cliente":
                    rename[col] = "cliente"
                elif cl == "terceirizado":
                    rename[col] = "terceirizado"
                elif cl == "cockpit":
                    rename[col] = "cockpit"
                elif cl == "marco":
                    rename[col] = "marco"
                elif cl == "categoria":
                    rename[col] = "categoria"
                elif cl == "multa":
                    rename[col] = "multa"
                elif cl in ("justificativas", "justificativa"):
                    rename[col] = "justificativa"
                elif "localiza" in cl:
                    rename[col] = "localizacao"
                elif "servico" in cl or "servic" in cl:
                    if "contratado" in cl:
                        rename[col] = "servico_contratado"
                    elif "realizado" in cl:
                        rename[col] = "servico_realizado"
                elif "material" in cl:
                    if "contratado" in cl:
                        rename[col] = "material_contratado"
                    elif "realizado" in cl:
                        rename[col] = "material_realizado"
                elif "inicio" in cl and "projeto" in cl:
                    rename[col] = "inicio_projeto"
                elif "termino" in cl and "projeto" in cl:
                    rename[col] = "termino_projeto"
            df = df.rename(columns=rename)

            # Parse BRL money columns
            money_cols = [
                "servico_contratado",
                "servico_realizado",
                "material_contratado",
                "material_realizado",
                "multa",
            ]
            for col in money_cols:
                if col in df.columns:
                    df[col] = df[col].apply(_parse_brl).fillna(0.0)

            data["financeiro"] = df

        # ── O&M ──────────────────────────────────────────────────
        if "om" in data and not data["om"].empty:
            df = data["om"]
            rename = {}
            for col in df.columns:
                cl = _strip_accents(col).lower()
                if cl == "data":
                    rename[col] = "data"
                elif cl == "contrato":
                    rename[col] = "contrato"
                elif cl == "projeto":
                    rename[col] = "projeto"
                elif cl == "cliente":
                    rename[col] = "cliente"
                elif cl == "terceirizado":
                    rename[col] = "terceirizado"
                elif "localiza" in cl:
                    rename[col] = "localizacao"
                elif "gera" in cl and "prevista" in cl:
                    rename[col] = "geracao_prevista_kwh"
                elif "energia" in cl and "injetada" in cl:
                    rename[col] = "energia_injetada_kwh"
                elif "compensado" in cl or ("kwh" in cl and "compens" in cl):
                    rename[col] = "compensado_kwh"
                elif "acumulado" in cl or ("kwh" in cl and "acumul" in cl):
                    rename[col] = "acumulado_kwh"
                elif "valor" in cl and "faturado" in cl:
                    rename[col] = "valor_faturado"
                elif cl.startswith("gest"):
                    rename[col] = "gestao"
                elif ("liquido" in cl) or ("fat" in cl and "liq" in cl):
                    rename[col] = "faturamento_liquido"

            df = df.rename(columns=rename)

            if "data" in df.columns:
                df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
                df["mes_ano"] = df["data"].dt.strftime("%m/%Y")

            # Parse numeric/money columns
            num_cols = [
                "geracao_prevista_kwh",
                "energia_injetada_kwh",
                "compensado_kwh",
                "acumulado_kwh",
                "valor_faturado",
                "gestao",
                "faturamento_liquido",
            ]
            for col in num_cols:
                if col in df.columns:
                    df[col] = df[col].apply(_parse_brl)

            data["om"] = df

        # Login agora vem do Supabase — não precisa normalizar a sheet

        # ── Cross-reference: valor_contratado from financeiro ────
        if "contratos" in data:
            con = data["contratos"]
            if "valor_contratado" not in con.columns:
                con["valor_contratado"] = 0.0

            if "financeiro" in data and not data["financeiro"].empty:
                fin = data["financeiro"]
                cols_needed = ["servico_contratado", "material_contratado"]
                valid_cols = [c for c in cols_needed if c in fin.columns]

                if valid_cols and "contrato" in fin.columns:
                    totals = fin.groupby("contrato")[valid_cols].sum().sum(axis=1).reset_index()
                    totals.columns = ["contrato", "valor_total"]
                    valor_map = dict(zip(totals["contrato"], totals["valor_total"]))
                    logger.info(f"Cross-ref financeiro→contratos: {len(valor_map)} contratos")
                    con["valor_contratado"] = con["contrato"].map(valor_map).fillna(0)

            data["contratos"] = con

        # ── Cross-reference: status from obras ───────────────────
        if "contratos" in data and "obras" in data and not data["obras"].empty:
            obras = data["obras"]
            con = data["contratos"]
            if "realizado_pct" in obras.columns and "contrato" in obras.columns:
                avg_real = obras.groupby("contrato")["realizado_pct"].mean().reset_index()
                status_map = {}
                for _, row in avg_real.iterrows():
                    if row["realizado_pct"] >= 100:
                        status_map[row["contrato"]] = "Concluído"
                    elif row["realizado_pct"] > 0:
                        status_map[row["contrato"]] = "Em Execução"
                    else:
                        status_map[row["contrato"]] = "Em Planejamento"
                con["status"] = con["contrato"].map(status_map).fillna("Em Planejamento")
                data["contratos"] = con

        # RDO sheets removidos — dados agora vêm do Supabase via rdo_service.py

        return data
