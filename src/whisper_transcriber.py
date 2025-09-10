"""
Módulo para transcripción de audios usando OpenAI Whisper.
"""

import soundfile as sf
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from openai import OpenAI
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Clase para manejar la transcripción de audios usando la API de OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model = "gpt-4o-transcribe"

    def convert_opus_to_wav(self, opus_path: str) -> str:
        wav_path = opus_path.replace(".opus", ".wav")
        # Read Opus file using soundfile
        data, samplerate = sf.read(opus_path)
        # Write as WAV with 16-bit PCM
        sf.write(wav_path, data, samplerate, subtype="PCM_16")
        return wav_path

    def transcribe_audio(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")
        ext = audio_file.suffix.lower()
        if ext == ".opus":
            audio_path = self.convert_opus_to_wav(str(audio_file))
        client = OpenAI(api_key=self.api_key)
        try:
            logger.info(f"Transcribiendo (API): {Path(audio_path).name}")
            with open(audio_path, "rb") as f:
                tx = client.audio.transcriptions.create(
                    file=f, model=self.model, response_format="text", language=language
                )
            transcription_data = {
                "text": tx.strip(),
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
