# Logging Quick Reference for Developers

## How to Add Logging to Your Code

### 1. Import Logging (Already Done in All Views)

```python
import logging

# Get logger instance
logger = logging.getLogger('timesheet')
access_logger = logging.getLogger('timesheet.access')
email_logger = logging.getLogger('timesheet.email')
import_logger = logging.getLogger('timesheet.import')
```

### 2. Common Logging Patterns

#### Pattern 1: Log Successful Operations
```python
def create_employee(request):
    employee = Employee.objects.create(
        name=request.POST['name'],
        email=request.POST['email']
    )
    logger.info(f"New employee created: {employee.name} (ID: {employee.employee_id}) by user: {request.user.username}")
    return redirect('employee_list')
```

#### Pattern 2: Log Failed Authorization
```python
def delete_employee(request, emp_id):
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to delete_employee by user: {request.user.username}")
        messages.error(request, 'You do not have permission')
        return redirect('dashboard')
    
    employee = Employee.objects.get(id=emp_id)
    logger.warning(f"Employee deleted: {employee.name} (ID: {employee.employee_id}) by user: {request.user.username}")
    employee.delete()
    return redirect('employee_list')
```

#### Pattern 3: Log with Try-Except
```python
def send_email(recipients, subject, message):
    try:
        email = EmailMessage(subject, message, to=recipients)
        email.send(fail_silently=False)
        email_logger.info(f"Email sent successfully to {len(recipients)} recipients")
    except Exception as e:
        email_logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        raise
```

#### Pattern 4: Log Search/Filter Operations
```python
def employee_report(request):
    search_term = request.GET.get('search', '')
    employees = Employee.objects.filter(name__icontains=search_term)
    logger.info(f"Employee search: '{search_term}' returned {employees.count()} results by user: {request.user.username}")
    return render(request, 'employee_report.html', {'employees': employees})
```

#### Pattern 5: Log Data Validation Errors
```python
def save_timesheet(request):
    try:
        # Validate data
        if not validate_timesheet_data(data):
            logger.warning(f"Invalid timesheet data submitted by user: {request.user.username}")
            return JsonResponse({'error': 'Invalid data'}, status=400)
        
        # Save data
        timesheet.save()
        logger.info(f"Timesheet saved successfully by user: {request.user.username}")
    except Exception as e:
        logger.error(f"Timesheet save failed: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
```

---

## Logger Types and When to Use Each

### 1. Main Logger (`logger`)
Use for general application events:
- Employee CRUD operations
- Status changes
- Business logic execution
- Import/Export operations
- Report generation

```python
logger.info("Comp-Off auto-created for John Doe on 2026-04-20")
logger.warning("Employee deleted: Jane Smith (ID: EMP001)")
logger.error("Failed to update timesheet: Database error")
```

### 2. Access Logger (`access_logger`)
Use for authentication and authorization:
- Login success/failure
- Permission denials
- Unauthorized access attempts
- Role-based access violations

```python
access_logger.info("User login successful: john.doe")
access_logger.warning("Failed login attempt for username: attacker")
access_logger.warning("Unauthorized access attempt to employee_delete by user: jane.smith")
```

### 3. Email Logger (`email_logger`)
Use for email operations:
- Email send success/failure
- Email delivery issues
- SMTP errors
- Recipient tracking

```python
email_logger.info(f"Timesheet report emailed successfully to {len(recipients)} recipients")
email_logger.error(f"Failed to send email: SMTP connection refused", exc_info=True)
```

### 4. Import Logger (`import_logger`)
Use for file operations:
- File import start/end
- Row-level errors
- Import statistics
- Processing results

```python
import_logger.info("Starting timesheet import from file: upload.xlsx")
import_logger.warning("Import completed with 3 errors")
import_logger.error("Failed to import file: Invalid format", exc_info=True)
```

---

## Log Levels Explained

| Level | Color | Usage |
|-------|-------|-------|
| **INFO** | 🟦 Blue | Normal operations, status changes |
| **WARNING** | 🟨 Yellow | Unexpected but recoverable issues |
| **ERROR** | 🟥 Red | Errors that need attention |
| **DEBUG** | 🟩 Green | Development only, detailed info |

### When to Use Each Level

```python
# INFO - Normal flow
logger.info("User logged in successfully")
logger.info("Employee created: John Doe")
logger.info("Report generated successfully")

# WARNING - Something unusual but handled
access_logger.warning("Failed login attempt")
logger.warning("Employee deleted")
logger.warning("Import completed with errors")

# ERROR - Something failed
logger.error("Failed to send email: SMTP error")
logger.error("Database query failed")
logger.error("File upload rejected: Invalid format")

# DEBUG - Detailed info (development only)
logger.debug("About to process row 42")
logger.debug("Employee object created in memory")
```

---

## Best Practices

### ✅ DO

```python
# ✅ Include relevant context
logger.info(f"New employee created: {employee.name} (ID: {employee.employee_id}) by user: {request.user.username}")

# ✅ Use consistent format
logger.warning(f"Unauthorized access attempt to {view_name} by user: {request.user.username}")

# ✅ Include error stack traces
logger.error(f"Failed to process: {str(e)}", exc_info=True)

# ✅ Use appropriate level
access_logger.warning("Failed login attempt")  # WARNING, not ERROR
logger.info("Import started")  # INFO, not DEBUG

# ✅ Log at decision points
if not is_admin(request.user):
    access_logger.warning(f"Unauthorized: {request.user.username}")
```

### ❌ DON'T

