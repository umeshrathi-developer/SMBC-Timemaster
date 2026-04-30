# Logging Implementation Guide

## Overview

A comprehensive logging system has been implemented across the Timemaster Django application to track application events, user access, errors, and data operations.

## Logging Configuration

### Location
`timemaster_project/settings.py` - Lines 107-170

### Log Files Generated

| Log File | Purpose | Contains |
|----------|---------|----------|
| `logs/timemaster.log` | General application logs | INFO level and above |
| `logs/errors.log` | Error-specific logs | ERROR level and above |
| `logs/access.log` | User access/permission events | Access denied, login attempts |

### Log Rotation
- **Max File Size:** 10 MB per log file
- **Backup Count:** 5 rotated backups
- **Format:** `{levelname} {asctime} {module} {process:d} {thread:d} {message}`

## Logger Instances

### 1. Main Application Logger
```python
logger = logging.getLogger('timesheet')
```
Used for general application events.

**Examples:**
```python
logger.info("New employee created: John Doe")
logger.warning("Employee deleted: Jane Smith")
logger.error("Failed to update employee: Database error")
```

### 2. Access Logger
```python
access_logger = logging.getLogger('timesheet.access')
```
Tracks user access and permission checks.

**Examples:**
```python
access_logger.info("User login successful: john.doe")
access_logger.warning("Failed login attempt for username: attacker")
access_logger.warning("Unauthorized access attempt to employee_add by user: john.doe")
```

### 3. Email Logger
```python
email_logger = logging.getLogger('timesheet.email')
```
Tracks email sending operations.

**Examples:**
```python
email_logger.info("Timesheet report emailed successfully to 5 recipients")
email_logger.error("Failed to send timesheet email: SMTP connection refused")
```

### 4. Import Logger
```python
import_logger = logging.getLogger('timesheet.import')
```
Tracks file import operations.

**Examples:**
```python
import_logger.info("Starting timesheet import from file: upload.xlsx")
import_logger.info("Import completed successfully. Summary=45, Details=150")
import_logger.error("Import failed: Invalid Excel format")
```

## What Gets Logged

### User Actions
- **Login/Logout:** Success/failure, username
- **Employee Management:** Create, update, delete operations
- **Permission Denials:** Who tried, what action, when
- **Data Submissions:** Timesheet submissions, Comp-Off creation

### System Events
- **File Imports:** Start time, file name, import date, results
- **Email Sending:** Recipients count, success/failure
- **Error Conditions:** Exception details with stack traces
- **Comp-Off Operations:** Auto-generation, deduction

### Examples of Logged Events

```
INFO 2026-04-22 10:30:45 views 1234 5678 User login successful: john.doe
INFO 2026-04-22 10:32:15 views 1234 5678 New employee created: Jane Smith (ID: EMP001) by user: john.doe
INFO 2026-04-22 10:35:22 views 1234 5678 Comp-Off auto-created for John Doe on 2026-04-20
ERROR 2026-04-22 10:40:10 views 1234 5678 Failed to send timesheet email: SMTP connection refused
WARNING 2026-04-22 10:42:55 views 1234 5678 Unauthorized access attempt to employee_delete by user: john.doe
```

## Reading Logs

### View Main Log
```bash
# From project directory
tail -f logs/timemaster.log
```

### View Error Log
```bash
grep ERROR logs/timemaster.log
# or
cat logs/errors.log
```

### View Access Log
```bash
cat logs/access.log
```

### Search for Specific User Activity
```bash
grep "john.doe" logs/access.log
grep "john.doe" logs/timemaster.log
```

### Search for Specific Operation
```bash
# Email operations
grep "email" logs/timemaster.log -i

# Comp-Off operations
grep "compoff" logs/timemaster.log -i

# Import operations
cat logs/timemaster.log | grep -i import
```

## Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed debugging info | Not currently used |
| **INFO** | Informational messages | Login success, data created |
| **WARNING** | Warning messages | Failed login, permission denied |
| **ERROR** | Error conditions | Email send failure, import error |
| **CRITICAL** | Critical errors | System failures |

