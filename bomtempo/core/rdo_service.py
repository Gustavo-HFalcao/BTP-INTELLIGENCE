"""
RDO Service - Geração PDF, Supabase, Análise IA
"""

import html as _html_mod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bomtempo.core.ai_client import ai_client
from bomtempo.core.config import Config
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.pdf_utils import html_to_pdf
from bomtempo.core.supabase_client import sb_insert, sb_select, sb_storage_upload, sb_update

logger = get_logger(__name__)


class RDOService:
    """Serviço centralizado para operações RDO"""

    @staticmethod
    def get_pdf_url(pdf_path: str) -> str:
        """Converte path absoluto do PDF para URL relativa servida pelo Reflex"""
        try:
            p = Path(pdf_path)
            parts = p.parts
            if "pdfs" in parts:
                idx = parts.index("pdfs")
                return "/" + "/".join(parts[idx:])
            return f"/pdfs/{p.name}"
        except Exception:
            return ""

    @staticmethod
    def init_database():
        """No-op: banco migrado para Supabase (tabelas gerenciadas pelo painel)."""
        logger.info("✅ Supabase — tabelas RDO gerenciadas externamente.")
        return True

    @staticmethod
    def _build_rdo_html(rdo_data: Dict[str, Any], is_preview: bool, id_rdo: str) -> str:
        """Builds the HTML document used for PDF rendering."""

        def e(s) -> str:
            return _html_mod.escape(str(s) if s is not None else "—")

        contrato = e(rdo_data.get("contrato") or "SEM-CONTRATO")
        data_rdo = e(rdo_data.get("data") or datetime.now().strftime("%Y-%m-%d"))
        projeto = e(rdo_data.get("projeto") or "—")
        cliente = e(rdo_data.get("cliente") or "—")
        localizacao = e(rdo_data.get("localizacao") or "—")
        clima = e(rdo_data.get("clima") or "—")
        turno = e(rdo_data.get("turno") or "—")
        h_ini = e(rdo_data.get("hora_inicio") or "—")
        h_fim = e(rdo_data.get("hora_termino") or "—")
        houve_intr = bool(rdo_data.get("houve_interrupcao"))
        interrupcao = "SIM" if houve_intr else "NÃO"
        motivo = e((rdo_data.get("motivo_interrupcao") or "—")[:80])
        obs_geral = e((rdo_data.get("observacoes") or "").strip())
        emissao = datetime.now().strftime("%d/%m/%Y às %H:%M")
        id_label = e(id_rdo) if id_rdo else ""

        mao_obra = rdo_data.get("mao_obra", [])
        equipamentos = rdo_data.get("equipamentos", [])
        atividades = rdo_data.get("atividades", [])
        materiais = rdo_data.get("materiais", [])

        # Conditional HTML blocks
        watermark = '<div class="watermark">RASCUNHO</div>' if is_preview else ""
        preview_badge = '<div class="preview-badge">RASCUNHO</div>' if is_preview else ""
        intr_lbl = 'class="info-label danger"' if houve_intr else 'class="info-label"'
        intr_val = 'class="info-value danger-bg"' if houve_intr else 'class="info-value"'
        mot_lbl = 'class="info-label danger"' if houve_intr else 'class="info-label"'
        mot_val = 'class="info-value danger-bg"' if houve_intr else 'class="info-value"'

        # ── Table row builders ──────────────────────────────────────────────────
        def mo_rows() -> str:
            if not mao_obra:
                return '<tr><td colspan="3" class="empty-row">Nenhum profissional registrado neste RDO.</td></tr>'
            rows = [
                f"<tr><td>{e(r.get('funcao'))}</td>"
                f'<td class="center">{e(str(r.get("quantidade") or "—"))}</td>'
                f"<td>{e(r.get('obs') or '—')}</td></tr>"
                for r in mao_obra[:25]
            ]
            rows.append(
                f'<tr class="total-row"><td colspan="3">TOTAL: {len(mao_obra)} profissional(is)</td></tr>'
            )
            return "\n".join(rows)

        def eq_rows() -> str:
            if not equipamentos:
                return '<tr><td colspan="2" class="empty-row">Nenhum equipamento registrado neste RDO.</td></tr>'
            return "\n".join(
                f"<tr><td>{e(r.get('descricao'))}</td>"
                f'<td class="center">{e(str(r.get("quantidade") or "—"))}</td></tr>'
                for r in equipamentos[:20]
            )

        def atv_rows() -> str:
            if not atividades:
                return '<tr><td colspan="2" class="empty-row">Nenhuma atividade registrada neste RDO.</td></tr>'
            rows = []
            for r in atividades[:25]:
                pct = str(r.get("percentual") or "—")
                rows.append(
                    f"<tr><td>{e(r.get('atividade'))}</td>"
                    f'<td class="center">{e(pct + "%" if pct != "—" else "—")}</td></tr>'
                )
            return "\n".join(rows)

        mat_section = ""
        if materiais:
            mat_rows = "\n".join(
                f"<tr><td>{e(r.get('descricao'))}</td>"
                f'<td class="center">{e(str(r.get("quantidade") or "—"))}</td>'
                f'<td class="center">{e(r.get("unidade") or "—")}</td></tr>'
                for r in materiais[:20]
            )
            mat_section = f"""
  <div class="section-hdr"><div class="sec-badge">4</div><div class="sec-title">Materiais Utilizados</div></div>
  <table class="tbl-gold">
    <thead><tr><th>Material / Descrição</th><th class="center w60">Qtd.</th><th class="center w70">Unidade</th></tr></thead>
    <tbody>{mat_rows}</tbody>
  </table>"""

        sec_obs = "5" if materiais else "4"
        obs_block = (
            f'<div class="obs-box">{obs_geral}</div>'
            if obs_geral
            else '<p class="empty-row" style="padding:10px 12px;">Sem observações registradas para este dia.</p>'
        )

        css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'IBM Plex Sans', sans-serif; background: #fff; color: #1a1a1a; font-size: 9pt; line-height: 1.4; }

