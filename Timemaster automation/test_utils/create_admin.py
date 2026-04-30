#!/usr/bin/env python
"""Script to create superuser (admin) account"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from django.contrib.auth.models import User

try:
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print('✓ Superuser created successfully')
    print('  Username: admin')
    print('  Password: admin123')
except Exception as e:
    print(f'✗ Error: {e}')
