"""
Módulo para extraer timestamps de nombres de archivos de audio de WhatsApp.
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path


class TimestampParser:
    """Parser para extraer timestamps de nombres de archivos de WhatsApp."""

    # Patrón específico para archivos PTT de WhatsApp
    PATTERNS = [
        # Patrón: PTT-YYYYMMDD-WAXXXX
        r"PTT-(\d{8})-WA(\d{4})",
    ]

    def __init__(self):
        self.compiled_patterns = [re.compile(pattern) for pattern in self.PATTERNS]

    def extract_timestamp(self, filename: str) -> Optional[datetime]:
        """
        Extrae el timestamp de un nombre de archivo de audio.

        Args:
            filename: Nombre del archivo de audio

        Returns:
            datetime object si se encuentra timestamp, None en caso contrario
        """
        filename = Path(filename).stem  # Remover extensión

        for i, pattern in enumerate(self.compiled_patterns):
            match = pattern.search(filename)
            if match:
                try:
                    return self._parse_match(match, i)
                except (ValueError, IndexError):
                    continue

        return None

    def _parse_match(self, match: re.Match, pattern_index: int) -> datetime:
        """Parsea el match según el patrón encontrado."""
        groups = match.groups()

        if pattern_index == 0:  # PTT-YYYYMMDD-WAXXXX
            date_str = groups[0]  # YYYYMMDD
            # Para PTT solo tenemos la fecha, usamos medianoche como hora por defecto
            return datetime.strptime(date_str, "%Y%m%d")

        raise ValueError(f"Patrón no reconocido: {pattern_index}")

    def is_audio_file(self, filename: str) -> bool:
        """
        Verifica si un archivo es de audio basado en su extensión.

        Args:
            filename: Nombre del archivo

        Returns:
            True si es archivo de audio, False en caso contrario
        """
        return Path(filename).suffix.lower() == ".opus"

    def get_audio_files_with_timestamps(
        self, directory: str
    ) -> list[Tuple[str, datetime]]:
        """
        Obtiene todos los archivos de audio con sus timestamps de un directorio.

        Args:
            directory: Directorio a escanear

        Returns:
            Lista de tuplas (ruta_archivo, timestamp)
        """
        audio_files = []
        directory_path = Path(directory)

        if not directory_path.exists():
            return audio_files

        for file_path in directory_path.iterdir():
            if file_path.is_file() and self.is_audio_file(file_path.name):
                timestamp = self.extract_timestamp(file_path.name)
                if timestamp:
                    audio_files.append((str(file_path), timestamp))

        # Ordenar por timestamp
        audio_files.sort(key=lambda x: x[1])
        return audio_files


def test_timestamp_parser():
    """Función de prueba para el parser de timestamps."""
    parser = TimestampParser()

    test_files = [
        "PTT-20250717-WA0056.opus",
        "PTT-20250613-WA0020.opus",
        "PTT-20250613-WA0056.opus",
    ]

    print("Probando parser de timestamps:")
    for filename in test_files:
        timestamp = parser.extract_timestamp(filename)
        print(f"{filename} -> {timestamp}")


if __name__ == "__main__":
    test_timestamp_parser()
