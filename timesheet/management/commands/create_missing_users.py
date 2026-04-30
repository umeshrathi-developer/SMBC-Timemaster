from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction

from timesheet.models import Employee


class Command(BaseCommand):
    help = 'Create Django user accounts for Employee records without a linked User.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which users would be created without saving.'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        group, _ = Group.objects.get_or_create(name='Employee')

        employees = Employee.objects.filter(user__isnull=True)
        total = employees.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No employees without user accounts found.'))
            return

        created_count = 0
        for emp in employees:
            # Derive first and last name from Employee.name
            name = (emp.name or '').strip()
            parts = name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = parts[-1]
            elif len(parts) == 1:
                first_name = parts[0]
                last_name = ''
            else:
                # Fallback to employee_id when name missing
                first_name = emp.employee_id
                last_name = ''

            # Build base username as firstname.lastname (lowercase)
            base_username = (first_name + ('.' + last_name if last_name else '')).lower()
            # Normalize whitespace and replace spaces with dot
            base_username = base_username.replace(' ', '.')

            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{suffix}"
                suffix += 1

            email = emp.email or ''
            password = username

            # Report or create
            if dry_run:
                self.stdout.write(f"Would create user: username={username}, email={email}, employee={emp.name} ({emp.employee_id})")
                created_count += 1
                continue

            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password,
                                                first_name=first_name, last_name=last_name)
                user.is_active = emp.is_active
                user.save()

                # Add to Employee group
                user.groups.add(group)

                # Link employee record
                emp.user = user
                emp.save()

            self.stdout.write(self.style.SUCCESS(
                f"Created user '{username}' for Employee {emp.name} ({emp.employee_id})"
            ))
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created_count} users."))
