"""
Global State Management
"""

import asyncio
import base64
import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import reflex as rx

from bomtempo.core import weather_api
from bomtempo.core.ai_client import ai_client
from bomtempo.core.ai_context import AIContext
from bomtempo.core.analysis_service import AnalysisService
from bomtempo.core.data_loader import DataLoader
from bomtempo.core.logging_utils import get_logger
from bomtempo.core.audit_logger import audit_log, audit_error, AuditCategory
from bomtempo.core.supabase_client import sb_select, sb_insert, sb_rpc
from bomtempo.core.ai_tools import AI_TOOLS, execute_tool

logger = get_logger(__name__)


def _msg(role: str, content: str, chart_json: str = "", chart_id: str = "") -> dict:
    """Cria um dict de mensagem com todos os campos esperados pelo chat_bubble."""
    return {"role": role, "content": content, "chart_json": chart_json, "chart_id": chart_id}


class GlobalState(rx.State):
    """Estado global da aplicação"""

    # --- AI & Voice Chat State ---
    chat_history: list[dict] = []
    chat_input: str = ""
    current_question: str = ""
    is_processing_chat: bool = False
    chat_tool_label: str = ""   # Status interno da tool em execução (exibido no typing indicator)
    chat_session_id: str = ""

    # Gráfico pendente — preenchido quando IA chama generate_chart_data
    # Injetado como campo "chart_json" na mensagem final antes de limpar
    _pending_chart_json: str = ""  # JSON serializado do gráfico

    # Conversation Mode (Hands-Free)
    is_recording: bool = False  # Legacy compatibility
    is_talking_mode: bool = False
    is_recording_voice: bool = False
    is_processing_voice: bool = False
    is_listening: bool = True  # Ready for next loop
    is_speaking: bool = False  # UI State for "AI Speaking"
    latest_audio_src: str = ""
    last_spoken_response: str = ""  # Subtitles/Legenda

    async def ensure_data_loaded(self):
        """Lazy load data if not present"""
        if not self._data:
            loader = DataLoader()
            self._data = loader.load_all()

    async def _perform_ai_query(self, _question: str):
        """Unified context-aware AI logic for both Desk/Mobile and Text/Voice chat."""
        # Visual feedback
        yield rx.toast("Processando...", position="top-center")

        try:
            # CRITICAL: Ensure data is loaded for context
            await self.ensure_data_loaded()

            # Prepare context
            dashboard_context = AIContext.get_dashboard_context(self._data)

            # Detect Mobile User (Role-based)
            is_mobile = self.current_user_role == "Gestão-Mobile"
            system_prompt = AIContext.get_system_prompt(is_mobile=is_mobile)

            # Build messages with focus on context and history
            messages = [{"role": "system", "content": f"{system_prompt}\n\n{dashboard_context}"}]

            # Add recent history (last 6 messages)
            history_msgs = [
                {"role": m["role"], "content": m["content"]} for m in self.chat_history[-6:]
            ]
            messages.extend(history_msgs)

            response_content = ai_client.query(messages)

            self.chat_history.append(_msg("assistant", response_content))

            # Handle TTS if in Talking Mode
            if self.is_talking_mode:
                self.last_spoken_response = response_content
                from bomtempo.core.tts_service import TTSService

                logger.info("Starting TTS generation...")
                audio_path = TTSService.generate_speech(response_content)
                if audio_path:
                    import time

                    final_url = f"{audio_path}?t={int(time.time())}"
                    self.latest_audio_src = final_url
                    self.is_speaking = True
                    yield rx.call_script(
                        f"if(window.playResponseAudio) window.playResponseAudio('{final_url}')"
                    )
                else:
                    self.last_spoken_response += "\n\n(⚠️ Falha na geração de áudio.)"

            # Auto-scroll after AI response
            yield rx.call_script("window.scrollToBottom('chat-container')")

        except Exception as e:
            logger.error(f"Erro no chat: {e}")
            self.chat_history.append(_msg("assistant", "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."))
            yield rx.toast("Erro ao processar mensagem.", position="top-center")
        finally:
            self.is_processing_chat = False
            self.current_question = ""
            yield rx.call_script("window.clearChatInput()")

    async def send_message(self):
        """Envia mensagem para a IA e processa resposta com streaming real."""
        question = self.current_question
        if not question.strip():
            return

        self.chat_history.append(_msg("user", question))
        self.current_question = ""
        self.is_processing_chat = True
        yield rx.call_script("window.scrollToBottom('chat-container')")
        yield GlobalState.stream_chat_bg

    async def load_chat_history(self):
        """Abre o chat sempre com sessão limpa. O banco existe só para contexto da IA."""
        username = self.current_user_name or "anonymous"
        # Sempre cria nova sessão ao entrar na página
        new_sess = sb_insert("chat_sessions", {"title": "Conversa", "username": username})
        if new_sess:
            self.chat_session_id = new_sess["id"]
        self.chat_history = [_msg("assistant", "👋 Olá! Sou o Bomtempo Intelligence. Como posso ajudar com seus dados hoje?")]
        self.is_processing_chat = False
        yield rx.call_script("setTimeout(function(){ window.scrollToBottom('chat-container'); }, 150);")

    async def new_conversation(self):
        """Inicia uma nova conversa — cria nova sessão no banco e limpa o histórico local."""
        username = self.current_user_name or "anonymous"
        new_sess = sb_insert("chat_sessions", {"title": "Conversa", "username": username})
        if new_sess:
            self.chat_session_id = new_sess["id"]
        self.chat_history = [_msg("assistant", "👋 Conversa reiniciada! Como posso ajudar?")]
        self.is_processing_chat = False
        yield rx.call_script("window.scrollToBottom('chat-container')")

    def save_chat_msg(self, role: str, content: str, tool_calls: any = None, tool_call_id: str = None):
        """Salva uma mensagem no banco de dados de forma assíncrona (fire-and-forget)."""
        if not self.chat_session_id: return
        data = {
            "session_id": self.chat_session_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id
        }
        try:
            sb_insert("chat_messages", data)
            # Atualiza timestamp da sessão
            sb_rpc("update_session_timestamp", {"sess_id": self.chat_session_id})
        except: pass

    @rx.event(background=True)
    async def stream_chat_bg(self):
        """Loop Agêntico com suporte a Tools e persistência."""
        import time

        async with self:
            # A última mensagem do usuário é agora a última do histórico (sem placeholder)
            question = self.chat_history[-1]["content"] if self.chat_history and self.chat_history[-1]["role"] == "user" else ""
            is_mobile = self.current_user_role == "Gestão-Mobile"
            self.save_chat_msg("user", question)
            
        system_prompt = AIContext.get_system_prompt(is_mobile=is_mobile)

        # Injeta dados reais do painel (contexto do dashboard) + schema para o agente
        # Os dados do painel dão awareness imediata; o schema permite queries precisas
        async with self:
            if not self._data:
                loader = DataLoader()
                self._data = loader.load_all()
            data_snapshot = self._data  # lê dentro do lock

        dashboard_context = AIContext.get_dashboard_context(data_snapshot)
        schema_context = sb_rpc("get_schema_context")

        messages = [{
            "role": "system",
            "content": (
                system_prompt
                + dashboard_context
                + f"\n\n## SCHEMA DO BANCO (para queries SQL)\n{schema_context}"
            ),
        }]
        
        async with self:
            history = [m for m in self.chat_history if m["content"]][-6:]
        messages.extend(history)

        # LOOP AGÊNTICO
        max_iterations = 5
        pending_chart_json = ""
        pending_chart_id = ""
        for i in range(max_iterations):
            # force_tool=True na primeira iteração evita que a IA "anuncie" antes de agir
            response = ai_client.query_agentic(messages, tools=AI_TOOLS, force_tool=(i == 0))

            if isinstance(response, str):
                final_content = re.sub(r'!\[.*?\]\(.*?\)', '', response).strip()
                async with self:
                    self.chat_history.append(_msg("assistant", final_content, chart_json=pending_chart_json, chart_id=pending_chart_id))
                    self.save_chat_msg("assistant", final_content)
                    self.is_processing_chat = False
                    self.chat_tool_label = ""
                    self._pending_chart_json = ""
                    if pending_chart_json and pending_chart_id:
                        safe_json = pending_chart_json.replace("`", "\\`")
                        yield rx.call_script(
                            f"window.__btpCharts = window.__btpCharts || {{}}; "
                            f"window.__btpCharts['{pending_chart_id}'] = {safe_json};"
                        )
                    yield rx.call_script("window.scrollToBottom('chat-container')")
                break

            # tool_call — serializa como dict para a API
            tool_calls = response.tool_calls
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tool_call in tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                # Atualiza label interno — exibido no typing_indicator, não no chat
                async with self:
                    self.chat_tool_label = "gerando gráfico..." if name == "generate_chart_data" else "consultando banco..."

                result = execute_tool(name, args)

                if name == "generate_chart_data":
                    try:
                        parsed = json.loads(result)
                        if parsed.get("__chart__"):
                            pending_chart_json = result
                            pending_chart_id = f"chart_{tool_call.id.replace('-', '_')}"
                    except Exception:
                        pass

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": result,
                })
        else:
            fallback = "Não consegui concluir a análise. Tente reformular a pergunta."
            async with self:
                self.chat_history.append(_msg("assistant", fallback))
                self.is_processing_chat = False
                self.chat_tool_label = ""
                self._pending_chart_json = ""
                yield rx.call_script("window.scrollToBottom('chat-container')")

    async def process_voice_input(self, text: str):
        """Receives transcribed text — funnels through the same agentic pipeline as typed messages."""
        if not text:
            return
        self.is_recording = False
        self.is_recording_voice = False
        # Reutiliza exatamente o mesmo fluxo do send_message: agentic loop + tool calls + charts
        self.current_question = text
        async for ev in self.send_message():
            yield ev

    async def process_audio_blob(self, base64_data: str):
        """Receives base64 audio and transcribes."""
        if not base64_data:
            return
        self.is_processing_chat = True
        self.is_recording = False
        self.is_recording_voice = False
        try:
            if "," in base64_data:
                header, encoded = base64_data.split(",", 1)
            else:
                encoded = base64_data
            ext = ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(base64.b64decode(encoded))
                tmp_path = tmp_file.name
            transcript = ai_client.transcribe_audio(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            if transcript:
                self.chat_input = transcript
                await self.send_message()
            else:
                yield rx.window_alert("Não foi possível transcrever o áudio.")
                self.is_processing_chat = False
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            self.is_processing_chat = False

    def start_recording(self):
        self.is_recording = True

    def stop_recording(self):
        self.is_recording = False

    def toggle_talking_mode(self):
        self.is_talking_mode = not self.is_talking_mode
        if not self.is_talking_mode:
            self.disable_talking_mode()

    def disable_talking_mode(self):
        self.is_talking_mode = False
        self.is_recording_voice = False
        self.is_processing_voice = False
        self.is_speaking = False
        self.latest_audio_src = ""
        self.last_spoken_response = ""
        self.is_recording = False

    def toggle_voice_recording(self):
        self.is_recording_voice = not self.is_recording_voice
        self.is_recording = self.is_recording_voice
        if self.is_recording_voice:
            return rx.call_script("if(window.startRecording) window.startRecording()")

    def audio_loaded(self):
        pass

    def audio_error(self):
        self.is_speaking = False

    def audio_ended(self):
        self.is_speaking = False
        if self.is_talking_mode:
            return rx.call_script(
                "if(window.startRecording) setTimeout(() => window.startRecording(), 500)"
            )

    def inject_conversation(self, user_text: str, ai_text: str):
        """
        Updates chat history with externally processed conversation (e.g., from API).
        Used to sync UI after JS-driven Audio/Text fetch.
        """
        if user_text:
            self.chat_history.append(_msg("user", user_text))
        if ai_text:
            self.chat_history.append(_msg("assistant", ai_text))
            self.last_spoken_response = ai_text

        self.is_processing_chat = False
        self.is_listening = True  # Ready for next loop
        self.current_question = ""
        yield rx.call_script("window.clearChatInput()")
        yield rx.call_script("window.scrollToBottom('chat-container')")

    def inject_conversation_json(self, json_data: str):
        """
        Wrapper for inject_conversation that parses JSON string.
        Bound to hidden input for JS-to-Python communication.
        """
        try:
            data = json.loads(json_data)
            self.inject_conversation(data.get("user", ""), data.get("ai", ""))
        except Exception as e:
            print(f"Error injecting conversation: {e}")

    # Dados brutos
    _data: Dict[str, pd.DataFrame] = {}

    # Flags de carregamento
    is_loading: bool = False
    is_navigating: bool = False       # Feedback imediato no clique de navegação (antes do round-trip)
    initial_loading: bool = False  # Loading screen after login
    show_loading_screen: bool = False  # Full-screen loading overlay
    is_authenticating: bool = False   # Intermediate auth button state (login page)
    error_message: str = ""

    # Dados processados para UI
    contratos_list: List[Dict[str, Any]] = []
    projetos_list: List[Dict[str, Any]] = []
    obras_list: List[Dict[str, Any]] = []
    financeiro_list: List[Dict[str, Any]] = []
    om_list: List[Dict[str, Any]] = []
    users_list: List[Dict[str, Any]] = []

    # Métricas Globais
    total_contratos: int = 0
    valor_tcv: float = 0.0
    contratos_ativos: int = 0

    # Preferências de UI
    sidebar_open: bool = True
    theme_mode: str = "dark"

    # Projetos page state
    selected_contrato: str = ""
    projetos_search: str = ""
    projetos_fase_filter: str = ""

    # Obras page state
    obras_selected_contract: str = ""
    obra_insight_text: str = ""
    obra_insight_loading: bool = False
    obras_navigating: bool = False   # True while transitioning list→detail or back

    # O&M page state
    om_time_filter: str = ""  # Empty = no time filter applied

    # ── GLOBAL FILTERS (Visão Geral, O&M, Financeiro) ──────────
    global_project_filter: str = ""  # "" means "Todos"
    om_project_filter: str = ""  # "" means "Todos"
    fin_project_filter: str = ""  # "" means "Todos"

    # ── Financeiro chart cache — calculado só ao mudar dados/filtro ──────────
    # Substitui @rx.var com groupby+cumsum que rodavam em CADA render
    financeiro_cockpit_chart: List[Dict[str, Any]] = []
    financeiro_scurve_chart: List[Dict[str, Any]] = []

    # Weather State
    weather_data: Dict[str, Any] = {}
    weather_loading: bool = False
    weather_risk_level: str = "Low"

    # Analysis Service State
    current_page_kpis: Dict[str, Any] = {}
    analysis_result: str = ""
    is_analyzing: bool = False
    is_streaming: bool = False  # True while chunks arriving, False when done
    show_analysis_dialog: bool = False
    _pending_page_name: str = ""  # Used by background streaming event

    # KPI Detail Popup State
    show_kpi_detail: str = ""  # "" | "total_contratado" | "total_medido" | "saldo_medir" | "contratos_ativos" | "receita_total"

    def set_analysis_dialog_open(self, value: bool):
        self.show_analysis_dialog = value
        if not value:
            self.analysis_result = ""
            self.is_streaming = False

    def close_analysis_dialog(self):
        self.set_analysis_dialog_open(False)

    def handle_detail_open_change(self, is_open: bool):
        if not is_open:
            self.show_kpi_detail = ""

    async def analyze_current_view(self):
        """Processes current page KPIs."""
        path = self.router.url.strip("/") or "index"
        data = {}
        page_name = "Visão Geral"

        if path in ["index", "visão geral", ""]:
            page_name = "Dashboard Estratégico"
            data = {
                "Total Contratos": self.total_contratos,
                "Valor em Carteira": self.valor_carteira_formatado,
                "Avanço Físico Global": self.avanco_fisico_geral_fmt,
                "Obras em Atraso": self.obras_atrasadas_count,
                "Margem Operacional Global": self.margem_pct_fmt,
            }
        elif "obras" in path:
            page_name = "Operações de Campo"
            data = {
                "Total de Obras": self.total_obras_andamento,
                "Avanço Físico Médio": self.avanco_fisico_geral_fmt,
                "Obras em Atraso": self.obras_atrasadas_count,
            }
            if self.obras_selected_contract:
                data["Recorte"] = f"Contrato: {self.obras_selected_contract}"
                # Only add high-level summary of selected obra
                data["Status da Obra Selecionada"] = self.obra_selected_data.get(
                    "status", "Em Execução"
                )
        elif "financeiro" in path:
            page_name = "Performance Financeira"
            data = {
                "Volume Contratado": self.financeiro_contratado_fmt,
                "Volume Realizado": self.financeiro_realizado_fmt,
                "Saldo de Medição": self.margem_bruta_fmt,
                "Margem Perc.": self.margem_pct_fmt,
            }
        elif "projetos" in path:
            if self.selected_contrato:
                # Compute KPIs scoped to THIS contract from filtered activities
                acts = self.filtered_projetos
                total_acts = len(acts)
                avg_progress = round(
                    sum(float(p.get("conclusao_pct", 0) or 0) for p in acts) / max(total_acts, 1), 1
                )
                criticos = len([p for p in acts if str(p.get("critico", "")).lower() == "sim"])
                atrasados = len([
                    p for p in acts
                    if str(p.get("critico", "")).lower() == "sim"
                    and float(p.get("conclusao_pct", 0) or 0) < 100
                ])
                page_name = f"Projeto: {self.selected_contrato_data.get('cliente', self.selected_contrato)}"
                data = {
                    "Contrato": self.selected_contrato_data.get("contrato", self.selected_contrato),
                    "Status Atual": self.selected_contrato_data.get("status", "Em Execução"),
                    "Progresso Global": f"{avg_progress}%",
                    "Total de Atividades": total_acts,
                    "Marcos Críticos (total)": criticos,
                    "Marcos Críticos (pendentes)": atrasados,
                    "Atividades Concluídas": len([p for p in acts if float(p.get("conclusao_pct", 0) or 0) >= 100]),
                }
            else:
                page_name = "Gestão de Portfólio"
                data = {
                    "Total Atividades": self.total_atividades,
                    "Atividades Concluídas": self.atividades_concluidas,
                    "Caminho Crítico (Alertas)": self.atividades_criticas_count,
                }
        elif "om" in path:
            page_name = "O&M - Performance Energética"
            data = {
                "Energia Injetada (Total)": self.om_energia_injetada_fmt,
                "Performance Hidráulica/Solar": self.om_performance_fmt,
                "Faturamento Líquido": self.om_fat_liquido_fmt,
                "Geração Acumulada": self.om_acumulado_fmt,
            }
        elif "analytics" in path:
            page_name = "Análise Preditiva"
            data = {
                "Atraso Médio Estimado": f"{self.analytics_atraso_medio}%",
                "Risco de Churn": self.analytics_churn_risk,
                "Eficiência de Entrega": f"{self.analytics_conclusao_rate}%",
            }
        elif "rdo" in path:
            page_name = "Dashboard RDO Analytics"
            try:
                from bomtempo.core.rdo_service import RDOService
                from bomtempo.core.supabase_client import sb_select

                rdos = RDOService.get_all_rdos(limit=200)
                mo = sb_select("rdo_mao_obra", limit=1000) or []
                eq = sb_select("rdo_equipamentos", limit=1000) or []
                data = {
                    "Total de RDOs Emitidos": len(rdos),
                    "Obras Operando": len(
                        set(r.get("contrato") for r in rdos if r.get("contrato"))
                    ),
                    "Profissionais em Campo": sum(int(r.get("Quantidade", 0) or 0) for r in mo),
                    "Registros de Equipamentos": len(eq),
                }
            except Exception as e:
                logger.warning(f"Erro KPI RDO: {e}")
                data = {"Seção": "RDO Analytics", "Status": "Carregando RDOs..."}

        # Fallback
        if not data:
            data = {
                "Visão": "Geral da Plataforma",
                "Total Contratos": self.total_contratos,
                "Valor Carteira": self.valor_carteira_formatado,
            }

        self.current_page_kpis = data
        self._pending_page_name = page_name

        if not self.current_page_kpis:
            yield rx.window_alert("Não há dados mapeados nesta página para analisar.")
            return

        self.is_analyzing = True
        self.show_analysis_dialog = True
        self.analysis_result = ""
        yield  # flush loading state + dialog to frontend

        # Trigger background streaming event (true char-by-char streaming)
        yield GlobalState.stream_analysis_bg

    @rx.event(background=True)
    async def stream_analysis_bg(self):
        """True AI streaming via thread + asyncio.Queue — updates every 50ms."""
        import threading
        import time

        async with self:
            page_name = self._pending_page_name
            kpis = dict(self.current_page_kpis)

        if not kpis:
            async with self:
                self.is_analyzing = False
            return

        messages = AnalysisService.get_kpi_analysis_messages(page_name, kpis)
        if not messages:
            async with self:
                self.analysis_result = "Não há dados suficientes para análise."
                self.is_analyzing = False
            return

        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _run_stream():
            try:
                for chunk in ai_client.query_stream(messages):
                    asyncio.run_coroutine_threadsafe(q.put(chunk), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(q.put(f"__STREAM_ERROR__:{e}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(None), loop)

        thread = threading.Thread(target=_run_stream, daemon=True)
        thread.start()

        full_text = ""
        last_update = time.monotonic()
        received_first_chunk = False

        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=90.0)
            except asyncio.TimeoutError:
                logger.error("Streaming timeout after 90s")
                break

            if chunk is None:
                break

            if isinstance(chunk, str) and chunk.startswith("__STREAM_ERROR__:"):
                async with self:
                    self.analysis_result = f"Erro na análise: {chunk[17:]}"
                    self.is_analyzing = False
                    self.is_streaming = False
                return

            full_text += chunk

            now = time.monotonic()
            # On first chunk: hide spinner and switch to streaming text view
            # Then batch every 200ms for smooth, readable reveal
            if not received_first_chunk or (now - last_update >= 0.35):
                async with self:
                    if not received_first_chunk:
                        self.is_analyzing = False  # Spinner → streaming text
                        self.is_streaming = True
                        received_first_chunk = True
                    self.analysis_result = full_text + "▌"  # typing cursor
                last_update = now

        # Streaming done: render final sanitized markdown, remove cursor
        async with self:
            self.analysis_result = self._sanitize_markdown(full_text)
            self.is_streaming = False
            self.is_analyzing = False

    # ── Navigation / Loading Computed Vars ──────────────────────────────────────

    @rx.var
    def show_progress_bar(self) -> bool:
        """True quando está navegando entre páginas OU carregando dados.
        Usado no layout para exibir a top-loading-bar de forma null-safe."""
        return self.is_loading or self.is_navigating

    # ── KPI Detail Popup Computed Vars ──────────────────────────────────────────

    @rx.var
    def fin_contrato_rows(self) -> List[Dict[str, Any]]:
        """Per-contract financial breakdown for detail popups."""
        data = self.financeiro_list
        if self.fin_project_filter and self.fin_project_filter != "Todos":
            data = [f for f in data if f.get("contrato") == self.fin_project_filter]
        if not data:
            return []
        df = pd.DataFrame(data)
        money_cols = ["servico_contratado", "material_contratado", "servico_realizado", "material_realizado"]
        for col in money_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "contrato" not in df.columns:
            return []
        grouped = (
            df.groupby("contrato")
            .agg(
                {
                    "servico_contratado": "sum",
                    "material_contratado": "sum",
                    "servico_realizado": "sum",
                    "material_realizado": "sum",
                }
            )
            .reset_index()
        )
        grouped["total_contratado"] = grouped["servico_contratado"] + grouped["material_contratado"]
        grouped["total_realizado"] = grouped["servico_realizado"] + grouped["material_realizado"]
        grouped["saldo"] = grouped["total_contratado"] - grouped["total_realizado"]
        grouped["pct_medido"] = (
            (grouped["total_realizado"] / grouped["total_contratado"] * 100).fillna(0).round(1)
        )
        result = []
        for _, row in grouped.iterrows():
            val_cont = float(row["total_contratado"])
            val_real = float(row["total_realizado"])
            saldo_v = float(row["saldo"])
            pct = float(row["pct_medido"])
            result.append(
                {
                    "contrato": str(row["contrato"]),
                    "total_contratado_fmt": self._fmt_money(val_cont),
                    "total_realizado_fmt": self._fmt_money(val_real),
                    "saldo_fmt": self._fmt_money(saldo_v),
                    "pct_medido": f"{pct:.1f}%",
                }
            )
        return result

    @rx.var
    def fin_cockpit_popup_rows(self) -> List[Dict[str, Any]]:
        """Per-cockpit breakdown with formatted money for Total Medido popup."""
        data = self.financeiro_list
        if self.fin_project_filter and self.fin_project_filter != "Todos":
            data = [f for f in data if f.get("contrato") == self.fin_project_filter]
        if not data:
            return []
        df = pd.DataFrame(data)
        money_cols = ["servico_contratado", "material_contratado", "servico_realizado", "material_realizado"]
        for col in money_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        if "cockpit" not in df.columns:
            return []
        grouped = (
            df.groupby("cockpit")
            .agg(
                {
                    "servico_contratado": "sum",
                    "material_contratado": "sum",
                    "servico_realizado": "sum",
                    "material_realizado": "sum",
                }
            )
            .reset_index()
        )
        grouped["total_contratado"] = grouped["servico_contratado"] + grouped["material_contratado"]
        grouped["total_realizado"] = grouped["servico_realizado"] + grouped["material_realizado"]
        grouped["pct_medido"] = (
            (grouped["total_realizado"] / grouped["total_contratado"] * 100).fillna(0).round(1)
        )
        grouped = grouped.sort_values("total_contratado", ascending=False)
        result = []
        for _, row in grouped.iterrows():
            val_cont = float(row["total_contratado"])
            val_real = float(row["total_realizado"])
            pct = float(row["pct_medido"])
            result.append(
                {
                    "cockpit": str(row["cockpit"]) or "—",
                    "total_contratado_fmt": self._fmt_money(val_cont),
                    "total_realizado_fmt": self._fmt_money(val_real),
                    "pct_medido": f"{pct:.1f}%",
                }
            )
        return result

    @rx.var
    def contratos_ativos_rows(self) -> List[Dict[str, Any]]:
        """Active contracts for the Contratos Ativos detail popup."""
        active = [
            c for c in self.contratos_list
            if str(c.get("status", "")).strip() == "Em Execução"
        ]
        result = []
        for c in active[:25]:
            val = float(c.get("valor_contratado", 0) or 0)
            result.append(
                {
                    "contrato": str(c.get("contrato", "—")),
                    "cliente": str(c.get("cliente", "—")),
                    "status": str(c.get("status", "—")),
                    "valor_fmt": self._fmt_money(val),
                }
            )
        return result

    def _sanitize_markdown(self, text: str) -> str:
        """Extreme Failsafe: Fixes mashed tables, missing pipes, and broken column alignment."""
        if not text:
            return ""
        import re

        # Ensure spaces around bold markers so rx.markdown doesn't concatenate adjacent words.
        # e.g. "R**4M**em" → "R **4M** em"
        text = re.sub(r'(\w)\*\*', r'\1 **', text)
        text = re.sub(r'\*\*(\w)', r'** \1', text)

        lines = text.split("\n")
        sanitized = []
        in_table = False

        # Table header keywords for the C-Level KPI matrix (reconstruct if mashed by AI)
        headers_keywords = ["Alavanca Crítica", "Status Atual", "Impacto & Ação Recomendada"]

        for i, line in enumerate(lines):
            trimmed = line.strip()

            # Detect Table Block Start (even if mashed)
            is_potential_header = any(
                kw.replace(" ", "") in trimmed.replace(" ", "") for kw in headers_keywords
            )

            if is_potential_header and not in_table:
                # Forcefully reconstruct the header line
                line = "| Alavanca Crítica | Status Atual | Impacto & Ação Recomendada |"
                sanitized.append(line)
                # Inject separator
                sanitized.append("| :--- | :--- | :--- |")
                in_table = True
                continue

            if in_table:
                # Check for end of table (empty line or new header)
                if trimmed == "" or (trimmed.startswith("#")):
                    in_table = False
                elif re.match(r'^[\|\s:\-]+$', trimmed):
                    # Skip separator rows — already injected on header detection
                    continue
                elif "|" not in trimmed:
                    # Attempt to split data row into 3 columns aggressively
                    # Look for markers like "R$", "%", or multiple spaces
                    parts = []
                    # 1. First column: The indicator name (usually first few words)
                    # 2. Second column: The value (usually has numbers, R$, or %)
                    # 3. Third column: The impact (the rest)

                    # Heuristic: split by double space first
                    raw_parts = [p.strip() for p in re.split(r"\s{2,}", trimmed) if p.strip()]

                    if len(raw_parts) >= 3:
                        parts = raw_parts[:3]
                    elif len(raw_parts) == 2:
                        # Split the part that contains a value
                        m = re.search(r"([R\$]?\s?\d+[\.,]?\d*\s?[%]?\w*)", raw_parts[1])
                        if m:
                            val = m.group(1).strip()
                            impact = raw_parts[1].replace(m.group(1), "").strip()
                            parts = [raw_parts[0], val, impact]
                    else:
                        # Fallback for single-space mashed sentence
                        # Find the first value-like thing (R$, %, or number)
                        m = re.search(r"(\s[R\$]?\s?\d+[\.,]?\d*\s?[%]?\w*)", trimmed)
                        if m:
                            val = m.group(1).strip()
                            idx = trimmed.find(m.group(1))
                            if idx > 0:
                                p1 = trimmed[:idx].strip()
                                p3 = trimmed[idx + len(m.group(1)) :].strip()
                                if p1 and p3:
                                    parts = [p1, val, p3]

                    if len(parts) >= 2:
                        while len(parts) < 3:
                            parts.append("-")
                        line = "| " + " | ".join(parts[:3]) + " |"
                    else:
                        in_table = False

            sanitized.append(line)

        return "\n".join(sanitized)

    # Navigation State
    current_path: str = ""

    # Authentication State
    is_authenticated: bool = False
    username_input: str = ""
    password_input: str = ""
    login_error: str = ""
    current_user_name: str = ""
    current_user_role: str = ""
    current_user_contrato: str = ""  # Contrato associado ao usuário (Mestre de Obras)
    allowed_modules: List[str] = []  # Module slugs from roles table
    active_features: List[str] = []  # Feature flags habilitadas para o contrato do usuário

    # Avatar personalization
    current_user_role_icon: str = "user"     # default icon from role row (roles.icon)
    current_user_avatar_icon: str = ""       # user-chosen icon (login.avatar_icon)
    current_user_avatar_type: str = "initial"  # "initial" or "icon" (login.avatar_type)
    show_avatar_modal: bool = False
    avatar_edit_icon: str = ""
    avatar_edit_type: str = "initial"

    # Contact info
    current_user_email: str = ""
    current_user_whatsapp: str = ""

    # Avatar modal tab ("avatar" | "senha" | "contato") + password fields
    avatar_modal_tab: str = "avatar"
    pw_current: str = ""
    pw_new: str = ""
    pw_confirm: str = ""
    pw_error: str = ""
    pw_success: bool = False
    # Contato edit fields
    contact_edit_email: str = ""
    contact_edit_whatsapp: str = ""
    contact_error: str = ""
    contact_success: bool = False

    async def check_login_on_enter(self, key: str):
        """Login apenas se Enter for pressionado"""
        if key == "Enter":
            async for update in self.check_login():
                yield update

    def logout(self):
        """Sai da plataforma"""
        audit_log(
            category=AuditCategory.LOGOUT,
            action=f"Usuário '{self.current_user_name}' fez logout",
            username=self.current_user_name,
            status="success",
        )
        self.is_authenticated = False
        self.username_input = ""
        self.password_input = ""
        self.allowed_modules = []
        self.current_user_name = ""
        self.current_user_role = ""
        self.current_user_role_icon = "user"
        self.current_user_avatar_icon = ""
        self.current_user_avatar_type = "initial"
        self.show_avatar_modal = False
        self.avatar_modal_tab = "avatar"
        self.pw_current = ""
        self.pw_new = ""
        self.pw_confirm = ""
        self.pw_error = ""
        self.pw_success = False
        self.current_user_email = ""
        self.current_user_whatsapp = ""
        self.contact_edit_email = ""
        self.contact_edit_whatsapp = ""
        self.contact_error = ""
        self.contact_success = False
        # Limpa sessão de chat para não vazar histórico entre usuários
        self.chat_session_id = ""
        self.chat_history = []

    def set_current_path(self, path: str):
        self.current_path = path

    def set_username_input(self, value: str):
        self.username_input = value

    def set_password_input(self, value: str):
        self.password_input = value

    # ── Avatar personalization ─────────────────────────────────────────────────

    @rx.var
    def avatar_fallback(self) -> str:
        """First letter of the logged-in username for avatar display."""
        name = self.current_user_name
        return name[0].upper() if name else "?"

    @rx.var
    def effective_avatar_icon(self) -> str:
        """Resolved icon slug to display when avatar_type == 'icon'."""
        return self.current_user_avatar_icon or self.current_user_role_icon or "user"

    def open_avatar_modal(self):
        self.avatar_edit_icon = self.current_user_avatar_icon
        self.avatar_edit_type = self.current_user_avatar_type
        self.avatar_modal_tab = "avatar"
        self.pw_current = ""
        self.pw_new = ""
        self.pw_confirm = ""
        self.pw_error = ""
        self.pw_success = False
        self.contact_edit_email = self.current_user_email
        self.contact_edit_whatsapp = self.current_user_whatsapp
        self.contact_error = ""
        self.contact_success = False
        self.show_avatar_modal = True

    def close_avatar_modal(self):
        self.show_avatar_modal = False

    def set_avatar_modal_tab(self, tab: str):
        self.avatar_modal_tab = tab
        self.pw_error = ""
        self.pw_success = False
        self.contact_error = ""
        self.contact_success = False

    def set_avatar_edit_type(self, val: str):
        self.avatar_edit_type = val

    def set_avatar_edit_icon(self, val: str):
        self.avatar_edit_icon = val

    def save_avatar_pref(self):
        """Persist avatar preferences to login table and update local state."""
        from bomtempo.core.supabase_client import sb_update
        try:
            sb_update(
                "login",
                filters={"username": self.current_user_name},
                data={
                    "avatar_icon": self.avatar_edit_icon,
                    "avatar_type": self.avatar_edit_type,
                },
            )
            self.current_user_avatar_icon = self.avatar_edit_icon
            self.current_user_avatar_type = self.avatar_edit_type
        except Exception as e:
            logger.error(f"Erro ao salvar preferência de avatar: {e}")
        self.show_avatar_modal = False

    # ── Change password ────────────────────────────────────────────────────────

    def set_pw_current(self, val: str):
        self.pw_current = val

    def set_pw_new(self, val: str):
        self.pw_new = val

    def set_pw_confirm(self, val: str):
        self.pw_confirm = val

    def save_password(self):
        self.pw_error = ""
        self.pw_success = False

        if not self.pw_new.strip():
            self.pw_error = "A nova senha não pode estar vazia."
            return
        if len(self.pw_new.strip()) < 3:
            self.pw_error = "A nova senha deve ter ao menos 3 caracteres."
            return
        if self.pw_new != self.pw_confirm:
            self.pw_error = "As senhas não coincidem."
            return

        from bomtempo.core.supabase_client import sb_select, sb_update
        try:
            rows = sb_select("login", filters={"username": self.current_user_name})
            if not rows:
                self.pw_error = "Usuário não encontrado."
                return
            db_pw = str(rows[0].get("password", ""))
            if self.pw_current.strip() != db_pw:
                self.pw_error = "Senha atual incorreta."
                return
            sb_update(
                "login",
                filters={"username": self.current_user_name},
                data={"password": self.pw_new.strip()},
            )
            self.pw_current = ""
            self.pw_new = ""
            self.pw_confirm = ""
            self.pw_success = True
        except Exception as e:
            logger.error(f"Erro ao alterar senha: {e}")
            self.pw_error = "Erro ao salvar. Tente novamente."

    # ── Contact info ───────────────────────────────────────────────────────────

    def set_contact_edit_email(self, val: str):
        self.contact_edit_email = val

    def set_contact_edit_whatsapp(self, val: str):
        self.contact_edit_whatsapp = val

    def save_contact(self):
        """Save email and whatsapp for the current user."""
        self.contact_error = ""
        self.contact_success = False
        from bomtempo.core.supabase_client import sb_update
        try:
            sb_update(
                "login",
                filters={"username": self.current_user_name},
                data={
                    "email": self.contact_edit_email.strip(),
                    "whatsapp": self.contact_edit_whatsapp.strip(),
                },
            )
            self.current_user_email = self.contact_edit_email.strip()
            self.current_user_whatsapp = self.contact_edit_whatsapp.strip()
            self.contact_success = True
        except Exception as e:
            logger.error(f"Erro ao salvar contato: {e}")
            self.contact_error = "Erro ao salvar. Tente novamente."

    @rx.var
    def page_title(self) -> str:
        """Returns the current page title for display."""
        path = self.router.page.path.strip("/")
        if not path or path == "index" or path == "/":
            return "Visão Geral"
        return path.replace("-", " ").title()

    def set_projetos_search(self, value: str):
        self.projetos_search = value

    def set_current_question(self, value: str):
        self.current_question = value

    def set_projetos_fase_filter(self, value: str):
        if self.projetos_fase_filter == value:
            self.projetos_fase_filter = ""
        else:
            self.projetos_fase_filter = value

    def set_om_time_filter(self, value: str):
        self.om_time_filter = value

    def set_obras_selected_contract(self, value: str):
        self.obras_selected_contract = value

    def set_global_project_filter(self, value: str):
        self.global_project_filter = value

    def set_om_project_filter(self, value: str):
        self.om_project_filter = value

    def _recompute_fin_charts(self):
        """Recalcula os gráficos financeiros pesados e armazena em state vars.
        Chamado apenas ao carregar dados ou mudar filtro — nunca em cada render.
        """
        data = self.financeiro_list
        if self.fin_project_filter and self.fin_project_filter != "Todos":
            data = [f for f in data if f.get("contrato") == self.fin_project_filter]

        if not data:
            self.financeiro_cockpit_chart = []
            self.financeiro_scurve_chart = []
            return

        df = pd.DataFrame(data)
        if "cockpit" not in df.columns:
            self.financeiro_cockpit_chart = []
            self.financeiro_scurve_chart = []
            return

        money_cols = ["servico_contratado", "material_contratado", "servico_realizado", "material_realizado"]
        for col in money_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        grouped = (
            df.groupby("cockpit")
            .agg({c: "sum" for c in money_cols if c in df.columns})
            .reset_index()
        )
        grouped["total_contratado"] = (
            grouped.get("servico_contratado", 0) + grouped.get("material_contratado", 0)
        )
        grouped["total_realizado"] = (
            grouped.get("servico_realizado", 0) + grouped.get("material_realizado", 0)
        )
        grouped["margem"] = grouped["total_contratado"] - grouped["total_realizado"]
        grouped["margem_pct"] = (
            (grouped["margem"] / grouped["total_contratado"].replace(0, float("nan")) * 100)
            .fillna(0).round(1)
        )
        grouped["total_contratado"] = grouped["total_contratado"].round(2)
        grouped["total_realizado"] = grouped["total_realizado"].round(2)
        grouped["formatted_total"] = grouped["total_contratado"].apply(
            lambda x: (
                f"R$ {x/1_000_000:.1f}M".replace(".", ",")
                if x >= 1_000_000
                else (f"R$ {x/1_000:.0f}k".replace(".", ",") if x >= 1_000 else f"R$ {x:.0f}")
            )
        )
        self.financeiro_cockpit_chart = grouped.to_dict("records")

        # S-Curve
        g2 = grouped.copy().sort_values("total_contratado")
        g2["cumulative_planned"] = g2["total_contratado"].cumsum().round(0)
        g2["cumulative_actual"] = g2["total_realizado"].cumsum().round(0)
        self.financeiro_scurve_chart = g2[["cockpit", "cumulative_planned", "cumulative_actual"]].to_dict("records")

    def set_fin_project_filter(self, value: str):
        self.fin_project_filter = value
        self._recompute_fin_charts()

    def load_data(self):
        """Carrega dados iniciais"""
        self.is_navigating = False  # Encerra feedback de navegação ao chegar na nova página
        # Se já temos dados, não recarrega (Persistência na Sessão)
        if self.contratos_list:
            logger.info("⚡ Dados já em cache. Pulando recarregamento.")
            self.is_loading = False
            return

        self.is_loading = True
        yield

        try:
            loader = DataLoader()
            self._data = loader.load_all()

            # Helper to safely get DF
            def get_df(key: str) -> pd.DataFrame:
                d = self._data.get(key)
                if d is None:
                    return pd.DataFrame()
                return d

            if "contratos" in self._data:
                df = get_df("contratos")
                if not df.empty:
                    # Convert Timestamp dates to strings
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].astype(str)
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            df[col] = df[col].fillna(0)
                        else:
                            df[col] = df[col].fillna("")
                    self.contratos_list = df.to_dict("records")
                    self.total_contratos = len(df)
                    self.valor_tcv = (
                        float(df["valor_contratado"].sum())
                        if "valor_contratado" in df.columns
                        else 0.0
                    )
                    self.contratos_ativos = (
                        len(df[df["status"] == "Em Execução"]) if "status" in df.columns else 0
                    )

            if "projeto" in self._data:
                df = get_df("projeto")
                if not df.empty:
                    for col in ["inicio_previsto", "termino_previsto"]:
                        if col in df.columns:
                            df[col] = df[col].astype(str)
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            df[col] = df[col].fillna(0)
                        else:
                            df[col] = df[col].fillna("")
                    self.projetos_list = df.to_dict("records")

            if "obras" in self._data:
                df = get_df("obras")
                if not df.empty:
                    if "data" in df.columns:
                        df["data"] = df["data"].astype(str)
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            df[col] = df[col].fillna(0)
                        else:
                            df[col] = df[col].fillna("")
                    self.obras_list = df.to_dict("records")

            if "financeiro" in self._data:
                df = get_df("financeiro")
                if not df.empty:
                    if "data" in df.columns:
                        df["data"] = df["data"].astype(str)
                    # Fill NaN: 0 for numeric cols, "" for object cols to avoid type errors in agg
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            df[col] = df[col].fillna(0)
                        else:
                            df[col] = df[col].fillna("")
                    self.financeiro_list = df.to_dict("records")

            if "om" in self._data:
                df = get_df("om")
                if not df.empty:
                    if "data" in df.columns:
                        df["data"] = df["data"].astype(str)
                    for col in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col]):
                            df[col] = df[col].fillna(0)
                        else:
                            df[col] = df[col].fillna("")
                    self.om_list = df.to_dict("records")

            # --- Update current page KPIs immediately on data load ---
            # Ideally this happens on page load, but we can pre-populate if data is ready.
            # However, simpler to let pages push their context on_mount.

            # Login agora vem do Supabase — users_list não é mais populado a partir de sheets
            # (check_login usa Supabase diretamente como primário + hardcoded fallback)

            # RDO dados agora são lidos do Supabase diretamente (rdo_service.py / rdo_historico.py)

            # Recalcula gráficos financeiros pesados uma única vez após carga
            self._recompute_fin_charts()

            # ── #12: Guard de tamanho — aviso se listas excederem threshold ──
            # financeiro_list é serializada ao browser; mais de 500 linhas é sinal
            # de que a tabela cresceu além do esperado (dados históricos acumulados)
            _FIN_WARN = 500
            if len(self.financeiro_list) > _FIN_WARN:
                logger.warning(
                    f"⚠️ financeiro_list tem {len(self.financeiro_list)} linhas → "
                    f"considere paginar no Supabase (limit + filtro por ano/contrato)"
                )

            self.is_loading = False
            logger.info("✅ Estado global atualizado com sucesso")

        except Exception as e:
            self.error_message = str(e)
            self.is_loading = False
            logger.error(f"❌ Erro no estado global: {e}")

    def force_refresh_data(self):
        """Recarrega TODOS os dados do Supabase, ignorando cache e guard.

        Chamado após commit no Editor de Dados para manter todas as páginas
        sincronizadas com as alterações mais recentes do banco.
        """
        import os
        from bomtempo.core.data_loader import CACHE_FILE

        # 1. Invalida cache em disco para forçar fetch fresco
        try:
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
                logger.info("🗑️ Cache invalidado (data_cache.pkl removido)")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao remover cache: {e}")

        # 2. Reseta guard vars para permitir recarregamento
        self.contratos_list = []
        self.projetos_list = []
        self.obras_list = []
        self.financeiro_list = []
        self.om_list = []
        self._data = {}

        # 3. Recarrega tudo (inline — sem yield)
        logger.info("🔄 force_refresh_data: recarregando dados do Supabase...")
        try:
            loader = DataLoader()
            self._data = loader.load_all()

            def get_df(key: str) -> pd.DataFrame:
                d = self._data.get(key)
                return d if d is not None else pd.DataFrame()

            for table_key, attr_name in [
                ("contratos", "contratos_list"),
                ("projeto", "projetos_list"),
                ("obras", "obras_list"),
                ("financeiro", "financeiro_list"),
                ("om", "om_list"),
            ]:
                if table_key in self._data:
                    df = get_df(table_key)
                    if not df.empty:
                        for col in df.columns:
                            if pd.api.types.is_datetime64_any_dtype(df[col]):
                                df[col] = df[col].astype(str)
                        for col in df.columns:
                            if pd.api.types.is_numeric_dtype(df[col]):
                                df[col] = df[col].fillna(0)
                            else:
                                df[col] = df[col].fillna("")
                        setattr(self, attr_name, df.to_dict("records"))

            if "contratos" in self._data:
                df = get_df("contratos")
                if not df.empty:
                    self.total_contratos = len(df)
                    self.valor_tcv = (
                        float(df["valor_contratado"].sum())
                        if "valor_contratado" in df.columns
                        else 0.0
                    )
                    self.contratos_ativos = (
                        len(df[df["status"] == "Em Execução"]) if "status" in df.columns else 0
                    )

            self.is_loading = False
            logger.info("✅ force_refresh_data: estado global re-sincronizado")
        except Exception as e:
            self.is_loading = False
            logger.error(f"❌ force_refresh_data falhou: {e}")

    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    def set_navigating(self):
        """Seta is_navigating=True para exibir top-bar imediatamente ao clicar na sidebar.
        A navegação SPA em si é feita pelo rx.link(href=...) — não usamos redirect aqui
        para evitar full page reload e o null-state error no frontend."""
        self.is_navigating = True

    def prefetch_route(self, route: str):
        """Aquece conexão HTTP ao passar o mouse sobre item do sidebar (#14).
        Dispara em daemon thread para não bloquear — o pool httpx já mantém
        o socket aberto, reduzindo latência do primeiro request ao navegar.
        """
        import threading as _t

        def _warm():
            try:
                from bomtempo.core.supabase_client import sb_select
                if route in ("/alertas",):
                    sb_select("alert_subscriptions", limit=1)
                elif route in ("/logs-auditoria",):
                    sb_select("system_logs", limit=1)
                elif route in ("/rdo-dashboard",):
                    sb_select("rdo_master", limit=1)
                elif route in ("/reembolso-dash",):
                    sb_select("fuel_requests", limit=1)
            except Exception:
                pass

        _t.Thread(target=_warm, daemon=True).start()

    def check_mobile_access(self):
        """Redireciona se não tiver permissão mobile"""
        if self.current_user_role != "Gestão-Mobile":
            return rx.redirect("/")

    def toggle_theme(self):
        self.theme_mode = "light" if self.theme_mode == "dark" else "dark"

    def select_contrato(self, contrato: str):
        self.selected_contrato = contrato

    def deselect_contrato(self):
        self.selected_contrato = ""

    # ── Authentication ──────────────────────────────────────────

    async def check_login(self):
        """Verifica credenciais no Supabase. Async para mostrar loading antes da query."""
        username = self.username_input.strip().lower()
        password = self.password_input.strip()

        logger.info(f"Tentativa de login: User='{username}'")

        if not username or not password:
            self.login_error = "Preencha usuário e senha"
            return

        # ── Intermediate auth state: button changes on login page ─────────────
        self.is_authenticating = True
        self.login_error = ""
        yield

        # ── Emergency Fallback ────────────────────────────────────────────────
        if username == "fallback" and password == "2":
            self.is_authenticated = True
            self.current_user_name = "fallback"
            self.current_user_role = "Administrador"
            self.current_user_contrato = ""
            from bomtempo.state.usuarios_state import MODULE_SLUGS
            self.allowed_modules = list(MODULE_SLUGS)
            self.login_error = ""
            self.username_input = ""
            self.password_input = ""
            self.is_authenticating = False
            self.show_loading_screen = True
            yield
            yield GlobalState.load_initial_data_smooth
            yield rx.redirect("/")
            return

        # ── Supabase ──────────────────────────────────────────────────────────
        try:
            import os

            if not os.getenv("SUPABASE_SERVICE_KEY"):
                logger.error(
                    "CRITICAL: SUPABASE_SERVICE_KEY não encontrada nas variáveis de ambiente."
                )
                self.is_authenticating = False
                self.show_loading_screen = False
                self.login_error = "Erro de Configuração: Chave de API não encontrada no servidor."
                self.is_authenticated = False
                return

            from bomtempo.core.supabase_client import sb_select

            # Busca apenas o usuário específico — não carrega tabela inteira
            user_rows = sb_select("login", filters={"username": username}, limit=1)
            logger.info(f"Supabase login: query filtrada p/ '{username}' → {len(user_rows)} linha(s)")

            def _get_password_field(row: dict) -> str:
                for key in ("password", "senha", "pass", "pwd"):
                    val = row.get(key)
                    if val is not None:
                        return str(val).strip()
                return ""

            def _get_role_field(row: dict) -> str:
                for key in ("user_role", "role", "permissao", "perfil"):
                    val = row.get(key)
                    if val is not None:
                        return str(val).strip()
                return "Visitante"

            matched = user_rows[0] if user_rows else None

            if matched is None:
                logger.warning(f"Usuário '{username}' não encontrado no Supabase.")
                audit_log(
                    category=AuditCategory.LOGIN,
                    action=f"Tentativa de login falhou — usuário '{username}' não encontrado",
                    username=username,
                    status="error",
                )
                self.is_authenticating = False
                self.show_loading_screen = False
                self.login_error = "Usuário ou senha inválidos"
                self.is_authenticated = False
                return

            if _get_password_field(matched) != password:
                logger.warning(f"Senha incorreta para '{username}'")
                audit_log(
                    category=AuditCategory.LOGIN,
                    action=f"Tentativa de login falhou — senha incorreta para '{username}'",
                    username=username,
                    status="error",
                )
                self.is_authenticating = False
                self.show_loading_screen = False
                self.login_error = "Usuário ou senha inválidos"
                self.is_authenticated = False
                return

            # ── Login OK — switch to enterprise full-screen loader ────────────
            self.is_authenticating = False
            self.show_loading_screen = True
            yield

            role = _get_role_field(matched)
            self.is_authenticated = True
            self.current_user_name = str(
                matched.get("user") or matched.get("username") or matched.get("login") or username
            )
            self.current_user_role = role
            self.current_user_contrato = str(
                matched.get("project") or matched.get("contrato") or ""
            )
            self.login_error = ""
            self.username_input = ""
            self.password_input = ""
            logger.info(f"✅ Login OK via Supabase. Role: {role}")

            # ── Fetch module permissions + role icon from roles table ─────────
            try:
                from bomtempo.core.supabase_client import sb_select
                from bomtempo.state.usuarios_state import MODULE_SLUGS
                role_rows = sb_select("roles", filters={"name": role})
                if role_rows:
                    self.allowed_modules = list(role_rows[0].get("modules", []))
                    self.current_user_role_icon = str(role_rows[0].get("icon", "user") or "user")
                    logger.info(f"Permissões carregadas: {len(self.allowed_modules)} módulos")
                else:
                    # Fallback: Administrador full access, others none (need role in DB)
                    self.allowed_modules = list(MODULE_SLUGS) if role == "Administrador" else []
                    self.current_user_role_icon = "user"
                    logger.warning(f"Role '{role}' não encontrado na tabela roles — fallback aplicado")
            except Exception as role_err:
                logger.error(f"Erro ao carregar permissões do role '{role}': {role_err}")
                self.allowed_modules = list(MODULE_SLUGS) if role == "Administrador" else []
                self.current_user_role_icon = "user"

            # ── Load feature flags for user's contract ────────────────────────
            _contrato = str(matched.get("project") or matched.get("contrato") or "")
            if _contrato and _contrato not in ("nan", "None", ""):
                try:
                    from bomtempo.core.feature_flags import FeatureFlagsService
                    self.active_features = FeatureFlagsService.get_features_for_contract(_contrato)
                    logger.info(f"Feature flags carregadas: {self.active_features}")
                except Exception as ff_err:
                    logger.warning(f"Erro ao carregar feature flags: {ff_err}")
                    self.active_features = []
            else:
                self.active_features = []

            # ── Load user avatar + contact preferences from login row ─────────
            self.current_user_avatar_icon = str(matched.get("avatar_icon", "") or "")
            self.current_user_avatar_type = str(matched.get("avatar_type", "initial") or "initial")
            self.current_user_email = str(matched.get("email", "") or "")
            self.current_user_whatsapp = str(matched.get("whatsapp", "") or "")
            audit_log(
                category=AuditCategory.LOGIN,
                action=f"Login bem-sucedido — role: {role}",
                username=self.current_user_name,
                metadata={"role": role},
                status="success",
            )

            yield GlobalState.load_initial_data_smooth

            if role == "Gestão-Mobile":
                yield rx.redirect("/mobile-chat")
            elif role == "Mestre de Obras":
                yield rx.redirect("/rdo-form")
            elif role == "solicitacao_reembolso":
                yield rx.redirect("/reembolso")
            elif role == "engenheiro":
                yield rx.redirect("/projetos")
            elif role == "data_edit":
                yield rx.redirect("/admin/editar_dados")
            else:
                yield rx.redirect("/")

        except Exception as e:
            logger.error(f"❌ Erro ao conectar com Supabase: {e}")
            audit_error(
                action=f"Erro crítico ao autenticar usuário '{username}'",
                username=username,
                error=e,
            )
            self.is_authenticating = False
            self.show_loading_screen = False
            self.login_error = "Erro ao conectar com o servidor. Tente novamente."
            self.is_authenticated = False

    async def guard_index_page(self):
        """on_load da página /: redireciona roles sem permissão antes de renderizar conteúdo."""
        if self.is_authenticated and self.current_user_role == "Mestre de Obras":
            yield rx.redirect("/rdo-form")
            return
        if self.is_authenticated and self.current_user_role == "solicitacao_reembolso":
            yield rx.redirect("/reembolso")
            return
        if self.is_authenticated and self.current_user_role == "data_edit":
            yield rx.redirect("/admin/editar_dados")
            return
        yield GlobalState.load_data

    async def load_initial_data_smooth(self):
        """Loading screen pós-login com duração mínima garantida pela animação CSS.
        
        Fluxo:
        - Carrega dados do Supabase enquanto a animação roda (pré-aquece o cache)
        - Aguarda no mínimo ANIMATION_DURATION + BUFFER (5.0s) antes de esconder
        - Se dados demorarem mais que a animação (raro), aguarda os dados + BUFFER
        - Quando on_load disparar na página destino, bate no cache e retorna instantaneamente
        """
        import asyncio
        import time

        ANIMATION_DURATION = 4.5  # deve coincidir com loaderProgress em style.css
        BUFFER = 0.5               # tempo extra após animação completar
        MIN_DISPLAY = ANIMATION_DURATION + BUFFER  # 5.0s mínimo total

        self.initial_loading = True
        self.show_loading_screen = True
        yield

        start = time.monotonic()

        # Executa load_data inline (itera o generator) para pré-carregar o cache
        # Assim quando on_load disparar na página destino, já bate no cache
        if not self.contratos_list:
            for _ in self.load_data():
                pass  # consome os yields do generator sem enviar deltas parciais

        # Aquece connection pool para módulos pesados em background durante a animação
        # Enquanto a tela de loading exibe os 4.5s de animação, preparamos as conexões
        import threading as _threading
        _role = self.current_user_role

        def _warm_module_connections():
            """Pré-aquece HTTP keep-alive para tabelas dos módulos secundários."""
            try:
                from bomtempo.core.supabase_client import sb_select
                # Todos os roles beneficiam de alertas pré-aquecidos
                sb_select("alert_subscriptions", limit=1)
                # Admin/Gestão: pré-aquece logs e RDO
                if _role in ("Administrador", "admin", "Gestão-Mobile"):
                    sb_select("system_logs", limit=1)
                    sb_select("rdo_master", limit=1)
            except Exception:
                pass  # falha silenciosa — é só aquecimento

        _threading.Thread(target=_warm_module_connections, daemon=True).start()

        data_elapsed = time.monotonic() - start

        # Aguarda o tempo restante para completar animação + buffer.
        # Se dados demoraram mais que a animação, aguarda só o buffer mínimo.
        remaining = max(MIN_DISPLAY - data_elapsed, BUFFER)
        await asyncio.sleep(remaining)

        self.initial_loading = False
        self.show_loading_screen = False

    # ── Filter Options ───────────────────────────────────────────

    @rx.var
    def project_filter_options(self) -> List[str]:
        """List of all project names for filter dropdowns"""
        if not self.contratos_list:
            return ["Todos"]
        # Fast list comprehension is fine here
        projects = sorted(
            set(c.get("contrato", "") for c in self.contratos_list if c.get("contrato"))
        )
        return ["Todos"] + projects

    @rx.var
    def om_time_filters(self) -> List[str]:
        return ["Mês", "Trimestre", "Ano"]

    @rx.var
    def contract_ids_list(self) -> List[str]:
        """Pure contract IDs for user→project assignment."""
        return [str(c.get("contrato", "")) for c in self.contratos_list if c.get("contrato")]

    @rx.var
    def contract_options_list(self) -> List[str]:
        """Contract IDs prefixed with 'Nenhum' sentinel for user dialog select."""
        return ["Nenhum"] + [str(c.get("contrato", "")) for c in self.contratos_list if c.get("contrato")]

    @rx.var
    def obras_contract_options(self) -> List[str]:
        """List of contract identifiers for obras dropdown"""
        if not self.contratos_list:
            return []
        # Build "Contrato - Cliente" strings
        options = []
        for c in self.contratos_list:
            label = c.get("contrato", "")
            cliente = c.get("cliente", "")
            if cliente:
                label = f"{label} - {cliente}"
            options.append(label)
        return options

    # ── Projetos ─────────────────────────────────────────────────

    @rx.var
    def fases_disponiveis(self) -> List[str]:
        """Returns unique fase_macro values directly from DB column, sorted by numeric prefix."""
        if not self.projetos_list:
            return []
        # Build ordered unique list preserving the numeric sort from 'fase' field
        seen: set = set()
        # Collect (numeric_prefix, macro_name) pairs
        pairs: list = []
        for p in self.projetos_list:
            macro = str(p.get("fase_macro", "")).strip()
            if not macro or macro in seen:
                continue
            seen.add(macro)
            try:
                prefix_num = int(float(str(p.get("fase", "99"))))
            except Exception:
                prefix_num = 99
            pairs.append((prefix_num, macro))
        pairs.sort(key=lambda x: x[0])
        return [m for _, m in pairs]

    @rx.var
    def filtered_contratos(self) -> List[Dict[str, Any]]:
        # Optimization: Use self._data["projeto"] instead of recreating DF
        # But for 'result', we are filtering the list.
        result = self.contratos_list
        if self.projetos_search:
            term = self.projetos_search.lower()
            result = [
                c
                for c in result
                if term in c.get("contrato", "").lower() or term in c.get("cliente", "").lower()
            ]
        if self.projetos_fase_filter:
            contratos_with_fase = {
                p.get("contrato", "")
                for p in self.projetos_list
                if p.get("fase_macro") == self.projetos_fase_filter
            }
            result = [c for c in result if c.get("contrato") in contratos_with_fase]

        # Calculate progress and dates from activities
        if not self.projetos_list:
            return [dict(c, progress=0, data_inicio="—", prazo_contratual="—") for c in result]

        # OPTIMIZATION: Use stored DataFrame
        df = self._data.get("projeto")
        if df is None or df.empty:
            return [dict(c, progress=0, data_inicio="—", prazo_contratual="—") for c in result]

        progress_map = {}
        dates_map = {}

        if "contrato" in df.columns:
            # Progress
            if "conclusao_pct" in df.columns:
                # df["conclusao_pct"] is already numeric from loader
                progress_map = df.groupby("contrato")["conclusao_pct"].mean().to_dict()

            # Dates
            if "inicio_previsto" in df.columns and "termino_previsto" in df.columns:
                # Group by contract
                grp = df.groupby("contrato")
                starts = grp["inicio_previsto"].min()
                ends = grp["termino_previsto"].max()

                for contract, start_date in starts.items():
                    end_date = ends.get(contract)
                    # Check if datetime before calling strftime
                    start_str = (
                        start_date.strftime("%d/%m/%Y")
                        if pd.notnull(start_date) and hasattr(start_date, "strftime")
                        else ("—" if pd.isnull(start_date) else str(start_date))
                    )
                    end_str = (
                        end_date.strftime("%d/%m/%Y")
                        if pd.notnull(end_date) and hasattr(end_date, "strftime")
                        else ("—" if pd.isnull(end_date) else str(end_date))
                    )
                    dates_map[contract] = {"start": start_str, "end": end_str}

        enriched_result = []
        for c in result:
            contract_code = c.get("contrato")
            p = progress_map.get(contract_code, 0)
            dates = dates_map.get(contract_code, {"start": "—", "end": "—"})

            # Create copy and update
            c_new = c.copy()
            c_new["progress"] = round(p, 1)
            c_new["data_inicio"] = dates["start"]
            c_new["prazo_contratual"] = dates["end"]
            enriched_result.append(c_new)

        return enriched_result

    @rx.var
    def selected_contrato_data(self) -> Dict[str, Any]:
        if not self.selected_contrato:
            return {}

        target = next(
            (c for c in self.contratos_list if c.get("contrato") == self.selected_contrato), None
        )
        if not target:
            return {}

        contract = target.copy()

        # Initialize date fields with default values
        if "projeto_inicio" not in contract:
            contract["projeto_inicio"] = "—"
        if "termino_estimado" not in contract:
            contract["termino_estimado"] = "—"

        # Optimization: Use stored DataFrame
        df = self._data.get("projeto")
        if df is not None and not df.empty and "contrato" in df.columns:
            # Filter for this contract using optimized pandas indexing
            mask = df["contrato"] == self.selected_contrato
            if mask.any():
                df_c = df.loc[mask]
                # Dates - use correct column names from normalization
                if "inicio_previsto" in df_c.columns:
                    s = df_c["inicio_previsto"].min()
                    if pd.notnull(s) and hasattr(s, "strftime"):
                        contract["projeto_inicio"] = s.strftime("%d/%m/%Y")
                    elif pd.notnull(s) and str(s) != "NaT":
                        contract["projeto_inicio"] = str(s)[:10]  # Get date part only

                if "termino_previsto" in df_c.columns:
                    e = df_c["termino_previsto"].max()
                    if pd.notnull(e) and hasattr(e, "strftime"):
                        contract["termino_estimado"] = e.strftime("%d/%m/%Y")
                    elif pd.notnull(e) and str(e) != "NaT":
                        contract["termino_estimado"] = str(e)[:10]  # Get date part only

        return contract

    @rx.var
    def filtered_projetos(self) -> List[Dict[str, Any]]:
        """Activities filtered by selected contract and optionally by phase

        Deduplicates activities with same name, keeping the one with highest completion.
        """
        if not self.selected_contrato or not self.projetos_list:
            return []

        # Filter by contract
        result = [p for p in self.projetos_list if p.get("contrato") == self.selected_contrato]

        # Filter by phase if set (prefix match: "1 — Projeto Básico" → fase starts with "1.")
        if self.projetos_fase_filter:
            result = [p for p in result if p.get("fase_macro") == self.projetos_fase_filter]

        # Deduplicate: Keep activity with highest completion %
        deduplicated = {}
        for activity in result:
            activity_name = activity.get("atividade", "")
            if not activity_name:
                continue

            # Get current completion percentage
            current_pct = float(activity.get("conclusao_pct", 0) or 0)

            # If activity not seen yet, or this one has higher completion
            if activity_name not in deduplicated:
                deduplicated[activity_name] = activity
            else:
                existing_pct = float(deduplicated[activity_name].get("conclusao_pct", 0) or 0)
                if current_pct > existing_pct:
                    deduplicated[activity_name] = activity

        return list(deduplicated.values())

    @rx.var
    def total_atividades(self) -> int:
        return len(self.projetos_list)

    @rx.var
    def atividades_concluidas(self) -> int:
        return len([p for p in self.projetos_list if p.get("conclusao_pct", 0) >= 100])

    @rx.var
    def atividades_criticas_count(self) -> int:
        return len([p for p in self.projetos_list if p.get("critico") == "Sim"])

    @rx.var
    def atividades_criticas_atrasadas(self) -> int:
        return len(
            [
                p
                for p in self.projetos_list
                if p.get("critico") == "Sim" and p.get("conclusao_pct", 0) < 100
            ]
        )

    @rx.var
    def atividades_por_fase_chart(self) -> List[Dict[str, Any]]:
        df = self._data.get("projeto")
        if df is None or df.empty or "fase" not in df.columns:
            return []

        dist = df["fase"].value_counts().reset_index()
        dist.columns = ["name", "value"]
        dist["value"] = dist["value"].astype(int)
        return dist.to_dict("records")

    @rx.var
    def projetos_em_andamento(self) -> List[Dict[str, Any]]:
        """Projects in progress for overview cards"""
        df = self._data.get("projeto")
        if (
            df is None
            or df.empty
            or "conclusao_pct" not in df.columns
            or "contrato" not in df.columns
        ):
            return []

        # Build aggregation dict only with existing columns
        agg_dict = {"conclusao_pct": "mean"}
        if "fase" in df.columns:
            agg_dict["fase"] = "first"
        if "projeto" in df.columns:
            agg_dict["projeto"] = "first"

        grouped = df.groupby("contrato").agg(agg_dict).reset_index()
        grouped = grouped[grouped["conclusao_pct"] < 100].sort_values(
            "conclusao_pct", ascending=False
        )
        grouped["conclusao_pct"] = grouped["conclusao_pct"].round(1)
        return grouped.to_dict("records")

    # ── Formatação Global ────────────────────────────────────────

    @rx.var
    def valor_carteira_formatado(self) -> str:
        v = self.valor_tcv
        if v >= 1_000_000:
            return f"R$ {v/1_000_000:,.1f}M".replace(",", "X").replace(".", ",").replace("X", ".")
        if v >= 1_000:
            return f"R$ {v/1_000:,.1f}k".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def total_projetos_andamento(self) -> int:
        return len([p for p in self.projetos_list if p.get("conclusao_pct", 0) < 100])

    # ── Contratos / Overview ─────────────────────────────────────

    @rx.var
    def faturamento_por_cliente(self) -> List[Dict[str, Any]]:
        df = self._data.get("contratos")
        if (
            df is None
            or df.empty
            or "cliente" not in df.columns
            or "valor_contratado" not in df.columns
        ):
            return []

        # Apply global project filter
        if self.global_project_filter and self.global_project_filter != "Todos":
            if "contrato" in df.columns:
                df = df[df["contrato"] == self.global_project_filter]

        grouped = df.groupby("cliente")["valor_contratado"].sum().reset_index()
        grouped = grouped.sort_values("valor_contratado", ascending=False).head(10)
        grouped["valor_contratado"] = grouped["valor_contratado"].round(2)
        # Pre-format for charts
        grouped["formatted_valor"] = grouped["valor_contratado"].apply(
            lambda x: (
                f"{x/1_000_000:.1f}M"
                if x >= 1_000_000
                else (f"{x/1_000:.0f}k" if x >= 1_000 else f"{x:.0f}")
            )
        )
        return grouped.to_dict("records")

    @rx.var
    def status_contratos_dist(self) -> List[Dict[str, Any]]:
        df = self._data.get("contratos")
        if df is None or df.empty or "status" not in df.columns:
            return []

        # Apply global project filter
        if self.global_project_filter and self.global_project_filter != "Todos":
            if "contrato" in df.columns:
                df = df[df["contrato"] == self.global_project_filter]

        dist = df["status"].value_counts().reset_index()
        dist.columns = ["name", "value"]
        dist["value"] = dist["value"].astype(int)
        colors = ["#C98B2A", "#2A9D8F", "#E0E0E0", "#E89845", "#3B82F6"]
        dist["fill"] = [colors[i % len(colors)] for i in range(len(dist))]
        return dist.to_dict("records")

    @rx.var
    def contratos_recentes(self) -> List[Dict[str, Any]]:
        return self.contratos_list[-5:] if self.contratos_list else []

    # ── Financeiro ───────────────────────────────────────────────

    @rx.var
    def _financeiro_filtered(self) -> List[Dict[str, Any]]:
        """Helper: financeiro data filtered by project"""
        # Kept as list processing for now, simpler for small lists
        data = self.financeiro_list
        if self.fin_project_filter and self.fin_project_filter != "Todos":
            data = [f for f in data if f.get("contrato") == self.fin_project_filter]
        return data

    @rx.var
    def total_financeiro_contratado(self) -> float:
        data = self._financeiro_filtered
        if not data:
            return 0.0
        # Use pandas on small filtered list is OK, or sum dicts
        s = sum(float(d.get("servico_contratado", 0) or 0) for d in data)
        m = sum(float(d.get("material_contratado", 0) or 0) for d in data)
        return s + m

    @rx.var
    def total_financeiro_realizado(self) -> float:
        data = self._financeiro_filtered
        if not data:
            return 0.0
        s = sum(float(d.get("servico_realizado", 0) or 0) for d in data)
        m = sum(float(d.get("material_realizado", 0) or 0) for d in data)
        return s + m

    @rx.var
    def margem_bruta(self) -> float:
        return self.total_financeiro_contratado - self.total_financeiro_realizado

    @rx.var
    def margem_pct(self) -> float:
        if self.total_financeiro_contratado > 0:
            return round((self.margem_bruta / self.total_financeiro_contratado) * 100, 1)
        return 0.0

    # financeiro_cockpit_chart e financeiro_scurve_chart são agora state vars
    # (declaradas no bloco de vars acima) — calculadas em _recompute_fin_charts()
    # chamado em load_data() e set_fin_project_filter(). Não rodam mais em cada render.

    def _fmt_money(self, value: float) -> str:
        """Format money values in Brazilian format"""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def financeiro_contratado_fmt(self) -> str:
        return self._fmt_money(self.total_financeiro_contratado)

    @rx.var
    def financeiro_realizado_fmt(self) -> str:
        return self._fmt_money(self.total_financeiro_realizado)

    @rx.var
    def margem_bruta_fmt(self) -> str:
        return self._fmt_money(self.margem_bruta)

    @rx.var
    def margem_pct_fmt(self) -> str:
        return f"{self.margem_pct:.1f}%"

    # ── Obras ────────────────────────────────────────────────────

    @rx.var
    def avanco_fisico_geral(self) -> float:
        # Utilize 'projeto' or 'obras'? Usually average completion of active projects.
        # Previous code used 'projetos_list' (activities).
        df = self._data.get("projeto")
        if df is None or df.empty:
            return 0.0

        # Filter by selected contract if set
        target = self.obras_selected_contract
        if target:
            code = target.split(" - ")[0].strip() if " - " in target else target
            if "contrato" in df.columns:
                df = df[df["contrato"] == code]

        if df.empty:
            return 0.0

        if "conclusao_pct" in df.columns:
            return round(float(df["conclusao_pct"].mean()), 1)
        return 0.0

    @rx.var
    def avanco_fisico_geral_fmt(self) -> str:
        return f"{self.avanco_fisico_geral:.1f}%"

    @rx.var
    def total_obras_andamento(self) -> int:
        df = self._data.get("obras")
        if df is None or df.empty or "contrato" not in df.columns:
            return 0
        return int(df["contrato"].nunique())

    @rx.var
    def obras_atrasadas_count(self) -> int:
        df = self._data.get("obras")
        if df is None or df.empty:
            return 0

        if "realizado_pct" in df.columns and "previsto_pct" in df.columns:
            # Need to handle potential string/numeric issues if not cleaned
            # But loader cleans it.
            try:
                atrasadas = df[df["realizado_pct"] < (df["previsto_pct"] - 5)]
                return (
                    int(atrasadas["contrato"].nunique()) if "contrato" in atrasadas.columns else 0
                )
            except Exception:
                return 0
        return 0

    @rx.var
    def disciplina_progress_chart(self) -> List[Dict[str, Any]]:
        """Progress by discipline (Civil, Estrutura Metálica, etc.)
        Filtered by selected contract."""
        df = self._data.get("obras")
        if df is None or df.empty:
            return []

        # Filter by selected contract
        target = self.obras_selected_contract
        if target:
            code = target.split(" - ")[0].strip() if " - " in target else target
            if "contrato" in df.columns:
                df = df[df["contrato"] == code]

        # Check if DataFrame is empty after filtering
        if df.empty:
            return []

        if "categoria" not in df.columns:
            return []

        # Ensure previsto_pct and realizado_pct columns exist and are numeric
        for col in ["previsto_pct", "realizado_pct"]:
            if col not in df.columns:
                return []  # Can't show progress without these columns

        # Get latest data per category
        if "data" in df.columns:
            # Remove NaT dates before sorting
            df_valid = df[df["data"].notna()].copy()
            if df_valid.empty:
                # If no valid dates, use mean
                latest = (
                    df.groupby("categoria")
                    .agg({"previsto_pct": "mean", "realizado_pct": "mean"})
                    .reset_index()
                )
            else:
                latest = df_valid.sort_values("data").groupby("categoria").last().reset_index()
        else:
            latest = (
                df.groupby("categoria")
                .agg({"previsto_pct": "mean", "realizado_pct": "mean"})
                .reset_index()
            )

        if latest.empty:
            return []

        # Ensure numeric types and handle NaN/None
        latest["previsto_pct"] = (
            pd.to_numeric(latest["previsto_pct"], errors="coerce").fillna(0).round(0).astype(int)
        )
        latest["realizado_pct"] = (
            pd.to_numeric(latest["realizado_pct"], errors="coerce").fillna(0).round(0).astype(int)
        )

        latest = latest.sort_values("previsto_pct", ascending=False)
        return latest[["categoria", "previsto_pct", "realizado_pct"]].to_dict("records")

    @rx.var
    def status_por_obra_chart(self) -> List[Dict[str, Any]]:
        df = self._data.get("obras")
        if df is None or df.empty:
            return []

        if "data" in df.columns and "projeto" in df.columns:
            latest = df.sort_values("data").groupby("projeto").last().reset_index()

            # Check if required columns exist before sorting
            if "realizado_pct" in latest.columns and "previsto_pct" in latest.columns:
                latest = latest.sort_values("realizado_pct", ascending=True).head(10)
                latest["realizado_pct"] = (
                    pd.to_numeric(latest["realizado_pct"], errors="coerce").fillna(0).round(1)
                )
                latest["previsto_pct"] = (
                    pd.to_numeric(latest["previsto_pct"], errors="coerce").fillna(0).round(1)
                )
                return latest[["projeto", "realizado_pct", "previsto_pct"]].to_dict("records")
        return []

    # ... sidebar/params vars skip ...

    @rx.var
    def evolucao_obras_chart(self) -> List[Dict[str, Any]]:
        df = self._data.get("obras")
        if df is None or df.empty:
            return []

        if "data" not in df.columns or "realizado_pct" not in df.columns:
            return []

        # Create a copy to not mutate stored DF
        df = df.copy()
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["mes"] = df["data"].dt.to_period("M").astype(str)
        grouped = df.groupby("mes")["realizado_pct"].mean().reset_index()
        grouped["realizado_pct"] = grouped["realizado_pct"].round(1)
        return grouped.to_dict("records")

    # ── Obras Detail ─────────────────────────────────────────────

    @rx.var
    def obra_selected_data(self) -> Dict[str, Any]:
        """Data for the selected contract in Obras page"""
        target = self.obras_selected_contract
        # Extract contract code from "BOM010-24 - Escola A" format
        if target and " - " in target:
            target_code = target.split(" - ")[0].strip()
        elif target:
            target_code = target
        else:
            target_code = ""

        if not target_code and self.contratos_list:
            target_code = self.contratos_list[0].get("contrato", "")

        # Start with contract info
        result: Dict[str, Any] = {}
        for c in self.contratos_list:
            if c.get("contrato") == target_code:
                result = dict(c)
                break

        if not result and self.contratos_list:
            result = dict(self.contratos_list[0])
            target_code = result.get("contrato", "")

        # Merge with obras data for construction-specific fields
        if target_code:
            df = self._data.get("obras")
            if df is not None and not df.empty and "contrato" in df.columns:
                # Optimized filter
                obras_for_contract = df[df["contrato"] == target_code]
                if not obras_for_contract.empty:
                    first_row = obras_for_contract.iloc[0]
                    for key in ["os", "potencia_kwp", "terceirizado", "localizacao", "tipo"]:
                        if key in first_row.index:
                            val = first_row[key]
                            result[key] = str(val) if pd.notna(val) else "—"

                    # Compute prazo from início → término
                    if "data" in obras_for_contract.columns:
                        dates = pd.to_datetime(obras_for_contract["data"], errors="coerce")
                        if not dates.isna().all():
                            days = (dates.max() - dates.min()).days
                            result["prazo_dias"] = f"{days} dias"
                        else:
                            result["prazo_dias"] = "—"
                    else:
                        result["prazo_dias"] = "—"

        return result

    # ── Obras Enterprise (Revamp) ─────────────────────────────────

    @rx.var
    def obras_cards_list(self) -> List[Dict[str, Any]]:
        """One enriched card per contract for the Obras list view."""
        if not self.contratos_list:
            return []

        df_obras = self._data.get("obras")
        cards = []

        for c in self.contratos_list:
            code = c.get("contrato", "")
            cliente = c.get("cliente", "")
            label = f"{code} - {cliente}" if cliente else code

            card: Dict[str, Any] = {
                "contrato": code,
                "label": label,
                "cliente": cliente or "—",
                "localizacao": c.get("localizacao", "—"),
                "status": c.get("status", "Em Execução"),
                "avanco_pct": 0.0,
                "budget_planejado": 0.0,
                "budget_realizado": 0.0,
                "equipe_presente_hoje": 0,
                "efetivo_planejado": 0,
                "chuva_acumulada_mm": 0.0,
                "risco_geral_score": 0,
            }

            if df_obras is not None and not df_obras.empty and "contrato" in df_obras.columns:
                sub = df_obras[df_obras["contrato"] == code]
                if not sub.empty:
                    if "realizado_pct" in sub.columns:
                        card["avanco_pct"] = round(float(sub["realizado_pct"].mean()), 1)

                    first = sub.iloc[0]
                    for col, default in [
                        ("budget_planejado", 0.0),
                        ("budget_realizado", 0.0),
                        ("equipe_presente_hoje", 0),
                        ("efetivo_planejado", 0),
                        ("chuva_acumulada_mm", 0.0),
                        ("risco_geral_score", 0),
                    ]:
                        if col in first.index:
                            raw = first[col]
                            if pd.notna(raw):
                                try:
                                    card[col] = (
                                        float(raw)
                                        if isinstance(default, float)
                                        else int(float(raw))
                                    )
                                except (ValueError, TypeError):
                                    card[col] = default
                            else:
                                card[col] = default
                        else:
                            card[col] = default

            cards.append(card)

        return cards

    @rx.var
    def obra_enterprise_data(self) -> Dict[str, Any]:
        """Extends obra_selected_data with enterprise columns (budget, equipe, risco)."""
        base = dict(self.obra_selected_data)

        target = self.obras_selected_contract
        if not target:
            return base

        code = target.split(" - ")[0].strip() if " - " in target else target
        df = self._data.get("obras")

        if df is not None and not df.empty and "contrato" in df.columns:
            sub = df[df["contrato"] == code]
            if not sub.empty:
                if "realizado_pct" in sub.columns:
                    base["avanco_pct"] = round(float(sub["realizado_pct"].mean()), 1)

                first = sub.iloc[0]
                for col, default in [
                    ("budget_planejado", 0.0),
                    ("budget_realizado", 0.0),
                    ("equipe_presente_hoje", 0),
                    ("efetivo_planejado", 0),
                    ("chuva_acumulada_mm", 0.0),
                    ("risco_geral_score", 0),
                ]:
                    if col in first.index:
                        raw = first[col]
                        if pd.notna(raw):
                            try:
                                base[col] = (
                                    float(raw)
                                    if isinstance(default, float)
                                    else int(float(raw))
                                )
                            except (ValueError, TypeError):
                                base[col] = default
                        else:
                            base[col] = default
                    else:
                        base[col] = default

        return base

    @rx.var
    def obra_budget_chart(self) -> List[Dict[str, Any]]:
        """Budget planejado vs realizado for bar chart visualization."""
        data = self.obra_enterprise_data
        bp = float(data.get("budget_planejado", 0) or 0)
        br = float(data.get("budget_realizado", 0) or 0)
        if bp == 0 and br == 0:
            return []
        return [
            {"categoria": "Planejado", "valor": bp},
            {"categoria": "Realizado", "valor": br},
        ]

    @rx.var
    def obra_kpi_fmt(self) -> Dict[str, Any]:
        """Pre-formatted KPI display strings for the obras detail view.
        All rounding and formatting done server-side to avoid float display issues.
        """
        data = self.obra_enterprise_data
        bp = float(data.get("budget_planejado", 0) or 0)
        br = float(data.get("budget_realizado", 0) or 0)
        equipe = int(data.get("equipe_presente_hoje", 0) or 0)
        efetivo = int(data.get("efetivo_planejado", 0) or 0)
        risco = int(data.get("risco_geral_score", 0) or 0)
        avanco = float(data.get("avanco_pct", 0) or 0)

        # Disciplinas em risco
        disc_data = self.disciplina_progress_chart
        disc_total = len(disc_data)
        disc_em_risco = sum(
            1
            for d in disc_data
            if float(d.get("realizado_pct", 0)) < float(d.get("previsto_pct", 0))
        )
        disc_val = f"{disc_em_risco} / {disc_total}" if disc_total > 0 else "— / —"
        if disc_total == 0:
            disc_sub = "Sem dados de disciplina"
            disc_icon_color = "#2A9D8F"
        elif disc_em_risco == 0:
            disc_sub = "✓ Todas em dia"
            disc_icon_color = "#2A9D8F"
        elif disc_em_risco <= 2:
            disc_sub = f"⚠ {disc_em_risco} com atraso"
            disc_icon_color = "#F59E0B"
        else:
            disc_sub = f"✕ {disc_em_risco} em atraso"
            disc_icon_color = "#EF4444"

        # Budget
        bp_fmt = f"R$ {bp / 1_000_000:.1f}M" if bp > 0 else "—"
        br_fmt = f"R$ {br / 1_000_000:.1f}M" if br > 0 else "—"
        budget_over = False
        var_fmt = "Orçamento não configurado"
        budget_bar_pct = 0
        budget_exec_rate_fmt = "—"
        budget_bar_label = "—"
        budget_color = "#2A9D8F"
        if bp > 0:
            exec_rate = br / bp * 100
            budget_over = exec_rate > 100
            budget_color = "#EF4444" if budget_over else "#2A9D8F"
            if budget_over:
                var_fmt = f"▲ {exec_rate:.1f}% do orçamento executado"
            else:
                var_fmt = f"▼ {exec_rate:.1f}% do orçamento executado"
            budget_bar_pct = min(int(exec_rate), 100)
            budget_exec_rate_fmt = f"{exec_rate:.1f}%"
            budget_bar_label = f"{exec_rate:.1f}% do orçamento executado"

        # Equipe
        equipe_val = f"{equipe} / {efetivo}"
        if efetivo > 0:
            equipe_pct = equipe / efetivo * 100
            equipe_sub = (
                f"⚠ {equipe_pct:.0f}% do efetivo"
                if equipe_pct < 70
                else f"✓ {equipe_pct:.0f}% do efetivo"
            )
        else:
            equipe_sub = "Planejado não definido"

        # Risco
        if risco >= 60:
            risco_label = "CRÍTICO"
            risco_color = "#EF4444"
            risco_bg = "rgba(239, 68, 68, 0.1)"
        elif risco >= 30:
            risco_label = "MODERADO"
            risco_color = "#F59E0B"
            risco_bg = "rgba(245, 158, 11, 0.12)"
        else:
            risco_label = "CONTROLADO"
            risco_color = "#2A9D8F"
            risco_bg = "rgba(42, 157, 143, 0.15)"

        return {
            "budget_planejado_fmt": bp_fmt,
            "budget_realizado_fmt": br_fmt,
            "budget_variacao_fmt": var_fmt,
            "budget_over": budget_over,
            "budget_bar_pct": budget_bar_pct,
            "budget_exec_rate_fmt": budget_exec_rate_fmt,
            "budget_bar_label": budget_bar_label,
            "budget_color": budget_color,
            "equipe_val": equipe_val,
            "equipe_sub": equipe_sub,
            "risco_val": str(risco),
            "risco_label": risco_label,
            "risco_color": risco_color,
            "risco_bg": risco_bg,
            "avanco_fmt": f"{avanco:.1f}%",
            "disc_val": disc_val,
            "disc_sub": disc_sub,
            "disc_icon_color": disc_icon_color,
        }

    @rx.var
    def disciplina_gauges_list(self) -> List[Dict[str, Any]]:
        """Pre-computed semi-circle gauge data for each discipline.
        SVG stroke-dasharray values calculated server-side.
        r=38, C=2*pi*38≈238.76, SEMI=C/2≈119.38
        stroke-dashoffset=-119.38 positions arc start at 9-o'clock (left).
        """
        data = self.disciplina_progress_chart
        r_svg = 38  # SVG circle radius
        cx, cy = 50, 50  # SVG circle center
        C = 2 * math.pi * r_svg  # ≈ 238.76
        SEMI = C / 2  # ≈ 119.38
        gauges = []
        for item in data:
            r_val = float(item.get("realizado_pct", 0))
            p_val = float(item.get("previsto_pct", 0))
            filled_r = round((r_val / 100) * SEMI, 2)

            if r_val >= p_val:
                color = "#2A9D8F"
                status = "on_track"
            elif r_val >= p_val - 15:
                color = "#F59E0B"
                status = "warning"
            else:
                color = "#EF4444"
                status = "delayed"

            # Previsto marker dot: position on the arc
            # Arc goes from 180° to 360° (left → top → right)
            angle = math.pi + (p_val / 100) * math.pi
            mx = round(cx + r_svg * math.cos(angle), 2)
            my = round(cy + r_svg * math.sin(angle), 2)

            gauges.append(
                {
                    "categoria": item.get("categoria", ""),
                    "realizado_pct": r_val,
                    "previsto_pct": p_val,
                    "realizado_pct_fmt": f"{r_val:.0f}%",
                    "previsto_pct_fmt": f"{p_val:.0f}%",
                    "pr_label": f"P:{p_val:.0f}% · R:{r_val:.0f}%",
                    "realizado_dash": f"{filled_r} {round(C, 2)}",
                    "status": status,
                    "color": color,
                    "marker_cx": str(mx),
                    "marker_cy": str(my),
                }
            )
        return gauges

    # ── O&M ──────────────────────────────────────────────────────

    @rx.var
    def _om_filtered(self) -> List[Dict[str, Any]]:
        """O&M data filtered by project and time period with lifetime cumulative calculation"""
        from datetime import datetime, timedelta

        import pandas as pd

        # 1. Start with full O&M list
        data = self.om_list
        if not data:
            return []

        df = pd.DataFrame(data)
        if df.empty:
            return []

        # Ensure data column is datetime for sorting
        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"], errors="coerce")

        # 2. Filter by project FIRST to calculate project-specific running total
        if self.om_project_filter and self.om_project_filter != "Todos":
            df = df[df["contrato"] == self.om_project_filter]

        if df.empty:
            return []

        # 3. Calculate Cumulative Lifetime Production for this project
        # Sort chronologically to ensure cumsum is correct regardless of source order
        df = df.sort_values("data")

        # Recalculate accumulated since source CSV might be missing it or have partial data
        # 'energia_injetada_kwh' is our base value
        if "energia_injetada_kwh" in df.columns:
            df["acumulado_kwh"] = pd.to_numeric(df["energia_injetada_kwh"], errors="coerce").fillna(0).cumsum()

        # 4. Apply time filtering AFTER cumulative calculation
        # This allows us to see 'Total Accumulated' for a month even if previous months are hidden
        if self.om_time_filter:
            now = datetime.now()
            if self.om_time_filter == "Mês":
                cutoff = now - timedelta(days=30)
                df = df[df["data"] >= cutoff]
            elif self.om_time_filter == "Trimestre":
                cutoff = now - timedelta(days=90)
                df = df[df["data"] >= cutoff]
            elif self.om_time_filter == "Ano":
                cutoff = now - timedelta(days=365)
                df = df[df["data"] >= cutoff]

        return df.to_dict("records")

    @rx.var
    def om_energia_injetada_fmt(self) -> str:
        data = self._om_filtered
        if not data:
            return "0 kWh"
        total = sum(float(d.get("energia_injetada_kwh", 0) or 0) for d in data)
        return f"{total:,.0f} kWh".replace(",", ".")

    @rx.var
    def om_acumulado_fmt(self) -> str:
        data = self._om_filtered
        if not data:
            return "0 kWh"
        # Cumulative running total is the maximum reached in the filtered window
        total = max(float(d.get("acumulado_kwh", 0) or 0) for d in data)
        return f"{total:,.0f} kWh".replace(",", ".")

    @rx.var
    def om_performance_fmt(self) -> str:
        data = self._om_filtered
        if not data:
            return "0%"
        prev = sum(float(d.get("geracao_prevista_kwh", 0) or 0) for d in data)
        inj = sum(float(d.get("energia_injetada_kwh", 0) or 0) for d in data)
        if prev > 0:
            return f"{(inj / prev * 100):.1f}%"
        return "0%"

    @rx.var
    def om_fat_liquido_fmt(self) -> str:
        data = self._om_filtered
        if not data:
            return "R$ 0,00"
        val = sum(float(d.get("faturamento_liquido", 0) or 0) for d in data)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def om_geracao_chart(self) -> List[Dict[str, Any]]:
        data = self._om_filtered
        if not data:
            return []
        df = pd.DataFrame(data)
        if "mes_ano" not in df.columns:
            return []

        # Ensure chronological order
        if "data" in df.columns:
            df = df.sort_values("data")

        agg_dict = {}
        for col, func in [
            ("geracao_prevista_kwh", "sum"),
            ("energia_injetada_kwh", "sum"),
            ("acumulado_kwh", "max"),
        ]:
            if col in df.columns:
                agg_dict[col] = func
        if not agg_dict:
            return []

        grouped = (
            df.groupby("mes_ano", sort=False)
            .agg(agg_dict)
            .reset_index()
        )

        for col in ["geracao_prevista_kwh", "energia_injetada_kwh", "acumulado_kwh"]:
            if col in grouped.columns:
                grouped[col] = pd.to_numeric(grouped[col], errors="coerce").fillna(0).round(0)
        return grouped.to_dict("records")

    @rx.var
    def om_table_data(self) -> List[Dict[str, Any]]:
        """O&M table data grouped by month"""
        data = self._om_filtered
        if not data:
            return []
        df = pd.DataFrame(data)
        if "mes_ano" not in df.columns:
            return []

        # Ensure chronological order
        if "data" in df.columns:
            df = df.sort_values("data")

        agg_cols = {}
        for col in [
            "energia_injetada_kwh",
            "compensado_kwh",
            "acumulado_kwh",
            "valor_faturado",
            "gestao",
            "faturamento_liquido",
        ]:
            if col in df.columns:
                # Cumulative values get 'max' (end of month value), others get 'sum'
                agg_cols[col] = "sum" if col != "acumulado_kwh" else "max"

        grouped = df.groupby("mes_ano", sort=False).agg(agg_cols).reset_index()
        for col in grouped.select_dtypes(include=["float64", "float32"]).columns:
            grouped[col] = grouped[col].round(2)
        return grouped.to_dict("records")

    # ── Analytics ────────────────────────────────────────────────

    @rx.var
    def analytics_atraso_medio(self) -> float:
        if not self.obras_list:
            return 0.0
        diffs = []
        for o in self.obras_list:
            r = float(o.get("realizado_pct", 0) or 0)
            p = float(o.get("previsto_pct", 0) or 0)
            d = r - p
            if d < 0:
                diffs.append(d)
        if diffs:
            return round(sum(diffs) / len(diffs), 1)
        return 0.0

    @rx.var
    def analytics_churn_risk(self) -> int:
        if not self.contratos_list:
            return 0
        return len([c for c in self.contratos_list if c.get("status") in ["Em Risco", "Atrasado"]])

    @rx.var
    def analytics_conclusao_rate(self) -> float:
        if not self.projetos_list:
            return 0.0
        concluidos = len([p for p in self.projetos_list if p.get("conclusao_pct", 0) >= 100])
        return (
            round((concluidos / len(self.projetos_list) * 100), 1)
            if len(self.projetos_list) > 0
            else 0.0
        )

    @rx.var
    def forecast_revenue_chart(self) -> List[Dict[str, Any]]:
        months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
        data = []
        base = 100000.0
        for i, m in enumerate(months):
            data.append(
                {
                    "name": m,
                    "real": round(base * (1 + i * 0.1), 2),
                    "previsto": round(base * (1 + i * 0.12), 2),
                }
            )
        return data

    # ── Chat ─────────────────────────────────────────────────────
    # Chat implementation moved to async send_message() at line 68

    # ── Weather ──────────────────────────────────────────────────

    weather_data: Optional[Dict[str, Any]] = None
    weather_loading: bool = False
    weather_risk_level: str = "Unknown"
    weather_location_name: str = "Recife, PE"

    @rx.event(background=True)
    async def select_obra_detail(self, label: str):
        """Navigate to obra detail view and trigger AI + weather in parallel."""
        async with self:
            self.obras_selected_contract = label
            self.obra_insight_text = ""
            self.obra_insight_loading = True
            # Pre-set weather loading so the widget shows immediately
            self.weather_loading = True
            self.weather_data = {}
            # Dispatch both background tasks in the same block → start in parallel
            yield GlobalState.load_weather_data
            yield GlobalState.generate_obra_insight_bg

    @rx.event(background=True)
    async def deselect_obra(self):
        """Return to obras list view."""
        async with self:
            self.obras_selected_contract = ""
            self.obra_insight_text = ""
            self.obra_insight_loading = False

    @rx.event(background=True)
    async def generate_obra_insight_bg(self):
        """Background fire-and-forget AI insight for the selected obra."""
        import threading

        async with self:
            data = dict(self.obra_enterprise_data)
            disciplines = list(self.disciplina_progress_chart)
            selected = self.obras_selected_contract

        if not data or not selected:
            async with self:
                self.obra_insight_loading = False
            return

        # Build context
        delayed = [
            d["categoria"]
            for d in disciplines
            if float(d.get("realizado_pct", 0)) < float(d.get("previsto_pct", 0))
        ]
        on_track = [
            d["categoria"]
            for d in disciplines
            if float(d.get("realizado_pct", 0)) >= float(d.get("previsto_pct", 0))
        ]

        bp = float(data.get("budget_planejado", 0) or 0)
        br = float(data.get("budget_realizado", 0) or 0)
        if bp > 0:
            variance = ((br - bp) / bp) * 100
            if variance > 10:
                budget_status = f"estourado em {variance:.0f}%"
            elif variance > 0:
                budget_status = f"levemente acima em {variance:.0f}%"
            else:
                budget_status = f"dentro do previsto ({abs(variance):.0f}% de sobra)"
        else:
            budget_status = "orçamento não configurado"

        risco = int(data.get("risco_geral_score", 0) or 0)
        avanco = float(data.get("avanco_pct", 0) or 0)
        equipe_hoje = int(data.get("equipe_presente_hoje", 0) or 0)
        efetivo_plan = int(data.get("efetivo_planejado", 0) or 0)
        chuva = float(data.get("chuva_acumulada_mm", 0) or 0)

        context = (
            f"Obra: {data.get('contrato', '—')} — {data.get('cliente', '—')}\n"
            f"Localização: {data.get('localizacao', '—')}\n"
            f"Avanço físico médio: {avanco:.1f}%\n"
            f"Orçamento: {budget_status}\n"
            f"Equipe hoje: {equipe_hoje} pessoas (planejado: {efetivo_plan})\n"
            f"Chuva acumulada: {chuva:.0f}mm\n"
            f"Score de risco: {risco}/100\n"
            f"Disciplinas em dia: {', '.join(on_track) if on_track else 'nenhuma'}\n"
            f"Disciplinas em atraso: {', '.join(delayed) if delayed else 'nenhuma'}"
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Você é um analista sênior de obras de engenharia civil. "
                    "Gere UM parágrafo executivo (2 a 3 frases) de diagnóstico desta obra, em português. "
                    "Seja direto, objetivo e use os dados fornecidos. Destaque o status geral, "
                    "o principal risco e o ponto de atenção mais crítico. "
                    "NÃO use markdown, bullets ou títulos — apenas texto corrido profissional."
                ),
            },
            {"role": "user", "content": context},
        ]

        result: Dict[str, Any] = {"text": ""}

        def run_ai():
            try:
                from bomtempo.core.ai_client import ai_client as _ai

                result["text"] = _ai.query(messages)
            except Exception:
                risco_lvl = "crítico" if risco >= 60 else ("moderado" if risco >= 30 else "controlado")
                result["text"] = (
                    f"Obra com risco {risco_lvl} ({risco}/100). "
                    f"Avanço físico em {avanco:.0f}% com orçamento {budget_status}. "
                    + (
                        f"Atenção às disciplinas: {', '.join(delayed)}."
                        if delayed
                        else "Todas as disciplinas dentro do prazo."
                    )
                )

        t = threading.Thread(target=run_ai, daemon=True)
        t.start()
        t.join(timeout=30)

        async with self:
            self.obra_insight_text = result["text"] or "Análise em processamento..."
            self.obra_insight_loading = False

    async def select_obra_and_load_weather(self, value: str):
        """Sets the selected contract and reloads weather data."""
        self.set_obras_selected_contract(value)
        return GlobalState.load_weather_data

    @rx.event(background=True)
    async def load_weather_data(self):
        """Fetches weather data from OpenMeteo with Dynamic Geocoding.
        Background event — HTTP calls happen outside the state lock so card
        clicks are never blocked while weather is loading.
        """
        # ── Step 1: read needed state under the lock (no I/O here) ──────────
        async with self:
            contract_to_use = self.obras_selected_contract
            df_obras_ref = self._data.get("obras")
            df_contratos_ref = self._data.get("contratos")
            # Auto-detect first available contract when none is selected
            if not contract_to_use or contract_to_use == "Todos":
                for df_key in ("obras", "contratos"):
                    df_auto = self._data.get(df_key)
                    if (
                        df_auto is not None
                        and not df_auto.empty
                        and "localizacao" in df_auto.columns
                    ):
                        first_loc = df_auto["localizacao"].dropna()
                        first_loc = first_loc[first_loc.str.strip() != ""]
                        if not first_loc.empty and "contrato" in df_auto.columns:
                            contract_to_use = df_auto.loc[first_loc.index[0], "contrato"]
                        break

        # ── Step 2: pandas lookups outside the lock (CPU, no I/O) ──────────
        lat, lon = -8.05428, -34.8813  # Recife (fallback)
        location_name = "Recife, PE"
        city = None

        if contract_to_use and contract_to_use != "Todos":
            target_code = (
                contract_to_use.split(" - ")[0].strip()
                if " - " in contract_to_use
                else contract_to_use
            )
            logger.info(f"DEBUG: Processing weather for contract: '{target_code}'")

            if df_obras_ref is not None and not df_obras_ref.empty:
                for _, row in df_obras_ref.iterrows():
                    contrato_val = str(row.get("contrato", "")).strip()
                    if contrato_val and (
                        target_code in contrato_val or contrato_val in target_code
                    ):
                        city = str(row.get("localizacao", "")).strip()
                        logger.info(f"DEBUG: Found in OBRA. City: '{city}'")
                        break

            if not city and df_contratos_ref is not None and not df_contratos_ref.empty:
                for _, row in df_contratos_ref.iterrows():
                    contrato_val = str(row.get("contrato", "")).strip()
                    if contrato_val and (
                        target_code in contrato_val or contrato_val in target_code
                    ):
                        city = str(row.get("localizacao", "")).strip()
                        logger.info(f"DEBUG: Found in CONTRATOS. City: '{city}'")
                        break

        # ── Step 3: geocoding HTTP call — outside the lock ──────────────────
        if city and city.lower() not in ("", "nan"):
            logger.info(f"DEBUG: Geocoding city: '{city}'")
            try:
                coords = await weather_api.get_coordinates(city)
                if coords:
                    lat = coords["lat"]
                    lon = coords["lon"]
                    location_name = coords["name"]
            except Exception as geo_err:
                logger.error(f"Geocoding Error: {geo_err}")

        # ── Step 4: mark loading (brief lock) ───────────────────────────────
        async with self:
            self.weather_location_name = location_name
            self.weather_loading = True

        # ── Step 5: forecast HTTP call — outside the lock ───────────────────
        weather_result = None
        risk = "Unknown"
        try:
            weather_result = await weather_api.get_forecast(lat=lat, lon=lon)
            if weather_result:
                today_rain = weather_result.get("daily_rain_sum", [0])[0]
                today_prob = weather_result.get("daily_rain_prob", [0])[0]
                current_rain = weather_result.get("rain", 0)
                if current_rain > 5 or today_rain > 15 or today_prob > 80:
                    risk = "High"
                elif current_rain > 0.5 or today_rain > 5 or today_prob > 50:
                    risk = "Medium"
                else:
                    risk = "Low"
        except Exception as e:
            logger.error(f"Error loading weather: {e}")

        # ── Step 6: write results to state (brief lock) ──────────────────────
        async with self:
            if weather_result:
                self.weather_data = weather_result
            self.weather_risk_level = risk
            self.weather_loading = False

    def _build_project_context_for_weather(self) -> str:
        """Extracts active obras and upcoming schedule milestones for weather cross-reference."""
        try:
            lines = []

            # Active obras — latest physical progress per project
            if "obras" in self._data and not self._data["obras"].empty:
                df = self._data["obras"].copy()
                if "projeto" in df.columns:
                    if "data" in df.columns:
                        df["data"] = pd.to_datetime(df["data"], errors="coerce")
                        agg_cols = [
                            c
                            for c in ["previsto_pct", "realizado_pct", "comentario"]
                            if c in df.columns
                        ]
                        latest = (
                            df.sort_values("data")
                            .dropna(subset=["data"])
                            .groupby("projeto")[agg_cols]
                            .last()
                            .reset_index()
                        )
                    else:
                        agg_cols = [
                            c
                            for c in ["previsto_pct", "realizado_pct"]
                            if c in df.columns
                        ]
                        latest = df.groupby("projeto")[agg_cols].last().reset_index()

                    # Only obras not yet 100% complete
                    if "realizado_pct" in latest.columns:
                        active = latest[latest["realizado_pct"] < 100]
                    else:
                        active = latest

                    if not active.empty:
                        lines.append(f"OBRAS EM EXECUÇÃO ({len(active)} ativas):")
                        for _, row in active.head(8).iterrows():
                            proj = row.get("projeto", "—")
                            realizado = row.get("realizado_pct", "?")
                            previsto = row.get("previsto_pct", "?")
                            lines.append(
                                f"  - {proj}: {realizado}% realizado / {previsto}% previsto"
                            )

            # Upcoming activities in project schedule (next 10 days)
            if "projeto" in self._data and not self._data["projeto"].empty:
                df = self._data["projeto"].copy()
                if "termino_previsto" in df.columns and "conclusao_pct" in df.columns:
                    today = pd.Timestamp.now()
                    df["termino_previsto"] = pd.to_datetime(
                        df["termino_previsto"], errors="coerce"
                    )
                    upcoming = df[
                        (df["termino_previsto"] >= today)
                        & (df["termino_previsto"] <= today + pd.Timedelta(days=10))
                        & (df["conclusao_pct"] < 100)
                    ]
                    if not upcoming.empty:
                        lines.append(
                            f"\nATIVIDADES COM PRAZO NOS PRÓXIMOS 10 DIAS ({len(upcoming)}):"
                        )
                        for _, row in upcoming.head(8).iterrows():
                            ativ = row.get("atividade", "—")
                            fase = row.get("fase", "—")
                            termino = row.get("termino_previsto")
                            pct = row.get("conclusao_pct", 0)
                            termino_str = str(termino.date()) if pd.notna(termino) else "—"
                            lines.append(
                                f"  - [{fase}] {ativ} — prazo {termino_str}, {pct}% concluído"
                            )

            return "\n".join(lines) if lines else ""
        except Exception as e:
            logger.warning(f"Erro ao extrair contexto de projetos para clima: {e}")
            return ""

    async def analyze_weather_impact(self):
        """Context-aware weather impact analysis — crosses forecast with active obras and schedule."""
        if not self.weather_data:
            return

        self.is_analyzing = True
        self.show_analysis_dialog = True
        self.analysis_result = ""
        yield

        try:
            project_context = self._build_project_context_for_weather()
            result = AnalysisService.analyze_weather_impact(
                self.weather_data, self.weather_location_name, project_context
            )
            self.analysis_result = self._sanitize_markdown(result)
        except Exception as e:
            self.analysis_result = f"Erro na análise: {str(e)}"
            logger.error(f"Erro analyze_weather_impact: {e}")
        finally:
            self.is_analyzing = False
