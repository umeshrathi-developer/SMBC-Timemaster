from django.contrib import admin
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
import logging
from .models import Project, Location, Employee, Holiday, CompOff, TimesheetSummary, TimesheetDetails, AttendanceSummary, AttendanceDetails, TimesheetImportLog, TimesheetEntry
from .forms import TimesheetImportForm
from .utils import import_employee_file, import_holiday_file

logger = logging.getLogger('timesheet')
import_logger = logging.getLogger('timesheet.import')


@admin.register(TimesheetSummary)
class TimesheetSummaryAdmin(admin.ModelAdmin):
    """Admin for Timesheet Summary"""
    list_display = ['team_member', 'project', 'total_hours', 'created_date']
    list_filter = ['created_date', 'project']
    search_fields = ['team_member', 'project', 'email_id']
    readonly_fields = ['created_date', 'updated_date']
    
    def has_add_permission(self, request):
        """Disable manual add, only allow import"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete"""
        return True


class TimesheetDetailsAdmin(admin.ModelAdmin):
    """Admin for Timesheet Details"""
    list_display = ['team_member', 'project', 'date', 'time_logged', 'created_date']
    list_filter = ['created_date', 'date', 'project']
    search_fields = ['team_member', 'project', 'email_id']
    readonly_fields = ['created_date', 'updated_date']
    
    def has_add_permission(self, request):
        """Disable manual add, only allow import"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete"""
        return True


class AttendanceSummaryAdmin(admin.ModelAdmin):
    """Admin for Attendance Summary"""
    list_display = ['team_member', 'business_hours', 'available_hours', 'project_hours', 'created_date']
    list_filter = ['created_date']
    search_fields = ['team_member', 'email_id']
    readonly_fields = ['created_date', 'updated_date']
    
    def has_add_permission(self, request):
        """Disable manual add, only allow import"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete"""
        return True


class AttendanceDetailsAdmin(admin.ModelAdmin):
    """Admin for Attendance Details"""
    list_display = ['team_member', 'date', 'business_hours', 'available_hours', 'created_date']
    list_filter = ['created_date', 'date']
    search_fields = ['team_member', 'email_id']
    readonly_fields = ['created_date', 'updated_date']
    
    def has_add_permission(self, request):
        """Disable manual add, only allow import"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete"""
        return True


class TimesheetImportAdmin(admin.AdminSite):
    """Custom admin site for timesheet import"""
    site_header = 'Timesheet Import'
    site_title = 'Timesheet Import'
    index_title = 'Timesheet Import Administration'
    site_url = None
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_view(self.import_view), name='timesheet_timesheetsummary_import'),
        ]
        return custom_urls + urls
    
    def import_view(self, request):
        """Custom import view for timesheet data"""
        from .utils import import_timesheet_file
        
        if request.method == 'POST':
            form = TimesheetImportForm(request.POST, request.FILES)
            if form.is_valid():
                # Process the import
                try:
                    file_path = form.cleaned_data['file'].temporary_file_path()
                    import_date = form.cleaned_data.get('import_date')
                    
                    # Import the file
                    result = import_timesheet_file(file_path, import_date)
                    
                    if result['success']:
                        import_logger.info(f"Admin import successful for {import_date} by user {request.user.username}")
                        messages.success(request, f'Successfully imported {result["summary_count"]} summary records and {result["details_count"]} detail records.')
                        return redirect('admin:index')
                    else:
                        import_logger.error(f"Admin import failed for {import_date}: {result['errors']}")
                        messages.error(request, f'Import failed: {result["message"]}')
                except Exception as e:
                    import_logger.error(f"Admin import error for user {request.user.username}: {str(e)}", exc_info=True)
                    messages.error(request, f'Import failed: {str(e)}')
        else:
            form = TimesheetImportForm()
        
        context = {
            'form': form,
            'title': 'Import Timesheet Data',
        }
        return self.render(request, 'admin/timesheet_import.html', context)




class HolidayAdminForm(forms.ModelForm):
    """Custom form for Holiday admin to exclude WEEKEND option"""
    holiday_type = forms.ChoiceField(
        choices=[
            ('PUBLIC_HOLIDAY', 'Public Holiday'),
            ('SPECIAL_HOLIDAY', 'Special Holiday'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = Holiday
        fields = ['name', 'date', 'holiday_type', 'location']


class HolidayImportForm(forms.Form):
    """Form for importing holidays from Excel."""
    file = forms.FileField(
        label='Holiday Excel File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xlsm',
        }),
        help_text='Upload an Excel file with columns: S. No., Date, Day, Holiday, Applicability'
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if file and not file.name.lower().endswith(('.xlsx', '.xlsm')):
            raise forms.ValidationError('Please upload an Excel file in .xlsx or .xlsm format.')
        return file


class EmployeeImportForm(forms.Form):
    """Form for importing employees from Excel."""
    file = forms.FileField(
        label='Employee Excel File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xlsm',
        }),
        help_text='Upload an Excel file with columns: name, employee_id, email, project, location, is_active'
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if file and not file.name.lower().endswith(('.xlsx', '.xlsm')):
            raise forms.ValidationError('Please upload an Excel file in .xlsx or .xlsm format.')
        return file


class HolidayAdmin(admin.ModelAdmin):
    """Custom admin for Holiday model"""
    form = HolidayAdminForm
    change_list_template = 'admin/holiday_change_list.html'
    list_display = ['name', 'date', 'holiday_type', 'location']
    list_filter = ['holiday_type', 'location', 'date']
    search_fields = ['name', 'date', 'location']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import/',
                self.admin_site.admin_view(self.import_view),
                name='timesheet_holiday_import',
            ),
        ]
        return custom_urls + urls

    def import_view(self, request):
        """Import holidays from an Excel file."""
        if request.method == 'POST':
            form = HolidayImportForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_holiday_file(form.cleaned_data['file'])
                if result['success']:
                    import_logger.info(
                        f"Holiday import completed by user {request.user.username}. "
                        f"Created={result['created_count']}, Updated={result['updated_count']}"
                    )
                    messages.success(
                        request,
                        f"Holiday import completed. Created {result['created_count']} and updated {result['updated_count']} records."
                    )
                    return redirect('admin:timesheet_holiday_changelist')

                import_logger.error(f"Holiday import failed: {result['errors']}")
                messages.error(request, result['message'])
        else:
            form = HolidayImportForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Import Holidays',
            'opts': self.model._meta,
        }
        return render(request, 'admin/holiday_import.html', context)


