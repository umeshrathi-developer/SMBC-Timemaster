@echo off
REM TimeMaster Setup Script for Windows

echo.
echo ================================
echo  TimeMaster Setup Script
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [3/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [4/5] Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Failed to run migrations
    pause
    exit /b 1
)

echo [5/5] Creating superuser (admin account)...
python manage.py createsuperuser
if errorlevel 1 (
    echo ERROR: Failed to create superuser
    pause
    exit /b 1
)

echo.
echo ================================
echo  Setup Completed Successfully!
echo ================================
echo.
echo Next steps:
echo 1. Run the development server:
echo    python manage.py runserver 0.0.0.0:8000
echo.
echo 2. Access the application:
echo    - Main App: http://localhost:8000/timesheet/
echo    - Admin: http://localhost:8000/admin/
echo.
echo 3. To access from other machines on the network:
echo    Replace 'localhost' with your machine IP address
echo.
pause
