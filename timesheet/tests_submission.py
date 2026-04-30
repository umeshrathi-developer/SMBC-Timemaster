from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from timesheet.models import CompOff, Employee, Holiday, TimesheetEntry


class TimesheetSubmissionCompOffTests(TestCase):
    def setUp(self):
        self.employee_group, _ = Group.objects.get_or_create(name='Employee')
        self.user = User.objects.create_user(username='alice', password='testpass123')
        self.user.groups.add(self.employee_group)
        self.employee = Employee.objects.create(
            user=self.user,
            name='Alice',
            employee_id='E001',
            email='alice@example.com',
            location='Indore',
        )

    def test_submission_uses_pending_compoff_for_missing_weekday(self):
        CompOff.objects.create(
            employee=self.employee,
            working_date=date(2026, 3, 29),
            status='PENDING',
        )
        TimesheetEntry.objects.create(
            employee=self.employee,
            date=date(2026, 4, 1),
            project='Client Project',
            hours=8,
            status='DRAFT',
        )

        self.client.login(username='alice', password='testpass123')
        response = self.client.post(
            reverse('timesheet_entry_submit'),
            {
                'month': '2026-04',
                'submit_all': 'false',
                'from_date': '2026-04-01',
                'to_date': '2026-04-02',
            },
        )

        self.assertEqual(response.status_code, 302)
        compoff = CompOff.objects.get(employee=self.employee)
        self.assertEqual(compoff.status, 'TAKEN')
        self.assertEqual(compoff.compoff_date, date(2026, 4, 2))

    def test_resubmitting_range_with_existing_submitted_entries_still_deducts_missing_day(self):
        CompOff.objects.create(
            employee=self.employee,
            working_date=date(2026, 3, 29),
            status='PENDING',
        )
        TimesheetEntry.objects.create(
            employee=self.employee,
            date=date(2026, 4, 1),
            project='Client Project',
            hours=8,
            status='SUBMITTED',
        )

        self.client.login(username='alice', password='testpass123')
        response = self.client.post(
            reverse('timesheet_entry_submit'),
            {
                'month': '2026-04',
                'submit_all': 'false',
                'from_date': '2026-04-01',
                'to_date': '2026-04-02',
            },
        )

        self.assertEqual(response.status_code, 302)
        compoff = CompOff.objects.get(employee=self.employee)
        self.assertEqual(compoff.status, 'TAKEN')
        self.assertEqual(compoff.compoff_date, date(2026, 4, 2))

    def test_empty_range_does_not_consume_pending_compoff(self):
        CompOff.objects.create(
            employee=self.employee,
            working_date=date(2026, 3, 29),
            status='PENDING',
        )

        self.client.login(username='alice', password='testpass123')
        response = self.client.post(
            reverse('timesheet_entry_submit'),
            {
                'month': '2026-04',
                'submit_all': 'false',
                'from_date': '2026-04-01',
                'to_date': '2026-04-02',
            },
        )

        self.assertEqual(response.status_code, 302)
        compoff = CompOff.objects.get(employee=self.employee)
        self.assertEqual(compoff.status, 'PENDING')
        self.assertIsNone(compoff.compoff_date)

    def test_submission_does_not_consume_future_pending_compoff(self):
        CompOff.objects.create(
            employee=self.employee,
            working_date=date(2026, 4, 5),
            status='PENDING',
        )
        TimesheetEntry.objects.create(
            employee=self.employee,
            date=date(2026, 4, 1),
            project='Client Project',
            hours=8,
            status='DRAFT',
        )

        self.client.login(username='alice', password='testpass123')
        response = self.client.post(
            reverse('timesheet_entry_submit'),
            {
                'month': '2026-04',
                'submit_all': 'false',
                'from_date': '2026-04-01',
                'to_date': '2026-04-02',
            },
        )

        self.assertEqual(response.status_code, 302)
        compoff = CompOff.objects.get(employee=self.employee)
        self.assertEqual(compoff.status, 'PENDING')
        self.assertIsNone(compoff.compoff_date)

    def test_same_location_public_holiday_is_not_treated_as_missing_workday(self):
        Holiday.objects.create(
            name='Indore Holiday',
            date=date(2026, 4, 2),
            holiday_type='PUBLIC_HOLIDAY',
            location='Indore',
        )
        CompOff.objects.create(
            employee=self.employee,
            working_date=date(2026, 3, 29),
            status='PENDING',
        )
        TimesheetEntry.objects.create(
            employee=self.employee,
            date=date(2026, 4, 1),
            project='Client Project',
            hours=8,
            status='DRAFT',
        )

        self.client.login(username='alice', password='testpass123')
        response = self.client.post(
            reverse('timesheet_entry_submit'),
            {
                'month': '2026-04',
                'submit_all': 'false',
                'from_date': '2026-04-01',
                'to_date': '2026-04-02',
            },
        )

        self.assertEqual(response.status_code, 302)
        compoff = CompOff.objects.get(employee=self.employee)
        self.assertEqual(compoff.status, 'PENDING')
        self.assertIsNone(compoff.compoff_date)

    def test_other_location_public_holiday_still_counts_as_missing_workday(self):
        Holiday.objects.create(
            name='Pune Holiday',
            date=date(2026, 4, 2),
            holiday_type='PUBLIC_HOLIDAY',
            location='Pune',
        )
        CompOff.objects.create(
            employee=self.employee,
            working_date=date(2026, 3, 29),
            status='PENDING',
        )
        TimesheetEntry.objects.create(
            employee=self.employee,
            date=date(2026, 4, 1),
            project='Client Project',
            hours=8,
            status='DRAFT',
        )

        self.client.login(username='alice', password='testpass123')
        response = self.client.post(
            reverse('timesheet_entry_submit'),
            {
                'month': '2026-04',
                'submit_all': 'false',
                'from_date': '2026-04-01',
                'to_date': '2026-04-02',
            },
        )

        self.assertEqual(response.status_code, 302)
        compoff = CompOff.objects.get(employee=self.employee)
        self.assertEqual(compoff.status, 'TAKEN')
        self.assertEqual(compoff.compoff_date, date(2026, 4, 2))
