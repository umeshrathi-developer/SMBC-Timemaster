#!/usr/bin/env python
"""
Script to fix employee IDs - remove 'EMP-' prefix and keep just the number
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from timesheet.models import Employee

# Get all employees with EMP- prefix
employees = Employee.objects.filter(employee_id__startswith='EMP-')

print(f"Found {employees.count()} employees with 'EMP-' prefix\n")

# Update each employee
for emp in employees:
    old_id = emp.employee_id
    # Extract just the number part (e.g., "EMP-007" -> "007")
    new_id = emp.employee_id.replace('EMP-', '')
    
    emp.employee_id = new_id
    emp.save()
    print(f'✓ {emp.name}: {old_id} → {new_id}')

print(f'\n✓ Total updated: {employees.count()}')
