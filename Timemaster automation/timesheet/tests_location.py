from datetime import date

from django.test import TestCase

from timesheet.forms import CompOffForm, TimesheetEntryForm
from timesheet.models import Employee, Holiday, Project
from timesheet.views import is_holiday_date


class LocationAwareHolidayTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            project_id=501,
            department_name='Risk Tech',
            project='Risk Tech',
            project_code=1501,
            manager='Manager One',
        )
        self.employee = Employee.objects.create(
            name='Alice',
            employee_id='LOC001',
            location='Indore',
            project=self.project,
        )

    def test_holiday_is_matched_for_employee_location(self):
        Holiday.objects.create(
            name='Indore Special Holiday',
            date=date(2026, 5, 1),
            holiday_type='SPECIAL_HOLIDAY',
            location='Indore',
        )

        self.assertTrue(is_holiday_date(date(2026, 5, 1), employee=self.employee))

    def test_holiday_in_other_location_does_not_apply(self):
        Holiday.objects.create(
            name='Pune Holiday',
            date=date(2026, 5, 1),
            holiday_type='PUBLIC_HOLIDAY',
            location='Pune',
        )

        self.assertFalse(is_holiday_date(date(2026, 5, 1), employee=self.employee))

    def test_timesheet_entry_special_holiday_validation_is_location_aware(self):
        Holiday.objects.create(
            name='Pune Special Holiday',
            date=date(2026, 5, 2),
            holiday_type='SPECIAL_HOLIDAY',
            location='Pune',
        )

        form = TimesheetEntryForm(
            data={
                'date': '2026-05-02',
                'project': 'Risk Tech',
                'hours': 8,
                'comments': '',
            },
            employee=self.employee,
        )

        self.assertTrue(form.is_valid())

    def test_compoff_form_validates_public_holiday_by_employee_location(self):
        Holiday.objects.create(
            name='Indore Public Holiday',
            date=date(2026, 5, 4),
            holiday_type='PUBLIC_HOLIDAY',
            location='Indore',
        )

        form = CompOffForm(
            data={
                'employee': self.employee.pk,
                'working_date': '2026-05-04',
                'compoff_date': '2026-05-05',
                'status': 'PENDING',
                'notes': '',
            },
            is_admin=True,
        )

        self.assertTrue(form.is_valid(), form.errors)
