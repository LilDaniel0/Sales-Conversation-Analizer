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
    extract_dir = input_dir / "whatsapp_chats"

    # Crear la carpeta de extracción si no existe
    extract_dir.mkdir(parents=True, exist_ok=True)

    zip_files = list(input_dir.glob("*.zip"))
    if not zip_files:
        print("No .zip file found in input_data directory.")
        return False

    zip_file = zip_files[0]
    print(f"Found zip file: {zip_file.name}")

    # Descomprimir el zip en whatsapp_chats
    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(extract_dir)
        print(f"Extracted {zip_file.name} to {extract_dir.resolve()}")

    text_files = list(extract_dir.glob("*.txt"))
    if not text_files:
        print("No .txt file found in extracted directory.")
        return False

    # Rename text file to chat.txt
    text_file = text_files[0]
    text_file.rename(extract_dir / "chat.txt")
    print(f"Renamed {text_file.name} to chat.txt")

    # copiar chat.txt a output_data
    shutil.copy(extract_dir / "chat.txt", output_dir / "chat.txt")
    print(f"Copied chat.txt to {output_dir.resolve()}")

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
        # Renombrar el archivo de texto final
        postprocess_whatsapp_export()
        print(f"\nArchivo de texto actualizado: {text_file}")
        print("¡Proceso completado!")

    except KeyboardInterrupt:
        print("\n\nProceso cancelado por el usuario.")
        return 1
    except Exception as e:
        print(f"\nError inesperado: {e}")
        return 1

    return 0


def postprocess_whatsapp_export():
    input_dir = Path("input_data")
    output_dir = Path("output_data")

    # Buscar archivo zip
    zip_files = list(input_dir.glob("*.zip"))
    zip_file = zip_files[0]

    # Buscar archivo txt
    txt_files = list(output_dir.glob("*.txt"))
    text_file = txt_files[0]

    # Renombrar
    new_name = output_dir / f"{zip_file.stem}.txt"

    text_file.rename(new_name)
    print(f"Text file renamed to: {new_name.name}")

    return True


if __name__ == "__main__":
    sys.exit(main())
