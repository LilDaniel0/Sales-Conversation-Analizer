"""
Módulo principal para procesar conversaciones de WhatsApp con transcripciones de audio.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .whisper_transcriber import WhisperTranscriber
from .text_processor import WhatsAppTextProcessor
from .image_processor import ImageProcessor

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConversationProcessor:
    """Procesador principal para conversaciones de WhatsApp."""

    def __init__(
        self, input_directory: str, text_file_path: str, language: Optional[str] = None
    ):
        """
        Inicializa el procesador de conversaciones.
        Args:
            input_directory: Directorio con archivos de audio e imágenes
            text_file_path: Ruta al archivo de texto de WhatsApp
            language: Idioma para transcripción (opcional)
        """
        self.input_directory = Path(input_directory)
        self.text_file_path = text_file_path
        self.language = language
        from src.config import Config

        self.whisper_transcriber = WhisperTranscriber(api_key=Config.OPENAI_API_KEY)
        self.text_processor = WhatsAppTextProcessor(self.text_file_path)
        self.image_processor = ImageProcessor(str(self.input_directory))
        logger.info(f"Procesador inicializado - Directorio: {self.input_directory}")
        logger.info(f"Archivo de texto: {self.text_file_path}")
        logger.info(f"Modelo OpenAI: {self.whisper_transcriber.model}")

    def process_audio_files(self) -> Dict[str, any]:
        """
        Procesa todos los archivos de audio y los transcribe.

        Returns:
            Diccionario con resultados del procesamiento
        """
        logger.info("Iniciando procesamiento de archivos de audio...")

        # Obtener archivos de audio
        audio_files = list(self.input_directory.glob("*.opus"))

        if not audio_files:
            logger.warning("No se encontraron archivos de audio .opus")
            return {"success": False, "message": "No se encontraron archivos de audio"}

        logger.info(f"Encontrados {len(audio_files)} archivos de audio")

        # Transcribir archivos
        try:
            transcriptions = self.whisper_transcriber.transcribe_multiple(
                [str(file_path) for file_path in audio_files], self.language
            )

            # Preparar transcripciones para inserción
            transcriptions_to_insert = []
            successful_transcriptions = 0

            for file_path in audio_files:
                str_file_path = str(file_path)
                if str_file_path in transcriptions:
                    transcription_data = transcriptions[str_file_path]

                    if "error" not in transcription_data and transcription_data["text"]:
                        # Extraer el nombre del archivo para usar como sender
                        audio_filename = file_path.name

                        # Find the line number for insertion
                        insertion_point = self.text_processor.find_transcription_insertion_point_by_filename(
                            audio_filename
                        )

                        transcriptions_to_insert.append(
                            {
                                "text": transcription_data["text"],
                                "timestamp": (
                                    datetime.now()
                                    if insertion_point is None
                                    else self.text_processor.parse_whatsapp_format()[
                                        insertion_point
                                    ]["timestamp"]
                                ),
                                "audio_filename": audio_filename,
                                "sender": "Transcripción de Audio",
                            }
                        )
                        successful_transcriptions += 1
                    else:
                        logger.error(
                            f"Error en transcripción de {file_path.name}: "
                            f"{transcription_data.get('error', 'Texto vacío')}"
                        )

            # Insertar transcripciones en el archivo de texto
            if transcriptions_to_insert:
                inserted_count = self.text_processor.insert_multiple_transcriptions(
                    transcriptions_to_insert
                )

                result = {
                    "success": True,
                    "total_audio_files": len(audio_files),
                    "successful_transcriptions": successful_transcriptions,
                    "inserted_transcriptions": inserted_count,
                    "transcriptions": transcriptions_to_insert,
                }

                logger.info(
                    f"Procesamiento completado: {inserted_count} transcripciones insertadas"
                )
                return result
            else:
                logger.error("No se pudieron procesar las transcripciones")
                return {
                    "success": False,
                    "message": "Error en el procesamiento de transcripciones",
                }

        except Exception as e:
            logger.error(f"Error durante el procesamiento de audio: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    def process_image_files(self) -> Dict[str, any]:
        """
        Procesa archivos de imagen y los referencia en el texto.

        Returns:
            Diccionario con resultados del procesamiento
        """
        logger.info("Iniciando procesamiento de archivos de imagen...")

        try:
            processed_count = self.image_processor.process_images_for_text_file(
                self.text_processor
            )

            result = {"success": True, "processed_images": processed_count}

            logger.info(
                f"Procesamiento de imágenes completado: {processed_count} imágenes procesadas"
            )
            return result

        except Exception as e:
            logger.error(f"Error durante el procesamiento de imágenes: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    def process_all(self) -> Dict[str, any]:
        """
        Procesa todos los archivos (audio e imágenes).

        Returns:
            Diccionario con resultados completos del procesamiento
        """
        logger.info("Iniciando procesamiento completo...")

        # Crear backup del archivo de texto
        try:
            backup_path = self.text_processor.create_backup()
            logger.info(f"Backup creado: {backup_path}")
        except Exception as e:
            logger.warning(f"No se pudo crear backup: {e}")

        # Procesar audios
        audio_result = self.process_audio_files()

        # Procesar imágenes
        image_result = self.process_image_files()

        # Resultado combinado
        result = {
            "success": audio_result.get("success", False)
            or image_result.get("success", False),
            "audio_processing": audio_result,
            "image_processing": image_result,
            "timestamp": datetime.now().isoformat(),
        }

        if result["success"]:
            logger.info("Procesamiento completo exitoso")
        else:
            logger.error("Procesamiento completo falló")

        return result

    def get_processing_summary(self) -> Dict[str, any]:
        """
        Obtiene un resumen del estado actual del procesamiento.

        Returns:
            Diccionario con información del estado
        """
        # Contar archivos de audio
        audio_files = list(self.input_directory.glob("*.opus"))

        # Contar imágenes
        image_files = self.image_processor.get_image_files()

        # Contar mensajes en el texto
        message_count = self.text_processor.get_message_count()

        return {
            "audio files found": len(audio_files),
            "image files found": len(image_files),
            "whisper model": self.whisper_transcriber.model,
            "language": self.language,
        }

    def validate_inputs(self) -> Tuple[bool, List[str]]:
        """
        Valida que todos los inputs necesarios estén disponibles.

        Returns:
            Tupla (es_válido, lista_de_errores)
        """
        errors = []

        # Verificar directorio de entrada
        if not self.input_directory.exists():
            errors.append(f"Directorio de entrada no existe: {self.input_directory}")

        # Verificar archivo de texto
        if not Path(self.text_file_path).exists():
            errors.append(f"Archivo de texto no existe: {self.text_file_path}")

        # Verificar que hay archivos de audio
        audio_files = list(self.input_directory.glob("*.opus"))
        if not audio_files:
            errors.append("No se encontraron archivos de audio .opus")

        return len(errors) == 0, errors
