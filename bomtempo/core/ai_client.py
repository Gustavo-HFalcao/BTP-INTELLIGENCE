import json
import os

from openai import OpenAI

from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

# Kimi API (Moonshot AI) Configuration
API_KEY = "sk-RkswUuLAZlphrur4HJIbwV0elSjm9NI6jLuSNStFZuHaCY2Q"
BASE_URL = "https://api.moonshot.ai/v1"

# Audio API Configuration (Moonshot doesn't support audio, use OpenAI or Groq)
# User must fill this if they want audio to work, or set OPENAI_API_KEY env var
OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY",
    "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",
)

# Vision API key (for fuel receipt analysis) — OPENAI_VISION_KEY in .env
OPENAI_VISION_KEY = os.environ.get("OPENAI_VISION_KEY", OPENAI_API_KEY)


class AIClient:
    """Client for interacting with Kimi AI via OpenAI-compatible API."""

    def __init__(self):
        # 1. Chat Client (Moonshot)
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
        )

        # 2. Audio Client (OpenAI Standard)
        # Only initialize if key is present to avoid errors
        if OPENAI_API_KEY:
            self.audio_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.audio_client = None

        # 3. Vision Client (OpenAI gpt-4o) — for receipt analysis
        if OPENAI_VISION_KEY:
            self.vision_client = OpenAI(api_key=OPENAI_VISION_KEY)
        else:
            self.vision_client = None

    def query_stream(self, messages: list[dict], model: str = "kimi-k2-turbo-preview"):
        """
        Streams a query to Kimi AI, yielding text chunks as they arrive.
        """
        try:
            logger.info(f"Streaming request to Kimi AI (model: {model})...")
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error streaming from Kimi AI: {e}")
            raise

    def query(self, messages: list[dict], model: str = "kimi-k2-turbo-preview") -> str:
        """
        Sends a query to Kimi AI.

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}, ...]
            model: Model ID to use.

        Returns:
            The content of the AI's response.
        """
        try:
            logger.info(f"Sending request to Kimi AI (model: {model})...")
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more factual answers
            )
            content = response.choices[0].message.content
            logger.info("Received response from Kimi AI.")
            return content
        except Exception as e:
            logger.error(f"Error querying Kimi AI: {e}")
            return "Desculpe, encontrei um erro ao processar sua solicitação. Tente novamente em instantes."

    def transcribe_audio(self, file_path: str) -> str:
        """
        Transcribes audio file to text using Whisper.
        """
        if not self.audio_client:
            logger.warning("Audio client not configured. Missing OPENAI_API_KEY.")
            return "[ERRO] Configuração de Áudio incompleta. Adicione uma OPENAI_API_KEY no arquivo ai_client.py para ativar a transcrição."

        try:
            logger.info(f"Transcribing audio file: {file_path}")
            with open(file_path, "rb") as audio_file:
                transcription = self.audio_client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, response_format="text"
                )
            logger.info("Transcription successful.")
            return str(transcription)
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return f"[ERRO] Falha na transcrição: {str(e)}"

    def analyze_receipt_image(self, image_b64: str, mime: str = "image/jpeg") -> dict:
        """
        Analyzes a fuel receipt image using gpt-4o Vision API.
        Returns a dict with extracted data or empty dict on failure.

        Expected return:
        {
            "fuel_type": "Gasolina",
            "liters": 40.5,
            "price_per_liter": 5.89,
            "total": 238.85,
            "date": "2024-01-15",
            "station": "Posto Shell",
            "confidence": 0.92
        }
        """
        if not self.vision_client:
            logger.warning("Vision client not configured. Set OPENAI_VISION_KEY in .env")
            return {}

        prompt = """Analise esta nota fiscal/cupom de abastecimento de combustível e extraia os dados.
Retorne SOMENTE um JSON válido, sem texto adicional, sem markdown, sem explicações.

Formato exato:
{"fuel_type": "Gasolina|Etanol|Diesel|GNV", "liters": 0.0, "price_per_liter": 0.0, "total": 0.0, "date": "YYYY-MM-DD", "station": "nome do posto", "confidence": 0.0}

- fuel_type: tipo de combustível encontrado na nota (Gasolina, Etanol, Diesel, GNV ou outro)
- liters: quantidade de litros abastecidos (número decimal)
- price_per_liter: preço por litro em reais (número decimal)
- total: valor total pago em reais (número decimal)
- date: data do abastecimento no formato YYYY-MM-DD (ou "" se não encontrado)
- station: nome do posto ou estabelecimento
- confidence: sua confiança na extração de 0.0 a 1.0

Se um campo não for encontrado, use null para números e "" para textos."""

        try:
            response = self.vision_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{image_b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=400,
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown code blocks if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            logger.info(f"✅ Vision API: confidence={result.get('confidence', 0)}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Vision API JSON parse error: {e} — raw: {raw[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return {}


# Singleton instance
ai_client = AIClient()
