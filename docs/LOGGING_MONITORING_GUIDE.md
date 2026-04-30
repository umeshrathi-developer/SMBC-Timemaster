# Logging, Monitoring & Troubleshooting Guide - Timemaster Automation

## LOGGING MECHANISMS IMPLEMENTED

### 1. **Database Logging (TimesheetImportLog Model)**
**Location:** [timesheet/models.py](timesheet/models.py#L155)

```python
class TimesheetImportLog(models.Model):
    """Log of timesheet imports to track versions and timing"""
    import_date = models.DateField()           # Date being imported
    uploaded_by = models.ForeignKey(User)      # Who uploaded it
    created_date = models.DateTimeField()      # When it was uploaded
    notes = models.TextField()                 # Optional admin notes
```

**What it tracks:**
- Import date/month
- Admin user who performed the import
- Exact timestamp of when import occurred
- Admin notes about the import
- Historical versioning of all imports

**Access:**
- Django Admin: `Admin → Timesheet Import Logs`
- View the complete import history with filtering by date

---

### 2. **Audit Trail on All Models**
Every data model has timestamp tracking:

```python
created_date = models.DateTimeField(auto_now_add=True)  # Set once, never changes
updated_date = models.DateTimeField(auto_now=True)      # Updates on every save
```

**Models with audit trail:**
- Employee
- CompOff
- TimesheetSummary
- TimesheetDetails
- AttendanceSummary
- AttendanceDetails
- TimesheetEntry

---

### 3. **Django Messages Framework** 
**Used throughout:** [timesheet/views.py](timesheet/views.py)

Displays user-friendly notifications in real-time:

```python
messages.success(request, 'Operation completed successfully!')
messages.error(request, 'Error occurred: details...')
messages.warning(request, 'Warning: check this...')
messages.info(request, 'Informational message')
```

**Message Categories:**
| Type | Usage | Color |
|------|-------|-------|
| `success` | Operation completed | Green |
| `error` | Operation failed | Red |
| `warning` | Caution needed | Yellow |
| `info` | FYI information | Blue |

**Examples in code:**
- Login success/failure messages
- Employee CRUD operations
- Comp-Off submission confirmations
- Timesheet entry creation/deletion
- Email sending status
- File import results

---

### 4. **Email Error Handling**
**Location:** [timesheet/views.py](timesheet/views.py#L703-L710)

```python
try:
    email_message.send(fail_silently=False)
    messages.success(request, 'Timesheet report emailed successfully.')
except Exception as exc:
    messages.error(request, f'Failed to send email: {exc}')
    # If using console backend, add a note
    if 'console' in settings.EMAIL_BACKEND:
        messages.info(request, 'Email was printed to the console (development mode).')
```

**Error cases handled:**
- Invalid email addresses
- SMTP connection failures
- Authentication errors
- Network timeouts

---

### 5. **File Import Error Handling**
**Location:** [timesheet/views.py](timesheet/views.py#L1490-L1515)

```python
try:
    result = import_timesheet_file(temp_file.name, import_date=import_date)
    if result['success']:
        # Create log entry with detailed counts
        TimesheetImportLog.objects.create(...)
        messages.success(request, f"{result['message']}\n"
            f"Timesheet Summary: {result['summary_count']} rows\n"
            f"Timesheet Details: {result['details_count']} rows\n"...)
    else:
        messages.error(request, f"{result['message']}\n" + 
                       "\n".join(result['errors'][:5]))
except Exception as e:
    messages.error(request, f"Error during import: {str(e)}")
finally:
    # Clean up temp file
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)
```

**Errors tracked:**
- Row parsing errors
- Data validation failures
- File format issues
- Missing sheets
- Duplicate entries

---

### 6. **Date/Time Validation with Error Messages**
**Location:** [timesheet/views.py](timesheet/views.py#L1227-1240)

```python
try:
    year, month = map(int, selected_month.split('-'))
    from datetime import date
    from calendar import monthrange
    selected_date = date(year, month, 1)
except (ValueError, IndexError):
    messages.error(request, 'Invalid month format.')
    return redirect('timesheet_entry_list')
```

---

### 7. **Permission & Authorization Logging**
Every protected view checks permissions and logs denial:

```python
if not is_admin(request.user):
    messages.error(request, 'You do not have permission to access this page.')
    return redirect('dashboard')
```

---

## MONITORING APPROACHES

### 1. **Django Admin Interface**
Access at: `http://localhost:8000/admin/`

**Monitor via Admin:**

| Item | Where | How to Monitor |
|------|-------|----------------|
| **Imports** | Timesheet → Timesheet Import Logs | Filter by date, see uploader, notes |
| **Employees** | Timesheet → Employees | View created/updated timestamps |
| **CompOffs** | Timesheet → CompOffs | Filter by status (PENDING/TAKEN) |
| **Entries** | Timesheet → Timesheet Entries | See submission history |
| **Users** | Auth → Users | Track who's active, last login |

---

### 2. **Database Queries to Monitor**
Run these in Django shell: `python manage.py shell`

```python
# Check recent imports
from timesheet.models import TimesheetImportLog
TimesheetImportLog.objects.all().order_by('-created_date')[:5]

# Check failed entries
from timesheet.models import TimesheetEntry
TimesheetEntry.objects.filter(status='DRAFT').count()

# Check pending CompOffs
from timesheet.models import CompOff
CompOff.objects.filter(status='PENDING').count()

# Check user activity
from django.contrib.auth.models import User
User.objects.filter(last_login__isnull=False).order_by('-last_login')

# Check recent changes
from timesheet.models import Employee
Employee.objects.all().order_by('-updated_date')[:10]
```

---

### 3. **Email Delivery Monitoring**

**Configuration Methods:**

**Development (Console Backend):**
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Emails print to Django console/stdout
```

**Gmail (SMTP Backend):**
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

**Monitor:**
- Check Gmail "Sent" folder for timesheet reports
- Check recipient inboxes for delivery confirmation
- Watch Django messages for send failures

---

### 4. **Import Statistics Tracking**

The import function returns detailed statistics:

```python
result = {
    'success': True/False,
    'message': 'Import successful',
    'summary_count': 45,        # Records imported
    'details_count': 150,       # Rows imported
    'attendance_summary_count': 35,
    'attendance_details_count': 200,
    'errors': [list of error messages]
}
```

---

## TROUBLESHOOTING GUIDE

### **Issue 1: Email Not Sending**

**Symptoms:**
- "Failed to send email" message appears
- Email doesn't arrive in inbox

**Debugging Steps:**

```python
# 1. Check email backend configuration
python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_BACKEND)
>>> print(settings.EMAIL_HOST)
>>> print(settings.EMAIL_PORT)
>>> print(settings.EMAIL_USE_TLS)

# 2. Test email sending
from django.core.mail import EmailMessage
email = EmailMessage(
    'Test Subject',
    'Test Body',
    'from@gmail.com',
    ['to@gmail.com'],
)
email.send()

# 3. Check for errors
# Look at Django console output for SMTP errors
```

**Common causes & fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `SMTPAuthenticationError` | Wrong password | Use App Password, not Gmail password |
| `SMTPException: connection refused` | Wrong host/port | Verify `smtp.gmail.com:587` |
| `Connection refused` | Firewall blocking | Check network/firewall settings |
| `Recipient rejected` | Invalid email | Verify recipient email format |

---

### **Issue 2: File Import Failures**

**Symptoms:**
- "Error during import: ..." message
- Only partial data imported

**Debugging Steps:**

```python
# 1. Check file format
- Must be .xlsx (Excel format)
- Required sheets: "Timesheet Summary", "Timesheet Details", 
  "Attendance Summary", "Attendance Details"

# 2. Check for import errors
python manage.py shell
>>> from timesheet.utils import import_timesheet_file
>>> result = import_timesheet_file('path/to/file.xlsx', import_date='2026-04-01')
>>> result['errors']  # See all errors
>>> result['success']  # Check if succeeded

# 3. Manual inspection
from openpyxl import load_workbook
wb = load_workbook('path/to/file.xlsx')
wb.sheetnames  # Should show required sheets
```

**Common causes:**

| Issue | Solution |
|-------|----------|
| Missing required sheets | Ensure all 4 sheets exist with exact names |
| Wrong column order | Check column sequence in Excel |
| Invalid data types | Verify hours are numeric, dates are valid |
| Duplicate entries | System prevents duplicate (email, date, project) |
| Empty rows | System skips empty rows automatically |

---

### **Issue 3: Comp-Off Not Auto-Generated**

**Symptoms:**
- No Comp-Off created when timesheet submitted for weekend work
- Pending CompOffs not deducted for missing weekdays

**Debugging:**

```python
python manage.py shell

# 1. Check timesheet entries
from timesheet.models import TimesheetEntry
entries = TimesheetEntry.objects.filter(status='SUBMITTED')
# Should have entries for weekends with hours >= 8

# 2. Check CompOffs
from timesheet.models import CompOff
compoffs = CompOff.objects.all()
compoffs.count()  # Should see auto-generated ones

# 3. Verify date is weekend/holiday
from datetime import date
from timesheet.views import is_weekend_or_fixed_holiday
test_date = date(2026, 4, 25)  # Saturday
is_weekend_or_fixed_holiday(test_date)  # Should be True

# 4. Check if duplicate exists
CompOff.objects.filter(employee_id=1, working_date=test_date).exists()
```

---

### **Issue 4: Permission Denied Errors**

**Symptoms:**
- "You do not have permission" message
- User can't access features

**Debugging:**

```python
python manage.py shell

# 1. Check user permissions
from django.contrib.auth.models import User
user = User.objects.get(username='username')
print(user.is_staff)  # Should be True for admin
print(user.groups.all())  # Should include 'Admin' group

# 2. Check employee link
from timesheet.models import Employee
emp = Employee.objects.filter(user=user).first()
print(emp)  # Should not be None for regular employees

# 3. Fix: Make user admin
user.is_staff = True
user.save()

# 4. Fix: Create employee record
Employee.objects.create(user=user, name='John Doe', employee_id='EMP001')
```

---

### **Issue 5: Timesheet Entry Not Submitting**

**Symptoms:**
- Submit button doesn't work
- Status stays as DRAFT

**Debugging:**

```python
python manage.py shell

# 1. Check for DRAFT entries
from timesheet.models import TimesheetEntry
entries = TimesheetEntry.objects.filter(
    employee__name='John Doe',
    status='DRAFT'
).count()
print(f"Draft entries: {entries}")

# 2. Check for validation errors
from timesheet.models import TimesheetEntry
from datetime import date
# Verify all required fields are present
entries = TimesheetEntry.objects.filter(
    employee_id=1,
    date__gte=date(2026, 4, 1),
    date__lte=date(2026, 4, 30)
)
for e in entries:
    print(f"{e.date}: {e.hours} hrs - {e.status}")

# 3. Manual submission
entry = TimesheetEntry.objects.get(pk=1)
entry.status = 'SUBMITTED'
entry.save()
```

---

## MONITORING CHECKLIST

Daily checks for production:

- [ ] Check Django Admin → Imports for new imports
- [ ] Review failed emails in messages
- [ ] Check Comp-Off pending count (shouldn't grow indefinitely)
- [ ] Review user login activity (last_login)
- [ ] Verify timesheet entries are being submitted
- [ ] Check for validation errors in import logs

---

## LOGS TO REVIEW REGULARLY

1. **Timesheet Import Log** (Django Admin)
   - New imports added daily/weekly
   - Check for upload errors in system

2. **Django Messages** (Web UI)
   - Appear after each action
   - Indicate success/failure

3. **Console Output** (Development)
   - Email sending events
   - Stack traces for exceptions

4. **Database Audit Trail**
   - created_date / updated_date on all records
   - Tracks data changes

---

## ENVIRONMENT CONFIGURATION FOR MONITORING

Set these in `.env` file:

```env
# Logging level (INFO, DEBUG, WARNING, ERROR)
LOG_LEVEL=INFO

# Email backend (console for dev, smtp for production)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# For SMTP errors logging
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## QUICK REFERENCE: WHERE TO FIND INFORMATION

| What to Check | Where to Look | How |
|---------------|---------------|-----|
| Import history | Django Admin → Timesheet Import Logs | Filter by date |
| Email errors | Web UI messages | After email action |
| Data changes | Each model's created/updated dates | Django Admin |
| User activity | Auth → Users (last_login) | View dashboard |
| Comp-Off status | Timesheet → CompOffs | Filter by PENDING/TAKEN |
| Employee records | Timesheet → Employees | Search by name |
| Timesheet entries | Timesheet → Timesheet Entries | Filter by employee/status |

