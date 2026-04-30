# Production Logging & Monitoring Setup

## Overview

This guide provides instructions for setting up logging and monitoring in production environments.

## 1. Log Directory Setup

### Create Logs Directory
```bash
# In project root
mkdir -p logs
chmod 755 logs
```

### Set Proper Permissions
```bash
# Ensure web server user can write to logs
sudo chown www-data:www-data logs/
sudo chmod 775 logs/
```

### Docker Setup (if using containers)
```dockerfile
# In Dockerfile
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Ensure proper ownership
RUN chown -R www-data:www-data /app/logs
```

---

## 2. Environment-Specific Configuration

### Development Environment
```python
# settings.py
if DEBUG:
    LOGGING['handlers']['console']['level'] = 'DEBUG'
    LOGGING['loggers']['timesheet']['level'] = 'DEBUG'
    LOGGING['loggers']['django']['level'] = 'DEBUG'
```

### Production Environment
```python
# settings.py
if not DEBUG:
    # Use INFO level (not DEBUG) to reduce log volume
    LOGGING['handlers']['console']['level'] = 'INFO'
    LOGGING['loggers']['timesheet']['level'] = 'INFO'
    
    # Ensure errors always logged
    LOGGING['loggers']['timesheet']['level'] = 'WARNING'
```

---

## 3. Nginx Configuration (Log Rotation)

### Install logrotate
```bash
sudo apt-get install logrotate
```

### Create Rotation Config
```bash
sudo nano /etc/logrotate.d/timemaster
```

### Logrotate Configuration
```
/path/to/project/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload gunicorn
    endscript
}
```

### Test Logrotate
```bash
sudo logrotate -d /etc/logrotate.d/timemaster
sudo logrotate -f /etc/logrotate.d/timemaster
```

---

## 4. Systemd Service Integration

### Create Service File
```bash
sudo nano /etc/systemd/system/timemaster.service
```

### Service Configuration
```ini
[Unit]
Description=Timemaster Django Application
After=network.target
Requires=gunicorn.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
EnvironmentFile=/etc/timemaster/timemaster.env
ExecStart=/path/to/venv/bin/gunicorn timemaster_project.wsgi:application

# Ensure logs directory exists
ExecStartPre=/bin/mkdir -p /path/to/project/logs

# Enable journalctl logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=timemaster

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable timemaster.service
sudo systemctl start timemaster.service
```

### View Service Logs
```bash
sudo journalctl -u timemaster.service -f
```

---

## 5. Centralized Log Collection

### Using ELK Stack (Elasticsearch, Logstash, Kibana)

#### Install Filebeat
```bash
wget https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.0.0-amd64.deb
sudo dpkg -i filebeat-8.0.0-amd64.deb
```

#### Configure Filebeat
```yaml
# /etc/filebeat/filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /path/to/project/logs/*.log
  multiline.pattern: '^\['
  multiline.negate: true
  multiline.match: after

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "timemaster-%{+yyyy.MM.dd}"

processors:
  - add_host_metadata: ~
  - add_process_metadata: ~
```

#### Start Filebeat
```bash
sudo systemctl start filebeat
sudo systemctl enable filebeat
```

---

## 6. Log Aggregation with rsyslog

### Configure rsyslog
```bash
sudo nano /etc/rsyslog.d/30-timemaster.conf
```

### Rsyslog Configuration
```
:programname, isequal, "timemaster" /var/log/timemaster.log
```

### Send to Remote Syslog Server
```
:programname, isequal, "timemaster" @@remote.server.com:514
```

---

## 7. Alert Configuration

### Email Alerts for Errors

#### Install mail-utils
```bash
sudo apt-get install mailutils
```

#### Create Alert Script
```bash
#!/bin/bash
# /usr/local/bin/check_timemaster_errors.sh

ERROR_COUNT=$(grep "ERROR" /path/to/project/logs/errors.log | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    mail -s "Timemaster Errors Detected" admin@company.com <<EOF
$ERROR_COUNT errors found in Timemaster.

Recent errors:
$(tail -10 /path/to/project/logs/errors.log)
EOF
fi
```

#### Schedule with Cron
```bash
# Check every hour
0 * * * * /usr/local/bin/check_timemaster_errors.sh

# Or check every 30 minutes
*/30 * * * * /usr/local/bin/check_timemaster_errors.sh
```

### Disk Space Alerts

#### Script to Monitor Log Size
```bash
#!/bin/bash
# /usr/local/bin/check_log_disk.sh

LOG_DIR="/path/to/project/logs"
MAX_SIZE_MB=500
CURRENT_SIZE_MB=$(du -sh "$LOG_DIR" | cut -f1 | tr -d 'MG')

if [ "$CURRENT_SIZE_MB" -gt "$MAX_SIZE_MB" ]; then
    mail -s "Timemaster Logs Disk Usage Alert" admin@company.com <<EOF
Log directory is using ${CURRENT_SIZE_MB}MB (limit: ${MAX_SIZE_MB}MB)

Please review and archive old logs.
EOF
fi
```

---

## 8. Log Monitoring Commands

### Real-time Monitoring
```bash
# Watch main log
watch -n 5 tail -f logs/timemaster.log

# Watch errors
watch -n 5 tail -f logs/errors.log

# Watch access
watch -n 5 tail -f logs/access.log
```

