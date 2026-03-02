"""
Fuel Reimbursement Service — PDF, Supabase, IA Vision, Validação
Padrão idêntico ao rdo_service.py (benchmark)
"""

import base64
import html as _html_mod
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from bomtempo.core.ai_client import ai_client
from bomtempo.core.config import Config
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.pdf_utils import html_to_pdf
from bomtempo.core.supabase_client import (
    sb_delete,
    sb_insert,
    sb_select,
    sb_storage_upload,
    sb_update,
)

logger = get_logger(__name__)

# Table name
_TABLE = "fuel_reimbursements"


def _to_float(val, default: float = 0.0) -> float:
    try:
        return float(str(val).strip().replace(",", "."))
    except (ValueError, TypeError):
        return default


def _user_uuid(username: str) -> str:
    """Gera UUID determinístico a partir do username (consistente entre sessões)."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bomtempo-{username.lower()}"))


class FuelService:
    """Serviço centralizado para o módulo de Reembolso de Combustível."""

    # ── IA Vision ─────────────────────────────────────────────────────────────

    @staticmethod
    def analyze_receipt_image(image_b64: str, mime: str = "image/jpeg") -> dict:
        """
        Chama gpt-4o Vision para extrair dados da nota fiscal.
        Retorna dict com campos extraídos ou {} em caso de erro.
        """
        return ai_client.analyze_receipt_image(image_b64, mime)

    # ── Validação ─────────────────────────────────────────────────────────────

    @staticmethod
    def validate_data(user_data: dict, ai_data: dict) -> dict:
        """
        Compara dados digitados pelo usuário com os extraídos pela IA.
        Tolerância ±R$0,50 no total. Verifica consistência litros×preço≈total.

        Returns:
            {"valid": bool, "errors": [...], "warnings": [...], "ai_verified": bool}
        """
        errors = []
        warnings = []
        ai_verified = False

        if not ai_data:
            warnings.append("IA não conseguiu extrair dados da imagem. Verifique manualmente.")
            return {"valid": True, "errors": errors, "warnings": warnings, "ai_verified": False}

        ai_total = _to_float(ai_data.get("total"))
        user_total = _to_float(user_data.get("valor_total"))

        # Validar valor total vs NF
        if ai_total > 0 and user_total > 0:
            diff = abs(ai_total - user_total)
            if diff > 0.50:
                errors.append(
                    f"Valor total diverge: você digitou R${user_total:.2f}, "
                    f"a nota fiscal indica R${ai_total:.2f} (diferença: R${diff:.2f})"
                )
            else:
                ai_verified = True

        # Consistência interna: litros × preço ≈ total
        ai_litros = _to_float(ai_data.get("liters"))
        ai_preco = _to_float(ai_data.get("price_per_liter"))
        if ai_litros > 0 and ai_preco > 0:
            expected = round(ai_litros * ai_preco, 2)
            if abs(expected - ai_total) > 1.00:
                warnings.append(
                    f"Inconsistência interna na NF: {ai_litros:.3f}L × R${ai_preco:.3f} "
                    f"= R${expected:.2f}, mas total informado é R${ai_total:.2f}"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "ai_verified": ai_verified and len(errors) == 0,
        }

    # ── Métricas ──────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_metrics(data: dict) -> dict:
        """Calcula km_per_liter, cost_per_km e km_driven."""
        km_start = _to_float(data.get("km_inicial"))
        km_end = _to_float(data.get("km_final"))
        litros = _to_float(data.get("litros"))
        total = _to_float(data.get("valor_total"))

        km_driven = max(0.0, km_end - km_start)
        km_per_liter = round(km_driven / litros, 2) if litros > 0 else 0.0
        cost_per_km = round(total / km_driven, 4) if km_driven > 0 else 0.0

        return {
            "km_driven": km_driven,
            "km_per_liter": km_per_liter,
            "cost_per_km": cost_per_km,
        }

    # ── Desvios (para anomalia) ────────────────────────────────────────────────

    @staticmethod
    def calculate_deviations(user_uuid: str, km_per_liter: float) -> dict:
        """
        Calcula desvio vs média do próprio usuário e vs frota.
        Retorna {"deviation_from_user_avg": float|None, "deviation_from_fleet_avg": float|None}
        """
        try:
            all_records = sb_select(_TABLE, limit=500) or []
            user_records = [r for r in all_records if r.get("user_id") == user_uuid]

            def _avg(records: list) -> Optional[float]:
                vals = [_to_float(r.get("km_per_liter")) for r in records if r.get("km_per_liter")]
                vals = [v for v in vals if v > 0]
                return round(sum(vals) / len(vals), 2) if vals else None

            user_avg = _avg(user_records)
            fleet_avg = _avg(all_records)

            dev_user = round((km_per_liter - user_avg) / user_avg * 100, 1) if user_avg else None
            dev_fleet = (
                round((km_per_liter - fleet_avg) / fleet_avg * 100, 1) if fleet_avg else None
            )

            return {"deviation_from_user_avg": dev_user, "deviation_from_fleet_avg": dev_fleet}
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular desvios: {e}")
            return {"deviation_from_user_avg": None, "deviation_from_fleet_avg": None}

    # ── PDF ───────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_fuel_html(data: dict, id_fr: str) -> str:
        """Builds the HTML document used for PDF rendering."""

        def e(s) -> str:
            return _html_mod.escape(str(s) if s is not None else "—")

        submitted_by = e(data.get("submitted_by") or "—")
        combustivel = e(data.get("combustivel") or "—")
        litros = _to_float(data.get("litros"))
        valor_litro = _to_float(data.get("valor_litro"))
        valor_total = _to_float(data.get("valor_total"))
        km_inicial = _to_float(data.get("km_inicial"))
        km_final = _to_float(data.get("km_final"))
        km_driven = _to_float(data.get("km_driven"))
        km_per_liter = _to_float(data.get("km_per_liter"))
        cost_per_km = _to_float(data.get("cost_per_km"))
        rota = e(data.get("rota") or "—")
        finalidade = e(data.get("finalidade") or "—")
        cidade = e(data.get("cidade") or "—")
        estado = e(data.get("estado") or "—")
        data_abast = e(data.get("data_abastecimento") or datetime.now().strftime("%Y-%m-%d"))
        ai_insight = (data.get("ai_insight_text") or "").strip()
        ai_verified = bool(data.get("ai_verified", False))
        id_label = e(id_fr) if id_fr else ""
        emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")

        badge_color = "#27AE60" if ai_verified else "#888888"
        badge_text = "NF VERIFICADA ✓ IA" if ai_verified else "NF NÃO VERIFICADA"

        ai_section = ""
        if ai_insight:
            ai_section = f"""
  <div class="section-hdr" style="border-left-color:{badge_color};">
    <div class="sec-badge" style="background:{badge_color};">IA</div>
    <div class="sec-title">Análise da Nota Fiscal (IA)</div>
  </div>
  <div class="obs-box">{e(ai_insight)}</div>"""

        css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'IBM Plex Sans', sans-serif; background: #fff; color: #1a1a1a; font-size: 9pt; line-height: 1.4; }

.header { background: #0B1A15; color: #fff; padding: 14px 20px 12px; border-top: 3px solid #C98B2A; border-bottom: 2px solid #2A9D8F; display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.hdr-left { flex: 1; }
.brand { display: flex; align-items: baseline; gap: 8px; }
.brand-main { font-size: 21pt; font-weight: 700; color: #fff; letter-spacing: -0.5px; }
.brand-accent { font-size: 21pt; font-weight: 700; color: #C98B2A; letter-spacing: -0.5px; }
.hdr-sub { font-size: 8.5pt; color: #CCC; margin-top: 3px; }
.ai-badge { display: inline-block; color: #fff; font-size: 6.5pt; font-weight: 700; padding: 2px 10px; border-radius: 3px; letter-spacing: 0.5px; margin-top: 6px; }
.hdr-box { background: #162820; border-radius: 8px; padding: 10px 20px; text-align: center; min-width: 168px; }
.hdr-box-lbl { font-size: 6pt; color: #C98B2A; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
.hdr-box-val { font-size: 15pt; font-weight: 700; color: #fff; margin-top: 3px; font-family: 'IBM Plex Mono', monospace; }
.hdr-box-sub { font-size: 7.5pt; color: #AAA; margin-top: 2px; }
.hdr-box-date { font-size: 7pt; color: #2A9D8F; margin-top: 2px; }

.content { padding: 10px 20px 0; }

.info-grid { display: grid; grid-template-columns: 92px 1fr 92px 1fr; border: 0.5px solid #D4C8A8; margin-bottom: 8px; }
.info-label { background: #ECEAE0; font-weight: 600; font-size: 7pt; text-transform: uppercase; letter-spacing: 0.3px; padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; border-right: 0.5px solid #D4C8A8; display: flex; align-items: center; }
.info-value { background: #F8F7F2; font-size: 8pt; padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; border-right: 0.5px solid #D4C8A8; display: flex; align-items: center; }
.span-3 { grid-column: span 3; }

.kpi-bar { background: #162820; display: flex; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
.kpi-item { flex: 1; text-align: center; padding: 10px 6px; border-right: 0.5px solid #334040; }
.kpi-item:last-child { border-right: none; }
.kpi-val { font-size: 11pt; font-weight: 700; color: #C98B2A; display: block; font-family: 'IBM Plex Mono', monospace; }
.kpi-lbl { font-size: 6pt; color: #AAA; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; display: block; }

.section-hdr { background: #0B1A15; color: #fff; padding: 7px 12px; display: flex; align-items: center; gap: 10px; margin-top: 8px; border-left: 3px solid #C98B2A; }
.sec-badge { background: #C98B2A; color: #fff; font-size: 7pt; font-weight: 700; width: 18px; height: 18px; border-radius: 3px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sec-title { font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; }

.hodo-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; border: 0.5px solid #D4C8A8; }
.hodo-lbl { background: #2A9D8F; color: #fff; font-weight: 600; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.3px; padding: 7px 8px; border-right: 0.5px solid rgba(255,255,255,0.2); text-align: center; }
.hodo-val { background: #F8F7F2; font-size: 14pt; font-weight: 700; padding: 8px; border-right: 0.5px solid #D4C8A8; text-align: center; font-family: 'IBM Plex Mono', monospace; color: #0B1A15; }
.hodo-lbl:last-child, .hodo-val:last-child { border-right: none; }

.obs-box { background: #F8F7F2; border: 0.5px solid #D4C8A8; padding: 10px 12px; font-size: 8.5pt; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }

.signatures { display: flex; gap: 16px; margin-top: 12px; }
.sig-box { flex: 1; border: 0.5px solid #D4C8A8; background: #F8F7F2; padding: 8px 10px; min-height: 52px; }
.sig-lbl { font-weight: 700; font-size: 6.5pt; text-transform: uppercase; color: #0B1A15; }
.sig-sub { font-size: 6.5pt; color: #888; margin-top: 20px; border-top: 0.5px solid #D4C8A8; padding-top: 4px; }

.footer { background: #0B1A15; color: #fff; padding: 6px 20px; display: flex; justify-content: space-between; align-items: center; margin-top: 12px; border-top: 1px solid #C98B2A; }
.footer-l { font-weight: 700; font-size: 7pt; }
.footer-c { font-size: 6.5pt; color: #AAA; }
.footer-r { font-size: 7pt; color: #C98B2A; font-weight: 700; }
"""

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<div class="header">
  <div class="hdr-left">
    <div class="brand"><span class="brand-main">BOMTEMPO</span><span class="brand-accent">ENGENHARIA</span></div>
    <div class="hdr-sub">Comprovante de Reembolso de Combustível</div>
    <div class="ai-badge" style="background:{badge_color};">{badge_text}</div>
  </div>
  <div class="hdr-box">
    <div class="hdr-box-lbl">Total Reembolso</div>
    <div class="hdr-box-val">R$ {valor_total:.2f}</div>
    <div class="hdr-box-sub">{combustivel}</div>
    <div class="hdr-box-date">{data_abast}</div>
  </div>
