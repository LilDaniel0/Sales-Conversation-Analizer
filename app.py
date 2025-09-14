import streamlit as st
import os
import io
import zipfile
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
input_dir.mkdir(exist_ok=True)
output_dir = Path("output_data")
output_dir.mkdir(exist_ok=True)

# Streamlit app
st.title("🗨️ WhatsApp Export Analyzer")
st.write(
    "Upload a WhatsApp ZIP export to transcribe audios and process images interactively."
)

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
    if st.button("Clear and Restart"):
        # Clear input_data contents
        for item in input_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
        # Clear output_data TXT files
        for txt in output_dir.glob("*.txt"):
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
if uploaded_file is not None:
    zip_name = uploaded_file.name
    zip_path = input_dir / zip_name
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    st.session_state.uploaded_zip_name = zip_name
    st.success(f"ZIP file '{zip_name}' saved to input_data.")

# Preprocess step
if st.session_state.uploaded_zip_name and not st.session_state.preprocess_success:
    if st.button("Run Preprocess"):
        with st.spinner("Preprocessing ZIP file..."):
            log_output = io.StringIO()
            with redirect_stdout(log_output):
                success = preprocess_whatsapp_export()
            st.session_state.logs["preprocess"] = log_output.getvalue()
            st.session_state.preprocess_success = success
            if success:
                st.success("Preprocessing completed!")
            else:
                st.error("Preprocessing failed. Check logs.")

if st.session_state.preprocess_success:
    with st.expander("Preprocessing Logs", expanded=True):
        st.text_area("Logs:", st.session_state.logs["preprocess"], height=200)

    # UI for choice (replace input())
    st.subheader("Select Processing Option")
    choice_options = [
        "1: Audio files only",
        "2: Image files only",
        "3: All (audio and images)",
    ]
    selected_choice = st.radio(
        "What do you want to process?", choice_options, key="choice_radio"
    )
    st.session_state.choice = selected_choice.split(":")[0]

    if st.button("Run Main Analysis"):
        with st.spinner(
            "Running analysis... This may take a while for transcriptions."
        ):
            progress_bar = st.progress(0)
            log_output = io.StringIO()
            with redirect_stdout(log_output):
                # Replicate main logic after preprocess
                Config.print_config()

                # Validate config
                is_valid, errors = Config.validate_config()
                if not is_valid:
                    print("\nConfig errors:")
                    for error in errors:
                        print(f"  - {error}")
                    st.session_state.main_result = None
                else:
                    # Use fixed paths: input_directory = input_data/whatsapp_chats (after extract), text_file = output_data/chat.txt
                    media_dir = input_dir / "whatsapp_chats"
                    text_file_path = output_dir / "chat.txt"
                    language = (
                        Config.WHISPER_LANGUAGE if Config.WHISPER_LANGUAGE else None
                    )

                    print(f"\nInitializing processor...")
                    processor = ConversationProcessor(
                        input_directory=str(media_dir),
                        text_file_path=str(text_file_path),
                        language=language,
                    )

                    # Summary
                    print("\nProcessing summary:")
                    summary = processor.get_processing_summary()
                    for key, value in summary.items():
                        print(f"  {key}: {value}")

                    # Validate inputs
                    is_valid, errors = processor.validate_inputs()
                    if not is_valid:
                        print("\nValidation errors:")
                        for error in errors:
                            print(f"  - {error}")
                        st.session_state.main_result = None
                    else:
                        choice = st.session_state.choice
                        if choice == "1":
                            result = processor.process_audio_files()
                        elif choice == "2":
                            result = processor.process_image_files()
                        elif choice == "3":
                            result = processor.process_all()
                        else:
                            print("Invalid choice, defaulting to audio.")
                            result = processor.process_audio_files()

                        # Show results
                        print("\n=== RESULTS ===")
                        if result.get("success", False):
                            print("✅ Processing completed successfully!")
                            if "audio_processing" in result:
                                audio = result["audio_processing"]
                                print(
                                    f"📝 Inserted transcriptions: {audio.get('inserted_transcriptions', 0)}"
                                )
                                print(
                                    f"🎵 Processed audios: {audio.get('successful_transcriptions', 0)}"
                                )
                            if "image_processing" in result:
                                images = result["image_processing"]
                                print(
                                    f"🖼️ Processed images: {images.get('processed_images', 0)}"
                                )
                        else:
                            print("❌ Processing error:")
                            if "audio_processing" in result:
                                print(
                                    f"  Audio: {result['audio_processing'].get('message', 'Unknown error')}"
                                )
                            if "image_processing" in result:
                                print(
                                    f"  Images: {result['image_processing'].get('message', 'Unknown error')}"
                                )

                        st.session_state.main_result = result

            st.session_state.logs["main"] = log_output.getvalue()
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

# Display main logs if available
if st.session_state.main_result:
    with st.expander("Main Execution Logs", expanded=True):
        st.text_area("Logs:", st.session_state.logs["main"], height=200)

    # Results summary
    if st.session_state.main_result.get("success"):
        col1, col2, col3 = st.columns(3)
        if "audio_processing" in st.session_state.main_result:
            audio = st.session_state.main_result["audio_processing"]
            col1.metric(
                "Inserted Transcriptions", audio.get("inserted_transcriptions", 0)
            )
            col2.metric("Successful Audios", audio.get("successful_transcriptions", 0))
        if "image_processing" in st.session_state.main_result:
            images = st.session_state.main_result["image_processing"]
            col3.metric("Processed Images", images.get("processed_images", 0))

if st.session_state.postprocess_success and st.session_state.final_file_path:
    with st.expander("Postprocessing Logs", expanded=True):
        st.text_area("Logs:", st.session_state.logs["postprocess"], height=100)

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
