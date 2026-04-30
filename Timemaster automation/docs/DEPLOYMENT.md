# Timesheet & Comp-Off Management - Private Network Deployment Guide

This guide explains how to deploy the Timesheet & Comp-Off Management system on a private corporate network accessible to all employees.

## Network Architecture

```
┌─────────────────────┐
│  Private Network    │
│  (Company LAN)      │
│                     │
│  ┌───────────────┐  │
│  │  Client PC 1  │  │
│  └───────────────┘  │
│         ↓           │
│  ┌───────────────┐  │
│  │  Client PC 2  │──→ Access via IP/Hostname
│  └───────────────┘  │
│         ↓           │
│  ┌──────────────────────┐
│  │  Server Machine      │
│  │  (Running Django)    │
│  │  http://192.168.x.x:8000/
│  └──────────────────────┘
│         ↓           │
│  ┌───────────────┐  │
│  │  Database     │  │
│  │  (SQLite/DB)  │  │
│  └───────────────┘  │
└─────────────────────┘
```

## Pre-Deployment Checklist

- [ ] Windows/Linux server machine designated for hosting
- [ ] Python 3.8+ installed on server
- [ ] Network connectivity verified between client and server
- [ ] Static IP or hostname assigned to server
- [ ] Firewall rules configured to allow port 8000 (or custom port)
- [ ] Backup mechanism in place

## Step 1: Server Machine Setup

### On the Server Machine (Windows)

1. **Install Python**
   - Download Python 3.10+ from python.org
   - Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **Clone/Copy Project Files**
   ```bash
   cd C:\MyProjects\
   # Copy Timemaster automation folder here
   cd "Timemaster automation"
   ```

3. **Run Setup Script**
   ```bash
   setup.bat
   ```
   This will:
   - Create virtual environment
   - Install dependencies
   - Run migrations
   - Create admin user

### On the Server Machine (Linux/macOS)

1. **Install Python and Dependencies**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv
   ```

2. **Clone/Copy Project Files**
   ```bash
   cd /opt/
   # Copy Timemaster automation folder here
   cd timemaster
   ```

3. **Run Setup Script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

## Step 2: Network Configuration

### Find Server IP Address

**Windows:**
```cmd
ipconfig
```
Look for IPv4 Address (typically 192.168.x.x or 10.x.x.x)

**Linux/macOS:**
```bash
ifconfig
# or
hostname -I
```

### Configure Django Settings

Edit `timemaster_project/settings.py`:

```python
# Add your server's IP address(es) and hostname(s)
ALLOWED_HOSTS = [
    '192.168.1.100',              # Server IP
    'timemaster.company.local',   # Hostname (if available)
    'localhost',
    '127.0.0.1',
]

# For production, set DEBUG to False
DEBUG = False
```

## Step 3: Firewall Configuration

### Windows Firewall

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Click "Change settings"
4. Click "Allow another app"
5. Select Python executable or add port 8000
6. Select both "Private" and "Domain"
7. Click "Add"

### Linux/macOS Firewall (ufw)

```bash
sudo ufw allow 8000/tcp
sudo ufw enable
```

### Network Router (if needed)

- Configure port forwarding if accessing from external network
- Set static IP for server machine
- Document server IP/hostname for all users

## Step 4: Start the Application

### Option A: Direct Execution (Development)

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Run server
python manage.py runserver 0.0.0.0:8000
```

**Pros**: Easy to manage, good for testing  
**Cons**: Requires terminal window to stay open, limited concurrency

### Option B: Gunicorn with Systemd (Linux/macOS - Recommended)

**Install Gunicorn:**
```bash
pip install gunicorn
```

**Create systemd service file:**
```bash
sudo nano /etc/systemd/system/timemaster.service
```

**Paste the following:**
```ini
[Unit]
Description=Timesheet & Comp-Off Management Django Application
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/opt/timemaster
ExecStart=/opt/timemaster/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 30 \
    timemaster_project.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable timemaster
sudo systemctl start timemaster
sudo systemctl status timemaster
```

### Option C: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Name: "TimeMaster Server"
4. Trigger: "At startup"
5. Action: "Start a program"
6. Program: `C:\path\to\venv\Scripts\python.exe`
7. Arguments: `manage.py runserver 0.0.0.0:8000`
8. Start in: `C:\path\to\Timemaster automation`
9. Check "Run whether user is logged in or not"

### Option D: Nginx Reverse Proxy (Production)

**Install Nginx:**
```bash
sudo apt-get install nginx
```

**Create Nginx config:**
```bash
sudo nano /etc/nginx/sites-available/timemaster
```

**Paste:**
```nginx
upstream timemaster {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name 192.168.1.100 timemaster.company.local;
    client_max_body_size 100M;

    location / {
        proxy_pass http://timemaster;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/timemaster/staticfiles/;
    }

    location /media/ {
        alias /opt/timemaster/media/;
    }
}
```

