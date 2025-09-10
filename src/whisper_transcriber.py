"""
Módulo para transcripción de audios usando OpenAI Whisper.
"""

import requests
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Clase para manejar la transcripción de audios usando la API de OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model = "gpt-4o-mini-audio-preview"

    def transcribe_audio(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe un archivo de audio usando la API de OpenAI.
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": (audio_file.name, open(audio_file, "rb"), "audio/opus")}
        data = {"model": self.model}
        if language:
            data["language"] = language

        try:
            logger.info(f"Transcribiendo (API): {audio_file.name}")
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            transcription_data = {
                "text": result.get("text", "").strip(),
                "language": language or "unknown",
                "segments": [],
                "audio_path": str(audio_file),
                "duration": 0.0,
            }
            logger.info(
                f"Transcripción completada: {len(transcription_data['text'])} caracteres"
            )
            return transcription_data
        except Exception as e:
            logger.error(f"Error al transcribir {audio_file.name}: {e}")
            return {
                "text": "",
                "language": language or "unknown",
                "segments": [],
                "audio_path": str(audio_file),
                "duration": 0.0,
                "error": str(e),
            }

    # No se requiere duración ni segmentos con la API

    def transcribe_multiple(
        self, audio_files: list[str], language: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Transcribe múltiples archivos de audio usando la API de OpenAI.
        """
        results = {}
        for i, audio_path in enumerate(audio_files, 1):
            logger.info(
                f"Procesando archivo {i}/{len(audio_files)}: {Path(audio_path).name}"
            )
            results[audio_path] = self.transcribe_audio(audio_path, language)
        return results

    # No se requiere cambiar modelo, solo se usa el de la API
