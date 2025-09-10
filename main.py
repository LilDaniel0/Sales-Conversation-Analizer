"""
Script principal para el procesador de conversaciones de WhatsApp.
"""

import sys
from pathlib import Path
from src.conversation_processor import ConversationProcessor
from src.config import Config


def main():
    """Función principal del programa."""
    print("=== Procesador de Conversaciones de WhatsApp ===")
    print(
        "Este programa transcribe audios de WhatsApp y los inserta en el archivo de texto."
    )
    print()

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
    model = Config.WHISPER_MODEL
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

        if choice == "1":
            result = processor.process_audio_files()
        elif choice == "2":
            result = processor.process_image_files()
        elif choice == "3":
            result = processor.process_all()
        else:
            print("Opción inválida.")
            return 1

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
