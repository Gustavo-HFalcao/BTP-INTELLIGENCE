"""
Reembolso State — Formulário + Análise IA + Submit
Padrão idêntico ao rdo_state.py (benchmark)
"""

from datetime import datetime
from typing import Any, Dict, List

import reflex as rx

from bomtempo.core.fuel_service import FuelService
from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)


class ReembolsoState(rx.State):
    """Estado do módulo de Reembolso de Combustível."""

    # ── Campos do formulário ───────────────────────────────────────────────────
    combustivel: str = "Gasolina"
    litros: str = ""
    valor_litro: str = ""
    valor_total: str = ""
    data_abastecimento: str = datetime.now().strftime("%Y-%m-%d")
    cidade: str = ""
    estado: str = ""
    km_inicial: str = ""
    km_final: str = ""
    rota: str = ""
    finalidade: str = ""

    # ── Upload de imagem ───────────────────────────────────────────────────────
    image_b64: str = ""  # base64 puro (sem prefixo data:)
    image_mime: str = "image/jpeg"
    image_filename: str = ""
    image_data_url: str = ""  # data:image/...;base64,... para preview

    # ── IA ─────────────────────────────────────────────────────────────────────
    is_analyzing: bool = False
    analysis_done: bool = False
    ai_extracted: Dict[str, Any] = {}
    validation_errors: List[str] = []
    validation_warnings: List[str] = []
    ai_verified: bool = False
    ai_confidence: float = 0.0
    ai_insight_text: str = ""
    # IA retry — máximo 3 tentativas antes de liberar envio manual
    ai_attempt_count: int = 0  # quantas análises foram feitas
    ai_override: bool = False  # usuário decidiu enviar mesmo com divergência

    # ── Submit ─────────────────────────────────────────────────────────────────
    is_submitting: bool = False
    submit_success: bool = False

    # ── Email management (admin) ────────────────────────────────────────────────
    email_list: List[Dict[str, Any]] = []
    email_new_contract: str = ""
    email_new_address: str = ""
    email_is_loading: bool = False

    # ── Dashboard (lista para admin) ───────────────────────────────────────────
    reembolsos_list: List[Dict[str, Any]] = []
    dash_total_gasto: float = 0.0
    dash_media_kml: float = 0.0
    dash_media_custo_km: float = 0.0
    dash_total_registros: int = 0
    dash_is_loading: bool = False
    # Dados para gráficos
    dash_chart_mensal: List[Dict[str, Any]] = []  # [{mes, total}, ...]
    dash_chart_combustivel: List[Dict[str, Any]] = []  # [{name, value}, ...]
    dash_alertas: List[Dict[str, Any]] = []  # registros com desvio > 30%
    dash_filtro_projeto: str = "Todos os Motivos"
    dash_filtro_contrato: str = "Todos os Contratos"

    def set_dash_filtro_projeto(self, val: str):
        self.dash_filtro_projeto = val

    def set_dash_filtro_contrato(self, val: str):
        self.dash_filtro_contrato = val

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _sanitize_money(self, val: str) -> str:
        if not val:
            return ""
        v = val.replace("R$", "").replace(" ", "").strip()
        if "," in v or "." in v:
            v = v.replace(",", ".")
            try:
                return f"{float(v):.2f}"
            except Exception:
                return v
        if v.isdigit() or (v.startswith("-") and v[1:].isdigit()):
            try:
                return f"{(float(v) / 100):.2f}"
            except Exception:
                return v
        return v

    def _sanitize_decimal(self, val: str) -> str:
        if not val:
            return ""
        v = val.strip()
        if "," in v or "." in v:
            v = v.replace(",", ".")
            try:
                return str(float(v))
            except Exception:
                return v
        return v

    def set_combustivel(self, v: str):
        self.combustivel = v

    def set_finalidade(self, v: str):
        self.finalidade = v

    def set_data_abastecimento(self, v: str):
        self.data_abastecimento = v

    def set_litros_and_calc(self, v: str):
        self.litros = self._sanitize_decimal(v)
        self.auto_calc_total()

    def set_valor_litro_and_calc(self, v: str):
        self.valor_litro = self._sanitize_money(v)
        self.auto_calc_total()

    def set_valor_total(self, v: str):
        self.valor_total = self._sanitize_money(v)

    def set_cidade(self, v: str):
        self.cidade = v

    def set_estado(self, v: str):
        self.estado = v

    def set_km_inicial(self, v: str):
        self.km_inicial = self._sanitize_decimal(v)

    def set_km_final(self, v: str):
        self.km_final = self._sanitize_decimal(v)

    def set_rota(self, v: str):
        self.rota = v

    def set_ai_override(self):
        """Marca que o usuário decidiu enviar mesmo com divergência da IA."""
        self.ai_override = True

    def submit_with_override(self):
        """Define ai_override e dispara submit (chamado pelo botão de override)."""
        self.ai_override = True
        return ReembolsoState.submit_reembolso

    def set_email_new_contract(self, v: str):
        self.email_new_contract = v

    def set_email_new_address(self, v: str):
        self.email_new_address = v

    def auto_calc_total(self):
        """Calcula valor total automaticamente quando litros/valor_litro mudam."""
        try:
            l_val = self.litros if self.litros else "0"
            vl_val = self.valor_litro if self.valor_litro else "0"
            litros_f = float(l_val.replace(",", "."))
            vlitro_f = float(vl_val.replace(",", "."))
            if litros_f > 0 and vlitro_f > 0:
                self.valor_total = f"{litros_f * vlitro_f:.2f}"
        except (ValueError, TypeError):
            pass

    def _build_data(self) -> Dict[str, Any]:
        """Compila dados do formulário + resultados IA."""
        base_data = {
            "combustivel": str(self.combustivel),
            "litros": str(self.litros),
            "valor_litro": str(self.valor_litro),
            "valor_total": str(self.valor_total),
            "data_abastecimento": str(self.data_abastecimento),
            "cidade": str(self.cidade),
            "estado": str(self.estado),
            "km_inicial": str(self.km_inicial),
            "km_final": str(self.km_final),
            "rota": str(self.rota),
            "finalidade": str(self.finalidade),
            "ai_verified": bool(self.ai_verified),
            "ai_confidence_score": float(self.ai_confidence),
            "ai_extracted_value": float(self.ai_extracted.get("total", 0) or 0),
            "ai_insight_text": str(self.ai_insight_text),
        }

        from bomtempo.core.fuel_service import FuelService

        metrics = FuelService.calculate_metrics(base_data)
        base_data.update(metrics)
        return base_data

    def reset_form(self):
        """Limpa o formulário após envio."""
        self.combustivel = "Gasolina"
        self.litros = ""
        self.valor_litro = ""
        self.valor_total = ""
        self.data_abastecimento = datetime.now().strftime("%Y-%m-%d")
        self.cidade = ""
        self.estado = ""
        self.km_inicial = ""
        self.km_final = ""
        self.rota = ""
        self.finalidade = ""
        self.image_b64 = ""
        self.image_mime = "image/jpeg"
        self.image_filename = ""
        self.image_data_url = ""
        self.is_analyzing = False
        self.analysis_done = False
        self.ai_extracted = {}
        self.validation_errors = []
        self.validation_warnings = []
        self.ai_verified = False
        self.ai_confidence = 0.0
        self.ai_insight_text = ""
        self.ai_attempt_count = 0
        self.ai_override = False
        self.submit_success = False

    # ── Upload de imagem ───────────────────────────────────────────────────────

    async def handle_nf_upload(self, files: list[rx.UploadFile]):
        """Recebe imagem da NF via rx.upload."""
        if not files:
            return
        file = files[0]
        data = await file.read()

        import base64

        b64 = base64.b64encode(data).decode("utf-8")

        ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpeg"
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "heic": "image/heic",
            "webp": "image/webp",
        }
        mime = mime_map.get(ext, "image/jpeg")

        self.image_b64 = b64
        self.image_mime = mime
        self.image_filename = file.filename
        self.image_data_url = f"data:{mime};base64,{b64}"
        # Limpa análise anterior
        self.analysis_done = False
        self.ai_extracted = {}
        self.validation_errors = []
        self.validation_warnings = []
        self.ai_verified = False
        yield rx.toast("Imagem carregada! Clique em 'Analisar com IA'.", position="top-center")

    # ── Análise IA ─────────────────────────────────────────────────────────────

    @rx.event(background=True)
    async def analyze_receipt(self):
        """
        Background event: envia imagem para Vision API e valida resultado.
        Fases separadas com async with self para flush imediato.
        """
        import asyncio

        loop = asyncio.get_running_loop()

        # FASE 1: mostrar loading
        async with self:
            self.is_analyzing = True
            self.analysis_done = False
            self.validation_errors = []
            self.validation_warnings = []
            self.ai_override = False  # reset override a cada nova tentativa

        # FASE 2: chamar Vision API em executor (não bloqueia event loop)
        ai_result = {}
        try:
            b64 = ""
            mime = "image/jpeg"
            async with self:
                b64 = str(self.image_b64)
                mime = str(self.image_mime)

            if not b64:
                async with self:
                    self.is_analyzing = False
                    yield rx.toast("⚠️ Nenhuma imagem carregada.", position="top-center")
                return

            ai_result = await loop.run_in_executor(
                None, lambda: FuelService.analyze_receipt_image(b64, mime)
            )
            logger.info(f"✅ Vision API result: {ai_result}")
        except Exception as e:
            logger.error(f"❌ analyze_receipt error: {e}")

        # FASE 3: validar e preencher campos
        async with self:
            self.ai_extracted = ai_result or {}
            self.ai_confidence = float(ai_result.get("confidence", 0) or 0)

            # Montar insight text para o PDF
            if ai_result:
                parts = []
                if ai_result.get("fuel_type"):
                    parts.append(f"Combustível: {ai_result['fuel_type']}")
                if ai_result.get("liters"):
                    parts.append(f"Litros: {ai_result['liters']:.3f}L")
                if ai_result.get("price_per_liter"):
                    parts.append(f"Preço/L: R${ai_result['price_per_liter']:.3f}")
                if ai_result.get("total"):
                    parts.append(f"Total NF: R${ai_result['total']:.2f}")
                if ai_result.get("station"):
                    parts.append(f"Posto: {ai_result['station']}")
                if ai_result.get("date"):
                    parts.append(f"Data NF: {ai_result['date']}")
                conf = self.ai_confidence
                parts.append(f"Confiança IA: {conf:.0%}")
                self.ai_insight_text = " | ".join(parts)

                # Pré-preencher campos se vazios
                if not self.litros and ai_result.get("liters"):
                    self.litros = f"{ai_result['liters']:.3f}"
                if not self.valor_litro and ai_result.get("price_per_liter"):
                    self.valor_litro = f"{ai_result['price_per_liter']:.3f}"
                if not self.valor_total and ai_result.get("total"):
                    self.valor_total = f"{ai_result['total']:.2f}"
                if not self.combustivel and ai_result.get("fuel_type"):
                    self.combustivel = ai_result["fuel_type"]
                if not self.data_abastecimento and ai_result.get("date"):
                    self.data_abastecimento = ai_result["date"]

            # Validar
            user_data = self._build_data()
            validation = FuelService.validate_data(user_data, ai_result)
            self.validation_errors = validation["errors"]
            self.validation_warnings = validation["warnings"]
            self.ai_verified = validation["ai_verified"]
            self.ai_attempt_count += 1
            self.analysis_done = True
            self.is_analyzing = False

            if validation["valid"] and ai_result:
                yield rx.toast("✅ Nota fiscal verificada pela IA!", position="top-center")
            elif not validation["valid"]:
                yield rx.toast(
                    "⚠️ Divergência encontrada — verifique os campos.", position="top-center"
                )
            else:
                yield rx.toast("ℹ️ Análise concluída. Verifique os avisos.", position="top-center")

    # ── Submit ─────────────────────────────────────────────────────────────────

    @rx.event(background=True)
    async def submit_reembolso(self):
        """
        Background event: salva reembolso no Supabase, gera PDF, faz upload.
        Estrutura de fases idêntica ao submit_rdo (benchmark).
        try/finally garante que is_submitting sempre é limpo.
        """
        import asyncio
        import threading

        loop = asyncio.get_running_loop()

        # FASE 1: mostrar loading
        async with self:
            self.is_submitting = True

        try:
            # FASE 2: coletar dados + usuário
            data = {}
            current_user = ""
            image_b64 = ""
            image_mime = "image/jpeg"
            ai_override_flag = False
            async with self:
                from bomtempo.state.global_state import GlobalState

                gs = await self.get_state(GlobalState)
                current_user = str(gs.current_user_name)
                data = self._build_data()
                data["submitted_by"] = current_user
                image_b64 = str(self.image_b64)
                image_mime = str(self.image_mime)
                ai_override_flag = bool(self.ai_override)

            # Adiciona nota de override no insight text
            if ai_override_flag:
                existing = data.get("ai_insight_text", "") or ""
                note = "NOTA: Usuário enviou com divergência IA (override manual)."
                data["ai_insight_text"] = f"{existing} | {note}".strip(" | ")

            # Validação básica
            if not data.get("valor_total") or not data.get("combustivel"):
                async with self:
                    yield rx.toast(
                        "⚠️ Preencha ao menos Combustível e Valor Total.", position="top-center"
                    )
                return

            # FASE 3: salvar no banco
            id_fr: str = ""
            try:
                id_fr = await loop.run_in_executor(
                    None, lambda: FuelService.save_to_database(data, submitted_by=current_user)
                )
                logger.info(f"✅ FR save_to_database: {id_fr}")
            except Exception as e:
                logger.error(f"❌ FR save_to_database: {e}", exc_info=True)

            if not id_fr:
                async with self:
                    yield rx.toast("❌ Erro ao salvar no banco de dados.", position="top-center")
                return

            # FASE 4: upload da imagem (se houver)
            if image_b64:
                try:
                    await loop.run_in_executor(
                        None,
                        lambda: FuelService.upload_image_to_storage(image_b64, id_fr, image_mime),
                    )
                    logger.info(f"✅ FR image uploaded for {id_fr}")
                except Exception as e:
                    logger.warning(f"⚠️ FR image upload: {e}")

            # FASE 5: gerar PDF
            pdf_path: str = ""
            try:
                result = await loop.run_in_executor(
                    None, lambda: FuelService.generate_pdf(data, id_fr=id_fr)
                )
                pdf_path = result[0] if result else ""
                logger.info(f"✅ FR generate_pdf: {pdf_path}")
            except Exception as e:
                logger.error(f"⚠️ FR generate_pdf: {e}")

            # FASE 6: upload PDF ao Storage
            if pdf_path:
                try:
                    await loop.run_in_executor(
                        None, lambda: FuelService.upload_pdf_to_storage(pdf_path, id_fr)
                    )
                    logger.info(f"✅ FR PDF uploaded for {id_fr}")
                except Exception as e:
                    logger.warning(f"⚠️ FR PDF upload: {e}")

            # FASE 6.5: email de notificação (fire-and-forget)
            final_pdf = str(pdf_path)
            final_data = dict(data)

            def _send_email_fr():
                try:
                    from bomtempo.core.email_service import EmailService

                    recipients = FuelService.get_notification_emails()
                    if recipients:
                        EmailService.send_reembolso_email(recipients, final_data, final_pdf)
                except Exception as ex:
                    logger.warning(f"⚠️ FR email send: {ex}")

            threading.Thread(target=_send_email_fr, daemon=True).start()

            # FASE 7: sucesso
            async with self:
                self.reset_form()
                self.submit_success = True
                yield rx.toast("✅ Reembolso enviado com sucesso!", position="top-center")
                yield rx.redirect("/reembolso")

        except Exception as e:
            logger.error(f"❌ FR submit_reembolso inesperado: {e}", exc_info=True)
            async with self:
                yield rx.toast("❌ Erro inesperado. Tente novamente.", position="top-center")
        finally:
            async with self:
                self.is_submitting = False

    # ── Dashboard load ──────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_record(r: dict) -> dict:
        """
        Pré-formata campos para uso em rx.foreach (Vars não suportam slicing Python).
        Adiciona date_short, formata valores numéricos como strings.
        """
        raw_date = str(r.get("created_at") or "")
        total_v = r.get("total_value")
        kml_v = r.get("km_per_liter")
        ckm_v = r.get("cost_per_km")
        dev_v = r.get("deviation_from_fleet_avg")
        return {
            **r,
            "date_short": raw_date[:10] if len(raw_date) >= 10 else raw_date,
            "total_value": f"{float(total_v):.2f}" if total_v is not None else "",
            "km_per_liter": f"{float(kml_v):.2f}" if kml_v is not None else "",
            "cost_per_km": f"{float(ckm_v):.4f}" if ckm_v is not None else "",
            "deviation_from_fleet_avg": f"{float(dev_v):.1f}" if dev_v is not None else "",
            "ai_verified": bool(r.get("ai_verified", False)),
            "pdf_report_url": str(r.get("pdf_report_url") or ""),
            "receipt_image_url": str(r.get("receipt_image_url") or ""),
            "id": str(r.get("id") or ""),
            "fuel_type": str(r.get("fuel_type") or ""),
            "purpose": str(r.get("purpose") or ""),
            "city": str(r.get("city") or ""),
        }

    async def load_dashboard(self):
        """Carrega dados do dashboard admin."""
        self.dash_is_loading = True
        yield
        import asyncio

        await asyncio.sleep(1)  # Sincronismo visual forçado / UX
        loop = asyncio.get_running_loop()

        try:
            records = await loop.run_in_executor(None, FuelService.get_all_reimbursements)

            if self.dash_filtro_projeto != "Todos os Motivos":
                records = [
                    r
                    for r in (records or [])
                    if self.dash_filtro_projeto.lower() in str(r.get("purpose", "")).lower()
                ]

            if self.dash_filtro_contrato != "Todos os Contratos":
                records = [
                    r
                    for r in (records or [])
                    if self.dash_filtro_contrato.lower() in str(r.get("city", "")).lower()
                ]  # Adaptado pois Finalidade é City/Rotas/Purpose

            self.reembolsos_list = [self._normalize_record(r) for r in (records or [])]

            # KPIs
            total_gasto = sum(float(r.get("total_value") or 0) for r in records)
            kml_vals = [float(r.get("km_per_liter") or 0) for r in records if r.get("km_per_liter")]
            ckm_vals = [float(r.get("cost_per_km") or 0) for r in records if r.get("cost_per_km")]

            self.dash_total_gasto = round(total_gasto, 2)
            self.dash_media_kml = round(sum(kml_vals) / len(kml_vals), 2) if kml_vals else 0.0
            self.dash_media_custo_km = round(sum(ckm_vals) / len(ckm_vals), 4) if ckm_vals else 0.0
            self.dash_total_registros = len(records)

            # Gráfico mensal: agrupa por mês (YYYY-MM)
            from collections import defaultdict

            mensal: dict = defaultdict(float)
            combustivel_count: dict = defaultdict(float)
            alertas = []
            for r in records or []:
                raw_date = str(r.get("created_at") or "")
                mes = raw_date[:7] if len(raw_date) >= 7 else "?"
                mensal[mes] += float(r.get("total_value") or 0)
                fuel = str(r.get("fuel_type") or "Outro")
                combustivel_count[fuel] += 1
                dev = float(r.get("deviation_from_fleet_avg") or 0)
                if abs(dev) > 30:
                    alertas.append(self._normalize_record(r))

            self.dash_chart_mensal = [
                {"mes": k, "total": round(v, 2)} for k, v in sorted(mensal.items())
            ]
            fuel_colors = {
                "Gasolina": "#FACC15",  # Yellow distinct
                "Gasolina Aditivada": "#EF4444",  # Red
                "Etanol": "#10B981",  # Green
                "Diesel": "#8B5CF6",  # Purple
                "Diesel S10": "#3B82F6",  # Blue
                "GNV": "#F97316",  # Orange
            }
            self.dash_chart_combustivel = [
                {"name": k, "value": int(v), "fill": fuel_colors.get(k, "#94A3B8")}
                for k, v in combustivel_count.items()
            ]
            self.dash_alertas = alertas
        except Exception as e:
            logger.error(f"❌ FR load_dashboard: {e}")
        finally:
            self.dash_is_loading = False

    async def load_my_reimbursements(self):
        """Carrega reembolsos do usuário logado."""
        import asyncio

        loop = asyncio.get_running_loop()

        try:
            from bomtempo.state.global_state import GlobalState

            gs = await self.get_state(GlobalState)
            username = str(gs.current_user_name)

            records = await loop.run_in_executor(
                None, lambda: FuelService.get_reimbursements_by_user(username)
            )
            self.reembolsos_list = [self._normalize_record(r) for r in (records or [])]
        except Exception as e:
            logger.error(f"❌ FR load_my_reimbursements: {e}")

    # ── Email management ─────────────────────────────────────────────────────

    @staticmethod
    def _normalize_email_record(r: dict) -> dict:
        """Normaliza registro de email para uso em rx.foreach."""
        return {
            "contract": str(r.get("contract") or ""),
            "email": str(r.get("email") or ""),
            "module": str(r.get("module") or "reembolso"),
            "created_by": str(r.get("created_by") or ""),
            "updated_date": str(r.get("updated_date") or ""),
        }

    async def load_emails(self):
        """Carrega lista de emails de notificação (module='reembolso')."""
        self.email_is_loading = True
        yield
        import asyncio

        loop = asyncio.get_running_loop()
        try:
            records = await loop.run_in_executor(None, FuelService.get_email_records)
            self.email_list = [self._normalize_email_record(r) for r in (records or [])]
        except Exception as e:
            logger.error(f"❌ load_emails: {e}")
        finally:
            self.email_is_loading = False

    async def add_email(self):
        """Adiciona email à lista de notificação."""
        import asyncio

        loop = asyncio.get_running_loop()

        contract = str(self.email_new_contract).strip()
        email_addr = str(self.email_new_address).strip()
        if not contract or not email_addr:
            yield rx.toast("⚠️ Preencha contrato e email.", position="top-center")
            return

        try:
            from bomtempo.state.global_state import GlobalState

            gs = await self.get_state(GlobalState)
            created_by = str(gs.current_user_name)
        except Exception:
            created_by = "admin"

        ok = await loop.run_in_executor(
            None, lambda: FuelService.add_notification_email(contract, email_addr, created_by)
        )
        if ok:
            self.email_new_contract = ""
            self.email_new_address = ""
            records = await loop.run_in_executor(None, FuelService.get_email_records)
            self.email_list = [self._normalize_email_record(r) for r in (records or [])]
            yield rx.toast("✅ Email adicionado com sucesso.", position="top-center")
        else:
            yield rx.toast("❌ Erro ao adicionar email.", position="top-center")

    async def delete_email(self, contract: str, email: str):
        """Remove email da lista de notificação."""
        import asyncio

        loop = asyncio.get_running_loop()

        ok = await loop.run_in_executor(
            None, lambda: FuelService.delete_notification_email(contract, email)
        )
        if ok:
            records = await loop.run_in_executor(None, FuelService.get_email_records)
            self.email_list = [self._normalize_email_record(r) for r in (records or [])]
            yield rx.toast("✅ Email removido.", position="top-center")
        else:
            yield rx.toast("❌ Erro ao remover email.", position="top-center")
