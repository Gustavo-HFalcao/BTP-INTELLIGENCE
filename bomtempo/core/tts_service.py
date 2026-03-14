import os
import uuid
from pathlib import Path

import reflex as rx

from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)


class TTSService:
    """
    Text-to-Speech Service using OpenAI's API.
    Converts text responses into audio files for the Conversation Mode.
    """

    @staticmethod
    def generate_speech(text: str) -> str:
        """
        Generates speech from text using OpenAI TTS-1.
        Saves to Reflex 'uploads' directory to allow dynamic serving.

        Args:
            text (str): The text to be spoken.

        Returns:
            str: The relative URL to the generated audio file (e.g., '/_upload/xyz.mp3').
                 Returns None if generation fails.
        """
        if not text:
            return None

        try:
            # Cleanup text (remove markdown like **, #, etc for smoother speech)
            clean_text = text.replace("**", "").replace("#", "").replace("- ", ". ")

            # Limit length to avoid huge costs/latency
            if len(clean_text) > 1000:
                clean_text = clean_text[:1000] + "..."

            # Generate unique filename
            filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"

            # Use Reflex Upload Directory (Runtime accessible)
            upload_dir = rx.get_upload_dir()
            path = Path(upload_dir)
            path.mkdir(parents=True, exist_ok=True)

            file_path = path / filename

            # Call OpenAI API
            import openai

            from bomtempo.core.ai_client import OPENAI_API_KEY

            # Check for API Key explicitly
            api_key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found. TTS skipped.")
                return None

            # Use the same client setup as AI Client
            client = openai.Client(api_key=api_key)

            response = client.audio.speech.create(
                model="tts-1", voice="onyx", input=clean_text  # Deep, executive voice
            )

            # Save to file
            with open(file_path, "wb") as f:
                f.write(response.content)

            # Verify file exists and has content
            if file_path.exists() and file_path.stat().st_size > 0:
                logger.info(f"TTS File Created: {file_path}")
            else:
                logger.error(f"TTS File Creation FAILED or EMPTY: {file_path}")
                return None

            # Return URL served by Reflex backend
            # Manually construct string to avoid Var boolean evaluation error in GlobalState
            # FIX: Prepend API URL to bypass frontend proxy issues (Test 4 confirmed backend works)
            # HARDCODED FIX for local dev since rx.get_api_url() is missing in this version
            api_url = "http://localhost:8000"
            web_path = f"{api_url}/_upload/{filename}"

            logger.info(f"TTS Audio generated successfully: {web_path}")
            return web_path

        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return None
