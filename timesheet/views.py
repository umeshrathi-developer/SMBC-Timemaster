from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from datetime import datetime, date, timedelta
import logging
import threading
from .models import Project, Employee, CompOff, Holiday, TimesheetSummary, TimesheetDetails, AttendanceSummary, AttendanceDetails, TimesheetEntry
from .forms import (
    EmployeeForm, CompOffForm, UserRegistrationForm, ChangePasswordForm,
    PasswordResetSelectionForm, TimesheetEntryForm, ClientTimesheetImportForm
)

# Initialize loggers
logger = logging.getLogger('timesheet')
access_logger = logging.getLogger('timesheet.access')
email_logger = logging.getLogger('timesheet.email')


# ============ HELPER FUNCTIONS ============

def is_admin(user):
    """Check if user is admin (staff) or in Admin group"""
    return user.is_staff or user.groups.filter(name='Admin').exists()


def is_employee(user):
    """Check if user is in Employee group"""
    return user.groups.filter(name='Employee').exists()


def can_access_employee_features(user):
    """Check if user can access employee-facing Comp-Off and Timesheet features."""
    return is_admin(user) or is_employee(user)


def get_user_employee(user):
    """Get the Employee record associated with the logged-in user"""
    try:
        return Employee.objects.get(user=user)
    except Employee.DoesNotExist:
        return None


def get_employee_project_choices(employee):
    """Return dropdown choices for projects available to the employee."""
    if employee and employee.project:
        project_name = employee.project.project
        return [(project_name, project_name)]
    return []


def get_employee_location_name(employee):
    """Return the employee's location name for text-based holiday applicability."""
    location = getattr(employee, 'location', None)
    return getattr(location, 'name', location) or ''


def deny_employee_feature_access(request, view_name):
    """Redirect users who are not allowed to access employee features."""
    access_logger.warning(
        f"Unauthorized employee feature access attempt to {view_name} by user: {request.user.username}"
    )
    messages.error(request, 'You do not have permission to access this page.')
    return redirect('dashboard')


def send_html_email_async(subject, html_message, from_email, recipients, success_log_message, failure_log_message):
    """Send an HTML email in a background thread."""
    def _send():
        email_message = EmailMessage(subject, html_message, from_email, recipients)
        email_message.content_subtype = 'html'
        try:
            email_message.send(fail_silently=False)
            email_logger.info(success_log_message)
        except Exception as exc:
            email_logger.error(f"{failure_log_message}: {exc}", exc_info=True)
            logger.error(f"{failure_log_message}: {str(exc)}")

    threading.Thread(target=_send, daemon=True).start()


def get_report_email_recipients():
    """Return configured report recipients as a clean list of email strings."""
    recipients = getattr(settings, 'REPORT_EMAIL_RECIPIENTS', [])
    if isinstance(recipients, str):
        recipients = recipients.split(',')

    return [
        str(recipient).strip()
        for recipient in recipients
        if str(recipient).strip()
    ]


def get_location_holiday_filter(location):
    """Return a holiday filter for the given location, including global holidays."""
    location = getattr(location, 'name', location) or ''
    if location:
        return Q(location=location) | Q(location='')
    return Q()


def is_holiday_date(date_obj, employee=None, exclude_special=False):
    """Check if date is a holiday.
    
    Args:
        date_obj: Date to check
        employee: Employee whose location should be used for holiday lookup
        exclude_special: If True, ignore SPECIAL_HOLIDAY type
    """
    holiday_types = ['PUBLIC_HOLIDAY', 'WEEKEND']
    if not exclude_special:
        holiday_types.append('SPECIAL_HOLIDAY')

    holiday_filters = Q(
        date=date_obj,
        holiday_type__in=holiday_types
    ) & get_location_holiday_filter(get_employee_location_name(employee))

    return Holiday.objects.filter(holiday_filters).exists()


def is_weekend_or_fixed_holiday(date_obj, employee=None):
    """Check if date is weekend (Sat/Sun) or PUBLIC_HOLIDAY.
    
    Used to identify eligible Comp-Off days (not SPECIAL_HOLIDAY).
    """
    # Saturday=5, Sunday=6 by weekday()
    if date_obj.weekday() >= 5:
        return True
    
    holiday_filters = Q(
        date=date_obj,
        holiday_type='PUBLIC_HOLIDAY'
    ) & get_location_holiday_filter(get_employee_location_name(employee))

    return Holiday.objects.filter(holiday_filters).exists()


def get_date_type(date_obj, employee=None):
    """Get the type of date (Weekend or Holiday name).
    
    Returns:
        'Weekend' if Saturday/Sunday
        Holiday display name if PUBLIC_HOLIDAY/SPECIAL_HOLIDAY
        Empty string if regular working day
    """
    if date_obj.weekday() >= 5:
        return 'Weekend'
    holiday_filters = Q(date=date_obj) & get_location_holiday_filter(get_employee_location_name(employee))
    holiday = Holiday.objects.filter(holiday_filters).first()
    if holiday:
        return holiday.get_holiday_type_display()
    return ''


def auto_deduct_compoff_for_missing_weekdays(employee, selected_date):
    """Auto-deduct accrued Comp-Off for missing weekday timesheet entries
    
    For a given month:
    1. Find all weekdays (excluding weekends and PUBLIC_HOLIDAY/SPECIAL_HOLIDAY)
    2. Check which dates have no timesheet entries
    3. For each missing date, find oldest PENDING Comp-Off and mark as TAKEN
    
    Args:
        employee: Employee instance
        selected_date: Date object representing the month (e.g., date(2026, 3, 1))
    """
    from datetime import date
    from calendar import monthrange
    
    # Get all days in the month
    days_in_month = monthrange(selected_date.year, selected_date.month)[1]
    month_start = date(selected_date.year, selected_date.month, 1)
    month_end = date(selected_date.year, selected_date.month, days_in_month)
    
    # Find all weekdays in the month (excluding holidays)
    missing_dates = []
    current = month_start
    
    while current <= month_end:
        # Check if it's a weekday (Monday=0 to Friday=4)
        if current.weekday() < 5:
            # Check if it's a holiday (PUBLIC_HOLIDAY or SPECIAL_HOLIDAY)
            if not is_holiday_date(current, employee=employee, exclude_special=True):
                # Check if employee has any timesheet entry for this date
                has_entry = TimesheetEntry.objects.filter(
                    employee=employee,
                    date=current
                ).exists()
                
                if not has_entry:
                    missing_dates.append(current)
        
        current += timedelta(days=1)
    
    # For each missing date, deduct the oldest PENDING CompOff
    compoff_deducted = 0
    for missing_date in missing_dates:
        # Get oldest PENDING Comp-Off for this employee
        oldest_compoff = CompOff.objects.filter(
            employee=employee,
            status='PENDING',
            compoff_date__isnull=True,  # Not yet scheduled
            working_date__lte=missing_date,
        ).order_by('created_date').first()
        
        if oldest_compoff:
            # Mark it as TAKEN for this missing date
            oldest_compoff.compoff_date = missing_date
            oldest_compoff.status = 'TAKEN'
            oldest_compoff.save()
            compoff_deducted += 1
    
    return compoff_deducted