## Error Tracking

### How Errors Are Logged

```python
# Regular error logging
logger.error(f"Operation failed: {str(e)}")

# Error with stack trace
logger.error(f"Failed to send email: {exc}", exc_info=True)
```

The `exc_info=True` parameter includes the full stack trace in the log.

### Example Error Log
```
ERROR 2026-04-22 10:40:10 views 1234 5678 Failed to send timesheet email: SMTP connection refused
Traceback (most recent call last):
  File "views.py", line 703, in manager_timesheet_report
    email_message.send(fail_silently=False)
  File ".../django/core/mail/__init__.py", line 61, in send
    ...
```

## Access Control Logging

Every protected view logs access attempts:

```python
if not is_admin(request.user):
    access_logger.warning(f"Unauthorized access attempt to {view_name} by user: {request.user.username}")
    messages.error(request, 'You do not have permission...')
    return redirect('dashboard')
```

### Access Log Examples
```
INFO 2026-04-22 10:30:45 views User login successful: john.doe
WARNING 2026-04-22 10:35:20 views Failed login attempt for username: attacker
WARNING 2026-04-22 10:40:55 views Unauthorized access attempt to employee_delete by user: jane.smith
```

## Monitoring Best Practices

### Daily Monitoring
1. Check `logs/errors.log` for any errors
2. Review `logs/access.log` for unauthorized attempts
3. Verify imports in `logs/timemaster.log`

### Weekly Monitoring
1. Check for patterns in failed logins
2. Review permission denial attempts
3. Monitor email sending issues

### Troubleshooting
1. When a user reports an issue, search logs with their username
2. Check error logs for stack traces
3. Verify email logs for delivery issues
4. Check import logs for data processing errors

## Django Admin Integration

Access logs are also stored in the database via `TimesheetImportLog` model:

1. Go to Django Admin: `/admin/`
2. Navigate to `Timesheet Import Logs`
3. Filter by date or user
4. View import notes and history

## Example Log Analysis

### Find all failed operations for a user
```bash
grep "john.doe" logs/errors.log
```

### Find all email errors
```bash
grep "email" logs/errors.log -i
```

### Find all import operations today
```bash
date=$(date +%Y-%m-%d)
grep "$date" logs/timemaster.log | grep -i import
```

### Find unauthorized access attempts
```bash
grep "Unauthorized" logs/access.log
```

## Future Enhancements

Potential improvements to logging:
- Add DEBUG level logging for development
- Implement log aggregation service
- Add metrics/monitoring dashboard
- Set up alert notifications for errors
- Implement log archival for old files

## Configuration Notes

### To Change Log Level

Edit `timemaster_project/settings.py`:

```python
# Change to DEBUG for more detailed logs
'level': 'DEBUG',  # From 'INFO'
```

### To Add New Logger

```python
# In settings.py LOGGING['loggers']
'new_logger': {
    'handlers': ['console', 'file', 'error_file'],
    'level': 'INFO',
    'propagate': False,
}

# In views.py
new_logger = logging.getLogger('timesheet.new_logger')
new_logger.info("Event message")
```

## Log Cleanup

Logs are automatically rotated when they reach 10 MB. Old logs are preserved in numbered backups (`.1`, `.2`, etc.) up to 5 backups.

To manually clean old logs:
```bash
rm logs/timemaster.log.*
rm logs/errors.log.*
rm logs/access.log.*
```

---

## Summary of Changes

### Files Modified
1. **settings.py** - Added complete LOGGING configuration
2. **views.py** - Added logging to all critical functions
3. **admin.py** - Added logging and removed unused imports
4. **utils.py** - Added logging to import functions

### Logging Added to
- ✅ Authentication (login/logout)
- ✅ Employee management (CRUD)
- ✅ Permission checks
- ✅ Email operations
- ✅ Timesheet imports
- ✅ Comp-Off operations
- ✅ Error conditions
- ✅ Data validations
