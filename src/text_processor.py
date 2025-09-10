"""
Módulo para procesar el archivo de texto de WhatsApp y insertar transcripciones.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class WhatsAppTextProcessor:
    """Procesador para archivos de texto de WhatsApp."""

    def __init__(self, text_file_path: str):
        """
        Inicializa el procesador con la ruta al archivo de texto.

        Args:
            text_file_path: Ruta al archivo de texto de WhatsApp
        """
        self.text_file_path = Path(text_file_path)
        self.lines = []
        self._load_text_file()

    def _load_text_file(self):
        """Carga el archivo de texto en memoria."""
        try:
            if not self.text_file_path.exists():
                logger.warning(f"Archivo de texto no encontrado: {self.text_file_path}")
                return

            with open(self.text_file_path, "r", encoding="utf-8") as f:
                self.lines = f.readlines()

            logger.info(f"Archivo cargado: {len(self.lines)} líneas")
        except Exception as e:
            logger.error(f"Error al cargar archivo de texto: {e}")
            raise

    def parse_whatsapp_format(self) -> List[Dict[str, str]]:
        """
        Parsea el formato de WhatsApp y extrae mensajes con timestamps.

        Returns:
            Lista de diccionarios con información de cada mensaje
        """
        messages = []
        current_message = {}

        # Patrón para detectar inicio de mensaje: DD/M/YYYY, H:MM a.m./p.m. - Nombre:
        message_pattern = re.compile(
            r"^(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2}) (a\.m\.|p\.m\.) - ([^:]+): (.+)$"
        )

        for i, line in enumerate(self.lines):
            line = line.strip()
            if not line:
                continue

            match = message_pattern.match(line)
            if match:
                # Guardar mensaje anterior si existe
                if current_message:
                    messages.append(current_message)

                # Iniciar nuevo mensaje
                date_str, time_str, am_pm, sender, content = match.groups()
                timestamp = self._parse_whatsapp_timestamp(date_str, time_str, am_pm)

                current_message = {
                    "timestamp": timestamp,
                    "date_str": date_str,
                    "time_str": f"{time_str} {am_pm}",
                    "sender": sender,
                    "content": content,
                    "line_number": i + 1,
                    "original_line": line,
                }
            else:
                # Continuación del mensaje anterior
                if current_message:
                    current_message["content"] += f" {line}"

        # Agregar último mensaje
        if current_message:
            messages.append(current_message)

        logger.info(f"Parseados {len(messages)} mensajes")
        return messages

    def _parse_whatsapp_timestamp(
        self, date_str: str, time_str: str, am_pm: str
    ) -> datetime:
        """
        Parsea timestamp de WhatsApp a objeto datetime.

        Args:
            date_str: Fecha en formato DD/M/YYYY
            time_str: Hora en formato H:MM
            am_pm: "a.m." o "p.m."

        Returns:
            Objeto datetime
        """
        try:
            # Parsear fecha
            date_parts = date_str.split("/")
            day = int(date_parts[0])
            month = int(date_parts[1])
            year = int(date_parts[2])

            # Parsear hora
            time_parts = time_str.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1])

            # Convertir a formato 24 horas
            if am_pm == "p.m." and hour != 12:
                hour += 12
            elif am_pm == "a.m." and hour == 12:
                hour = 0

            return datetime(year, month, day, hour, minute)
        except (ValueError, IndexError) as e:
            logger.error(
                f"Error al parsear timestamp: {date_str} {time_str} {am_pm} - {e}"
            )
            return datetime.now()

    def find_insertion_point(
        self, target_timestamp: datetime, messages: List[Dict[str, str]]
    ) -> int:
        """
        Encuentra la posición donde insertar una transcripción basada en timestamp.

        Args:
            target_timestamp: Timestamp de la transcripción a insertar
            messages: Lista de mensajes parseados

        Returns:
            Índice donde insertar la transcripción
        """
        # Si el timestamp es solo fecha (medianoche), buscar el primer mensaje del mismo día
        if target_timestamp.hour == 0 and target_timestamp.minute == 0:
            target_date = target_timestamp.date()
            for i, message in enumerate(messages):
                message_date = message["timestamp"].date()
                if message_date == target_date:
                    return i
                elif message_date > target_date:
                    return i
        else:
            # Para timestamps con hora específica, usar la lógica original
            for i, message in enumerate(messages):
                if message["timestamp"] > target_timestamp:
                    return i

        # Si no se encuentra posición, insertar al final
        return len(messages)

    def insert_transcription(
        self,
        transcription_text: str,
        timestamp: datetime,
        sender: str = "Transcripción de Audio",
        audio_filename: Optional[str] = None,
    ) -> bool:
        """
        Reemplaza la mención del archivo de audio con su transcripción.

        Args:
            transcription_text: Texto de la transcripción
            timestamp: No se usa (mantenido por compatibilidad)
            sender: No se usa (mantenido por compatibilidad)
            audio_filename: Nombre del archivo de audio

        Returns:
            True si se reemplazó correctamente, False en caso contrario
        """
        try:
            if not audio_filename:
                logger.error("No se proporcionó nombre de archivo de audio")
                return False

            filename_with_text = f"{audio_filename} (archivo adjunto)"

            # Buscar y reemplazar la mención del archivo
            for i, line in enumerate(self.lines):
                if filename_with_text in line:
                    # Reemplazar solo la mención, manteniendo el resto de la línea
                    self.lines[i] = line.replace(filename_with_text, transcription_text)
                    
                    # Guardar archivo actualizado
                    self._save_text_file()

                    logger.info(f"Transcripción reemplazada en línea {i + 1}")
                    return True

            logger.warning(f"No se encontró la mención del archivo {audio_filename}")
            return False

        except Exception as e:
            logger.error(f"Error al insertar transcripción: {e}")
            return False

    def insert_multiple_transcriptions(
        self, transcriptions: List[Dict[str, any]]
    ) -> int:
        """
        Inserta múltiples transcripciones en el archivo.

        Args:
            transcriptions: Lista de diccionarios con 'text', 'timestamp', 'audio_filename' y opcionalmente 'sender'

        Returns:
            Número de transcripciones insertadas exitosamente
        """
        success_count = 0

        # Ordenar transcripciones por timestamp
        sorted_transcriptions = sorted(transcriptions, key=lambda x: x["timestamp"])

        for transcription in sorted_transcriptions:
            text = transcription.get("text", "")
            timestamp = transcription.get("timestamp")
            sender = transcription.get("sender", "Transcripción de Audio")
            audio_filename = transcription.get("audio_filename")

            if text and timestamp:
                if self.insert_transcription(text, timestamp, sender, audio_filename):
                    success_count += 1

        logger.info(f"Insertadas {success_count}/{len(transcriptions)} transcripciones")
        return success_count

    def _save_text_file(self):
        """Guarda el archivo de texto actualizado."""
        try:
            with open(self.text_file_path, "w", encoding="utf-8") as f:
                f.writelines(self.lines)
            logger.info("Archivo guardado exitosamente")
        except Exception as e:
            logger.error(f"Error al guardar archivo: {e}")
            raise

    def create_backup(self) -> str:
        """
        Crea una copia de seguridad del archivo original.

        Returns:
            Ruta al archivo de backup
        """
        backup_path = self.text_file_path.with_suffix(".backup")
        try:
            with open(self.text_file_path, "r", encoding="utf-8") as original:
                with open(backup_path, "w", encoding="utf-8") as backup:
                    backup.write(original.read())

            logger.info(f"Backup creado: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            raise

    def get_message_count(self) -> int:
        """Retorna el número de mensajes en el archivo."""
        messages = self.parse_whatsapp_format()
        return len(messages)

    def search_messages(
        self, query: str, case_sensitive: bool = False
    ) -> List[Dict[str, str]]:
        """
        Busca mensajes que contengan una consulta específica.

        Args:
            query: Texto a buscar
            case_sensitive: Si la búsqueda debe ser sensible a mayúsculas

        Returns:
            Lista de mensajes que coinciden con la búsqueda
        """
        messages = self.parse_whatsapp_format()
        results = []

        search_query = query if case_sensitive else query.lower()

        for message in messages:
            content = (
                message["content"] if case_sensitive else message["content"].lower()
            )
            if search_query in content:
                results.append(message)

        return results

    def find_transcription_insertion_point_by_filename(
        self, audio_filename: str
    ) -> Optional[int]:
        """
        Encuentra la posición de inserción de una transcripción basada en el nombre del archivo de audio.

        Args:
            audio_filename: Nombre del archivo de audio a buscar

        Returns:
            Índice de la línea de mensaje que contiene el nombre del archivo de audio, 
            o None si no se encuentra
        """
        try:
            filename_with_text = f"{audio_filename} (archivo adjunto)"
            messages = self.parse_whatsapp_format()

            for i, message in enumerate(messages):
                if filename_with_text in message["content"]:
                    return i

            return None
        except Exception as e:
            logger.error(f"Error al buscar punto de inserción por nombre de archivo: {e}")
            return None


def test_text_processor():
    """Función de prueba para el procesador de texto."""
    # Crear archivo de prueba
    test_file = Path("test_whatsapp.txt")
    test_content = """12/6/2025, 3:15 p.m. - Robert: Que dejó el TLF y subimos a esperar
12/6/2025, 3:15 p.m. - Hermano: Ok ok
13/6/2025, 7:21 a.m. - Hermano: ‎PTT-20250613-WA0020.opus (archivo adjunto)
13/6/2025, 9:52 a.m. - Robert: Si chamo gracias a Dios"""

    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)

    # Probar procesador
    processor = WhatsAppTextProcessor(str(test_file))
    messages = processor.parse_whatsapp_format()

    print(f"Mensajes encontrados: {len(messages)}")
    for msg in messages:
        print(f"{msg['timestamp']} - {msg['sender']}: {msg['content']}")

    # Limpiar archivo de prueba
    test_file.unlink()


if __name__ == "__main__":
    test_text_processor()