```python
# ❌ Log sensitive data
logger.info(f"User password: {password}")  # NEVER!

# ❌ Log system.exit() calls
import sys
sys.exit()  # Don't log this

# ❌ Use print() instead of logging
print("Something happened")  # Use logger instead

# ❌ Vague messages
logger.error("Error occurred")  # Too vague

# ❌ Log at wrong level
logger.info("Failed to send email")  # Should be ERROR
logger.error("User logged in")  # Should be INFO
```

---

## Common Logging Scenarios

### Scenario 1: Login Attempt
```python
def login_view(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    user = authenticate(username=username, password=password)
    if user:
        auth_login(request, user)
        access_logger.info(f"User login successful: {username}")
    else:
        access_logger.warning(f"Failed login attempt for username: {username}")
        messages.error(request, 'Invalid username or password')
    
    return redirect('dashboard')
```

### Scenario 2: Create Operation with Authorization
```python
def employee_add(request):
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to employee_add by user: {request.user.username}")
        messages.error(request, 'You do not have permission')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            logger.info(f"New employee created: {employee.name} (ID: {employee.employee_id}) by user: {request.user.username}")
            messages.success(request, 'Employee added successfully')
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    
    return render(request, 'employee_form.html', {'form': form})
```

### Scenario 3: Email Operation
```python
def send_report_email(request):
    try:
        recipients = get_email_recipients()
        email_message = EmailMessage(
            subject='Timesheet Report',
            body=generate_report(),
            to=recipients
        )
        email_message.send(fail_silently=False)
        email_logger.info(f"Timesheet report emailed successfully to {len(recipients)} recipients by user: {request.user.username}")
        messages.success(request, 'Email sent successfully')
    except Exception as e:
        email_logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        logger.error(f"Email error for user {request.user.username}: {str(e)}")
        messages.error(request, 'Failed to send email')
    
    return redirect('manager_dashboard')
```

### Scenario 4: File Import with Error Handling
```python
def import_file(request):
    try:
        file = request.FILES['file']
        import_logger.info(f"Starting import from file: {file.name}")
        
        results = import_timesheet_file(file.temporary_file_path())
        
        if results['success']:
            import_logger.info(f"Import completed successfully. Summary={results['summary_count']}, Details={results['details_count']}")
            messages.success(request, 'Import completed successfully')
        else:
            import_logger.warning(f"Import completed with {len(results['errors'])} errors")
            messages.warning(request, f"Import completed with {len(results['errors'])} errors")
    
    except Exception as e:
        import_logger.error(f"Failed to import file: {str(e)}", exc_info=True)
        messages.error(request, 'Import failed')
    
    return redirect('import_page')
```

---

## Testing Your Logging

### Test 1: Verify Logger Output
```python
# In Django shell
python manage.py shell

>>> import logging
>>> logger = logging.getLogger('timesheet')
>>> logger.info('Test message')
>>> # Check logs/timemaster.log - should have the message
```

### Test 2: Test Access Logger
```python
>>> access_logger = logging.getLogger('timesheet.access')
>>> access_logger.warning('Test warning')
>>> # Check logs/access.log - should have the message
```

### Test 3: Test with Error Stack Trace
```python
>>> try:
...     1 / 0
... except Exception as e:
...     logger.error(f"Error occurred: {str(e)}", exc_info=True)
>>> # Check logs/errors.log - should include stack trace
```

---

## Viewing Logs While Developing

### Real-time Log Monitoring
```bash
# In one terminal, watch the main log
tail -f logs/timemaster.log

# In another terminal, watch errors
tail -f logs/errors.log

# In another terminal, watch access logs
tail -f logs/access.log
```

### Search Logs Quickly
```bash
# Find specific user activity
grep "john.doe" logs/*.log

# Find all errors
grep "ERROR" logs/timemaster.log

# Find all warnings
grep "WARNING" logs/timemaster.log

# Count occurrences
grep "import" logs/timemaster.log | wc -l
```

---

## Adding Logging to New Views

### Template for New View
```python
def my_new_view(request):
    """
    Description of what this view does
    """
    # 1. Authorization check
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to my_new_view by user: {request.user.username}")
        messages.error(request, 'You do not have permission')
        return redirect('dashboard')
    
    # 2. Log start of operation
    logger.info(f"User {request.user.username} accessed my_new_view")
    
    try:
        # 3. Perform operation
        data = get_data()
        
        # 4. Log success
        logger.info(f"Operation completed successfully for user: {request.user.username}")
        
    except Exception as e:
        # 5. Log error with stack trace
        logger.error(f"Operation failed for user {request.user.username}: {str(e)}", exc_info=True)
        messages.error(request, 'Operation failed')
    
    # 6. Return response
    return render(request, 'template.html', {'data': data})
```

---

## Troubleshooting Logging

### No logs are being written
```bash
# Check if logs directory exists
ls -la logs/

# If missing, create it
mkdir -p logs

# Check permissions
chmod 755 logs/
```

### Logs are not appearing in real-time
```bash
# Make sure you're using the correct logger name
logger = logging.getLogger('timesheet')  # Correct
logger = logging.getLogger('myapp')      # Wrong

# Check log level in settings
'level': 'INFO'  # Not 'DEBUG'
```

### Too many logs being generated
```python
# In settings.py, increase log level
'level': 'WARNING'  # Only show warnings and errors
```

---

## Quick Copy-Paste Examples

### Info Log
```python
logger.info(f"Operation completed for user: {request.user.username}")
```

### Warning Log
```python
access_logger.warning(f"Unauthorized access attempt by user: {request.user.username}")
```

### Error Log
```python
logger.error(f"Failed to process: {str(e)}", exc_info=True)
```

### Email Log
```python
email_logger.info(f"Email sent to {len(recipients)} recipients")
```

### Import Log
```python
import_logger.info(f"Import completed: {count} records processed")
```

---

**Last Updated:** April 22, 2026
**Version:** 1.0