def auto_deduct_compoff_for_missing_weekdays_in_range(employee, from_date, to_date):
    """Mark PENDING CompOffs as TAKEN for missing weekday entries in a date range.
    
    For each weekday (Mon-Fri) with no timesheet entry, deduct one PENDING CompOff.
    """
    # Find missing weekdays in the range
    missing_dates = []
    current = from_date
    
    while current <= to_date:
        if current.weekday() < 5 and not is_holiday_date(current, employee=employee, exclude_special=False):
            if not TimesheetEntry.objects.filter(employee=employee, date=current).exists():
                missing_dates.append(current)
        current += timedelta(days=1)
    
    # For each missing date, deduct the oldest PENDING CompOff
    compoff_deducted = 0
    for missing_date in missing_dates:
        # Get oldest PENDING Comp-Off for this employee
        oldest_compoff = CompOff.objects.filter(
            employee=employee,
            status='PENDING',
            compoff_date__isnull=True,  # Not yet scheduled
            working_date__lte=missing_date,
        ).order_by('created_date').first()
        
        if oldest_compoff:
            # Mark it as TAKEN for this missing date
            oldest_compoff.compoff_date = missing_date
            oldest_compoff.status = 'TAKEN'
            oldest_compoff.save()
            compoff_deducted += 1
    
    return compoff_deducted


def has_submitted_entries_in_range(employee, from_date, to_date):
    """Check whether a date range has any submitted entries."""
    return TimesheetEntry.objects.filter(
        employee=employee,
        date__gte=from_date,
        date__lte=to_date,
        status='SUBMITTED'
    ).exists()



# ============ AUTHENTICATION VIEWS ============

def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            access_logger.info(f"User login successful: {username}")
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            access_logger.warning(f"Failed login attempt for username: {username}")
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'registration/login.html')


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ============ PASSWORD MANAGEMENT ============

@login_required(login_url='login')
def change_password(request):
    """Change password for logged-in user"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully! Please login again.')
            logout(request)
            return redirect('login')
    else:
        form = ChangePasswordForm(request.user)
    
    return render(request, 'auth/change_password.html', {'form': form})


@login_required(login_url='login')
def reset_password(request):
    """Reset employee password - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to reset passwords.')
        return redirect('dashboard')
    
    reset_info = None
    
    if request.method == 'POST':
        form = PasswordResetSelectionForm(request.POST)
        if form.is_valid():
            employee = form.cleaned_data['employee']
            user = employee.user
            
            if user:
                # Generate a temporary password (8 characters)
                temp_password = get_random_string(length=8, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                user.set_password(temp_password)
                user.save()
                
                # Create reset info message in standard format
                reset_info = {
                    'employee_name': employee.name,
                    'employee_id': employee.employee_id,
                    'username': user.username,
                    'temp_password': temp_password,
                    'message': f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASSWORD RESET CONFIRMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Employee: {employee.name}
Employee ID: {employee.employee_id}
Username: {user.username}

TEMPORARY PASSWORD: {temp_password}

⚠️  IMPORTANT INSTRUCTIONS:
1. Share this temporary password with the employee
2. Employee must change password on first login
3. This temporary password is valid for immediate use only
4. For security, temporary password should not be stored or reused

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                }
                
                messages.success(request, f'Password reset successful for {employee.name}. See details below.')
            else:
                messages.error(request, 'Employee does not have a user account linked.')
    else:
        form = PasswordResetSelectionForm()
    
    context = {
        'form': form,
        'reset_info': reset_info,
    }
    return render(request, 'auth/reset_password.html', context)


# ============ DASHBOARD ============

@login_required(login_url='login')
def dashboard(request):
    """Main dashboard - Shows different data based on user role"""
    admin = is_admin(request.user)
    
    if admin:
        # Admins see all employees and all compoffs
        total_employees = Employee.objects.count()
        total_compoffs = CompOff.objects.count()
        pending_compoffs = CompOff.objects.filter(status='PENDING').count()
    else:
        # Non-admins see only their own data
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'You do not have an associated employee record.')
            return redirect('compoff_list')
        
        total_employees = 1  # Just themselves
        total_compoffs = CompOff.objects.filter(employee=employee).count()
        pending_compoffs = CompOff.objects.filter(employee=employee, status='PENDING').count()
    
    context = {
        'total_employees': total_employees,
        'total_compoffs': total_compoffs,
        'pending_compoffs': pending_compoffs,
        'is_admin': admin,
    }
    return render(request, 'dashboard.html', context)


# ============ EMPLOYEE MANAGEMENT ============

@login_required(login_url='login')
def employee_list(request):
    """List all employees - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    employees = Employee.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(project__project__icontains=search_query) |
            Q(project__department_name__icontains=search_query) |
            Q(project__manager__icontains=search_query) |
            Q(location__name__icontains=search_query)
        )
    
    context = {
        'employees': employees,
        'search_query': search_query,
    }
    return render(request, 'timesheet/employee_list.html', context)


@login_required(login_url='login')
def employee_add(request):
    """Add new employee - Admin only"""
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to employee_add by user: {request.user.username}")
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            logger.info(f"New employee created: {employee.name} (ID: {employee.employee_id}) by user: {request.user.username}")
            messages.success(request, 'Employee added successfully!')
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    
    return render(request, 'timesheet/employee_form.html', {'form': form, 'title': 'Add Employee'})


@login_required(login_url='login')
def employee_edit(request, pk):
    """Edit employee - Admin only"""
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to employee_edit by user: {request.user.username}")
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            logger.info(f"Employee updated: {employee.name} (ID: {employee.employee_id}) by user: {request.user.username}")
            messages.success(request, 'Employee updated successfully!')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=employee)
    
    return render(request, 'timesheet/employee_form.html', {'form': form, 'title': 'Edit Employee'})


@login_required(login_url='login')
@require_http_methods(["POST"])
def employee_delete(request, pk):
    """Delete employee - Admin only"""
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to employee_delete by user: {request.user.username}")
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    employee = get_object_or_404(Employee, pk=pk)
    name = employee.name
    employee_id = employee.employee_id
    employee.delete()
    logger.warning(f"Employee deleted: {name} (ID: {employee_id}) by user: {request.user.username}")
    messages.success(request, f'Employee {name} deleted successfully!')
    return redirect('employee_list')


# ============ Comp-Off MANAGEMENT ============

@login_required(login_url='login')
def compoff_list(request):
    """List compoffs - employees see only their own, admins see all"""
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'compoff_list')

    compoffs = CompOff.objects.select_related('employee').order_by('-created_date')
    admin = is_admin(request.user)
    current_employee = None
    
    # If user is not admin, filter to their own CompOffs only
    if not admin:
        current_employee = get_user_employee(request.user)
        if not current_employee:
            messages.error(request, 'You do not have an associated employee record.')
            return redirect('dashboard')
        compoffs = compoffs.filter(employee=current_employee)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        compoffs = compoffs.filter(status=status)
    
    # Filter by employee (admin only)
    employee_id = request.GET.get('employee', '')
    if employee_id and admin:
        compoffs = compoffs.filter(employee_id=employee_id)
    
    # For non-admins, pass only their own employee; for admins pass all
    if admin:
        employees = Employee.objects.all()
    else:
        employees = [current_employee]  # Pass only current employee for filter display
    
    context = {
        'compoffs': compoffs,
        'employees': employees,
        'selected_status': status,
        'selected_employee': employee_id,
        'is_admin': admin,
    }
    return render(request, 'timesheet/compoff_list.html', context)


@login_required(login_url='login')
def compoff_add(request):
    """Add new compoff"""
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'compoff_add')

    # Non-admins can only add Comp-Off for themselves
    if not is_admin(request.user):
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'You do not have an associated employee record.')
            return redirect('dashboard')
    
    if request.method == 'POST':
        form = CompOffForm(request.POST, user=request.user, is_admin=is_admin(request.user), employee=employee if not is_admin(request.user) else None)
        if form.is_valid():
            compoff = form.save(commit=False)
            
            # If not admin, force the employee to be the logged-in user's employee
            if not is_admin(request.user):
                compoff.employee = employee
            
            compoff.save()
            messages.success(request, 'Comp-Off added successfully!')
            return redirect('compoff_list')
    else:
        form = CompOffForm(user=request.user, is_admin=is_admin(request.user), employee=employee if not is_admin(request.user) else None)
        # If not admin, pre-select their own employee record
        if not is_admin(request.user):
            form.fields['employee'].initial = employee
    
    return render(request, 'timesheet/compoff_form.html', {'form': form, 'title': 'Add CompOff'})


@login_required(login_url='login')
def compoff_edit(request, pk):
    """Edit Comp-Off - employees can only edit their own"""
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'compoff_edit')

    compoff = get_object_or_404(CompOff, pk=pk)
    
    # Check permission: allow if admin or if it's the user's own CompOff
    if not is_admin(request.user):
        employee = get_user_employee(request.user)
        if not employee or compoff.employee != employee:
            messages.error(request, 'You do not have permission to edit this CompOff.')
            return redirect('compoff_list')
    
    if request.method == 'POST':
        form = CompOffForm(request.POST, instance=compoff, user=request.user, is_admin=is_admin(request.user), employee=employee if not is_admin(request.user) else None)
        if form.is_valid():
            compoff = form.save(commit=False)
            
            # Prevent non-admins from changing the employee
            if not is_admin(request.user):
                compoff.employee = employee
            
            compoff.save()
            messages.success(request, 'Comp-Off updated successfully!')
            return redirect('compoff_list')
    else:
        form = CompOffForm(instance=compoff, user=request.user, is_admin=is_admin(request.user), employee=employee if not is_admin(request.user) else None)
    
    return render(request, 'timesheet/compoff_form.html', {'form': form, 'title': 'Edit CompOff'})


@login_required(login_url='login')
@require_http_methods(["POST"])
def compoff_delete(request, pk):
    """Delete Comp-Off - employees can only delete their own"""
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'compoff_delete')

    compoff = get_object_or_404(CompOff, pk=pk)
    
    # Check permission: allow if admin or if it's the user's own CompOff
    if not is_admin(request.user):
        employee = get_user_employee(request.user)
        if not employee or compoff.employee != employee:
            messages.error(request, 'You do not have permission to delete this CompOff.')
            return redirect('compoff_list')
    
    compoff.delete()
    messages.success(request, 'Comp-Off deleted successfully!')
    return redirect('compoff_list')


# ============ REPORTS ============

@login_required(login_url='login')
def employee_report(request, pk):
    """Employee detailed report with all compoffs - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    employee = get_object_or_404(Employee, pk=pk)
    compoffs = CompOff.objects.filter(employee=employee).order_by('-created_date')
    
    context = {
        'employee': employee,
        'compoffs': compoffs,
        'total_compoffs': compoffs.count(),
        'pending_compoffs': compoffs.filter(status='PENDING').count(),
        'taken_compoffs': compoffs.filter(status='TAKEN').count(),
    }
    return render(request, 'timesheet/employee_report.html', context)


