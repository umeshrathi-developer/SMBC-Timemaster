# Quick Start Commands for TimeMaster

## Initial Setup

### Windows
```bash
setup.bat
```

### macOS/Linux
```bash
chmod +x setup.sh
./setup.sh
```

## Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver 0.0.0.0:8000
```

## Access the Application
- Main App: http://localhost:8000/timesheet/
- Admin: http://localhost:8000/admin/
- Network Access: http://<your_machine_ip>:8000/

## Useful Django Commands

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver

# Open Django shell
python manage.py shell

# Backup database
python manage.py dumpdata > backup.json

# Restore from backup
python manage.py loaddata backup.json

# Reset database (delete and recreate)
# Delete db.sqlite3 file, then:
python manage.py migrate
python manage.py createsuperuser
```

## Troubleshooting

### Virtual Environment Not Activating
Make sure you're in the project directory and use the correct activate command for your OS.

### Port 8000 Already in Use
```bash
python manage.py runserver 0.0.0.0:8001
```

### Database Issues
```bash
# Delete database and start fresh
rm db.sqlite3  # Linux/macOS
del db.sqlite3  # Windows

python manage.py migrate
python manage.py createsuperuser
```

### Static Files Not Loading
```bash
python manage.py collectstatic
```

## Network Configuration

### Access from Other Machines
If you want to access the application from other computers on your network:

1. Find your machine's IP address:
   - Windows: `ipconfig` command in cmd
   - macOS/Linux: `ifconfig` command in terminal

2. Run the server with:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

3. Access from another machine:
   ```
   http://<your_machine_ip>:8000/timesheet/
   ```

### For Production Deployment
See README.md for production setup instructions using Gunicorn and Nginx.
