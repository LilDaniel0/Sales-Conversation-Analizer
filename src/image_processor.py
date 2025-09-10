"""
Módulo para procesar imágenes de conversaciones de WhatsApp.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Procesador para imágenes de conversaciones de WhatsApp."""

    def __init__(self, input_directory: str):
        """
        Inicializa el procesador de imágenes.

        Args:
            input_directory: Directorio donde están las imágenes
        """
        self.input_directory = Path(input_directory)
        self.supported_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

    def get_image_files(self) -> List[Path]:
        """
        Obtiene todos los archivos de imagen del directorio.

        Returns:
            Lista de rutas a archivos de imagen
        """
        if not self.input_directory.exists():
            logger.warning(f"Directorio no encontrado: {self.input_directory}")
            return []

        image_files = []
        for file_path in self.input_directory.iterdir():
            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.supported_formats
            ):
                image_files.append(file_path)

        logger.info(f"Encontradas {len(image_files)} imágenes")
        return image_files

    def extract_timestamp_from_filename(self, filename: str) -> Optional[datetime]:
        """
        Extrae timestamp del nombre de archivo de imagen.

        Args:
            filename: Nombre del archivo de imagen

        Returns:
            Timestamp extraído o None si no se encuentra
        """
        # Patrones comunes para imágenes de WhatsApp
        patterns = [
            r"IMG-(\d{8})-WA(\d{4})",  # IMG-YYYYMMDD-WAXXXX
            r"IMG_(\d{8})_(\d{6})",  # IMG_YYYYMMDD_HHMMSS
            r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})",  # YYYYMMDD_HHMMSS
        ]

        import re

        filename_stem = Path(filename).stem

        for pattern in patterns:
            match = re.search(pattern, filename_stem)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 6:  # YYYYMMDD_HHMMSS
                        year, month, day, hour, minute, second = groups[:6]
                        return datetime(
                            int(year),
                            int(month),
                            int(day),
                            int(hour),
                            int(minute),
                            int(second),
                        )
                    elif len(groups) == 2:  # IMG-YYYYMMDD-WAXXXX
                        date_str = groups[0]
                        return datetime.strptime(date_str, "%Y%m%d")
                except (ValueError, IndexError):
                    continue

        return None

    def get_images_with_timestamps(self) -> List[Tuple[Path, Optional[datetime]]]:
        """
        Obtiene imágenes con sus timestamps.

        Returns:
            Lista de tuplas (ruta_imagen, timestamp)
        """
        image_files = self.get_image_files()
        images_with_timestamps = []

        for image_path in image_files:
            timestamp = self.extract_timestamp_from_filename(image_path.name)
            images_with_timestamps.append((image_path, timestamp))

        # Ordenar por timestamp (las que no tienen timestamp van al final)
        images_with_timestamps.sort(key=lambda x: x[1] or datetime.max)

        return images_with_timestamps

    def create_image_reference(
        self, image_path: Path, timestamp: Optional[datetime], sender: str = "Imagen"
    ) -> str:
        """
        Crea una referencia de texto para una imagen.

        Args:
            image_path: Ruta a la imagen
            timestamp: Timestamp de la imagen
            sender: Nombre del remitente

        Returns:
            Línea de texto formateada para WhatsApp
        """
        if timestamp:
            date_str = timestamp.strftime("%d/%m/%Y")
            time_str = timestamp.strftime("%H:%M:%S")
            return f"[{date_str}, {time_str}] {sender}: [Imagen: {image_path.name}]"
        else:
            return f"[Sin timestamp] {sender}: [Imagen: {image_path.name}]"

    def process_images_for_text_file(self, text_processor) -> int:
        """
        Procesa todas las imágenes y las inserta en el archivo de texto.

        Args:
            text_processor: Instancia de WhatsAppTextProcessor

        Returns:
            Número de imágenes procesadas
        """
        images_with_timestamps = self.get_images_with_timestamps()
        processed_count = 0

        for image_path, timestamp in images_with_timestamps:
            try:
                if timestamp:
                    # Crear referencia de imagen
                    image_reference = self.create_image_reference(image_path, timestamp)

                    # Insertar en el archivo de texto
                    if text_processor.insert_transcription(
                        f"[Imagen: {image_path.name}]", timestamp, "Imagen"
                    ):
                        processed_count += 1
                        logger.info(f"Imagen procesada: {image_path.name}")
                else:
                    logger.warning(f"Imagen sin timestamp: {image_path.name}")

            except Exception as e:
                logger.error(f"Error procesando imagen {image_path.name}: {e}")

        logger.info(f"Procesadas {processed_count} imágenes")
        return processed_count

    def get_image_info(self, image_path: Path) -> Dict[str, any]:
        """
        Obtiene información básica de una imagen.

        Args:
            image_path: Ruta a la imagen

        Returns:
            Diccionario con información de la imagen
        """
        try:
            stat = image_path.stat()
            timestamp = self.extract_timestamp_from_filename(image_path.name)

            return {
                "name": image_path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "timestamp": timestamp,
                "extension": image_path.suffix.lower(),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
            }
        except Exception as e:
            logger.error(f"Error obteniendo info de imagen {image_path}: {e}")
            return {}


def test_image_processor():
    """Función de prueba para el procesador de imágenes."""
    # Crear directorio de prueba
    test_dir = Path("test_images")
    test_dir.mkdir(exist_ok=True)

    # Crear archivos de prueba (simulados)
    test_files = [
        "IMG-20231215-WA0001.jpg",
        "IMG_20231215_143022.png",
        "20231215_143022.gif",
    ]

    for filename in test_files:
        (test_dir / filename).touch()

    # Probar procesador
    processor = ImageProcessor(str(test_dir))
    images_with_timestamps = processor.get_images_with_timestamps()

    print(f"Imágenes encontradas: {len(images_with_timestamps)}")
    for image_path, timestamp in images_with_timestamps:
        print(f"{image_path.name} -> {timestamp}")

    # Limpiar directorio de prueba
    import shutil

    shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_image_processor()
