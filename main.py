"""
Script principal para el procesador de conversaciones de WhatsApp.
"""

import sys
import os
import shutil
import zipfile
from pathlib import Path
from src.conversation_processor import ConversationProcessor
from src.config import Config


def preprocess_whatsapp_export():
    """Preprocess WhatsApp chat export."""
    input_dir = Path("input_data")
    output_dir = Path("output_data")
    whatsapp_chats_dir = input_dir / "whatsapp_chats"

    zip_files = list(input_dir.glob("*.zip"))
    if not zip_files:
        print("No .zip file found in input_data directory.")
        return False

    zip_file = zip_files[0]
    print(f"Found zip file: {zip_file.name}")

    # Create whatsapp_chats directory
    whatsapp_chats_dir.mkdir()

    # Extract zip contents
    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            # First, find the root folder in the zip
            root_folders = set(
                name.split("/")[0] for name in zip_ref.namelist() if "/" in name
            )

            if not root_folders:
                print("No folder found in the zip file.")
                return False

            # Extract contents to a temporary subfolder first
            zip_ref.extractall(whatsapp_chats_dir)

    except Exception as e:
        print(f"Error during zip extraction: {e}")
        return False

    # Find .text file
    text_files = list(whatsapp_chats_dir.glob("*.text"))
    if not text_files:
        print("No .text file found in whatsapp_chats directory.")
        return False

    # Rename .text file
    original_text_file = text_files[0]
    chat_text_file = whatsapp_chats_dir / "chat.text"
    original_text_file.rename(chat_text_file)

    # Copy to output_data
    output_file = output_dir / "chat.text"
    shutil.copy(chat_text_file, output_file)

    return True


def main():
    """Función principal del programa."""
    print("=== Procesador de Conversaciones de WhatsApp ===")
    print(
        "Este programa transcribe audios de WhatsApp y los inserta en el archivo de texto."
    )
    print()

    # Preprocesar archivos
    if not preprocess_whatsapp_export():
        print("Error en el preprocesamiento. Deteniendo el programa.")
        return 1

    # Cargar configuración
    Config.print_config()

    # Validar configuración
    is_valid, errors = Config.validate_config()
    if not is_valid:
        print("\nErrores de configuración:")
        for error in errors:
            print(f"  - {error}")
        return 1

    # Usar configuración del archivo .env
    input_dir = str(Config.get_input_directory())
    text_file = str(Config.get_text_file())
    language = Config.WHISPER_LANGUAGE if Config.WHISPER_LANGUAGE else None

    try:
        # Crear procesador
        print(f"\nInicializando procesador...")
        processor = ConversationProcessor(
            input_directory=input_dir,
            text_file_path=text_file,
            language=language,
        )

        # Mostrar resumen
        print("\nResumen de archivos encontrados:")
        summary = processor.get_processing_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Validar inputs
        is_valid, errors = processor.validate_inputs()
        if not is_valid:
            print("\nErrores de validación:")
            for error in errors:
                print(f"  - {error}")
            return 1

        # Preguntar qué procesar
        print("\n¿Qué deseas procesar?")
        print("1. Solo archivos de audio")
        print("2. Solo archivos de imagen")
        print("3. Todo (audio e imágenes)")

        choice = input("Selecciona una opción (1-3): ").strip()

        if choice == "" or choice == "1":
            result = processor.process_audio_files()
        elif choice == "2":
            result = processor.process_image_files()
        elif choice == "3":
            result = processor.process_all()
        else:
            print("Opción inválida. Procesando archivos de audio por defecto.")
            result = processor.process_audio_files()

        # Mostrar resultados
        print("\n=== RESULTADOS ===")
        if result["success"]:
            print("✅ Procesamiento completado exitosamente!")

            if "audio_processing" in result:
                audio = result["audio_processing"]
                print(
                    f"📝 Transcripciones insertadas: {audio.get('inserted_transcriptions', 0)}"
                )
                print(
                    f"🎵 Archivos de audio procesados: {audio.get('successful_transcriptions', 0)}"
                )

            if "image_processing" in result:
                images = result["image_processing"]
                print(f"🖼️  Imágenes procesadas: {images.get('processed_images', 0)}")
        else:
            print("❌ Error en el procesamiento:")
            if "audio_processing" in result:
                print(
                    f"  Audio: {result['audio_processing'].get('message', 'Error desconocido')}"
                )
            if "image_processing" in result:
                print(
                    f"  Imágenes: {result['image_processing'].get('message', 'Error desconocido')}"
                )
            return 1

        print(f"\nArchivo de texto actualizado: {text_file}")
        print("¡Proceso completado!")

    except KeyboardInterrupt:
        print("\n\nProceso cancelado por el usuario.")
        return 1
    except Exception as e:
        print(f"\nError inesperado: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
