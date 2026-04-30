from django.urls import path, include
from . import views
from .admin import (
    TimesheetImportAdmin, TimesheetSummaryAdmin, TimesheetDetailsAdmin,
    AttendanceSummaryAdmin, AttendanceDetailsAdmin, TimesheetImportLogAdmin
)
from .models import TimesheetSummary, TimesheetDetails, AttendanceSummary, AttendanceDetails, TimesheetImportLog

# Create an instance of the custom admin site
timesheet_admin = TimesheetImportAdmin(name='timesheet_admin')

# Register models with the custom admin site
timesheet_admin.register(TimesheetSummary, TimesheetSummaryAdmin)
timesheet_admin.register(TimesheetDetails, TimesheetDetailsAdmin)
timesheet_admin.register(AttendanceSummary, AttendanceSummaryAdmin)
timesheet_admin.register(AttendanceDetails, AttendanceDetailsAdmin)
timesheet_admin.register(TimesheetImportLog, TimesheetImportLogAdmin)

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Management
    path('change-password/', views.change_password, name='change_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Employee Management
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_add, name='employee_add'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('employees/<int:pk>/report/', views.employee_report, name='employee_report'),
    
    # Comp-Off Management
    path('compoffs/', views.compoff_list, name='compoff_list'),
    path('compoffs/add/', views.compoff_add, name='compoff_add'),
    path('compoffs/<int:pk>/edit/', views.compoff_edit, name='compoff_edit'),
    path('compoffs/<int:pk>/delete/', views.compoff_delete, name='compoff_delete'),
    
    # Timesheet Data Views
    path('timesheet-data/', views.timesheet_data_view, name='timesheet_data'),
    path('client-reporting/', views.client_reporting, name='client_reporting'),
    path('accrual-summary/', views.accrual_summary, name='accrual_summary'),
    path('timesheet-summary/', views.timesheet_summary_view, name='timesheet_summary'),
    path('timesheet-details/', views.timesheet_details_view, name='timesheet_details'),
    path('attendance-summary/', views.attendance_summary_view, name='attendance_summary'),
    path('attendance-details/', views.attendance_details_view, name='attendance_details'),
    
    # Import Timesheet Data
    path('import-timesheet/', views.import_timesheet_data, name='import_timesheet_data'),
    path('import-client-timesheet/', views.import_client_timesheet_data, name='import_client_timesheet_data'),
    
    # Timesheet Entry Management (User Input)
    path('my-timesheet/', views.timesheet_entry_list, name='timesheet_entry_list'),
    path('my-timesheet/add/', views.timesheet_entry_add, name='timesheet_entry_add'),
    path('my-timesheet/<int:pk>/edit/', views.timesheet_entry_edit, name='timesheet_entry_edit'),
    path('my-timesheet/<int:pk>/delete/', views.timesheet_entry_delete, name='timesheet_entry_delete'),
    path('my-timesheet/submit/', views.timesheet_entry_submit, name='timesheet_entry_submit'),
    path('api/generate-weekdays/', views.generate_timesheet_weekdays, name='generate_timesheet_weekdays'),
    
    # Custom Timesheet Admin
    path('admin/timesheet/', include((timesheet_admin.get_urls(), timesheet_admin.name), namespace=timesheet_admin.name)),
]