class TimesheetImportLogAdmin(admin.ModelAdmin):
    """Admin for Timesheet Import Log"""
    list_display = ['import_date', 'uploaded_by', 'created_date']
    list_filter = ['import_date', 'created_date']
    search_fields = ['uploaded_by__username', 'notes']
    readonly_fields = ['created_date']
    
    def has_add_permission(self, request):
        """Disable manual add, only allow via import"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable change"""
        return False


class TimesheetEntryAdmin(admin.ModelAdmin):
    """Admin for User-entered Timesheet Entries"""
    list_display = ['employee', 'date', 'project', 'hours', 'status', 'created_date']
    list_filter = ['status', 'created_date', 'date', 'employee']
    search_fields = ['employee__name', 'project', 'comments']
    readonly_fields = ['created_date', 'updated_date']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Employee & Date', {
            'fields': ('employee', 'date'),
            'classes': ('wide',)
        }),
        ('Entry Details', {
            'fields': ('project', 'hours', 'comments'),
            'classes': ('wide',)
        }),
        ('Status', {
            'fields': ('status',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('wide', 'collapse'),
        }),
    )
    
    def get_queryset(self, request):
        """Show recent entries first"""
        qs = super().get_queryset(request)
        return qs.order_by('-date', '-created_date')


class EmployeeAdmin(admin.ModelAdmin):
    """Admin for Employee"""
    change_list_template = 'admin/employee_change_list.html'
    list_display = ['name', 'employee_id', 'email', 'project', 'location', 'is_active']
    list_filter = ['is_active', 'project', 'location', 'created_date']
    search_fields = ['name', 'employee_id', 'email', 'project__project', 'project__manager', 'location__name']
    readonly_fields = ['created_date', 'updated_date']
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'employee_id', 'email')
        }),
        ('Project Assignment', {
            'fields': ('project', 'location')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import/',
                self.admin_site.admin_view(self.import_view),
                name='timesheet_employee_import',
            ),
        ]
        return custom_urls + urls

    def import_view(self, request):
        """Import employees from an Excel file."""
        if request.method == 'POST':
            form = EmployeeImportForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_employee_file(form.cleaned_data['file'])
                if result['success']:
                    import_logger.info(
                        f"Employee import completed by user {request.user.username}. "
                        f"Created={result['created_count']}, Updated={result['updated_count']}, "
                        f"UsersCreated={result['user_created_count']}, ProjectsCreated={result['project_created_count']}"
                    )
                    messages.success(
                        request,
                        f"Employee import completed. Created {result['created_count']}, "
                        f"updated {result['updated_count']}, created {result['user_created_count']} users, "
                        f"and created {result['project_created_count']} projects."
                    )
                    return redirect('admin:timesheet_employee_changelist')

                import_logger.error(f"Employee import failed: {result['errors']}")
                messages.error(request, result['message'])
        else:
            form = EmployeeImportForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Import Employees',
            'opts': self.model._meta,
        }
        return render(request, 'admin/employee_import.html', context)


class ProjectAdmin(admin.ModelAdmin):
    """Admin for Project"""
    list_display = ['project_id', 'project', 'department_name', 'project_code', 'manager', 'to_email', 'cc_email']
    list_filter = ['department_name', 'project', 'created_date']
    search_fields = ['project', 'department_name', 'manager', 'to_email', 'cc_email']
    readonly_fields = ['created_date', 'updated_date']
    fieldsets = (
        ('Project Information', {
            'fields': ('project_id', 'project', 'department_name', 'project_code', 'manager')
        }),
        ('Email Recipients', {
            'fields': ('to_email', 'cc_email')
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        }),
    )


class LocationAdmin(admin.ModelAdmin):
    """Admin for Location"""
    list_display = ['name', 'created_date', 'updated_date']
    search_fields = ['name']
    readonly_fields = ['created_date', 'updated_date']
    fieldsets = (
        ('Location Information', {
            'fields': ('name',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Project, ProjectAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Holiday, HolidayAdmin)
admin.site.register(CompOff)
# TimesheetSummary is registered via @admin.register decorator
# Models are now registered with the custom admin site in urls.py
