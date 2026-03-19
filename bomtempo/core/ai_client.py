import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from bomtempo.core.logging_utils import get_logger

load_dotenv()
logger = get_logger(__name__)

# Chat AI Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
API_KEY = OPENAI_API_KEY
BASE_URL = "https://api.openai.com/v1"

# Vision API key (for fuel receipt analysis)
OPENAI_VISION_KEY = os.environ.get("OPENAI_VISION_KEY", OPENAI_API_KEY)


class AIClient:
    """Client for interacting with AI via OpenAI-compatible API with Agentic Tool Support."""

    def __init__(self):
        # 1. Chat Client (OpenAI/Kimi)
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
        )

        # 2. Audio Client (OpenAI Standard)
        if OPENAI_API_KEY:
            self.audio_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.audio_client = None

        # 3. Vision Client (OpenAI gpt-4o)
        if OPENAI_VISION_KEY:
            self.vision_client = OpenAI(api_key=OPENAI_VISION_KEY)
        else:
            self.vision_client = None

    def query_agentic(self, messages: list[dict], tools: list[dict] = None, model: str = "gpt-4o", force_tool: bool = False):
        """
        Executes one turn of the agentic loop with tool calling support.

        Returns:
            str  — final text response when the model has no tool calls.
            ChatCompletionMessage — the raw message object when tool_calls are present.
                The caller is responsible for serializing it to dict and appending to messages.
        """
        try:
            logger.info(f"Agentic Query → {model} | msgs={len(messages)}")
            # Na primeira iteração (sem histórico de tool results), força o uso de tools
            # para evitar que a IA "anuncie" antes de agir.
            has_tool_results = any(m.get("role") == "tool" for m in messages)
            if tools and force_tool and not has_tool_results:
                tool_choice = "required"
            elif tools:
                tool_choice = "auto"
            else:
                tool_choice = "none"
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools or [],
                tool_choice=tool_choice,
                temperature=0.3,
                # Parallel tool calls desabilitado: garante ordem determinística
                # (executa get_schema_info antes de execute_sql antes de generate_chart_data)
                parallel_tool_calls=False,
            )
            response_message = response.choices[0].message

            if response_message.tool_calls:
                # Retorna o objeto bruto — o caller serializa e appenda ao histórico
                return response_message

            return response_message.content or ""

        except Exception as e:
            logger.error(f"Error in Agentic Query: {e}")
            return "Desculpe, falhei ao processar como agente. Tente novamente."

    def query_stream(self, messages: list[dict], model: str = "gpt-4o", max_tokens: int = 8192):
        """
        Streams a query, yielding text chunks as they arrive.
        """
        try:
            logger.info(f"Streaming request to AI (model: {model})...")
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error streaming from AI: {e}")
            raise

    def query(self, messages: list[dict], model: str = "gpt-4o") -> str:
        """Standard non-streaming completion."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error querying AI: {e}")
            return "Erro ao processar solicitação."

    def transcribe_audio(self, file_path: str) -> str:
        """Transcribes audio file using Whisper."""
        if not self.audio_client: return "[ERRO] Configuração incompleta."
        try:
            with open(file_path, "rb") as audio_file:
                transcription = self.audio_client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, response_format="text"
                )
            return str(transcription)
        except Exception as e:
            logger.error(f"Error transcribing: {e}")
            return f"[ERRO] {str(e)}"

    def analyze_receipt_image(self, image_b64: str, mime: str = "image/jpeg") -> dict:
        """Analyzes receipt using Vision API."""
        if not self.vision_client: return {}
        prompt = """Analise este cupom e retorne um JSON com: fuel_type, liters, price_per_liter, total, date, station, confidence."""
        try:
            response = self.vision_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}}]}],
                max_tokens=400,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            if "```" in raw: raw = raw.split("```")[1].replace("json", "")
            return json.loads(raw)
        except Exception: return {}


# Singleton instance
ai_client = AIClient()
