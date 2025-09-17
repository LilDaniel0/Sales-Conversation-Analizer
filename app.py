import streamlit as st
import io, sys, contextlib
import shutil
from pathlib import Path
from contextlib import redirect_stdout

# Load env
from dotenv import load_dotenv

load_dotenv("config.env")

# Import original functions
from main import preprocess_whatsapp_export, postprocess_whatsapp_export
from src.config import Config
from src.conversation_processor import ConversationProcessor

# Ensure directories exist
input_dir = Path("input_data")
output_dir = Path("output_data")

# Streamlit app
st.title("🗨️ WhatsApp Conversation Analyzer")
st.write("Upload a WhatsApp ZIP export to transcribe audios and get an Analisis.")

# Session state
if "uploaded_zip_name" not in st.session_state:
    st.session_state.uploaded_zip_name = None
if "preprocess_success" not in st.session_state:
    st.session_state.preprocess_success = False
if "main_result" not in st.session_state:
    st.session_state.main_result = None
if "postprocess_success" not in st.session_state:
    st.session_state.postprocess_success = False
if "logs" not in st.session_state:
    st.session_state.logs = {"preprocess": "", "main": "", "postprocess": ""}
if "final_file_path" not in st.session_state:
    st.session_state.final_file_path = None
if "choice" not in st.session_state:
    st.session_state.choice = None

# Sidebar for clear/restart
with st.sidebar:
    if st.button("Clear"):
        if input_dir.exists():
            try:
                # Check permissions by attempting to list
                items = list(input_dir.iterdir())
            except Exception as e:
                st.error(f"Error accessing input_dir: {e}")
                items = []
        else:
            st.error("input_dir does not exist - skipping clear")
            items = []

        # Clear input_data contents if possible
        for item in items:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)

        txt_files = list(output_dir.glob("*.txt"))
        for txt in txt_files:
            txt.unlink()

        # Reset session state
        st.session_state.preprocess_success = False
        st.session_state.main_result = None
        st.session_state.postprocess_success = False
        st.session_state.logs = {"preprocess": "", "main": "", "postprocess": ""}
        st.session_state.final_file_path = None
        st.session_state.choice = None
        st.session_state.uploaded_zip_name = None
        st.success("Session cleared! You can upload a new ZIP.")
        st.rerun()

# File upload
uploaded_file = st.file_uploader("Upload WhatsApp ZIP file", type=["zip"])
if uploaded_file is not None and st.session_state.uploaded_zip_name is None:
    zip_name = uploaded_file.name
    zip_path = input_dir / zip_name
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    st.session_state.uploaded_zip_name = zip_name

    # Automatic preprocess
    with st.spinner("Preprocessing ZIP file automatically..."):
        log_output = io.StringIO()
        with redirect_stdout(log_output):
            success = preprocess_whatsapp_export()
        st.session_state.logs["preprocess"] = log_output.getvalue()
        st.session_state.preprocess_success = success
        if success:
            st.success("Preprocesamiento listo! ✅")

        else:
            st.error("Preprocessing failed. Check logs.")

