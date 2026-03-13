"""
RDO State - Formulário e Wizard
"""

from datetime import datetime
from typing import Any, Dict, List

import reflex as rx

from bomtempo.core.email_service import EmailService
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.rdo_service import RDOService
from bomtempo.core.audit_logger import audit_log, audit_error, AuditCategory

logger = get_logger(__name__)


class RDOState(rx.State):
    """Estado do formulário RDO"""

    # ── Wizard Control ────────────────────────────────────────
    current_step: int = 1  # 1-5 (Cabeçalho → Materiais)
    is_preview: bool = False
    is_submitting: bool = False

    # ── Cabeçalho (Step 1) ────────────────────────────────────
    rdo_data: str = datetime.now().strftime("%Y-%m-%d")
    rdo_contrato: str = ""
    rdo_projeto: str = ""
    rdo_cliente: str = ""
    rdo_localizacao: str = ""
    rdo_clima: str = "Ensolarado"
    rdo_turno: str = "Diurno"
    rdo_hora_inicio: str = "07:00"
    rdo_hora_termino: str = "17:00"
    rdo_houve_interrupcao: bool = False
    rdo_motivo_interrupcao: str = ""
    rdo_observacoes: str = ""

    # ── Listas Dinâmicas (Steps 2-5) ─────────────────────────
    mao_obra_items: List[Dict[str, Any]] = []
    equipamentos_items: List[Dict[str, Any]] = []
    atividades_items: List[Dict[str, Any]] = []
    materiais_items: List[Dict[str, Any]] = []

    # ── Temp Input Vars (Steps 2-5) ──────────────────────────
    mo_funcao: str = ""
    mo_qtd: str = ""
    mo_obs: str = ""
    eq_desc: str = ""
    eq_qtd: str = ""
    eq_status: str = "Operando"
    at_desc: str = ""
    at_pct: str = "100"
    mt_desc: str = ""
    mt_qtd: str = ""
    mt_unid: str = "un"

    # ── Preview & Submit ──────────────────────────────────────
    preview_pdf_path: str = ""
    preview_pdf_url: str = ""  # data: URL (base64) para iframe
    form_errors: Dict[str, str] = {}
    is_generating_preview: bool = False

    # ── Helpers ───────────────────────────────────────────────

    def next_step(self):
        """Avança wizard"""
        if self.current_step < 5:
            self.current_step += 1

    def prev_step(self):
        """Retorna wizard"""
        if self.current_step > 1:
            self.current_step -= 1

    def go_to_step(self, step: int):
        """Vai para step específico"""
        if 1 <= step <= 5:
            self.current_step = step

    # ── Mão de Obra ───────────────────────────────────────────

    def add_mo(self):
        """Adiciona mão de obra a partir dos campos temporários"""
        if self.mo_funcao.strip():
            # Reatribuição completa garante detecção de mudança pelo Reflex
            self.mao_obra_items = [
                *self.mao_obra_items,
                {
                    "funcao": self.mo_funcao.strip(),
                    "quantidade": self.mo_qtd.strip(),
                    "obs": self.mo_obs.strip(),
                },
            ]
            self.mo_funcao = ""
            self.mo_qtd = ""
            self.mo_obs = ""

    def remove_mao_obra(self, index: int):
        """Remove item da lista"""
        self.mao_obra_items = [item for i, item in enumerate(self.mao_obra_items) if i != index]

    # ── Equipamentos ──────────────────────────────────────────

    def add_eq(self):
        """Adiciona equipamento a partir dos campos temporários"""
        if self.eq_desc.strip():
            self.equipamentos_items = [
                *self.equipamentos_items,
                {
                    "descricao": self.eq_desc.strip(),
                    "quantidade": self.eq_qtd.strip(),
                    "status": self.eq_status,
                },
            ]
            self.eq_desc = ""
            self.eq_qtd = ""
            self.eq_status = "Operando"

    def remove_equipamento(self, index: int):
        """Remove equipamento"""
        self.equipamentos_items = [
            item for i, item in enumerate(self.equipamentos_items) if i != index
        ]

    # ── Atividades ────────────────────────────────────────────

    def add_at(self):
        """Adiciona atividade a partir dos campos temporários"""
        if self.at_desc.strip():
            self.atividades_items = [
                *self.atividades_items,
                {
                    "atividade": self.at_desc.strip(),
                    "percentual": self.at_pct.strip(),
                },
            ]
            self.at_desc = ""
            self.at_pct = "100"

    def remove_atividade(self, index: int):
        """Remove atividade"""
        self.atividades_items = [item for i, item in enumerate(self.atividades_items) if i != index]

    # ── Materiais ─────────────────────────────────────────────

    def add_mt(self):
        """Adiciona material a partir dos campos temporários"""
        if self.mt_desc.strip():
            self.materiais_items = [
                *self.materiais_items,
                {
                    "descricao": self.mt_desc.strip(),
                    "quantidade": self.mt_qtd.strip(),
                    "unidade": self.mt_unid,
                },
            ]
            self.mt_desc = ""
            self.mt_qtd = ""
            self.mt_unid = "un"

    def remove_material(self, index: int):
        """Remove material"""
        self.materiais_items = [item for i, item in enumerate(self.materiais_items) if i != index]

    # ── Validação ─────────────────────────────────────────────

    def validate_form(self) -> bool:
        """Valida campos obrigatórios"""
        errors = {}

        if not self.rdo_contrato.strip():
            errors["contrato"] = "Contrato é obrigatório"
        if not self.rdo_data:
            errors["data"] = "Data é obrigatória"

        self.form_errors = errors
        return len(errors) == 0

    # ── Build RDO Data ────────────────────────────────────────

    def _build_rdo_data(self) -> Dict[str, Any]:
        """Compila todos os dados do formulário - converte Vars para valores reais"""
        return {
            # Cabeçalho - converter Vars para strings
            "data": str(self.rdo_data),
            "contrato": str(self.rdo_contrato),
            "projeto": str(self.rdo_projeto),
            "cliente": str(self.rdo_cliente),
            "localizacao": str(self.rdo_localizacao),
            "clima": str(self.rdo_clima),
            "turno": str(self.rdo_turno),
            "hora_inicio": str(self.rdo_hora_inicio),
            "hora_termino": str(self.rdo_hora_termino),
            "houve_interrupcao": bool(self.rdo_houve_interrupcao),
            "motivo_interrupcao": str(self.rdo_motivo_interrupcao),
            "observacoes": str(self.rdo_observacoes),
            # Listas - já são listas Python normais
            "mao_obra": list(self.mao_obra_items),
            "equipamentos": list(self.equipamentos_items),
            "atividades": list(self.atividades_items),
            "materiais": list(self.materiais_items),
        }

    # ── Preview ───────────────────────────────────────────────

    @rx.event(background=True)
    async def generate_preview(self):
        """Gera preview do PDF — background event para não travar a UI."""
        import asyncio
        import base64

        # Fase 1: validar + capturar dados dentro do lock
        rdo_data = None
        async with self:
            if self.validate_form():
                self.is_generating_preview = True
                rdo_data = self._build_rdo_data()

        if rdo_data is None:
            yield rx.toast("⚠️ Preencha os campos obrigatórios (Contrato e Data)", position="top-center")
            return

        # Fase 2: gerar PDF FORA do lock (I/O bloqueante)
        try:
            loop = asyncio.get_running_loop()
            pdf_path, pdf_url = await loop.run_in_executor(
                None,
                lambda: RDOService.generate_pdf(rdo_data, is_preview=True),
            )

            if pdf_path:
                with open(pdf_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                async with self:
                    self.preview_pdf_path = pdf_path
                    self.preview_pdf_url = f"data:application/pdf;base64,{b64}"
                    self.is_preview = True
                    self.is_generating_preview = False
            else:
                async with self:
                    self.is_generating_preview = False
                yield rx.toast("❌ Erro ao gerar preview do PDF", position="top-center")

        except Exception as e:
            logger.error(f"Erro ao gerar preview: {e}")
            async with self:
                self.is_generating_preview = False
            yield rx.toast(f"❌ Erro: {str(e)[:120]}", position="top-center")

    def edit_form(self):
        """Volta para o formulário mantendo dados — retorna ao step 5 (último preenchido)"""
        self.is_preview = False
        self.current_step = 5

    # ── Submit ────────────────────────────────────────────────
    # Versão: 2026-02-23T13:44 — Two-handler chain pattern.
    # submit_rdo → sets is_submitting → yields execute_submit.
    # Reflex sends state delta to client BEFORE running execute_submit.

    async def submit_rdo(self):
        """
        Handler 1/2: Mostra loading IMEDIATAMENTE, depois dispara
        execute_submit como evento separado.
        """
        if self.is_submitting:
            return
        self.is_submitting = True
        yield RDOState.execute_submit

    @rx.event(background=True)
    async def execute_submit(self):
        """
        Handler 2/2: BACKGROUND event — loading já está visível.
        Background é OBRIGATÓRIO para não bloquear o event loop do Reflex
        e evitar websocket timeout. Usa 'async with self' para cada
        mutação de estado.
        """
        import asyncio
        import threading

        logger.info("🚀 execute_submit INÍCIO (background)")

        try:
            loop = asyncio.get_running_loop()

            # Coletar dados (precisa de state lock)
            async with self:
                from bomtempo.state.global_state import GlobalState

                gs = await self.get_state(GlobalState)
                user_name = str(gs.current_user_name)
                rdo_data = self._build_rdo_data()
            logger.info(f"📋 dados coletados, contrato={rdo_data.get('contrato')}")

            # Salvar no banco (executor — não bloqueia event loop)
            id_rdo = await loop.run_in_executor(
                None,
                lambda: RDOService.save_to_database(rdo_data, submitted_by=user_name),
            )
            logger.info(f"💾 DB → {id_rdo}")
            if not id_rdo:
                async with self:
                    self.is_submitting = False
                    yield rx.toast("❌ Erro ao salvar no banco", position="top-center")
                return

            # Gerar PDF (executor)
            pdf_path = ""
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: RDOService.generate_pdf(rdo_data, is_preview=False, id_rdo=id_rdo),
                )
                pdf_path = result[0] if result and result[0] else ""
                logger.info(f"📄 PDF → {pdf_path}")
            except Exception as e:
                logger.error(f"⚠️ PDF falhou: {e}")

            # Upload para Storage (executor)
            if pdf_path:
                try:
                    url = await loop.run_in_executor(
                        None,
                        lambda: RDOService.upload_pdf_to_storage(pdf_path, id_rdo),
                    )
                    if url:
                        await loop.run_in_executor(
                            None,
                            lambda: RDOService.update_pdf_info(id_rdo, url),
                        )
                        logger.info(f"☁️ Storage → {url}")
                    else:
                        logger.warning("⚠️ Storage retornou URL vazia")
                except Exception as e:
                    logger.warning(f"⚠️ Storage: {e}")

            # Buscar destinatários (executor)
            recipients = []
            try:
                from bomtempo.core.supabase_client import sb_select

                contrato = rdo_data.get("contrato", "")
                rows = await loop.run_in_executor(
                    None,
                    lambda: sb_select("email_sender", filters={"contract": contrato}),
                )
                recipients = [
                    r.get("email", "").strip() for r in (rows or []) if r.get("email", "").strip()
                ]
                logger.info(f"📧 Recipients → {recipients}")
            except Exception as e:
                logger.error(f"⚠️ Recipients: {e}")

            # Email (daemon thread — fire-and-forget)
            if recipients and pdf_path:
                _d, _p, _r = dict(rdo_data), str(pdf_path), list(recipients)

                def _email():
                    try:
                        ai = RDOService.analyze_with_ai(_d)
                        ok = EmailService.send_rdo_email(_r, _d, _p, ai)
                        logger.info(f"✅ Email {'OK' if ok else 'FALHOU'} → {_r}")
                    except Exception as exc:
                        logger.error(f"❌ Email: {exc}")

                threading.Thread(target=_email, daemon=True).start()
                toast_msg = (
                    f"✅ RDO salvo! Email enviando para {len(recipients)} destinatário(s)..."
                )
            else:
                toast_msg = "✅ RDO salvo com sucesso!"

            # Sucesso — reset + redirect
            logger.info(f"🎯 COMPLETO: {id_rdo}")
            audit_log(
                category=AuditCategory.RDO_CREATE,
                action=f"RDO criado — contrato '{rdo_data.get('contrato', '')}' por '{user_name}'",
                username=user_name,
                entity_type="rdo",
                entity_id=str(id_rdo),
                metadata={"contrato": rdo_data.get("contrato", ""), "data": rdo_data.get("data", "")},
                status="success",
            )
            async with self:
                self._reset_form()
                self.is_submitting = False
                yield rx.toast(toast_msg, position="top-center")
                yield rx.redirect("/rdo-historico")

        except Exception as e:
            logger.error(f"❌ execute_submit ERRO: {e}", exc_info=True)
            audit_error(
                action=f"Falha ao submeter RDO",
                username=user_name if "user_name" in dir() else "unknown",
                entity_type="rdo",
                error=e,
            )
            async with self:
                self.is_submitting = False
                yield rx.toast(f"❌ Erro: {str(e)[:80]}", position="top-center")

    # ── Pre-fill from user profile ────────────────────────────

    async def init_from_user_profile(self):
        """
        Pré-preenche campos com dados do contrato associado ao usuário logado.
        Estratégia de fallback:
          1. Preenche rdo_contrato de current_user_contrato
          2. Tenta encontrar detalhes em contratos_list (se já carregou)
          3. Fallback: busca último RDO deste contrato no Supabase rdo_cabecalho
        """
        from bomtempo.state.global_state import GlobalState

        gs = await self.get_state(GlobalState)
        contrato = str(gs.current_user_contrato).strip()

        if not contrato or contrato in ("nan", "None"):
            logger.info("⚠️ init_from_user_profile: sem contrato no perfil do usuário")
            return

        # Só pré-preenche se o form está vazio (evita sobrescrever edição manual)
        if self.rdo_contrato.strip():
            return

        self.rdo_contrato = contrato
        filled = False

        # Estratégia 1: contratos_list já carregada
        for c in gs.contratos_list or []:
            ctr = str(c.get("contrato", "")).strip()
            if ctr == contrato:
                projeto = str(c.get("projeto", "") or c.get("nome_projeto", "") or "")
                cliente = str(c.get("cliente", "") or c.get("nome_cliente", "") or "")
                loc = str(
                    c.get("cidade", "") or c.get("localizacao", "") or c.get("endereco", "") or ""
                )
                if projeto and projeto != "nan":
                    self.rdo_projeto = projeto
                if cliente and cliente != "nan":
                    self.rdo_cliente = cliente
                if loc and loc != "nan":
                    self.rdo_localizacao = loc
                filled = True
                logger.info(f"✅ RDO pré-preenchido via contratos_list: {contrato}")
                break

        # Estratégia 2 (fallback): buscar último RDO deste contrato no Supabase
        if not filled:
            try:
                from bomtempo.core.supabase_client import sb_select

                rdos = sb_select(
                    "rdo_cabecalho",
                    filters={"Contrato": contrato},
                    order="ID_RDO.desc",
                    limit=1,
                )
                if rdos:
                    last = rdos[0]
                    projeto = str(last.get("Projeto", "") or "")
                    cliente = str(last.get("Cliente", "") or "")
                    loc = str(last.get("Localizacao", "") or "")
                    if projeto and projeto != "nan":
                        self.rdo_projeto = projeto
                    if cliente and cliente != "nan":
                        self.rdo_cliente = cliente
                    if loc and loc != "nan":
                        self.rdo_localizacao = loc
                    logger.info(f"✅ RDO pré-preenchido via último RDO Supabase: {contrato}")
                else:
                    logger.info(f"⚠️ Nenhum RDO anterior encontrado para contrato={contrato}")
            except Exception as e:
                logger.warning(f"⚠️ Fallback Supabase para auto-fill falhou: {e}")

    def _reset_form(self):
        """Limpa formulário completo após envio"""
        from datetime import datetime

        # Wizard
        self.current_step = 1
        self.is_preview = False
        self.form_errors = {}
        # Cabeçalho (Step 1)
        self.rdo_data = datetime.now().strftime("%Y-%m-%d")
        self.rdo_contrato = ""
        self.rdo_projeto = ""
        self.rdo_cliente = ""
        self.rdo_localizacao = ""
        self.rdo_clima = "Ensolarado"
        self.rdo_turno = "Diurno"
        self.rdo_hora_inicio = "07:00"
        self.rdo_hora_termino = "17:00"
        self.rdo_houve_interrupcao = False
        self.rdo_motivo_interrupcao = ""
        self.rdo_observacoes = ""
        # Listas
        self.mao_obra_items = []
        self.equipamentos_items = []
        self.atividades_items = []
        self.materiais_items = []
        # PDF
        self.preview_pdf_path = ""
        self.preview_pdf_url = ""
        # Temp inputs
        self.mo_funcao = ""
        self.mo_qtd = ""
        self.mo_obs = ""
        self.eq_desc = ""
        self.eq_qtd = ""
        self.eq_status = "Operando"
        self.at_desc = ""
        self.at_pct = "100"
        self.mt_desc = ""
        self.mt_qtd = ""
        self.mt_unid = "un"
