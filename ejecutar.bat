@echo off
cd /d "%~dp0"
cmd /k "uv run -m streamlit run .\app.py"