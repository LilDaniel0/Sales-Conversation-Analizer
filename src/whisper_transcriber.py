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
        data, samplerate = sf.read(
            opus_path
        )  # puede lanzar excepción si está malformado
        sf.write(wav_path, data, samplerate, subtype="PCM_16")
        return wav_path

    def transcribe_audio(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        audio_file = Path(audio_path)
        if not audio_file.exists():
            # No levantamos excepción: devolvemos dict con error para que el lote siga
            err_msg = f"Archivo de audio no encontrado: {audio_path}"
            logger.error(err_msg)
            return {
                "text": "",
                "language": language or "unknown",
                "segments": [],
                "audio_path": str(audio_file),
                "duration": 0.0,
                "error": err_msg,
            }

        original_path = str(audio_file)
        working_path = original_path

        # --- Conversión a WAV protegida ---
        if audio_file.suffix.lower() == ".opus":
            try:
                working_path = self.convert_opus_to_wav(original_path)
            except Exception as conv_err:
                # Si el .opus está corrupto, reportamos el error y continuamos con el siguiente archivo
                logger.error(f"Error convirtiendo {audio_file.name} a WAV: {conv_err}")
                return {
                    "text": "",
                    "language": language or "unknown",
                    "segments": [],
                    "audio_path": str(
                        audio_file
                    ),  # mantenemos la ruta original en el payload
                    "duration": 0.0,
                    "error": f"Conversión a WAV falló: {conv_err}",
                }

        client = OpenAI(api_key=self.api_key)
        try:
            logger.info(f"Transcribiendo (API): {Path(working_path).name}")
            with open(working_path, "rb") as f:
                tx = client.audio.transcriptions.create(
                    file=f,
                    model=self.model,
                    response_format="text",
                    language=language,
                )
            transcription_data = {
                "text": tx.strip(),
                "language": language or "unknown",
                "segments": [],
                "audio_path": str(audio_file),  # ruta del audio original
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
        """Transcribe múltiples archivos de audio usando la API de OpenAI."""
        results: Dict[str, Dict[str, Any]] = {}
        total = len(audio_files)

        for i, audio_path in enumerate(audio_files, 1):
            file_name = Path(audio_path).name
            logger.info(f"Procesando archivo {i}/{total}: {file_name}")

            try:
                results[audio_path] = self.transcribe_audio(audio_path, language)
            except Exception as e:
                # Cualquier excepción inesperada en este archivo no tumba el lote
                logger.error(f"Fallo procesando {file_name}: {e}")
                results[audio_path] = {
                    "text": "",
                    "language": language or "unknown",
                    "segments": [],
                    "audio_path": audio_path,
                    "duration": 0.0,
                    "error": f"Fallo inesperado: {e}",
                }

        return results