**Enable and restart:**
```bash
sudo ln -s /etc/nginx/sites-available/timemaster /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## Step 5: Client Access

### For Users on Network

1. **Get Server IP/Hostname from IT**
   - Example: `192.168.1.100` or `timemaster.company.local`

2. **Open Web Browser**
   - URL: `http://192.168.1.100:8000/timesheet/`
   - Or: `http://timemaster.company.local/timesheet/` (if using Nginx)

3. **Login with Credentials**
   - Use admin account or user account
   - URL to access: `http://192.168.1.100:8000/timesheet/login/`

4. **Create User Accounts** (Admin only)
   - Admin panel: `http://192.168.1.100:8000/admin/`
   - Add users and assign permissions

## Database Management

### Backup Database

```bash
# On server machine
cd "path/to/Timemaster automation"

# Backup
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json

# Check backup size
ls -lh backup_*.json
```

### Backup Database on Schedule

**Linux (Cron):**
```bash
# Add to crontab
crontab -e

# Add line for daily backup at 2 AM
0 2 * * * cd /opt/timemaster && python manage.py dumpdata > backup_$(date +\%Y\%m\%d).json
```

**Windows (Task Scheduler):**
Create a batch file:
```batch
@echo off
cd C:\path\to\Timemaster
python manage.py dumpdata > backup_%date:~10,4%%date:~4,2%%date:~7,2%.json
```

### Restore from Backup

```bash
python manage.py loaddata backup_20240409_120000.json
```

## Monitoring & Maintenance

### Check Application Status

```bash
# Check if port 8000 is active
# Windows:
netstat -ano | findstr :8000

# Linux:
sudo netstat -tulpn | grep :8000
# or
sudo ss -tulpn | grep :8000
```

### View Application Logs

```bash
# If using systemd
sudo journalctl -u timemaster -f

# File logs (create log file)
python manage.py runserver 0.0.0.0:8000 > timemaster.log 2>&1
```

### Common Issues & Solutions

#### Issue: Port Already in Use
```bash
# Use different port
python manage.py runserver 0.0.0.0:8001

# Or kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux:
sudo fuser -k 8000/tcp
```

#### Issue: Cannot Access from Another Machine
1. Check firewall rules
2. Verify IP address in ALLOWED_HOSTS
3. Test connectivity: `ping <server_IP>`
4. Check if Django is running: `netstat -an | grep 8000`

#### Issue: Static Files Not Loading
```bash
python manage.py collectstatic --noinput
```

#### Issue: Database Locked
```bash
# Restart the application service
# Windows (if using Task Scheduler):
taskkill /IM python.exe /F
# Then restart through Task Scheduler

# Linux:
sudo systemctl restart timemaster
```

## Security Considerations

### Network Security

1. **Firewall Rules**
   - Only allow port 8000 from internal network
   - Block external access

2. **VPN Access** (if remote access needed)
   - Configure VPN server first
   - Connect through VPN before accessing

3. **Network Segmentation**
   - Place on dedicated employee subnet if possible
   - Restrict database access to server only

### Application Security

1. **Change Default Credentials**
   - Update admin password after setup
   - Create separate user accounts

2. **Enable HTTPS** (Recommended)
   - Use self-signed certificate for internal network
   - Configure SSL in Nginx

3. **Restrict Permissions**
   - Use Django admin to set user roles
   - Create read-only users if needed

4. **Regular Backups**
   - Automated daily backups
   - Store backups securely
   - Test restore procedure monthly

## Disaster Recovery

### Database Recovery Plan

1. **Regular Backups**: Daily automated backups
2. **Off-site Storage**: Copy backups to shared drive
3. **Recovery Testing**: Monthly restore tests
4. **Documentation**: Keep clear recovery procedures

### Service Continuity

1. **Redundant Setup**: Consider secondary server if critical
2. **Load Balancing**: Set up for high availability
3. **Maintenance Windows**: Schedule during low usage
4. **Communication**: Notify users before maintenance

## Performance Optimization

### Database Optimization

```bash
# Add database indexing in models if needed
# Run migrations after model changes
python manage.py makemigrations
python manage.py migrate
```

### Connection Optimization

For multiple concurrent users:
- Increase Gunicorn workers: `--workers 8`
- Use load balancer (HAProxy/Nginx)
- Monitor CPU and memory usage

### Caching

Consider adding Redis for production:
```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

## Support & Documentation

- Keep admin credentials secure
- Document server location and credentials
- Create user guide for employees
- Provide admin contact for issues
- Schedule regular maintenance windows

---

**Last Updated**: April 2024  
**Django Version**: 4.2  
**Python Version**: 3.8+
