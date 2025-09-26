"""
Job individual para procesar un archivo ZIP con transcripciones de WhatsApp.
"""

import logging
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .conversation_processor import ConversationProcessor
from .config import Config
import sys
from pathlib import Path

# Add the parent directory to Python path to import main
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))
import main

logger = logging.getLogger(__name__)


class ProcessingJob:
    """Encapsula el procesamiento completo de un archivo ZIP individual."""

    def __init__(
        self,
        job_id: str,
        zip_path: str,
        zip_name: str,
        processing_dir: Path,
        output_dir: Path
    ):
        """
        Inicializa un job de procesamiento.

        Args:
            job_id: ID único del job
            zip_path: Ruta al archivo ZIP
            zip_name: Nombre original del archivo ZIP
            processing_dir: Directorio base para procesamiento
            output_dir: Directorio para archivos finales
        """
        self.job_id = job_id
        self.zip_path = Path(zip_path)
        self.zip_name = zip_name
        self.zip_stem = Path(zip_name).stem

        # Directorios únicos para este job
        self.work_dir = processing_dir / f"{self.zip_stem}_{job_id}"
        self.extract_dir = self.work_dir / "whatsapp_chats"
        self.output_dir = output_dir
        self.final_output_path = self.output_dir / f"{self.zip_stem}.txt"

        # Estado del job
        self.status = "pending"  # pending, preprocessing, processing, postprocessing, completed, failed
        self.progress = 0.0
        self.error = None
        self.result = None
        self.start_time = None
        self.end_time = None

        logger.info(f"Job {self.job_id} inicializado para {self.zip_name}")

    def get_status(self) -> Dict:
        """
        Obtiene el estado completo del job.

        Returns:
            Diccionario con toda la información del job
        """
        return {
            "job_id": self.job_id,
            "zip_name": self.zip_name,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "result": self.result,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "final_output_path": str(self.final_output_path) if self.final_output_path.exists() else None
        }

    def preprocess(self) -> bool:
        """
        Extrae el ZIP a un directorio único y prepara los archivos.

        Returns:
            True si el preprocesamiento fue exitoso, False en caso contrario
        """
        try:
            self.status = "preprocessing"
            self.progress = 0.1
            logger.info(f"Job {self.job_id}: Iniciando preprocesamiento")

            # Usar la función individual de main.py
            success = main.preprocess_single_zip(str(self.zip_path), self.work_dir)

            if success:
                self.progress = 0.5
                logger.info(f"Job {self.job_id}: Preprocesamiento completado")
                return True
            else:
                raise Exception("preprocess_single_zip returned False")

        except Exception as e:
            self.status = "failed"
            self.error = f"Error en preprocesamiento: {str(e)}"
            logger.error(f"Job {self.job_id}: {self.error}")
            return False

    def process(self) -> Dict:
        """
        Ejecuta la transcripción y procesamiento de audio.

        Returns:
            Diccionario con los resultados del procesamiento
        """
        try:
            self.status = "processing"
            self.progress = 0.6
            logger.info(f"Job {self.job_id}: Iniciando procesamiento de audio")

            # Configurar paths para el procesador
            media_dir = str(self.extract_dir)

            # Usar el nombre del archivo temporal que genera preprocess_single_zip
            zip_stem = self.zip_path.stem
            temp_filename = f"chat_{zip_stem}_{self.work_dir.name}.txt"
            text_file_path = str(self.output_dir / temp_filename)
            language = Config.WHISPER_LANGUAGE or None

            # Crear procesador
            processor = ConversationProcessor(
                input_directory=media_dir,
                text_file_path=text_file_path,
                language=language,
            )

            self.progress = 0.7

            # Validar inputs
            is_valid, errors = processor.validate_inputs()
            if not is_valid:
                raise ValueError(f"Validación fallida: {'; '.join(errors)}")

            # Procesar archivos de audio
            result = processor.process_audio_files()

            self.progress = 0.8
            self.result = result

            if result.get("success"):
                logger.info(f"Job {self.job_id}: Procesamiento de audio completado exitosamente")
            else:
                logger.warning(f"Job {self.job_id}: Procesamiento de audio con errores")

            return result

        except Exception as e:
            self.status = "failed"
            self.error = f"Error en procesamiento: {str(e)}"
            logger.error(f"Job {self.job_id}: {self.error}")
            return {"success": False, "error": str(e)}

    def postprocess(self) -> bool:
        """
        Finaliza el procesamiento renombrando el archivo a su nombre final.

        Returns:
            True si el postprocesamiento fue exitoso, False en caso contrario
        """
        try:
            self.status = "postprocessing"
            self.progress = 0.9
            logger.info(f"Job {self.job_id}: Iniciando postprocesamiento")

            # Usar la función individual de main.py
            success = main.postprocess_single_zip(
                str(self.zip_path),
                self.work_dir,
                self.final_output_path
            )

            if success:
                self.progress = 1.0
                self.status = "completed"
                self.end_time = datetime.now()
                logger.info(f"Job {self.job_id}: Postprocesamiento completado")
                return True
            else:
                raise Exception("postprocess_single_zip returned False")

        except Exception as e:
            self.status = "failed"
            self.error = f"Error en postprocesamiento: {str(e)}"
            logger.error(f"Job {self.job_id}: {self.error}")
            return False

    def run_complete_processing(self) -> Dict:
        """
        Ejecuta el procesamiento completo: preprocess -> process -> postprocess.

        Returns:
            Diccionario con el resultado final
        """
        self.start_time = datetime.now()
        logger.info(f"Job {self.job_id}: Iniciando procesamiento completo")

        try:
            # Fase 1: Preprocesamiento
            if not self.preprocess():
                return {"success": False, "error": self.error, "job_id": self.job_id}

            # Fase 2: Procesamiento principal
            process_result = self.process()
            if not process_result.get("success"):
                return {"success": False, "error": self.error or "Error en procesamiento", "job_id": self.job_id}

            # Fase 3: Postprocesamiento
            if not self.postprocess():
                return {"success": False, "error": self.error, "job_id": self.job_id}

            # Resultado exitoso
            final_result = {
                "success": True,
                "job_id": self.job_id,
                "zip_name": self.zip_name,
                "output_file": str(self.final_output_path),
                "processing_result": process_result,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": (self.end_time - self.start_time).total_seconds()
            }

            logger.info(f"Job {self.job_id}: Procesamiento completo exitoso")
            return final_result

        except Exception as e:
            self.status = "failed"
            self.error = f"Error inesperado: {str(e)}"
            self.end_time = datetime.now()
            logger.error(f"Job {self.job_id}: {self.error}")

            return {
                "success": False,
                "error": self.error,
                "job_id": self.job_id,
                "start_time": self.start_time,
                "end_time": self.end_time
            }

    def cleanup(self):
        """
        Limpia los directorios de trabajo del job.
        """
        try:
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir, ignore_errors=True)
                logger.info(f"Job {self.job_id}: Directorio de trabajo limpiado")

            # Limpiar archivo temporal si existe
            temp_file = self.output_dir / f"chat_{self.job_id}.txt"
            if temp_file.exists():
                temp_file.unlink()
                logger.info(f"Job {self.job_id}: Archivo temporal limpiado")

        except Exception as e:
            logger.error(f"Job {self.job_id}: Error durante limpieza: {e}")

    def __str__(self) -> str:
        """Representación string del job."""
        return f"ProcessingJob(id={self.job_id}, file={self.zip_name}, status={self.status})"