import streamlit as st
import io, sys, contextlib
import shutil
from pathlib import Path
from contextlib import redirect_stdout
from src import analizer

# Load env
from dotenv import load_dotenv

load_dotenv("config.env")

# Import original functions
from main import preprocess_whatsapp_export, postprocess_whatsapp_export
from src.config import Config
from src.conversation_processor import ConversationProcessor
from src.multi_file_processor import MultiFileProcessor
from src import analizer

# Ensure directories exist
input_dir = Path("input_data")
output_dir = Path("output_data")

# Streamlit app
st.title("🗨️ WhatsApp Conversation Analyzer")
st.write("Upload a WhatsApp ZIP export to transcribe audios and get an Analisis.")

# Session state - Nuevo sistema para múltiples archivos
if "use_multi_mode" not in st.session_state:
    st.session_state.use_multi_mode = False
if "multi_processor" not in st.session_state:
    st.session_state.multi_processor = None
if "processing_jobs" not in st.session_state:
    st.session_state.processing_jobs = {}
if "processing_results" not in st.session_state:
    st.session_state.processing_results = {}

# Session state - Compatibilidad con modo single
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
if "clearing" not in st.session_state:
    st.session_state.clearing = False
if st.session_state.clearing:
    st.toast("Session cleared! You can upload a new ZIP.", icon="✅")
    st.session_state.clearing = False

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

        # Clear processing directories
        processing_dir = input_dir / "processing"
        uploaded_files_dir = input_dir / "uploaded_files"
        if processing_dir.exists():
            shutil.rmtree(processing_dir, ignore_errors=True)
        if uploaded_files_dir.exists():
            shutil.rmtree(uploaded_files_dir, ignore_errors=True)

        # Reset session state - Single mode
        st.session_state.clearing = True
        st.session_state.preprocess_success = False
        st.session_state.main_result = None
        st.session_state.postprocess_success = False
        st.session_state.logs = {"preprocess": "", "main": "", "postprocess": ""}
        st.session_state.final_file_path = None
        st.session_state.choice = None
        st.session_state.uploaded_zip_name = None

        # Reset session state - Multi mode
        st.session_state.use_multi_mode = False
        st.session_state.multi_processor = None
        st.session_state.processing_jobs = {}
        st.session_state.processing_results = {}
        st.rerun()


# Mode selection
st.subheader("📁 Upload Mode")
mode_col1, mode_col2 = st.columns(2)
with mode_col1:
    single_mode = st.button("Single File Mode", use_container_width=True, type="primary" if not st.session_state.use_multi_mode else "secondary")
with mode_col2:
    multi_mode = st.button("Multiple Files Mode", use_container_width=True, type="primary" if st.session_state.use_multi_mode else "secondary")

if single_mode:
    st.session_state.use_multi_mode = False
    st.rerun()
if multi_mode:
    st.session_state.use_multi_mode = True
    st.rerun()

# File upload
if st.session_state.use_multi_mode:
    uploaded_files = st.file_uploader(
        "Upload WhatsApp ZIP files",
        type=["zip"],
        accept_multiple_files=True,
        help="Select multiple ZIP files to process simultaneously"
    )
else:
    uploaded_file = st.file_uploader("Upload WhatsApp ZIP file", type=["zip"])

# Handle multiple files upload
if st.session_state.use_multi_mode and uploaded_files:
    if not st.session_state.multi_processor:
        st.session_state.multi_processor = MultiFileProcessor(max_workers=3)

    uploaded_files_dir = input_dir / "uploaded_files"
    uploaded_files_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded files and create jobs
    new_jobs = {}
    for uploaded_file in uploaded_files:
        if uploaded_file.name not in st.session_state.processing_jobs:
            # Save file
            zip_path = uploaded_files_dir / uploaded_file.name
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())

            # Create job
            job_id = st.session_state.multi_processor.submit_zip(str(zip_path), uploaded_file.name)
            new_jobs[uploaded_file.name] = {
                "job_id": job_id,
                "zip_name": uploaded_file.name,
                "status": "uploaded",
                "zip_path": str(zip_path)
            }

            st.session_state.processing_jobs.update(new_jobs)

    if new_jobs:
        st.success(f"✅ Uploaded {len(new_jobs)} new files!")

# Handle single file upload (existing logic)
elif not st.session_state.use_multi_mode and uploaded_file is not None and st.session_state.uploaded_zip_name is None:
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

