@echo off
REM Quick activation script for BisonGuard virtual environment

if not exist "venv" (
    echo Virtual environment not found!
    echo Please run setup_env.bat first
    pause
    exit /b 1
)

echo Activating BisonGuard virtual environment...
call venv\Scripts\activate.bat
echo.
echo Virtual environment activated!
echo Python: %VIRTUAL_ENV%\Scripts\python.exe
echo.
echo Available commands:
echo   python flask_dashboard.py    - Start web dashboard
echo   python track.py              - Run video tracker
echo   python rtsp_bison_tracker_2.py - RTSP streaming server
echo   python test-rtsps.py         - Test RTSP connection
echo   deactivate                   - Exit virtual environment
echo.
