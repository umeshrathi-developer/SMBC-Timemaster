from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """Project master table - Normalized from Employee"""
    project_id = models.IntegerField(primary_key=True)
    department_name = models.CharField(max_length=100)
    project = models.CharField(max_length=100)
    project_code = models.IntegerField()
    manager = models.CharField(max_length=100, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['project_id']
        indexes = [
            models.Index(fields=['department_name']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return '{} - {} (ID: {})'.format(self.project, self.department_name, self.project_id)


class Location(models.Model):
    """Location master table"""
    name = models.CharField(max_length=100, unique=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='timesheet_l_name_b53e0a_idx'),
        ]

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Employee master table"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, blank=False)
    employee_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} ({})'.format(self.name, self.employee_id)


class Holiday(models.Model):
    """Holiday/Weekend master table"""
    HOLIDAY_TYPES = (
        ('PUBLIC_HOLIDAY', 'Public Holiday'),
        ('WEEKEND', 'Weekend'),
        ('SPECIAL_HOLIDAY', 'Special Holiday'),
    )

    name = models.CharField(max_length=100, blank=False)
    date = models.DateField()
    holiday_type = models.CharField(max_length=50, choices=HOLIDAY_TYPES)
    location = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return '{} - {} ({})'.format(self.name, self.date, self.holiday_type)


class CompOff(models.Model):
    """Compensatory Off (CompOff) table"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('TAKEN', 'Taken'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='compoffs')
    working_date = models.DateField(null=True, blank=True)
    compoff_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        """Auto-update status based on compoff_date"""
        from datetime import date
        
        # If compoff_date is empty, ensure status is PENDING
        if not self.compoff_date:
            self.status = 'PENDING'
        # If compoff_date is in the past, change status to TAKEN
        elif self.compoff_date < date.today():
            self.status = 'TAKEN'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return '{} - Comp-Off (Status: {})'.format(self.employee.name, self.status)


class TimesheetSummary(models.Model):
    """Timesheet Summary from import"""
    email_id = models.EmailField(max_length=100)
    team_member = models.CharField(max_length=100)
    project_id = models.IntegerField()
    project = models.CharField(max_length=100)
    total_hours = models.DecimalField(max_digits=8, decimal_places=2)
    import_date = models.DateField(null=True, blank=True, help_text='Date/Month of this import')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Timesheet Summary'
        verbose_name_plural = 'Timesheet Summaries'

    def __str__(self):
        return '{} - {} ({} hrs)'.format(self.team_member, self.project, self.total_hours)


class TimesheetDetails(models.Model):
    """Timesheet Details from import"""
    email_id = models.EmailField(max_length=100)
    team_member = models.CharField(max_length=100)
    project_id = models.IntegerField()
    project = models.CharField(max_length=100)
    date = models.DateField()
    time_logged = models.DecimalField(max_digits=8, decimal_places=2)
    comment = models.TextField(blank=True)
    import_date = models.DateField(null=True, blank=True, help_text='Date/Month of this import')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Timesheet Detail'
        verbose_name_plural = 'Timesheet Details'

    def __str__(self):
        return '{} - {} on {}'.format(self.team_member, self.project, self.date)


class AttendanceSummary(models.Model):
    """Attendance Summary from import"""
    email_id = models.EmailField(max_length=100)
    team_member = models.CharField(max_length=100)
    business_hours = models.DecimalField(max_digits=8, decimal_places=2)
    available_hours = models.DecimalField(max_digits=8, decimal_places=2)
    project_hours = models.DecimalField(max_digits=8, decimal_places=2)
    import_date = models.DateField(null=True, blank=True, help_text='Date/Month of this import')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Attendance Summary'
        verbose_name_plural = 'Attendance Summaries'

    def __str__(self):
        return '{} - Business: {} hrs, Project: {} hrs'.format(
            self.team_member, self.business_hours, self.project_hours
        )


class AttendanceDetails(models.Model):
    """Attendance Details from import"""
    email_id = models.EmailField(max_length=100)
    team_member = models.CharField(max_length=100)
    date = models.DateField()
    business_hours = models.DecimalField(max_digits=8, decimal_places=2)
    available_hours = models.DecimalField(max_digits=8, decimal_places=2)
    remarks = models.TextField(blank=True)
    import_date = models.DateField(null=True, blank=True, help_text='Date/Month of this import')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Attendance Detail'
        verbose_name_plural = 'Attendance Details'

    def __str__(self):
        return '{} - {} ({} hrs)'.format(self.team_member, self.date, self.business_hours)


class TimesheetImportLog(models.Model):
    """Log of timesheet imports to track versions and timing"""
    import_date = models.DateField(help_text='Date of the timesheet being imported (e.g., last day of month)')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text='Optional notes about this import')

    class Meta:
        verbose_name = 'Timesheet Import Log'
        verbose_name_plural = 'Timesheet Import Logs'
        ordering = ['-import_date', '-created_date']

    def __str__(self):
        return 'Timesheet for {} (Imported on {})'.format(
            self.import_date.strftime('%B %Y'), 
            self.created_date.strftime('%Y-%m-%d %H:%M')
        )


class TimesheetEntry(models.Model):
    """User-entered timesheet entries for tracking project hours"""
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='timesheet_entries')
    date = models.DateField()
    project = models.CharField(max_length=100)
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Timesheet Entry'
        verbose_name_plural = 'Timesheet Entries'
        ordering = ['-date', 'employee']
        unique_together = ('employee', 'date', 'project')
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return '{} - {} on {} ({} hrs)'.format(
            self.employee.name, self.project, self.date, self.hours
        )
