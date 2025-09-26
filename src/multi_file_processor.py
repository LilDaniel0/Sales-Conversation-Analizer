"""
Coordinador principal para procesamiento de múltiples archivos ZIP simultáneamente.
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .processing_job import ProcessingJob

logger = logging.getLogger(__name__)


class MultiFileProcessor:
    """Coordinador principal que maneja múltiples archivos ZIP simultáneamente."""

    def __init__(self, max_workers: int = 3):
        """
        Inicializa el procesador múltiple.

        Args:
            max_workers: Número máximo de trabajos simultáneos
        """
        self.max_workers = max_workers
        self.jobs: Dict[str, ProcessingJob] = {}
        self.lock = threading.Lock()
        self.input_dir = Path("input_data")
        self.output_dir = Path("output_data")
        self.processing_dir = self.input_dir / "processing"
        self.uploaded_files_dir = self.input_dir / "uploaded_files"

        # Crear directorios necesarios
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.uploaded_files_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MultiFileProcessor inicializado con {max_workers} workers")

    def submit_zip(self, zip_path: str, zip_name: str) -> str:
        """
        Crea y registra un job de procesamiento para un archivo ZIP.

        Args:
            zip_path: Ruta al archivo ZIP
            zip_name: Nombre original del archivo ZIP

        Returns:
            ID único del job creado
        """
        job_id = str(uuid.uuid4())[:8]  # ID corto único

        with self.lock:
            self.jobs[job_id] = ProcessingJob(
                job_id=job_id,
                zip_path=zip_path,
                zip_name=zip_name,
                processing_dir=self.processing_dir,
                output_dir=self.output_dir
            )

        logger.info(f"Job {job_id} creado para {zip_name}")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Obtiene el estado de un job específico.

        Args:
            job_id: ID del job

        Returns:
            Diccionario con el estado del job o None si no existe
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                return job.get_status()
        return None

    def get_all_jobs_status(self) -> Dict[str, Dict]:
        """
        Obtiene el estado de todos los jobs.

        Returns:
            Diccionario con el estado de todos los jobs
        """
        with self.lock:
            return {job_id: job.get_status() for job_id, job in self.jobs.items()}

    def process_all_jobs(self) -> Dict[str, Dict]:
        """
        Procesa todos los jobs registrados usando ThreadPoolExecutor.

        Returns:
            Diccionario con los resultados de todos los jobs
        """
        if not self.jobs:
            logger.warning("No hay jobs para procesar")
            return {}

        logger.info(f"Iniciando procesamiento de {len(self.jobs)} jobs con {self.max_workers} workers")

        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Enviar todos los jobs
            future_to_job = {
                executor.submit(job.run_complete_processing): job_id
                for job_id, job in self.jobs.items()
            }

            # Recoger resultados conforme van completándose
            for future in as_completed(future_to_job):
                job_id = future_to_job[future]
                try:
                    result = future.result()
                    results[job_id] = result
                    logger.info(f"Job {job_id} completado")
                except Exception as e:
                    logger.error(f"Job {job_id} falló: {e}")
                    results[job_id] = {
                        "success": False,
                        "error": str(e),
                        "job_id": job_id
                    }

        logger.info(f"Procesamiento completo. {len(results)} jobs procesados")
        return results

    def process_single_job(self, job_id: str) -> Dict:
        """
        Procesa un job individual.

        Args:
            job_id: ID del job a procesar

        Returns:
            Resultado del procesamiento
        """
        with self.lock:
            job = self.jobs.get(job_id)

        if not job:
            error_msg = f"Job {job_id} no encontrado"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        logger.info(f"Procesando job individual {job_id}")
        try:
            result = job.run_complete_processing()
            logger.info(f"Job {job_id} completado exitosamente")
            return result
        except Exception as e:
            logger.error(f"Error procesando job {job_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "job_id": job_id
            }

    def cleanup_completed_jobs(self) -> int:
        """
        Limpia los jobs completados y sus directorios de trabajo.

        Returns:
            Número de jobs limpiados
        """
        cleaned_count = 0

        with self.lock:
            completed_jobs = [
                job_id for job_id, job in self.jobs.items()
                if job.status in ["completed", "failed"]
            ]

        for job_id in completed_jobs:
            try:
                job = self.jobs[job_id]
                job.cleanup()
                del self.jobs[job_id]
                cleaned_count += 1
                logger.info(f"Job {job_id} limpiado")
            except Exception as e:
                logger.error(f"Error limpiando job {job_id}: {e}")

        logger.info(f"Limpiados {cleaned_count} jobs")
        return cleaned_count

    def cancel_job(self, job_id: str) -> bool:
        """
        Intenta cancelar un job (solo si está pendiente).

        Args:
            job_id: ID del job a cancelar

        Returns:
            True si se pudo cancelar, False en caso contrario
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.status == "pending":
                job.status = "cancelled"
                logger.info(f"Job {job_id} cancelado")
                return True

        logger.warning(f"No se pudo cancelar job {job_id}")
        return False