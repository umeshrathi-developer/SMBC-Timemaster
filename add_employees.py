#!/usr/bin/env python
"""
Script to add new employees to the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from timesheet.models import Employee

# Get the last employee_id
last_employee = Employee.objects.all().order_by('-created_date').first()
last_id = 0
if last_employee:
    try:
        # Try to extract number from employee_id (e.g., "EMP-001" -> 1)
        parts = last_employee.employee_id.split('-')
        if len(parts) > 1:
            last_id = int(parts[-1])
        else:
            last_id = int(last_employee.employee_id) if last_employee.employee_id.isdigit() else 0
    except (ValueError, IndexError):
        # If parsing fails, get the count and use that
        last_id = Employee.objects.count()

# New employees data from the spreadsheet
employees_data = [
    ('Sadashiv Munde', 'Laxman', 'CLEAR', 'sadashiv.munde@infobeans.com'),
    ('Saurabh Suman', 'Laxman', 'CLEAR', 'saurabh.suman@infobeans.com'),
    ('Nirav Dagli', 'Laxman', 'CLEAR', 'nirav.dagli@infobeans.com'),
    ('Rahul Manghani', 'Laxman', 'CLEAR', 'rahul.manghani@infobeans.com'),
    ('Tanya Malik', 'Laxman', 'CLEAR', 'tanya.malik@infobeans.com'),
    ('Pallavi Kalamkar', 'Laxman', 'CLEAR', 'pallavi.kalamkar@infobeans.com'),
    ('Sachin Ajabe', 'Laxman', 'CLEAR', 'sachin.ajabe@infobeans.com'),
    ('Unnati Warade', 'Laxman', 'CLEAR', 'unnati.warade@infobeans.com'),
    ('Sai Ratna', 'Laxman', 'CLEAR', 'sai.ratne@infobeans.com'),
    ('Pratik Jain', 'Raj Betreja', 'ESS', 'pratik.jain@infobeans.com'),
    ('Nitin Shettikar', 'Raj Betreja', 'ESS', 'nitin.shettikar@infobeans.com'),
    ('Vaibhav Tandale', 'Shane/Jyo', 'MDM', 'vaibhav.tandale@infobeans.com'),
    ('Chandan Sarode', 'Ravi Pavuluri', 'LTTS', 'chandan.sarode@infobeans.com'),
    ('Raj Shah', 'Ravi Pavuluri', 'LTTS', 'raj.shah@infobeans.com'),
    ('Mohit Kothari', 'Ranzith', 'EWI', 'mohit.kothari@infobeans.com'),
    ('Harrati Varma', 'Ranzith', 'EWI', 'harrati.varma@infobeans.com'),
    ('Pawan Jaiswal', 'Ranzith', 'EWI', 'pawan.jaiswal@infobeans.com'),
    ('Shubham Thakur', 'Ranzith', 'EWI', 'shubham.thakur@infobeans.com'),
    ('Amit Patil', 'Ranzith', 'EWI', 'amit.patil@infobeans.com'),
    ('Manish Pal', 'Ranzith', 'EWI', 'manish.pal@infobeans.com'),
    ('Chandan Haliware', 'Ranzith', 'EWI', 'chandan.haliware@infobeans.com'),
    ('Dnyeshwar Rawat', 'Ranzith', 'EWI', 'dnyeshwar.rawat@infobeans.com'),
    ('Himesh Haswani', 'Ambalika', 'SR1+10 (A)', 'himesh.haswani@infobeans.com'),
    ('Murlee Patil', 'Ambalika', 'SR1+10 (A)', 'murlee.patil@infobeans.com'),
    ('Akshay Gaikwad', 'Ambalika', 'SR1+10 (A)', 'akshay.gaikwad@infobeans.com'),
    ('Saloni Tongia', 'Ambalika', 'SR1+10 (A)', 'saloni.tongia@infobeans.com'),
    ('Rashmi Sharma', 'Sunita', 'SR1+10 (S)', 'rashmi.sharma@infobeans.com'),
    ('Hemant Joshi', 'Sunita', 'SR1+10 (S)', 'hemant.joshi@infobeans.com'),
    ('Santosh Dhawe', 'Sunita', 'SR1+10 (S)', 'santosh.dhawe@infobeans.com'),
    ('Mohit Varma', 'Vinay Chitimille', 'SR1+10 (V)', 'mohit.varma@infobeans.com'),
]

# Add employees
created_count = 0
for name, manager, department, email in employees_data:
    last_id += 1
    employee_id = f'{last_id:03d}'  # Format as 001, 002, 003, etc.
    
    # Check if employee already exists
    if Employee.objects.filter(email=email).exists():
        print(f'✓ {name} ({email}) - Already exists')
        continue
    
    try:
        employee = Employee(
            name=name,
            employee_id=employee_id,
            email=email,
            department=department,
            manager=manager,
            project_code=1000,
            is_active=True
        )
        employee.save()
        created_count += 1
        print(f'✓ {name} ({employee_id}) - Created')
    except Exception as e:
        print(f'✗ {name} - Error: {str(e)}')

print(f'\n✓ Total employees created: {created_count}')
