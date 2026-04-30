#!/usr/bin/env python
"""Script to create user accounts for employees"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from timesheet.models import Employee, CompOff

# Employee data
employees_data = [
    {'emp_id': '002', 'name': 'Aishwarya Moongrey', 'email': 'aishwarya.moongrey@infobeans.com'},
    {'emp_id': '003', 'name': 'Akshay Gaikwad', 'email': 'akshay.gaikwad@infobeans.com'},
    {'emp_id': '004', 'name': 'Anjali James', 'email': 'anjali.james@infobeans.com'},
    {'emp_id': '005', 'name': 'Deepak Pauranik', 'email': 'deepak.pauranik@infobeans.com'},
    {'emp_id': '006', 'name': 'Harrshit Varma', 'email': 'harrshit.varma@infobeans.com'},
]

# Create or get groups
employee_group, _ = Group.objects.get_or_create(name='Employee')
admin_group, _ = Group.objects.get_or_create(name='Admin')

# Get Comp-Off permissions for employee group
compoff_content_type = ContentType.objects.get_for_model(CompOff)
compoff_permissions = Permission.objects.filter(content_type=compoff_content_type)

# Set permissions for Employee group (only view own CompOff)
employee_group.permissions.set(compoff_permissions)

# Set permissions for Admin group (all permissions)
all_permissions = Permission.objects.all()
admin_group.permissions.set(all_permissions)

print("✓ Groups 'Employee' and 'Admin' created/configured")
print(f"✓ Employee group has {employee_group.permissions.count()} permissions")
print(f"✓ Admin group has {admin_group.permissions.count()} permissions\n")

# Create user accounts for employees
created_count = 0
linked_count = 0

for emp_data in employees_data:
    try:
        # Get the employee
        employee = Employee.objects.get(employee_id=emp_data['emp_id'])
        
        # Create username from email (first part before @)
        username = emp_data['email'].split('@')[0]
        
        # Check if user already exists
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': emp_data['email'],
                'first_name': emp_data['name'].split()[0],
                'last_name': ' '.join(emp_data['name'].split()[1:]),
            }
        )
        
        # Set password if user was just created
        if created:
            user.set_password(username)  # Default password = username
            user.save()
            print(f"✓ Created User: {username}")
            created_count += 1
        else:
            print(f"⊘ User already exists: {username}")
        
        # Link employee to user
        if not employee.user:
            employee.user = user
            employee.save()
            print(f"  └─ Linked to Employee: {employee.name} (ID: {employee.employee_id})")
            linked_count += 1
        else:
            print(f"  └─ Already linked to Employee: {employee.name}")
        
        # Add user to Employee group
        if not user.groups.filter(name='Employee').exists():
            user.groups.add(employee_group)
            print(f"  └─ Added to 'Employee' group")
        
    except Employee.DoesNotExist:
        print(f"✗ Employee with ID {emp_data['emp_id']} not found")
    except Exception as e:
        print(f"✗ Error processing {emp_data['name']}: {str(e)}")

print(f"\nSummary: {created_count} users created, {linked_count} linked to employees")
print("\n📝 NOTE: Default password for each user is their username (e.g., 'aishwarya.moongrey')")
print("⚠️  Users should change their password on first login!")