@login_required(login_url='login')
def client_reporting(request):
    """Generate and optionally email a client reporting timesheet."""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    managers = Project.objects.values_list('manager', flat=True).exclude(manager__exact='').distinct().order_by('manager')
    if request.method == 'POST':
        selected_manager = request.POST.get('manager', '').strip()
        start_date_input = request.POST.get('start_date', '').strip()
        end_date_input = request.POST.get('end_date', '').strip()
    else:
        selected_manager = request.GET.get('manager', '').strip()
        start_date_input = request.GET.get('start_date', '').strip()
        end_date_input = request.GET.get('end_date', '').strip()

    employees = []
    report_rows = []
    employee_totals = []
    report_total_hours = 0
    accrual_pending_hours_list = []
    accrual_days_list = []
    accrual_adjusted_list = []
    selected_manager_email = None

    if selected_manager:
        employees = Employee.objects.filter(project__manager=selected_manager, is_active=True).select_related('project').order_by('name')

        if start_date_input and end_date_input:
            try:
                start_date = datetime.strptime(start_date_input, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_input, '%Y-%m-%d').date()
            except ValueError:
                start_date = None
                end_date = None
                messages.error(request, 'Invalid date format. Use YYYY-MM-DD.')

            if start_date and end_date:
                if end_date < start_date:
                    messages.error(request, 'End date cannot be before start date.')
                elif employees:
                    entries = TimesheetEntry.objects.filter(
                        employee__in=employees,
                        date__range=(start_date, end_date),
                        status='SUBMITTED'
                    )

                    entry_map = {}

                    for entry in entries:
                        hours = float(entry.hours)
                        key = (entry.employee_id, entry.date)
                        entry_map[key] = entry_map.get(key, 0) + hours

                    # Get all comp-offs taken in the date range for highlighting
                    taken_compoffs = list(CompOff.objects.filter(
                        employee__in=employees,
                        status='TAKEN',
                        compoff_date__range=(start_date, end_date)
                    ))
                    compoff_map = {}
                    for compoff in taken_compoffs:
                        key = (compoff.employee_id, compoff.compoff_date)
                        compoff_map[key] = True

                    compoff_working_dates = [
                        compoff.working_date for compoff in taken_compoffs if compoff.working_date
                    ]
                    compoff_source_hours = {}
                    if compoff_working_dates:
                        compoff_source_entries = TimesheetEntry.objects.filter(
                            employee__in=employees,
                            date__in=compoff_working_dates,
                            status='SUBMITTED'
                        )
                        for entry in compoff_source_entries:
                            key = (entry.employee_id, entry.date)
                            compoff_source_hours[key] = compoff_source_hours.get(key, 0) + float(entry.hours)

                    compoff_hours_map = {}
                    for compoff in taken_compoffs:
                        if not compoff.compoff_date:
                            continue
                        source_hours = compoff_source_hours.get((compoff.employee_id, compoff.working_date), 8)
                        compoff_hours_map[(compoff.employee_id, compoff.compoff_date)] = source_hours

                    totals_by_employee = {employee.id: 0 for employee in employees}

                    current_date = start_date
                    while current_date <= end_date:
                        row_date_types = [
                            get_date_type(current_date, employee=employee)
                            for employee in employees
                        ]
                        row_hours = []
                        row_compoff_taken = []
                        for employee in employees:
                            date_type = get_date_type(current_date, employee=employee)
                            submitted_hours = entry_map.get((employee.id, current_date))
                            took_compoff = (employee.id, current_date) in compoff_map

                            if date_type:
                                display_hours = ''
                            elif took_compoff:
                                display_hours = compoff_hours_map.get((employee.id, current_date), '')
                            else:
                                display_hours = submitted_hours if submitted_hours is not None else ''

                            if display_hours != '':
                                totals_by_employee[employee.id] += float(display_hours)

                            row_hours.append(display_hours)
                            row_compoff_taken.append(took_compoff)

                        report_rows.append({
                            'date': current_date,
                            'date_type': row_date_types[0] if row_date_types else '',
                            'is_holiday_or_weekend': any(bool(date_type) for date_type in row_date_types),
                            'hours': row_hours,
                            'compoff_taken': row_compoff_taken
                        })
                        current_date += timedelta(days=1)

                    employee_totals = [
                        totals_by_employee.get(employee.id, 0)
                        for employee in employees
                    ]
                    report_total_hours = sum(employee_totals)

                    # Calculate accrual data for each employee
                    accrual_pending_hours_list = []
                    accrual_days_list = []
                    accrual_adjusted_list = []

                    for employee in employees:
                        # Accrual Pending in Hours: count of pending CompOffs * 8 (assuming 8 hours per day)
                        pending_compoffs = CompOff.objects.filter(employee=employee, status='PENDING')
                        accrual_pending_hours = pending_compoffs.count() * 8
                        accrual_pending_hours_list.append(accrual_pending_hours)

                        # Accrual Days: dates of pending compoffs (working_date)
                        accrual_days = [c.working_date.strftime('%d-%b-%Y') for c in pending_compoffs if c.working_date]
                        accrual_days_list.append(', '.join(accrual_days) if accrual_days else '')

                        # Accrual Adjusted: Comp-Off dates for 'TAKEN' status within date range
                        taken_compoffs = CompOff.objects.filter(
                            employee=employee,
                            status='TAKEN',
                            compoff_date__range=(start_date, end_date)
                        )
                        accrual_adjusted = [c.compoff_date.strftime('%d-%b-%Y') for c in taken_compoffs if c.compoff_date]
                        accrual_adjusted_list.append(', '.join(accrual_adjusted) if accrual_adjusted else '')
                else:
                    messages.warning(request, 'No employees found for the selected manager.')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'email_report':
            if not selected_manager or not start_date_input or not end_date_input:
                messages.error(request, 'Please select a manager and date range before emailing the report.')
            elif not employees:
                messages.error(request, 'No employees available for the selected manager.')
            elif not report_rows:
                messages.error(request, 'Report has no rows. Please check the date range.')
            else:
                recipients = get_report_email_recipients()
                if not recipients:
                    messages.error(request, 'No valid email recipients found for the selected manager or employees.')
                else:
                    subject = f'Timesheet Report - {selected_manager} ({start_date_input} to {end_date_input})'
                    email_context = {
                        'approver_manager': selected_manager,
                        'employees': employees,
                        'report_rows': report_rows,
                        'employee_totals': employee_totals,
                        'report_total_hours': report_total_hours,
                        'accrual_pending_hours_list': accrual_pending_hours_list,
                        'accrual_days_list': accrual_days_list,
                        'accrual_adjusted_list': accrual_adjusted_list,
                        'start_date': start_date_input,
                        'end_date': end_date_input,
                    }
                    html_message = render_to_string('managers/client_reporting_email.html', email_context)
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'noreply@example.com')
                    send_html_email_async(
                        subject,
                        html_message,
                        from_email,
                        recipients,
                        f"Timesheet report emailed successfully to {len(recipients)} recipients by user: {request.user.username}",
                        f"Failed to send timesheet email for user {request.user.username}"
                    )
                    messages.success(request, 'Timesheet report email has been queued and will be sent shortly.')
                    if 'console' in settings.EMAIL_BACKEND:
                        messages.info(request, 'Email sending was queued for the console backend (development mode).')

    context = {
        'managers': managers,
        'selected_manager': selected_manager,
        'start_date': start_date_input,
        'end_date': end_date_input,
        'employees': employees,
        'report_rows': report_rows,
        'employee_totals': employee_totals,
        'report_total_hours': report_total_hours,
        'accrual_pending_hours_list': accrual_pending_hours_list,
        'accrual_days_list': accrual_days_list,
        'accrual_adjusted_list': accrual_adjusted_list,
    }
    return render(request, 'managers/client_reporting.html', context)


