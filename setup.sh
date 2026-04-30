#!/bin/bash

# TimeMaster Setup Script for macOS/Linux

echo
echo "================================"
echo " TimeMaster Setup Script"
echo "================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

echo "[1/5] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "[2/5] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

echo "[3/5] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo "[4/5] Running database migrations..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to run migrations"
    exit 1
fi

echo "[5/5] Creating superuser (admin account)..."
python manage.py createsuperuser
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create superuser"
    exit 1
fi

echo
echo "================================"
echo " Setup Completed Successfully!"
echo "================================"
echo
echo "Next steps:"
echo "1. Run the development server:"
echo "   python manage.py runserver 0.0.0.0:8000"
echo
echo "2. Access the application:"
echo "   - Main App: http://localhost:8000/timesheet/"
echo "   - Admin: http://localhost:8000/admin/"
echo
echo "3. To access from other machines on the network:"
echo "   Replace 'localhost' with your machine IP address"
echo