if st.session_state.preprocess_success:

    with st.expander("Information", expanded=False):
        st.caption("Validación y resumen de documentos")

        logs = []  # opcional: colector de logs

        def log(msg):
            logs.append(str(msg))

        # Validate general config
        is_valid, errors = Config.validate_config()
        if not is_valid:
            st.error("Config inválida")
            st.write(errors)  # se muestra la lista en el expander
            st.session_state.main_result = None

            log("Config errors:")
            for e in errors:
                log(f"  - {e}")

        else:
            media_dir = input_dir / "whatsapp_chats"
            text_file_path = output_dir / "chat.txt"
            language = Config.WHISPER_LANGUAGE or None

            with st.spinner("Inicializando processor…"):
                processor = ConversationProcessor(
                    input_directory=str(media_dir),
                    text_file_path=str(text_file_path),
                    language=language,
                )

            # Documents summary
            summary = processor.get_processing_summary()
            log("Documents summary:")
            for k, v in summary.items():
                log(f"  {k}: {v}")
            st.dataframe(summary)  # muestra el dict bonito

    # UI for choice (replace input())
    st.subheader("Select Processing Option")
    choice_options = [
        "1: Audio files only",
        "2: Image files only",
        "3: All (audio and images)",
    ]
    selected = st.radio(
        "What do you want to process?", choice_options, key="choice_radio"
    )
    st.session_state.choice = selected.split(":")[0]

    if st.button("Run Main Analysis"):
        st.write("Starting analysis...")
        with st.spinner(
            "Running analysis... This may take a while for transcriptions."
        ):
            progress_bar = st.progress(0)
            progress_bar.progress(0.2)

            # Asegura el dict de logs en session_state
            if "logs" not in st.session_state:
                st.session_state.logs = {}

            choice = st.session_state.choice
            if choice == "1":
                result = processor.process_audio_files()
            elif choice == "2":
                result = processor.process_image_files()
            elif choice == "3":
                result = processor.process_all()
            else:
                print("Invalid choice, defaulting to audio.", flush=True)
                result = processor.process_audio_files()
            progress_bar.progress(0.8)

            # --- Expander y placeholders para logs/resultados ---
            exp = st.expander("Logs de preprocesamiento", expanded=True)

            with exp:
                result_container = (
                    st.container()
                )  # aquí mostraremos el bloque de "RESULTS" después
                with result_container:
                    st.text("\n RESULTS \n")
                    if result.get("success", False):
                        st.text("✅ Processing completed successfully!")
                        if "audio_processing" in result:
                            audio = result["audio_processing"]
                            st.text(
                                f"📝 Inserted transcriptions: {audio.get('inserted_transcriptions', 0)}"
                            )
                            st.text(
                                f"🎵 Processed audios: {audio.get('successful_transcriptions', 0)}"
                            )
                        if "image_processing" in result:
                            images = result["image_processing"]
                            st.text(
                                f"🖼️ Processed images: {images.get('processed_images', 0)}"
                            )
                    else:
                        st.text("❌ Processing error:")
                        if "audio_processing" in result:
                            st.text(
                                f"  Audio: {result['audio_processing'].get('message', 'Unknown error')}"
                            )
                        if "image_processing" in result:
                            st.text(
                                f"  Images: {result['image_processing'].get('message', 'Unknown error')}"
                            )

            # Guarda el log completo en session_state (como ya hacías)
            st.session_state.main_result = result
            progress_bar.progress(1.0)

            if st.session_state.main_result and st.session_state.main_result.get(
                "success"
            ):
                # Postprocess
                log_output_post = io.StringIO()
                with redirect_stdout(log_output_post):
                    post_success = postprocess_whatsapp_export()
                st.session_state.logs["postprocess"] = log_output_post.getvalue()
                st.session_state.postprocess_success = post_success
                if post_success:
                    zip_stem = Path(st.session_state.uploaded_zip_name).stem
                    final_path = output_dir / f"{zip_stem}.txt"
                    if final_path.exists():
                        st.session_state.final_file_path = str(final_path)
                    st.success("Analysis and postprocessing completed!")
            else:
                st.error("Analysis failed. Check logs.")

if st.session_state.postprocess_success and st.session_state.final_file_path:
    # Download
    final_path = Path(st.session_state.final_file_path)
    if final_path.exists():
        with open(final_path, "r", encoding="utf-8") as f:
            data = f.read()
        st.subheader("Download Results")
        st.download_button(
            label="Download Processed Chat",
            data=data,
            file_name=final_path.name,
            mime="text/plain",
        )

# Error displays
if st.session_state.uploaded_zip_name and not st.session_state.preprocess_success:
    st.error("Preprocessing failed. Check logs or clear session.")

if st.session_state.main_result and not st.session_state.main_result.get("success"):
    st.error("Main processing failed.")
