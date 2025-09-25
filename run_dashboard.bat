@echo off
echo Starting BisonGuard Dashboard...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Setting up...
    call setup_env.bat
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if Flask is installed
python -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo Flask not found. Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo ========================================
echo Starting Flask Dashboard
echo ========================================
echo.
echo Dashboard will be available at:
echo   http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Check which dashboard to run
if exist "enhanced_dashboard.py" (
    echo Starting Enhanced Dashboard with Analytics...
    python enhanced_dashboard.py
) else (
    echo Starting Standard Dashboard...
    python flask_dashboard.py
)
