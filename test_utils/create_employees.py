#!/usr/bin/env python
"""Script to create 5 employees in the database"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from timesheet.models import Employee

# Employee data to create
employees_data = [
    {
        'name': 'Aishwarya Moongrey',
        'employee_id': '002',
        'email': 'aishwarya.moongrey@infobeans.com',
        'department': 'SMBC1',
    },
    {
        'name': 'Akshay Gaikwad',
        'employee_id': '003',
        'email': 'akshay.gaikwad@infobeans.com',
        'department': 'SMBC1',
    },
    {
        'name': 'Anjali James',
        'employee_id': '004',
        'email': 'anjali.james@infobeans.com',
        'department': 'SMBC1',
    },
    {
        'name': 'Deepak Pauranik',
        'employee_id': '005',
        'email': 'deepak.pauranik@infobeans.com',
        'department': 'SMBC1',
    },
    {
        'name': 'Harrshit Varma',
        'employee_id': '006',
        'email': 'harrshit.varma@infobeans.com',
        'department': 'SMBC1',
    },
]

# Create employees
created_count = 0
skipped_count = 0

for emp_data in employees_data:
    try:
        employee, created = Employee.objects.get_or_create(
            employee_id=emp_data['employee_id'],
            defaults={
                'name': emp_data['name'],
                'email': emp_data['email'],
                'department': emp_data['department'],
                'is_active': True,
            }
        )
        
        if created:
            print(f"✓ Created: {employee.name} (ID: {employee.employee_id})")
            created_count += 1
        else:
            print(f"⊘ Already exists: {employee.name} (ID: {employee.employee_id})")
            skipped_count += 1
            
    except Exception as e:
        print(f"✗ Error creating employee: {emp_data['name']} - {str(e)}")

print(f"\nSummary: {created_count} created, {skipped_count} skipped")