# Multi-file processing UI
if st.session_state.use_multi_mode and st.session_state.processing_jobs:
    st.divider()
    st.subheader("📊 Processing Dashboard")

    # Show uploaded files
    if st.session_state.processing_jobs:
        st.write(f"**Files uploaded:** {len(st.session_state.processing_jobs)}")

        # Process all files button
        if st.button("🚀 Process All Files", type="primary", use_container_width=True):
            with st.spinner("Processing all files..."):
                st.session_state.processing_results = st.session_state.multi_processor.process_all_jobs()
            st.success("Processing completed!")
            st.rerun()

        # Show individual file status
        for zip_name, job_info in st.session_state.processing_jobs.items():
            job_id = job_info["job_id"]

            # Get current job status
            job_status = st.session_state.multi_processor.get_job_status(job_id)

            with st.expander(f"📄 {zip_name}", expanded=job_status and job_status.get("status") == "processing"):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    if job_status:
                        status = job_status.get("status", "unknown")
                        progress = job_status.get("progress", 0.0)

                        # Status indicator
                        status_colors = {
                            "pending": "🟡",
                            "preprocessing": "🔄",
                            "processing": "🔄",
                            "postprocessing": "🔄",
                            "completed": "✅",
                            "failed": "❌"
                        }
                        st.write(f"{status_colors.get(status, '❓')} **Status:** {status.title()}")

                        # Progress bar
                        if status in ["preprocessing", "processing", "postprocessing"]:
                            st.progress(progress)
                            st.write(f"Progress: {progress:.1%}")

                with col2:
                    if st.button(f"🔍 Details", key=f"details_{job_id}"):
                        st.json(job_status)

                with col3:
                    # Download button if completed
                    result = st.session_state.processing_results.get(job_id)
                    if result and result.get("success") and "output_file" in result:
                        output_path = Path(result["output_file"])
                        if output_path.exists():
                            with open(output_path, "r", encoding="utf-8") as f:
                                data = f.read()
                            st.download_button(
                                label="📥 Download",
                                data=data,
                                file_name=output_path.name,
                                mime="text/plain",
                                key=f"download_{job_id}"
                            )

                # Show results if completed
                if job_id in st.session_state.processing_results:
                    result = st.session_state.processing_results[job_id]
                    if result.get("success"):
                        st.success("✅ Processing completed successfully!")
                        if "processing_result" in result and "audio_processing" in result["processing_result"]:
                            audio_result = result["processing_result"]["audio_processing"]
                            st.write(f"🎵 Audio files processed: {audio_result.get('successful_transcriptions', 0)}")
                            st.write(f"📝 Transcriptions inserted: {audio_result.get('inserted_transcriptions', 0)}")

                        # Analysis button
                        if st.button(f"🔍 Analyze Conversation", key=f"analyze_{job_id}"):
                            output_path = Path(result["output_file"])
                            if output_path.exists():
                                with open(output_path, "r", encoding="utf-8") as f:
                                    data = f.read()
                                with st.spinner("Analyzing conversation..."):
                                    explanation = analizer.analize_conversation(data)
                                if explanation:
                                    st.write("**Analysis:**")
                                    st.write(explanation)
                    else:
                        st.error(f"❌ Processing failed: {result.get('error', 'Unknown error')}")

# Single-file processing UI (existing)
elif st.session_state.preprocess_success:

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
    choice_options = ["1: Audio files only"]
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
    st.divider()
    final_path = Path(st.session_state.final_file_path)
    if final_path.exists():
        with open(final_path, "r", encoding="utf-8") as f:
            data = f.read()
        st.subheader("Download Results - Analize Conversation")
        st.download_button(
            label="Download Processed Chat",
            data=data,
            file_name=final_path.name,
            mime="text/plain",
        )
        analizar = st.button("Analizar Conversacion")
        if analizar:
            with st.spinner("Analizando Conversacion"):
                explanation = analizer.analize_conversation(data)

            if explanation:
                with st.expander("See explanation"):
                    st.write(explanation)


# Error displays
if st.session_state.uploaded_zip_name and not st.session_state.preprocess_success:
    st.error("Preprocessing failed. Check logs or clear session.")

if st.session_state.main_result and not st.session_state.main_result.get("success"):
    st.error("Main processing failed.")
