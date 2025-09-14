@echo off
cd /d "%~dp0"
cmd /k "uv run streamlit run app.py"