@login_required(login_url='login')
def accrual_summary(request):
    """Display accrual summary data (Pending Hours, Days, Adjusted) for employees under a manager."""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    managers = Project.objects.values_list('manager', flat=True).exclude(manager__exact='').distinct().order_by('manager')
    
    if request.method == 'POST':
        selected_manager = request.POST.get('manager', '').strip()
        start_date_input = request.POST.get('start_date', '').strip()
        end_date_input = request.POST.get('end_date', '').strip()
    else:
        selected_manager = request.GET.get('manager', '').strip()
        start_date_input = request.GET.get('start_date', '').strip()
        end_date_input = request.GET.get('end_date', '').strip()

    accrual_data = []
    start_date = None
    end_date = None
    employees = []

    if selected_manager:
        employees = Employee.objects.filter(project__manager=selected_manager, is_active=True).select_related('project').order_by('name')

        if start_date_input and end_date_input:
            try:
                start_date = datetime.strptime(start_date_input, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_input, '%Y-%m-%d').date()
            except ValueError:
                start_date = None
                end_date = None
                messages.error(request, 'Invalid date format. Use YYYY-MM-DD.')

            if start_date and end_date:
                if end_date < start_date:
                    messages.error(request, 'End date cannot be before start date.')
                elif employees:
                    # Gather accrual data for each employee
                    for employee in employees:
                        # Accrual Pending in Hours: count of pending CompOffs * 8 (assuming 8 hours per day)
                        pending_compoffs = CompOff.objects.filter(employee=employee, status='PENDING')
                        accrual_pending_hours = pending_compoffs.count() * 8

                        # Accrual Days: dates of pending compoffs (working_date)
                        accrual_days = [c.working_date.strftime('%d-%b-%Y') for c in pending_compoffs if c.working_date]
                        accrual_days_str = ', '.join(accrual_days) if accrual_days else 'N/A'

                        # Accrual Adjusted: Comp-Off dates for 'TAKEN' status within date range
                        taken_compoffs = CompOff.objects.filter(
                            employee=employee,
                            status='TAKEN',
                            compoff_date__range=(start_date, end_date)
                        ).order_by('compoff_date', 'working_date')
                        work_dates = [
                            c.working_date.strftime('%d-%b-%Y')
                            for c in taken_compoffs
                            if c.working_date
                        ]
                        compoff_dates = [
                            c.compoff_date.strftime('%d-%b-%Y')
                            for c in taken_compoffs
                            if c.compoff_date
                        ]
                        if work_dates and compoff_dates:
                            accrual_adjusted_str = (
                                f"Worked on {', '.join(work_dates)} adjusted against PTO on "
                                f"{', '.join(compoff_dates)}"
                            )
                        else:
                            accrual_adjusted_str = 'N/A'

                        accrual_data.append({
                            'employee': employee.name,
                            'pending_hours': accrual_pending_hours,
                            'pending_days': accrual_days_str,
                            'adjusted_dates': accrual_adjusted_str,
                        })
                else:
                    messages.warning(request, 'No employees found for the selected manager.')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'email_report':
            if not selected_manager or not start_date_input or not end_date_input:
                messages.error(request, 'Please select a manager and date range before emailing the report.')
            elif not employees:
                messages.error(request, 'No employees available for the selected manager.')
            elif not accrual_data:
                messages.error(request, 'No accrual data available. Please check the date range.')
            else:
                recipients = get_report_email_recipients()
                if not recipients:
                    messages.error(request, 'No valid email recipients found for the selected manager or employees.')
                else:
                    subject = f'Accrual Summary Report - {selected_manager} ({start_date_input} to {end_date_input})'
                    email_context = {
                        'manager_name': selected_manager,
                        'accrual_data': accrual_data,
                        'start_date': start_date_input,
                        'end_date': end_date_input,
                    }
                    html_message = render_to_string('managers/accrual_summary_email.html', email_context)
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'noreply@example.com')
                    send_html_email_async(
                        subject,
                        html_message,
                        from_email,
                        recipients,
                        f"Accrual summary report emailed successfully to {len(recipients)} recipients by user: {request.user.username}",
                        f"Failed to send accrual summary email for user {request.user.username}"
                    )
                    messages.success(request, 'Accrual summary report email has been queued and will be sent shortly.')
                    if 'console' in settings.EMAIL_BACKEND:
                        messages.info(request, 'Email sending was queued for the console backend (development mode).')

    context = {
        'managers': managers,
        'selected_manager': selected_manager,
        'start_date': start_date_input,
        'end_date': end_date_input,
        'accrual_data': accrual_data,
    }
    return render(request, 'managers/accrual_summary.html', context)


# ============ TIMESHEET DATA VIEWS ============

