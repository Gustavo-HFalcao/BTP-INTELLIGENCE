import os
import sys

# Garante que o diretório atual está no PYTHON PATH para conseguir importar 'bomtempo'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from bomtempo.core.tts_service import TTSService
from bomtempo.core.logging_utils import get_logger

logger = get_logger(__name__)

def main():
    print("Iniciando Teste do TTS + Storage Bucket...")
    url = TTSService.generate_speech("Teste de comunicação com o bucket do Supabase. Respondendo do terminal.")
    print("\n[RESULTADO DA API]:", url)
    
if __name__ == "__main__":
    main()
