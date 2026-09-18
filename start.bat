@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Setting up for the first time...
  python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)
echo Collecting news and building the site...
".venv\Scripts\python.exe" build.py
if errorlevel 1 goto :end
start "" /min cmd /c "ping -n 3 127.0.0.1 > nul & start "" http://127.0.0.1:8000/"
echo Preview: http://127.0.0.1:8000/  (press Ctrl+C to stop)
".venv\Scripts\python.exe" -m http.server 8000 --bind 127.0.0.1 --directory site
:end
pause