@login_required(login_url='login')
def timesheet_data_view(request):
    """View all timesheet and attendance data on one page - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    from .models import TimesheetImportLog
    
    # Get all unique import logs with dates and notes for dropdown
    import_logs = TimesheetImportLog.objects.values('import_date', 'notes').distinct().order_by('-import_date')
    selected_import_date = request.GET.get('import_date', '')
    
    # Base querysets
    ts_summaries = TimesheetSummary.objects.all().order_by('team_member')
    ts_details = TimesheetDetails.objects.all().order_by('-date', 'team_member')
    att_summaries = AttendanceSummary.objects.all().order_by('team_member')
    att_details = AttendanceDetails.objects.all().order_by('-date', 'team_member')
    
    # Apply import_date filter if selected
    if selected_import_date:
        ts_summaries = ts_summaries.filter(import_date=selected_import_date)
        ts_details = ts_details.filter(import_date=selected_import_date)
        att_summaries = att_summaries.filter(import_date=selected_import_date)
        att_details = att_details.filter(import_date=selected_import_date)
    
    ts_summary_total_hours = ts_summaries.aggregate(Sum('total_hours'))['total_hours__sum'] or 0
    ts_details_total_hours = ts_details.aggregate(Sum('time_logged'))['time_logged__sum'] or 0
    
    # Search functionality for timesheet summary
    ts_search = request.GET.get('ts_search', '')
    if ts_search:
        ts_summaries = ts_summaries.filter(
            Q(team_member__icontains=ts_search) |
            Q(project__icontains=ts_search) |
            Q(email_id__icontains=ts_search)
        )
    
    # Search and date filter for timesheet details
    ts_detail_search = request.GET.get('ts_detail_search', '')
    ts_date = request.GET.get('ts_date', '')
    if ts_detail_search:
        ts_details = ts_details.filter(
            Q(team_member__icontains=ts_detail_search) |
            Q(project__icontains=ts_detail_search) |
            Q(email_id__icontains=ts_detail_search)
        )
    if ts_date:
        ts_details = ts_details.filter(date=ts_date)
    
    # Search functionality for attendance summary
    att_search = request.GET.get('att_search', '')
    if att_search:
        att_summaries = att_summaries.filter(
            Q(team_member__icontains=att_search) |
            Q(email_id__icontains=att_search)
        )
    
    # Search and date filter for attendance details
    att_detail_search = request.GET.get('att_detail_search', '')
    att_date = request.GET.get('att_date', '')
    if att_detail_search:
        att_details = att_details.filter(
            Q(team_member__icontains=att_detail_search) |
            Q(email_id__icontains=att_detail_search)
        )
    if att_date:
        att_details = att_details.filter(date=att_date)
    
    context = {
        'import_logs': import_logs,
        'selected_import_date': selected_import_date,
        
        'ts_summaries': ts_summaries,
        'ts_summary_total_hours': ts_summary_total_hours,
        'ts_summary_count': ts_summaries.count(),
        'ts_search': ts_search,
        
        'ts_details': ts_details,
        'ts_details_total_hours': ts_details_total_hours,
        'ts_details_count': ts_details.count(),
        'ts_detail_search': ts_detail_search,
        'ts_date': ts_date,
        
        'att_summaries': att_summaries,
        'att_summary_count': att_summaries.count(),
        'att_search': att_search,
        
        'att_details': att_details,
        'att_details_count': att_details.count(),
        'att_detail_search': att_detail_search,
        'att_date': att_date,
    }
    return render(request, 'timesheet/timesheet_data.html', context)


@login_required(login_url='login')
def timesheet_summary_view(request):
    """View timesheet summary data"""
    summaries = TimesheetSummary.objects.all().order_by('team_member')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        summaries = summaries.filter(
            Q(team_member__icontains=search_query) |
            Q(project__icontains=search_query) |
            Q(email_id__icontains=search_query)
        )
    
    # Statistics
    total_hours = summaries.aggregate(Sum('total_hours'))['total_hours__sum'] or 0
    
    context = {
        'summaries': summaries,
        'search_query': search_query,
        'total_hours': total_hours,
        'count': summaries.count(),
    }
    return render(request, 'timesheet/timesheet_summary.html', context)


@login_required(login_url='login')
def timesheet_details_view(request):
    """View timesheet details data"""
    details = TimesheetDetails.objects.all().order_by('-date', 'team_member')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        details = details.filter(
            Q(team_member__icontains=search_query) |
            Q(project__icontains=search_query) |
            Q(email_id__icontains=search_query)
        )
    
    # Date filter
    date_filter = request.GET.get('date', '')
    if date_filter:
        details = details.filter(date=date_filter)
    
    # Statistics
    total_hours = details.aggregate(Sum('time_logged'))['time_logged__sum'] or 0
    
    context = {
        'details': details,
        'search_query': search_query,
        'date_filter': date_filter,
        'total_hours': total_hours,
        'count': details.count(),
    }
    return render(request, 'timesheet/timesheet_details.html', context)


@login_required(login_url='login')
def attendance_summary_view(request):
    """View attendance summary data"""
    summaries = AttendanceSummary.objects.all().order_by('team_member')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        summaries = summaries.filter(
            Q(team_member__icontains=search_query) |
            Q(email_id__icontains=search_query)
        )
    
    context = {
        'summaries': summaries,
        'search_query': search_query,
        'count': summaries.count(),
    }
    return render(request, 'timesheet/attendance_summary.html', context)


@login_required(login_url='login')
def attendance_details_view(request):
    """View attendance details data"""
    details = AttendanceDetails.objects.all().order_by('-date', 'team_member')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        details = details.filter(
            Q(team_member__icontains=search_query) |
            Q(email_id__icontains=search_query)
        )
    
    # Date filter
    date_filter = request.GET.get('date', '')
    if date_filter:
        details = details.filter(date=date_filter)
    
    context = {
        'details': details,
        'search_query': search_query,
        'date_filter': date_filter,
        'count': details.count(),
    }
    return render(request, 'timesheet/attendance_details.html', context)


# ============ TIMESHEET ENTRY MANAGEMENT ============

@login_required(login_url='login')
def timesheet_entry_list(request):
    """List timesheet entries for logged-in employee for selected month
    
    Supports partial month submission - allows editing of DRAFT entries
    even if some entries are already SUBMITTED.
    
    For admin users, shows dropdown to select employee.
    """
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'timesheet_entry_list')

    # Get selected month/year from request, default to current month
    from datetime import datetime, date
    selected_month = request.GET.get('month', '')
    
    if selected_month:
        # Parse month in format YYYY-MM
        try:
            year, month = map(int, selected_month.split('-'))
            selected_date = date(year, month, 1)
        except (ValueError, IndexError):
            selected_date = date.today().replace(day=1)
    else:
        selected_date = date.today().replace(day=1)
    
    employee = None
    all_employees = None
    
    if is_admin(request.user):
        # Admin user - can view any employee's timesheet
        all_employees = Employee.objects.all().order_by('name')
        selected_employee_id = request.GET.get('employee', '')
        if selected_employee_id:
            try:
                employee = Employee.objects.get(pk=selected_employee_id)
            except Employee.DoesNotExist:
                employee = None
    else:
        # Regular user - only their own timesheet
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'You do not have an associated employee record.')
            return redirect('dashboard')
    
    entries = []
    submitted_entries = False
    draft_entries = False
    all_submitted = False
    total_hours = 0
    submitted_hours = 0
    holiday_dates = []

    if employee:
        # Get all entries for this month
        from calendar import monthrange
        days_in_month = monthrange(selected_date.year, selected_date.month)[1]
        month_end = date(selected_date.year, selected_date.month, days_in_month)
        
        entries = TimesheetEntry.objects.filter(
            employee=employee,
            date__gte=selected_date,
            date__lte=month_end
        ).order_by('date', 'project')
        
        # Get all weekend and holiday dates for this month for highlighting
        current = selected_date
        while current <= month_end:
            if get_date_type(current, employee=employee):  # If there's a date_type (holiday or weekend)
                holiday_dates.append(current)
            current += timedelta(days=1)
        
        # Check if entire month is submitted or if there are still DRAFT entries
        submitted_entries = entries.filter(status='SUBMITTED').exists()
        draft_entries = entries.filter(status='DRAFT').exists()
        
        # all_submitted is TRUE only if:
        # 1. There are existing entries AND
        # 2. All existing entries are SUBMITTED (no DRAFT entries) AND
        # 3. All working days of the month have SUBMITTED entries (not just some days)
        all_submitted = False
        if submitted_entries and not draft_entries:
            # All existing entries are submitted, check if entire month is covered
            all_days_covered = True
            current = selected_date
            while current <= month_end:
                # Check if it's a working day (Monday=0 to Friday=4, not a holiday)
                if current.weekday() < 5:
                    # Check if it's a holiday (PUBLIC_HOLIDAY or SPECIAL_HOLIDAY)
                    if not is_holiday_date(current, employee=employee, exclude_special=False):
                        # Check if employee has a SUBMITTED entry for this date
                        has_submitted_entry = TimesheetEntry.objects.filter(
                            employee=employee,
                            date=current,
                            status='SUBMITTED'
                        ).exists()
                        
                        if not has_submitted_entry:
                            all_days_covered = False
                            break
                current += timedelta(days=1)
            
            all_submitted = all_days_covered
        
        # Calculate total hours for the month
        total_hours = entries.aggregate(Sum('hours'))['hours__sum'] or 0
        
        # Calculate submitted hours
        submitted_hours = entries.filter(status='SUBMITTED').aggregate(Sum('hours'))['hours__sum'] or 0
    
    available_projects = get_employee_project_choices(employee)

    context = {
        'employee': employee,
        'all_employees': all_employees,
        'available_projects': available_projects,
        'selected_employee_id': request.GET.get('employee', ''),
        'entries': entries,
        'selected_month': selected_month or selected_date.strftime('%Y-%m'),
        'selected_date': selected_date,
        'month_display': selected_date.strftime('%B %Y'),
        'total_hours': total_hours,
        'submitted_hours': submitted_hours,
        'submitted': submitted_entries,  # True if ANY entries are submitted
        'all_submitted': all_submitted,  # True only if ALL entries are submitted
        'has_draft': draft_entries,  # True if there are DRAFT entries
        'is_admin': is_admin(request.user),
        'holiday_dates': holiday_dates,
    }
    return render(request, 'timesheet/timesheet_entry_list.html', context)


@login_required(login_url='login')
def timesheet_entry_add(request):
    """Add new timesheet entry
    
    Allows regular employees to add their own entries and admins to add entries for any employee.
    """
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'timesheet_entry_add')

    # Determine which employee to add entry for
    if is_admin(request.user):
        # Admin can select which employee to add entry for
        selected_employee_id = request.GET.get('employee', '')
        if not selected_employee_id:
            messages.error(request, 'Admin must select an employee.')
            return redirect('timesheet_entry_list')
        try:
            employee = Employee.objects.get(pk=selected_employee_id)
        except Employee.DoesNotExist:
            messages.error(request, 'Selected employee not found.')
            return redirect('timesheet_entry_list')
    else:
        # Regular user can only add their own entries
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'You do not have an associated employee record.')
            return redirect('dashboard')
    
    # Get the month parameter from query string
    from datetime import date
    selected_month = request.GET.get('month', '')
    
    if request.method == 'POST':
        form = TimesheetEntryForm(request.POST, employee=employee)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.employee = employee
            entry.save()
            
            messages.success(request, 'Timesheet entry added successfully!')
            # Redirect to the same month the user was viewing
            if selected_month:
                redirect_url = reverse('timesheet_entry_list') + f'?month={selected_month}'
                if is_admin(request.user):
                    redirect_url += f'&employee={employee.pk}'
                return redirect(redirect_url)
            return redirect('timesheet_entry_list')
    else:
        form = TimesheetEntryForm(employee=employee)
    
    context = {
        'form': form,
        'employee': employee,
        'available_projects': get_employee_project_choices(employee),
        'selected_month': selected_month,
    }
    return render(request, 'timesheet/timesheet_entry_form.html', context)


@login_required(login_url='login')
def timesheet_entry_edit(request, pk):
    """Edit existing timesheet entry
    
    Allows regular employees to edit their own entries and admins to edit any employee's entries.
    """
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'timesheet_entry_edit')

    if is_admin(request.user):
        # Admin can edit any entry
        try:
            entry = TimesheetEntry.objects.get(pk=pk)
        except TimesheetEntry.DoesNotExist:
            messages.error(request, 'Entry not found.')
            return redirect('timesheet_entry_list')
        employee = entry.employee
    else:
        # Regular user can only edit their own entries
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'You do not have an associated employee record.')
            return redirect('dashboard')
        
        try:
            entry = TimesheetEntry.objects.get(pk=pk, employee=employee)
        except TimesheetEntry.DoesNotExist:
            messages.error(request, 'Entry not found.')
            return redirect('timesheet_entry_list')
    
    # Check if submitted
    if entry.status == 'SUBMITTED':
        messages.error(request, 'Cannot edit submitted timesheet entries.')
        return redirect('timesheet_entry_list')
    
    # Get the month parameter from query string
    from datetime import date
    selected_month = request.GET.get('month', '')
    
    if request.method == 'POST':
        form = TimesheetEntryForm(request.POST, instance=entry, employee=employee)
        if form.is_valid():
            updated_entry = form.save()
            
            messages.success(request, 'Timesheet entry updated successfully!')
            # Redirect to the same month the user was viewing
            if selected_month:
                redirect_url = reverse('timesheet_entry_list') + f'?month={selected_month}'
                if is_admin(request.user):
                    redirect_url += f'&employee={employee.pk}'
                return redirect(redirect_url)
            return redirect('timesheet_entry_list')
    else:
        form = TimesheetEntryForm(instance=entry, employee=employee)
    
    context = {
        'form': form,
        'employee': employee,
        'entry': entry,
        'available_projects': get_employee_project_choices(employee),
        'selected_month': selected_month,
    }
    return render(request, 'timesheet/timesheet_entry_form.html', context)


@login_required(login_url='login')
@require_http_methods(["DELETE"])
def timesheet_entry_delete(request, pk):
    """Delete timesheet entry via AJAX
    
    Only allows deletion of DRAFT (unsubmitted) entries.
    Admins can delete any employee's entry; regular users can only delete their own.
    CompOffs are only created at submission time, so no cleanup needed here.
    """
    if not can_access_employee_features(request.user):
        return JsonResponse(
            {'success': False, 'message': 'You do not have permission to access this page.'},
            status=403
        )

    if is_admin(request.user):
        # Admin can delete any entry
        try:
            entry = TimesheetEntry.objects.get(pk=pk)
        except TimesheetEntry.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Entry not found.'}, status=404)
    else:
        # Regular user can only delete their own entries
        employee = get_user_employee(request.user)
        if not employee:
            return JsonResponse({'success': False, 'message': 'No employee record found.'}, status=400)
        
        try:
            entry = TimesheetEntry.objects.get(pk=pk, employee=employee)
        except TimesheetEntry.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Entry not found.'}, status=404)
    
    # Check if submitted
    if entry.status == 'SUBMITTED':
        return JsonResponse({'success': False, 'message': 'Cannot delete submitted entries.'}, status=400)
    
    date_str = entry.date.strftime('%Y-%m-%d')
    
    # Delete the timesheet entry
    entry.delete()
    
    return JsonResponse({'success': True, 'message': f'Entry for {date_str} deleted successfully!'})


@login_required(login_url='login')
@require_http_methods(["POST"])
def timesheet_entry_submit(request):
    """Submit timesheet entries for a date range. Supports partial month submission.
    
    POST Parameters:
    - month: YYYY-MM format
    - submit_all: 'true' for full month, else from_date/to_date required
    - from_date, to_date: YYYY-MM-DD for partial submission
    - employee (optional): For admin users, which employee's timesheet to submit
    """
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'timesheet_entry_submit')

    # Determine which employee's timesheet to submit
    if is_admin(request.user):
        # Admin can select which employee to submit for
        selected_employee_id = request.POST.get('employee', '')
        if not selected_employee_id:
            messages.error(request, 'Admin must select an employee.')
            return redirect('timesheet_entry_list')
        try:
            employee = Employee.objects.get(pk=selected_employee_id)
        except Employee.DoesNotExist:
            messages.error(request, 'Selected employee not found.')
            return redirect('timesheet_entry_list')
    else:
        # Regular user can only submit their own timesheet
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'No employee record found.')
            return redirect('timesheet_entry_list')
    
    selected_month = request.POST.get('month', '')
    if not selected_month:
        messages.error(request, 'Month is required.')
        return redirect('timesheet_entry_list')
    
    try:
        year, month = map(int, selected_month.split('-'))
        from datetime import date
        from calendar import monthrange
        selected_date = date(year, month, 1)
        days_in_month = monthrange(year, month)[1]
        month_end = date(year, month, days_in_month)
    except (ValueError, IndexError):
        messages.error(request, 'Invalid month format.')
        return redirect('timesheet_entry_list')
    
    # Determine date range for submission
    submit_all = request.POST.get('submit_all') == 'true'
    
    if submit_all:
        # Submit all DRAFT entries for the entire month
        from_date = selected_date
        to_date = month_end
    else:
        # Partial submission - submit only entries within specified date range
        from_date_str = request.POST.get('from_date', '')
        to_date_str = request.POST.get('to_date', '')
        
        if not from_date_str or not to_date_str:
            messages.error(request, 'Date range is required for partial submission.')
            return redirect(reverse('timesheet_entry_list') + f'?month={selected_month}')
        
        try:
            from_date = date.fromisoformat(from_date_str)
            to_date = date.fromisoformat(to_date_str)
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect(reverse('timesheet_entry_list') + f'?month={selected_month}')
        
        # Validate dates are within the selected month
        if from_date < selected_date or to_date > month_end or from_date > to_date:
            messages.error(request, 'Dates must be within the selected month.')
            return redirect(reverse('timesheet_entry_list') + f'?month={selected_month}')
    
    # Update DRAFT entries within the date range to SUBMITTED
    entries = TimesheetEntry.objects.filter(
        employee=employee,
        date__gte=from_date,
        date__lte=to_date,
        status='DRAFT'
    ).order_by('date')
    
    if not entries.exists():
        messages.warning(request, 'No draft entries to submit for the selected date range.')
    else:
        # Convert QuerySet to list - forces full evaluation, gets all records into memory
        entries_list = list(entries)
        
        # Create detailed message about which entries are being submitted
        entry_dates = [entry.date.strftime('%a, %b %d') for entry in entries_list]
        
        # Mark all entries as submitted
        for entry in entries_list:
            entry.status = 'SUBMITTED'
        TimesheetEntry.objects.bulk_update(entries_list, ['status'], batch_size=100)
        count = len(entries_list)
        
        if submit_all:
            messages.success(request, f'{count} timesheet entries submitted successfully for {selected_date.strftime("%B %Y")}!')
        else:
            messages.success(request, f'{count} timesheet entries submitted successfully for {from_date.strftime("%b %d")} to {to_date.strftime("%b %d")}!')
        
        # Show which dates were submitted for debugging
        messages.info(request, f'Submitted entries for: {", ".join(entry_dates)}')
        
        # Create CompOffs for eligible submitted entries (weekend/holiday with 8+ hours)
        compoff_created = 0
        for entry in entries_list:
            if entry.status == 'SUBMITTED' and is_weekend_or_fixed_holiday(entry.date, employee=entry.employee) and entry.hours >= 8:
                # Avoid duplicates - check if Comp-Off already exists
                if not CompOff.objects.filter(employee=entry.employee, working_date=entry.date).exists():
                    CompOff.objects.create(
                        employee=entry.employee,
                        working_date=entry.date,
                        compoff_date=None,
                        status='PENDING',
                        notes=f'Auto-generated Comp-Off for working on weekend/holiday ({entry.date.strftime("%a, %b %d, %Y")})'
                    )
                    compoff_created += 1
                    logger.info(f"Comp-Off auto-created for {entry.employee.name} on {entry.date}")
        
        if compoff_created > 0:
            logger.info(f"{compoff_created} CompOff(s) created for working on weekend(s)/holiday(ies)")
            messages.info(request, f'{compoff_created} CompOff(s) created for working on weekend(s)/holiday(ies).')
        
    # Deduct PENDING CompOffs for missing weekdays once the range has submitted entries.
    # This keeps "leave as compoff" working even if the user re-submits a range where
    # the work days were already submitted earlier, while still avoiding deduction for
    # completely empty ranges.
    if has_submitted_entries_in_range(employee, from_date, to_date):
        compoff_deducted = auto_deduct_compoff_for_missing_weekdays_in_range(employee, from_date, to_date)
        if compoff_deducted > 0:
            logger.info(f"{compoff_deducted} pending CompOff(s) marked as taken for missing weekday(s)")
            messages.info(request, f'{compoff_deducted} pending CompOff(s) marked as taken for missing weekday(s).')
    
    # Redirect back with employee info if admin
    redirect_url = reverse('timesheet_entry_list') + f'?month={selected_month}'
    if is_admin(request.user):
        redirect_url += f'&employee={employee.pk}'
    return redirect(redirect_url)


@login_required(login_url='login')
@require_http_methods(["POST"])
def generate_timesheet_weekdays(request):
    """Generate timesheet entries for specified days between given dates
    
    By default generates entries for weekdays (Monday-Friday) only.
    Can optionally include Saturdays and/or Sundays.
    Admins can generate for any employee; regular users can only generate for themselves.
    """
    if not can_access_employee_features(request.user):
        return deny_employee_feature_access(request, 'generate_timesheet_weekdays')

    # Determine which employee to generate entries for
    if is_admin(request.user):
        # Admin can select which employee to generate for
        selected_employee_id = request.POST.get('employee', '')
        if not selected_employee_id:
            messages.error(request, 'Admin must select an employee.')
            return redirect('timesheet_entry_list')
        try:
            employee = Employee.objects.get(pk=selected_employee_id)
        except Employee.DoesNotExist:
            messages.error(request, 'Selected employee not found.')
            return redirect('timesheet_entry_list')
    else:
        # Regular user can only generate for themselves
        employee = get_user_employee(request.user)
        if not employee:
            messages.error(request, 'No employee record found.')
            return redirect('timesheet_entry_list')
    
    from_date = request.POST.get('from_date', '')
    to_date = request.POST.get('to_date', '')
    project = request.POST.get('project', '')
    hours_per_day = request.POST.get('hours_per_day', '8')
    comments = request.POST.get('comments', '')
    selected_month = request.POST.get('month', '')
    include_saturday = request.POST.get('include_saturday') == 'on'
    include_sunday = request.POST.get('include_sunday') == 'on'

    redirect_url = reverse('timesheet_entry_list')
    if selected_month:
        redirect_url += f'?month={selected_month}'
        if is_admin(request.user):
            redirect_url += f'&employee={employee.pk}'
    
    if not from_date or not to_date or not project:
        messages.error(request, 'From Date, To Date, and Project are required.')
        return redirect(redirect_url)
    
    try:
        from_dt = date.fromisoformat(from_date)
        to_dt = date.fromisoformat(to_date)
        hours = int(hours_per_day)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid date or hours format.')
        return redirect(redirect_url)
    
    if from_dt > to_dt:
        messages.error(request, 'From Date cannot be later than To Date.')
        return redirect(redirect_url)
    
    if hours < 0 or hours > 12:
        messages.error(request, 'Hours must be between 0 and 12.')
        return redirect(redirect_url)

    allowed_projects = {choice[0] for choice in get_employee_project_choices(employee)}
    if not allowed_projects:
        messages.error(request, 'No project is assigned to this employee.')
        return redirect(redirect_url)

    if project not in allowed_projects:
        messages.error(request, 'Please select a valid project assigned to this employee.')
        return redirect(redirect_url)
    
    # Determine which days to include (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
    days_to_include = list(range(5))  # Weekdays by default
    if include_saturday:
        days_to_include.append(5)
    if include_sunday:
        days_to_include.append(6)
    days_to_include.sort()
    
    # Generate entries for specified days, excluding PUBLIC_HOLIDAY and SPECIAL_HOLIDAY
    entries_created = 0
    entries_skipped = 0
    current = from_dt
    
    while current <= to_dt:
        weekday = current.weekday()
        if weekday in days_to_include:
            # Skip holidays (PUBLIC_HOLIDAY, SPECIAL_HOLIDAY)
            holiday_filters = Q(
                date=current,
                holiday_type__in=['PUBLIC_HOLIDAY', 'SPECIAL_HOLIDAY']
            ) & get_location_holiday_filter(get_employee_location_name(employee))
            is_blocked_holiday = Holiday.objects.filter(holiday_filters).exists()
            
            if not is_blocked_holiday:
                # Avoid duplicates
                if not TimesheetEntry.objects.filter(
                    employee=employee,
                    date=current,
                    project=project
                ).exists():
                    TimesheetEntry.objects.create(
                        employee=employee,
                        date=current,
                        project=project,
                        hours=hours,
                        comments=comments,
                        status='DRAFT'
                    )
                    entries_created += 1
                else:
                    entries_skipped += 1
        current += timedelta(days=1)
    
    if entries_created == 0:
        messages.warning(request, f'No new entries created. {entries_skipped} entries already exist for this project in the date range.')
    else:
        message = f'{entries_created} timesheet entries generated successfully!'
        if entries_skipped > 0:
            message += f' ({entries_skipped} entries already existed and were skipped.)'
        messages.success(request, message)
    
    # Redirect back with employee info if admin
    if selected_month:
        redirect_url = reverse('timesheet_entry_list') + f'?month={selected_month}'
        if is_admin(request.user):
            redirect_url += f'&employee={employee.pk}'
        return redirect(redirect_url)
    return redirect('timesheet_entry_list')


# ============ IMPORT TIMESHEET DATA ============

@login_required(login_url='login')
def import_timesheet_data(request):
    """Import timesheet data - Admin only"""
    if not is_admin(request.user):
        access_logger.warning(f"Unauthorized access attempt to import_timesheet_data by user: {request.user.username}")
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    import tempfile
    import os
    from .forms import TimesheetImportForm
    from .utils import import_timesheet_file
    from .models import TimesheetImportLog
    
    import_logger = logging.getLogger('timesheet.import')
    
    if request.method == 'POST':
        form = TimesheetImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Save uploaded file to temp location
            uploaded_file = request.FILES['file']
            import_date = form.cleaned_data['import_date']
            notes = form.cleaned_data.get('notes', '')
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            
            try:
                # Write file content
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file.close()
                
                # Import data
                try:
                    result = import_timesheet_file(temp_file.name, import_date=import_date)
                    
                    if result['success']:
                        # Save import log
                        TimesheetImportLog.objects.create(
                            import_date=import_date,
                            uploaded_by=request.user,
                            notes=notes
                        )
                        
                        import_logger.info(f"Timesheet import successful for {import_date.strftime('%B %Y')} by user {request.user.username}: "
                                          f"Summary={result['summary_count']}, Details={result['details_count']}, "
                                          f"AttSummary={result['attendance_summary_count']}, AttDetails={result['attendance_details_count']}")
                        
                        messages.success(
                            request,
                            f"{result['message']}\n"
                            f"Timesheet Summary: {result['summary_count']} rows\n"
                            f"Timesheet Details: {result['details_count']} rows\n"
                            f"Attendance Summary: {result['attendance_summary_count']} rows\n"
                            f"Attendance Details: {result['attendance_details_count']} rows\n"
                            f"Import logged for: {import_date.strftime('%B %Y')}"
                        )
                    else:
                        import_logger.error(f"Timesheet import failed for {import_date.strftime('%B %Y')} by user {request.user.username}: {result['errors']}")
                        messages.error(request, f"{result['message']}\n" + "\n".join(result['errors'][:5]))
                except Exception as e:
                    import_logger.error(f"Error during import for user {request.user.username}: {str(e)}", exc_info=True)
                    logger.error(f"Import error: {str(e)}")
                    messages.error(request, f"Error during import: {str(e)}")
            except Exception as e:
                import_logger.error(f"Error processing file for user {request.user.username}: {str(e)}", exc_info=True)
                logger.error(f"File processing error: {str(e)}")
                messages.error(request, f"Error processing file: {str(e)}")
            finally:
                # Clean up temp file
                try:
                    if os.path.exists(temp_file.name):
                        os.remove(temp_file.name)
                except:
                    pass
        else:
            messages.error(request, "Form validation failed")
    else:
        form = TimesheetImportForm()
    
    context = {
        'form': form,
        'is_admin': True,
        'import_logs': TimesheetImportLog.objects.all().order_by('-created_date')[:10],
    }
    return render(request, 'timesheet/import_timesheet.html', context)


@login_required(login_url='login')
def import_client_timesheet_entries(request):
    """Import client timesheet entries for multiple employees - Admin only"""
    if not is_admin(request.user):
        access_logger.warning(
            f"Unauthorized access attempt to import_client_timesheet_entries by user: {request.user.username}"
        )
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    from .utils import import_client_timesheet_entries as import_entries

    import_logger = logging.getLogger('timesheet.import')
    client_import_status = getattr(settings, 'CLIENT_TIMESHEET_IMPORT_STATUS', 'DRAFT')

    if request.method == 'POST':
        form = ClientTimesheetImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            import_date = form.cleaned_data['import_date']
            notes = form.cleaned_data.get('notes', '')
            overwrite_drafts = form.cleaned_data['overwrite_drafts']
            result = import_entries(
                uploaded_file,
                overwrite_drafts=overwrite_drafts,
                import_date=import_date,
                notes=notes
            )

            from .models import TimesheetImportLog

            if result['success']:
                TimesheetImportLog.objects.create(
                    import_date=import_date,
                    uploaded_by=request.user,
                    notes=(
                        f"Client Timesheet Import\n"
                        f"Created: {result['created_count']}\n"
                        f"Updated: {result['updated_count']}\n"
                        f"Skipped: {result['skipped_count']}\n"
                        f"{notes}"
                    ).strip()
                )
                import_logger.info(
                    f"Client timesheet import successful by user {request.user.username}: "
                    f"Created={result['created_count']}, Updated={result['updated_count']}, "
                    f"Skipped={result['skipped_count']}"
                )
                messages.success(
                    request,
                    f"Client timesheet import completed. "
                    f"Created {result['created_count']}, updated {result['updated_count']}, "
                    f"skipped {result['skipped_count']} entries."
                )
                return render(
                    request,
                    'timesheet/import_client_timesheet.html',
                    {
                        'form': ClientTimesheetImportForm(),
                        'result': result,
                        'client_import_status': result.get('import_status', client_import_status),
                    }
                )

            import_logger.error(
                f"Client timesheet import failed by user {request.user.username}: {result['errors']}"
            )
            messages.error(
                request,
                f"{result['message']}\n" + "\n".join(result['errors'][:10])
            )
            return render(
                request,
                'timesheet/import_client_timesheet.html',
                {
                    'form': form,
                    'result': result,
                    'client_import_status': result.get('import_status', client_import_status),
                }
            )
    else:
        form = ClientTimesheetImportForm()

    return render(
        request,
        'timesheet/import_client_timesheet.html',
        {'form': form, 'client_import_status': client_import_status}
    )

