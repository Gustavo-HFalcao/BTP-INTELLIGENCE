"""
RelatoriosState — Bomtempo Intelligence
State and event handlers for the Relatórios module (Feature 3).
"""

from __future__ import annotations

import asyncio
import threading
import time
import unicodedata
from datetime import datetime

import reflex as rx

from bomtempo.core.logging_utils import get_logger
from bomtempo.core.report_service import ReportService
from bomtempo.core.audit_logger import audit_log, audit_error, AuditCategory

logger = get_logger(__name__)


class RelatoriosState(rx.State):
    # ── Seleção ──────────────────────────────────────────────────────────────
    selected_contrato: str = ""
    selected_abordagem: str = "estrategica"

    # ── Static Dossier ────────────────────────────────────────────────────────
    report_html_preview: str = ""
    report_pdf_url: str = ""
    is_generating_static: bool = False

    # ── AI Report ────────────────────────────────────────────────────────────
    ai_report_text: str = ""
    is_generating_ai: bool = False

    # ── Custom Chatbox ────────────────────────────────────────────────────────
    custom_prompt: str = ""
    is_generating_custom: bool = False

    # ── Shared streaming flag ────────────────────────────────────────────────
    is_streaming: bool = False

    # ── History ───────────────────────────────────────────────────────────────
    reports_history: list[dict] = []
    is_loading_history: bool = False

    # ── Error / UI feedback ───────────────────────────────────────────────────
    error_msg: str = ""

    # ── Setters (Reflex compiler requirement — no dynamic setattr) ────────────

    def set_selected_contrato(self, val: str):
        self.selected_contrato = val
        # Reset previous output when contrato changes
        self.report_html_preview = ""
        self.report_pdf_url = ""
        self.ai_report_text = ""
        self.error_msg = ""

    def set_selected_abordagem(self, val: str):
        self.selected_abordagem = val

    def set_custom_prompt(self, val: str):
        self.custom_prompt = val

    def clear_ai_text(self):
        self.ai_report_text = ""
        self.error_msg = ""

    def clear_static_preview(self):
        self.report_html_preview = ""
        self.report_pdf_url = ""
        self.error_msg = ""

    # ── On Load ───────────────────────────────────────────────────────────────

    async def load_page(self):
        """Called on page load — fetches report history from Supabase."""
        self.is_loading_history = True
        yield
        loop = asyncio.get_event_loop()
        try:
            history = await loop.run_in_executor(None, ReportService.load_history)
            self.reports_history = history
        except Exception as e:
            logger.error(f"RelatoriosState.load_page error: {e}")
        finally:
            self.is_loading_history = False

    # ── Generate Static Report ────────────────────────────────────────────────

    @rx.event(background=True)
    async def generate_static_report(self):
        """Build static HTML dossier, generate PDF, upload to Supabase."""
        # Collect ALL state reads inside async with self: (including get_state)
        contrato = ""
        cliente = "—"
        current_user = "Sistema"
        fmt: dict = {}
        obra: dict = {}
        disciplinas: list = []

        async with self:
            contrato = self.selected_contrato or "Geral / Portfólio"
            self.is_generating_static = True
            self.report_html_preview = ""
            self.report_pdf_url = ""
            self.error_msg = ""

            from bomtempo.state.global_state import GlobalState
            gs = await self.get_state(GlobalState)
            fmt = dict(gs.obra_kpi_fmt)
            obra = dict(gs.obra_enterprise_data)
            disciplinas = list(gs.disciplina_progress_chart)
            current_user = str(gs.current_user_name)
            for c in gs.contratos_list:
                if c.get("contrato", "") == contrato:
                    cliente = c.get("cliente", "—")
                    break

        data = {
            "contrato": contrato,
            "cliente": cliente,
            "gerado_por": current_user,
            "fmt": fmt,
            "obra": obra,
            "disciplinas": disciplinas,
        }

        loop = asyncio.get_running_loop()

        try:
            # Build HTML (CPU-bound — run in executor to free event loop)
            html = await loop.run_in_executor(None, lambda: ReportService.build_static_html(data))

            # Show preview immediately
            async with self:
                self.report_html_preview = html

            # Generate PDF + upload to Supabase Storage
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            _raw = contrato.replace(" ", "_").replace("/", "-")[:30]
            safe_name = unicodedata.normalize("NFKD", _raw).encode("ascii", "ignore").decode("ascii")
            filename = f"relatorio_{safe_name}_{ts}.pdf"

            pdf_path, pdf_url = await loop.run_in_executor(
                None, lambda: ReportService.generate_pdf(html, filename)
            )

            # Save record to Supabase
            record = {
                "contrato": contrato,
                "cliente": cliente,
                "tipo": "estatico",
                "titulo": f"Relatório Estático — {contrato}",
                "pdf_path": pdf_path,
                "pdf_url": pdf_url,
                "created_by": current_user,
            }
            await loop.run_in_executor(None, lambda: ReportService.save_report(record))

            # Reload history
            history = await loop.run_in_executor(None, ReportService.load_history)

            audit_log(
                category=AuditCategory.REPORT_GEN,
                action=f"Relatório estático gerado — contrato '{contrato}' por '{current_user}'",
                username=current_user,
                entity_type="relatorio",
                metadata={"contrato": contrato, "tipo": "estatico", "pdf_url": pdf_url},
                status="success",
            )
            async with self:
                self.report_pdf_url = pdf_url
                self.reports_history = history
                self.is_generating_static = False

        except Exception as e:
            logger.error(f"generate_static_report failed: {e}")
            audit_error(
                action=f"Falha ao gerar relatório estático — contrato '{contrato}'",
                username=current_user,
                entity_type="relatorio",
                error=e,
            )
            async with self:
                self.error_msg = f"Erro ao gerar relatório: {str(e)[:200]}"
                self.is_generating_static = False

    # ── Generate AI Report ────────────────────────────────────────────────────

    @rx.event(background=True)
    async def generate_ai_report(self):
        """Stream AI-generated report based on selected approach."""
        contrato = ""
        cliente = "—"
        current_user = "Sistema"
        abordagem = "estrategica"
        fmt: dict = {}
        obra: dict = {}
        disciplinas: list = []

        async with self:
            contrato = self.selected_contrato or "Geral / Portfólio"
            abordagem = self.selected_abordagem
            self.is_generating_ai = True
            self.is_streaming = True
            self.ai_report_text = ""
            self.error_msg = ""

            from bomtempo.state.global_state import GlobalState
            gs = await self.get_state(GlobalState)
            fmt = dict(gs.obra_kpi_fmt)
            obra = dict(gs.obra_enterprise_data)
            disciplinas = list(gs.disciplina_progress_chart)
            current_user = str(gs.current_user_name)
            for c in gs.contratos_list:
                if c.get("contrato", "") == contrato:
                    cliente = c.get("cliente", "—")
                    break

        data = {
            "contrato": contrato,
            "cliente": cliente,
            "gerado_por": current_user,
            "fmt": fmt,
            "obra": obra,
            "disciplinas": disciplinas,
        }

        messages = ReportService.build_ai_prompt(abordagem, data)
        full_text = await self._stream_ai_text(messages)

        # Generate PDF + save to Supabase
        if full_text:
            loop = asyncio.get_running_loop()
            pdf_path = ""
            pdf_url = ""
            try:
                # Build styled HTML from AI markdown
                ai_html = await loop.run_in_executor(
                    None, lambda: ReportService.build_ai_html(full_text, data, abordagem)
                )
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                _raw = contrato.replace(" ", "_").replace("/", "-")[:30]
                safe_name = unicodedata.normalize("NFKD", _raw).encode("ascii", "ignore").decode("ascii")
                filename = f"relatorio_ia_{safe_name}_{ts}.pdf"
                pdf_path, pdf_url = await loop.run_in_executor(
                    None, lambda: ReportService.generate_pdf(ai_html, filename)
                )
            except Exception as e:
                logger.error(f"Error generating AI report PDF: {e}")

            try:
                record = {
                    "contrato": contrato,
                    "cliente": cliente,
                    "tipo": "ia",
                    "abordagem": abordagem,
                    "titulo": f"Análise IA ({abordagem.capitalize()}) — {contrato}",
                    "ai_text": full_text,
                    "pdf_path": pdf_path,
                    "pdf_url": pdf_url,
                    "created_by": current_user,
                }
                await loop.run_in_executor(None, lambda: ReportService.save_report(record))
                history = await loop.run_in_executor(None, ReportService.load_history)
                async with self:
                    self.report_pdf_url = pdf_url
                    self.reports_history = history
            except Exception as e:
                logger.error(f"Error saving AI report to Supabase: {e}")

        audit_log(
            category=AuditCategory.REPORT_GEN,
            action=f"Relatório IA ({abordagem}) gerado — contrato '{contrato}' por '{current_user}'",
            username=current_user,
            entity_type="relatorio",
            metadata={"contrato": contrato, "tipo": "ia", "abordagem": abordagem},
            status="success",
        )
        async with self:
            self.is_generating_ai = False
            self.is_streaming = False

    # ── Generate Custom Report (Chatbox) ──────────────────────────────────────

    @rx.event(background=True)
    async def generate_custom_report(self):
        """Stream custom AI report from user's natural language prompt."""
        contrato = ""
        cliente = "—"
        current_user = "Sistema"
        prompt = ""
        fmt: dict = {}
        obra: dict = {}
        disciplinas: list = []

        async with self:
            contrato = self.selected_contrato or "Geral / Portfólio"
            prompt = self.custom_prompt.strip()

            if not prompt:
                self.error_msg = "Descreva o relatório desejado."
                return

            self.is_generating_custom = True
            self.is_streaming = True
            self.ai_report_text = ""
            self.error_msg = ""

            from bomtempo.state.global_state import GlobalState
            gs = await self.get_state(GlobalState)
            fmt = dict(gs.obra_kpi_fmt)
            obra = dict(gs.obra_enterprise_data)
            disciplinas = list(gs.disciplina_progress_chart)
            current_user = str(gs.current_user_name)
            for c in gs.contratos_list:
                if c.get("contrato", "") == contrato:
                    cliente = c.get("cliente", "—")
                    break

        data = {
            "contrato": contrato,
            "cliente": cliente,
            "gerado_por": current_user,
            "fmt": fmt,
            "obra": obra,
            "disciplinas": disciplinas,
        }

        messages = ReportService.build_ai_prompt("custom", data, custom_instruction=prompt)
        full_text = await self._stream_ai_text(messages)

        if full_text:
            loop = asyncio.get_running_loop()
            pdf_path = ""
            pdf_url = ""
            try:
                ai_html = await loop.run_in_executor(
                    None, lambda: ReportService.build_ai_html(full_text, data, "custom")
                )
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                _raw = contrato.replace(" ", "_").replace("/", "-")[:30]
                safe_name = unicodedata.normalize("NFKD", _raw).encode("ascii", "ignore").decode("ascii")
                filename = f"relatorio_custom_{safe_name}_{ts}.pdf"
                pdf_path, pdf_url = await loop.run_in_executor(
                    None, lambda: ReportService.generate_pdf(ai_html, filename)
                )
            except Exception as e:
                logger.error(f"Error generating custom report PDF: {e}")

            try:
                short_prompt = prompt[:60] + ("..." if len(prompt) > 60 else "")
                record = {
                    "contrato": contrato,
                    "cliente": cliente,
                    "tipo": "custom",
                    "abordagem": short_prompt,
                    "titulo": f"Relatório Customizado — {contrato}",
                    "ai_text": full_text,
                    "pdf_path": pdf_path,
                    "pdf_url": pdf_url,
                    "created_by": current_user,
                }
                await loop.run_in_executor(None, lambda: ReportService.save_report(record))
                history = await loop.run_in_executor(None, ReportService.load_history)
                async with self:
                    self.report_pdf_url = pdf_url
                    self.reports_history = history
                    self.custom_prompt = ""
            except Exception as e:
                logger.error(f"Error saving custom report: {e}")

        audit_log(
            category=AuditCategory.REPORT_GEN,
            action=f"Relatório custom gerado — contrato '{contrato}' por '{current_user}'",
            username=current_user,
            entity_type="relatorio",
            metadata={"contrato": contrato, "tipo": "custom", "prompt_preview": (prompt or "")[:120]},
            status="success",
        )
        async with self:
            self.is_generating_custom = False
            self.is_streaming = False

    # ── Copy AI Text ──────────────────────────────────────────────────────────

    async def copy_ai_text(self):
        yield rx.set_clipboard(self.ai_report_text)

    def open_pdf_url(self, url: str):
        """Abre PDF em nova aba via JS — bypassa SPA/PWA router."""
        if url and url.startswith("http"):
            return rx.call_script(f"window.open({repr(url)}, '_blank', 'noopener,noreferrer')")

    # ── Internal: Streaming Helper ────────────────────────────────────────────

    async def _stream_ai_text(self, messages: list[dict]) -> str:
        """
        Stream AI response tokens via thread + asyncio.Queue.
        Updates self.ai_report_text every 200ms with live cursor.
        Returns full text on completion (or "" on error).
        """
        from bomtempo.core.ai_client import ai_client

        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _run():
            try:
                for chunk in ai_client.query_stream(messages):
                    asyncio.run_coroutine_threadsafe(q.put(chunk), loop)
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(q.put(f"__STREAM_ERROR__:{exc}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(None), loop)

        threading.Thread(target=_run, daemon=True).start()

        full_text = ""
        last_update = time.monotonic()
        received_first = False

        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=90.0)
            except asyncio.TimeoutError:
                logger.error("AI report streaming timeout after 90s")
                break

            if chunk is None:
                break

            if isinstance(chunk, str) and chunk.startswith("__STREAM_ERROR__:"):
                err = chunk.split(":", 1)[1] if ":" in chunk else "Erro desconhecido"
                async with self:
                    self.ai_report_text = (
                        f"**Erro ao conectar com a IA:** {err[:200]}\n\nTente novamente."
                    )
                    self.error_msg = err[:200]
                return ""

            full_text += chunk
            now = time.monotonic()

            if not received_first or (now - last_update >= 0.20):
                async with self:
                    self.ai_report_text = full_text + "▌"
                received_first = True
                last_update = now

        if full_text:
            async with self:
                self.ai_report_text = full_text

        return full_text
