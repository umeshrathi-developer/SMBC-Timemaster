#!/usr/bin/env python
"""
Script to update employee emails from infobeans.com to testt.com
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from timesheet.models import Employee

# Find all employees with infobeans.com email
employees = Employee.objects.filter(email__icontains='infobeans.com')
count = employees.count()
print(f"Found {count} employees with infobeans.com email")

# Update each employee's email
updated = 0
for emp in employees:
    old_email = emp.email
    emp.email = emp.email.replace('infobeans.com', 'testt.com')
    emp.save()
    print(f"Updated: {old_email} → {emp.email}")
    updated += 1

print(f"\nTotal updated: {updated} employees")

# Verify the update
remaining = Employee.objects.filter(email__icontains='infobeans.com').count()
print(f"Remaining infobeans.com emails: {remaining}")

new_testt = Employee.objects.filter(email__icontains='testt.com').count()
print(f"Total testt.com emails: {new_testt}")