</div>

<div class="content">
  <div class="info-grid">
    <div class="info-label">Solicitante</div><div class="info-value">{submitted_by}</div>
    <div class="info-label">Finalidade</div><div class="info-value">{finalidade}</div>
    <div class="info-label">Combustível</div><div class="info-value">{combustivel}</div>
    <div class="info-label">Data</div><div class="info-value">{data_abast}</div>
    <div class="info-label">Cidade</div><div class="info-value">{cidade}</div>
    <div class="info-label">Estado</div><div class="info-value">{estado}</div>
    <div class="info-label">Rota</div><div class="info-value span-3">{rota}</div>
  </div>

  <div class="kpi-bar">
    <div class="kpi-item"><span class="kpi-val">{litros:.2f} L</span><span class="kpi-lbl">Litros</span></div>
    <div class="kpi-item"><span class="kpi-val">R$ {valor_litro:.3f}</span><span class="kpi-lbl">Preço / Litro</span></div>
    <div class="kpi-item"><span class="kpi-val">{km_driven:.0f} km</span><span class="kpi-lbl">KM Rodados</span></div>
    <div class="kpi-item"><span class="kpi-val">{km_per_liter:.2f} km/L</span><span class="kpi-lbl">Eficiência</span></div>
    <div class="kpi-item"><span class="kpi-val">R$ {cost_per_km:.3f}</span><span class="kpi-lbl">Custo / KM</span></div>
  </div>

  <div class="section-hdr"><div class="sec-badge">KM</div><div class="sec-title">Hodômetro</div></div>
  <div class="hodo-grid">
    <div class="hodo-lbl">KM Inicial</div><div class="hodo-lbl">KM Final</div><div class="hodo-lbl">KM Rodados</div>
    <div class="hodo-val">{km_inicial:,.0f}</div><div class="hodo-val">{km_final:,.0f}</div><div class="hodo-val">{km_driven:,.0f}</div>
  </div>
{ai_section}
  <div class="signatures">
    <div class="sig-box">
      <div class="sig-lbl">Solicitante</div>
      <div class="sig-sub">{submitted_by}</div>
    </div>
    <div class="sig-box">
      <div class="sig-lbl">Aprovado por / Gestor</div>
      <div class="sig-sub">Data: {data_abast}</div>
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-l">BOMTEMPO INTELLIGENCE</div>
  <div class="footer-c">Reembolso Combustível{f" · {id_label}" if id_label else ""} · {submitted_by} · {data_abast} · Emitido em {emissao}</div>
  <div class="footer-r">Comprovante de Reembolso</div>
