from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Employee, Project, CompOff, Holiday, TimesheetImportLog, TimesheetEntry


class EmployeeForm(forms.ModelForm):
    """Form for creating/updating employees"""
    class Meta:
        model = Employee
        fields = ['name', 'employee_id', 'email', 'project', 'location', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 001'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'project': forms.Select(attrs={
                'class': 'form-control',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Indore'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class CompOffForm(forms.ModelForm):
    """Form for creating/updating compoffs"""
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select Employee",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    def __init__(self, *args, **kwargs):
        """Initialize form with user context to filter employee list
        
        Args:
            user: Django User object (optional)
            is_admin: Boolean indicating if user is admin (optional)
            employee: Employee object for non-admin users (optional)
        """
        self.user = kwargs.pop('user', None)
        self.is_admin = kwargs.pop('is_admin', False)
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Store original instance for later validation
        self._original_instance = self.instance
        
        # Filter employee queryset based on user role
        if not self.is_admin and self.employee:
            # For non-admin users, only show their own employee record
            self.fields['employee'].queryset = Employee.objects.filter(pk=self.employee.pk)
            # Remove the empty label for non-admins (they have only one choice)
            self.fields['employee'].empty_label = None
            # Mark field as not required - we'll handle validation in clean()
            self.fields['employee'].required = False
            # Disable the field for non-admins to prevent modification
            self.fields['employee'].disabled = True

    def clean(self):
        """Handle validation including disabled employee field"""
        cleaned_data = super().clean()
        
        # If employee field is disabled, restore it from the instance or passed employee
        if self.fields['employee'].disabled:
            if self._original_instance.pk:
                # Editing existing Comp-Off - use the instance's employee
                cleaned_data['employee'] = self._original_instance.employee
            elif self.employee:
                # Creating new Comp-Off as non-admin - use the passed employee
                cleaned_data['employee'] = self.employee
        
        # Ensure employee is always present
        if not cleaned_data.get('employee'):
            raise forms.ValidationError('Employee field is required.')

        working_date = cleaned_data.get('working_date')
        compoff_date = cleaned_data.get('compoff_date')
        if working_date and compoff_date and compoff_date < working_date:
            raise ValidationError(
                'Comp-Off date cannot be earlier than the work date.'
            )
        
        return cleaned_data

    def _holiday_exists_for_employee(self, holiday_date, holiday_types=None):
        """Check whether a holiday exists for the selected employee's location."""
        employee = self.cleaned_data.get('employee') or self.employee
        holiday_filters = Q(date=holiday_date)
        if holiday_types:
            holiday_filters &= Q(holiday_type__in=holiday_types)

        location = getattr(employee, 'location', '') if employee else ''
        if location:
            holiday_filters &= Q(location=location) | Q(location='')

        return Holiday.objects.filter(holiday_filters).exists()

    class Meta:
        model = CompOff
        fields = ['employee', 'working_date', 'compoff_date', 'status', 'notes']
        widgets = {
            'working_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'compoff_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
        }

    def clean_working_date(self):
        """Validate that working_date is a weekend or public holiday but not a special holiday"""
        working_date = self.cleaned_data.get('working_date')
        if working_date:
            # Check if it's a special holiday - NOT ALLOWED
            special_holiday = self._holiday_exists_for_employee(
                working_date,
                holiday_types=['SPECIAL_HOLIDAY']
            )
            if special_holiday:
                raise forms.ValidationError(
                    'Comp-Off cannot be created for special holidays.'
                )
            
            # Check if it's a weekend (Saturday=5, Sunday=6)
            if working_date.weekday() < 5:  # Monday to Friday
                # Check if it's a public holiday
                if not self._holiday_exists_for_employee(
                    working_date,
                    holiday_types=['PUBLIC_HOLIDAY', 'WEEKEND']
                ):
                    raise forms.ValidationError(
                        'Working date must be a weekend (Saturday/Sunday) or a public holiday.'
                    )
        return working_date

    def clean_compoff_date(self):
        """Validate that compoff_date is a weekday and not a holiday"""
        compoff_date = self.cleaned_data.get('compoff_date')
        if compoff_date:
            # Check if it's a weekend (Saturday=5, Sunday=6) - NOT ALLOWED
            if compoff_date.weekday() >= 5:
                raise forms.ValidationError(
                    'Comp-Off date must be a weekday (Monday to Friday).'
                )
            
            # Check if it's any holiday - NOT ALLOWED
            if self._holiday_exists_for_employee(
                compoff_date,
                holiday_types=['PUBLIC_HOLIDAY', 'WEEKEND', 'SPECIAL_HOLIDAY']
            ):
                raise forms.ValidationError(
                    'Comp-Off date cannot be a holiday or weekend.'
                )
        return compoff_date


class UserRegistrationForm(forms.ModelForm):
    """Form for user registration"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
        min_length=8
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        }),
        min_length=8
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password != password_confirm:
            raise forms.ValidationError("Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ChangePasswordForm(forms.Form):
    """Form for users to change their password"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Password'
        }),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        }),
        label='New Password',
        min_length=8
    )
    new_password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        }),
        label='Confirm New Password',
        min_length=8
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        """Verify current password is correct"""
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Current password is incorrect.')
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')

        if new_password and new_password_confirm:
            if new_password != new_password_confirm:
                raise forms.ValidationError('New passwords do not match!')

        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


