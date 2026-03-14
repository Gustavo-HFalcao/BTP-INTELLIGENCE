from datetime import datetime

import reflex as rx

from bomtempo.core.ai_client import ai_client
from bomtempo.core.ai_context import AIContext
from bomtempo.core.data_loader import DataLoader

# from bomtempo.core.openai_service import get_openai_client # Deprecated for this use case


class VoiceChatState(rx.State):
    """
    Estado Simplificado: Push-to-Talk (Transcrever + Chat apenas)
    Sem TTS / Sem Autoplay Handsfree (Removido por limitação de navegador)
    """

    # Chat State
    messages: list[dict] = []
    is_listening: bool = False  # Se Web Speech API está ouvindo
    is_processing: bool = False  # Se está gerando resposta da AI

    # Debug Legend
    debug_logs: list[str] = []

    def add_log(self, message: str):
        """Log visual"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.debug_logs.insert(0, f"[{timestamp}] {message}")
        if len(self.debug_logs) > 20:
            self.debug_logs.pop()

    def start_listening(self):
        """Ativa microfone via JS (Interaction One-Shot: Limpa histórico)"""
        self.messages = []  # Limpa o chat anterior
        self.is_listening = True
        self.add_log("Ouvindo...")
        return rx.call_script("""
            window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (window.SpeechRecognition) {
                if (!window.recognition) {
                    window.recognition = new window.SpeechRecognition();
                    window.recognition.continuous = false;
                    window.recognition.lang = 'pt-BR';
                    window.recognition.interimResults = false;
                    
                    window.recognition.onend = () => {
                        const input = document.getElementById('voice_status_input');
                        if(input) {
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(input, "stopped");
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    };

                    window.recognition.onresult = (event) => {
                        const transcript = event.results[0][0].transcript;
                        const input = document.getElementById('voice_transcript_input');
                        if (input) {
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(input, transcript);
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    };
                }
                window.recognition.start();
            } else {
                alert("Navegador não suporta reconhecimento de voz.");
            }
        """)

    def stop_listening(self):
        """Para microfone via JS"""
        self.is_listening = False
        self.add_log("Parando microfone...")
        return rx.call_script("if(window.recognition) window.recognition.stop();")

    def on_voice_status_change(self, status: str):
        """Callback do JS quando reconhecimento para"""
        if status == "stopped":
            self.is_listening = False

    async def process_transcript(self, text: str):
        """Recebe texto, envia para GPT (KIMI) e mostra resposta"""
        if not text:
            return

        self.is_listening = False
        self.is_processing = True
        self.add_log(f"Usuário: {text}")
        self.messages.append({"role": "user", "content": text})
        yield

        try:
            # 1. Carregar Contexto do Dashboard (Cacheado)
            loader = DataLoader()
            data = loader.load_all()

            # 2. Preparar Prompt do Sistema (Persona KIMI)
            # Detectar se é mobile? Voice Chat page pode ser desktop ou mobile.
            # Vamos assumir desktop/geral por enquanto ou criar um flag.
            system_prompt = AIContext.get_system_prompt(is_mobile=False)
            dashboard_context = AIContext.get_dashboard_context(data)

            # 3. Construir Mensagens com Contexto
            # O AIClient espera uma lista de mensagens completa incluindo system
            context_messages = [
                {
                    "role": "system",
                    "content": f"{system_prompt}\n\nContexto Atual:\n{dashboard_context}",
                }
            ]

            # Adicionar histórico recente (limitar para não estourar tokens)
            # Pegar as últimas 6 mensagens do chat atual
            recent_history = self.messages[-6:]
            context_messages.extend(recent_history)

            # 4. Consultar AI Client
            response_content = ai_client.query(context_messages)

            self.add_log(f"AI: {response_content[:30]}...")
            self.messages.append({"role": "assistant", "content": response_content})

        except Exception as e:
            error_msg = f"Erro ao processar: {str(e)}"
            self.add_log(error_msg)
            print(error_msg)
            self.messages.append(
                {
                    "role": "assistant",
                    "content": "Desculpe, estou com dificuldade para acessar os dados agora.",
                }
            )
        finally:
            self.is_processing = False
            yield
