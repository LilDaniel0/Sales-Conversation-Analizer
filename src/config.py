"""
Configuración del proyecto usando variables de entorno.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde config.env
load_dotenv("config.env")


class Config:
    """Configuración del proyecto."""

    # Directorio base del proyecto
    BASE_DIR = Path(__file__).parent.parent

    # Configuración de la API de OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es")

    # Rutas de archivos
    INPUT_DIRECTORY = os.getenv(
        "INPUT_DIRECTORY", "input_data/Chat de WhatsApp con Hermano"
    )
    TEXT_FILE = os.getenv(
        "TEXT_FILE",
        "input_data/Chat de WhatsApp con Hermano/Chat de WhatsApp con Hermano.txt",
    )

    # Configuración de logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_input_directory(cls) -> Path:
        """Obtiene la ruta absoluta del directorio de entrada."""
        if Path(cls.INPUT_DIRECTORY).is_absolute():
            return Path(cls.INPUT_DIRECTORY)
        return cls.BASE_DIR / cls.INPUT_DIRECTORY

    @classmethod
    def get_text_file(cls) -> Path:
        """Obtiene la ruta absoluta del archivo de texto."""
        if Path(cls.TEXT_FILE).is_absolute():
            return Path(cls.TEXT_FILE)
        return cls.BASE_DIR / cls.TEXT_FILE

    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """Valida que la configuración sea correcta."""
        errors = []

        # Verificar directorio de entrada
        input_dir = cls.get_input_directory()
        if not input_dir.exists():
            errors.append(f"Directorio de entrada no existe: {input_dir}")

        # Verificar archivo de texto
        text_file = cls.get_text_file()
        if not text_file.exists():
            errors.append(f"Archivo de texto no existe: {text_file}")

        # Verificar API Key
        if not cls.OPENAI_API_KEY:
            errors.append("API Key de OpenAI no configurada en config.env")

        return len(errors) == 0, errors

    @classmethod
    def print_config(cls):
        """Imprime la configuración actual."""
        print("=== Configuración del Proyecto ===")
        print(f"Directorio de entrada: {cls.get_input_directory()}")
        print(f"Archivo de texto: {cls.get_text_file()}")
        print(f"Idioma: {cls.WHISPER_LANGUAGE or 'Auto-detectar'}")
        print(f"Nivel de log: {cls.LOG_LEVEL}")
        print(f"API Key configurada: {'Sí' if cls.OPENAI_API_KEY else 'No'}")
        print("=" * 35)