.header { background: #0B1A15; color: #fff; padding: 14px 20px 12px; border-top: 3px solid #C98B2A; border-bottom: 2px solid #2A9D8F; display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.hdr-left { flex: 1; }
.brand { display: flex; align-items: baseline; gap: 8px; }
.brand-main { font-size: 21pt; font-weight: 700; color: #fff; letter-spacing: -0.5px; }
.brand-accent { font-size: 21pt; font-weight: 700; color: #C98B2A; letter-spacing: -0.5px; }
.hdr-sub { font-size: 8.5pt; color: #CCC; margin-top: 3px; }
.preview-badge { display: inline-block; background: #C0392B; color: #fff; font-size: 6.5pt; font-weight: 700; padding: 2px 8px; border-radius: 3px; letter-spacing: 1px; margin-top: 6px; }
.hdr-box { background: #162820; border-radius: 8px; padding: 10px 20px; text-align: center; min-width: 160px; }
.hdr-box-lbl { font-size: 6pt; color: #C98B2A; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; }
.hdr-box-val { font-size: 15pt; font-weight: 700; color: #fff; margin-top: 3px; font-family: 'IBM Plex Mono', monospace; }
.hdr-box-date { font-size: 7.5pt; color: #AAA; margin-top: 2px; }
.hdr-box-clima { font-size: 7pt; color: #2A9D8F; margin-top: 2px; }

.content { padding: 10px 20px 0; }

.info-grid { display: grid; grid-template-columns: 92px 1fr 92px 1fr; border: 0.5px solid #D4C8A8; margin-bottom: 8px; }
.info-label { background: #ECEAE0; font-weight: 600; font-size: 7pt; text-transform: uppercase; letter-spacing: 0.3px; padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; border-right: 0.5px solid #D4C8A8; display: flex; align-items: center; }
.info-value { background: #F8F7F2; font-size: 8pt; padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; border-right: 0.5px solid #D4C8A8; display: flex; align-items: center; }
.info-label.danger { color: #C0392B; }
.info-value.danger-bg { background: #FAE5E5; }

.kpi-bar { background: #162820; display: flex; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
.kpi-item { flex: 1; text-align: center; padding: 10px 8px; border-right: 0.5px solid #334040; }
.kpi-item:last-child { border-right: none; }
.kpi-val { font-size: 14pt; font-weight: 700; color: #C98B2A; display: block; font-family: 'IBM Plex Mono', monospace; }
.kpi-lbl { font-size: 6pt; color: #AAA; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; display: block; }

.section-hdr { background: #0B1A15; color: #fff; padding: 7px 12px; display: flex; align-items: center; gap: 10px; margin-top: 8px; border-left: 3px solid #C98B2A; page-break-inside: avoid; }
.sec-badge { background: #C98B2A; color: #fff; font-size: 7pt; font-weight: 700; width: 18px; height: 18px; border-radius: 3px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sec-title { font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; }

table { width: 100%; border-collapse: collapse; font-size: 8pt; page-break-inside: auto; }
thead { display: table-header-group; }
thead th { font-size: 7.5pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; padding: 7px 8px; color: #fff; text-align: left; }
tbody tr:nth-child(odd) td { background: #fff; }
tbody tr:nth-child(even) td { background: #F2F0E8; }
tbody tr td { padding: 6px 8px; border-bottom: 0.3px solid #D4C8A8; vertical-align: middle; }
.center { text-align: center; }
.w55 { width: 55px; } .w60 { width: 60px; } .w70 { width: 70px; }
.total-row td { background: #EAE4D0 !important; font-weight: 600; font-size: 7.5pt; border-top: 1px solid #C98B2A; }
.empty-row { background: #ECEAE0 !important; color: #888; font-style: italic; text-align: center; padding: 10px 8px; }
.tbl-patina thead { background: #1d7066; }
.tbl-copper thead { background: #9B6820; }
.tbl-green thead { background: #1d6e63; }
.tbl-gold thead { background: #6B5A1E; }

.obs-box { background: #F8F7F2; border: 0.5px solid #D4C8A8; padding: 10px 12px; font-size: 8.5pt; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }

.signatures { display: flex; gap: 16px; margin-top: 12px; }
.sig-box { flex: 1; border: 0.5px solid #D4C8A8; background: #F8F7F2; padding: 8px 10px; min-height: 52px; }
.sig-lbl { font-weight: 700; font-size: 6.5pt; text-transform: uppercase; color: #0B1A15; }
.sig-sub { font-size: 6.5pt; color: #888; margin-top: 20px; border-top: 0.5px solid #D4C8A8; padding-top: 4px; }

.footer { background: #0B1A15; color: #fff; padding: 6px 20px; display: flex; justify-content: space-between; align-items: center; margin-top: 12px; border-top: 1px solid #C98B2A; }
.footer-l { font-weight: 700; font-size: 7pt; }
.footer-c { font-size: 6.5pt; color: #AAA; }
.footer-r { font-size: 7pt; color: #C98B2A; font-weight: 700; }

.watermark { position: fixed; top: 45%; left: 50%; transform: translate(-50%, -50%) rotate(35deg); font-size: 80pt; font-weight: 700; color: rgba(0,0,0,0.05); pointer-events: none; z-index: 999; letter-spacing: 6px; white-space: nowrap; }
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
{watermark}
<div class="header">
  <div class="hdr-left">
    <div class="brand"><span class="brand-main">BOMTEMPO</span><span class="brand-accent">ENGENHARIA</span></div>
    <div class="hdr-sub">Relatório Diário de Obra — RDO</div>
    {preview_badge}
  </div>
  <div class="hdr-box">
    <div class="hdr-box-lbl">Contrato</div>
    <div class="hdr-box-val">{contrato}</div>
    <div class="hdr-box-date">{data_rdo}</div>
    <div class="hdr-box-clima">{clima}</div>
  </div>
</div>

<div class="content">
  <div class="info-grid">
    <div class="info-label">Projeto</div><div class="info-value">{projeto}</div>
    <div class="info-label">Cliente</div><div class="info-value">{cliente}</div>
    <div class="info-label">Localização</div><div class="info-value">{localizacao}</div>
    <div class="info-label">Clima</div><div class="info-value">{clima}</div>
    <div class="info-label">Turno</div><div class="info-value">{turno}</div>
    <div class="info-label">Horário</div><div class="info-value">{h_ini} – {h_fim}</div>
    <div {intr_lbl}>Interrupção</div><div {intr_val}>{interrupcao}</div>
    <div {mot_lbl}>Motivo</div><div {mot_val}>{motivo}</div>
  </div>

  <div class="kpi-bar">
    <div class="kpi-item"><span class="kpi-val">{len(mao_obra)}</span><span class="kpi-lbl">Profissionais</span></div>
    <div class="kpi-item"><span class="kpi-val">{len(equipamentos)}</span><span class="kpi-lbl">Equipamentos</span></div>
    <div class="kpi-item"><span class="kpi-val">{len(atividades)}</span><span class="kpi-lbl">Atividades</span></div>
    <div class="kpi-item"><span class="kpi-val">{len(materiais)}</span><span class="kpi-lbl">Materiais</span></div>
  </div>

  <div class="section-hdr"><div class="sec-badge">1</div><div class="sec-title">Mão de Obra em Campo</div></div>
  <table class="tbl-patina">
    <thead><tr><th>Função / Cargo</th><th class="center w55">Qtd.</th><th>Observações</th></tr></thead>
    <tbody>{mo_rows()}</tbody>
  </table>

  <div class="section-hdr"><div class="sec-badge">2</div><div class="sec-title">Equipamentos Mobilizados</div></div>
  <table class="tbl-copper">
    <thead><tr><th>Equipamento / Descrição</th><th class="center w60">Qtd.</th></tr></thead>
    <tbody>{eq_rows()}</tbody>
  </table>

  <div class="section-hdr"><div class="sec-badge">3</div><div class="sec-title">Atividades Executadas no Dia</div></div>
  <table class="tbl-green">
    <thead><tr><th>Atividade / Descrição</th><th class="center w70">Progresso</th></tr></thead>
    <tbody>{atv_rows()}</tbody>
  </table>
{mat_section}
  <div class="section-hdr"><div class="sec-badge">{sec_obs}</div><div class="sec-title">Observações Gerais</div></div>
  {obs_block}

  <div class="signatures">
    <div class="sig-box">
      <div class="sig-lbl">Responsável Técnico / Mestre de Obras</div>
      <div class="sig-sub">Assinatura</div>
    </div>
    <div class="sig-box">
      <div class="sig-lbl">Engenheiro Responsável / Fiscal</div>
      <div class="sig-sub">Data: {data_rdo}</div>
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-l">BOMTEMPO INTELLIGENCE</div>
  <div class="footer-c">RDO{f" · {id_label}" if id_label else ""} · Contrato {contrato} · {data_rdo} · Emitido em {emissao}</div>
  <div class="footer-r">Relatório Diário de Obra</div>
</div>
</body>
</html>"""

    @staticmethod
    def generate_pdf(
        rdo_data: Dict[str, Any], is_preview: bool = False, id_rdo: str = ""
    ) -> tuple:
        """
        Gera PDF do RDO via HTML → Playwright (Edge).

        Args:
            rdo_data: Dados do RDO (cabeçalho + listas)
            is_preview: Se True, gera arquivo temporário com marca d'água RASCUNHO
            id_rdo: ID do RDO (usado como nome do arquivo quando disponível)

        Returns:
            (pdf_path: str, pdf_url: str)
        """
        try:
            Config.RDO_PDF_DIR.mkdir(parents=True, exist_ok=True)

            contrato = rdo_data.get("contrato", "SEM-CONTRATO")
            data = rdo_data.get("data", datetime.now().strftime("%Y-%m-%d"))

            if is_preview:
                filename = f"RDO-PREVIEW-{contrato}-{data}.pdf"
            elif id_rdo:
                filename = f"{id_rdo}.pdf"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"RDO-{contrato}-{data}-{timestamp}.pdf"

            pdf_path = Config.RDO_PDF_DIR / filename

            html = RDOService._build_rdo_html(rdo_data, is_preview, id_rdo)
            html_to_pdf(html, pdf_path)

            pdf_url = RDOService.get_pdf_url(str(pdf_path))
            logger.info(f"✅ PDF gerado: {pdf_path.name} → {pdf_url}")
            return str(pdf_path), pdf_url

        except Exception as e:
            logger.error(f"❌ Erro ao gerar PDF: {e}")
            return None, ""

    @staticmethod
    def save_to_database(
        rdo_data: Dict[str, Any], submitted_by: str = ""
    ) -> Optional[str]:  # noqa: ARG004
        """
        Salva RDO no Supabase (rdo_cabecalho + sub-tabelas).
        Retorna id_rdo (string) ou None se falhar.

        Schema real Supabase (case-sensitive com aspas):
        rdo_cabecalho:   ID_RDO, Data, Contrato, Projeto, Cliente, Terceirizado,
                         Localizacao, Condicao_Climatica, Turno, Hora_Inicio, Hora_Termino,
                         Houve_Interrupcao, Motivo_Interrupcao, Houve_Acidente, Observacoes
        rdo_mao_obra:    ID_RDO, Contrato, Data, Profissao, Quantidade(bigint),
                         Horas_Trabalhadas(bigint), Custo_Unitario_Hora, Custo_Total, observacoes
        rdo_equipamentos:ID_RDO, Contrato, Data, Equipamento, Unidade, Quantidade(bigint),
                         Horas_Utilizadas(bigint), Custo_Unitario_Hora, Custo_Total
        rdo_atividades:  ID_RDO, Contrato, Data, Sequencia(bigint), Atividade,
                         Progresso_Percentual, Status
        rdo_materiais:   NÃO EXISTE no schema — dados de materiais ignorados
        """
        try:
            contrato = rdo_data.get("contrato", "SEM-CONTRATO")
            data = rdo_data.get("data", datetime.now().strftime("%Y-%m-%d"))
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            id_rdo = f"RDO-{contrato}-{data}-{timestamp}"

            def _to_int(val) -> int:
                try:
                    return int(str(val).strip())
                except (ValueError, TypeError):
                    return 0

            # 1. Cabeçalho — nomes de coluna exatos do schema Supabase
            # NOTA: pdf_path NÃO vai no INSERT inicial — é atualizado via UPDATE
            # após o upload ao Supabase Storage (evita falha se coluna não existe ainda).
            cabecalho = {
                "ID_RDO": id_rdo,
                "Data": data,
                "Contrato": contrato,
                "Projeto": rdo_data.get("projeto", ""),
                "Cliente": rdo_data.get("cliente", ""),
                "Terceirizado": "",
                "Localizacao": rdo_data.get("localizacao", ""),
                "Condicao_Climatica": rdo_data.get("clima", ""),
                "Turno": rdo_data.get("turno", ""),
                "Hora_Inicio": rdo_data.get("hora_inicio", ""),
                "Hora_Termino": rdo_data.get("hora_termino", ""),
                "Houve_Interrupcao": "Sim" if rdo_data.get("houve_interrupcao") else "Não",
                "Motivo_Interrupcao": rdo_data.get("motivo_interrupcao", ""),
                "Houve_Acidente": "Não",
                "Observacoes": rdo_data.get("observacoes", ""),
            }
            result = sb_insert("rdo_cabecalho", cabecalho)
            if result is None:
                logger.error("❌ Falha ao inserir rdo_cabecalho no Supabase")
                return None

            # 2. Mão de Obra
            for item in rdo_data.get("mao_obra", []):
                sb_insert(
                    "rdo_mao_obra",
                    {
                        "ID_RDO": id_rdo,
                        "Contrato": contrato,
                        "Data": data,
                        "Profissao": item.get("funcao", ""),
                        "Quantidade": _to_int(item.get("quantidade", 0)),
                        "Horas_Trabalhadas": 0,
                        "Custo_Unitario_Hora": "",
                        "Custo_Total": "",
                        "observacoes": item.get("obs", ""),  # lowercase no schema
                    },
                )

            # 3. Equipamentos
            for item in rdo_data.get("equipamentos", []):
                sb_insert(
                    "rdo_equipamentos",
                    {
                        "ID_RDO": id_rdo,
                        "Contrato": contrato,
                        "Data": data,
                        "Equipamento": item.get("descricao", ""),
                        "Unidade": "",
                        "Quantidade": _to_int(item.get("quantidade", 0)),
                        "Horas_Utilizadas": 0,
                        "Custo_Unitario_Hora": "",
                        "Custo_Total": "",
                    },
                )

            # 4. Atividades
            for seq, item in enumerate(rdo_data.get("atividades", []), start=1):
                sb_insert(
                    "rdo_atividades",
                    {
                        "ID_RDO": id_rdo,
                        "Contrato": contrato,
                        "Data": data,
                        "Sequencia": seq,
                        "Atividade": item.get("atividade", ""),
                        "Progresso_Percentual": str(item.get("percentual", "")),
                        "Status": "Em andamento",
                    },
                )

            # 5. Materiais
            for item in rdo_data.get("materiais", []):
                sb_insert(
                    "rdo_materiais",
                    {
                        "ID_RDO": id_rdo,
                        "Contrato": contrato,
                        "Data": data,
                        "Material": item.get("descricao", ""),
                        "Unidade": item.get("unidade", ""),
                        "Quantidade": _to_int(item.get("quantidade", 0)),
                        "Custo_Unitario": "",
                        "Custo_Total": "",
                    },
                )

            logger.info(f"✅ RDO salvo no Supabase: {id_rdo}")
            return id_rdo

        except Exception as e:
            logger.error(f"❌ Erro ao salvar RDO: {e}")
            return None

    @staticmethod
    def upload_pdf_to_storage(pdf_path: str, id_rdo: str, bucket: str = "rdo-pdfs") -> str:
        """
        Faz upload do PDF gerado para o Supabase Storage.
        Retorna a URL pública permanente (para guardar no banco) ou "" em caso de erro.

        Padrão reutilizável em todos os módulos:
          - RDO: bucket="rdo-pdfs", path="{id_rdo}.pdf"
          - Reembolso: bucket="reembolso-docs", path="{id_reembolso}/nota.jpg"
          - Qualquer arquivo: sb_storage_upload(bucket, path, bytes, content_type)
        """
        try:
            with open(pdf_path, "rb") as f:
                file_bytes = f.read()
            storage_path = f"{id_rdo}.pdf"
            url = sb_storage_upload(bucket, storage_path, file_bytes, "application/pdf")
            return url or ""
        except Exception as e:
            logger.error(f"❌ Erro ao fazer upload do PDF para Storage: {e}")
            return ""

    @staticmethod
    def update_pdf_info(id_rdo: str, pdf_url: str) -> bool:
        """Atualiza pdf_path no rdo_cabecalho com a URL pública do Supabase Storage."""
        if not pdf_url:
            return False
        ok = sb_update("rdo_cabecalho", {"ID_RDO": id_rdo}, {"pdf_path": pdf_url})
        if not ok:
            logger.error(f"❌ Falha ao atualizar pdf_path para {id_rdo}")
        return ok

    @staticmethod
    def analyze_with_ai(rdo_data: Dict[str, Any]) -> str:
        """
        Analisa RDO usando IA e retorna insights

        Returns:
            Texto markdown com análise
        """
        try:
            # Preparar prompt
            mao_obra_count = len(rdo_data.get("mao_obra", []))
            equipamentos_count = len(rdo_data.get("equipamentos", []))
            atividades_count = len(rdo_data.get("atividades", []))
            clima = rdo_data.get("clima", "Não informado")
            houve_interrupcao = rdo_data.get("houve_interrupcao", False)

            # Dados extras para contexto
            mao_obra_lista = rdo_data.get("mao_obra", [])
            atividades_lista = rdo_data.get("atividades", [])

            mao_obra_detalhe = (
                "\n".join(
                    f"  - {item.get('funcao','?')}: {item.get('quantidade','?')} unid."
                    for item in mao_obra_lista[:8]
                )
                or "  (Nenhuma registrada)"
            )

            atividades_detalhe = (
                "\n".join(f"  - {item.get('atividade','?')}" for item in atividades_lista[:8])
                or "  (Nenhuma registrada)"
            )

            prompt = f"""Você é um consultor sênior de engenharia civil com 20 anos de experiência em gestão de obras. Analise o RDO abaixo e produza um relatório profissional, direto e acionável.

**DADOS DO RDO:**
- Data: {rdo_data.get('data', 'N/A')} | Contrato: {rdo_data.get('contrato', 'N/A')}
- Clima: {clima} | Turno: {rdo_data.get('turno', 'N/A')} | Horário: {rdo_data.get('hora_inicio','?')}–{rdo_data.get('hora_termino','?')}
- Houve Interrupção: {'⚠️ SIM' if houve_interrupcao else 'Não'}{f" — Motivo: {rdo_data.get('motivo_interrupcao','?')}" if houve_interrupcao else ''}
- Profissionais em campo: {mao_obra_count}
- Equipamentos mobilizados: {equipamentos_count}
- Atividades registradas: {atividades_count}

**MÃO DE OBRA:**
{mao_obra_detalhe}

**ATIVIDADES DO DIA:**
{atividades_detalhe}

**OBSERVAÇÕES:** {rdo_data.get('observacoes', 'Nenhuma')[:300]}

---

Retorne a análise EXATAMENTE neste formato Markdown (mantenha os títulos e estrutura, preencha com conteúdo específico e concreto):

## 📊 RESUMO EXECUTIVO
[2 frases concisas: o que foi feito, situação geral da obra nesse dia. Se campo vazio, diagnostique o que isso indica.]

## 🔨 ESCOPO EXECUTADO
- [Liste o que foi realizado com base nas atividades informadas]
- [Se não há atividades, indique ausência e impacto]

## ⚠️ ALERTAS E RISCOS
- **Cronograma:** [avalie risco de atraso com base no volume de trabalho declarado]
- **Clima:** [avalie impacto do clima {clima} na produtividade e segurança]
- **Recursos:** [avalie adequação da equipe de {mao_obra_count} profissional(is) para o escopo declarado]

## 💡 RECOMENDAÇÕES
1. **Imediata:** [ação para o próximo dia de obra]
2. **Preventiva:** [medida para evitar repetição do problema ou manter o ritmo]
3. **Documentação:** [o que deve ser registrado ou formalizado]"""

            messages = [
                {
                    "role": "system",
                    "content": "Você é um consultor de engenharia civil sênior. Seja preciso, direto e profissional. Não use linguagem vaga. Baseie-se exclusivamente nos dados fornecidos.",
                },
                {"role": "user", "content": prompt},
            ]

            response = ai_client.query(messages)
            logger.info("✅ Análise IA concluída")
            return response

        except Exception as e:
            logger.error(f"❌ Erro na análise IA: {e}")
            return f"""## ⚠️ Erro na Análise

Não foi possível processar a análise IA neste momento.

**Resumo Manual:**
- RDO registrado com sucesso
- Dados salvos e PDF gerado

{str(e)}"""

    @staticmethod
    def get_rdos_by_contract(contrato: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Busca RDOs de um contrato específico no Supabase"""
        return sb_select(
            "rdo_cabecalho",
            filters={"Contrato": contrato},  # case-sensitive conforme schema
            order="ID_RDO.desc",
            limit=limit,
        )

    @staticmethod
    def get_all_rdos(limit: int = 500) -> List[Dict[str, Any]]:
        """Busca todos os RDOs (admin) no Supabase"""
        return sb_select(
            "rdo_cabecalho",
            order="ID_RDO.desc",
            limit=limit,
        )