### Daily Log Summary
```bash
#!/bin/bash
# /usr/local/bin/daily_log_summary.sh

echo "=== Timemaster Daily Log Summary ==="
echo "Date: $(date)"
echo ""

echo "Total Logins:"
grep "User login successful" logs/access.log | wc -l

echo "Failed Logins:"
grep "Failed login attempt" logs/access.log | wc -l

echo "Unauthorized Access Attempts:"
grep "Unauthorized access" logs/access.log | wc -l

echo "Errors Today:"
grep "$(date +%Y-%m-%d)" logs/errors.log | wc -l

echo "Emails Sent:"
grep "emailed successfully" logs/timemaster.log | wc -l

echo "Imports Completed:"
grep "Import completed" logs/timemaster.log | wc -l
```

---

## 9. Monitoring Dashboard

### Create Monitoring Script
```python
# /path/to/project/management/commands/log_stats.py

from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
import os

class Command(BaseCommand):
    help = 'Display log statistics'

    def handle(self, *args, **options):
        log_file = 'logs/timemaster.log'
        errors_file = 'logs/errors.log'
        access_file = 'logs/access.log'
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Count by level
        info_count = len([l for l in lines if 'INFO' in l])
        warning_count = len([l for l in lines if 'WARNING' in l])
        error_count = len([l for l in lines if 'ERROR' in l])
        
        self.stdout.write(f"INFO: {info_count}")
        self.stdout.write(self.style.WARNING(f"WARNING: {warning_count}"))
        self.stdout.write(self.style.ERROR(f"ERROR: {error_count}"))
        
        # File sizes
        for filename in [log_file, errors_file, access_file]:
            if os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                self.stdout.write(f"{filename}: {size_mb:.2f} MB")
```

### Run Statistics
```bash
python manage.py log_stats
```

---

## 10. Performance Considerations

### Optimize for High-Volume Logging

```python
# settings.py - For high-traffic sites
LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',  # Only INFO and above
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/timemaster.log',
            'maxBytes': 5242880,  # 5 MB (reduced from 10 MB)
            'backupCount': 3,     # Keep 3 backups (reduced from 5)
            'formatter': 'simple',
        },
    },
}
```

### Disable Verbose Logging in Production
```python
# settings.py
if not DEBUG:
    # Disable DEBUG logs
    LOGGING['loggers']['django']['level'] = 'WARNING'
    
    # Only track errors and access
    LOGGING['loggers']['timesheet']['level'] = 'WARNING'
```

---

## 11. Backup and Archival

### Weekly Backup Script
```bash
#!/bin/bash
# /usr/local/bin/backup_logs.sh

BACKUP_DIR="/path/to/backups"
LOG_DIR="/path/to/project/logs"
DATE=$(date +%Y-%m-%d)

# Create backup
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" "$LOG_DIR"

# Keep only 30 days of backups
find "$BACKUP_DIR" -name "logs_*.tar.gz" -mtime +30 -delete

echo "Logs backed up to $BACKUP_DIR/logs_$DATE.tar.gz"
```

### Schedule Backup
```bash
# Backup every Sunday at 2 AM
0 2 * * 0 /usr/local/bin/backup_logs.sh
```

---

## 12. Troubleshooting Production Logs

### No Logs Being Generated
```bash
# Check logs directory exists
ls -la logs/

# Check permissions
chmod 755 logs/
chmod 644 logs/*

# Check Django settings
python manage.py shell
>>> import logging
>>> logging.getLogger('timesheet').info('Test')
```

### Logs Not Rotating
```bash
# Test logrotate
sudo logrotate -d /etc/logrotate.d/timemaster

# Force rotation
sudo logrotate -f /etc/logrotate.d/timemaster
```

### Disk Space Issues
```bash
# Check log size
du -sh logs/

# Cleanup old logs
find logs/ -name "*.log.*" -mtime +30 -delete
```

---

## 13. Security Considerations

### Restrict Log Access
```bash
# Only admin can read logs
sudo chmod 640 logs/*.log
sudo chown www-data:adm logs/*.log
```

### Sanitize Sensitive Data
The logging system automatically prevents logging:
- Passwords
- API keys
- Personal identification data

### Log File Permissions
```bash
# Correct permissions
-rw-r----- 1 www-data adm logs/timemaster.log
-rw-r----- 1 www-data adm logs/errors.log
-rw-r----- 1 www-data adm logs/access.log
```

---

## 14. Monitoring Checklist

Daily:
- [ ] Check error log for critical issues
- [ ] Verify log files are being written
- [ ] Check disk space usage

Weekly:
- [ ] Review access patterns for anomalies
- [ ] Check for repeated errors
- [ ] Verify log rotation working

Monthly:
- [ ] Archive old logs
- [ ] Review log statistics
- [ ] Capacity planning for log growth

---

## 15. Quick Reference

### View Recent Errors
```bash
tail -20 logs/errors.log
```

### Count Errors by Type
```bash
grep "ERROR" logs/timemaster.log | grep -oP "(?<=ERROR: ).*" | sort | uniq -c
```

### Monitor in Real-time
```bash
tail -f logs/timemaster.log | grep -E "(ERROR|WARNING|emailed)"
```

### Search for User Activity
```bash
grep "john.doe" logs/*.log
```

### Get Log Statistics
```bash
wc -l logs/*.log
du -sh logs/
```

---

**Last Updated:** April 22, 2026
**Environment:** Production
