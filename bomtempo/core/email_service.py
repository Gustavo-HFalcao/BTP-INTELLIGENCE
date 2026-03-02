"""
Email Service - Envio SMTP com anexos e HTML formatado
"""

import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List

from bomtempo.core.config import Config
from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)


def _md_to_html(text: str) -> str:
    """Converte Markdown simples para HTML formatado"""
    if not text:
        return ""

    lines = text.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        # Headings
        if line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = line[3:].strip()
            html_lines.append(
                f'<h3 style="color:#C98B2A;margin-top:20px;margin-bottom:8px;font-size:15px;border-bottom:1px solid rgba(201,139,42,0.3);padding-bottom:6px;">{content}</h3>'
            )
        elif line.startswith("# "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = line[2:].strip()
            html_lines.append(f'<h2 style="color:#C98B2A;margin-top:24px;">{content}</h2>')
        # List items
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                html_lines.append('<ul style="margin:8px 0;padding-left:20px;">')
                in_ul = True
            content = line[2:].strip()
            # Bold dentro do item
            content = re.sub(
                r"\*\*(.+?)\*\*", r'<strong style="color:#E0E0E0;">\1</strong>', content
            )
            html_lines.append(f'<li style="margin:4px 0;color:#C8D8D4;">{content}</li>')
        # Numbered list
        elif re.match(r"^\d+\.\s", line):
            if not in_ul:
                html_lines.append('<ol style="margin:8px 0;padding-left:20px;">')
                in_ul = True
            content = re.sub(r"^\d+\.\s", "", line).strip()
            content = re.sub(
                r"\*\*(.+?)\*\*", r'<strong style="color:#E0E0E0;">\1</strong>', content
            )
            html_lines.append(f'<li style="margin:4px 0;color:#C8D8D4;">{content}</li>')
        # Empty line
        elif line.strip() == "":
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("<br>")
        # Normal paragraph
        else:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            content = line.strip()
            # Bold
            content = re.sub(
                r"\*\*(.+?)\*\*", r'<strong style="color:#E0E0E0;">\1</strong>', content
            )
            if content:
                html_lines.append(f'<p style="margin:6px 0;color:#C8D8D4;">{content}</p>')

    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _build_data_table(rdo_data: dict) -> str:
    """Gera tabela HTML com os dados principais do RDO"""
    rows = [
        ("Data", rdo_data.get("data", "—")),
        ("Contrato", rdo_data.get("contrato", "—")),
        ("Projeto", rdo_data.get("projeto", "—") or "—"),
        ("Cliente", rdo_data.get("cliente", "—") or "—"),
        ("Localização", rdo_data.get("localizacao", "—") or "—"),
        ("Condição Climática", rdo_data.get("clima", "—")),
        ("Turno", rdo_data.get("turno", "—")),
        ("Horário", f"{rdo_data.get('hora_inicio','—')} → {rdo_data.get('hora_termino','—')}"),
        ("Mão de Obra", f"{len(rdo_data.get('mao_obra', []))} profissional(is)"),
        ("Equipamentos", f"{len(rdo_data.get('equipamentos', []))} unidade(s)"),
        ("Atividades", f"{len(rdo_data.get('atividades', []))} atividade(s)"),
        ("Houve Interrupção", "Sim" if rdo_data.get("houve_interrupcao") else "Não"),
    ]

    table_rows = ""
    for i, (label, value) in enumerate(rows):
        bg = "rgba(201,139,42,0.05)" if i % 2 == 0 else "transparent"
        table_rows += f"""
        <tr style="background:{bg};">
            <td style="padding:10px 14px;font-weight:600;color:#889999;font-size:13px;width:40%;border-bottom:1px solid rgba(255,255,255,0.05);">{label}</td>
            <td style="padding:10px 14px;color:#E0E0E0;font-size:13px;border-bottom:1px solid rgba(255,255,255,0.05);">{value}</td>
        </tr>"""

    return f"""
    <table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;">
        <thead>
            <tr style="background:rgba(201,139,42,0.15);">
                <th colspan="2" style="padding:12px 14px;text-align:left;color:#C98B2A;font-size:13px;text-transform:uppercase;letter-spacing:0.05em;border-bottom:2px solid rgba(201,139,42,0.3);">
                    📋 Dados do Relatório
                </th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>"""


class EmailService:
    """Serviço de envio de emails via SMTP"""

    @staticmethod
    def send_rdo_email(
        recipients: List[str], rdo_data: dict, pdf_path: str, ai_insights: str
    ) -> bool:
        """
        Envia RDO por email com PDF anexo + análise IA formatada

        Args:
            recipients: Lista de emails destinatários
            rdo_data: Dados do RDO
            pdf_path: Caminho do PDF a anexar
            ai_insights: Análise IA em markdown

        Returns:
            True se enviado com sucesso
        """
        try:
            if not recipients:
                logger.warning("Nenhum destinatário fornecido")
                return False

            if not Config.RDO_EMAIL_PASSWORD:
                logger.error("❌ RDO_EMAIL_PASSWORD não configurado no .env")
                return False

            if not Path(pdf_path).exists():
                logger.error(f"❌ PDF não encontrado: {pdf_path}")
                return False

            msg = MIMEMultipart("alternative")
            msg["From"] = Config.RDO_EMAIL_USER
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = (
                f"📋 RDO | {rdo_data.get('contrato','?')} | "
                f"{rdo_data.get('data','?')} | BOMTEMPO Engenharia"
            )

            data_table = _build_data_table(rdo_data)
            ai_html = _md_to_html(ai_insights)

            contrato = rdo_data.get("contrato", "N/A")
            data_rdo = rdo_data.get("data", "N/A")
            observacoes = (
                rdo_data.get("observacoes", "").strip() or "Nenhuma observação registrada."
            )

            body_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#030504;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030504;">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#0e1a17;border-radius:16px;overflow:hidden;border:1px solid rgba(201,139,42,0.2);">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a0e00 0%,#C98B2A 50%,#2A9D8F 100%);padding:32px 32px 24px;text-align:center;">
            <p style="margin:0 0 4px;color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;text-transform:uppercase;">BOMTEMPO INTELLIGENCE</p>
            <h1 style="margin:0 0 8px;color:#fff;font-size:22px;font-weight:700;letter-spacing:0.02em;">Relatório Diário de Obra</h1>
            <p style="margin:0;background:rgba(0,0,0,0.25);display:inline-block;padding:6px 16px;border-radius:20px;color:#fff;font-size:14px;">
              {contrato} &nbsp;·&nbsp; {data_rdo}
            </p>
          </td>
        </tr>

        <!-- INTRO -->
        <tr>
          <td style="padding:28px 32px 0;">
            <p style="margin:0 0 12px;color:#C8D8D4;font-size:14px;line-height:1.7;">
              Olá! Segue abaixo o <strong style="color:#E0E0E0;">Relatório Diário de Obra</strong> referente ao contrato
              <strong style="color:#C98B2A;">{contrato}</strong> do dia <strong style="color:#C98B2A;">{data_rdo}</strong>.
              O relatório completo em PDF está anexado a este email para registro e archivamento.
            </p>
          </td>
        </tr>

        <!-- TABELA DE DADOS -->
        <tr>
          <td style="padding:20px 32px;">
            {data_table}
          </td>
        </tr>

        <!-- OBSERVAÇÕES (se houver) -->
        {'<tr><td style="padding:0 32px 20px;"><div style="background:rgba(42,157,143,0.08);border-left:3px solid #2A9D8F;padding:14px 18px;border-radius:0 8px 8px 0;"><p style="margin:0 0 6px;color:#2A9D8F;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">📝 Observações do Dia</p><p style="margin:0;color:#C8D8D4;font-size:13px;line-height:1.6;">' + observacoes + '</p></div></td></tr>' if observacoes and observacoes != "Nenhuma observação registrada." else ''}

        <!-- DIVISOR IA -->
        <tr>
          <td style="padding:0 32px;">
            <div style="border-top:1px solid rgba(42,157,143,0.2);margin:8px 0;"></div>
          </td>
        </tr>

        <!-- ANÁLISE IA -->
        <tr>
          <td style="padding:20px 32px 28px;">
            <div style="background:rgba(42,157,143,0.05);border:1px solid rgba(42,157,143,0.15);border-radius:12px;padding:24px;">
              <div style="display:flex;align-items:center;margin-bottom:16px;">
                <span style="font-size:20px;margin-right:10px;">🤖</span>
                <div>
                  <p style="margin:0;color:#2A9D8F;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;">Análise Automatizada · BOMTEMPO Intelligence</p>
                  <p style="margin:0;color:#889999;font-size:11px;">Gerada por IA com base nos dados deste RDO</p>
                </div>
              </div>
              <div style="color:#C8D8D4;font-size:13px;line-height:1.7;">
                {ai_html}
              </div>
            </div>
          </td>
        </tr>

        <!-- ANEXO INFO -->
        <tr>
          <td style="padding:0 32px 28px;">
            <div style="background:rgba(201,139,42,0.06);border:1px solid rgba(201,139,42,0.15);border-radius:8px;padding:14px 18px;">
              <p style="margin:0;color:#C98B2A;font-size:13px;">
                <strong>📎 Anexo:</strong>&nbsp; O PDF completo do RDO está anexado a este email.
              </p>
            </div>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#081210;padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);">
            <p style="margin:0 0 4px;color:#889999;font-size:12px;">🚀 Gerado automaticamente pelo <strong style="color:#C98B2A;">BOMTEMPO Dashboard</strong></p>
            <p style="margin:0;color:#4a5a58;font-size:11px;">Este é um email automático — não responda diretamente.</p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

            msg.attach(MIMEText(body_html, "html", "utf-8"))

            # Anexar PDF
            pdf_filename = Path(pdf_path).name
            with open(pdf_path, "rb") as f:
                pdf_attach = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attach.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=pdf_filename,
                )
                msg.attach(pdf_attach)

            logger.info(f"Conectando ao SMTP: {Config.RDO_SMTP_SERVER}:{Config.RDO_SMTP_PORT}")

            with smtplib.SMTP(Config.RDO_SMTP_SERVER, Config.RDO_SMTP_PORT) as server:
                server.starttls()
                server.login(Config.RDO_EMAIL_USER, Config.RDO_EMAIL_PASSWORD)
                server.send_message(msg)

            logger.info(
                f"✅ Email enviado para {len(recipients)} destinatário(s): {', '.join(recipients)}"
            )
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Falha de autenticação SMTP. Verifique RDO_EMAIL_PASSWORD no .env")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Erro SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email: {e}")
            return False

    @staticmethod
    def send_reembolso_email(
        recipients: List[str],
        data: dict,
        pdf_path: str,
    ) -> bool:
        """
        Envia notificação de reembolso de combustível por email.
        PDF anexado se disponível. Padrão visual idêntico ao send_rdo_email.
        """
        try:
            if not recipients:
                logger.warning("Nenhum destinatário fornecido para reembolso email")
                return False

            if not Config.RDO_EMAIL_PASSWORD:
                logger.error("❌ RDO_EMAIL_PASSWORD não configurado no .env")
                return False

            submitted_by = str(data.get("submitted_by", "—") or "—")
            combustivel = str(data.get("combustivel", "—") or "—")
            valor_total = str(data.get("valor_total", "—") or "—")
            data_abast = str(data.get("data_abastecimento", "—") or "—")
            cidade = str(data.get("cidade", "—") or "—")
            estado = str(data.get("estado", "—") or "—")
            finalidade = str(data.get("finalidade", "—") or "—")
            litros = str(data.get("litros", "—") or "—")
            rota = str(data.get("rota", "—") or "—")[:100]
            ai_verified = bool(data.get("ai_verified", False))
            ai_insight = str(data.get("ai_insight_text", "") or "")

            ai_badge = "✅ NF Verificada pela IA" if ai_verified else "⚠️ NF não verificada pela IA"
            ai_badge_color = "#27AE60" if ai_verified else "#C0392B"

            rows = [
                ("Solicitante", submitted_by),
                ("Combustível", combustivel),
                ("Litros", f"{litros}L"),
                ("Valor Total", f"R$ {valor_total}"),
                ("Data", data_abast),
                ("Cidade/Estado", f"{cidade}/{estado}"),
                ("Finalidade", finalidade),
                ("Rota", rota),
            ]
            table_rows_html = ""
            for i, (label, value) in enumerate(rows):
                bg = "rgba(201,139,42,0.05)" if i % 2 == 0 else "transparent"
                table_rows_html += (
                    f'<tr style="background:{bg};">'
                    f'<td style="padding:10px 14px;font-weight:600;color:#889999;font-size:13px;'
                    f'width:40%;border-bottom:1px solid rgba(255,255,255,0.05);">{label}</td>'
                    f'<td style="padding:10px 14px;color:#E0E0E0;font-size:13px;'
                    f'border-bottom:1px solid rgba(255,255,255,0.05);">{value}</td>'
                    f"</tr>"
                )

            pdf_exists = pdf_path and Path(pdf_path).exists()
            pdf_section = ""
            if pdf_exists:
                pdf_section = (
                    '<tr><td style="padding:0 32px 20px;">'
                    '<div style="background:rgba(201,139,42,0.06);border:1px solid rgba(201,139,42,0.15);'
                    'border-radius:8px;padding:14px 18px;">'
                    '<p style="margin:0;color:#C98B2A;font-size:13px;">'
                    "<strong>📎 Anexo:</strong>&nbsp;O comprovante PDF está anexado a este email.</p>"
                    "</div></td></tr>"
                )
            ai_section = ""
            if ai_insight:
                ai_section = (
                    '<tr><td style="padding:0 32px 20px;">'
                    '<div style="background:rgba(42,157,143,0.06);border:1px solid rgba(42,157,143,0.15);'
                    'border-radius:8px;padding:14px 18px;">'
                    '<p style="margin:0 0 6px;color:#2A9D8F;font-size:12px;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:0.05em;">🤖 Análise IA</p>'
                    f'<p style="margin:0;color:#C8D8D4;font-size:13px;line-height:1.6;">{ai_insight}</p>'
                    "</div></td></tr>"
                )

            body_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#030504;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030504;">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#0e1a17;border-radius:16px;overflow:hidden;border:1px solid rgba(201,139,42,0.2);">

        <tr>
          <td style="background:linear-gradient(135deg,#1a0e00 0%,#C98B2A 50%,#2A9D8F 100%);padding:32px 32px 24px;text-align:center;">
            <p style="margin:0 0 4px;color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;text-transform:uppercase;">BOMTEMPO INTELLIGENCE</p>
            <h1 style="margin:0 0 8px;color:#fff;font-size:22px;font-weight:700;">⛽ Reembolso de Combustível</h1>
            <p style="margin:0;background:rgba(0,0,0,0.25);display:inline-block;padding:6px 16px;border-radius:20px;color:#fff;font-size:14px;">
              {submitted_by} &nbsp;·&nbsp; {data_abast}
            </p>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 32px 0;">
            <div style="background:{ai_badge_color}20;border:1px solid {ai_badge_color};border-radius:8px;padding:10px 16px;text-align:center;">
              <p style="margin:0;color:{ai_badge_color};font-size:13px;font-weight:600;">{ai_badge}</p>
            </div>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 32px;">
            <table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;">
              <thead>
                <tr style="background:rgba(201,139,42,0.15);">
                  <th colspan="2" style="padding:12px 14px;text-align:left;color:#C98B2A;font-size:13px;text-transform:uppercase;letter-spacing:0.05em;border-bottom:2px solid rgba(201,139,42,0.3);">
                    ⛽ Dados do Abastecimento
                  </th>
                </tr>
              </thead>
              <tbody>{table_rows_html}</tbody>
            </table>
          </td>
        </tr>

        {ai_section}
        {pdf_section}

        <tr>
          <td style="background:#081210;padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);">
            <p style="margin:0 0 4px;color:#889999;font-size:12px;">🚀 Gerado automaticamente pelo <strong style="color:#C98B2A;">BOMTEMPO Dashboard</strong></p>
            <p style="margin:0;color:#4a5a58;font-size:11px;">Este é um email automático — não responda diretamente.</p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

            msg = MIMEMultipart("alternative")
            msg["From"] = Config.RDO_EMAIL_USER
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"⛽ Reembolso Combustível | {submitted_by} | {data_abast} | BOMTEMPO"

            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if pdf_exists:
                pdf_filename = Path(pdf_path).name
                with open(pdf_path, "rb") as f:
                    pdf_attach = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attach.add_header(
                        "Content-Disposition", "attachment", filename=pdf_filename
                    )
                    msg.attach(pdf_attach)

            with smtplib.SMTP(Config.RDO_SMTP_SERVER, Config.RDO_SMTP_PORT) as server:
                server.starttls()
                server.login(Config.RDO_EMAIL_USER, Config.RDO_EMAIL_PASSWORD)
                server.send_message(msg)

            logger.info(
                f"✅ Reembolso email enviado para {len(recipients)} destinatário(s): {', '.join(recipients)}"
            )
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Falha de autenticação SMTP para reembolso email")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de reembolso: {e}")
            return False

    @staticmethod
    def test_connection() -> bool:
        """Testa conexão SMTP"""
        try:
            if not Config.RDO_EMAIL_PASSWORD:
                logger.error("❌ RDO_EMAIL_PASSWORD não configurado")
                return False

            with smtplib.SMTP(Config.RDO_SMTP_SERVER, Config.RDO_SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(Config.RDO_EMAIL_USER, Config.RDO_EMAIL_PASSWORD)

            logger.info("✅ Conexão SMTP OK")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao testar SMTP: {e}")
            return False
