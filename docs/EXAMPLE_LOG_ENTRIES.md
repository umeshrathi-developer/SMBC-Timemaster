# Example Log Entries

This document shows real examples of log entries you can expect to see in each log file.

## timemaster.log - General Application Log

### User Authentication
```
INFO 2026-04-22 10:30:45,123 views 8024 5678 User login successful: john.doe
INFO 2026-04-22 10:35:12,456 views 8024 5678 User login successful: alice.smith
INFO 2026-04-22 14:15:32,789 views 8024 5678 User login successful: manager@company.com
```

### Employee Management
```
INFO 2026-04-22 10:32:15,234 views 8024 5678 New employee created: Jane Smith (ID: EMP042) by user: john.doe
INFO 2026-04-22 10:45:22,567 views 8024 5678 Employee updated: EMP042 - Jane Smith by user: john.doe
WARNING 2026-04-22 11:00:10,891 views 8024 5678 Employee deleted: Jane Smith (ID: EMP042) by user: john.doe
```

### Comp-Off Operations
```
INFO 2026-04-22 11:15:30,123 views 8024 5678 Comp-Off auto-created for John Doe on 2026-04-20 (Reason: Holiday on 2026-04-20)
INFO 2026-04-22 11:20:45,456 views 8024 5678 Comp-Off status updated: EMP001 - Status changed to approved by user: manager
WARNING 2026-04-22 11:30:22,789 views 8024 5678 Comp-Off deducted for John Doe on 2026-04-25
```

### Email Operations
```
INFO 2026-04-22 15:45:30,234 views 8024 5678 Timesheet report emailed successfully to 12 recipients by user: john.doe
INFO 2026-04-22 16:00:15,567 views 8024 5678 Timesheet report email recipients: alice@testt.com, bob@testt.com, charlie@testt.com (3 total)
ERROR 2026-04-22 16:30:45,891 views 8024 5678 Failed to send timesheet email: [Errno 111] Connection refused by mail server
ERROR 2026-04-22 16:31:22,123 views 8024 5678 SMTP authentication failed: Invalid username or password
```

### File Import Operations
```
INFO 2026-04-22 09:00:30,234 utils 8024 5678 Starting timesheet import from file: uploads/timesheet_april.xlsx, import_date: 2026-04-01
INFO 2026-04-22 09:00:31,456 utils 8024 5678 Excel file loaded. Sheets found: ['Timesheet Summary', 'Timesheet Details', 'Attendance Summary', 'Attendance Details']
INFO 2026-04-22 09:01:15,789 utils 8024 5678 Import completed successfully. Summary=45, Details=156, AttSummary=45, AttDetails=312
WARNING 2026-04-22 09:05:30,123 utils 8024 5678 Import completed with 3 errors: ['Row 12: Invalid date format', 'Row 45: Employee ID not found', 'Row 78: Duplicate entry']
ERROR 2026-04-22 09:10:45,456 utils 8024 5678 Failed to import file: [Errno 2] No such file or directory: 'uploads/missing_file.xlsx'
ERROR 2026-04-22 09:15:22,789 utils 8024 5678 Failed to import file: Unsupported format or corrupted file (stack trace included)
```

## errors.log - Error-Specific Log

### Email Errors
```
ERROR 2026-04-22 16:30:45,891 views 8024 5678 Failed to send timesheet email: [Errno 111] Connection refused by mail server
Traceback (most recent call last):
  File "/path/to/views.py", line 703, in manager_timesheet_report
    email_message.send(fail_silently=False)
  File "/path/to/django/core/mail/__init__.py", line 61, in send
    connection = get_connection(self.connection_params)
  File "/path/to/django/core/mail/__init__.py", line 141, in get_connection
    return backend_class(**kwargs)
  ...
smtplib.SMTPServerDisconnected: Connection unexpectedly closed
```

### Import Errors
```
ERROR 2026-04-22 09:10:45,456 utils 8024 5678 Failed to import file: [Errno 2] No such file or directory: 'uploads/missing_file.xlsx'
Traceback (most recent call last):
  File "/path/to/utils.py", line 47, in import_timesheet_file
    workbook = load_workbook(file_path)
  File "/path/to/openpyxl/reader/excel.py", line 315, in load_workbook
    reader = ExcelReader(filename, read_only, data_only, **kw)
  File "/path/to/openpyxl/reader/excel.py", line 145, in __init__
    self.archive = ZipFile(filename)
FileNotFoundError: [Errno 2] No such file or directory: 'uploads/missing_file.xlsx'
```

