@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 (echo Instala Python 3.11 y activa Add Python to PATH. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (echo Error al instalar dependencias. & pause & exit /b 1)
start http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