</div>
</body>
</html>"""

    @staticmethod
    def generate_pdf(data: dict, id_fr: str = "") -> tuple:
        """
        Gera PDF do Reembolso de Combustível via HTML → Playwright (Edge).

        Returns: (pdf_path: str, pdf_url: str)
        """
        try:
            Config.FR_PDF_DIR.mkdir(parents=True, exist_ok=True)

            data_prefix = (
                data.get("data_abastecimento", datetime.now().strftime("%Y-%m-%d"))
                .replace("-", "")
            )
            filename = (
                f"Reembolso_{data_prefix}_{id_fr}.pdf"
                if id_fr
                else f"Reembolso_PREVIEW_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            pdf_path = Config.FR_PDF_DIR / filename

            html = FuelService._build_fuel_html(data, id_fr)
            html_to_pdf(html, pdf_path)

            logger.info(f"✅ FR PDF gerado: {pdf_path.name}")
            return str(pdf_path), ""

        except Exception as e:
            logger.error(f"❌ Erro ao gerar PDF FR: {e}")
            return "", ""

    # ── Banco de dados ─────────────────────────────────────────────────────────

    @staticmethod
    def save_to_database(data: dict, submitted_by: str = "") -> Optional[str]:
        """
        Salva reembolso no Supabase (fuel_reimbursements).
        Retorna id_fr (string) ou None se falhar.

        Mapeamento de campos:
        - submitted_by → user_id (UUID determinístico via uuid5)
        - combustivel   → fuel_type
        - litros        → liters
        - valor_litro   → pricer_per_liter  (TYPO na coluna — mantido)
        - valor_total   → total_value
        - data_abastecimento → created_at
        - cidade        → city
        - estado        → state
        - km_inicial    → km_start
        - km_final      → km_end
        - km_driven     → km_driven
        - rota          → route_description
        - finalidade    → purpose
        """
        try:
            metrics = FuelService.calculate_metrics(data)
            user_uuid = _user_uuid(submitted_by or "anonimo")
            deviations = FuelService.calculate_deviations(user_uuid, metrics["km_per_liter"])

            now = datetime.now().isoformat()

            record = {
                "user_id": user_uuid,
                "created_at": data.get("data_abastecimento") or now,
                "status": now,  # submitted_at
                "fuel_type": data.get("combustivel", ""),
                "liters": _to_float(data.get("litros")) or None,
                "pricer_per_liter": _to_float(data.get("valor_litro")) or None,
                "total_value": _to_float(data.get("valor_total")) or None,
                "km_start": _to_float(data.get("km_inicial")) or None,
                "km_end": _to_float(data.get("km_final")) or None,
                "km_driven": metrics["km_driven"] or None,
                "route_description": data.get("rota", ""),
                "purpose": data.get("finalidade", ""),
                "city": data.get("cidade", ""),
                "state": data.get("estado", ""),
                "km_per_liter": metrics["km_per_liter"] or None,
                "cost_per_km": metrics["cost_per_km"] or None,
                "ai_verified": bool(data.get("ai_verified", False)),
                "ai_confidence_score": _to_float(data.get("ai_confidence_score")) or None,
                "ai_extracted_value": _to_float(data.get("ai_extracted_value")) or None,
                "ai_insight_text": data.get("ai_insight_text", "") or None,
                "deviation_from_user_avg": deviations.get("deviation_from_user_avg"),
                "deviation_from_fleet_avg": deviations.get("deviation_from_fleet_avg"),
                # receipt_image_url e pdf_report_url atualizados via UPDATE após upload
            }

            result = sb_insert(_TABLE, record)
            if result is None:
                logger.error("❌ Falha ao inserir fuel_reimbursements no Supabase")
                return None

            id_fr = str(result.get("id", ""))
            logger.info(f"✅ FR salvo no Supabase: id={id_fr}")
            return id_fr

        except Exception as e:
            logger.error(f"❌ Erro ao salvar FR: {e}")
            return None

    @staticmethod
    def upload_image_to_storage(image_b64: str, id_fr: str, mime: str = "image/jpeg") -> str:
        """
        Faz upload da imagem da NF para o Supabase Storage.
        Aceita base64 string (sem o prefixo data:...).
        Retorna URL pública ou "".
        """
        try:
            ext = mime.split("/")[-1].replace("jpeg", "jpg")
            data_prefix = datetime.now().strftime("%Y%m%d")
            storage_path = f"Reembolso_{data_prefix}_{id_fr}_nota.{ext}"
            image_bytes = base64.b64decode(image_b64)
            url = sb_storage_upload(Config.FR_BUCKET_NF, storage_path, image_bytes, mime)
            if url:
                sb_update(_TABLE, {"id": id_fr}, {"receipt_image_url": url})
                logger.info(f"✅ FR image uploaded: {url}")
            return url or ""
        except Exception as e:
            logger.error(f"❌ Erro ao fazer upload da imagem FR: {e}")
            return ""

    @staticmethod
    def upload_pdf_to_storage(pdf_path: str, id_fr: str) -> str:
        """
        Faz upload do PDF para o Supabase Storage.
        Retorna URL pública permanente ou "".
        """
        try:
            with open(pdf_path, "rb") as f:
                file_bytes = f.read()
            data_prefix = datetime.now().strftime("%Y%m%d")
            storage_path = f"Reembolso_{data_prefix}_{id_fr}.pdf"
            url = sb_storage_upload(
                Config.FR_BUCKET_PDF, storage_path, file_bytes, "application/pdf"
            )
            if url:
                sb_update(_TABLE, {"id": id_fr}, {"pdf_report_url": url})
                logger.info(f"✅ FR PDF uploaded: {url}")
            return url or ""
        except Exception as e:
            logger.error(f"❌ Erro ao fazer upload do PDF FR: {e}")
            return ""

    # ── Queries ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_all_reimbursements(limit: int = 200) -> List[Dict[str, Any]]:
        """Busca todos os reembolsos (admin)."""
        return sb_select(_TABLE, order="id.desc", limit=limit) or []

    @staticmethod
    def get_reimbursements_by_user(username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Busca reembolsos de um usuário específico."""
        user_uuid = _user_uuid(username)
        return sb_select(_TABLE, filters={"user_id": user_uuid}, order="id.desc", limit=limit) or []

    # ── Email de notificação ───────────────────────────────────────────────────

    @staticmethod
    def get_notification_emails() -> List[str]:
        """Retorna lista de emails (strings) para notificação de reembolso."""
        try:
            records = sb_select("email_sender", filters={"module": "reembolso"}) or []
            return [str(r.get("email", "")).strip() for r in records if r.get("email")]
        except Exception as e:
            logger.warning(f"⚠️ get_notification_emails: {e}")
            return []

    @staticmethod
    def get_email_records() -> List[Dict[str, Any]]:
        """Retorna registros completos de email para display no dashboard."""
        try:
            return (
                sb_select(
                    "email_sender", filters={"module": "reembolso"}, order="updated_date.desc"
                )
                or []
            )
        except Exception as e:
            logger.warning(f"⚠️ get_email_records: {e}")
            return []

    @staticmethod
    def add_notification_email(contract: str, email: str, created_by: str = "admin") -> bool:
        """Adiciona email de notificação para um contrato."""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = {
                "contract": contract,
                "email": email,
                "module": "reembolso",
                "created_by": created_by,
                "updated_date": now,
            }
            result = sb_insert("email_sender", record)
            return result is not None
        except Exception as e:
            logger.error(f"❌ add_notification_email: {e}")
            return False

    @staticmethod
    def delete_notification_email(contract: str, email: str) -> bool:
        """Remove email de notificação pelo par (contract, email)."""
        try:
            return sb_delete("email_sender", {"contract": contract, "email": email})
        except Exception as e:
            logger.error(f"❌ delete_notification_email: {e}")
            return False