### Database Errors
```
ERROR 2026-04-22 14:45:30,123 views 8024 5678 Failed to create employee: UNIQUE constraint failed: timesheet_employee.email
Traceback (most recent call last):
  File "/path/to/views.py", line 325, in employee_add
    employee.save()
  File "/path/to/django/db/models/base.py", line 828, in save
    self.save_base(using=using, force_insert=force_insert)
IntegrityError: UNIQUE constraint failed: timesheet_employee.email
```

## access.log - Access Control Log

### Successful Logins
```
INFO 2026-04-22 10:30:45,123 views User login successful: john.doe
INFO 2026-04-22 10:35:12,456 views User login successful: alice.smith
INFO 2026-04-22 14:15:32,789 views User login successful: manager@company.com
```

### Failed Login Attempts
```
WARNING 2026-04-22 10:32:15,234 views Failed login attempt for username: john.doe
WARNING 2026-04-22 10:33:22,567 views Failed login attempt for username: attacker
WARNING 2026-04-22 10:35:45,891 views Failed login attempt for username: guest_user
WARNING 2026-04-22 10:36:10,123 views Failed login attempt for username: admin (3 attempts in 2 minutes)
```

### Unauthorized Access Attempts
```
WARNING 2026-04-22 11:00:30,234 views Unauthorized access attempt to employee_add by user: alice.smith
WARNING 2026-04-22 11:15:45,567 views Unauthorized access attempt to employee_delete by user: jane.doe
WARNING 2026-04-22 11:30:22,891 views Unauthorized access attempt to import_timesheet_data by user: regular_user
WARNING 2026-04-22 11:45:15,123 views Unauthorized access attempt to manager_timesheet_report by user: non_manager
```

---

## How to Search for Specific Patterns

### Find all failed logins
```bash
grep "Failed login attempt" logs/access.log
```

Output:
```
WARNING 2026-04-22 10:32:15,234 views Failed login attempt for username: john.doe
WARNING 2026-04-22 10:33:22,567 views Failed login attempt for username: attacker
```

### Find all unauthorized access
```bash
grep "Unauthorized access" logs/access.log
```

Output:
```
WARNING 2026-04-22 11:00:30,234 views Unauthorized access attempt to employee_add by user: alice.smith
WARNING 2026-04-22 11:15:45,567 views Unauthorized access attempt to employee_delete by user: jane.doe
```

### Find all email errors
```bash
grep -i "email" logs/errors.log
```

Output:
```
ERROR 2026-04-22 16:30:45,891 views 8024 5678 Failed to send timesheet email: [Errno 111] Connection refused
```

### Find all activity for a specific user
```bash
grep "john.doe" logs/timemaster.log
```

Output:
```
INFO 2026-04-22 10:30:45,123 views 8024 5678 User login successful: john.doe
INFO 2026-04-22 10:32:15,234 views 8024 5678 New employee created: Jane Smith (ID: EMP042) by user: john.doe
INFO 2026-04-22 15:45:30,234 views 8024 5678 Timesheet report emailed successfully to 12 recipients by user: john.doe
```

### Find all import operations for a specific date
```bash
grep "2026-04-22" logs/timemaster.log | grep -i import
```

### Count how many times a user logged in
```bash
grep "john.doe" logs/access.log | wc -l
```

### Find errors only
```bash
grep "ERROR" logs/timemaster.log
```

### Find warnings only
```bash
grep "WARNING" logs/timemaster.log
```

---

## Log Entry Format Explanation

Each log entry follows this format:
```
LEVEL TIMESTAMP.MILLISECONDS MODULE PID THREAD MESSAGE
```

Example:
```
INFO 2026-04-22 10:30:45,123 views 8024 5678 User login successful: john.doe
```

Breakdown:
- **INFO** = Log level (INFO, WARNING, ERROR)
- **2026-04-22 10:30:45,123** = Date and time with milliseconds
- **views** = Module name (which file created the log)
- **8024** = Process ID
- **5678** = Thread ID
- **User login successful: john.doe** = Actual log message

---

## Timestamp Format

All logs use ISO 8601 format:
- **Date:** YYYY-MM-DD (e.g., 2026-04-22)
- **Time:** HH:MM:SS,mmm (24-hour format with milliseconds)
- **Example:** 2026-04-22 14:35:22,567 (2:35 PM and 567 milliseconds)

---

## Performance Impact

These log entries will have minimal performance impact:
- Logging runs asynchronously where possible
- Rotating file handlers prevent disk space issues
- INFO and above levels are captured (not DEBUG verbose logging)
- Console output can be disabled in production

---

## Archival

Old log files are automatically rotated:
- Original file: `logs/timemaster.log`
- First backup: `logs/timemaster.log.1`
- Second backup: `logs/timemaster.log.2`
- ... up to `logs/timemaster.log.5`

After 5 backups, the oldest is removed when a new rotation occurs.

---

**Last Updated:** April 22, 2026
**Environment:** Development & Production
