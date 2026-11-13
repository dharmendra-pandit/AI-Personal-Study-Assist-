@echo off
rem Start the app with the project's virtual environment (no activation needed).
rem Usage:  run.bat            (from cmd, PowerShell: .\run.bat, or double-click)
cd /d "%~dp0"
if not exist "myenv\Scripts\python.exe" (
    echo myenv not found. Create it first:
    echo     python -m venv myenv
    echo     myenv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)
"myenv\Scripts\python.exe" -m streamlit run app.py %*