class PasswordResetSelectionForm(forms.Form):
    """Form for admin to select which employee's password to reset"""
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select Employee",
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Select Employee to Reset Password'
    )


class TimesheetImportForm(forms.Form):
    """Form for importing timesheet XLSX files"""
    import_date = forms.DateField(
        label='Timesheet For (Date)',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        help_text='Select the date/month this timesheet is for (e.g., last day of month)'
    )
    file = forms.FileField(
        label='XLSX File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx',
        }),
        help_text='Upload an Excel file (.xlsx) with timesheet data'
    )
    notes = forms.CharField(
        label='Notes (Optional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any notes about this timesheet import'
        }),
        required=False,
        help_text='Optional notes about this import'
    )

    def clean_file(self):
        """Validate file is an Excel file"""
        file = self.cleaned_data['file']
        if file:
            if not file.name.endswith('.xlsx'):
                raise forms.ValidationError('Please upload a .xlsx file')
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('File size must be less than 5MB')
        return file


class ClientTimesheetImportForm(forms.Form):
    """Form for importing client timesheet data from XLSX files
    
    Expected format:
    - Row 1: Headers (optional)
    - Row 2: Date | Employee Name 1 | Employee Name 2 | ... | Employee Name N
    - Row 3+: Date | Hours for Employee 1 | Hours for Employee 2 | ... | Hours for Employee N
    - Data spans from start to end of month (including weekends/holidays)
    - Only create entries for cells with value > 0
    """
    import_date = forms.DateField(
        label='Timesheet Month',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        help_text='Select the date/month this timesheet is for (e.g., last day of month)'
    )
    file = forms.FileField(
        label='XLSX File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx',
        }),
        help_text='Upload an Excel file (.xlsx) with client timesheet data'
    )
    project = forms.CharField(
        label='Project Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Project ABC',
        }),
        help_text='Fallback project name for employees without an assigned project'
    )
    notes = forms.CharField(
        label='Notes (Optional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any notes about this import'
        }),
        required=False,
        help_text='Optional notes about this import'
    )

    def clean_file(self):
        """Validate file is an Excel file"""
        file = self.cleaned_data['file']
        if file:
            if not file.name.endswith('.xlsx'):
                raise forms.ValidationError('Please upload a .xlsx file')
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('File size must be less than 5MB')
        return file


class TimesheetEntryForm(forms.ModelForm):
    """Form for creating/updating timesheet entries"""
    project = forms.ChoiceField(
        choices=(),
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    hours = forms.IntegerField(
        min_value=0,
        max_value=12,
        initial=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 8',
            'step': '1',
            'min': '0',
            'max': '12'
        })
    )

    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        self.fields['project'].choices = self._get_project_choices()
        if not self.fields['project'].choices:
            self.fields['project'].choices = [('', 'No project assigned')]
            self.fields['project'].widget.attrs['disabled'] = True
        else:
            self.fields['project'].widget.attrs.pop('disabled', None)

    def _get_project_choices(self):
        """Return project dropdown choices allowed for the employee."""
        if self.employee and self.employee.project:
            project_name = self.employee.project.project
            return [(project_name, project_name)]

        instance_project = getattr(getattr(self, 'instance', None), 'project', '')
        if instance_project:
            return [(instance_project, instance_project)]

        return []
    
    class Meta:
        model = TimesheetEntry
        fields = ['date', 'project', 'hours', 'comments']
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional comments'
            }),
        }

    def clean_hours(self):
        """Validate hours is between 0 and 12"""
        hours = self.cleaned_data.get('hours')
        if hours is not None:
            if hours < 0 or hours > 12:
                raise forms.ValidationError('Hours must be between 0 and 12.')
        return hours

    def clean_date(self):
        """Prevent timesheet entries from being created on special holidays."""
        entry_date = self.cleaned_data.get('date')
        if entry_date:
            holiday_filters = Q(
                date=entry_date,
                holiday_type='SPECIAL_HOLIDAY'
            )
            if getattr(self.employee, 'location', ''):
                holiday_filters &= Q(location=self.employee.location) | Q(location='')

            if Holiday.objects.filter(holiday_filters).exists():
                raise forms.ValidationError(
                    'Timesheet entries are not allowed on special holidays.'
                )
        return entry_date

    def clean(self):
        """Show a friendly validation error for duplicate employee/date/project entries."""
        cleaned_data = super().clean()
        entry_date = cleaned_data.get('date')
        project = cleaned_data.get('project')
        employee = self.employee or getattr(self.instance, 'employee', None)

        if employee and not employee.project:
            raise forms.ValidationError(
                'No project is assigned to this employee. Please contact an administrator.'
            )

        if employee and employee.project and project != employee.project.project:
            raise forms.ValidationError(
                'Please select a project assigned to this employee.'
            )

        if employee and entry_date and project:
            duplicate_qs = TimesheetEntry.objects.filter(
                employee=employee,
                date=entry_date,
                project=project
            )

            if self.instance.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)

            if duplicate_qs.exists():
                raise forms.ValidationError(
                    'A timesheet entry already exists for this employee, date, and project.'
                )

        return cleaned_data

