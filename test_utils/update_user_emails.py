#!/usr/bin/env python
"""
Script to update user emails from infobeans.com to testt.com
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timemaster_project.settings')
django.setup()

from django.contrib.auth.models import User

# Find all users with infobeans.com email
users = User.objects.filter(email__icontains='infobeans.com')
count = users.count()
print(f"Found {count} users with infobeans.com email")

# Update each user's email
updated = 0
for user in users:
    old_email = user.email
    user.email = user.email.replace('infobeans.com', 'testt.com')
    user.save()
    print(f"Updated: {old_email} → {user.email}")
    updated += 1

print(f"\nTotal updated: {updated} users")

# Verify the update
remaining = User.objects.filter(email__icontains='infobeans.com').count()
print(f"Remaining infobeans.com emails: {remaining}")

new_testt = User.objects.filter(email__icontains='testt.com').count()
print(f"Total testt.com emails: {new_testt}")
