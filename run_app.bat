@echo off
cd /d "%~dp0"
start "Invoice Extractor Server" "C:\Users\ironh\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run src\app.py --server.headless true
timeout /t 3 /nobreak >nul
start "" "http://localhost:8501"
