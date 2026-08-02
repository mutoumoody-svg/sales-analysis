@echo off
REM ============================================
REM AI Business Decision Platform - Backend Runner
REM ============================================

cd /d "%~dp0"

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Install dependencies if needed
pip install -r requirements.txt --quiet

REM Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
